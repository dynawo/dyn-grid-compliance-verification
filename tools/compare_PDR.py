#!/usr/bin/env python3
import argparse
import math
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objs as go


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name).strip("._") or "signal"


def find_csv_files(root: Path, csv_name: str, depth: int = 4) -> dict[str, Path]:
    """Busca archivos CSV solo en directorios con profundidad específica desde root."""
    mapping = {}
    for csv_path in root.rglob(csv_name):
        parent = csv_path.parent
        try:
            rel_parts = parent.relative_to(root).parts
        except ValueError:
            continue
        if len(rel_parts) == depth:
            rel_key = str(parent.relative_to(root))
            mapping[rel_key] = csv_path
    return mapping


def load_curves(csv_path: Path, time_col: str = "time") -> pd.DataFrame:
    # Lectura con delimitador ';'
    df = pd.read_csv(csv_path, sep=";", engine="python")
    if time_col not in df.columns:
        raise KeyError(f"Time column '{time_col}' not found in {csv_path}")
    tc = df[time_col]
    df[time_col] = pd.to_numeric(tc, errors="coerce")
    if df[time_col].isna().any():
        dt = pd.to_datetime(tc, errors="coerce")
        base = dt.dropna().iloc[0]
        df[time_col] = (dt - base).dt.total_seconds()
    return df.sort_values(time_col).reset_index(drop=True)


def align_on_union(
    df_a: pd.DataFrame, df_b: pd.DataFrame, time_col: str, interpolate: bool = True
):
    union_t = np.union1d(df_a[time_col].to_numpy(), df_b[time_col].to_numpy())

    def _prep(df):
        # Eliminar duplicados antes de reindexar
        df = df.drop_duplicates(subset=[time_col])
        df = df.set_index(time_col)
        df = df[[c for c in df.columns if c != time_col]].reindex(union_t)
        if interpolate:
            df = df.interpolate(method="index", limit_direction="both")
        return df

    return union_t, _prep(df_a), _prep(df_b)


def compute_metrics(a: pd.Series, b: pd.Series):
    mask = (~a.isna()) & (~b.isna())
    if mask.sum() == 0:
        return {"n_points": 0, "rmse": math.nan, "mae": math.nan, "max_abs_err": math.nan}
    diff = (a[mask] - b[mask]).to_numpy()
    return {
        "n_points": int(mask.sum()),
        "rmse": float(np.sqrt(np.mean(diff**2))),
        "mae": float(np.mean(np.abs(diff))),
        "max_abs_err": float(np.max(np.abs(diff))),
    }


def create_html_plot(time_axis, A, B, scenario_name, label_a, label_b, output_path: Path):
    signals = sorted(set(A.columns).union(B.columns))
    fig = go.Figure()

    # Add traces for all signals (initially only first visible)
    for i, sig in enumerate(signals):
        y_a = A[sig] if sig in A.columns else pd.Series(index=A.index, dtype=float)
        y_b = B[sig] if sig in B.columns else pd.Series(index=B.index, dtype=float)
        fig.add_trace(
            go.Scatter(
                x=time_axis, y=y_a, mode="lines", name=f"{sig} ({label_a})", visible=(i == 0)
            )
        )
        fig.add_trace(
            go.Scatter(
                x=time_axis, y=y_b, mode="lines", name=f"{sig} ({label_b})", visible=(i == 0)
            )
        )

    # Create buttons for signal selection
    buttons = []
    for i, sig in enumerate(signals):
        vis = [False] * len(fig.data)
        vis[2 * i] = True
        vis[2 * i + 1] = True
        buttons.append(
            dict(
                label=sig,
                method="update",
                args=[
                    {"visible": vis},
                    {"title.text": f"Scenario: {scenario_name} | Signal: {sig}"},
                ],
            )
        )

    # Update layout: selector near legend, dynamic title
    fig.update_layout(
        updatemenus=[
            dict(
                active=0,
                buttons=buttons,
                x=1.02,
                y=0.5,
                xanchor="left",
                yanchor="middle",
                direction="down",
            )
        ],
        title=f"Scenario: {scenario_name} | Signal: {signals[0] if signals else ''}",
        xaxis_title="Time [s]",
        yaxis_title="Value",
        height=600,
    )

    fig.write_html(str(output_path))


def build_model_paths(base_dir: Path, case_name: str) -> tuple[Path, Path]:
    return base_dir / case_name / "Dynawo", base_dir / f"{case_name}PDRControl" / "Dynawo"


def run_dycov(
    dynawo: Path, dynawo_pdr: Path, model: Path, model_pdr: Path, out: Path, out_pdr: Path
):
    subprocess.run(
        ["bash", "-lc", f"dycov performance -m {model} -o {out} -l {dynawo} --testing"], check=True
    )
    subprocess.run(
        [
            "bash",
            "-lc",
            f"dycov performance -m {model_pdr} -o {out_pdr} -l {dynawo_pdr} --testing",
        ],
        check=True,
    )


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run DyCoV and compare curves_calculated.csv files with interactive HTML plots"
    )
    parser.add_argument(
        "--dynawo", type=Path, default=Path("dynawo.sh"), help="Nightly Dynawo launcher"
    )
    parser.add_argument(
        "--dynawo-pdr",
        type=Path,
        default=Path("dynawo.sh"),
        help="Dynawo with PDR models launcher",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("examples/Performance/Single"),
        help="Base directory for the case_name",
    )
    parser.add_argument("--case-name", type=str, help="Case name used to build model paths")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("Output"), help="Directory for HTML outputs"
    )
    parser.add_argument(
        "--csv-name", type=str, default="curves_calculated.csv", help="Name of CSV file to compare"
    )
    parser.add_argument(
        "--time-col", type=str, default="time", help="Name of time column in CSV files"
    )
    parser.add_argument(
        "--depth", type=int, default=4, help="Directory depth where CSV files are located"
    )
    parser.add_argument(
        "--keep-results",
        action="store_true",
        help="Keep dycov results directories instead of deleting",
    )
    return parser.parse_args()


def run_comparisons(args):
    ensure_dir(args.output_dir)
    model, model_pdr = build_model_paths(args.base_dir, args.case_name)
    global_summary, index_links = [], []

    with tempfile.TemporaryDirectory() as tmpdir:
        results_root = Path(tmpdir) / "Results"
        results_pdr_root = Path(tmpdir) / "ResultsPDR"
        run_dycov(args.dynawo, args.dynawo_pdr, model, model_pdr, results_root, results_pdr_root)

        map_a = find_csv_files(results_root, args.csv_name, depth=args.depth)
        map_b = find_csv_files(results_pdr_root, args.csv_name, depth=args.depth)
        common_keys = sorted(set(map_a.keys()).intersection(map_b.keys()))

        for key in common_keys:
            df_a = load_curves(map_a[key], args.time_col)
            df_b = load_curves(map_b[key], args.time_col)
            time_axis, A, B = align_on_union(df_a, df_b, args.time_col)

            scenario_dir = args.output_dir / key
            ensure_dir(scenario_dir)
            html_path = scenario_dir / "comparison.html"
            create_html_plot(time_axis, A, B, key, "Results", "ResultsPDR", html_path)

            for sig in sorted(set(A.columns).union(B.columns)):
                m = compute_metrics(
                    A[sig] if sig in A.columns else pd.Series(index=A.index),
                    B[sig] if sig in B.columns else pd.Series(index=B.index),
                )
                m.update({"scenario": key, "signal": sig, "html": str(html_path)})
                global_summary.append(m)

            rel_link = str((scenario_dir / "comparison.html").relative_to(args.output_dir))
            index_links.append(f'<li><a href="{rel_link}">{key}</a></li>')

    return global_summary, index_links


def generate_summary_files(args, global_summary, index_links):
    summary_df = pd.DataFrame(global_summary)

    # Improved summary
    rename_map = {
        "scenario": "Scenario",
        "signal": "Signal",
        "n_points": "Number of Points",
        "rmse": "RMSE (Root Mean Square Error)",
        "mae": "MAE (Mean Absolute Error)",
        "max_abs_err": "Max Absolute Error",
        "html": "HTML Report Path",
    }
    readable_df = summary_df.rename(columns=rename_map)
    ordered_cols = [
        "Scenario",
        "Signal",
        "Number of Points",
        "RMSE (Root Mean Square Error)",
        "MAE (Mean Absolute Error)",
        "Max Absolute Error",
        "HTML Report Path",
    ]
    readable_df = readable_df[[c for c in ordered_cols if c in readable_df.columns]]
    readable_path = args.output_dir / "global_summary_readable.csv"
    readable_df.to_csv(readable_path, index=False)

    # Metadata
    meta_path = args.output_dir / "global_summary_metadata.txt"
    with open(meta_path, "w", encoding="utf-8") as f_meta:
        f_meta.write("Column Descriptions:\n")
        for col in ordered_cols:
            desc = {
                "Scenario": "PCS-Benchmark-OperatingCondition Identifier",
                "Signal": "Name of the signal compared",
                "Number of Points": "Aligned time points",
                "RMSE (Root Mean Square Error)": "Deviation between curves",
                "MAE (Mean Absolute Error)": "Average absolute difference",
                "Max Absolute Error": "Maximum absolute difference",
                "HTML Report Path": "Path to HTML plot",
            }.get(col, "")
            f_meta.write(f"{col}: {desc}\n")

    # Index HTML
    with (args.output_dir / "index.html").open("w", encoding="utf-8") as f:
        f.write("<html><body><h1>Scenario Comparison Index</h1><ul>")
        f.write("\n".join(index_links))
        f.write("</ul></body></html>")

    print(f"Created {len(index_links)} scenario comparisons.")
    print(f"Readable summary: {readable_path}")
    print(f"Metadata: {meta_path}")


def main():
    args = parse_arguments()
    global_summary, index_links = run_comparisons(args)
    generate_summary_files(args, global_summary, index_links)


if __name__ == "__main__":
    main()
