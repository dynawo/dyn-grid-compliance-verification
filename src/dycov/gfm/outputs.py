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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, TextIO

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib import pyplot as plt

from dycov.configuration.cfg import config
from dycov.gfm import constants

# The envelopes of a test: the magnitude they bound, whether they are for EMT simulations, their
# time values with the time and the duration of the event, the response of the ideal voltage
# source with its two bounds, the extra bounds saved for debugging, and the parameters printed on
# the figure
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
    ],
)
_SECTION_RULE = "=" * 30


def save_results_to_csv(
    path: Path,
    magnitude: str,
    time_array: np.ndarray,
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    extra_envelopes: Optional[dict[str, np.ndarray]] = None,
    producer_signal: Optional[np.ndarray] = None,
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
    """
    data = {
        "Time (s)": time_array,
        f"{magnitude} PGU (pu)": pcc_signal,
        f"{magnitude} lower (pu)": lower_envelope,
        f"{magnitude} upper (pu)": upper_envelope,
    }
    for name, signal in (extra_envelopes or {}).items():
        data[f"{magnitude} {name} (pu)"] = signal
    if producer_signal is not None:
        data[f"{magnitude} producer (pu)"] = producer_signal

    pd.DataFrame(data).to_csv(path, index=False, sep=";", float_format="%.3e")


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
        The index buffer_points before the first step where any of the signals changes by more
        than the tolerance, or 0 if none does.

    Raises
    ------
    ValueError
        If the signals differ in length.
    """
    _check_same_length(pcc_signal, lower_envelope, upper_envelope)
    signals = (pcc_signal, lower_envelope, upper_envelope)
    for i in range(len(pcc_signal) - 1):
        if any(abs(signal[i + 1] - signal[i]) > tolerance for signal in signals):
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
        The index buffer_points after the last step where any of the signals changes by more
        than the tolerance, or the length of the signals if none does.

    Raises
    ------
    ValueError
        If the signals differ in length.
    """
    _check_same_length(pcc_signal, lower_envelope, upper_envelope)
    signals = (pcc_signal, lower_envelope, upper_envelope)
    for i in range(len(pcc_signal) - 1, 0, -1):
        if any(abs(signal[i] - signal[i - 1]) > tolerance for signal in signals):
            return min(i + buffer_points, len(pcc_signal))
    return len(pcc_signal)


def _check_same_length(
    pcc_signal: np.ndarray, lower_envelope: np.ndarray, upper_envelope: np.ndarray
) -> None:
    lengths = (len(pcc_signal), len(lower_envelope), len(upper_envelope))
    if len(set(lengths)) > 1:
        raise ValueError(
            "The PCC signal and the lower and upper envelopes must have the same length, not "
            f"{lengths[0]}, {lengths[1]} and {lengths[2]}."
        )


@dataclass
class _Window:
    """The part of the signals the figures draw, around the transient."""

    time: np.ndarray
    pcc: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    extra: dict[str, np.ndarray]
    producer: Optional[np.ndarray]


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
    params_list: Optional[list] = None,
    extra_envelopes: Optional[dict[str, np.ndarray]] = None,
    producer_signal: Optional[np.ndarray] = None,
) -> None:
    """
    Renders and exports simulation results graphically.

    Parameters
    ----------
    path : Path
        Destination path for the plot file; its suffix is replaced by that of each format.
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
    extra_envelopes : dict[str, np.ndarray], optional
        Additional signals to plot. Defaults to None.
    producer_signal : np.ndarray, optional
        Filtered producer curve on the same time values, checked against the envelopes.
        Defaults to None.

    Raises
    ------
    TypeError
        If the output format is not text.
    ValueError
        If the output format names neither png nor html, or the time, the signals and the
        envelopes differ in length.
    """
    _check_plot_options(output_format)
    _check_plot_lengths(
        time_array, pcc_signal, lower_envelope, upper_envelope, extra_envelopes, producer_signal
    )
    window = _transient_window(
        time_array, pcc_signal, lower_envelope, upper_envelope, extra_envelopes, producer_signal
    )
    event_x = event_time + shift_time / 1000
    watermark_text = _watermark_text()

    if "png" in output_format:
        _plot_png(
            path.with_suffix(".png"),
            title,
            magnitude,
            window,
            event_x,
            params_list,
            watermark_text,
        )
    if "html" in output_format:
        _plot_html(
            path.with_suffix(".html"),
            title,
            magnitude,
            window,
            event_x,
            params_list,
            watermark_text,
        )


def _check_plot_options(output_format: str) -> None:
    if not isinstance(output_format, str):
        raise TypeError(
            f"The output format must be text, not of type {type(output_format).__name__}."
        )
    if "png" not in output_format and "html" not in output_format:
        raise ValueError(f"The output format must name png, html or both, not {output_format!r}.")


def _check_plot_lengths(
    time_array: np.ndarray,
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    extra_envelopes: Optional[dict[str, np.ndarray]],
    producer_signal: Optional[np.ndarray],
) -> None:
    lengths = {
        "time": len(time_array),
        "PCC signal": len(pcc_signal),
        "lower envelope": len(lower_envelope),
        "upper envelope": len(upper_envelope),
        **{name: len(signal) for name, signal in (extra_envelopes or {}).items()},
        **({"producer signal": len(producer_signal)} if producer_signal is not None else {}),
    }
    if len(set(lengths.values())) > 1:
        raise ValueError(
            "The time, the PCC signal and the envelopes must have the same length, not "
            + ", ".join(f"{length} ({name})" for name, length in lengths.items())
            + "."
        )


def _transient_window(
    time_array: np.ndarray,
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    extra_envelopes: Optional[dict[str, np.ndarray]],
    producer_signal: Optional[np.ndarray],
) -> _Window:
    start_index = find_start_trim_index(pcc_signal, lower_envelope, upper_envelope)
    end_index = find_end_trim_index(pcc_signal, lower_envelope, upper_envelope)
    window = slice(start_index, end_index)
    return _Window(
        time=time_array[window],
        pcc=pcc_signal[window],
        lower=lower_envelope[window],
        upper=upper_envelope[window],
        extra={name: signal[window] for name, signal in (extra_envelopes or {}).items()},
        producer=producer_signal[window] if producer_signal is not None else None,
    )


def _watermark_text() -> str:
    try:
        return f"dycov v{importlib.metadata.version('dycov')}"
    except importlib.metadata.PackageNotFoundError:
        return "dycov v(unknown)"


def _extra_envelope_color(name: str) -> str:
    return "purple" if "overdamped" in name else "orange"


def _extra_envelope_label(name: str) -> str:
    return name.replace("_", " ").title()


def _plot_png(
    path: Path,
    title: str,
    magnitude: str,
    window: _Window,
    event_x: float,
    params_list: Optional[list],
    watermark_text: str,
) -> None:
    plt.figure(figsize=(8, 5))

    for name, signal in window.extra.items():
        plt.plot(
            window.time,
            signal,
            linestyle=":",
            linewidth=1,
            color=_extra_envelope_color(name),
            alpha=0.7,
            label=_extra_envelope_label(name),
        )

    plt.plot(window.time, window.pcc, label=f"{magnitude} at PGU", linewidth=3)
    plt.plot(window.time, window.lower, label=f"{magnitude} envelopes", linewidth=2, color="red")
    plt.plot(window.time, window.upper, linewidth=2, color="red")
    if window.producer is not None:
        plt.plot(
            window.time, window.producer, label=f"{magnitude} producer", linewidth=2, color="green"
        )

    plt.xlabel("Time (s)")
    plt.ylabel(f"{magnitude} (pu)")
    plt.title(title)
    plt.axvline(x=event_x, color="black", linestyle="--", label="Event Time")

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
    plt.xlim(window.time[0], window.time[-1])
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight", dpi=300)
    plt.close()


def _plot_html(
    path: Path,
    title: str,
    magnitude: str,
    window: _Window,
    event_x: float,
    params_list: Optional[list],
    watermark_text: str,
) -> None:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([window.time, window.time[::-1]]),
            y=np.concatenate([window.upper, window.lower[::-1]]),
            fill="toself",
            fillcolor="rgba(255, 0, 0, 0.2)",
            line=dict(color="rgba(255, 255, 255, 0)"),
            hoverinfo="none",
            showlegend=False,
        )
    )

    for name, signal in window.extra.items():
        fig.add_trace(
            go.Scatter(
                x=window.time,
                y=signal,
                mode="lines",
                line=dict(color=_extra_envelope_color(name), width=1, dash="dot"),
                name=_extra_envelope_label(name),
                opacity=0.7,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=window.time,
            y=window.upper,
            mode="lines",
            line=dict(color="red", width=2),
            name=f"{magnitude} envelopes",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=window.time,
            y=window.lower,
            mode="lines",
            line=dict(color="red", width=2),
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=window.time,
            y=window.pcc,
            mode="lines",
            line=dict(color="blue", width=3),
            name=f"{magnitude} PGU",
        )
    )
    if window.producer is not None:
        fig.add_trace(
            go.Scatter(
                x=window.time,
                y=window.producer,
                mode="lines",
                line=dict(color="green", width=2),
                name=f"{magnitude} producer",
            )
        )

    fig.add_vline(
        x=event_x,
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
    fig.write_html(path)


def save_ini_dump(
    path: Path, parameters: Any, producer_config: configparser.ConfigParser, calculator: Any
) -> None:
    """
    Writes the state of a calculation to a text file, for diagnosis.

    It holds the D, H and damping ratio of each variation the calculator ran, the attributes
    of the parameters and of the calculator, and the producer's configuration.

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
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write("GFM SIMULATION DUMP\n===================\n\n")
        f.write(_section_header("Key Validation Values"))
        _write_validation_values(f, calculator)

        if hasattr(parameters, "__dict__"):
            _write_attributes(f, "GFMParameters Attributes", parameters.__dict__)
        if hasattr(calculator, "__dict__"):
            _write_attributes(f, "GFMCalculator Attributes", calculator.__dict__)

        f.write("\n" + _section_header("GFMProducer Configuration (INI)"))
        if producer_config:
            for section in producer_config.sections():
                f.write(f"[{section}]\n")
                for key, value in producer_config.items(section):
                    f.write(f"{key} = {value}\n")
                f.write("\n")


def _section_header(title: str) -> str:
    return f"{_SECTION_RULE}\n {title}\n{_SECTION_RULE}\n"


def _write_validation_values(f: TextIO, calculator: Any) -> None:
    try:
        d_vals = getattr(calculator, "_d_vals", None)
        h_vals = getattr(calculator, "_h_vals", None)
        eps_vals = getattr(calculator, "_epsilon_vals", None)

        if d_vals is None or h_vals is None:
            f.write("D and H variations data not available in calculator.\n")
            return
        for i in range(len(d_vals)):
            label = "Nominal" if i == 0 else f"Variation {i}"
            line = f"[{label}] D = {d_vals[i]:.6f}, H = {h_vals[i]:.6f}"
            if eps_vals is not None and i < len(eps_vals):
                line += f", Epsilon = {eps_vals[i]:.6f}"
            f.write(line + "\n")
    except Exception as e:
        f.write(f"Could not retrieve validation values: {e}\n")


def _write_attributes(f: TextIO, title: str, attributes: dict) -> None:
    f.write("\n" + _section_header(title))
    for key, value in sorted(attributes.items()):
        if not callable(value):
            f.write(f"{key} = {value}\n")


def save_results(path: Path, envelopes: Envelopes, curves_check: Any = None) -> None:
    """
    Exports what describes the envelopes of a test to a JSON file, with the compliance of its
    producer curves when they are checked. A performance verification given the envelopes reads
    the description back.

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
            "damping_event_delay": config.get_float("GFM", "damping_event_delay", 0.005),
            "damping_time_step": config.get_float("GFM", "damping_time_step", 0.005),
            "damping_pencil_order": config.get_int("GFM", "damping_pencil_order", 6),
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
    )
