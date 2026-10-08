#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the figures and the page of the HTML report."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

from dycov.report import html
from dycov.report.types import DynamicBand, FigureDescription, FinalValueBand, FrequencyBand


@pytest.fixture
def html_templates(monkeypatch, tmp_path):
    """Points the HTML module at a templates directory of the test's own, holding the charts
    script, and returns where the page template goes."""
    module_dir = tmp_path / "report"
    templates_dir = module_dir / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "sync_charts.js").write_text("// sync charts js dummy")
    monkeypatch.setattr(html, "__file__", str(module_dir / "html.py"))
    return templates_dir / "template.html"


def _make_output_path(tmp_path: Path) -> Path:
    output_path = tmp_path / "output"
    (output_path / "HTML").mkdir(parents=True)
    (output_path / "HTML" / "plotly.min.js").write_text("// plotly js dummy")
    return output_path


def _make_injector_current_curves():
    """The Zone 1 injector currents, with the magnitude column the report adds beforehand."""
    return pd.DataFrame(
        {
            "time": [0, 1, 2],
            "WT_GEN_ActiveCurrentInjTerminal": [0.8, 0.6, 0.4],
            "WT_GEN_ReactiveCurrentInjTerminal": [0.1, 0.3, 0.5],
            "WT_GEN_modIInjTerminal": [0.81, 0.67, 0.64],
        }
    )


def test_plotly_figures_single_curve_success():
    figure_description = FigureDescription(
        name="desc", variables=[{"type": "bus", "variable": "ActivePower"}], ylabel="Power [pu]"
    )

    calculated_curves = pd.DataFrame(
        {"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0]}
    )
    reference_curves = pd.DataFrame({"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.4, 0.9]})
    results = {}

    curve_names, _, html_out = html.plotly_figures(
        figure_description,
        calculated_curves,
        reference_curves,
        results,
    )

    assert curve_names == ["BusPDR_BUS_ActivePower"]
    assert isinstance(html_out, str)
    assert "<html" not in html_out
    assert "plotly" in html_out.lower()


def test_plotly_figures_with_additional_traces():
    figure_description = FigureDescription(
        name="desc",
        variables=[{"type": "bus", "variable": "ActivePower"}],
        ylabel="Power [pu]",
        tolerance_band=FinalValueBand(upper=10.0, lower=10.0, color="#55a868"),
        frequency_bands=[FrequencyBand(upper=1.0, lower=1.0)],
        dynamic_band=DynamicBand(upper=5.0, lower=5.0, source_key="AVR_5_crvs"),
    )

    calculated_curves = pd.DataFrame(
        {"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0]}
    )
    reference_curves = pd.DataFrame({"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.4, 0.9]})
    results = {
        "AVR_5_crvs": [[0.0, 0.5, 1.0]],
        "sim_t_event_start": 0.0,
        "time_85U": 1.0,
        "calc_reaction_target": {"BusPDR_BUS_ActivePower": 1.0},
        "calc_reaction_time": 1.0,
        "calc_rise_target": {"BusPDR_BUS_ActivePower": 1.0},
        "calc_rise_time": 1.5,
        "calc_settling_tube": {"BusPDR_BUS_ActivePower": [0.9, 1.1]},
        "calc_settling_time": 2.0,
        "calc_ss_value": 1.0,
    }

    curve_names, _, html_out = html.plotly_figures(
        figure_description,
        calculated_curves,
        reference_curves,
        results,
    )

    assert curve_names == ["BusPDR_BUS_ActivePower"]
    assert isinstance(html_out, str)
    assert "plotly" in html_out.lower()


def test_plotly_figures_draw_the_frequency_and_its_reference_in_hz():
    figure_description = FigureDescription(
        name="fig_WRef",
        variables=[{"type": "generator", "variable": "NetworkFrequencyPu"}],
        ylabel=r"$\omega$ (Hz)",
        in_hz=True,
    )
    calculated_curves = pd.DataFrame({"time": [0, 1], "WT_GEN_NetworkFrequencyPu": [1.0, 0.98]})
    reference_curves = pd.DataFrame({"time": [0, 1], "WT_GEN_NetworkFrequencyPu": [1.0, 0.99]})
    fig = go.Figure()

    html._plotly_figures(
        fig,
        "WT_GEN_NetworkFrequencyPu",
        figure_description,
        calculated_curves,
        reference_curves,
        {},
    )

    assert [list(trace.y) for trace in fig.data] == [
        pytest.approx([50.0, 49.5]),
        pytest.approx([50.0, 49.0]),
    ]


def test_create_html_success(html_templates, tmp_path):
    html_templates.write_text("{{ figures|length }} figures rendered")
    output_path = _make_output_path(tmp_path)
    figures = [("figure1", "<div>figure1</div>"), ("figure2", "<div>figure2</div>")]

    html.create_html("producer", figures, "test_condition", output_path)

    output_html = output_path / "HTML" / "producer.test_condition.html"
    assert output_html.read_text() == "2 figures rendered"


def test_plotly_figures_missing_reference_curves():
    figure_description = FigureDescription(
        name="desc", variables=[{"type": "bus", "variable": "ActivePower"}], ylabel="Power [pu]"
    )

    calculated_curves = pd.DataFrame(
        {"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0]}
    )
    reference_curves = None
    results = {}

    curve_names, _, html_out = html.plotly_figures(
        figure_description,
        calculated_curves,
        reference_curves,
        results,
    )

    assert curve_names == ["BusPDR_BUS_ActivePower"]
    assert isinstance(html_out, str)


def test_plotly_figures_no_curve_names():
    figure_description = FigureDescription(name="desc", variables=[], ylabel="Power [pu]")

    calculated_curves = pd.DataFrame({"time": [0, 1, 2]})
    reference_curves = pd.DataFrame({"time": [0, 1, 2]})
    results = {}

    curve_names, _, html_out = html.plotly_figures(
        figure_description,
        calculated_curves,
        reference_curves,
        results,
    )

    assert curve_names == []
    assert html_out == ""


def test_plotly_figures_incomplete_results_dict():
    figure_description = FigureDescription(
        name="desc", variables=[{"type": "bus", "variable": "ActivePower"}], ylabel="Power [pu]"
    )

    calculated_curves = pd.DataFrame(
        {"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0]}
    )
    reference_curves = pd.DataFrame({"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.4, 0.9]})
    results = {}

    curve_names, _, html_out = html.plotly_figures(
        figure_description,
        calculated_curves,
        reference_curves,
        results,
    )

    assert curve_names == ["BusPDR_BUS_ActivePower"]
    assert isinstance(html_out, str)


def test_plotly_figures_multiple_curves():
    figure_description = FigureDescription(
        name="desc",
        variables=[
            {"type": "bus", "variable": "ActivePower"},
            {"type": "bus", "variable": "ReactivePower"},
        ],
        ylabel="Power [pu]",
    )

    calculated = pd.DataFrame(
        {
            "time": [0, 1, 2],
            "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0],
            "BusPDR_BUS_ReactivePower": [0.0, -0.5, -1.0],
        }
    )
    reference = pd.DataFrame(
        {
            "time": [0, 1, 2],
            "BusPDR_BUS_ActivePower": [0.0, 0.4, 0.9],
            "BusPDR_BUS_ReactivePower": [0.0, -0.4, -0.9],
        }
    )
    results = {}

    curve_names, _, html_out = html.plotly_figures(
        figure_description,
        calculated,
        reference,
        results,
    )

    assert set(curve_names) == {
        "BusPDR_BUS_ActivePower",
        "BusPDR_BUS_ReactivePower",
    }
    assert isinstance(html_out, str)


def test_create_html_missing_template(html_templates, tmp_path):
    output_path = _make_output_path(tmp_path)
    figures = [("figure1", "<div>figure1</div>")]

    with pytest.raises(FileNotFoundError, match="template.html"):
        html.create_html("producer", figures, "missing_template", output_path)


def test_plotly_figures_zone1_uses_internalnode1_labels():
    figure_description = FigureDescription(
        name="desc", variables=[{"type": "bus", "variable": "ActivePower"}], ylabel="Power [pu]"
    )
    calculated_curves = pd.DataFrame(
        {"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0]}
    )
    reference_curves = pd.DataFrame({"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.4, 0.9]})
    results = {}

    curve_names, _, html_out = html.plotly_figures(
        figure_description,
        calculated_curves,
        reference_curves,
        results,
        zone=1,
    )

    assert curve_names == ["BusPDR_BUS_ActivePower"]
    assert "InternalNode1" in html_out
    assert "PDR Bus" not in html_out


def test_plotly_figures_zone3_uses_pdr_labels():
    figure_description = FigureDescription(
        name="desc", variables=[{"type": "bus", "variable": "ActivePower"}], ylabel="Power [pu]"
    )
    calculated_curves = pd.DataFrame(
        {"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0]}
    )
    reference_curves = pd.DataFrame({"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.4, 0.9]})
    results = {}

    _, _, html_out = html.plotly_figures(
        figure_description,
        calculated_curves,
        reference_curves,
        results,
        zone=3,
    )

    assert "PDR Bus" in html_out
    assert "InternalNode1" not in html_out


def test_plotly_figures_marks_the_mxe_the_zone_measured_on_the_curve(monkeypatch):
    marked = []
    monkeypatch.setattr(
        html,
        "draw_mxe",
        lambda renderer, curve_name, results, zone: marked.append((curve_name, zone)),
    )
    figure_description = FigureDescription(
        name="fig_V", variables=[{"type": "bus", "variable": "Voltage"}], ylabel="V"
    )
    calculated_curves = pd.DataFrame({"time": [0, 1, 2], "BusPDR_BUS_Voltage": [1.0, 0.5, 1.0]})

    html.plotly_figures(figure_description, calculated_curves, None, {}, zone=1)

    assert marked == [("BusPDR_BUS_Voltage", 1)]


def test_plotly_figures_marks_no_mxe_on_a_figure_of_several_magnitudes(monkeypatch):
    """#553: the figure of the currents draws Ip and Iq together, and their MXE belongs to the
    figures that draw each of them alone."""
    marked = []
    monkeypatch.setattr(html, "draw_mxe", lambda *args: marked.append(args[1]))
    figure_description = FigureDescription(
        name="fig_I",
        variables=[
            {"type": "generator", "variable": "ActiveCurrentInjTerminal"},
            {"type": "generator", "variable": "ReactiveCurrentInjTerminal"},
        ],
        ylabel="I",
    )

    html.plotly_figures(figure_description, _make_injector_current_curves(), None, {}, zone=1)

    assert marked == []


def test_plotly_figures_draws_a_curve_without_reference_alone():
    """#553: the power at InternalNode1 needs no reference curve to be drawn."""
    figure_description = FigureDescription(
        name="fig_InternalNode1P", variables="BusPDR_BUS_ActivePower", ylabel="P"
    )
    calculated_curves = pd.DataFrame(
        {"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0]}
    )
    reference_curves = pd.DataFrame({"time": [0, 1, 2], "BusPDR_BUS_Voltage": [1.0, 1.0, 1.0]})

    curve_names, name, html_out = html.plotly_figures(
        figure_description, calculated_curves, reference_curves, {}, zone=1
    )

    assert (curve_names, name) == (["BusPDR_BUS_ActivePower"], "fig_InternalNode1P")
    assert "InternalNode1" in html_out
    assert "Active Power calculated" in html_out
    assert "Active Power reference" not in html_out


_POWER_WITH_ITS_SETPOINT = FigureDescription(
    name="fig_P",
    variables=[
        {"type": "generator", "variable": "ActivePowerControlledPu"},
        {"type": "generator", "variable": "ActivePowerSetpointPu"},
    ],
    ylabel="P",
)


def _make_power_curves(with_setpoint: bool = True) -> pd.DataFrame:
    curves = {"time": [0, 1, 2], "WT_GEN_ActivePowerControlledPu": [0.85, 0.82, 0.80]}
    if with_setpoint:
        curves["WT_GEN_ActivePowerSetpointPu"] = [0.85, 0.80, 0.80]
    return pd.DataFrame(curves)


def _drawn_traces(figure_description, calculated_curves, reference_curves) -> list:
    """The name and dash of every trace the figure draws, which the page only holds escaped."""
    fig = go.Figure()
    for curve_name in html._get_curve_names(figure_description.variables, calculated_curves):
        html._plotly_figures(
            fig, curve_name, figure_description, calculated_curves, reference_curves, {}, zone=1
        )
    return [(trace.name, trace.line.dash) for trace in fig.data]


def test_plotly_figures_draws_both_setpoints_over_the_power_they_drive():
    """#554: a reference setpoint that does not lie on the simulated one tells the user the
    reference curves stepped another setpoint, so both are drawn and named apart."""
    traces = _drawn_traces(_POWER_WITH_ITS_SETPOINT, _make_power_curves(), _make_power_curves())

    assert traces == [
        ("Active Power — WT reference", "solid"),
        ("Active Power — WT calculated", "solid"),
        ("Active Power Setpoint — WT reference", "dash"),
        ("Active Power Setpoint — WT calculated", "dot"),
    ]


def test_plotly_figures_draws_the_power_of_a_reference_without_its_setpoint():
    traces = _drawn_traces(
        _POWER_WITH_ITS_SETPOINT, _make_power_curves(), _make_power_curves(with_setpoint=False)
    )

    assert [name for name, _ in traces] == [
        "Active Power — WT reference",
        "Active Power — WT calculated",
        "Active Power Setpoint — WT calculated",
    ]


def test_plotly_figures_titles_the_figure_after_the_power_and_not_its_setpoint():
    curve_names, name, html_out = html.plotly_figures(
        _POWER_WITH_ITS_SETPOINT, _make_power_curves(), None, {}, zone=1
    )

    assert curve_names == ["WT_GEN_ActivePowerControlledPu", "WT_GEN_ActivePowerSetpointPu"]
    assert name == "fig_P"
    assert "Active Power \\u2014 Generator" in html_out


def test_plotly_all_curves_skips_plotted_and_time():
    calculated_curves = pd.DataFrame(
        {
            "time": [0, 1, 2],
            "curve1": [1, 2, 3],
            "curve2": [4, 5, 6],
            "curve3": [7, 8, 9],
        }
    )
    results = {"curves": calculated_curves, "reference_curves": None}
    plotted_curves = ["curve2", "curve3"]

    figures = html.plotly_all_curves(plotted_curves, results)

    assert len(figures) == 1
    assert figures[0][0] == "curve1"


def test_get_curve_names_draws_the_magnitude_with_both_components():
    variables = [
        {"type": "generator", "variable": "ActiveCurrentInjTerminal"},
        {"type": "generator", "variable": "ReactiveCurrentInjTerminal"},
    ]

    names = html._get_curve_names(variables, _make_injector_current_curves())

    assert "WT_GEN_modIInjTerminal" in names


def test_get_curve_names_leaves_the_magnitude_out_of_the_active_current_figure():
    variables = [{"type": "generator", "variable": "ActiveCurrentInjTerminal"}]

    names = html._get_curve_names(variables, _make_injector_current_curves())

    # The magnitude is the resultant of both components, so it belongs only to the figure
    # that draws both.
    assert names == ["WT_GEN_ActiveCurrentInjTerminal"]
