#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path
from typing import Optional

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
    extra_envelopes: dict[str, np.ndarray] | None = None,
) -> None:
    """
    Save the calculated results to a CSV file.

    If extra_envelopes are provided (for hybrid mode), they are added as new columns.
    """
    data = {
        "Time (s)": time_array,
        f"{magnitude} PGU (pu)": pcc_signal,
        f"{magnitude} lower (pu)": lower_envelope,
        f"{magnitude} upper (pu)": upper_envelope,
    }

    # Add extra envelopes if requested (Hybrid mode detailed output)
    if extra_envelopes:
        for name, signal in extra_envelopes.items():
            # Clean name for CSV header (e.g., "upper_overdamped" -> "P upper_overdamped (pu)")
            col_name = f"{magnitude} {name} (pu)"
            data[col_name] = signal

    df = pd.DataFrame(data)
    df.to_csv(path, index=False, sep=";", float_format="%.3e")


def find_start_trim_index(
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    tolerance: float = 1e-5,
    buffer_points: int = 10,
) -> int:
    """
    Find the index to trim leading stable data from signals.

    This function iterates forward from the start of the signals and finds the
    first point where there is a significant change in any of the signals.
    """
    for i in range(len(pcc_signal) - 1):
        pcc_changed = abs(pcc_signal[i + 1] - pcc_signal[i]) > tolerance
        down_changed = abs(lower_envelope[i + 1] - lower_envelope[i]) > tolerance
        up_changed = abs(upper_envelope[i + 1] - upper_envelope[i]) > tolerance

        if pcc_changed or down_changed or up_changed:
            # First significant change found. Return index with buffer.
            return max(0, i - buffer_points)

    # If no significant change is found, return 0 (no trimming).
    return 0


def find_end_trim_index(
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    tolerance: float = 1e-5,
    buffer_points: int = 10,
) -> int:
    """
    Find the index to trim trailing stable data from signals.

    This function iterates backward from the end of the signals and finds the
    last point where there is a significant change in any of the signals.
    """
    for i in range(len(pcc_signal) - 1, 0, -1):
        pcc_changed = abs(pcc_signal[i] - pcc_signal[i - 1]) > tolerance
        down_changed = abs(lower_envelope[i] - lower_envelope[i - 1]) > tolerance
        up_changed = abs(upper_envelope[i] - upper_envelope[i - 1]) > tolerance

        if pcc_changed or down_changed or up_changed:
            # Last significant change found. Return index with buffer.
            return min(i + buffer_points, len(pcc_signal))

    # If no significant change is found, return the original length (no trimming).
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
    disclaimer_message: str | None = None,
    extra_envelopes: dict[str, np.ndarray] | None = None,
) -> None:
    """
    Plot the results, trimming stable data at the start and end.

    Saves an interactive HTML file and a static PNG image.
    Includes optional extra envelopes for hybrid mode visualization.
    """
    # 1. Find the optimal indices to trim the data (based on main envelopes)
    start_index = find_start_trim_index(pcc_signal, lower_envelope, upper_envelope)
    end_index = find_end_trim_index(pcc_signal, lower_envelope, upper_envelope)

    # 2. Slice the arrays to remove redundant data.
    time_trimmed = time_array[start_index:end_index]
    pcc_trimmed = pcc_signal[start_index:end_index]
    down_trimmed = lower_envelope[start_index:end_index]
    up_trimmed = upper_envelope[start_index:end_index]

    # 2b. Slice extra envelopes if they exist
    extra_trimmed = {}
    if extra_envelopes:
        for name, signal in extra_envelopes.items():
            extra_trimmed[name] = signal[start_index:end_index]

    # 3. Prepare disclaimer text if needed
    disclaimer_text_mpl = ""
    disclaimer_text_html = ""
    if show_disclaimer:
        default_msg = "Inconsistent damping. Envelopes may be unreliable."
        disclaimer_text_mpl = "Disclaimer:\n" + (disclaimer_message or default_msg)
        html_msg = disclaimer_message.replace("\n", "<br>") if disclaimer_message else default_msg
        disclaimer_text_html = f"<b>Disclaimer:</b><br>{html_msg}"

    # --- Plotting with Matplotlib (for PNG) ---
    if "png" in output_format:
        plt.figure(figsize=(8, 5))

        # Plot Extra Envelopes first (behind the main lines) if they exist
        if extra_trimmed:
            colors = {"overdamped": "purple", "underdamped": "orange"}
            for name, signal in extra_trimmed.items():
                # Determine style based on name
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

        # Plot Main Envelopes and PCC
        plt.plot(
            time_trimmed,
            pcc_trimmed,
            label=f"{magnitude} at PGU",
            linewidth=3,
        )
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

        # Adjust legend to handle many items
        plt.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize="small")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.xlim(time_trimmed[0], time_trimmed[-1])

        # Tight layout to accommodate external legend
        plt.tight_layout()
        plt.savefig(path.with_suffix(".png"), bbox_inches="tight", dpi=300)
        plt.close()

    # --- Plotting with Plotly (for HTML) ---
    if "html" in output_format:
        fig = go.Figure()

        # Add filled area for envelopes
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

        # Plot Extra Envelopes
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

        # Plot Main Lines
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

        fig.update_layout(
            title_text=title,
            xaxis_title="Time (s)",
            yaxis_title=f"{magnitude} (pu)",
            legend=dict(x=1.02, y=0.5, xanchor="left", yanchor="middle"),
            template="plotly_white",
            margin=dict(r=150),  # Add margin for external legend
        )

        fig.write_html(path.with_suffix(".html"))
