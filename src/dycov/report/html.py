#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import inspect
import shutil
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from jinja2 import Template

from dycov.configuration.cfg import config


def _is_controlled_magnitude(curve_name: str, column_name: str) -> bool:
    if curve_name == "BusPDR_BUS_ActivePower":
        return column_name == "P"
    if curve_name == "BusPDR_BUS_ReactivePower":
        return column_name == "Q"
    if curve_name == "BusPDR_BUS_ActiveCurrent":
        return column_name == "P"
    if curve_name == "BusPDR_BUS_ReactiveCurrent":
        return column_name == "Q"
    if curve_name == "BusPDR_BUS_Voltage":
        return column_name == "V"
    if curve_name == "NetworkFrequencyPu":
        return column_name == "$\\omega"

    return False


def _get_measurement_type(curve_name: str) -> str:
    if curve_name == "BusPDR_BUS_ActivePower":
        return "active_power"
    if curve_name == "BusPDR_BUS_ReactivePower":
        return "reactive_power"
    if curve_name == "BusPDR_BUS_ActiveCurrent":
        return "active_current"
    if curve_name == "BusPDR_BUS_ReactiveCurrent":
        return "reactive_current"
    if curve_name == "BusPDR_BUS_Voltage":
        return "voltage"
    if curve_name == "NetworkFrequencyPu":
        return "frequency"

    return ""


def _get_curve_names(
    variable_names,
    curves,
) -> list:
    if isinstance(variable_names, str):
        curve_names = [variable_names]
    else:
        curve_names = []
        for name in variable_names:
            if name["type"] == "generator":
                curve_names.extend(
                    [col for col in curves if col.endswith("_GEN_" + name["variable"])]
                )
            elif name["type"] == "transformer":
                curve_names.extend(
                    [col for col in curves if col.endswith("_XFMR_" + name["variable"])]
                )
            elif name["type"] == "bus":
                curve_names.extend(["BusPDR" + "_BUS_" + name["variable"]])

    return curve_names


def _additional_active_traces(fig, additional_curves, time, curve, results):
    last_val = curve.iloc[-1]
    if "10P" in additional_curves:
        if abs(last_val) <= 1:
            mean_val_max = last_val + 0.1
            mean_val_min = last_val - 0.1

        # If the value is more than 1, we use relative value
        else:
            mean_val_max = last_val + abs(0.1 * last_val)
            mean_val_min = last_val - abs(0.1 * last_val)

        fig.add_hline(y=mean_val_max, line_color="#55a868", line_dash="dash")
        fig.add_hline(y=mean_val_min, line_color="#55a868", line_dash="dash")

    if "5P" in additional_curves:
        # Get the tube
        if abs(last_val) <= 1:
            mean_val_max = last_val + 0.05
            mean_val_min = last_val - 0.05

        # If the value is more than 1, we use relative value
        else:
            mean_val_max = last_val + abs(0.05 * last_val)
            mean_val_min = last_val - abs(0.05 * last_val)

        fig.add_hline(y=mean_val_max, line_color="#c44e52", line_dash="dash")
        fig.add_hline(y=mean_val_min, line_color="#c44e52", line_dash="dash")

    if "10Pfloor" in additional_curves:
        # Get the tube
        if abs(last_val) <= 1:
            mean_val_min = last_val - 0.1

        # If the value is more than 1, we use relative value
        else:
            mean_val_min = last_val - abs(0.1 * last_val)

        fig.add_hline(y=mean_val_min, line_color="#55a868", line_dash="dash")

    if "5Pfloor" in additional_curves:
        # Get the tube
        if abs(last_val) <= 1:
            mean_val_min = last_val - 0.05

        # If the value is more than 1, we use relative value
        else:
            mean_val_min = last_val - abs(0.05 * last_val)

        fig.add_hline(y=mean_val_min, line_color="#c44e52", line_dash="dash")


def _additional_traces(fig, additional_curves, time, curve, results):
    if "85U" in additional_curves:
        val_85 = results["time_85U"] + results["sim_t_event_start"]
        fig.add_vline(x=val_85, opacity=0.8, line_color="#000000", line_dash="dash")

    f_nom = config.get_float("Global", "f_nom", 50.0)
    if "freq_1" in additional_curves:
        fig.add_hline(y=(f_nom + 1) / f_nom, line_color="#c44e52", line_dash="dash")
        fig.add_hline(y=(f_nom - 1) / f_nom, line_color="#c44e52", line_dash="dash")

    if "freq_200" in additional_curves:
        fig.add_hline(y=(f_nom + 0.2) / f_nom, line_color="#55a868", line_dash="dash")
        fig.add_hline(y=(f_nom - 0.2) / f_nom, line_color="#55a868", line_dash="dash")

    if "freq_250" in additional_curves:
        fig.add_hline(y=(f_nom + 0.250) / f_nom, line_color="#c44e52", line_dash="dash")
        fig.add_hline(y=(f_nom - 0.250) / f_nom, line_color="#c44e52", line_dash="dash")

    if "AVR5" in additional_curves:
        # Get the tube
        percent = 0.05
        for AVR_5_crv in results["AVR_5_crvs"]:
            line_max = []
            line_min = []
            for i in AVR_5_crv:
                mean_val = i
                if mean_val <= 1:
                    mean_val_max = mean_val + percent
                    mean_val_min = mean_val - percent
                # If the value is more than 1, we use relative value
                else:
                    mean_val_max = mean_val + abs(percent * mean_val)
                    mean_val_min = mean_val - abs(percent * mean_val)

                line_max.append(mean_val_max)
                line_min.append(mean_val_min)

            fig.add_traces(
                go.Scatter(
                    x=time,
                    y=line_max,
                    mode="lines",
                    line_color="#c44e52",
                    line_dash="dash",
                )
            )
            fig.add_traces(
                go.Scatter(
                    x=time,
                    y=line_min,
                    mode="lines",
                    line_color="#c44e52",
                    line_dash="dash",
                )
            )


def _response_charact_traces(fig, results, curve_name):
    if "calc_reaction_target" in results:
        if curve_name in results["calc_reaction_target"]:
            treaction = results["calc_reaction_time"] + results["sim_t_event_start"]
            target = results["calc_reaction_target"][curve_name]
            fig.add_hline(y=target, line_color="#bee7fa", line_dash="dashdot", line_width=1)
            fig.add_vline(x=treaction, line_color="#f7d7f6", line_dash="dashdot", line_width=1)

    if "calc_rise_target" in results:
        if curve_name in results["calc_rise_target"]:
            trise = results["calc_rise_time"] + results["sim_t_event_start"]
            target = results["calc_rise_target"][curve_name]
            fig.add_hline(y=target, line_color="#bee7fa", line_dash="dashdot", line_width=1)
            fig.add_vline(x=trise, line_color="#f7d7f6", line_dash="dashdot", line_width=1)
            offset_y = 10.0
            if (
                results["calc_rise_target"][curve_name]
                > results["calc_reaction_target"][curve_name]
            ):
                offset_y = -10.0
            fig.add_traces(
                go.Scatter(
                    x=[trise],
                    y=[target],
                    line_color="#fcb1fa",
                    name="rise time",
                )
            )
            fig.add_annotation(
                text=f"{trise:.4f}s",
                x=trise,
                y=target,
                xshift=25,
                yshift=offset_y,
                showarrow=False,
                font=dict(
                    family="sans serif",
                    size=14,
                    color="#ff82fc",
                ),
            )

    if "calc_settling_tube" in results:
        if curve_name in results["calc_settling_tube"]:
            tsettling = results["calc_settling_time"] + results["sim_t_event_start"]
            ss_value = results["calc_ss_value"]
            tube = results["calc_settling_tube"][curve_name]
            fig.add_hrect(y0=tube[0], y1=tube[1], line_width=0, fillcolor="#d7f7e0", opacity=0.5)
            fig.add_vline(x=tsettling, line_color="#f7d7f6", line_dash="dashdot", line_width=1)
            offset_y = 10.0
            if "calc_rise_target" in results and (
                results["calc_rise_target"][curve_name]
                > results["calc_reaction_target"][curve_name]
            ):
                offset_y = -10.0
            fig.add_traces(
                go.Scatter(
                    x=[tsettling],
                    y=[ss_value],
                    line_color="#fcb1fa",
                    name="settling time",
                )
            )
            fig.add_annotation(
                text=f"{tsettling:.4f}s",
                x=tsettling,
                y=ss_value,
                xshift=25,
                yshift=offset_y,
                showarrow=False,
                font=dict(
                    family="sans serif",
                    size=14,
                    color="#ff82fc",
                ),
            )


def _mxe_traces(fig, results, curve_name):
    measurement_type = _get_measurement_type(curve_name)
    if "setpoint_tracking_controlled_magnitude_name" in results:
        measurement_type = "tc_controlled_magnitude"
        if not _is_controlled_magnitude(
            curve_name, results["setpoint_tracking_controlled_magnitude_name"]
        ):
            return

    before_mxe = None
    during_mxe = None
    after_mxe = None
    if "before_mxe_" + measurement_type + "_position" in results:
        mxe_position = results["before_mxe_" + measurement_type + "_position"]
        before_mxe = results["before_mxe_" + measurement_type + "_value"]
        tmxe = mxe_position[0]
        fig.add_vline(x=tmxe, line_color="#9acd83", line_dash="dashdot", line_width=1)

    if "during_mxe_" + measurement_type + "_position" in results:
        mxe_position = results["during_mxe_" + measurement_type + "_position"]
        during_mxe = results["during_mxe_" + measurement_type + "_value"]
        tmxe = mxe_position[0]
        fig.add_vline(x=tmxe, line_color="#9acd83", line_dash="dashdot", line_width=1)

    if "after_mxe_" + measurement_type + "_position" in results:
        mxe_position = results["after_mxe_" + measurement_type + "_position"]
        after_mxe = results["after_mxe_" + measurement_type + "_value"]
        tmxe = mxe_position[0]
        fig.add_vline(x=tmxe, line_color="#9acd83", line_dash="dashdot", line_width=1)

    text = ""
    if before_mxe is not None:
        text += f"Before: {before_mxe:.3f}<br>"
    if during_mxe is not None:
        text += f"During: {during_mxe:.3f}<br>"
    if after_mxe is not None:
        text += f"After: {after_mxe:.3f}<br>"
    if len(text) > 0:
        fig.add_annotation(
            text="MXE:<br>" + text,
            xref="paper",
            yref="paper",
            x=1,
            y=0,
            showarrow=False,
            font=dict(
                family="sans serif",
                size=14,
                color="#9acd83",
            ),
            align="left",
        )


def _reference_traces(fig, reference_curves, curve_name):
    if reference_curves is None:
        return

    if curve_name not in reference_curves:
        return

    if "AVRSetpointPu" in curve_name:
        return

    fig.add_traces(
        go.Scatter(
            x=reference_curves["time"],
            y=reference_curves[curve_name],
            mode="lines",
            name="reference",
            line_color="#dd8452",
        )
    )


def _exclusion_windows(fig, results):
    if "event_exclusion_window_start" in results:
        fig.add_vrect(
            x0=results["event_exclusion_window_start"],
            x1=results["event_exclusion_window_end"],
            line_width=0,
            opacity=0.5,
            fillcolor="#e8e8e8",
        )
    if "clear_exclusion_window_start" in results:
        fig.add_vrect(
            x0=results["clear_exclusion_window_start"],
            x1=results["clear_exclusion_window_end"],
            line_width=0,
            opacity=0.5,
            fillcolor="#e8e8e8",
        )


def _plotly_figures(
    fig,
    curve_name,
    additional_curves,
    calculated_curves,
    reference_curves,
    results,
    show_response_characteristics,
):
    _exclusion_windows(fig, results)

    _additional_active_traces(
        fig,
        additional_curves,
        calculated_curves["time"],
        calculated_curves[curve_name],
        results,
    )
    _additional_traces(
        fig,
        additional_curves,
        calculated_curves["time"],
        calculated_curves[curve_name],
        results,
    )
    if show_response_characteristics:
        _response_charact_traces(fig, results, curve_name)
        _mxe_traces(fig, results, curve_name)

    name = "calculated"
    line_color = "#4c72b0"
    line_dash = "solid"
    if "AVRSetpointPu" in curve_name:
        name = "setpoint"
        line_color = "#959595"
        line_dash = "dot"

    _reference_traces(fig, reference_curves, curve_name)

    fig.add_traces(
        go.Scatter(
            x=calculated_curves["time"],
            y=calculated_curves[curve_name],
            mode="lines",
            name=name,
            line_color=line_color,
            line_dash=line_dash,
        )
    )


def _update_layout(fig, curve_name, figure_description):
    fig.update_layout(
        title=curve_name,
        xaxis_title="Time",
        yaxis_title=figure_description,
        template="plotly_dark",
        font_color="#000000",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
    )
    fig.update_xaxes(
        showline=True,
        linewidth=2,
        linecolor="black",
        showgrid=False,
    )
    fig.update_yaxes(
        showline=True,
        linewidth=2,
        linecolor="black",
        showgrid=False,
    )


def plotly_figures(
    figure_description: list,
    calculated_curves: pd.DataFrame,
    reference_curves: pd.DataFrame,
    results: dict,
) -> str:
    """Create plotly figures for the curves.

    Parameters
    ----------
    figure_description: list
        List of figure description
    calculated_curves: DataFrame
        DataFrame with the calculated curves
    reference_curves: DataFrame
        DataFrame with the reference curves
    results: dict
        Dictionary with the results of the simulation

    Returns
    -------
    str
        HTML string of the plotly figures
    """
    curve_names = _get_curve_names(figure_description[1], calculated_curves)

    fig = go.Figure()
    for curve_name in curve_names:
        _plotly_figures(
            fig,
            curve_name,
            figure_description[2],
            calculated_curves,
            reference_curves,
            results,
            True,
        )

    if curve_names:
        _update_layout(fig, curve_names[0], figure_description[3])
        return (
            curve_names,
            curve_names[0],
            fig.to_html(full_html=False, include_plotlyjs="directory", div_id=curve_names[0]),
        )

    return curve_names, "", ""


def plotly_all_curves(
    plotted_curves: list,
    results: dict,
) -> list:
    """Create plotly figures for all curves.

    Parameters
    ----------
    plotted_curves: list
        List of curves to be plotted
    results: dict
        Dictionary with the results of the simulation

    Returns
    -------
    list
        List of HTML strings of the plotly figures
    """
    calculated_curves = results["curves"]
    if "reference_curves" in results:
        reference_curves = results["reference_curves"]
    else:
        reference_curves = None

    figures = list()
    for curve_name in calculated_curves:
        if curve_name in plotted_curves or "time" == curve_name.lower():
            continue

        fig = go.Figure()
        _plotly_figures(fig, curve_name, [], calculated_curves, reference_curves, results, False)
        _update_layout(fig, curve_name, "Magnitude")
        figures.append(
            (
                curve_name,
                fig.to_html(full_html=False, include_plotlyjs="directory", div_id=curve_name),
            )
        )

    return figures


def create_html(
    producer: str, figures_to_plot: list, operating_condition: str, output_path: Path
) -> None:
    """Create the HTML report using Jinja2.

    Parameters
    ----------
    producer: str
        Producer name
    figures: list
        List of figure HTML strings
    operating_condition: str
        Operating condition for the report
    output_path: Path
        Path to the output directory
    """
    html_output_dir = output_path / "HTML"
    if not html_output_dir.exists():
        html_output_dir.mkdir()

    # Leave a copy of plotly.min.js (common JavaScript library used by all HTML output files):
    plotly_js_lib = html_output_dir / "plotly.min.js"
    if not plotly_js_lib.exists():
        shutil.copy(
            Path(inspect.getfile(go)).resolve().parent.parent / "package_data/plotly.min.js",
            html_output_dir,
        )

    sync_charts_js = html_output_dir / "sync_charts.js"
    if not sync_charts_js.exists():
        shutil.copy(
            Path(__file__).resolve().parent / "templates" / "sync_charts.js",
            html_output_dir,
        )

    # Instantiate the HTML file using Jinja
    chart_ids = [fig[0] for fig in figures_to_plot]
    figures = [fig[1] for fig in figures_to_plot]
    plotly_jinja_data = {"chart_ids": chart_ids, "figures": figures}
    output_html = html_output_dir / f"{producer}.{operating_condition}.html"
    input_template = Path(__file__).resolve().parent / "templates" / "template.html"
    with open(output_html, "w", encoding="utf-8") as output_file:
        with open(input_template) as template_file:
            j2_template = Template(template_file.read())
            output_file.write(j2_template.render(plotly_jinja_data))
