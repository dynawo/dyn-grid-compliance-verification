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

from dycov.report.curve_classification import (
    build_curve_label,
    build_figure_title,
    get_curve_style,
)
from dycov.report.figure_decorations import (
    draw_additional_curves,
    draw_exclusion_windows,
    draw_mxe,
    draw_reference_curve,
    draw_response_characteristics,
)
from dycov.report.figure_renderer import PlotlyRenderer
from dycov.report.types import FigureDescription


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
                    [
                        col
                        for col in curves
                        if col.endswith("_GEN_" + name["variable"])
                        and "modIInjTerminal" not in col
                    ]
                )
            elif name["type"] == "transformer":
                curve_names.extend(
                    [col for col in curves if col.endswith("_XFMR_" + name["variable"])]
                )
            elif name["type"] == "bus":
                curve_names.extend(["BusPDR" + "_BUS_" + name["variable"]])

    ip_names = [n for n in curve_names if "IpInjTerminal" in n]
    if ip_names:
        mag_names = [col for col in curves.columns if "modIInjTerminal" in col]
        for insert_pos, mag_name in enumerate(mag_names):
            curve_names.insert(insert_pos, mag_name)

    return curve_names


def _has_iq_curve(variables) -> bool:
    if isinstance(variables, str):
        return False
    return any("IqInjTerminal" in v.get("variable", "") for v in variables)


def _plotly_figures(
    fig,
    curve_name,
    figure_description,
    calculated_curves,
    reference_curves,
    results,
    band_ref_val: float | None = None,
):
    renderer = PlotlyRenderer(fig)
    is_iq_curve = "IqInjTerminal" in curve_name
    if is_iq_curve or not _has_iq_curve(figure_description.variables):
        last_val = (
            band_ref_val if band_ref_val is not None else calculated_curves[curve_name].iloc[-1]
        )
        draw_additional_curves(
            renderer,
            figure_description,
            calculated_curves["time"],
            last_val,
            results,
            ymin=0.0,
            ymax=0.0,
        )
    draw_response_characteristics(renderer, curve_name, results)
    draw_mxe(renderer, curve_name, results)

    curve_style = get_curve_style(curve_name)
    role = "setpoint" if "VoltageSetpointPu" in curve_name else "calculated"
    show_equipment = not isinstance(figure_description.variables, str)
    label = build_curve_label(curve_name, role, show_equipment)
    ref_label = build_curve_label(curve_name, "reference", show_equipment)

    draw_reference_curve(renderer, curve_name, reference_curves, ref_label)

    fig.add_traces(
        go.Scatter(
            x=calculated_curves["time"],
            y=calculated_curves[curve_name],
            mode="lines",
            name=label,
            line_color=curve_style.color,
            line_dash=curve_style.style.replace("-", "solid").replace(":", "dot"),
        )
    )


def _update_layout(fig, curve_name, yaxis_title):
    fig.update_layout(
        title=curve_name,
        xaxis_title="Time",
        yaxis_title=yaxis_title,
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
    figure_description: FigureDescription,
    calculated_curves: pd.DataFrame,
    reference_curves: pd.DataFrame,
    results: dict,
    band_ref_val: float | None = None,
) -> str:
    """Create plotly figures for the curves.

    Parameters
    ----------
    figure_description: FigureDescription
        Description of the figure to plot
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
    curve_names = _get_curve_names(figure_description.variables, calculated_curves)

    fig = go.Figure()
    renderer = PlotlyRenderer(fig)
    draw_exclusion_windows(renderer, results)

    for curve_name in curve_names:
        _plotly_figures(
            fig,
            curve_name,
            figure_description,
            calculated_curves,
            reference_curves,
            results,
            band_ref_val=band_ref_val,
        )

    if curve_names:
        title = build_figure_title(figure_description.variables)
        _update_layout(fig, title, figure_description.ylabel)
        return (
            curve_names,
            figure_description.name,
            fig.to_html(
                full_html=False, include_plotlyjs="directory", div_id=figure_description.name
            ),
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
        empty_description = FigureDescription(
            name=curve_name,
            variables=curve_name,
            ylabel="Magnitude",
        )
        _plotly_figures(
            fig, curve_name, empty_description, calculated_curves, reference_curves, results
        )
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
