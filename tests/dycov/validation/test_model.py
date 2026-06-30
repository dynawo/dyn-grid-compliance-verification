#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

from dycov.validation.common import get_ss_tolerance
from dycov.validation.model import (
    ModelValidator,
    _check_value_by_threshold,
    _get_column_name,
    _get_measurement_name,
)


def _make_validator(validations=None):
    return ModelValidator(
        curves_manager=Mock(),
        pcs_bm_name="test",
        producer=Mock(),
        validations=validations or [],
        is_field_measurements=False,
        pcs_name="test",
        bm_name="test",
    )


# =========================
# Helpers
# =========================

def test_zero_setpoint_variation():
    assert get_ss_tolerance(0.0) == 0.005


def test_ss_tolerance():
    assert get_ss_tolerance(0.1) == 0.0005


def test_check_value_by_threshold():
    assert _check_value_by_threshold(0.001, 0.01) is True
    assert _check_value_by_threshold(0.1, 0.01) is False


def test_get_column_name():
    assert _get_column_name("ActivePowerSetpointPu") == "P"
    assert _get_column_name("ReactivePowerSetpointPu") == "Q"
    assert _get_column_name("VoltageSetpointPu") == "V"
    assert _get_column_name("NetworkFrequencyPu") == "$\\omega"
    assert _get_column_name("") == "Q"


def test_get_measurement_name():
    assert _get_measurement_name("ActivePowerSetpointPu") == "BusPDR_BUS_ActivePower"
    assert _get_measurement_name("ReactivePowerSetpointPu") == "BusPDR_BUS_ReactivePower"
    assert _get_measurement_name("VoltageSetpointPu") == "BusPDR_BUS_Voltage"
    assert _get_measurement_name("NetworkFrequencyPu") == "NetworkFrequencyPu"
    assert _get_measurement_name("") == "BusPDR_BUS_ReactivePower"


# =========================
# Calculation (ModelValidator)
# =========================

def test_calculate_executes():
    validator = _make_validator()

    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])
    validator._get_reference_curve_by_name = Mock(return_value=[0, 1, 2])
    validator._get_curves_by_windows = Mock(
        return_value=(
            pd.DataFrame({
                "time": [0, 1, 2],
                "BusPDR_BUS_Voltage": [1, 1, 1],
                "BusPDR_BUS_ActivePower": [1, 1, 1],
                "BusPDR_BUS_ReactivePower": [1, 1, 1],
                "BusPDR_BUS_ActiveCurrent": [1, 1, 1],
                "BusPDR_BUS_ReactiveCurrent": [1, 1, 1],
            }),
            pd.DataFrame({
                "time": [0, 1, 2],
                "BusPDR_BUS_Voltage": [1, 1, 1],
                "BusPDR_BUS_ActivePower": [1, 1, 1],
                "BusPDR_BUS_ReactivePower": [1, 1, 1],
                "BusPDR_BUS_ActiveCurrent": [1, 1, 1],
                "BusPDR_BUS_ReactiveCurrent": [1, 1, 1],
            }),
        )
    )

    import dycov.validation.common as common
    common.is_invalid_test = Mock(return_value=False)
    common.get_reached_time = Mock(return_value=(1.0, 1.0))
    common.get_response_time = Mock(return_value=1.0)
    common.get_settling_time = Mock(return_value=(1.0, 0, 0, 0, 1.0))
    common.get_overshoot = Mock(return_value=0.1)
    common.mean_absolute_error = Mock(return_value=0.01)

    with patch("dycov.validation.model.calculate_errors", return_value={}), \
         patch("dycov.validation.model.calculate_curves_errors"):

        res = validator._ModelValidator__calculate(
            zone=1,
            start_event=0.0,
            duration_event=1.0,
            freq0=1.0,
            freq_peak=0.0,
            modified_setpoint="ActivePowerSetpointPu",
            setpoint_variation=0.1,
        )

    assert isinstance(res, dict)


# =========================
# Check (ModelValidator)
# =========================

def test_check_executes():
    validator = _make_validator()

    compliance_values = {
        "t_event_start": 0.0,
        "is_invalid_test": False,
    }

    with patch("dycov.validation.model.save_measurement_errors"), \
         patch("dycov.validation.model.check_measurement"), \
         patch("dycov.validation.model.complete_setpoint_tracking"):

        res = validator._ModelValidator__check(
            compliance_values,
            modified_setpoint="ActivePowerSetpointPu",
        )

    assert isinstance(res, dict)


def test_check_times_executes():
    validator = _make_validator(validations=["reaction_time"])

    results = {"compliance": True}
    compliance_values = {
        "calc_reaction_time": 1.0,
        "ref_reaction_time": 1.0,
        "calc_reaction_target": {"x": 1.0},
    }

    import dycov.validation.common as common
    common.check_time = Mock(return_value=(0.0, True))

    validator._ModelValidator__check_times(results, compliance_values)

    assert "reaction_time_check" in results


def test_check_ramp_executes():
    validator = _make_validator(validations=["ramp_time_lag"])

    results = {"compliance": True}
    compliance_values = {"ramp_time_lag": 0.05}

    validator._ModelValidator__check_ramp(results, compliance_values)

    assert "ramp_time_check" in results


def test_check_mae_executes():
    validator = _make_validator(validations=["mean_absolute_error_voltage"])

    results = {"compliance": True, "stabilized": True}
    compliance_values = {
        "mae_voltage_1P": 0.005,
        "ss_error_voltage_1P": 0.001,
        "mae_voltage_1P_stabilized": True,
    }

    validator._ModelValidator__check_mae(results, compliance_values)

    assert "mae_voltage_1P_check" in results


# =========================
# Validate (orchestration)
# =========================

def test_validate_executes():
    producer = Mock()
    producer.get_zone = Mock(return_value=1)

    validator = ModelValidator(
        curves_manager=Mock(),
        pcs_bm_name="test",
        producer=producer,
        validations=[],
        is_field_measurements=False,
        pcs_name="test",
        bm_name="test",
    )

    validator._curves_manager.apply_signal_processing = Mock()
    validator._get_calculated_curves = Mock(return_value=pd.DataFrame())
    validator._get_reference_curves = Mock(return_value=pd.DataFrame())
    validator._get_exclusion_windows = Mock(
        return_value=Mock(event_start=0.0, event_end=1.0, clear_start=0.0, clear_end=0.0)
    )

    with patch.object(validator, "_ModelValidator__calculate", return_value={
        "t_event_start": 0.0,
        "is_invalid_test": False
    }), patch.object(validator, "_ModelValidator__check", return_value={"compliance": True}):

        res = validator.validate(
            "oc",
            Path("/tmp"),
            "out",
            {
                "start_time": 0.0,
                "duration_time": 1.0,
                "connect_to": "ActivePowerSetpointPu",
                "step_value": 0.1,
            },
            has_reference=True,
        )

    assert res["compliance"] is True


# =========================
# MAE calculation (heavy block)
# =========================

def test_calculate_mean_absolute_error_executes():
    validator = _make_validator(validations=["mean_absolute_error_voltage"])

    df_calc = pd.DataFrame({
        "time": [0, 1, 2, 3],
        "BusPDR_BUS_Voltage": [1.0, 1.0, 1.0, 1.0],
    })

    df_ref = pd.DataFrame({
        "time": [0, 1, 2, 3],
        "BusPDR_BUS_Voltage": [1.0, 1.0, 1.0, 1.0],
    })

    import dycov.validation.common as common

    common.get_settling_time = Mock(return_value=(1.0, 1, 0, 0, 1.0))
    common.mean_absolute_error = Mock(return_value=0.01)
    common.is_stable = Mock(return_value=(True, 1))

    results = {}

    validator._ModelValidator__calculate_mean_absolute_error(
        "BusPDR_BUS_Voltage",
        (df_calc, df_ref),
        0.1,
        results,
    )

    assert "mae_voltage_1P" in results


# =========================
# MAE extended branches
# =========================

def test_calculate_mean_absolute_error_power_branches():
    validator = _make_validator(validations=["mean_absolute_error_power_1P"])

    df_calc = pd.DataFrame({
        "time": [0, 1, 2, 3],
        "BusPDR_BUS_ActivePower": [1, 1, 1, 1],
        "BusPDR_BUS_ReactivePower": [1, 1, 1, 1],
    })

    df_ref = pd.DataFrame({
        "time": [0, 1, 2, 3],
        "BusPDR_BUS_ActivePower": [1, 1, 1, 1],
        "BusPDR_BUS_ReactivePower": [1, 1, 1, 1],
    })

    import dycov.validation.common as common

    common.get_settling_time = Mock(return_value=(1.0, 1, 0, 0, 1.0))
    common.mean_absolute_error = Mock(return_value=0.01)
    common.is_stable = Mock(return_value=(True, 1))

    results = {}

    validator._ModelValidator__calculate_mean_absolute_error(
        "BusPDR_BUS_ActivePower",
        (df_calc, df_ref),
        0.1,
        results,
    )

    assert "mae_active_power_1P" in results
    assert "mae_reactive_power_1P" in results


def test_calculate_mean_absolute_error_injection_branches():
    validator = _make_validator(validations=["mean_absolute_error_injection_1P"])

    df_calc = pd.DataFrame({
        "time": [0, 1, 2, 3],
        "BusPDR_BUS_ActiveCurrent": [1, 1, 1, 1],
        "BusPDR_BUS_ReactiveCurrent": [1, 1, 1, 1],
    })

    df_ref = pd.DataFrame({
        "time": [0, 1, 2, 3],
        "BusPDR_BUS_ActiveCurrent": [1, 1, 1, 1],
        "BusPDR_BUS_ReactiveCurrent": [1, 1, 1, 1],
    })

    import dycov.validation.common as common

    common.get_settling_time = Mock(return_value=(1.0, 1, 0, 0, 1.0))
    common.mean_absolute_error = Mock(return_value=0.01)
    common.is_stable = Mock(return_value=(True, 1))

    results = {}

    validator._ModelValidator__calculate_mean_absolute_error(
        "BusPDR_BUS_ActiveCurrent",
        (df_calc, df_ref),
        0.1,
        results,
    )

    assert "mae_active_current_1P" in results
    assert "mae_reactive_current_1P" in results


# =========================
# Calculation - edge branches
# =========================

def test_calculate_handles_value_error():
    validator = _make_validator()

    validator._get_curves_by_windows = Mock(side_effect=ValueError)
    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])

    res = validator._ModelValidator__calculate(
        zone=1,
        start_event=0.0,
        duration_event=1.0,
        freq0=1.0,
        freq_peak=0.0,
        modified_setpoint="ActivePowerSetpointPu",
        setpoint_variation=0.1,
    )

    assert res["is_invalid_test"] == "N/A"
    assert res["t_event_start"] == 0.0


# =========================
# Check - advanced branches
# =========================

def test_check_active_power_recovery_branch():
    validator = _make_validator(validations=["active_power_recovery"])

    compliance_values = {
        "t_event_start": 0.0,
        "is_invalid_test": False,
        "t_P90_error": 0.01,
        "t_P90_ref": 1.0,
    }

    with patch("dycov.validation.model.save_measurement_errors"), \
         patch("dycov.validation.model.check_measurement"), \
         patch("dycov.validation.model.complete_setpoint_tracking"):

        res = validator._ModelValidator__check(
            compliance_values,
            "ActivePowerSetpointPu",
        )

    assert "t_P90_check" in res


# =========================
# Check - setpoint tracking branches
# =========================

def test_check_setpoint_tracking_branches():
    validator = _make_validator(validations=[
        "setpoint_tracking_controlled_magnitude",
        "setpoint_tracking_active_power",
        "setpoint_tracking_reactive_power",
    ])

    compliance_values = {
        "t_event_start": 0.0,
        "is_invalid_test": False,
    }

    with patch("dycov.validation.model.save_measurement_errors"), \
         patch("dycov.validation.model.check_measurement"), \
         patch("dycov.validation.model.complete_setpoint_tracking"):

        res = validator._ModelValidator__check(
            compliance_values,
            "VoltageSetpointPu",
        )

    assert "setpoint_tracking_controlled_magnitude_name" in res
    assert "setpoint_tracking_active_power_name" in res
    assert "setpoint_tracking_reactive_power_name" in res


# =========================
# Validate - extra branches
# =========================

def test_validate_without_reference():
    producer = Mock()
    producer.get_zone = Mock(return_value=1)

    validator = ModelValidator(
        curves_manager=Mock(),
        pcs_bm_name="test",
        producer=producer,
        validations=[],
        is_field_measurements=False,
        pcs_name="test",
        bm_name="test",
    )

    validator._curves_manager.apply_signal_processing = Mock()
    validator._get_calculated_curves = Mock(return_value=pd.DataFrame())
    validator._get_reference_curves = Mock(return_value=pd.DataFrame())
    validator._get_exclusion_windows = Mock(
        return_value=Mock(event_start=0.0, event_end=1.0, clear_start=0.0, clear_end=0.0)
    )

    with patch.object(validator, "_ModelValidator__calculate", return_value={
        "t_event_start": 0.0,
        "is_invalid_test": False
    }), patch.object(validator, "_ModelValidator__check", return_value={"compliance": True}):

        res = validator.validate(
            "oc",
            Path("/tmp"),
            "out",
            {
                "start_time": 0.0,
                "duration_time": 1.0,
                "connect_to": "ActivePowerSetpointPu",
                "step_value": 0.1,
            },
            has_reference=False,
        )

    assert res["incomplete_curves"] is True


# =========================
# Calculation - active power recovery
# =========================

def test_active_power_recovery_executes():
    validator = _make_validator(validations=["active_power_recovery"])

    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])
    validator._get_reference_curve_by_name = Mock(return_value=[0, 1, 2])

    import dycov.validation.common as common
    common.get_reached_time = Mock(return_value=(1.0, 1.0))

    results = {}

    validator._ModelValidator__active_power_recovery_error(
        start_event=0.0,
        duration_event=1.0,
        results=results,
    )

    assert "t_P90_error" in results


# =========================
# Calculation - event times
# =========================

def test_compare_event_times_executes():
    validator = _make_validator(validations=["reaction_time", "rise_time"])

    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])
    validator._get_reference_curve_by_name = Mock(return_value=[0, 1, 2])

    import dycov.validation.common as common
    common.get_reached_time = Mock(return_value=(1.0, 1.0))

    results = {}

    validator._ModelValidator__compare_event_times(
        measurement_name="BusPDR_BUS_ActivePower",
        start_event=0.0,
        setpoint_variation=0.1,
        results=results,
    )

    assert "calc_reaction_time" in results
    assert "calc_rise_time" in results


# =========================
# Calculation - ramp
# =========================

def test_compare_ideal_ramp_executes():
    validator = _make_validator(validations=["ramp_time_lag"])

    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])

    import dycov.validation.common as common
    common.get_time_lag = Mock(return_value=0.1)
    common.get_value_error = Mock(return_value=0.1)

    results = {}

    validator._ModelValidator__compare_ideal_ramp(
        measurement_name="BusPDR_BUS_ActivePower",
        t_event_start=0.0,
        t_event_duration=1.0,
        freq0=1.0,
        freq_peak=0.5,
        results=results,
    )

    assert "ramp_time_lag" in results


# =========================
# Calculation - ss tolerance branch
# =========================

def test_get_ss_tolerance_zero_variation_branch():
    with patch("dycov.configuration.cfg.Config.get_float", return_value=0.01):
        assert get_ss_tolerance(0.0) == 0.01


def test_get_ss_tolerance_non_zero_branch():
    with patch("dycov.configuration.cfg.Config.get_float", return_value=0.01):
        assert get_ss_tolerance(0.2) == 0.002

# =========================
# Check - full time branches
# =========================

def test_check_times_all_branches():
    validator = _make_validator(validations=[
        "reaction_time",
        "rise_time",
        "settling_time",
        "overshoot",
    ])

    results = {"compliance": True}
    compliance_values = {
        "calc_reaction_time": 1.0,
        "ref_reaction_time": 1.0,
        "calc_reaction_target": {"x": 1.0},
        "calc_rise_time": 1.0,
        "ref_rise_time": 1.0,
        "calc_rise_target": {"x": 1.0},
        "calc_settling_time": 1.0,
        "ref_settling_time": 1.0,
        "calc_settling_tube": {"x": [0, 1]},
        "calc_ss_value": 1.0,
        "calc_overshoot": 0.1,
        "ref_overshoot": 0.1,
    }

    import dycov.validation.common as common
    common.check_time = Mock(return_value=(0.0, True))

    validator._ModelValidator__check_times(results, compliance_values)

    assert "reaction_time_check" in results
    assert "rise_time_check" in results
    assert "settling_time_check" in results
    assert "overshoot_check" in results


# =========================
# Validate - frequency branch
# =========================

def test_validate_frequency_branch():
    producer = Mock()
    producer.get_zone = Mock(return_value=1)

    validator = ModelValidator(
        curves_manager=Mock(),
        pcs_bm_name="test",
        producer=producer,
        validations=[],
        is_field_measurements=False,
        pcs_name="test",
        bm_name="test",
    )

    validator._curves_manager.apply_signal_processing = Mock()
    validator._get_calculated_curves = Mock(return_value=pd.DataFrame())
    validator._get_reference_curves = Mock(return_value=pd.DataFrame())
    validator._get_exclusion_windows = Mock(
        return_value=Mock(event_start=0.0, event_end=1.0, clear_start=0.0, clear_end=0.0)
    )

    with patch.object(validator, "_ModelValidator__calculate", return_value={
        "t_event_start": 0.0,
        "is_invalid_test": False
    }), patch.object(validator, "_ModelValidator__check", return_value={"compliance": True}):

        validator.validate(
            "oc",
            Path("/tmp"),
            "out",
            {
                "start_time": 0.0,
                "duration_time": 1.0,
                "connect_to": "NetworkFrequencyPu",
                "step_value": 0.2,
            },
            has_reference=True,
        )
