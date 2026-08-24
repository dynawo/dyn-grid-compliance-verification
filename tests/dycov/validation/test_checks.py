#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Unit tests for the curve error metrics and their compliance checks."""

import numpy as np
import pandas as pd
import pytest

from dycov.validation import checks

CHECKS_MODULE = "dycov.validation.checks"

WINDOWS = ("before", "during", "after")
ERRORS = ("mae", "me", "mxe")


class RecordingLogger:
    """Logger stand-in collecting the emitted errors."""

    def __init__(self):
        self.errors = []

    def error(self, message: str) -> None:
        self.errors.append(message)


def _make_window_errors(measurement, value=0.001):
    """Error metrics of one measurement in one window, with their positions."""
    errors = {error: value for error in ERRORS}
    errors.update({f"t{error}": 0.5 for error in ERRORS})
    errors.update({f"y{error}": 1.5 for error in ERRORS})
    return {measurement: errors}


def _make_compliance_values(measurement, values=None):
    """Per-window error metrics of one measurement, one value per window."""
    values = values or {window: 0.001 for window in WINDOWS}
    return {
        window: _make_window_errors(measurement, values[window]) if values[window] else {}
        for window in WINDOWS
    }


def _make_saved_errors(measurement, value=0.1, windows=WINDOWS):
    saved = {}
    for window in windows:
        for error in ERRORS:
            saved[f"{window}_{error}_{measurement}_value"] = value
            saved[f"{window}_{error}_{measurement}_position"] = [0.5, 1.5]
    return saved


def _make_window_checks(measurement, failing_window=None, windows=WINDOWS):
    return {
        f"{window}_{error}_{measurement}_check": window != failing_window
        for window in windows
        for error in ERRORS
    }


@pytest.fixture
def step_curves():
    """Calculated and reference curves differing by 1.0 in a single sample."""
    time = [0.0, 0.25, 0.5, 0.75, 1.0]
    calculated = pd.DataFrame(
        {
            "time": time,
            "BusPDR_BUS_ActivePower": [1.0, 2.0, 3.0, 4.0, 5.0],
            "BusPDR_BUS_ReactivePower": [1.0, 1.0, 1.0, 1.0, 1.0],
        }
    )
    reference = pd.DataFrame(
        {
            "time": time,
            "BusPDR_BUS_ActivePower": [1.0, 2.0, 2.0, 4.0, 5.0],
            "BusPDR_BUS_ReactivePower": [1.0, 1.0, 1.0, 1.0, 1.0],
        }
    )
    return calculated, reference


# ---------------------------------------------------------------------------
# Setpoint name mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "modified_setpoint, expected",
    [
        ("ActivePowerSetpointPu", "BusPDR_BUS_ActivePower"),
        ("ReactivePowerSetpointPu", "BusPDR_BUS_ReactivePower"),
        ("VoltageSetpointPu", "BusPDR_BUS_Voltage"),
        ("NetworkFrequencyPu", "NetworkFrequencyPu"),
        ("UnknownSetpoint", "BusPDR_BUS_ReactivePower"),
    ],
)
def test_get_measurement_name_maps_every_setpoint(modified_setpoint, expected):
    assert checks._get_measurement_name(modified_setpoint) == expected


def test_check_value_by_threshold_is_strict():
    assert checks._check_value_by_threshold(0.001, 0.01) is True
    assert checks._check_value_by_threshold(0.01, 0.01) is False


# ---------------------------------------------------------------------------
# Error metrics
# ---------------------------------------------------------------------------


def test_calculate_errors_computes_every_metric(step_curves):
    results = checks.calculate_errors(step_curves, 1.0)

    # A single sample deviates by 1.0 out of the five compared.
    active_power = results["BusPDR_BUS_ActivePower"]
    assert active_power["me"] == pytest.approx(0.2)
    assert active_power["mae"] == pytest.approx(0.2)
    assert active_power["mxe"] == pytest.approx(1.0)
    assert active_power["tmxe"] == pytest.approx(0.5)
    assert active_power["ymxe"] == pytest.approx(3.0)
    assert active_power["yref"] == pytest.approx(2.0)


def test_calculate_errors_normalizes_by_the_step_magnitude(step_curves):
    results = checks.calculate_errors(step_curves, 2.0)

    active_power = results["BusPDR_BUS_ActivePower"]
    assert active_power["me"] == pytest.approx(0.1)
    assert active_power["mae"] == pytest.approx(0.1)
    assert active_power["mxe"] == pytest.approx(0.5)


def test_calculate_errors_of_identical_curves_is_zero(step_curves):
    results = checks.calculate_errors(step_curves, 1.0)

    reactive_power = results["BusPDR_BUS_ReactivePower"]
    assert reactive_power["me"] == pytest.approx(0.0)
    assert reactive_power["mae"] == pytest.approx(0.0)
    assert reactive_power["mxe"] == pytest.approx(0.0)


def test_calculate_errors_without_samples_returns_no_metrics():
    empty = pd.DataFrame({"time": []})

    results = checks.calculate_errors((empty, empty), 1.0)

    assert results == {}


def test_calculate_errors_ignores_curves_outside_the_measurement_list(step_curves):
    calculated, reference = step_curves
    calculated["Wind_Turbine_GEN_InternalAngle"] = [0.1, 0.1, 0.1, 0.1, 0.1]
    reference["Wind_Turbine_GEN_InternalAngle"] = [0.2, 0.2, 0.2, 0.2, 0.2]

    results = checks.calculate_errors((calculated, reference), 1.0)

    assert set(results) == {"BusPDR_BUS_ActivePower", "BusPDR_BUS_ReactivePower"}


def test_calculate_errors_reports_a_measurement_missing_from_the_simulation(
    monkeypatch, step_curves
):
    logger = RecordingLogger()
    monkeypatch.setattr(f"{CHECKS_MODULE}.dycov_logging", logger)
    calculated, reference = step_curves
    reference["BusPDR_BUS_Voltage"] = [1.0, 1.0, 1.0, 1.0, 1.0]

    results = checks.calculate_errors((calculated, reference), 1.0)

    assert "BusPDR_BUS_Voltage" not in results
    assert logger.errors == ["Curve BusPDR_BUS_Voltage not found in simulation results."]


# ---------------------------------------------------------------------------
# Setpoint tracking
# ---------------------------------------------------------------------------


def test_complete_setpoint_tracking_within_the_thresholds_is_compliant():
    compliance_values = _make_compliance_values("BusPDR_BUS_ActivePower")
    results = {"compliance": True}

    checks.complete_setpoint_tracking(
        compliance_values, "ActivePowerSetpointPu", "active_power", results
    )

    assert results["setpoint_tracking_active_power_check"] is True
    assert results["compliance"] is True
    for window in WINDOWS:
        assert results[f"{window}_mae_tc_active_power_value"] == pytest.approx(0.001)
        assert results[f"{window}_mae_tc_active_power_check"] is True
        assert results[f"{window}_mae_tc_active_power_position"] == [0.5, 1.5]


def test_complete_setpoint_tracking_above_a_threshold_fails():
    compliance_values = _make_compliance_values(
        "BusPDR_BUS_ActivePower", {"before": 0.001, "during": 0.5, "after": 0.001}
    )
    results = {"compliance": True}

    checks.complete_setpoint_tracking(
        compliance_values, "ActivePowerSetpointPu", "active_power", results
    )

    assert results["during_mae_tc_active_power_check"] is False
    assert results["setpoint_tracking_active_power_check"] is False
    assert results["compliance"] is False


def test_complete_setpoint_tracking_without_the_during_window_skips_it():
    compliance_values = _make_compliance_values(
        "BusPDR_BUS_ActivePower", {"before": 0.001, "during": None, "after": 0.001}
    )
    results = {"compliance": True}

    checks.complete_setpoint_tracking(
        compliance_values, "ActivePowerSetpointPu", "active_power", results
    )

    assert "during_mae_tc_active_power_value" not in results
    assert results["setpoint_tracking_active_power_check"] is True
    assert results["compliance"] is True


# ---------------------------------------------------------------------------
# Voltage dip thresholds
# ---------------------------------------------------------------------------


def test_check_voltage_dips_uses_the_simulation_thresholds():
    compliance_values = _make_compliance_values(
        "BusPDR_BUS_ActivePower", {"before": 0.075, "during": 0.075, "after": 0.075}
    )

    before_check, during_check, after_check = (
        checks._check_voltage_dips(
            compliance_values, "BusPDR_BUS_ActivePower", "mae", is_field_measurements=False
        )[index]
        for index in (1, 4, 7)
    )

    # Simulation thresholds are 0.03 before/after and 0.07 during.
    assert before_check is False
    assert during_check is False
    assert after_check is False


def test_check_voltage_dips_uses_the_field_measurement_thresholds():
    compliance_values = _make_compliance_values(
        "BusPDR_BUS_ActivePower", {"before": 0.06, "during": 0.075, "after": 0.06}
    )

    before_check, during_check, after_check = (
        checks._check_voltage_dips(
            compliance_values, "BusPDR_BUS_ActivePower", "mae", is_field_measurements=True
        )[index]
        for index in (1, 4, 7)
    )

    # Field measurement thresholds are 0.07 before/after and 0.08 during.
    assert before_check is True
    assert during_check is True
    assert after_check is True


def test_check_voltage_dips_without_the_during_window_returns_no_during_metrics():
    compliance_values = _make_compliance_values(
        "BusPDR_BUS_ActivePower", {"before": 0.001, "during": None, "after": 0.001}
    )

    (
        _,
        before_check,
        _,
        during_value,
        during_check,
        during_position,
        _,
        after_check,
        _,
    ) = checks._check_voltage_dips(
        compliance_values, "BusPDR_BUS_ActivePower", "mae", is_field_measurements=False
    )

    assert before_check is True
    assert after_check is True
    assert during_value is None
    assert during_check is None
    assert during_position == [None, None]


def test_calculate_curves_errors_in_zone1_excludes_the_frequency():
    results = _make_compliance_values("BusPDR_BUS_ActivePower")

    checks.calculate_curves_errors(1, False, results)

    assert results["before_mae_active_power_value"] == pytest.approx(0.001)
    assert results["before_mae_active_power_check"] is True
    assert results["before_me_active_power_check"] is True
    assert results["before_mxe_active_power_check"] is True
    assert "before_mae_frequency_value" not in results


def test_calculate_curves_errors_in_zone3_includes_the_frequency():
    results = _make_compliance_values("NetworkFrequencyPu")

    checks.calculate_curves_errors(3, False, results)

    assert results["before_mae_frequency_value"] == pytest.approx(0.001)
    # The network frequency has no configured voltage dip threshold.
    assert results["before_mae_frequency_check"] is None


def test_calculate_curves_errors_without_the_during_window():
    results = _make_compliance_values(
        "BusPDR_BUS_ActivePower", {"before": 0.001, "during": None, "after": 0.001}
    )

    checks.calculate_curves_errors(1, False, results)

    assert results["during_mae_active_power_value"] is None
    assert results["during_me_active_power_value"] is None
    assert results["during_mxe_active_power_value"] is None
    assert results["after_mae_active_power_check"] is True


# ---------------------------------------------------------------------------
# Saved error metrics
# ---------------------------------------------------------------------------


def test_save_measurement_errors_copies_every_window_and_error():
    compliance_values = _make_saved_errors("active_power")
    results = {}

    checks.save_measurement_errors(compliance_values, "active_power", results)

    for window in WINDOWS:
        for error in ERRORS:
            assert results[f"{window}_{error}_active_power_value"] == pytest.approx(0.1)
            assert results[f"{window}_{error}_active_power_position"] == [0.5, 1.5]


def test_save_measurement_errors_skips_the_windows_without_a_value():
    compliance_values = _make_saved_errors("active_power")
    compliance_values["after_mae_active_power_value"] = None
    compliance_values["after_mae_active_power_position"] = None
    results = {}

    checks.save_measurement_errors(compliance_values, "active_power", results)

    assert "after_mae_active_power_value" not in results
    assert "after_mae_active_power_position" not in results
    assert results["before_mae_active_power_value"] == pytest.approx(0.1)


def test_save_measurement_errors_ignores_the_absent_windows():
    compliance_values = _make_saved_errors("active_power", windows=("before",))
    results = {}

    checks.save_measurement_errors(compliance_values, "active_power", results)

    assert set(results) == {
        f"before_{error}_active_power_{field}"
        for error in ERRORS
        for field in ("value", "position")
    }


# ---------------------------------------------------------------------------
# Measurement compliance check
# ---------------------------------------------------------------------------


def test_check_measurement_with_every_window_within_the_thresholds():
    compliance_values = _make_window_checks("active_power")
    results = {"compliance": True}

    checks.check_measurement(compliance_values, "active_power", results)

    assert results["voltage_dips_active_power_check"] is True
    assert results["compliance"] is True


def test_check_measurement_aggregates_a_failing_window():
    compliance_values = _make_window_checks("active_power", failing_window="during")
    results = {"compliance": True}

    checks.check_measurement(compliance_values, "active_power", results)

    assert results["during_mae_active_power_check"] is False
    assert results["voltage_dips_active_power_check"] is False
    assert results["compliance"] is False


def test_check_measurement_without_the_window_checks_reports_not_available():
    results = {"compliance": True}

    checks.check_measurement({}, "active_power", results)

    assert results["before_mae_active_power_check"] == "N/A"
    assert results["voltage_dips_active_power_check"] == "N/A"
    assert results["compliance"] is False


def test_check_measurement_ignores_the_windows_without_a_check():
    compliance_values = _make_window_checks("active_power")
    compliance_values["during_mae_active_power_check"] = None
    results = {"compliance": True}

    checks.check_measurement(compliance_values, "active_power", results)

    assert "during_mae_active_power_check" not in results
    assert results["voltage_dips_active_power_check"] is True
    assert results["compliance"] is True


# ---------------------------------------------------------------------------
# Injector voltage guard warnings
# ---------------------------------------------------------------------------


def _terminal_frame(voltages):
    return pd.DataFrame(
        {
            "time": np.linspace(0, 1, len(voltages)),
            "Wind_Turbine_GEN_UPuInjTerminal": voltages,
        }
    )


def test_guard_warnings_with_empty_frames():
    warnings = checks.get_injector_voltage_guard_warnings(pd.DataFrame(), pd.DataFrame())

    assert warnings == []


def test_guard_warnings_with_healthy_voltages():
    warnings = checks.get_injector_voltage_guard_warnings(
        _terminal_frame([0.9, 1.0]), _terminal_frame([0.95, 1.0])
    )

    assert warnings == []


def test_guard_warnings_with_calculated_voltage_below_guard():
    warnings = checks.get_injector_voltage_guard_warnings(
        _terminal_frame([1e-5, 1.0]), _terminal_frame([0.95, 1.0])
    )

    assert len(warnings) == 1
    assert "calculated" in warnings[0]
    assert "InternalNode2" in warnings[0]
    assert "2.0e-04" in warnings[0]
    assert "transformer impedance" in warnings[0]


def test_guard_warnings_with_reference_voltage_below_guard():
    warnings = checks.get_injector_voltage_guard_warnings(
        _terminal_frame([0.9, 1.0]), _terminal_frame([0.0, 1.0])
    )

    assert len(warnings) == 1
    assert "reference" in warnings[0]


def test_guard_warnings_with_both_voltages_below_guard():
    warnings = checks.get_injector_voltage_guard_warnings(
        _terminal_frame([0.0, 1.0]), _terminal_frame([1e-6, 1.0])
    )

    assert len(warnings) == 2
    assert "calculated" in warnings[0]
    assert "reference" in warnings[1]


def test_guard_warnings_at_the_guard_value():
    warnings = checks.get_injector_voltage_guard_warnings(
        _terminal_frame([2e-4, 1.0]), pd.DataFrame()
    )

    assert len(warnings) == 1


def test_guard_warnings_ignores_non_finite_samples():
    warnings = checks.get_injector_voltage_guard_warnings(
        _terminal_frame([np.nan, 0.9]), _terminal_frame([np.inf, 1.0])
    )

    assert warnings == []


def test_guard_warnings_without_terminal_columns():
    curves = pd.DataFrame({"time": [0.0, 1.0], "BusPDR_BUS_Voltage": [0.0, 1.0]})

    warnings = checks.get_injector_voltage_guard_warnings(curves, curves)

    assert warnings == []
