import argparse
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objs as go


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def find_csv_files(root: Path, csv_name: str, depth: int = 4):
    mapping = {}
    for csv_path in root.rglob(csv_name):
        parent = csv_path.parent
        try:
            rel_parts = parent.relative_to(root).parts
        except ValueError:
            continue
        if len(rel_parts) == depth:
            mapping[str(parent.relative_to(root))] = csv_path
    return mapping


def load_curves(csv_path: Path, time_col: str = "time") -> pd.DataFrame:
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


def align_on_union(df_a, df_b, time_col, interpolate=True):
    union_t = np.union1d(df_a[time_col].to_numpy(), df_b[time_col].to_numpy())

    def _prep(df):
        df = df.drop_duplicates(subset=[time_col]).set_index(time_col)
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


def copy_and_toggle_ppc_local(src_dynawo_dir: Path, dst_dynawo_dir: Path):
    if dst_dynawo_dir.exists():
        shutil.rmtree(dst_dynawo_dir)
    shutil.copytree(src_dynawo_dir, dst_dynawo_dir)
    candidates = list(dst_dynawo_dir.glob("*.par")) + list(dst_dynawo_dir.glob("*.PAR"))
    if not candidates:
        candidates.extend(list(dst_dynawo_dir.rglob("*.par")))
        candidates.extend(list(dst_dynawo_dir.rglob("*.PAR")))
    if not candidates:
        raise FileNotFoundError(f"No PAR file found under {dst_dynawo_dir}")
    par_path = candidates[0]
    text = par_path.read_text(encoding="utf-8")
    old_text = '_PPCLocal" value="false"/>'
    new_text = '_PPCLocal" value="true"/>'
    if old_text not in text:
        pattern = r"_PPCLocal\" value=\"false\"/>"
        if re.search(pattern, text) is None:
            raise ValueError(f"Expected text '{old_text}' not found in {par_path}")
        new_text_effective = re.sub(pattern, new_text, text)
    else:
        new_text_effective = text.replace(old_text, new_text)
    par_path.write_text(new_text_effective, encoding="utf-8")
    return par_path


def run_dycov(
    dynawo_launcher: Path, model_base: Path, model_pdr: Path, out_base: Path, out_pdr: Path
):
    subprocess.run(
        [
            "bash",
            "-lc",
            f"dycov performance -m {model_base} -o {out_base} -l {dynawo_launcher} --testing",
        ],
        check=True,
    )
    subprocess.run(
        [
            "bash",
            "-lc",
            f"dycov performance -m {model_pdr} -o {out_pdr} -l {dynawo_launcher} --testing",
        ],
        check=True,
    )


def parse_arguments():
    default_dynawo = Path(os.environ.get("DYNAWOPATH", "dynawo.sh"))
    parser = argparse.ArgumentParser(
        description="Run DyCoV twice (PPCLocal vs NotPPCLocal) and compare curves_calculated.csv"
    )
    parser.add_argument("--dynawo", type=Path, default=default_dynawo, help="Dynawo launcher")
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("examples/Performance/Single"),
        help="Base directory for the case",
    )
    parser.add_argument("--case-name", type=str, required=True, help="Case name")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("Output"), help="Directory for HTML outputs"
    )
    parser.add_argument(
        "--csv-name", type=str, default="curves_calculated.csv", help="CSV file name"
    )
    parser.add_argument("--time-col", type=str, default="time", help="Time column name")
    parser.add_argument("--depth", type=int, default=4, help="Directory depth for CSV search")
    return parser.parse_args()


def run_comparisons(args):
    ensure_dir(args.output_dir)
    src_dynawo = args.base_dir / args.case_name / "Dynawo"
    if not src_dynawo.exists():
        raise FileNotFoundError(f"Dynawo directory not found: {src_dynawo}")
    global_summary, index_links = [], []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        model_base = tmp / "DynawoBase"
        model_pdr = tmp / "DynawoPDR"
        copy_and_toggle_ppc_local(src_dynawo, model_base)
        shutil.copytree(src_dynawo, model_pdr)
        results_base_root = tmp / "ResultsBase"
        results_pdr_root = tmp / "ResultsPDR"
        run_dycov(args.dynawo, model_base, model_pdr, results_base_root, results_pdr_root)
        map_a = find_csv_files(results_base_root, args.csv_name, depth=args.depth)
        map_b = find_csv_files(results_pdr_root, args.csv_name, depth=args.depth)
        common_keys = sorted(set(map_a.keys()).intersection(map_b.keys()))
        for key in common_keys:
            df_a = load_curves(map_a[key], args.time_col)
            df_b = load_curves(map_b[key], args.time_col)
            time_axis, A, B = align_on_union(df_a, df_b, args.time_col)
            scenario_dir = args.output_dir / key
            ensure_dir(scenario_dir)
            html_path = scenario_dir / "comparison.html"
            create_html_plot(time_axis, A, B, key, "PPCLocal", "NotPPCLocal", html_path)
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
    rename_map = {
        "scenario": "Scenario",
        "signal": "Signal",
        "n_points": "Number of Points",
        "rmse": "RMSE",
        "mae": "MAE",
        "max_abs_err": "Max Absolute Error",
        "html": "HTML Report Path",
    }
    readable_df = summary_df.rename(columns=rename_map)
    readable_path = args.output_dir / "global_summary_readable.csv"
    readable_df.to_csv(readable_path, index=False)
    with (args.output_dir / "index.html").open("w", encoding="utf-8") as f:
        f.write("<html><body><h1>Scenario Comparison Index</h1><ul>")
        f.write("\n".join(index_links))
        f.write("</ul></body></html>")
    print(f"Created {len(index_links)} scenario comparisons.")
    print(f"Summary: {readable_path}")


def main():
    args = parse_arguments()
    global_summary, index_links = run_comparisons(args)
    generate_summary_files(args, global_summary, index_links)


if __name__ == "__main__":
    main()
