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

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib import pyplot as plt


def save_results_to_csv(
    path: Path,
    magnitude: str,
    time_array: np.ndarray,
    pcc: np.ndarray,
    down: np.ndarray,
    up: np.ndarray,
) -> None:
    """
    Save the calculated results (PCC, down, up) to a CSV file.

    Parameters
    ----------
    path : Path
        The file path where the CSV file will be saved.
    magnitude : str
        Name of the magnitude.
    time_array : np.ndarray
        The time array corresponding to the power signals.
    pcc : np.ndarray
        The calculated power at the point of common coupling.
    down : np.ndarray
        The lower power envelope.
    up : np.ndarray
        The upper power envelope.
    """
    df = pd.DataFrame(
        {
            "Time (s)": time_array,
            f"{magnitude} PCC (pu)": pcc,
            f"{magnitude} down (pu)": down,
            f"{magnitude} up (pu)": up,
        }
    )
    df.to_csv(path, index=False, sep=";", float_format="%.3e")


def find_start_trim_index(
    pcc: np.ndarray,
    down: np.ndarray,
    up: np.ndarray,
    tolerance: float = 1e-5,
    buffer_points: int = 10,
) -> int:
    """
    Find the index to trim leading stable data from signals.

    This function iterates forward from the start of the signals and finds the
    first point where there is a significant change in any of the signals.

    Args:
        pcc: The main signal array.
        down: The lower envelope signal array.
        up: The upper envelope signal array.
        tolerance: The minimum change between two consecutive points to be
                   considered a variation.
        buffer_points: Number of data points to keep before the first detected
                       change to provide some context.

    Returns:
        The index from which the data should be kept.
    """
    # Start from the first point and go forward
    for i in range(len(pcc) - 1):
        # Check if the absolute difference in any signal is greater than the tolerance
        pcc_changed = abs(pcc[i + 1] - pcc[i]) > tolerance
        down_changed = abs(down[i + 1] - down[i]) > tolerance
        up_changed = abs(up[i + 1] - up[i]) > tolerance

        if pcc_changed or down_changed or up_changed:
            # First significant change found at index i.
            # We determine the start index by subtracting a small buffer.
            # Ensure the index is not negative.
            start_index = max(0, i - buffer_points)
            return start_index

    # If no significant change is found, return 0 (no trimming)
    return 0


def find_end_trim_index(
    pcc: np.ndarray,
    down: np.ndarray,
    up: np.ndarray,
    tolerance: float = 1e-5,
    buffer_points: int = 10,
) -> int:
    """
    Find the index to trim trailing stable data from signals.

    This function iterates backward from the end of the signals and finds the
    last point where there is a significant change in any of the signals.

    Args:
        pcc: The main signal array.
        down: The lower envelope signal array.
        up: The upper envelope signal array.
        tolerance: The minimum change between two consecutive points to be
                   considered a variation.
        buffer_points: Number of data points to keep after the last detected
                       change to provide some context.

    Returns:
        The index up to which the data should be kept.
    """
    # Start from the second-to-last point and go backward
    for i in range(len(pcc) - 1, 0, -1):
        # Check if the absolute difference in any signal is greater than the tolerance
        pcc_changed = abs(pcc[i] - pcc[i - 1]) > tolerance
        down_changed = abs(down[i] - down[i - 1]) > tolerance
        up_changed = abs(up[i] - up[i - 1]) > tolerance

        if pcc_changed or down_changed or up_changed:
            # Last significant change found at index i.
            # We determine the trim index by adding a small buffer.
            # Ensure the index does not exceed the array bounds.
            end_index = min(i + buffer_points, len(pcc))
            return end_index

    # If no significant change is found, return the original length (no trimming)
    return len(pcc)


def plot_results(
    path: Path,
    title: str,
    magnitude: str,
    time: np.ndarray,
    event_time: float,
    shift_time: float,
    pcc: np.ndarray,
    down: np.ndarray,
    up: np.ndarray,
    format: str,
    params_list: list = None,
) -> None:
    """
    Plot the results, trimming any stable/redundant data at the start and end.

    The interactive plot is saved as a self-contained HTML file, and a
    static version is saved as a PNG image.
    """
    # 1. Find the optimal indices to trim the data from the start and end
    start_index = find_start_trim_index(pcc, down, up)
    end_index = find_end_trim_index(pcc, down, up)

    # 2. Slice the arrays to remove redundant data from both ends
    time_trimmed = time[start_index:end_index]
    pcc_trimmed = pcc[start_index:end_index]
    down_trimmed = down[start_index:end_index]
    up_trimmed = up[start_index:end_index]

    # --- Plotting with Matplotlib (for PNG) ---
    if "png" in format:
        plt.figure(figsize=(8, 5))
        plt.plot(
            time_trimmed,
            pcc_trimmed,
            label=f"{magnitude} at PCC",
            linewidth=3,
        )
        plt.plot(
            time_trimmed, down_trimmed, label=f"{magnitude} envelopes", linewidth=2, color="red"
        )
        plt.plot(time_trimmed, up_trimmed, linewidth=2, color="red")
        plt.xlabel("t (s)")
        plt.ylabel(f"{magnitude} (pu)")
        plt.title(title)

        plt.axvline(
            x=event_time + shift_time / 1000,
            color="black",
            linestyle="--",
            label="t at Event Time",
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

        plt.legend(loc="lower right")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.xlim(time_trimmed[0], time_trimmed[-1])  # Ensure x-axis is trimmed too

        plt.savefig(path.with_suffix(".png"), bbox_inches="tight", dpi=300)
        plt.close()

    # --- Plotting with Plotly (for HTML) ---
    if "html" in format:
        fig = go.Figure()

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
                name=f"{magnitude} at PCC",
            )
        )

        event_time_sec = event_time + shift_time / 1000
        fig.add_vline(
            x=event_time_sec,
            line_width=2,
            line_dash="dash",
            line_color="black",
        )
        fig.add_trace(
            go.Scatter(
                x=[event_time_sec, event_time_sec],
                y=[np.min(down_trimmed), np.max(up_trimmed)],
                mode="lines",
                line=dict(color="black", dash="dash"),
                name="t at Event Time",
            )
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

        fig.update_layout(
            title_text=title,
            xaxis_title="t (s)",
            yaxis_title=f"{magnitude} (pu)",
            legend=dict(x=0.99, y=0.01, xanchor="right", yanchor="bottom"),
            template="plotly_white",
        )

        fig.write_html(path.with_suffix(".html"))
