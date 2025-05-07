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


def test_plotly_figures_single_curve_success():
    # Prepare minimal valid data for a single curve
    figure_description = [
        "desc",
        {"type": "bus", "variable": "ActivePower"},
        [],
        "Power [pu]",
    ]
    calculated_curves = pd.DataFrame(
        {"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0]}
    )
    reference_curves = pd.DataFrame({"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.4, 0.9]})
    results = {}

    curve_names, html_out = html.plotly_figures(
        [
            figure_description[0],
            [figure_description[1]],
            figure_description[2],
            figure_description[3],
        ],
        calculated_curves,
        reference_curves,
        results,
    )
    assert curve_names == ["BusPDR_BUS_ActivePower"]
    assert isinstance(html_out, str)
    assert "<html" not in html_out  # Should be a fragment, not full HTML
    assert "plotly" in html_out.lower()


def test_plotly_figures_with_additional_traces():
    # Prepare data with additional traces and response characteristics
    figure_description = [
        "desc",
        {"type": "bus", "variable": "ActivePower"},
        ["10P", "5P", "freq_1", "AVR5"],
        "Power [pu]",
    ]
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

    curve_names, html_out = html.plotly_figures(
        [
            figure_description[0],
            [figure_description[1]],
            figure_description[2],
            figure_description[3],
        ],
        calculated_curves,
        reference_curves,
        results,
    )
    assert curve_names == ["BusPDR_BUS_ActivePower"]
    assert isinstance(html_out, str)
    assert "plotly" in html_out.lower()


def test_create_html_success():
    # Prepare a temporary directory and a dummy template
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir)
        html_dir = output_path / "HTML"
        html_dir.mkdir()
        # Create a dummy plotly.min.js
        plotly_js = html_dir / "plotly.min.js"
        plotly_js.write_text("// plotly js dummy")
        # Create a dummy template
        templates_dir = Path(__file__).resolve().parent / "templates"
        templates_dir.mkdir(exist_ok=True)
        template_path = templates_dir / "template.html"
        template_path.write_text("{{ figures|length }} figures rendered")
        # Prepare figures
        figures = ["<div>figure1</div>", "<div>figure2</div>"]
        operating_condition = "test_condition"
        # Patch __file__ to point to this test file for template resolution
        orig_file = html.__file__
        html.__file__ = str(Path(__file__))
        try:
            html.create_html(figures, operating_condition, output_path)
            output_html = html_dir / f"{operating_condition}.html"
            assert output_html.exists()
            content = output_html.read_text()
            assert "2 figures rendered" in content
        finally:
            html.__file__ = orig_file
            if template_path.exists():
                template_path.unlink()
            if templates_dir.exists():
                try:
                    templates_dir.rmdir()
                except Exception:
                    pass


def test_plotly_figures_missing_reference_curves():
    figure_description = [
        "desc",
        {"type": "bus", "variable": "ActivePower"},
        [],
        "Power [pu]",
    ]
    calculated_curves = pd.DataFrame(
        {"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0]}
    )
    reference_curves = None
    results = {}

    curve_names, html_out = html.plotly_figures(
        [
            figure_description[0],
            [figure_description[1]],
            figure_description[2],
            figure_description[3],
        ],
        calculated_curves,
        reference_curves,
        results,
    )
    assert curve_names == ["BusPDR_BUS_ActivePower"]
    assert isinstance(html_out, str)


def test_plotly_figures_no_curve_names():
    figure_description = [
        "desc",
        [],
        [],
        "Power [pu]",
    ]
    calculated_curves = pd.DataFrame(
        {
            "time": [0, 1, 2],
        }
    )
    reference_curves = pd.DataFrame(
        {
            "time": [0, 1, 2],
        }
    )
    results = {}

    curve_names, html_out = html.plotly_figures(
        [
            figure_description[0],
            figure_description[1],
            figure_description[2],
            figure_description[3],
        ],
        calculated_curves,
        reference_curves,
        results,
    )
    assert curve_names == []
    assert html_out == ""


def test_plotly_figures_incomplete_results_dict():
    figure_description = [
        "desc",
        {"type": "bus", "variable": "ActivePower"},
        [],
        "Power [pu]",
    ]
    calculated_curves = pd.DataFrame(
        {"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0]}
    )
    reference_curves = pd.DataFrame({"time": [0, 1, 2], "BusPDR_BUS_ActivePower": [0.0, 0.4, 0.9]})
    # results missing many keys
    results = {}

    curve_names, html_out = html.plotly_figures(
        [
            figure_description[0],
            [figure_description[1]],
            figure_description[2],
            figure_description[3],
        ],
        calculated_curves,
        reference_curves,
        results,
    )
    assert curve_names == ["BusPDR_BUS_ActivePower"]
    assert isinstance(html_out, str)


def test_plotly_figures_multiple_curves():
    figure_description = [
        "desc",
        [
            {"type": "bus", "variable": "ActivePower"},
            {"type": "bus", "variable": "ReactivePower"},
        ],
        [],
        "Power [pu]",
    ]
    calculated_curves = pd.DataFrame(
        {
            "time": [0, 1, 2],
            "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0],
            "BusPDR_BUS_ReactivePower": [0.0, -0.5, -1.0],
        }
    )
    reference_curves = pd.DataFrame(
        {
            "time": [0, 1, 2],
            "BusPDR_BUS_ActivePower": [0.0, 0.4, 0.9],
            "BusPDR_BUS_ReactivePower": [0.0, -0.4, -0.9],
        }
    )
    results = {}

    curve_names, html_out = html.plotly_figures(
        [
            figure_description[0],
            figure_description[1],
            figure_description[2],
            figure_description[3],
        ],
        calculated_curves,
        reference_curves,
        results,
    )
    assert set(curve_names) == {"BusPDR_BUS_ActivePower", "BusPDR_BUS_ReactivePower"}
    assert isinstance(html_out, str)


def test_create_html_missing_template():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir)
        html_dir = output_path / "HTML"
        html_dir.mkdir()
        # Remove template if exists
        templates_dir = Path(__file__).resolve().parent / "templates"
        template_path = templates_dir / "template.html"
        if template_path.exists():
            template_path.unlink()
        figures = ["<div>figure1</div>"]
        operating_condition = "missing_template"
        orig_file = html.__file__
        html.__file__ = str(Path(__file__))
        try:
            with pytest.raises(FileNotFoundError):
                html.create_html(figures, operating_condition, output_path)
        finally:
            html.__file__ = orig_file


def test_plotly_all_curves_skips_plotted_and_time():
    calculated_curves = pd.DataFrame(
        {
            "time": [0, 1, 2],
            "curve1": [1, 2, 3],
            "curve2": [4, 5, 6],
            "curve3": [7, 8, 9],
        }
    )
    results = {
        "curves": calculated_curves,
        "reference_curves": None,
    }
    plotted_curves = ["curve2", "curve3"]
    figures = html.plotly_all_curves(plotted_curves, results)
    # Only curve1 should be plotted (not time, not curve2, not curve3)
    assert len(figures) == 1
    assert "curve1" in figures[0]


# Returns "active_power" when curve_name is "BusPDR_BUS_ActivePower"
def test_returns_active_power_for_active_power_curve():
    # Arrange
    curve_name = "BusPDR_BUS_ActivePower"

    # Act
    result = html._get_measurement_type(curve_name)

    # Assert
    assert result == "active_power"


# Returns "reactive_power" when curve_name is "BusPDR_BUS_ReactivePower"
def test_returns_reactive_power_for_reactive_power_curve():
    # Arrange
    curve_name = "BusPDR_BUS_ReactivePower"

    # Act
    result = html._get_measurement_type(curve_name)

    # Assert
    assert result == "reactive_power"


# Returns "active_current" when curve_name is "BusPDR_BUS_ActiveCurrent"
def test_returns_active_current_for_active_current_curve():
    # Arrange
    curve_name = "BusPDR_BUS_ActiveCurrent"

    # Act
    result = html._get_measurement_type(curve_name)

    # Assert
    assert result == "active_current"


# Returns "reactive_current" when curve_name is "BusPDR_BUS_ReactiveCurrent"
def test_returns_reactive_current_for_reactive_current_curve():
    # Arrange
    curve_name = "BusPDR_BUS_ReactiveCurrent"

    # Act
    result = html._get_measurement_type(curve_name)

    # Assert
    assert result == "reactive_current"


# Returns "voltage" when curve_name is "BusPDR_BUS_Voltage"
def test_returns_voltage_for_voltage_curve():
    # Arrange
    curve_name = "BusPDR_BUS_Voltage"

    # Act
    result = html._get_measurement_type(curve_name)

    # Assert
    assert result == "voltage"


# Returns "frequency" when curve_name is "NetworkFrequencyPu"
def test_returns_frequency_for_network_frequency_curve():
    # Arrange
    curve_name = "NetworkFrequencyPu"

    # Act
    result = html._get_measurement_type(curve_name)

    # Assert
    assert result == "frequency"


# Return true when curve_name is "BusPDR_BUS_ActivePower" and column_name is "P"
def test_active_power_with_p_returns_true():
    # Arrange
    curve_name = "BusPDR_BUS_ActivePower"
    column_name = "P"

    # Act
    result = html._is_controlled_magnitude(curve_name, column_name)

    # Assert
    assert result is True


# Return true when curve_name is "BusPDR_BUS_RectivePower" and column_name is "Q"
def test_reactive_power_with_q_returns_true():
    # Arrange
    curve_name = "BusPDR_BUS_ReactivePower"
    column_name = "Q"

    # Act
    result = html._is_controlled_magnitude(curve_name, column_name)

    # Assert
    assert result is True


# Return true when curve_name is "BusPDR_BUS_ActiveCurrent" and column_name is "P"
def test_active_current_with_p_returns_true():
    # Arrange
    curve_name = "BusPDR_BUS_ActiveCurrent"
    column_name = "P"

    # Act
    result = html._is_controlled_magnitude(curve_name, column_name)

    # Assert
    assert result is True


# Return true when curve_name is "BusPDR_BUS_RectiveCurrent" and column_name is "Q"
def test_reactive_current_with_q_returns_true():
    # Arrange
    curve_name = "BusPDR_BUS_ReactiveCurrent"
    column_name = "Q"

    # Act
    result = html._is_controlled_magnitude(curve_name, column_name)

    # Assert
    assert result is True


# Return true when curve_name is "BusPDR_BUS_Voltage" and column_name is "V"
def test_voltage_with_v_returns_true():
    # Arrange
    curve_name = "BusPDR_BUS_Voltage"
    column_name = "V"

    # Act
    result = html._is_controlled_magnitude(curve_name, column_name)

    # Assert
    assert result is True


# Return true when curve_name is "NetworkFrequencyPu" and column_name is "$\\omega"
def test_network_frequency_with_omega_returns_true():
    # Arrange
    curve_name = "NetworkFrequencyPu"
    column_name = "$\\omega"

    # Act
    result = html._is_controlled_magnitude(curve_name, column_name)

    # Assert
    assert result is True
