#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from dycov.report import html
from dycov.report.curve_classification import get_measurement_type, is_controlled_magnitude
from dycov.report.types import FigureDescription


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
    from dycov.report.types import DynamicBand, FinalValueBand, FrequencyBand

    figure_description = FigureDescription(
        name="desc",
        variables=[{"type": "bus", "variable": "ActivePower"}],
        ylabel="Power [pu]",
        tolerance_band=FinalValueBand(upper=10.0, lower=10.0, color="#55a868"),
        frequency_band=FrequencyBand(upper=1.0, lower=1.0),
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


def test_create_html_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir)
        html_dir = output_path / "HTML"
        html_dir.mkdir()

        (html_dir / "plotly.min.js").write_text("// plotly js dummy")

        templates_dir = Path(__file__).resolve().parent / "templates"
        templates_dir.mkdir(exist_ok=True)
        template_path = templates_dir / "template.html"
        template_path.write_text("{{ figures|length }} figures rendered")

        js_path = templates_dir / "sync_charts.js"
        js_path.write_text("// sync charts js dummy")

        producer = "producer"
        figures = [("figure1", "<div>figure1</div>"), ("figure2", "<div>figure2</div>")]
        operating_condition = "test_condition"

        orig_file = html.__file__
        html.__file__ = str(Path(__file__))

        try:
            html.create_html(producer, figures, operating_condition, output_path)
            output_html = html_dir / f"{producer}.{operating_condition}.html"
            assert output_html.exists()
            content = output_html.read_text()
            assert "2 figures rendered" in content
        finally:
            html.__file__ = orig_file
            if template_path.exists():
                template_path.unlink()
            if js_path.exists():
                js_path.unlink()
            try:
                templates_dir.rmdir()
            except Exception:
                pass


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


def test_create_html_missing_template():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir)
        html_dir = output_path / "HTML"
        html_dir.mkdir()

        templates_dir = Path(__file__).resolve().parent / "templates"
        template_path = templates_dir / "template.html"
        if template_path.exists():
            template_path.unlink()

        producer = "producer"
        figures = [("figure1", "<div>figure1</div>")]
        operating_condition = "missing_template"

        orig_file = html.__file__
        html.__file__ = str(Path(__file__))

        try:
            with pytest.raises(FileNotFoundError):
                html.create_html(producer, figures, operating_condition, output_path)
        finally:
            html.__file__ = orig_file


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


def test_returns_active_power_for_active_power_curve():
    assert get_measurement_type("BusPDR_BUS_ActivePower") == "active_power"


def test_returns_reactive_power_for_reactive_power_curve():
    assert get_measurement_type("BusPDR_BUS_ReactivePower") == "reactive_power"


def test_returns_active_current_for_active_current_curve():
    assert get_measurement_type("BusPDR_BUS_ActiveCurrent") == "active_current"


def test_returns_reactive_current_for_reactive_current_curve():
    assert get_measurement_type("BusPDR_BUS_ReactiveCurrent") == "reactive_current"


def test_returns_voltage_for_voltage_curve():
    assert get_measurement_type("BusPDR_BUS_Voltage") == "voltage"


def test_returns_frequency_for_network_frequency_curve():
    assert get_measurement_type("NetworkFrequencyPu") == "frequency"


def test_active_power_with_p_returns_true():
    assert is_controlled_magnitude("BusPDR_BUS_ActivePower", "P") is True


def test_reactive_power_with_q_returns_true():
    assert is_controlled_magnitude("BusPDR_BUS_ReactivePower", "Q") is True


def test_active_current_with_p_returns_true():
    assert is_controlled_magnitude("BusPDR_BUS_ActiveCurrent", "P") is True


def test_reactive_current_with_q_returns_true():
    assert is_controlled_magnitude("BusPDR_BUS_ReactiveCurrent", "Q") is True


def test_voltage_with_v_returns_true():
    assert is_controlled_magnitude("BusPDR_BUS_Voltage", "V") is True


def test_network_frequency_with_omega_returns_true():
    assert is_controlled_magnitude("NetworkFrequencyPu", "$\\omega") is True
