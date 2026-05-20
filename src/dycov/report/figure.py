#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import math
from pathlib import Path
from typing import Optional, Union

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import FormatStrFormatter

from dycov.configuration.cfg import config
from dycov.logging.logging import dycov_logging
from dycov.report.curve_classification import get_curve_style
from dycov.report.figure_decorations import (
    _COLOR_REFERENCE,
    draw_additional_curves,
    draw_exclusion_windows,
    draw_mxe,
    draw_response_characteristics,
)
from dycov.report.figure_renderer import MatplotlibRenderer
from dycov.report.types import FigureDescription


def _add_curve2plot(
    variable_tool_name: str,
    curve_name: str,
    curves: pd.DataFrame,
    plot_curves: list,
    is_reference: bool = False,
) -> None:
    if curve_name is None:
        return
    if variable_tool_name == "VoltageSetpointPu" and is_reference:
        return

    curve_style = get_curve_style(variable_tool_name, is_reference)
    if curve_name in curves:
        plot_curves.append(
            {
                "name": curve_name,
                "curve": list(curves[curve_name]),
                "color": curve_style.color,
                "style": curve_style.style,
            }
        )


def _get_xrange(
    operating_condition: str,
    unit_characteristics: dict,
    time_curve: list,
    curves: list,
    sim_t_event_end: float,
) -> tuple[Optional[float], Optional[float]]:
    xmax = -999999
    xmin = 999999
    for curve in curves:
        xrange_min, xrange_max = _get_xrange_for_curve(
            operating_condition, unit_characteristics, time_curve, curve["curve"], sim_t_event_end
        )
        if xrange_min is None:
            return None, None
        else:
            if xrange_min < xmin:
                xmin = xrange_min
            if xrange_max > xmax:
                xmax = xrange_max

    return xmin, xmax


def _obtain_value(value_definition: str, unit_characteristics: dict) -> float:
    if "*" in value_definition:
        multiplier = float(value_definition.split("*")[0])
        value = value_definition.split("*")[1]
        if value in unit_characteristics:
            return multiplier * unit_characteristics[value]
    return float(value_definition)


def _get_xrange_for_curve(
    operating_condition: str,
    unit_characteristics: dict,
    time_curve: list,
    curve: list,
    sim_t_event_end: float,
) -> tuple[float, float]:
    # Tolerance for reference tracking tests should be adapted to the magnitude of the step change
    reference_step_size = config.get_value(operating_condition, "reference_step_size")
    if reference_step_size is None:
        graph_scale = 1.0
    else:
        graph_scale = abs(_obtain_value(str(reference_step_size), unit_characteristics))
    graph_rel_tol = config.get_float("Global", "graph_rel_tol", 0.002)
    graph_abs_tol = config.get_float("Global", "graph_abs_tol", 0.01) * graph_scale

    last_value = curve[-1]
    steady_pos = 0
    for i in range(len(curve)):
        pos = len(curve) - (i + 1)
        if not math.isclose(curve[pos], last_value, rel_tol=graph_rel_tol, abs_tol=graph_abs_tol):
            break

        steady_pos = pos

    xmin = None
    xmax = None

    if time_curve[steady_pos] >= sim_t_event_end:
        graph_preevent_trange_pct = (
            config.get_float("Global", "graph_preevent_trange_pct", 15) / 100.0
        )
        graph_postevent_trange_pct = (
            config.get_float("Global", "graph_postevent_trange_pct", 20) / 100.0
        )
        # To prevent completely flat curves
        plot_range = max(1, abs(time_curve[steady_pos] - sim_t_event_end))
        xmin = sim_t_event_end - graph_preevent_trange_pct * plot_range
        xmax = time_curve[steady_pos] + graph_postevent_trange_pct * plot_range

    return xmin, xmax


def _get_yrange(curves: list) -> tuple[Optional[float], Optional[float]]:
    """
    For all the curves to be plotted on the same graph, obtain the common y-axis range.
    """
    # Returning None means 'let it plot on auto-range'.
    manage_plots_yrange = not config.get_boolean("Global", "graph_auto_range_yrange", False)
    if not manage_plots_yrange:
        return None, None

    ymax = -math.inf
    ymin = math.inf
    for curve in curves:
        yrange_min, yrange_max = _get_yrange_for_curve(curve["curve"])
        if yrange_min is None or yrange_max is None:
            # if any curve in the list is on auto-range, all of them will
            return None, None
        else:
            if yrange_min < ymin:
                ymin = yrange_min
            if yrange_max > ymax:
                ymax = yrange_max

    return ymin, ymax


def _get_yrange_for_curve(curve: list) -> tuple[float, float]:
    """
    If the curve shows a large enough variation, let it plot with auto-range for the y-axis.
    Else, set the y-range explicitly. The idea is to show a sufficient amount of "zoom".
    """
    # curves varying less than this fraction of their avg value will receive an explicit y-range:
    limit_fraction = config.get_float("Global", "graph_minvariaton_yrange_pct", 2) / 100.0
    # yields margin of 10% of the curve variation
    bottom_expand = 1.0 + 2 * config.get_float("Global", "graph_bottom_yrange_pct", 10) / 100.0
    # yields margin of 5% of the curve variation
    top_expand = 1.0 + 2 * config.get_float("Global", "graph_top_yrange_pct", 5) / 100.0

    midpoint = (max(curve) + min(curve)) / 2
    variation = max(curve) - min(curve)
    if variation > limit_fraction * abs(midpoint):
        yrange_min = None
        yrange_max = None
    else:
        if variation == 0:
            variation = max(0.001, 0.1 * abs(midpoint))  # for flat curves
        yrange_min = midpoint - bottom_expand * variation / 2
        yrange_max = midpoint + top_expand * variation / 2

    return yrange_min, yrange_max


def _save_plot(
    fig: Figure,
    ax: Axes,
    time: list,
    curves: list,
    time_reference: list,
    curves_reference: list,
    time_range: dict,
    output_file: Path,
    unit: str,
    ymin: float,
    ymax: float,
) -> None:

    if time_reference is not None and curves_reference is not None:
        for curve_reference in curves_reference:
            ax.plot(
                time_reference, curve_reference["curve"], color=_COLOR_REFERENCE, linestyle="-"
            )

    for curve in curves:
        ax.plot(time, curve["curve"], color=curve["color"], linestyle=curve["style"])

    ax.yaxis.set_major_formatter(FormatStrFormatter("%.5g"))
    fig.subplots_adjust(left=0.2)
    if time_range["min"] is not None:
        try:
            ax.set_xlim(time_range["min"], time_range["max"])
        except UserWarning as uw:
            dycov_logging.get_logger("Figures").warning(f"X-axis warning {uw}")
    if ymin is not None:
        try:
            ax.set_ylim(ymin, ymax)
        except UserWarning as uw:
            dycov_logging.get_logger("Figures").warning(f"Y-axis warning {uw}")

    ax.set_xlabel("t(s)", fontsize=16)
    ax.set_ylabel(unit, fontsize=16)
    fig.savefig(output_file)
    plt.close(fig)


def _get_time_range(
    operating_condition: str,
    unit_characteristics: dict,
    figures_description: dict,
    results: dict,
    time: list,
) -> tuple[float, float]:
    curves = results["curves"]
    xmin = 99999
    xmax = -99999
    figure_key = operating_condition.rsplit(".", 1)[0]
    for figure_description in figures_description[figure_key]:
        plot_curves = get_curves2plot(figure_description.variables, curves)
        if len(plot_curves) == 0:
            continue

        xrange_min, xrange_max = _get_xrange(
            operating_condition,
            unit_characteristics,
            time,
            plot_curves,
            results["sim_t_event_start"],
        )
        if xrange_min is None:
            continue
        else:
            if xrange_min < xmin:
                xmin = xrange_min
            if xrange_max > xmax:
                xmax = xrange_max

    return xmin, xmax


def get_common_time_range(
    operating_condition: str,
    unit_characteristics: dict,
    figures_description: dict,
    results: dict,
) -> tuple[float, float]:
    """For a set of given curves, it obtains the minimum temporal range necessary to visualize all
    variations.

    Parameters
    ----------
    operating_condition: str
        Full operating condition name (with PCS and Benchmark)
    unit_characteristics: dict
        Generating unit characteristics
    figures_description: dict
        Description of every figure to plot by PCS
    results: dict
        Results of the validations applied in the pcs

    Returns
    -------
    float
        Minimum value of the time range
    float
        Maximum value of the time range
    """
    curves = results["curves"]
    time = list(curves["time"])
    xmin, xmax = _get_time_range(
        operating_condition, unit_characteristics, figures_description, results, time
    )

    if xmin == 99999 and xmax == -99999:
        dycov_logging.get_logger("Figures").warning(
            f"All curves appear to be flat in {operating_condition};"
            " something must be wrong with the simulation"
        )

    if xmin == 99999:
        xmin = time[0]
    if xmax == -99999:
        xmax = time[-1]

    # The settling time must always be visible; if it is not include in the calculated range,
    #  it is expanded to include it. In theory, it should never happen.
    if "calc_settling_time" in results:
        tsettling = results["calc_settling_time"] + results["sim_t_event_start"]
        if xmax < tsettling:
            xmax = tsettling + 5.0

    return xmin, xmax


def create_plot(
    time: list,
    figure_description: FigureDescription,
    curves: list,
    time_reference: list,
    curves_reference: list,
    time_range: dict,
    output_file: Path,
    results: dict,
    band_ref_val: float | None = None,
) -> None:
    """Draw a figure.

    Parameters
    ----------
    time: list
        Calculate times
    figure_description: FigureDescription
        Description of the figure to plot
    curves: list
        Calculate curves, with color and style
    time_reference: list
        Reference times
    curves_reference: list
        Reference curves, with color and style
    time_range: dict
        Time range to be displayed
    output_file: Path
        File where the graph will be saved
    results: dict
        Results of the validations applied in the pcs
    band_ref_val: float | None
        Reference value for the tolerance band, if applicable
    """
    ymin, ymax = _get_yrange(curves + curves_reference if curves_reference is not None else curves)
    last_val = band_ref_val if band_ref_val is not None else curves[0]["curve"][-1]

    variable_names = figure_description.variables
    unit = figure_description.ylabel

    if isinstance(variable_names, str):
        _plot_curve(
            time,
            variable_names,
            curves,
            time_reference,
            curves_reference,
            time_range,
            output_file,
            results,
            unit,
            ymin,
            ymax,
            figure_description=figure_description,
            last_val=last_val,
        )
    elif variable_names[0]["type"] == "bus":
        curve_name = "BusPDR_BUS_" + variable_names[0]["variable"]
        _plot_curve(
            time,
            curve_name,
            curves,
            time_reference,
            curves_reference,
            time_range,
            output_file,
            results,
            unit,
            ymin,
            ymax,
            figure_description,
            last_val,
        )
    else:
        variable_type = variable_names[0]["type"]
        suffix_map = {
            "generator": "_GEN_",
            "transformer": "_XFMR_",
            "sync_condenser": "_GEN_TSO_",
            "load": "_LOAD_TSO_",
        }
        suffix = suffix_map.get(variable_type, "")
        curves_names = [
            curve["name"]
            for curve in curves
            if curve["name"].endswith(suffix + variable_names[0]["variable"])
        ]
        for curve_name in curves_names:
            _plot_curve(
                time,
                curve_name,
                curves,
                time_reference,
                curves_reference,
                time_range,
                output_file,
                results,
                unit,
                ymin,
                ymax,
                figure_description,
                last_val,
            )


def _plot_curve(
    time: list,
    curve_name: str,
    curves: list,
    time_reference: list,
    curves_reference: list,
    time_range: dict,
    output_file: Path,
    results: dict,
    unit: str,
    ymin: float,
    ymax: float,
    figure_description: FigureDescription,
    last_val: float,
) -> None:
    fig, ax = plt.subplots()
    plt.sca(ax)

    renderer = MatplotlibRenderer()
    ymin, ymax = draw_additional_curves(
        renderer, figure_description, time, last_val, results, ymin, ymax
    )
    draw_response_characteristics(renderer, curve_name, results)
    draw_exclusion_windows(renderer, results)
    draw_mxe(renderer, curve_name, results)

    _save_plot(
        fig,
        ax,
        time,
        curves,
        time_reference,
        curves_reference,
        time_range,
        output_file,
        unit,
        ymin,
        ymax,
    )


def get_curves2plot(
    variable_names: Union[str, list],
    curves: pd.DataFrame,
    is_reference: bool = False,
) -> list:
    """Gets the data to graph.

    Parameters
    ----------
    variable_names: Union[str, list]
        Variables to plot
    curves: DataFrame
        Curves (calculated or reference)
    is_reference: bool
        Activate the flag to indicate that the input comes from the reference curves

    Returns
    -------
    list
        Curves to plot, with color and style
    """
    plot_curves = []
    if isinstance(variable_names, str):
        variable_name = variable_names
        curve_name = variable_names
        _add_curve2plot(variable_name, curve_name, curves, plot_curves, is_reference)
    else:
        for name in variable_names:
            if name["type"] == "generator":
                filter_col = [col for col in curves if col.endswith("_GEN_" + name["variable"])]
                for curve_name in filter_col:
                    _add_curve2plot(
                        name["variable"], curve_name, curves, plot_curves, is_reference
                    )
            elif name["type"] == "sync_condenser":
                filter_col = [
                    col for col in curves if col.endswith("_GEN_TSO_" + name["variable"])
                ]
                for curve_name in filter_col:
                    _add_curve2plot(
                        name["variable"], curve_name, curves, plot_curves, is_reference
                    )
            elif name["type"] == "load":
                filter_col = [
                    col for col in curves if col.endswith("_LOAD_TSO_" + name["variable"])
                ]
                for curve_name in filter_col:
                    _add_curve2plot(
                        name["variable"], curve_name, curves, plot_curves, is_reference
                    )
            elif name["type"] == "transformer":
                filter_col = [col for col in curves if col.endswith("_XFMR_" + name["variable"])]
                for curve_name in filter_col:
                    _add_curve2plot(
                        name["variable"], curve_name, curves, plot_curves, is_reference
                    )
            elif name["type"] == "bus":
                curve_name = "BusPDR" + "_BUS_" + name["variable"]
                _add_curve2plot(name["variable"], curve_name, curves, plot_curves, is_reference)

    return plot_curves
