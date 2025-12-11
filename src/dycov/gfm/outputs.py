#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import configparser
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
    """
    Save the calculated results to a CSV file.

    If extra_envelopes are provided (for hybrid mode), they are added as new columns.

    Parameters
    ----------
    path : Path
        The file path where the CSV file will be saved.
    magnitude : str
        Name of the magnitude (e.g., "P", "Iq").
    time_array : np.ndarray
        The time array corresponding to the signals.
    pcc_signal : np.ndarray
        The calculated signal at the point of common coupling.
    lower_envelope : np.ndarray
        The lower envelope of the signal.
    upper_envelope : np.ndarray
        The upper envelope of the signal.

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

    Parameters
    ----------
    pcc_signal : np.ndarray
        The main signal array.
    lower_envelope : np.ndarray
        The lower envelope signal array.
    upper_envelope : np.ndarray
        The upper envelope signal array.
    tolerance : float
        The minimum change between consecutive points to be considered a variation.
    buffer_points : int
        Number of data points to keep before the first detected change.

    Returns
    -------
    int
        The index from which the data should be kept.
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

    Parameters
    ----------
    pcc_signal : np.ndarray
        The main signal array.
    lower_envelope : np.ndarray
        The lower envelope signal array.
    upper_envelope : np.ndarray
        The upper envelope signal array.
    tolerance : float
        The minimum change between consecutive points to be considered a variation.
    buffer_points : int
        Number of data points to keep after the last detected change.

    Returns
    -------
    int
        The index up to which the data should be kept.
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
    disclaimer_message: str = None,
    extra_envelopes: dict[str, np.ndarray] = None,
) -> None:
    """
    Plot the results, trimming stable data at the start and end.

    Saves an interactive HTML file and a static PNG image.

    Parameters
    ----------
    path : Path
        The base file path for the output plots (extension will be added).
    title : str
        The title for the plot.
    magnitude : str
        The name of the magnitude being plotted (e.g., "P", "Iq").
    time_array : np.ndarray
        The full time array for the simulation.
    event_time : float
        The absolute time of the event.
    shift_time : float
        A time shift to apply to the event marker, if needed.
    pcc_signal : np.ndarray
        The main signal from the PCC.
    lower_envelope : np.ndarray
        The lower envelope signal.
    upper_envelope : np.ndarray
        The upper envelope signal.
    output_format : str
        The desired output format(s), e.g., "png&html".
    params_list : list, optional
        A list of formatted strings containing simulation parameters to display.
    show_disclaimer : bool
        If True, adds a warning disclaimer to the plot.
    disclaimer_message : str | None
        The detailed message for the disclaimer.
    """
    # 1. Find the optimal indices to trim the data.
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
        # Format for Matplotlib (uses \n)
        disclaimer_text_mpl = "Disclaimer:\n" + (disclaimer_message or default_msg)
        # Format for Plotly (uses <br>)
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


def save_ini_dump(
    path: Path,
    parameters: Any,
    producer_config: configparser.ConfigParser,
    calculator: Any,
) -> None:
    """
    Dumps all attributes from Parameters, Producer Config, and Calculator
    to a text file.

    Parameters
    ----------
    path : Path
        The full path (including filename) where the text file will be saved.
    parameters : GFMParameters
        The parameters object containing simulation settings.
    producer_config : configparser.ConfigParser
        The configuration object from the GFMProducer.
    calculator : GFMCalculator
        The calculator instance used for the simulation.
    """

    def _write_dict(f, title: str, data_dict: dict):
        f.write(f"\n{'=' * 30}\n")
        f.write(f" {title}\n")
        f.write(f"{'=' * 30}\n")
        for key, value in sorted(data_dict.items()):
            # Filter out private attributes that might be irrelevant or callables
            if not callable(value):
                f.write(f"{key} = {value}\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("GFM SIMULATION DUMP\n")
        f.write("===================\n")

        # 1. Key Validation Values (D, H, variations, and Epsilon)
        f.write(f"\n{'=' * 30}\n")
        f.write(" Key Validation Values\n")
        f.write(f"{'=' * 30}\n")
        try:
            # Retrieve the list of used values stored in the calculator
            d_vals = getattr(calculator, "_d_vals", None)
            h_vals = getattr(calculator, "_h_vals", None)
            eps_vals = getattr(calculator, "_epsilon_vals", None)

            if d_vals is not None and h_vals is not None:
                # Iterate over all combinations used (Nominal + Variations)
                for i in range(len(d_vals)):
                    # Determine label (0=Nominal, others=Variations)
                    label = "Nominal" if i == 0 else f"Variation {i}"

                    line = f"[{label}] D = {d_vals[i]:.6f}, H = {h_vals[i]:.6f}"

                    # Add Epsilon if available
                    if eps_vals is not None and i < len(eps_vals):
                        line += f", Epsilon = {eps_vals[i]:.6f}"

                    f.write(line + "\n")
            else:
                f.write("D and H variations data not available in calculator.\n")

        except Exception as e:
            f.write(f"Could not retrieve validation values: {e}\n")

        # 2. Dump GFMParameters
        # We access the __dict__ to get all instance attributes
        if hasattr(parameters, "__dict__"):
            _write_dict(f, "GFMParameters Attributes", parameters.__dict__)

        # 3. Dump GFMCalculator
        if hasattr(calculator, "__dict__"):
            _write_dict(f, "GFMCalculator Attributes", calculator.__dict__)

        # 4. Dump Producer Configuration (INI structure)
        f.write(f"\n{'=' * 30}\n")
        f.write(" GFMProducer Configuration (INI)\n")
        f.write(f"{'=' * 30}\n")

        if producer_config:
            for section in producer_config.sections():
                f.write(f"[{section}]\n")
                for key, value in producer_config.items(section):
                    f.write(f"{key} = {value}\n")
                f.write("\n")
