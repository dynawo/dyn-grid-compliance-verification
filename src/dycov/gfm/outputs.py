#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

import configparser
import importlib.metadata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, TextIO

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib import pyplot as plt

_DEFAULT_DISCLAIMER = "Inconsistent damping. Envelopes may be unreliable."
_SECTION_RULE = "=" * 30


def save_results_to_csv(
    path: Path,
    magnitude: str,
    time_array: np.ndarray,
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    extra_envelopes: Optional[dict[str, np.ndarray]] = None,
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
    """
    data = {
        "Time (s)": time_array,
        f"{magnitude} PGU (pu)": pcc_signal,
        f"{magnitude} lower (pu)": lower_envelope,
        f"{magnitude} upper (pu)": upper_envelope,
    }
    for name, signal in (extra_envelopes or {}).items():
        data[f"{magnitude} {name} (pu)"] = signal

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
    """
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
    """
    signals = (pcc_signal, lower_envelope, upper_envelope)
    for i in range(len(pcc_signal) - 1, 0, -1):
        if any(abs(signal[i] - signal[i - 1]) > tolerance for signal in signals):
            return min(i + buffer_points, len(pcc_signal))
    return len(pcc_signal)


@dataclass
class _Window:
    """The part of the signals the figures draw, around the transient."""

    time: np.ndarray
    pcc: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    extra: dict[str, np.ndarray]


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
    show_disclaimer: bool = False,
    disclaimer_message: Optional[str] = None,
    extra_envelopes: Optional[dict[str, np.ndarray]] = None,
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
    show_disclaimer : bool, optional
        Whether to display a warning disclaimer. Defaults to False.
    disclaimer_message : str, optional
        Custom disclaimer text. Defaults to None.
    extra_envelopes : dict[str, np.ndarray], optional
        Additional signals to plot. Defaults to None.
    """
    window = _transient_window(
        time_array, pcc_signal, lower_envelope, upper_envelope, extra_envelopes
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
            _png_disclaimer(disclaimer_message) if show_disclaimer else None,
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
            _html_disclaimer(disclaimer_message) if show_disclaimer else None,
            watermark_text,
        )


def _transient_window(
    time_array: np.ndarray,
    pcc_signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
    extra_envelopes: Optional[dict[str, np.ndarray]],
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
    )


def _watermark_text() -> str:
    try:
        return f"dycov v{importlib.metadata.version('dycov')}"
    except importlib.metadata.PackageNotFoundError:
        return "dycov v(unknown)"


def _png_disclaimer(disclaimer_message: Optional[str]) -> str:
    return "Disclaimer:\n" + (disclaimer_message or _DEFAULT_DISCLAIMER)


def _html_disclaimer(disclaimer_message: Optional[str]) -> str:
    html_msg = (
        disclaimer_message.replace("\n", "<br>") if disclaimer_message else _DEFAULT_DISCLAIMER
    )
    return f"<b>Disclaimer:</b><br>{html_msg}"


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
    disclaimer_text: Optional[str],
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

    if disclaimer_text is not None:
        plt.text(
            0.02,
            0.02,
            disclaimer_text,
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
    disclaimer_text: Optional[str],
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

    if disclaimer_text is not None:
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.02,
            y=0.02,
            text=disclaimer_text,
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
