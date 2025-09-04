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
    Plot the results of the GFM phase jump using Plotly.

    The interactive plot is saved as a self-contained HTML file, and a
    static version is saved as a PNG image.
    """
    if "png" in format:
        plt.figure(figsize=(8, 5))
        plt.plot(
            time,
            pcc,
            label=f"{magnitude} at PCC",
            linewidth=3,
        )
        plt.plot(time, down, label=f"{magnitude} envelopes", linewidth=2, color="red")
        plt.plot(time, up, linewidth=2, color="red")
        plt.xlabel("t (s)")
        plt.ylabel(f"{magnitude} (pu)")
        plt.title(title)

        plt.axvline(
            x=event_time + shift_time / 1000,  # Convert ms to seconds
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
        plt.grid(True)
        plt.savefig(path.with_suffix(".png"), bbox_inches="tight", dpi=300)
        plt.close()

    if "html" in format:
        fig = go.Figure()

        # Add envelope traces
        fig.add_trace(
            go.Scatter(
                x=time,
                y=up,
                mode="lines",
                line=dict(color="red", width=2),
                name=f"{magnitude} envelopes",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=time,
                y=down,
                mode="lines",
                line=dict(color="red", width=2),
                showlegend=False,  # Avoid duplicating the legend entry for the envelope
            )
        )

        # Add main PCC trace
        fig.add_trace(
            go.Scatter(
                x=time,
                y=pcc,
                mode="lines",
                line=dict(color="blue", width=3),
                name=f"{magnitude} at PCC",
            )
        )

        # Add vertical line for the event time
        event_time_sec = event_time + shift_time / 1000
        fig.add_vline(
            x=event_time_sec,
            line_width=2,
            line_dash="dash",
            line_color="black",
        )
        # Trick to add a legend entry for the vertical line
        fig.add_trace(
            go.Scatter(
                x=[event_time_sec, event_time_sec],
                y=[np.min(down), np.max(up)],
                mode="lines",
                line=dict(color="black", dash="dash"),
                name="t at Event Time",
            )
        )

        # Add annotation box if parameters are provided
        if params_list:
            full_text = "<br>".join(params_list)  # Plotly uses <br> for line breaks
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

        # Configure plot layout
        fig.update_layout(
            title_text=title,
            xaxis_title="t (s)",
            yaxis_title=f"{magnitude} (pu)",
            legend=dict(x=0.99, y=0.01, xanchor="right", yanchor="bottom"),
            template="plotly_white",
        )

        # Save output files
        fig.write_html(path.with_suffix(".html"))
