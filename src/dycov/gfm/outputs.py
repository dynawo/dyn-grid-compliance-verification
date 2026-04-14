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
    """Exports the generated mathematical envelopes and signals into a CSV format.

    If the system operates in hybrid mode and generates extra envelopes,
    they are dynamically appended as subsequent columns in the dataset.

    Parameters
    ----------
    path : Path
        The absolute or relative destination path for the output CSV file.
    magnitude : str
        The physical magnitude being analyzed (e.g., 'P', 'Iq').
    time_array : np.ndarray
        Array containing all time steps used in the simulation.
    pcc_signal : np.ndarray
        The recorded system signal at the Point of Common Coupling.
    lower_envelope : np.ndarray
        The array corresponding to the lower bound of the calculated envelope.
    upper_envelope : np.ndarray
        The array corresponding to the upper bound of the calculated envelope.
    extra_envelopes : dict[str, np.ndarray], optional
        A dictionary containing additional data series, where keys represent
        the series names and values are the corresponding data arrays.
    """
    data = {
        "Time (s)": time_array,
        f"{magnitude} PGU (pu)": pcc_signal,
        f"{magnitude} lower (pu)": lower_envelope,
        f"{magnitude} upper (pu)": upper_envelope,
    }

    # Append extra envelopes if requested (provides detailed output for hybrid mode)
    if extra_envelopes:
        for name, signal in extra_envelopes.items():
            # Format the column name appropriately for the CSV header
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
    """Identifies the ideal index to trim leading stable, non-informative data.

    This function iterates forward from the start of the signals and stops when
    it detects a significant variation exceeding the predefined tolerance threshold.

    Parameters
    ----------
    pcc_signal : np.ndarray
        The recorded system signal array.
    lower_envelope : np.ndarray
        The lower bounded envelope array.
    upper_envelope : np.ndarray
        The upper bounded envelope array.
    tolerance : float, optional
        The absolute difference threshold to trigger a detection. Defaults to 1e-5.
    buffer_points : int, optional
        The number of historical points to preserve prior to the detected change.
        Defaults to 10.

    Returns
    -------
    int
        The integer index representing the recommended starting point for analysis.
    """
    for i in range(len(pcc_signal) - 1):
        pcc_changed = abs(pcc_signal[i + 1] - pcc_signal[i]) > tolerance
        down_changed = abs(lower_envelope[i + 1] - lower_envelope[i]) > tolerance
        up_changed = abs(upper_envelope[i + 1] - upper_envelope[i]) > tolerance

        if pcc_changed or down_changed or up_changed:
            # First significant variation detected. Return index including the safety buffer.
            return max(0, i - buffer_points)

    # Return 0 if no significant change is identified (no trimming applied).
    return 0


def find_end_trim_index(
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    tolerance: float = 1e-5,
    buffer_points: int = 10,
) -> int:
    """Identifies the ideal index to trim trailing stable, non-informative data.

    This function iterates backward from the end of the signals and stops when
    it detects the last point where there is a significant variation.

    Parameters
    ----------
    pcc_signal : np.ndarray
        The recorded system signal array.
    lower_envelope : np.ndarray
        The lower bounded envelope array.
    upper_envelope : np.ndarray
        The upper bounded envelope array.
    tolerance : float, optional
        The absolute difference threshold to trigger a detection. Defaults to 1e-5.
    buffer_points : int, optional
        The number of historical points to preserve after the detected change.
        Defaults to 10.

    Returns
    -------
    int
        The integer index representing the recommended ending point for analysis.
    """
    for i in range(len(pcc_signal) - 1, 0, -1):
        pcc_changed = abs(pcc_signal[i] - pcc_signal[i - 1]) > tolerance
        down_changed = abs(lower_envelope[i] - lower_envelope[i - 1]) > tolerance
        up_changed = abs(upper_envelope[i] - upper_envelope[i - 1]) > tolerance

        if pcc_changed or down_changed or up_changed:
            # Last significant variation detected. Return index including the safety buffer.
            return min(i + buffer_points, len(pcc_signal))

    # Return the original array length if no significant change is identified.
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
    """Renders and exports the simulation results graphically, automatically trimming stable data.

    Generates both an interactive HTML file and a static PNG image depending on the requested format.

    Parameters
    ----------
    path : Path
        The base file path for the output plots (extensions will be appended automatically).
    title : str
        The descriptive title rendered on the plot.
    magnitude : str
        The physical magnitude being graphed (e.g., 'P', 'Iq').
    time_array : np.ndarray
        The complete time array corresponding to the simulation.
    event_time : float
        The absolute time coordinate indicating the start of the event.
    shift_time : float
        An optional temporal shift applied to the event marker line.
    pcc_signal : np.ndarray
        The main calculated signal from the Point of Common Coupling.
    lower_envelope : np.ndarray
        The array corresponding to the lower bound envelope.
    upper_envelope : np.ndarray
        The array corresponding to the upper bound envelope.
    output_format : str
        String specifying the desired output format(s), such as 'png&html'.
    params_list : list, optional
        A list of formatted text strings detailing simulation parameters for the legend.
    show_disclaimer : bool, optional
        If True, renders a warning disclaimer overlay on the plot. Defaults to False.
    disclaimer_message : str | None, optional
        Custom detailed text for the disclaimer overlay.
    extra_envelopes : dict[str, np.ndarray], optional
        Supplementary bounding envelopes to be rendered alongside the main signals.
    """
    # 1. Identify optimal indices to crop uninformative pre- and post-event data
    start_index = find_start_trim_index(pcc_signal, lower_envelope, upper_envelope)
    end_index = find_end_trim_index(pcc_signal, lower_envelope, upper_envelope)

    # 2. Slice arrays utilizing the calculated boundaries
    time_trimmed = time_array[start_index:end_index]
    pcc_trimmed = pcc_signal[start_index:end_index]
    down_trimmed = lower_envelope[start_index:end_index]
    up_trimmed = upper_envelope[start_index:end_index]

    # Process supplementary envelopes if provided
    extra_trimmed = {}
    if extra_envelopes:
        for name, signal in extra_envelopes.items():
            extra_trimmed[name] = signal[start_index:end_index]

    # 3. Format disclaimer overlays based on the output backend requirements
    disclaimer_text_mpl = ""
    disclaimer_text_html = ""
    if show_disclaimer:
        default_msg = "Inconsistent damping. Envelopes may be unreliable."
        # Configure line breaks for Matplotlib rendering
        disclaimer_text_mpl = "Disclaimer:\n" + (disclaimer_message or default_msg)
        # Configure HTML tags for Plotly rendering
        html_msg = disclaimer_message.replace("\n", "<br>") if disclaimer_message else default_msg
        disclaimer_text_html = f"<b>Disclaimer:</b><br>{html_msg}"

    # --- Static Plot Generation via Matplotlib (PNG) ---
    if "png" in output_format:
        plt.figure(figsize=(8, 5))

        # Render supplementary envelopes beneath the main data lines
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

        # Render the primary bounds and PCC signal
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

        # Apply layout adjustments and export
        plt.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize="small")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.xlim(time_trimmed[0], time_trimmed[-1])

        plt.tight_layout()
        plt.savefig(path.with_suffix(".png"), bbox_inches="tight", dpi=300)
        plt.close()

    # --- Interactive Plot Generation via Plotly (HTML) ---
    if "html" in output_format:
        fig = go.Figure()

        # Render the shaded region bound by the main envelopes
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

        # Render supplementary envelopes
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

        # Render primary bounding lines and main signal
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
            margin=dict(r=150),
        )

        fig.write_html(path.with_suffix(".html"))


def save_ini_dump(
    path: Path,
    parameters: Any,
    producer_config: configparser.ConfigParser,
    calculator: Any,
) -> None:
    """Serializes and exports all internal attributes from the simulation entities into a text
    file.

    Parameters
    ----------
    path : Path
        The absolute or relative path (including filename) destination for the dump file.
    parameters : GFMParameters
        The parameter configuration object guiding the simulation.
    producer_config : configparser.ConfigParser
        The parsed producer configuration object representing INI settings.
    calculator : GFMCalculator
        The instantiated calculator object containing current evaluation state.
    """

    def _write_dict(f: Any, title: str, data_dict: dict) -> None:
        """Helper method to format and write a dictionary's contents to an open file.

        Parameters
        ----------
        f : Any
            The open file handler with write permissions.
        title : str
            The header string to prepend to the serialized dictionary block.
        data_dict : dict
            The dictionary payload to format and output.
        """
        f.write(f"\n{'=' * 30}\n")
        f.write(f" {title}\n")
        f.write(f"{'=' * 30}\n")
        for key, value in sorted(data_dict.items()):
            # Isolate standard variables by excluding callable methods
            if not callable(value):
                f.write(f"{key} = {value}\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("GFM SIMULATION DUMP\n")
        f.write("===================\n")

        # 1. Export core validation limits (D, H, system margins, and Epsilon)
        f.write(f"\n{'=' * 30}\n")
        f.write(" Key Validation Values\n")
        f.write(f"{'=' * 30}\n")
        try:
            # Extract internal validation arrays mapped within the calculator instance
            d_vals = getattr(calculator, "_d_vals", None)
            h_vals = getattr(calculator, "_h_vals", None)
            eps_vals = getattr(calculator, "_epsilon_vals", None)

            if d_vals is not None and h_vals is not None:
                # Iterate and format all validation combinations (Nominal + Variations)
                for i in range(len(d_vals)):
                    label = "Nominal" if i == 0 else f"Variation {i}"
                    line = f"[{label}] D = {d_vals[i]:.6f}, H = {h_vals[i]:.6f}"

                    # Append Epsilon constraints if defined in the parameters
                    if eps_vals is not None and i < len(eps_vals):
                        line += f", Epsilon = {eps_vals[i]:.6f}"

                    f.write(line + "\n")
            else:
                f.write("D and H variations data not available in calculator.\n")

        except Exception as e:
            f.write(f"Could not retrieve validation values: {e}\n")

        # 2. Export serialized GFMParameters object state
        if hasattr(parameters, "__dict__"):
            _write_dict(f, "GFMParameters Attributes", parameters.__dict__)

        # 3. Export serialized GFMCalculator object state
        if hasattr(calculator, "__dict__"):
            _write_dict(f, "GFMCalculator Attributes", calculator.__dict__)

        # 4. Reconstruct and export Producer INI Configuration
        f.write(f"\n{'=' * 30}\n")
        f.write(" GFMProducer Configuration (INI)\n")
        f.write(f"{'=' * 30}\n")

        if producer_config:
            for section in producer_config.sections():
                f.write(f"[{section}]\n")
                for key, value in producer_config.items(section):
                    f.write(f"{key} = {value}\n")
                f.write("\n")
