#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

import configparser
import importlib.metadata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib import pyplot as plt


def save_results_to_csv(
    path: Path,
    magnitude: str,
    time_array: np.ndarray,
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    extra_envelopes: dict[str, np.ndarray] = None,
) -> None:
    """Exports envelopes and signals to a CSV file.

    Parameters
    ----------
    path : Path
        Destination path for the output CSV file.
    magnitude : str
        Physical magnitude analyzed (e.g., 'P', 'Iq').
    time_array : np.ndarray
        Simulation time steps.
    pcc_signal : np.ndarray
        Recorded system signal at the Point of Common Coupling.
    lower_envelope : np.ndarray
        Lower bound of the calculated envelope.
    upper_envelope : np.ndarray
        Upper bound of the calculated envelope.
    extra_envelopes : dict[str, np.ndarray], optional
        Additional data series to append as columns.
    """
    data = {
        "Time (s)": time_array,
        f"{magnitude} PGU (pu)": pcc_signal,
        f"{magnitude} lower (pu)": lower_envelope,
        f"{magnitude} upper (pu)": upper_envelope,
    }

    if extra_envelopes:
        for name, signal in extra_envelopes.items():
            data[f"{magnitude} {name} (pu)"] = signal

    df = pd.DataFrame(data)
    df.to_csv(path, index=False, sep=";", float_format="%.3e")


def find_start_trim_index(
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    tolerance: float = 1e-5,
    buffer_points: int = 10,
) -> int:
    """Finds the starting index to trim leading stable data.

    Stops at the first significant variation exceeding the tolerance.

    Parameters
    ----------
    pcc_signal : np.ndarray
        Recorded system signal array.
    lower_envelope : np.ndarray
        Lower bounded envelope array.
    upper_envelope : np.ndarray
        Upper bounded envelope array.
    tolerance : float, optional
        Absolute difference threshold to trigger detection.
    buffer_points : int, optional
        Number of points to preserve prior to the detected change.

    Returns
    -------
    int
        Recommended starting index for analysis.
    """
    for i in range(len(pcc_signal) - 1):
        pcc_changed = abs(pcc_signal[i + 1] - pcc_signal[i]) > tolerance
        down_changed = abs(lower_envelope[i + 1] - lower_envelope[i]) > tolerance
        up_changed = abs(upper_envelope[i + 1] - upper_envelope[i]) > tolerance

        if pcc_changed or down_changed or up_changed:
            return max(0, i - buffer_points)

    return 0


def find_end_trim_index(
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    tolerance: float = 1e-5,
    buffer_points: int = 10,
) -> int:
    """Finds the ending index to trim trailing stable data.

    Stops at the last point where a significant variation is detected.

    Parameters
    ----------
    pcc_signal : np.ndarray
        Recorded system signal array.
    lower_envelope : np.ndarray
        Lower bounded envelope array.
    upper_envelope : np.ndarray
        Upper bounded envelope array.
    tolerance : float, optional
        Absolute difference threshold to trigger detection.
    buffer_points : int, optional
        Number of points to preserve after the detected change.

    Returns
    -------
    int
        Recommended ending index for analysis.
    """
    for i in range(len(pcc_signal) - 1, 0, -1):
        pcc_changed = abs(pcc_signal[i] - pcc_signal[i - 1]) > tolerance
        down_changed = abs(lower_envelope[i] - lower_envelope[i - 1]) > tolerance
        up_changed = abs(upper_envelope[i] - upper_envelope[i - 1]) > tolerance

        if pcc_changed or down_changed or up_changed:
            return min(i + buffer_points, len(pcc_signal))

    return len(pcc_signal)


def plot_results(
    path: Path,
    title: str,
    magnitude: str,
    time_array: np.ndarray,
    event_time: float,
    shift_time: float,
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    output_format: str,
    params_list: list = None,
    show_disclaimer: bool = False,
    disclaimer_message: str = None,
    extra_envelopes: dict[str, np.ndarray] = None,
) -> None:
    """Renders and exports simulation results graphically.

    Automatically trims stable data and generates HTML/PNG files.

    Parameters
    ----------
    path : Path
        Base file path for output plots.
    title : str
        Plot title.
    magnitude : str
        Physical magnitude graphed (e.g., 'P', 'Iq').
    time_array : np.ndarray
        Simulation time array.
    event_time : float
        Absolute time indicating the event start.
    shift_time : float
        Temporal shift applied to the event marker line.
    pcc_signal : np.ndarray
        Main signal from the Point of Common Coupling.
    lower_envelope : np.ndarray
        Lower bound envelope.
    upper_envelope : np.ndarray
        Upper bound envelope.
    output_format : str
        Desired output format(s), e.g., 'png&html'.
    params_list : list, optional
        Simulation parameters for the legend.
    show_disclaimer : bool, optional
        If True, renders a warning disclaimer overlay.
    disclaimer_message : str, optional
        Custom text for the disclaimer overlay.
    extra_envelopes : dict[str, np.ndarray], optional
        Supplementary bounding envelopes to render.
    """
    start_index = find_start_trim_index(pcc_signal, lower_envelope, upper_envelope)
    end_index = find_end_trim_index(pcc_signal, lower_envelope, upper_envelope)

    time_trimmed = time_array[start_index:end_index]
    pcc_trimmed = pcc_signal[start_index:end_index]
    down_trimmed = lower_envelope[start_index:end_index]
    up_trimmed = upper_envelope[start_index:end_index]

    extra_trimmed = {}
    if extra_envelopes:
        for name, signal in extra_envelopes.items():
            extra_trimmed[name] = signal[start_index:end_index]

    disclaimer_text_mpl = ""
    disclaimer_text_html = ""

    if show_disclaimer:
        default_msg = "Inconsistent damping. Envelopes may be unreliable."
        disclaimer_text_mpl = "Disclaimer:\n" + (disclaimer_message or default_msg)
        html_msg = disclaimer_message.replace("\n", "<br>") if disclaimer_message else default_msg
        disclaimer_text_html = f"<b>Disclaimer:</b><br>{html_msg}"

    try:
        software_version = importlib.metadata.version("dycov")
        watermark_text = f"dycov v{software_version}"
    except importlib.metadata.PackageNotFoundError:
        watermark_text = "dycov v(unknown)"

    # Matplotlib PNG Generation
    if "png" in output_format:
        plt.figure(figsize=(8, 5))

        if extra_trimmed:
            colors = {"overdamped": "purple", "underdamped": "orange"}
            for name, signal in extra_trimmed.items():
                style_color = "gray"
                if "overdamped" in name:
                    style_color = colors["overdamped"]
                if "underdamped" in name:
                    style_color = colors["underdamped"]

                plt.plot(
                    time_trimmed,
                    signal,
                    linestyle=":",
                    linewidth=1,
                    color=style_color,
                    alpha=0.7,
                    label=name.replace("_", " ").title(),
                )

        plt.plot(time_trimmed, pcc_trimmed, label=f"{magnitude} at PGU", linewidth=3)
        plt.plot(
            time_trimmed, down_trimmed, label=f"{magnitude} envelopes", linewidth=2, color="red"
        )
        plt.plot(time_trimmed, up_trimmed, linewidth=2, color="red")

        plt.xlabel("Time (s)")
        plt.ylabel(f"{magnitude} (pu)")
        plt.title(title)
        plt.axvline(
            x=event_time + shift_time / 1000,
            color="black",
            linestyle="--",
            label="Event Time",
        )

        if params_list:
            full_text = "\n".join(params_list)
            plt.text(
                0.98,
                0.98,
                full_text,
                transform=plt.gca().transAxes,
                fontsize=9,
                verticalalignment="top",
                horizontalalignment="right",
                bbox=dict(boxstyle="round,pad=0.5", fc="wheat", alpha=0.5),
            )

        if show_disclaimer:
            plt.text(
                0.02,
                0.02,
                disclaimer_text_mpl,
                transform=plt.gca().transAxes,
                fontsize=8,
                color="red",
                verticalalignment="bottom",
                horizontalalignment="left",
                bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="red", alpha=0.8),
            )

        plt.text(
            0.98,
            0.02,
            watermark_text,
            transform=plt.gca().transAxes,
            fontsize=12,
            color="gray",
            alpha=0.3,
            verticalalignment="bottom",
            horizontalalignment="right",
        )

        plt.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize="small")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.xlim(time_trimmed[0], time_trimmed[-1])
        plt.tight_layout()
        plt.savefig(path.with_suffix(".png"), bbox_inches="tight", dpi=300)
        plt.close()

    # Plotly HTML Generation
    if "html" in output_format:
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=np.concatenate([time_trimmed, time_trimmed[::-1]]),
                y=np.concatenate([up_trimmed, down_trimmed[::-1]]),
                fill="toself",
                fillcolor="rgba(255, 0, 0, 0.2)",
                line=dict(color="rgba(255, 255, 255, 0)"),
                hoverinfo="none",
                showlegend=False,
            )
        )

        if extra_trimmed:
            colors = {"overdamped": "purple", "underdamped": "orange"}
            for name, signal in extra_trimmed.items():
                style_color = "gray"
                if "overdamped" in name:
                    style_color = colors["overdamped"]
                if "underdamped" in name:
                    style_color = colors["underdamped"]

                fig.add_trace(
                    go.Scatter(
                        x=time_trimmed,
                        y=signal,
                        mode="lines",
                        line=dict(color=style_color, width=1, dash="dot"),
                        name=name.replace("_", " ").title(),
                        opacity=0.7,
                    )
                )

        fig.add_trace(
            go.Scatter(
                x=time_trimmed,
                y=up_trimmed,
                mode="lines",
                line=dict(color="red", width=2),
                name=f"{magnitude} envelopes",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=time_trimmed,
                y=down_trimmed,
                mode="lines",
                line=dict(color="red", width=2),
                showlegend=False,
            )
        )

        fig.add_trace(
            go.Scatter(
                x=time_trimmed,
                y=pcc_trimmed,
                mode="lines",
                line=dict(color="blue", width=3),
                name=f"{magnitude} PGU",
            )
        )

        event_time_sec = event_time + shift_time / 1000
        fig.add_vline(
            x=event_time_sec,
            line_width=2,
            line_dash="dash",
            line_color="black",
            annotation_text="Event Time",
            annotation_position="top right",
        )

        if params_list:
            full_text = "<br>".join(params_list)
            fig.add_annotation(
                xref="paper",
                yref="paper",
                x=0.98,
                y=0.98,
                text=full_text,
                showarrow=False,
                align="right",
                valign="top",
                bgcolor="rgba(245, 222, 179, 0.7)",
                borderpad=10,
            )

        if show_disclaimer:
            fig.add_annotation(
                xref="paper",
                yref="paper",
                x=0.02,
                y=0.02,
                text=disclaimer_text_html,
                showarrow=False,
                align="left",
                valign="bottom",
                font=dict(color="red", size=10),
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="red",
                borderwidth=1,
                borderpad=10,
            )

        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.98,
            y=0.02,
            text=watermark_text,
            showarrow=False,
            font=dict(color="gray", size=14),
            opacity=0.3,
            xanchor="right",
            yanchor="bottom",
        )

        fig.update_layout(
            title_text=title,
            xaxis_title="Time (s)",
            yaxis_title=f"{magnitude} (pu)",
            legend=dict(x=1.02, y=0.5, xanchor="left", yanchor="middle"),
            template="plotly_white",
            margin=dict(r=150),
        )

        fig.write_html(path.with_suffix(".html"))


def save_ini_dump(
    path: Path,
    parameters: Any,
    producer_config: configparser.ConfigParser,
    calculator: Any,
) -> None:
    """Serializes simulation entity attributes to a text file.

    Parameters
    ----------
    path : Path
        Destination file path.
    parameters : GFMParameters
        Parameter configuration guiding the simulation.
    producer_config : configparser.ConfigParser
        Parsed INI settings.
    calculator : GFMCalculator
        Instantiated calculator object.
    """

    def _write_dict(f: Any, title: str, data_dict: dict) -> None:
        """Helper to format and write a dictionary to a file."""
        f.write(f"\n{'=' * 30}\n")
        f.write(f" {title}\n")
        f.write(f"{'=' * 30}\n")
        for key, value in sorted(data_dict.items()):
            if not callable(value):
                f.write(f"{key} = {value}\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("GFM SIMULATION DUMP\n")
        f.write("===================\n")
        f.write(f"\n{'=' * 30}\n")
        f.write(" Key Validation Values\n")
        f.write(f"{'=' * 30}\n")

        try:
            d_vals = getattr(calculator, "_d_vals", None)
            h_vals = getattr(calculator, "_h_vals", None)
            eps_vals = getattr(calculator, "_epsilon_vals", None)

            if d_vals is not None and h_vals is not None:
                for i in range(len(d_vals)):
                    label = "Nominal" if i == 0 else f"Variation {i}"
                    line = f"[{label}] D = {d_vals[i]:.6f}, H = {h_vals[i]:.6f}"
                    if eps_vals is not None and i < len(eps_vals):
                        line += f", Epsilon = {eps_vals[i]:.6f}"
                    f.write(line + "\n")
            else:
                f.write("D and H variations data not available in calculator.\n")
        except Exception as e:
            f.write(f"Could not retrieve validation values: {e}\n")

        if hasattr(parameters, "__dict__"):
            _write_dict(f, "GFMParameters Attributes", parameters.__dict__)

        if hasattr(calculator, "__dict__"):
            _write_dict(f, "GFMCalculator Attributes", calculator.__dict__)

        f.write(f"\n{'=' * 30}\n")
        f.write(" GFMProducer Configuration (INI)\n")
        f.write(f"{'=' * 30}\n")

        if producer_config:
            for section in producer_config.sections():
                f.write(f"[{section}]\n")
                for key, value in producer_config.items(section):
                    f.write(f"{key} = {value}\n")
                f.write("\n")
