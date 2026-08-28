#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Unit tests for the model validation (ModelValidator) compliance criteria."""

import pandas as pd
import pytest

from dycov.model.parameters import ExclusionWindows
from dycov.validation.model import (
    ModelValidator,
    _check_value_by_threshold,
    _get_column_name,
    _get_measurement_name,
)

MODEL_MODULE = "dycov.validation.model"
COMMON_MODULE = "dycov.validation.common"

# Thresholds used by every check exercised here, kept independent of the user configuration.
THRESHOLDS = {
    "thr_ss_tol": 0.002,
    "thr_reaction_time": 0.10,
    "thr_rise_time": 0.10,
    "thr_settling_time": 0.10,
    "thr_overshoot": 0.15,
    "thr_ramp_time_lag": 0.10,
    "thr_ramp_error": 0.10,
    "thr_final_ss_mae": 0.01,
}


class DummyConfig:
    """Configuration stand-in serving THRESHOLDS, falling back to the requested default."""

    def __init__(self, **overrides):
        self._values = dict(THRESHOLDS, **overrides)

    def get_float(self, section: str, key: str, default: float) -> float:
        return self._values.get(key, default)


class DummyProducer:
    def __init__(self, zone=1):
        self._zone = zone

    def get_zone(self) -> int:
        return self._zone


class DummyCurvesManager:
    """Curves manager stand-in serving in-memory curves and exclusion windows."""

    def __init__(
        self,
        calculated=None,
        reference=None,
        windows=None,
        exclusion_windows=None,
        windows_raise=False,
    ):
        self._curves = {
            "calculated": pd.DataFrame() if calculated is None else calculated,
            "reference": pd.DataFrame() if reference is None else reference,
        }
        self._windows = windows or {}
        self._exclusion_windows = exclusion_windows or ExclusionWindows(0.0, 0.0, 0.0, 0.0)
        self._windows_raise = windows_raise
        self.signal_processing_calls = []

    def get_curves(self, curve: str) -> pd.DataFrame:
        return self._curves[curve]

    def get_curves_by_windows(self, windows: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        if self._windows_raise:
            raise ValueError("no curves available for the requested window")
        return self._windows[windows]

    def get_exclusion_windows(self) -> ExclusionWindows:
        return self._exclusion_windows

    def apply_signal_processing(self, working_path, event_params, tracks_setpoint) -> None:
        self.signal_processing_calls.append((working_path, event_params, tracks_setpoint))


class RecordingLogger:
    """Logger stand-in collecting the emitted warnings."""

    def __init__(self):
        self.warnings = []

    def get_logger(self, name: str):
        return self

    def warning(self, message: str) -> None:
        self.warnings.append(message)


def _make_validator(
    validations=None,
    zone=1,
    curves_manager=None,
    is_field_measurements=False,
):
    return ModelValidator(
        curves_manager=curves_manager or DummyCurvesManager(),
        pcs_bm_name="PCS_RTE-I16z3.GridFreqRamp",
        producer=DummyProducer(zone=zone),
        validations=validations or [],
        is_field_measurements=is_field_measurements,
        pcs_name="PCS_RTE-I16z3",
        bm_name="GridFreqRamp",
    )


def _make_pdr_curves(voltage=None, active_power=None):
    """Full set of PDR measurements; voltage and active power are parametrizable."""
    time = [0.0, 1.0, 2.0, 3.0]
    return pd.DataFrame(
        {
            "time": time,
            "BusPDR_BUS_Voltage": voltage or [1.0, 1.0, 1.0, 1.0],
            "BusPDR_BUS_ActivePower": active_power or [0.5, 0.5, 0.6, 0.6],
            "BusPDR_BUS_ReactivePower": [0.1, 0.1, 0.1, 0.1],
            "BusPDR_BUS_ActiveCurrent": [0.5, 0.5, 0.6, 0.6],
            "BusPDR_BUS_ReactiveCurrent": [0.1, 0.1, 0.1, 0.1],
        }
    )


def _make_window_manager(calculated=None, windows_raise=False):
    """Curves manager whose three windows serve the same pair of curves."""
    calculated = calculated if calculated is not None else _make_pdr_curves()
    reference = _make_pdr_curves()
    windows = {window: (calculated, reference) for window in ("before", "during", "after")}
    return DummyCurvesManager(
        calculated=calculated,
        reference=reference,
        windows=windows,
        windows_raise=windows_raise,
    )


# The ideal frequency ramp goes from 1.0 pu to 1.2 pu over the [0, 2] s event window.
IDEAL_RAMP_FREQUENCY = [1.0, 1.05, 1.10, 1.15, 1.20]
RAMP_EVENT_PARAMS = {
    "start_time": 2.0,
    "duration_time": 2.0,
    "connect_to": "NetworkFrequencyPu",
    "step_value": 0.2,
}


def _make_ramp_curves(frequency):
    time = [0.0, 0.5, 1.0, 1.5, 2.0]
    return pd.DataFrame(
        {
            "time": time,
            "NetworkFrequencyPu": frequency,
            "BusPDR_BUS_Voltage": [1.0, 1.0, 1.0, 1.0, 1.0],
            "BusPDR_BUS_ActivePower": [0.5, 0.5, 0.5, 0.5, 0.7],
            "BusPDR_BUS_ReactivePower": [0.1, 0.1, 0.1, 0.1, 0.1],
            "BusPDR_BUS_ActiveCurrent": [0.5, 0.5, 0.5, 0.5, 0.7],
            "BusPDR_BUS_ReactiveCurrent": [0.1, 0.1, 0.1, 0.1, 0.1],
        }
    )


def _make_ramp_manager(frequency):
    curves = _make_ramp_curves(frequency)
    windows = {window: (curves, curves) for window in ("before", "during", "after")}
    return DummyCurvesManager(calculated=curves, reference=curves, windows=windows)


@pytest.fixture(autouse=True)
def dummy_config(monkeypatch):
    """Serve deterministic thresholds to both the validator and the common helpers."""
    config = DummyConfig()
    monkeypatch.setattr(f"{MODEL_MODULE}.config", config)
    monkeypatch.setattr(f"{COMMON_MODULE}.config", config)
    return config


# ---------------------------------------------------------------------------
# Setpoint name mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "modified_setpoint, expected",
    [
        ("ActivePowerSetpointPu", "P"),
        ("ReactivePowerSetpointPu", "Q"),
        ("VoltageSetpointPu", "V"),
        ("NetworkFrequencyPu", "$\\omega"),
        ("", "Q"),
    ],
)
def test_get_column_name_maps_every_setpoint(modified_setpoint, expected):
    assert _get_column_name(modified_setpoint) == expected


@pytest.mark.parametrize(
    "modified_setpoint, expected",
    [
        ("ActivePowerSetpointPu", "BusPDR_BUS_ActivePower"),
        ("ReactivePowerSetpointPu", "BusPDR_BUS_ReactivePower"),
        ("VoltageSetpointPu", "BusPDR_BUS_Voltage"),
        ("NetworkFrequencyPu", "NetworkFrequencyPu"),
        ("", "BusPDR_BUS_ReactivePower"),
    ],
)
def test_get_measurement_name_maps_every_setpoint(modified_setpoint, expected):
    assert _get_measurement_name(modified_setpoint) == expected


def test_check_value_by_threshold_is_strict():
    assert _check_value_by_threshold(0.001, 0.01) is True
    assert _check_value_by_threshold(0.01, 0.01) is False
    assert _check_value_by_threshold(0.1, 0.01) is False


# ---------------------------------------------------------------------------
# Ideal ramp calculation
# ---------------------------------------------------------------------------


def test_compare_ideal_ramp_computes_both_magnitudes():
    validator = _make_validator(
        validations=["ramp_time_lag", "ramp_error"],
        curves_manager=_make_ramp_manager(IDEAL_RAMP_FREQUENCY),
    )
    results = {}

    validator._ModelValidator__compare_ideal_ramp(
        measurement_name="NetworkFrequencyPu",
        t_event_start=2.0,
        t_event_duration=2.0,
        freq0=1.0,
        freq_peak=0.2,
        results=results,
    )

    # The calculated frequency follows the ideal ramp exactly, so neither magnitude deviates.
    assert results["ramp_time_lag"] == pytest.approx(0.0)
    assert results["ramp_error"] == pytest.approx(0.0)


def test_compare_ideal_ramp_measures_the_deviation_from_the_ideal_ramp():
    validator = _make_validator(
        validations=["ramp_error"],
        curves_manager=_make_ramp_manager([1.0, 1.20, 1.10, 1.15, 1.20]),
    )
    results = {}

    validator._ModelValidator__compare_ideal_ramp(
        measurement_name="NetworkFrequencyPu",
        t_event_start=2.0,
        t_event_duration=2.0,
        freq0=1.0,
        freq_peak=0.2,
        results=results,
    )

    # The second sample sits at 1.20 pu where the ideal ramp is at 1.05 pu.
    assert results["ramp_error"] == pytest.approx(0.15)
    assert "ramp_time_lag" not in results


def test_compare_ideal_ramp_skips_disabled_validations():
    validator = _make_validator(curves_manager=_make_ramp_manager(IDEAL_RAMP_FREQUENCY))
    results = {}

    validator._ModelValidator__compare_ideal_ramp(
        measurement_name="NetworkFrequencyPu",
        t_event_start=2.0,
        t_event_duration=2.0,
        freq0=1.0,
        freq_peak=0.2,
        results=results,
    )

    assert results == {}


# ---------------------------------------------------------------------------
# Ideal ramp compliance check (issue #370)
# ---------------------------------------------------------------------------


def test_check_ramp_below_the_thresholds_is_compliant():
    """Issue #370: both guards asked for the "*_check" keys that __check_ramp itself
    produces instead of the "ramp_time_lag"/"ramp_error" magnitudes it receives, so every
    ramp check fell through to "N/A" and forced compliance False, making I16z3 unpassable.
    """
    validator = _make_validator(validations=["ramp_time_lag", "ramp_error"])
    check_results = {"compliance": True}

    validator._ModelValidator__check_ramp(
        check_results, {"ramp_time_lag": 0.04, "ramp_error": 0.02}
    )

    assert check_results["ramp_time_check"] is True
    assert check_results["ramp_error_check"] is True
    assert check_results["compliance"] is True

    # Magnitudes and thresholds are reported as percentages.
    assert check_results["ramp_time_lag"] == pytest.approx(4.0)
    assert check_results["ramp_time_thr"] == pytest.approx(10.0)
    assert check_results["ramp_error"] == pytest.approx(2.0)
    assert check_results["ramp_error_thr"] == pytest.approx(10.0)


def test_check_ramp_at_the_thresholds_is_compliant():
    validator = _make_validator(validations=["ramp_time_lag", "ramp_error"])
    check_results = {"compliance": True}

    validator._ModelValidator__check_ramp(
        check_results, {"ramp_time_lag": 0.10, "ramp_error": 0.10}
    )

    assert check_results["ramp_time_check"] is True
    assert check_results["ramp_error_check"] is True
    assert check_results["compliance"] is True


def test_check_ramp_above_the_time_lag_threshold_fails():
    validator = _make_validator(validations=["ramp_time_lag", "ramp_error"])
    check_results = {"compliance": True}

    validator._ModelValidator__check_ramp(
        check_results, {"ramp_time_lag": 0.11, "ramp_error": 0.02}
    )

    assert check_results["ramp_time_check"] is False
    assert check_results["ramp_error_check"] is True
    assert check_results["compliance"] is False


def test_check_ramp_above_the_value_error_threshold_fails():
    validator = _make_validator(validations=["ramp_time_lag", "ramp_error"])
    check_results = {"compliance": True}

    validator._ModelValidator__check_ramp(
        check_results, {"ramp_time_lag": 0.04, "ramp_error": 0.5}
    )

    assert check_results["ramp_time_check"] is True
    assert check_results["ramp_error_check"] is False
    assert check_results["compliance"] is False


def test_check_ramp_without_the_magnitudes_reports_not_available():
    validator = _make_validator(validations=["ramp_time_lag", "ramp_error"])
    check_results = {"compliance": True}

    validator._ModelValidator__check_ramp(check_results, {})

    # The validations stay active, but their magnitudes could not be computed.
    assert check_results["ramp_time_check"] == "N/A"
    assert check_results["ramp_error_check"] == "N/A"
    assert check_results["compliance"] is False
    assert "ramp_time_lag" not in check_results
    assert "ramp_error" not in check_results


def test_check_ramp_only_checks_the_enabled_validations():
    validator = _make_validator(validations=["ramp_time_lag"])
    check_results = {"compliance": True}

    validator._ModelValidator__check_ramp(
        check_results, {"ramp_time_lag": 0.04, "ramp_error": 0.5}
    )

    assert check_results["ramp_time_check"] is True
    assert "ramp_error_check" not in check_results
    assert check_results["compliance"] is True


# ---------------------------------------------------------------------------
# Event times calculation
# ---------------------------------------------------------------------------


def _make_step_manager():
    """Calculated active power steps 1 s after the event, the reference one 2 s after."""
    time = [0.0, 1.0, 2.0, 3.0, 4.0]
    calculated = pd.DataFrame({"time": time, "BusPDR_BUS_ActivePower": [0.0, 0.0, 1.0, 1.0, 1.0]})
    reference = pd.DataFrame({"time": time, "BusPDR_BUS_ActivePower": [0.0, 0.0, 0.0, 1.0, 1.0]})
    return DummyCurvesManager(calculated=calculated, reference=reference)


def test_compare_event_times_computes_reaction_and_rise_times():
    validator = _make_validator(
        validations=["reaction_time", "rise_time"], curves_manager=_make_step_manager()
    )
    results = {}

    validator._ModelValidator__compare_event_times(
        measurement_name="BusPDR_BUS_ActivePower",
        start_event=1.0,
        setpoint_variation=0.1,
        results=results,
    )

    assert results["t_event_start"] == 1.0
    assert results["calc_reaction_time"] == pytest.approx(1.0)
    assert results["ref_reaction_time"] == pytest.approx(2.0)
    assert results["calc_reaction_target"] == {"BusPDR_BUS_ActivePower": pytest.approx(0.1)}
    assert results["calc_rise_time"] == pytest.approx(1.0)
    assert results["ref_rise_time"] == pytest.approx(2.0)
    assert results["calc_rise_target"] == {"BusPDR_BUS_ActivePower": pytest.approx(0.9)}


def test_compare_event_times_computes_response_and_settling_times():
    validator = _make_validator(
        validations=["response_time", "settling_time"], curves_manager=_make_step_manager()
    )
    results = {}

    validator._ModelValidator__compare_event_times(
        measurement_name="BusPDR_BUS_ActivePower",
        start_event=1.0,
        setpoint_variation=0.1,
        results=results,
    )

    # The last sample outside the steady-state tube is the one just before the step.
    assert results["calc_response_time"] == pytest.approx(0.0)
    assert results["ref_response_time"] == pytest.approx(1.0)
    assert results["calc_settling_time"] == pytest.approx(0.0)
    assert results["ref_settling_time"] == pytest.approx(1.0)
    assert results["calc_ss_value"] == pytest.approx(0.0)
    assert results["calc_settling_tube"]["BusPDR_BUS_ActivePower"] == pytest.approx(
        [0.9998, 1.0002]
    )


def test_compare_event_times_computes_overshoot():
    time = [0.0, 1.0, 2.0, 3.0]
    curves_manager = DummyCurvesManager(
        calculated=pd.DataFrame({"time": time, "BusPDR_BUS_ActivePower": [0.0, 1.25, 1.0, 1.0]}),
        reference=pd.DataFrame({"time": time, "BusPDR_BUS_ActivePower": [0.0, 1.10, 1.0, 1.0]}),
    )
    validator = _make_validator(validations=["overshoot"], curves_manager=curves_manager)
    results = {}

    validator._ModelValidator__compare_event_times(
        measurement_name="BusPDR_BUS_ActivePower",
        start_event=1.0,
        setpoint_variation=0.1,
        results=results,
    )

    assert results["calc_overshoot"] == pytest.approx(0.25)
    assert results["ref_overshoot"] == pytest.approx(0.10)


def test_compare_event_times_without_validations_only_stores_the_event_start():
    validator = _make_validator(curves_manager=_make_step_manager())
    results = {}

    validator._ModelValidator__compare_event_times(
        measurement_name="BusPDR_BUS_ActivePower",
        start_event=1.0,
        setpoint_variation=0.1,
        results=results,
    )

    assert results == {"t_event_start": 1.0}


def test_active_power_recovery_error_compares_the_p90_instants():
    validator = _make_validator(
        validations=["active_power_recovery"], curves_manager=_make_step_manager()
    )
    results = {}

    validator._ModelValidator__active_power_recovery_error(
        start_event=0.0,
        duration_event=3.0,
        results=results,
    )

    # Both 90% instants are searched from t = 0 + 3/3 = 1 s onwards.
    assert results["t_P90_ref"] == pytest.approx(2.0)
    assert results["t_P90_error"] == pytest.approx(1.0)


def test_active_power_recovery_error_skipped_when_the_validation_is_disabled():
    validator = _make_validator(curves_manager=_make_step_manager())
    results = {}

    validator._ModelValidator__active_power_recovery_error(
        start_event=0.0,
        duration_event=3.0,
        results=results,
    )

    assert results == {}


# ---------------------------------------------------------------------------
# Event times compliance check
# ---------------------------------------------------------------------------


def test_check_times_within_the_thresholds_is_compliant():
    validator = _make_validator(
        validations=["reaction_time", "rise_time", "settling_time", "overshoot"]
    )
    check_results = {"compliance": True}
    compliance_values = {
        "calc_reaction_time": 1.0,
        "ref_reaction_time": 1.05,
        "calc_reaction_target": {"BusPDR_BUS_ActivePower": 0.1},
        "calc_rise_time": 2.0,
        "ref_rise_time": 2.05,
        "calc_rise_target": {"BusPDR_BUS_ActivePower": 0.9},
        "calc_settling_time": 3.0,
        "ref_settling_time": 3.05,
        "calc_settling_tube": {"BusPDR_BUS_ActivePower": [0.99, 1.01]},
        "calc_ss_value": 1.0,
        "calc_overshoot": 0.10,
        "ref_overshoot": 0.105,
    }

    validator._ModelValidator__check_times(check_results, compliance_values)

    assert check_results["reaction_time_check"] is True
    assert check_results["rise_time_check"] is True
    assert check_results["settling_time_check"] is True
    assert check_results["overshoot_check"] is True
    assert check_results["compliance"] is True

    # Thresholds are reported as percentages, together with the relative error.
    assert check_results["reaction_time_thr"] == pytest.approx(10.0)
    assert check_results["reaction_time_error"] == pytest.approx(4.7619, rel=1e-4)
    assert check_results["calc_reaction_time"] == 1.0
    assert check_results["ref_reaction_time"] == 1.05


def test_check_times_outside_the_reaction_time_threshold_fails():
    validator = _make_validator(validations=["reaction_time"])
    check_results = {"compliance": True}
    compliance_values = {
        "calc_reaction_time": 2.0,
        "ref_reaction_time": 1.0,
        "calc_reaction_target": {"BusPDR_BUS_ActivePower": 0.1},
    }

    validator._ModelValidator__check_times(check_results, compliance_values)

    assert check_results["reaction_time_check"] is False
    assert check_results["reaction_time_error"] == pytest.approx(100.0)
    assert check_results["compliance"] is False


@pytest.mark.parametrize(
    "validation, check_key",
    [
        ("reaction_time", "reaction_time_check"),
        ("rise_time", "rise_time_check"),
        ("settling_time", "settling_time_check"),
        ("overshoot", "overshoot_check"),
    ],
)
def test_check_times_without_the_magnitudes_reports_not_available(validation, check_key):
    validator = _make_validator(validations=[validation])
    check_results = {"compliance": True}

    validator._ModelValidator__check_times(check_results, {})

    assert check_results[check_key] == "N/A"
    assert check_results["compliance"] is False


# ---------------------------------------------------------------------------
# Mean absolute error calculation
# ---------------------------------------------------------------------------


def _make_mae_curves(measurement_name):
    """The calculated curve settles 0.02 pu above the reference from the third sample on."""
    time = [0.0, 1.0, 2.0, 3.0]
    calculated = pd.DataFrame({"time": time, measurement_name: [1.0, 1.0, 1.02, 1.02]})
    reference = pd.DataFrame({"time": time, measurement_name: [1.0, 1.0, 1.0, 1.0]})
    return calculated, reference


def test_calculate_mean_absolute_error_for_voltage():
    validator = _make_validator(validations=["mean_absolute_error_voltage"])
    curves = _make_mae_curves("BusPDR_BUS_Voltage")
    results = {}

    validator._ModelValidator__calculate_mean_absolute_error(
        "BusPDR_BUS_Voltage", curves, 0.1, results
    )

    # Averaged over the three samples after the calculated settling instant.
    assert results["mae_voltage_1P"] == pytest.approx(0.04 / 3)
    assert results["ss_error_voltage_1P"] == pytest.approx(0.04 / 3)
    assert results["mae_voltage_1P_stabilized"] is True


def test_calculate_mean_absolute_error_for_power_covers_both_components():
    validator = _make_validator(validations=["mean_absolute_error_power_1P"])
    calculated, reference = _make_mae_curves("BusPDR_BUS_ActivePower")
    calculated["BusPDR_BUS_ReactivePower"] = [0.1, 0.1, 0.1, 0.1]
    reference["BusPDR_BUS_ReactivePower"] = [0.1, 0.1, 0.1, 0.1]
    results = {}

    validator._ModelValidator__calculate_mean_absolute_error(
        "BusPDR_BUS_ActivePower", (calculated, reference), 0.1, results
    )

    assert results["mae_active_power_1P"] == pytest.approx(0.04 / 3)
    assert results["ss_error_active_power_1P"] == pytest.approx(0.04 / 3)
    assert results["mae_reactive_power_1P"] == pytest.approx(0.0)
    assert results["ss_error_reactive_power_1P"] == pytest.approx(0.0)
    assert results["mae_active_power_1P_stabilized"] is True
    assert results["mae_reactive_power_1P_stabilized"] is True


def test_calculate_mean_absolute_error_for_injection_covers_both_components():
    validator = _make_validator(validations=["mean_absolute_error_injection_1P"])
    calculated, reference = _make_mae_curves("BusPDR_BUS_ActiveCurrent")
    calculated["BusPDR_BUS_ReactiveCurrent"] = [0.1, 0.1, 0.1, 0.1]
    reference["BusPDR_BUS_ReactiveCurrent"] = [0.1, 0.1, 0.1, 0.1]
    results = {}

    validator._ModelValidator__calculate_mean_absolute_error(
        "BusPDR_BUS_ActiveCurrent", (calculated, reference), 0.1, results
    )

    assert results["mae_active_current_1P"] == pytest.approx(0.04 / 3)
    assert results["ss_error_active_current_1P"] == pytest.approx(0.04 / 3)
    assert results["mae_reactive_current_1P"] == pytest.approx(0.0)
    assert results["ss_error_reactive_current_1P"] == pytest.approx(0.0)


def test_calculate_mean_absolute_error_reports_a_curve_still_moving_as_not_stabilized():
    validator = _make_validator(validations=["mean_absolute_error_voltage"])
    calculated, reference = _make_mae_curves("BusPDR_BUS_Voltage")
    calculated["BusPDR_BUS_Voltage"] = [1.0, 1.0, 1.02, 1.06]
    results = {}

    validator._ModelValidator__calculate_mean_absolute_error(
        "BusPDR_BUS_Voltage", (calculated, reference), 0.1, results
    )

    assert results["mae_voltage_1P_stabilized"] is False


def test_calculate_mean_absolute_error_reports_not_stabilized_when_stability_is_undecidable(
    monkeypatch,
):
    validator = _make_validator(validations=["mean_absolute_error_voltage"])
    curves = _make_mae_curves("BusPDR_BUS_Voltage")

    def _raise(time_curve, curve, thr_ss_tol):
        raise ValueError("the curve values and its time series have different length")

    monkeypatch.setattr(f"{COMMON_MODULE}.is_stable", _raise)
    results = {}

    validator._ModelValidator__calculate_mean_absolute_error(
        "BusPDR_BUS_Voltage", curves, 0.1, results
    )

    assert results["mae_voltage_1P_stabilized"] is False


# ---------------------------------------------------------------------------
# Mean absolute error compliance check
# ---------------------------------------------------------------------------


def test_check_mae_below_the_threshold_is_compliant():
    validator = _make_validator(validations=["mean_absolute_error_voltage"])
    check_results = {"compliance": True, "stabilized": True}
    compliance_values = {
        "mae_voltage_1P": 0.005,
        "ss_error_voltage_1P": 0.001,
        "mae_voltage_1P_stabilized": True,
    }

    validator._ModelValidator__check_mae(check_results, compliance_values)

    assert check_results["mae_voltage_1P_check"] is True
    assert check_results["mae_voltage_1P"] == pytest.approx(0.005)
    assert check_results["ss_error_voltage_1P"] == pytest.approx(0.001)
    assert check_results["compliance"] is True
    assert check_results["stabilized"] is True


def test_check_mae_above_the_threshold_fails():
    validator = _make_validator(validations=["mean_absolute_error_voltage"])
    check_results = {"compliance": True, "stabilized": True}
    compliance_values = {
        "mae_voltage_1P": 0.05,
        "ss_error_voltage_1P": 0.001,
        "mae_voltage_1P_stabilized": True,
    }

    validator._ModelValidator__check_mae(check_results, compliance_values)

    assert check_results["mae_voltage_1P_check"] is False
    assert check_results["compliance"] is False
    assert check_results["stabilized"] is True


def test_check_mae_without_stabilization_fails():
    validator = _make_validator(validations=["mean_absolute_error_voltage"])
    check_results = {"compliance": True, "stabilized": True}
    compliance_values = {
        "mae_voltage_1P": 0.005,
        "ss_error_voltage_1P": 0.001,
        "mae_voltage_1P_stabilized": False,
    }

    validator._ModelValidator__check_mae(check_results, compliance_values)

    assert check_results["mae_voltage_1P_check"] is True
    assert check_results["stabilized"] is False
    assert check_results["compliance"] is False


def test_check_mae_for_power_checks_both_components():
    validator = _make_validator(validations=["mean_absolute_error_power_1P"])
    check_results = {"compliance": True, "stabilized": True}
    compliance_values = {
        "mae_active_power_1P": 0.005,
        "ss_error_active_power_1P": 0.001,
        "mae_active_power_1P_stabilized": True,
        "mae_reactive_power_1P": 0.05,
        "ss_error_reactive_power_1P": 0.002,
        "mae_reactive_power_1P_stabilized": True,
    }

    validator._ModelValidator__check_mae(check_results, compliance_values)

    assert check_results["mae_active_power_1P_check"] is True
    assert check_results["mae_reactive_power_1P_check"] is False
    assert check_results["compliance"] is False


def test_check_mae_for_injection_checks_both_components():
    validator = _make_validator(validations=["mean_absolute_error_injection_1P"])
    check_results = {"compliance": True, "stabilized": True}
    compliance_values = {
        "mae_active_current_1P": 0.005,
        "ss_error_active_current_1P": 0.001,
        "mae_active_current_1P_stabilized": True,
        "mae_reactive_current_1P": 0.005,
        "ss_error_reactive_current_1P": 0.002,
        "mae_reactive_current_1P_stabilized": True,
    }

    validator._ModelValidator__check_mae(check_results, compliance_values)

    assert check_results["mae_active_current_1P_check"] is True
    assert check_results["mae_reactive_current_1P_check"] is True
    assert check_results["compliance"] is True


@pytest.mark.parametrize(
    "validation, check_keys",
    [
        ("mean_absolute_error_voltage", ["mae_voltage_1P_check"]),
        (
            "mean_absolute_error_power_1P",
            ["mae_active_power_1P_check", "mae_reactive_power_1P_check"],
        ),
        (
            "mean_absolute_error_injection_1P",
            ["mae_active_current_1P_check", "mae_reactive_current_1P_check"],
        ),
    ],
)
def test_check_mae_without_the_magnitudes_reports_not_available(validation, check_keys):
    validator = _make_validator(validations=[validation])
    check_results = {"compliance": True, "stabilized": True}

    validator._ModelValidator__check_mae(check_results, {})

    for check_key in check_keys:
        assert check_results[check_key] == "N/A"
        assert check_results[check_key.replace("_check", "_stabilized")] == "N/A"
    assert check_results["stabilized"] is False
    assert check_results["compliance"] is False


# ---------------------------------------------------------------------------
# Calculation orchestration
# ---------------------------------------------------------------------------


def test_calculate_populates_the_window_errors_and_the_validity_flag():
    validator = _make_validator(curves_manager=_make_window_manager())

    results = validator._ModelValidator__calculate(
        zone=1,
        start_event=1.0,
        duration_event=1.0,
        freq0=1.0,
        freq_peak=0.0,
        modified_setpoint="ActivePowerSetpointPu",
        setpoint_variation=0.1,
    )

    # The calculated and reference curves are identical, so every window error is zero.
    assert results["is_invalid_test"] is False
    assert results["before"]["BusPDR_BUS_ActivePower"]["mae"] == pytest.approx(0.0)
    assert results["after"]["BusPDR_BUS_Voltage"]["mxe"] == pytest.approx(0.0)
    # Comparing numpy magnitudes against the thresholds yields numpy booleans.
    assert bool(results["before_mae_active_power_check"]) is True


def test_calculate_normalizes_a_zero_setpoint_variation():
    calculated = _make_pdr_curves(active_power=[0.5, 0.5, 0.7, 0.7])
    validator = _make_validator(curves_manager=_make_window_manager(calculated=calculated))

    results = validator._ModelValidator__calculate(
        zone=1,
        start_event=1.0,
        duration_event=1.0,
        freq0=1.0,
        freq_peak=0.0,
        modified_setpoint="ActivePowerSetpointPu",
        setpoint_variation=0.0,
    )

    # A null setpoint variation falls back to a unit step magnitude, so the error is not scaled.
    assert results["before"]["BusPDR_BUS_ActivePower"]["mxe"] == pytest.approx(0.1)


def test_calculate_without_curves_marks_the_test_as_not_available(monkeypatch):
    logger = RecordingLogger()
    monkeypatch.setattr(f"{MODEL_MODULE}.dycov_logging", logger)
    validator = _make_validator(curves_manager=_make_window_manager(windows_raise=True))

    results = validator._ModelValidator__calculate(
        zone=1,
        start_event=1.0,
        duration_event=1.0,
        freq0=1.0,
        freq_peak=0.0,
        modified_setpoint="ActivePowerSetpointPu",
        setpoint_variation=0.1,
    )

    assert results["is_invalid_test"] == "N/A"
    assert results["t_event_start"] == 1.0
    assert len(logger.warnings) == 1


# ---------------------------------------------------------------------------
# Check orchestration
# ---------------------------------------------------------------------------


def _make_compliance_values(**extra):
    values = {"t_event_start": 1.0, "is_invalid_test": False}
    values.update(extra)
    return values


def test_check_creates_the_base_results():
    validator = _make_validator()
    compliance_values = _make_compliance_values()

    check_results = validator._ModelValidator__check(
        compliance_values, modified_setpoint="ActivePowerSetpointPu"
    )

    assert check_results["compliance"] is True
    assert check_results["stabilized"] is True
    assert check_results["sim_t_event_start"] == 1.0
    assert check_results["is_invalid_test"] is False
    assert check_results["curves_error"] is compliance_values


def test_check_active_power_recovery_within_the_threshold_is_compliant():
    validator = _make_validator(validations=["active_power_recovery"])
    compliance_values = _make_compliance_values(t_P90_error=0.01, t_P90_ref=1.0)

    check_results = validator._ModelValidator__check(
        compliance_values, modified_setpoint="ActivePowerSetpointPu"
    )

    # The threshold is min(10% of the reference instant, 100 ms).
    assert check_results["t_P90_threshold"] == pytest.approx(0.1)
    assert check_results["t_P90_error"] == pytest.approx(0.01)
    assert check_results["t_P90_check"] is True
    assert check_results["compliance"] is True


def test_check_active_power_recovery_above_the_threshold_fails():
    validator = _make_validator(validations=["active_power_recovery"])
    compliance_values = _make_compliance_values(t_P90_error=0.5, t_P90_ref=1.0)

    check_results = validator._ModelValidator__check(
        compliance_values, modified_setpoint="ActivePowerSetpointPu"
    )

    assert check_results["t_P90_check"] is False
    assert check_results["compliance"] is False


def test_check_active_power_recovery_without_a_reference_instant_is_compliant():
    validator = _make_validator(validations=["active_power_recovery"])
    compliance_values = _make_compliance_values(t_P90_error=0.5, t_P90_ref=0.0)

    check_results = validator._ModelValidator__check(
        compliance_values, modified_setpoint="ActivePowerSetpointPu"
    )

    assert check_results["t_P90_check"] is True
    assert check_results["compliance"] is True


def _make_window_checks(measurement, failing_window=None):
    return {
        f"{window}_{error}_{measurement}_check": window != failing_window
        for window in ("before", "during", "after")
        for error in ("mae", "me", "mxe")
    }


@pytest.mark.parametrize(
    "measurement", ["active_power", "reactive_power", "active_current", "reactive_current"]
)
def test_check_voltage_dips_within_the_thresholds_is_compliant(measurement):
    validator = _make_validator(validations=[f"voltage_dips_{measurement}"])
    compliance_values = _make_compliance_values(**_make_window_checks(measurement))

    check_results = validator._ModelValidator__check(
        compliance_values, modified_setpoint="ActivePowerSetpointPu"
    )

    assert check_results[f"voltage_dips_{measurement}_check"] is True
    assert check_results["compliance"] is True


@pytest.mark.parametrize(
    "measurement", ["active_power", "reactive_power", "active_current", "reactive_current"]
)
def test_check_voltage_dips_aggregates_a_failing_window(measurement):
    validator = _make_validator(validations=[f"voltage_dips_{measurement}"])
    compliance_values = _make_compliance_values(
        **_make_window_checks(measurement, failing_window="during")
    )

    check_results = validator._ModelValidator__check(
        compliance_values, modified_setpoint="ActivePowerSetpointPu"
    )

    assert check_results[f"voltage_dips_{measurement}_check"] is False
    assert check_results["compliance"] is False


@pytest.mark.parametrize(
    "measurement", ["active_power", "reactive_power", "active_current", "reactive_current"]
)
def test_check_voltage_dips_without_the_window_checks_reports_not_available(measurement):
    validator = _make_validator(validations=[f"voltage_dips_{measurement}"])

    check_results = validator._ModelValidator__check(
        _make_compliance_values(), modified_setpoint="ActivePowerSetpointPu"
    )

    assert check_results[f"voltage_dips_{measurement}_check"] == "N/A"
    assert check_results[f"before_mae_{measurement}_check"] == "N/A"
    assert check_results["compliance"] is False


def test_check_setpoint_tracking_names_every_tracked_magnitude():
    validator = _make_validator(
        validations=[
            "setpoint_tracking_controlled_magnitude",
            "setpoint_tracking_active_power",
            "setpoint_tracking_reactive_power",
        ]
    )
    window_errors = {
        "BusPDR_BUS_Voltage": {"mae": 0.001, "me": 0.001, "mxe": 0.001},
        "BusPDR_BUS_ActivePower": {"mae": 0.001, "me": 0.001, "mxe": 0.001},
        "BusPDR_BUS_ReactivePower": {"mae": 0.001, "me": 0.001, "mxe": 0.001},
    }
    compliance_values = _make_compliance_values(
        before=window_errors, during=window_errors, after=window_errors
    )

    check_results = validator._ModelValidator__check(
        compliance_values, modified_setpoint="VoltageSetpointPu"
    )

    assert check_results["setpoint_tracking_controlled_magnitude_name"] == "V"
    assert check_results["setpoint_tracking_active_power_name"] == "P"
    assert check_results["setpoint_tracking_reactive_power_name"] == "Q"
    assert check_results["setpoint_tracking_controlled_magnitude_check"] is True
    assert check_results["compliance"] is True


# ---------------------------------------------------------------------------
# Validation orchestration
# ---------------------------------------------------------------------------


def test_validate_a_compliant_frequency_ramp(tmp_path):
    """Issue #370: the GridFreqRamp operating condition of PCS_RTE-I16z3 must be able to
    pass when the simulated frequency follows the ideal ramp.
    """
    curves_manager = _make_ramp_manager(IDEAL_RAMP_FREQUENCY)
    validator = _make_validator(
        validations=["ramp_time_lag", "ramp_error"], zone=3, curves_manager=curves_manager
    )

    results = validator.validate("GridFreqRamp", tmp_path, "outputs", RAMP_EVENT_PARAMS)

    assert bool(results["ramp_time_check"]) is True
    assert bool(results["ramp_error_check"]) is True
    assert bool(results["compliance"]) is True
    assert results["sim_t_event_start"] == 2.0
    assert curves_manager.signal_processing_calls == [(tmp_path, RAMP_EVENT_PARAMS, False)]


def test_validate_a_frequency_ramp_outside_the_value_error_threshold(tmp_path):
    validator = _make_validator(
        validations=["ramp_time_lag", "ramp_error"],
        zone=3,
        curves_manager=_make_ramp_manager([1.0, 1.20, 1.10, 1.15, 1.20]),
    )

    results = validator.validate("GridFreqRamp", tmp_path, "outputs", RAMP_EVENT_PARAMS)

    assert results["ramp_error"] == pytest.approx(15.0)
    assert bool(results["ramp_error_check"]) is False
    assert bool(results["compliance"]) is False


def test_validate_exposes_the_curves_and_the_exclusion_windows(tmp_path):
    curves_manager = _make_window_manager()
    curves_manager._exclusion_windows = ExclusionWindows(1.0, 1.02, 2.0, 2.06)
    validator = _make_validator(zone=3, curves_manager=curves_manager)
    event_params = {
        "start_time": 1.0,
        "duration_time": 1.0,
        "connect_to": "ActivePowerSetpointPu",
        "step_value": 0.1,
    }

    results = validator.validate("oc", tmp_path, "outputs", event_params)

    assert results["event_exclusion_window_start"] == 1.0
    assert results["event_exclusion_window_end"] == 1.02
    assert results["clear_exclusion_window_start"] == 2.0
    assert results["clear_exclusion_window_end"] == 2.06
    assert results["curves"] is curves_manager.get_curves("calculated")
    assert results["reference_curves"] is curves_manager.get_curves("reference")
    assert "incomplete_curves" not in results


def test_validate_without_clear_exclusion_window_omits_it(tmp_path):
    validator = _make_validator(zone=3, curves_manager=_make_window_manager())
    event_params = {
        "start_time": 1.0,
        "duration_time": 1.0,
        "connect_to": "ActivePowerSetpointPu",
        "step_value": 0.1,
    }

    results = validator.validate("oc", tmp_path, "outputs", event_params)

    assert "clear_exclusion_window_start" not in results
    assert "clear_exclusion_window_end" not in results


def test_validate_without_reference_curves_marks_the_results_as_incomplete(tmp_path):
    curves_manager = _make_window_manager()
    curves_manager._curves["reference"] = pd.DataFrame()
    validator = _make_validator(zone=3, curves_manager=curves_manager)
    event_params = {
        "start_time": 1.0,
        "duration_time": 1.0,
        "connect_to": "ActivePowerSetpointPu",
        "step_value": 0.1,
    }

    results = validator.validate("oc", tmp_path, "outputs", event_params, has_reference=False)

    assert results["incomplete_curves"] is True
    assert "reference_curves" not in results


def test_validate_reports_the_setpoint_tracking_flag_to_the_signal_processing(tmp_path):
    curves_manager = _make_window_manager()
    validator = _make_validator(
        validations=["setpoint_tracking_controlled_magnitude"],
        zone=3,
        curves_manager=curves_manager,
    )
    event_params = {
        "start_time": 1.0,
        "duration_time": 1.0,
        "connect_to": "ActivePowerSetpointPu",
        "step_value": 0.1,
    }

    validator.validate("oc", tmp_path, "outputs", event_params)

    assert curves_manager.signal_processing_calls == [(tmp_path, event_params, True)]


# ---------------------------------------------------------------------------
# Validation orchestration - injector voltage guard warnings
# ---------------------------------------------------------------------------


def _make_guard_manager(injector_voltage):
    calculated = _make_pdr_curves()
    calculated["WT_GEN_UPuInjTerminal"] = injector_voltage
    return _make_window_manager(calculated=calculated)


GUARD_EVENT_PARAMS = {
    "start_time": 1.0,
    "duration_time": 1.0,
    "connect_to": "ActivePowerSetpointPu",
    "step_value": 0.1,
}


def test_validate_zone1_warns_when_the_injector_voltage_falls_below_the_guard(
    monkeypatch, tmp_path
):
    logger = RecordingLogger()
    monkeypatch.setattr(f"{MODEL_MODULE}.dycov_logging", logger)
    validator = _make_validator(zone=1, curves_manager=_make_guard_manager([1e-5, 1.0, 1.0, 1.0]))

    results = validator.validate("oc", tmp_path, "outputs", GUARD_EVENT_PARAMS)

    assert len(results["warnings"]) == 1
    assert "InternalNode2" in results["warnings"][0]
    assert "calculated" in results["warnings"][0]
    assert logger.warnings == results["warnings"]


def test_validate_zone1_without_a_guard_violation_reports_no_warnings(tmp_path):
    validator = _make_validator(zone=1, curves_manager=_make_guard_manager([0.9, 1.0, 1.0, 1.0]))

    results = validator.validate("oc", tmp_path, "outputs", GUARD_EVENT_PARAMS)

    assert results["warnings"] == []


def test_validate_zone3_does_not_report_guard_warnings(tmp_path):
    validator = _make_validator(zone=3, curves_manager=_make_guard_manager([1e-5, 1.0, 1.0, 1.0]))

    results = validator.validate("oc", tmp_path, "outputs", GUARD_EVENT_PARAMS)

    assert "warnings" not in results


# ---------------------------------------------------------------------------
# Required measurements
# ---------------------------------------------------------------------------


def test_get_measurement_names_in_zone1_excludes_the_network_frequency():
    validator = _make_validator(zone=1)

    names = validator.get_measurement_names()

    assert names == [
        "BusPDR_BUS_ActivePower",
        "BusPDR_BUS_ReactivePower",
        "BusPDR_BUS_ActiveCurrent",
        "BusPDR_BUS_ReactiveCurrent",
        "BusPDR_BUS_Voltage",
    ]


def test_get_measurement_names_in_zone3_includes_the_network_frequency():
    validator = _make_validator(zone=3)

    names = validator.get_measurement_names()

    assert names == [
        "BusPDR_BUS_ActivePower",
        "BusPDR_BUS_ReactivePower",
        "BusPDR_BUS_ActiveCurrent",
        "BusPDR_BUS_ReactiveCurrent",
        "BusPDR_BUS_Voltage",
        "NetworkFrequencyPu",
    ]
