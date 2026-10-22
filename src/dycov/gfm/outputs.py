#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

import configparser
import importlib.metadata
import json
from collections import namedtuple
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib import pyplot as plt

from dycov.configuration.cfg import config
from dycov.gfm import constants

# The envelopes of a test: the magnitude they bound, whether they are for EMT simulations, their
# time values with the time and the duration of the event, the response of the ideal voltage
# source with its two bounds, the extra bounds saved for debugging, the parameters printed on the
# figure, and the warning on their consistency, None when there is none
Envelopes = namedtuple(
    "Envelopes",
    [
        "magnitude",
        "emt",
        "time",
        "event_time",
        "event_duration",
        "response",
        "lower",
        "upper",
        "extra",
        "parameters",
        "disclaimer",
    ],
)


def save_results_to_csv(
    path: Path,
    magnitude: str,
    time_array: np.ndarray,
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    extra_envelopes: dict[str, np.ndarray] = None,
    producer_signal: np.ndarray = None,
) -> None:
    """
    Exports envelopes and signals to a CSV file.

    Parameters
    ----------
    path : Path
        Destination path for the CSV file.
    magnitude : str
        Name of the magnitude being recorded.
    time_array : np.ndarray
        Array of time steps.
    pcc_signal : np.ndarray
        Array of Point of Common Coupling signal values.
    lower_envelope : np.ndarray
        Array of lower envelope values.
    upper_envelope : np.ndarray
        Array of upper envelope values.
    extra_envelopes : dict[str, np.ndarray], optional
        Additional envelopes to save. Defaults to None.
    producer_signal : np.ndarray, optional
        Filtered producer curve on the same time values. Defaults to None.

    Returns
    -------
    None
    """
    # Map core signals to their respective CSV column headers
    data = {
        "Time (s)": time_array,
        f"{magnitude} PGU (pu)": pcc_signal,
        f"{magnitude} lower (pu)": lower_envelope,
        f"{magnitude} upper (pu)": upper_envelope,
    }

    if extra_envelopes:
        for name, signal in extra_envelopes.items():
            data[f"{magnitude} {name} (pu)"] = signal
    if producer_signal is not None:
        data[f"{magnitude} producer (pu)"] = producer_signal

    df = pd.DataFrame(data)
    # Use scientific notation to preserve precision for sensitive envelope bounds
    df.to_csv(path, index=False, sep=";", float_format="%.3e")


def find_start_trim_index(
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    tolerance: float = 1e-5,
    buffer_points: int = 10,
) -> int:
    """
    Finds the starting index to trim leading stable data.

    Parameters
    ----------
    pcc_signal : np.ndarray
        The main signal array.
    lower_envelope : np.ndarray
        The lower envelope array.
    upper_envelope : np.ndarray
        The upper envelope array.
    tolerance : float, optional
        Variation threshold to detect changes. Defaults to 1e-5.
    buffer_points : int, optional
        Number of safety points to keep before the change. Defaults to 10.

    Returns
    -------
    int
        The calculated starting index.
    """
    # Scan forward to bypass initial flatlines until a significant variation is detected
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
    """
    Finds the ending index to trim trailing stable data.

    Parameters
    ----------
    pcc_signal : np.ndarray
        The main signal array.
    lower_envelope : np.ndarray
        The lower envelope array.
    upper_envelope : np.ndarray
        The upper envelope array.
    tolerance : float, optional
        Variation threshold to detect changes. Defaults to 1e-5.
    buffer_points : int, optional
        Number of safety points to keep after the change. Defaults to 10.

    Returns
    -------
    int
        The calculated ending index.
    """
    # Scan backward from the end to strip trailing stable data
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
    producer_signal: np.ndarray = None,
) -> None:
    """
    Renders and exports simulation results graphically.

    Parameters
    ----------
    path : Path
        Destination path for the plot file.
    title : str
        Title of the plot.
    magnitude : str
        The physical magnitude being plotted.
    time_array : np.ndarray
        The time steps array.
    event_time : float
        The timestamp of the main simulation event.
    shift_time : float
        Time shift in milliseconds to adjust the vertical event line.
    pcc_signal : np.ndarray
        Main signal data to plot.
    lower_envelope : np.ndarray
        Lower bounds data.
    upper_envelope : np.ndarray
        Upper bounds data.
    output_format : str
        The desired output formats (e.g., 'png&html').
    params_list : list, optional
        List of parameter strings to display on the plot. Defaults to None.
    show_disclaimer : bool, optional
        Whether to display a warning disclaimer. Defaults to False.
    disclaimer_message : str, optional
        Custom disclaimer text. Defaults to None.
    extra_envelopes : dict[str, np.ndarray], optional
        Additional signals to plot. Defaults to None.
    producer_signal : np.ndarray, optional
        Filtered producer curve on the same time values, checked against the envelopes.
        Defaults to None.

    Returns
    -------
    None
    """
    start_index = find_start_trim_index(pcc_signal, lower_envelope, upper_envelope)
    end_index = find_end_trim_index(pcc_signal, lower_envelope, upper_envelope)

    # Slice all arrays to focus only on the active transient event window
    time_trimmed = time_array[start_index:end_index]
    pcc_trimmed = pcc_signal[start_index:end_index]
    down_trimmed = lower_envelope[start_index:end_index]
    up_trimmed = upper_envelope[start_index:end_index]

    extra_trimmed = {}
    if extra_envelopes:
        for name, signal in extra_envelopes.items():
            extra_trimmed[name] = signal[start_index:end_index]
    producer_trimmed = (
        producer_signal[start_index:end_index] if producer_signal is not None else None
    )

    disclaimer_text_mpl = ""
    disclaimer_text_html = ""
    if show_disclaimer:
        default_msg = "Inconsistent damping. Envelopes may be unreliable."
        disclaimer_text_mpl = "Disclaimer:\n" + (disclaimer_message or default_msg)
        html_msg = disclaimer_message.replace("\n", "<br>") if disclaimer_message else default_msg
        disclaimer_text_html = f"<b>Disclaimer:</b><br>{html_msg}"

    # Attempt to watermark plots with the currently installed package version
    try:
        software_version = importlib.metadata.version("dycov")
        watermark_text = f"dycov v{software_version}"
    except importlib.metadata.PackageNotFoundError:
        watermark_text = "dycov v(unknown)"

    if "png" in output_format:
        plt.figure(figsize=(8, 5))

        if extra_trimmed:
            colors = {"overdamped": "purple", "underdamped": "orange"}
            for name, signal in extra_trimmed.items():
                style_color = (
                    colors.get("overdamped")
                    if "overdamped" in name
                    else colors.get("underdamped", "gray")
                )
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
        if producer_trimmed is not None:
            plt.plot(
                time_trimmed,
                producer_trimmed,
                label=f"{magnitude} producer",
                linewidth=2,
                color="green",
            )

        plt.xlabel("Time (s)")
        plt.ylabel(f"{magnitude} (pu)")
        plt.title(title)

        # Shift event time from ms to seconds for correct vertical line placement
        plt.axvline(
            x=event_time + shift_time / 1000, color="black", linestyle="--", label="Event Time"
        )

        if params_list:
            plt.text(
                0.98,
                0.98,
                "\n".join(params_list),
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

    if "html" in output_format:
        fig = go.Figure()

        # Create a shaded area between the upper and lower envelopes
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
                style_color = (
                    colors.get("overdamped")
                    if "overdamped" in name
                    else colors.get("underdamped", "gray")
                )
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
        if producer_trimmed is not None:
            fig.add_trace(
                go.Scatter(
                    x=time_trimmed,
                    y=producer_trimmed,
                    mode="lines",
                    line=dict(color="green", width=2),
                    name=f"{magnitude} producer",
                )
            )

        fig.add_vline(
            x=event_time + shift_time / 1000,
            line_width=2,
            line_dash="dash",
            line_color="black",
            annotation_text="Event Time",
            annotation_position="top right",
        )

        if params_list:
            fig.add_annotation(
                xref="paper",
                yref="paper",
                x=0.98,
                y=0.98,
                text="<br>".join(params_list),
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
    path: Path, parameters: Any, producer_config: configparser.ConfigParser, calculator: Any
) -> None:
    """
    Serializes simulation entity attributes to a text file for debugging.

    Parameters
    ----------
    path : Path
        Destination path for the text dump file.
    parameters : Any
        The simulation parameters object.
    producer_config : configparser.ConfigParser
        The parsed INI configuration.
    calculator : Any
        The instantiated calculator object.

    Returns
    -------
    None
    """

    def _write_dict(f: Any, title: str, data_dict: dict) -> None:
        f.write(f"\n{'=' * 30}\n {title}\n{'=' * 30}\n")
        for key, value in sorted(data_dict.items()):
            # Filter out callable methods to serialize only attributes/properties
            if not callable(value):
                f.write(f"{key} = {value}\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write(
            "GFM SIMULATION DUMP\n"
            "===================\n\n"
            f"{'=' * 30}\n"
            " Key Validation Values\n"
            f"{'=' * 30}\n"
        )

        # Extract internal validation arrays safely across calculator instances
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

        f.write(f"\n{'=' * 30}\n GFMProducer Configuration (INI)\n{'=' * 30}\n")
        if producer_config:
            for section in producer_config.sections():
                f.write(f"[{section}]\n")
                for key, value in producer_config.items(section):
                    f.write(f"{key} = {value}\n")
                f.write("\n")


def save_results(path: Path, envelopes: Envelopes, curves_check: Any = None) -> None:
    """
    Exports what describes the envelopes of a test to a JSON file, with the compliance of its
    producer curves when they are checked. A model validation given the envelopes reads the
    description back.

    Parameters
    ----------
    path : Path
        Destination path for the JSON file.
    envelopes : Envelopes
        The envelopes of the test.
    curves_check : Any, optional
        The result of checking the producer curves against the envelopes and the damping
        criterion. Defaults to None, when the producer curves are not checked.

    Returns
    -------
    None
    """
    results = {
        "magnitude": envelopes.magnitude,
        "emt": envelopes.emt,
        "event_duration": envelopes.event_duration,
        "parameters": envelopes.parameters,
        "disclaimer": envelopes.disclaimer,
    }
    if curves_check is not None:
        results |= {
            "compliance": curves_check.compliance.to_str(),
            "cutoff": config.get_float("GFM", "cutoff", 30.0),
            "envelope_tolerance": config.get_float("GFM", "envelope_tolerance", 0.005),
            "envelope": curves_check.envelope._asdict() if curves_check.envelope else None,
            "thr_damping_ratio": config.get_float("GFM", "thr_damping_ratio", 0.40),
            "damping_band": [
                config.get_float("GFM", "damping_f_min", 0.1),
                config.get_float("GFM", "damping_f_max", 10.0),
            ],
            "damping_min_amplitude": config.get_float("GFM", "damping_min_amplitude", 0.001),
            "modes": [mode._asdict() for mode in curves_check.modes],
        }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)


def read_envelopes(directory: Path, title: str) -> Optional[Envelopes]:
    """
    Reads back the envelopes of a test from the directory where they were written.

    Parameters
    ----------
    directory : Path
        Directory of the test, holding the CSV file of its envelopes and their description.
    title : str
        The name of the test, which names its CSV file.

    Returns
    -------
    Optional[Envelopes]
        The envelopes of the test, or None when the directory lacks either file.

    Raises
    ------
    ValueError
        If either file cannot be parsed.
    KeyError
        If either file lacks what describes the envelopes.
    """
    csv_path = directory / f"{title}.csv"
    results_path = directory / "results.json"
    if not (csv_path.is_file() and results_path.is_file()):
        return None

    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)
    magnitude = results["magnitude"]
    data = pd.read_csv(csv_path, sep=";")
    return Envelopes(
        magnitude=magnitude,
        emt=results["emt"],
        time=data["Time (s)"].to_numpy(),
        event_time=constants.SIMULATION_EVENT_TIME,
        event_duration=results["event_duration"],
        response=data[f"{magnitude} PGU (pu)"].to_numpy(),
        lower=data[f"{magnitude} lower (pu)"].to_numpy(),
        upper=data[f"{magnitude} upper (pu)"].to_numpy(),
        extra=None,
        parameters=results["parameters"],
        disclaimer=results["disclaimer"],
    )
