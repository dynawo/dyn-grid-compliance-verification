#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import pandas as pd

from dycov.configuration.cfg import config
from dycov.report.curve_classification import get_measurement_type, is_controlled_magnitude
from dycov.report.figure_renderer import FigureRenderer
from dycov.report.types import (
    DynamicBand,
    EventMarker,
    FigureDescription,
    FinalValueBand,
    FrequencyBand,
    ToleranceBand,
    band_limits,
)

_COLOR_MXE = "#9acd83"
_COLOR_REACTION = "#bee7fa"
_COLOR_SETTLE_RECT = "#d7f7e0"
_COLOR_SETTLE_LINE = "#f7d7f6"
_COLOR_SETTLE_POINT = "#fcb1fa"
_COLOR_SETTLE_LABEL = "#ff82fc"
_COLOR_EXCLUSION = "#e8e8e8"
_COLOR_REFERENCE = "#dd8452"
_COLOR_IMAX_REAC = "#8172b3"
_COLOR_EVENT_MARKER = "#cccccc"


def draw_tolerance_band(
    renderer: FigureRenderer,
    band: ToleranceBand,
    last_val: float,
    results: dict,
) -> None:
    """Draw tolerance bands on the figure based on the type of band and results.

    Parameters
    ----------
    renderer: FigureRenderer
        The figure renderer to use for drawing.
    band: ToleranceBand
        The tolerance band to draw (FinalValueBand, FrequencyBand, or DynamicBand).
    last_val: float
        The last value of the curve, used for FinalValueBand calculations.
    results: dict
        The results dictionary containing any necessary values for band calculations
        (e.g., targets).
    """
    if isinstance(band, FinalValueBand):
        upper, lower = band_limits(last_val, band.upper, band.lower)
        if upper is not None:
            renderer.add_hline(y=upper, color=band.color)
        if lower is not None:
            renderer.add_hline(y=lower, color=band.color)
        return

    for target in results.get("reactive_current_target", {}).values():
        upper, lower = band_limits(target, band.upper, band.lower)
        if upper is not None:
            renderer.add_hline(y=upper, color=_COLOR_IMAX_REAC)
        if lower is not None:
            renderer.add_hline(y=lower, color=_COLOR_IMAX_REAC)


def draw_frequency_band(
    renderer: FigureRenderer,
    band: FrequencyBand,
    ymin: float,
    ymax: float,
) -> tuple[float, float]:
    """Draw frequency deviation bands on the figure.

    Parameters
    ----------
    renderer: FigureRenderer
        The figure renderer to use for drawing.
    band: FrequencyBand
        The frequency band to draw, with upper and lower deviation values in Hz.
    ymin: float
        The current minimum y-axis limit, used to adjust the limit if the band extends beyond it.
    ymax: float
        The current maximum y-axis limit, used to adjust the limit if the band extends beyond it.

    Returns
    -------
    tuple
        Updated ymin and ymax values after considering the frequency band limits.
    """
    f_nom = config.get_float("Global", "f_nom", 50.0)
    margin = band.upper * 0.5 if band.upper is not None else 0.0
    color = "#c44e52" if band.upper and band.upper >= 1.0 else "#55a868"

    if band.upper is not None:
        y_upper = (f_nom + band.upper) / f_nom
        renderer.add_hline(y=y_upper, color=color)
        if ymax and ymax < y_upper + margin / f_nom:
            ymax = y_upper + margin / f_nom

    if band.lower is not None:
        y_lower = (f_nom - band.lower) / f_nom
        renderer.add_hline(y=y_lower, color=color)
        if ymin and ymin > y_lower - margin / f_nom:
            ymin = y_lower - margin / f_nom

    return ymin, ymax


def draw_dynamic_band(
    renderer: FigureRenderer,
    band: DynamicBand,
    time: list,
    results: dict,
) -> None:
    """Draw dynamic tolerance bands on the figure based on an external reference curve.

    Parameters
    ----------
    renderer: FigureRenderer
        The figure renderer to use for drawing.
    band: DynamicBand
        The dynamic band to draw, with upper and lower percentage values relative to the reference
        curve.
    time: list
        The time values corresponding to the reference curve points.
    results: dict
        The results dictionary containing the reference curve data under the key specified by
        band.source_key.
    """
    percent = band.upper / 100.0 if band.upper is not None else 0.0
    for crv in results.get(band.source_key, []):
        line_max = []
        line_min = []
        for val in crv:
            delta = percent if val <= 1 else abs(percent * val)
            line_max.append(val + delta)
            line_min.append(val - delta)
        renderer.add_curve(x=time, y=line_max, color="#c44e52", style="--")
        renderer.add_curve(x=time, y=line_min, color="#c44e52", style="--")


def draw_event_markers(
    renderer: FigureRenderer,
    markers: list[EventMarker],
    results: dict,
) -> None:
    """Draw vertical lines on the figure at specific event times based on the provided markers and
    results.

    Parameters
    ----------
    renderer: FigureRenderer
        The figure renderer to use for drawing.
    markers: list[EventMarker]
        A list of event markers, each containing a source_key to look up the event time in results.
    results: dict
        The results dictionary containing event times under the keys specified by the markers'
        source_key.
    """
    for marker in markers:
        val = results.get(marker.source_key)
        if val is not None:
            renderer.add_vline(
                x=val + results.get("sim_t_event_start", 0.0),
                color=_COLOR_EVENT_MARKER,
            )


def draw_additional_curves(
    renderer: FigureRenderer,
    figure_description: FigureDescription,
    time: list,
    last_val: float,
    results: dict,
    ymin: float,
    ymax: float,
) -> tuple[float, float]:
    """Draw additional curves and bands on the figure based on the figure description and results.

    This includes tolerance bands, frequency deviation bands, dynamic bands, and event markers.

    Parameters
    ----------
    renderer: FigureRenderer
        The figure renderer to use for drawing.
    figure_description: FigureDescription
        The description of the figure, including any bands and markers to draw.
    time: list
        The time values corresponding to the curves.
    last_val: float
        The last value of the main curve, used for FinalValueBand calculations.
    results: dict
        The results dictionary containing any necessary values for band calculations and event
        times.
    ymin: float
        The current minimum y-axis limit, used to adjust the limit if bands extend beyond it.
    ymax: float
        The current maximum y-axis limit, used to adjust the limit if bands extend beyond it.

    Returns
    -------
    tuple
        Updated ymin and ymax values after considering the drawn bands.
    """
    if figure_description.tolerance_band is not None:
        draw_tolerance_band(renderer, figure_description.tolerance_band, last_val, results)
    if figure_description.frequency_band is not None:
        ymin, ymax = draw_frequency_band(renderer, figure_description.frequency_band, ymin, ymax)
    if figure_description.dynamic_band is not None:
        draw_dynamic_band(renderer, figure_description.dynamic_band, time, results)
    draw_event_markers(renderer, figure_description.event_markers, results)

    return ymin, ymax


def draw_exclusion_windows(renderer: FigureRenderer, results: dict) -> None:
    """Draw exclusion windows on the figure based on the results.

    Parameters
    ----------
    renderer: FigureRenderer
        The figure renderer to use for drawing.
    results: dict
        The results dictionary containing the start and end times of exclusion windows under the
        keys "event_exclusion_window_start", "event_exclusion_window_end",
        "clear_exclusion_window_start", and "clear_exclusion_window_end".
    """
    if "event_exclusion_window_start" in results:
        renderer.add_vrect(
            x0=results["event_exclusion_window_start"],
            x1=results["event_exclusion_window_end"],
            color=_COLOR_EXCLUSION,
        )
    if "clear_exclusion_window_start" in results:
        renderer.add_vrect(
            x0=results["clear_exclusion_window_start"],
            x1=results["clear_exclusion_window_end"],
            color=_COLOR_EXCLUSION,
        )


def draw_response_characteristics(
    renderer: FigureRenderer,
    curve_name: str,
    results: dict,
) -> None:
    """Draw response characteristics (reaction time, rise time, settling time) on the figure based
    on the results.

    Parameters
    ----------
    renderer: FigureRenderer
        The figure renderer to use for drawing.
    curve_name: str
        The name of the curve for which to draw the response characteristics.
    results: dict
        The results dictionary containing the calculated response characteristics under the keys
        "calc_reaction_time", "calc_reaction_target", "calc_rise_time", "calc_rise_target",
        "calc_settling_time", "calc_ss_value", and "calc_settling_tube".
    """
    if "calc_reaction_target" in results and curve_name in results["calc_reaction_target"]:
        treaction = results["calc_reaction_time"] + results["sim_t_event_start"]
        target = results["calc_reaction_target"][curve_name]
        renderer.add_hline(y=target, color=_COLOR_REACTION, style="-", linewidth=0.2)
        renderer.add_vline(x=treaction, color=_COLOR_SETTLE_LINE, style="-", linewidth=0.2)

    if "calc_rise_target" in results and curve_name in results["calc_rise_target"]:
        trise = results["calc_rise_time"] + results["sim_t_event_start"]
        target = results["calc_rise_target"][curve_name]
        renderer.add_hline(y=target, color=_COLOR_REACTION, style="-", linewidth=0.2)
        renderer.add_vline(x=trise, color=_COLOR_SETTLE_LINE, style="-", linewidth=0.2)
        renderer.add_scatter(x=trise, y=target, color=_COLOR_SETTLE_POINT, name="rise time")
        offset_y = 5.0
        if results["calc_rise_target"][curve_name] > results["calc_reaction_target"][curve_name]:
            offset_y = -10.0
        renderer.add_annotation(
            text=f"{trise:.4f}s",
            x=trise,
            y=target,
            color=_COLOR_SETTLE_LABEL,
            offset_y=offset_y,
        )

    if "calc_settling_tube" in results and curve_name in results["calc_settling_tube"]:
        tsettling = results["calc_settling_time"] + results["sim_t_event_start"]
        ss_value = results["calc_ss_value"]
        tube = results["calc_settling_tube"][curve_name]
        renderer.add_hrect(y0=tube[0], y1=tube[1], color=_COLOR_SETTLE_RECT)
        renderer.add_vline(x=tsettling, color=_COLOR_SETTLE_LINE, style="-", linewidth=0.2)
        renderer.add_scatter(
            x=tsettling, y=ss_value, color=_COLOR_SETTLE_POINT, name="settling time"
        )
        offset_y = 5.0
        if "calc_rise_target" in results and (
            results["calc_rise_target"][curve_name] > results["calc_reaction_target"][curve_name]
        ):
            offset_y = -10.0
        renderer.add_annotation(
            text=f"{tsettling:.4f}s",
            x=tsettling,
            y=ss_value,
            color=_COLOR_SETTLE_LABEL,
            offset_y=offset_y,
        )


def _build_mxe_text(
    curve_name: str,
    measurement_type: str,
    results: dict,
    renderer: FigureRenderer,
) -> str:
    before_mxe = None
    during_mxe = None
    after_mxe = None

    if "before_mxe_" + measurement_type + "_position" in results:
        before_mxe = results["before_mxe_" + measurement_type + "_value"]
        renderer.add_vline(
            x=results["before_mxe_" + measurement_type + "_position"][0],
            color=_COLOR_MXE,
            style="-",
            linewidth=0.2,
        )
    if "during_mxe_" + measurement_type + "_position" in results:
        during_mxe = results["during_mxe_" + measurement_type + "_value"]
        renderer.add_vline(
            x=results["during_mxe_" + measurement_type + "_position"][0],
            color=_COLOR_MXE,
            style="-",
            linewidth=0.2,
        )
    if "after_mxe_" + measurement_type + "_position" in results:
        after_mxe = results["after_mxe_" + measurement_type + "_value"]
        renderer.add_vline(
            x=results["after_mxe_" + measurement_type + "_position"][0],
            color=_COLOR_MXE,
            style="-",
            linewidth=0.2,
        )

    text = ""
    if before_mxe is not None:
        text += f"Before: {before_mxe:.3f}\n"
    if during_mxe is not None:
        text += f"During: {during_mxe:.3f}\n"
    if after_mxe is not None:
        text += f"After: {after_mxe:.3f}\n"
    return text


def draw_mxe(
    renderer: FigureRenderer,
    curve_name: str,
    results: dict,
) -> None:
    """Draw MXE (Maximum Excursion) annotations on the figure based on the results.

    Parameters
    ----------
    renderer: FigureRenderer
        The figure renderer to use for drawing.
    curve_name: str
        The name of the curve for which to draw the MXE annotations.
    results: dict
        The results dictionary containing the calculated MXE values and their positions under the
        keys "before_mxe_{measurement_type}_value", "before_mxe_{measurement_type}_position",
        "during_mxe_{measurement_type}_value", "during_mxe_{measurement_type}_position",
        "after_mxe_{measurement_type}_value", and "after_mxe_{measurement_type}_position", where
        {measurement_type} is determined based on the curve_name.
    """
    measurement_type = get_measurement_type(curve_name)
    if "setpoint_tracking_controlled_magnitude_name" in results:
        measurement_type = "tc_controlled_magnitude"
        if not is_controlled_magnitude(
            curve_name, results["setpoint_tracking_controlled_magnitude_name"]
        ):
            return

    text = _build_mxe_text(curve_name, measurement_type, results, renderer)
    if text:
        renderer.add_annotation(
            text="MXE:\n" + text,
            x=0.0,
            y=0.0,
            color=_COLOR_MXE,
            paper_coords=True,
        )


def draw_reference_curve(
    renderer: FigureRenderer,
    curve_name: str,
    reference_curves: pd.DataFrame,
    label: str = "reference",
) -> None:
    """Draw a reference curve on the figure if it exists in the reference_curves DataFrame.

    Parameters
    ----------
    renderer: FigureRenderer
        The figure renderer to use for drawing.
    curve_name: str
        The name of the curve for which to draw the reference curve.
    reference_curves: pd.DataFrame
        The DataFrame containing reference curves, with a "time" column and columns for each curve.
    label: str
        The label to use for the reference curve in the legend.
    """
    if reference_curves is None:
        return
    if curve_name not in reference_curves:
        return
    if "VoltageSetpointPu" in curve_name:
        return

    renderer.add_curve(
        x=reference_curves["time"],
        y=reference_curves[curve_name],
        color=_COLOR_REFERENCE,
        style="-",
        name=label,
    )
