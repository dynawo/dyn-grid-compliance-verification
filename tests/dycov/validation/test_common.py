#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Unit tests for the curve measurement helpers shared by every validator."""

import numpy as np
import pandas as pd
import pytest

from dycov.validation import common

COMMON_MODULE = "dycov.validation.common"

THRESHOLDS = {"thr_ss_tol": 0.002}


class DummyConfig:
    """Configuration stand-in serving THRESHOLDS, falling back to the requested default."""

    def __init__(self, **overrides):
        self._values = dict(THRESHOLDS, **overrides)

    def get_float(self, section: str, key: str, default: float) -> float:
        return self._values.get(key, default)


@pytest.fixture(autouse=True)
def dummy_config(monkeypatch):
    """Serve a deterministic steady-state tolerance regardless of the user configuration."""
    monkeypatch.setattr(f"{COMMON_MODULE}.config", DummyConfig())


# ---------------------------------------------------------------------------
# Steady-state tolerance
# ---------------------------------------------------------------------------


def test_get_ss_tolerance_without_setpoint_variation_returns_the_configured_tolerance():
    assert common.get_ss_tolerance(0.0) == pytest.approx(0.002)


def test_get_ss_tolerance_scales_with_the_setpoint_variation():
    assert common.get_ss_tolerance(0.1) == pytest.approx(0.0002)


# ---------------------------------------------------------------------------
# Time comparison
# ---------------------------------------------------------------------------


def test_check_time_within_the_tolerances_reports_the_relative_error():
    error, time_check = common.check_time(10.01, 10.0, 0.1, 0.05)

    assert time_check is True
    assert error == pytest.approx(0.1)


def test_check_time_outside_the_tolerances_fails():
    error, time_check = common.check_time(12.0, 10.0, 0.1)

    assert time_check is False
    assert error == pytest.approx(20.0)


def test_check_time_against_a_null_reference_reports_no_error():
    error, time_check = common.check_time(0.0, 0.0, 0.1)

    # A null reference makes the relative error meaningless.
    assert time_check is True
    assert error == "-"


# ---------------------------------------------------------------------------
# Flat response detection
# ---------------------------------------------------------------------------


def test_is_invalid_test_with_flat_curves():
    time = [0, 1, 2, 3, 4, 5]

    result = common.is_invalid_test(time, [1] * 6, [2] * 6, [3] * 6, t_event=2)

    assert result is True


def test_is_invalid_test_with_a_responding_curve():
    time = [0, 1, 2, 3, 4, 5]
    active = [2, 2, 2, 2.5, 2.5, 2.5]

    result = common.is_invalid_test(time, [1] * 6, active, [3] * 6, t_event=2)

    assert result is False


# ---------------------------------------------------------------------------
# Stabilization
# ---------------------------------------------------------------------------


def test_is_stable_returns_the_first_index_of_the_steady_state():
    time = [0, 1, 2, 3, 4, 5, 6, 7, 8]
    curve = [1, 2, 3, 4, 5, 5, 5, 5, 5]

    stable, index = common.is_stable(time, curve, thr_ss_tol=0.002)

    assert stable is True
    assert index == 4


def test_is_stable_with_a_diverged_curve():
    time = [0, 1, 2]
    curve = [0.0, 1.0, float("nan")]

    stable, index = common.is_stable(time, curve, thr_ss_tol=0.002)

    # A non-finite final value can never be approached.
    assert stable is False
    assert index == -1


def test_is_stable_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="different length"):
        common.is_stable([0, 1, 2], [1, 2], thr_ss_tol=1)


def test_theta_pi_within_the_bounds():
    assert common.theta_pi([0, 1, 2], [0.0, 1.5, -1.5]) is True


def test_theta_pi_outside_the_bounds():
    assert common.theta_pi([0, 1, 2], [0.0, 3.2, 1.0]) is False


def test_theta_pi_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="different length"):
        common.theta_pi([0, 1, 2], [0, 1])


# ---------------------------------------------------------------------------
# Static difference
# ---------------------------------------------------------------------------


def test_get_static_diff_relative_to_the_setpoint():
    result = common.get_static_diff([1.0, 1.05, 1.10], [1.0, 1.04, 1.00])

    assert result == pytest.approx(0.10)


def test_get_static_diff_against_a_null_setpoint_is_absolute():
    result = common.get_static_diff([1.0, 0.05], [0.0, 0.0])

    assert result == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# Time to reach a tolerance tube
# ---------------------------------------------------------------------------


def test_get_txu_relative_measures_the_time_after_the_event():
    time = [0, 1, 2, 3, 4]
    curve = [0.0, 0.0, 0.5, 1.0, 1.0]

    result = common.get_txu_relative(0.1, time, curve, sim_t_event_end=1)

    # The last sample outside the [0.9, 1.1] tube is at t = 2 s.
    assert result == pytest.approx(1.0)


def test_get_txu_relative_of_a_flat_curve_uses_an_absolute_tube():
    time = [0, 1, 2, 3, 4]
    curve = [1.0, 1.0, 1.0, 1.0, 1.0]

    result = common.get_txu_relative(0.1, time, curve, sim_t_event_end=1)

    # The curve never leaves the tube, so the search reaches the first sample.
    assert result == 0


def test_get_txu_relative_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="different length"):
        common.get_txu_relative(0.1, [0, 1, 2], [1, 2], sim_t_event_end=1)


def test_get_txp_measures_the_time_after_the_event():
    time = [0, 1, 2, 3]
    curve = [0.0, 0.0, 1.0, 1.0]

    result = common.get_txp(0.05, time, curve, sim_t_event_end=0.5)

    # The last sample outside the [0.95, 1.05] tube is at t = 1 s.
    assert result == pytest.approx(0.5)


def test_get_txp_of_a_near_zero_target_uses_an_absolute_tube():
    time = [0, 1, 2, 3]
    curve = [0.5, 0.01, 0.005, 0.005]

    result = common.get_txp(0.05, time, curve, sim_t_event_end=1)

    # Below 0.01 the tube becomes 0.005 +- 0.02, so only the first sample is outside it.
    assert result == 0


def test_get_txp_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="different length"):
        common.get_txp(0.05, [0, 1, 2], [1, 2], sim_t_event_end=1)


def test_get_txpfloor_only_considers_the_lower_bound():
    time = [0, 1, 2, 3]
    curve = [2.0, 0.5, 1.0, 1.0]

    result = common.get_txpfloor(0.1, time, curve, sim_t_event_end=0.5)

    # The overshoot at t = 0 s is ignored; only the 0.5 sample is below the 0.9 floor.
    assert result == pytest.approx(0.5)


def test_get_txpfloor_of_an_event_after_the_deviation_returns_zero():
    time = [0, 1, 2]
    curve = [0.5, 1.0, 1.0]

    result = common.get_txpfloor(0.1, time, curve, sim_t_event_end=1.5)

    # The only sample below the floor precedes the end of the event.
    assert result == 0


def test_get_txpfloor_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="different length"):
        common.get_txpfloor(0.1, [0, 1, 2], [1, 2], sim_t_event_end=1)


def test_get_txu_measures_the_time_to_reach_the_threshold():
    time = [0, 1, 2, 3, 4, 5]
    curve = [1, 2, 3, 4, 5, 6]

    result = common.get_txu(4, time, curve, sim_t_event_end=2)

    assert result == pytest.approx(1.0)


def test_get_txu_of_an_unreached_threshold_returns_the_last_instant():
    time = [0, 1, 2, 3, 4]
    curve = [0, 0, 0, 0, 0]

    result = common.get_txu(10, time, curve, sim_t_event_end=1)

    assert result == pytest.approx(3.0)


def test_get_txu_of_a_curve_already_above_the_threshold_returns_zero():
    time = [0, 1, 2, 3]
    curve = [5, 5, 5, 5]

    result = common.get_txu(1, time, curve, sim_t_event_end=2)

    # The threshold is already exceeded before the event.
    assert result == 0


def test_get_txu_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="different length"):
        common.get_txu(1, [0, 1, 2], [1, 2], sim_t_event_end=1)


# ---------------------------------------------------------------------------
# Generator current limit
# ---------------------------------------------------------------------------


def test_check_generator_imax_prioritizes_the_reactive_current():
    time = [0, 1, 2, 3, 4, 5]

    first_id_value, id_not_increase = common.check_generator_imax(
        5, time, [1, 3, 5, 5, 5, 5], [2, 2, 2, 2, 2, 2]
    )

    assert id_not_increase is True
    assert first_id_value == -1


def test_check_generator_imax_detects_an_active_current_increase_under_saturation():
    time = [0, 1, 2, 3]

    first_id_value, id_not_increase = common.check_generator_imax(
        5, time, [5, 5, 5, 5], [1, 1, 2, 2]
    )

    assert id_not_increase is False
    assert first_id_value == 2


def test_check_generator_imax_resets_when_the_saturation_ends():
    time = [0, 1, 2]

    first_id_value, id_not_increase = common.check_generator_imax(5, time, [5, 1, 5], [1, 1, 5])

    # Leaving saturation drops the reference, so the later increase is not a violation.
    assert id_not_increase is True
    assert first_id_value == -1


def test_check_generator_imax_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="All input lists must have the same length"):
        common.check_generator_imax(5, [0, 1, 2], [1, 2], [1, 2])


# ---------------------------------------------------------------------------
# AVR tracking
# ---------------------------------------------------------------------------


def test_get_AVR_x_within_the_tolerance():
    time = [0, 1, 2, 3, 4]
    curve = [1.0, 1.05, 1.04, 1.03, 1.02]
    target_values = [1.0, 1.0, 1.0, 1.0, 1.0]

    pass_check, error_time = common.get_AVR_x(time, curve, target_values, sim_t_event_end=2)

    assert pass_check is True
    assert error_time == -1


def test_get_AVR_x_outside_the_tolerance_reports_the_instant():
    time = [0, 1, 2]
    curve = [1.0, 1.0, 2.0]
    target_values = [1.0, 1.0, 1.0]

    pass_check, error_time = common.get_AVR_x(time, curve, target_values, sim_t_event_end=1)

    assert pass_check is False
    assert error_time == pytest.approx(1.0)


def test_get_AVR_x_against_a_null_target_uses_the_absolute_error():
    time = [0, 1, 2]
    curve = [0.0, 0.0, 0.02]
    target_values = [0.0, 0.0, 0.0]

    pass_check, error_time = common.get_AVR_x(time, curve, target_values, sim_t_event_end=0)

    assert pass_check is True
    assert error_time == -1


# ---------------------------------------------------------------------------
# Frequency band
# ---------------------------------------------------------------------------


def test_check_frequency_within_the_threshold():
    frequency = [1.0, 1.01, 0.99, 1.0, 1.005]
    time = [0, 1, 2, 3, 4]

    pass_test, error_time = common.check_frequency(0.02, frequency, time)

    assert pass_test is True
    assert error_time == -1


def test_check_frequency_outside_the_threshold_reports_the_instant():
    frequency = [1.0, 1.05, 1.0]
    time = [0, 1, 2]

    pass_test, error_time = common.check_frequency(0.02, frequency, time)

    assert pass_test is False
    assert error_time == 1


# ---------------------------------------------------------------------------
# Error metrics
# ---------------------------------------------------------------------------


def test_mean_error_is_signed():
    result = common.mean_error([1, 2, 3, 4], [1, 2, 2, 2], step_magnitude=2)

    assert result == pytest.approx(0.375)


def test_mean_error_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="different length"):
        common.mean_error([1, 2, 3], [1, 2], step_magnitude=1)


def test_mean_absolute_error_ignores_the_sign():
    result = common.mean_absolute_error([1, 2, 1, 0], [1, 2, 2, 2], step_magnitude=2)

    assert result == pytest.approx(0.375)


def test_mean_absolute_error_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="different length"):
        common.mean_absolute_error([1, 2, 3], [1, 2], step_magnitude=1)


def test_maximum_error_returns_the_largest_deviation():
    result = common.maximum_error(np.array([1, 2, 3, 4]), np.array([1, 2, 2, 2]), step_magnitude=2)

    assert result == pytest.approx(1.0)


def test_maximum_error_of_empty_signals_is_zero():
    result = common.maximum_error(np.array([]), np.array([]), step_magnitude=1)

    assert result == 0


def test_maximum_error_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="different length"):
        common.maximum_error(np.array([1, 2, 3]), np.array([1, 2]), step_magnitude=1)


def test_maximum_error_position_raises_value_error_on_length_mismatch():
    time = pd.Series([0, 1, 2])
    signal = pd.Series([1, 2, 3])
    reference = pd.Series([1, 2])
    with pytest.raises(ValueError, match="different length"):
        common.maximum_error_position(time, signal, reference, "")


class _RecordingLogger:
    """Captures the warnings emitted through dycov_logging."""

    def __init__(self):
        self.warnings = []

    def get_logger(self, name):
        return self

    def warning(self, msg):
        self.warnings.append(msg)


@pytest.fixture
def logged_warnings(monkeypatch):
    logger = _RecordingLogger()
    monkeypatch.setattr("dycov.validation.common.dycov_logging", logger)
    return logger.warnings


def test_maximum_error_position_locates_the_largest_deviation():
    time = pd.Series([0.0, 0.5, 1.0])
    signal = pd.Series([1.0, 3.0, 1.0])
    reference = pd.Series([1.0, 1.0, 1.0])

    position = common.maximum_error_position(time, signal, reference, "BusPDR_BUS_ActivePower")

    assert position == (0.5, 3.0, 1.0)


def test_maximum_error_position_without_reference_values_is_not_computable(logged_warnings):
    """Issue #373: an all-NaN reference used to return a two-element tuple, which broke the
    three-value unpacking done by the caller; it is now a single "not computable" answer."""
    time = pd.Series([0.0, 0.5, 1.0])
    signal = pd.Series([1.0, 3.0, 1.0])
    reference = pd.Series([np.nan, np.nan, np.nan])

    position = common.maximum_error_position(time, signal, reference, "BusPDR_BUS_Voltage")

    assert position is None
    assert logged_warnings == ["No reference values in BusPDR_BUS_Voltage"]


def test_maximum_error_position_of_empty_curves_is_not_computable(logged_warnings):
    """Issue #373: empty curves used to return the bare scalar 0 instead of a tuple."""
    empty = pd.Series([], dtype=float)

    position = common.maximum_error_position(empty, empty, empty, "BusPDR_BUS_Voltage")

    assert position is None
    assert logged_warnings == ["No reference values in BusPDR_BUS_Voltage"]


def test_get_reached_time_returns_correct_time_and_value():
    # Curve starts at 2, ends at 10, 50% of the way is 2 + 0.5*(10-2) = 6
    time = [0, 1, 2, 3, 4, 5]
    curve = [2, 3, 5, 6, 8, 10]
    percentage = 0.5
    sim_t_event_start = 1
    ret_val, objective_value = common.get_reached_time(percentage, time, curve, sim_t_event_start)
    # After event at t=1, curve[2]=5, curve[3]=6, so first >=6 is at t=3
    assert ret_val == 2  # time[3] - sim_t_event_start = 3 - 1 = 2
    assert pytest.approx(objective_value, rel=1e-9) == 6


# ---------------------------------------------------------------------------
# Response and settling times
# ---------------------------------------------------------------------------


def test_get_response_time_measures_the_time_after_the_event():
    time = [0, 1, 2, 3, 4]
    curve = [0, 0, 0.9, 1.0, 1.0]

    result = common.get_response_time(0.1, time, curve, sim_t_event_start=1)

    assert result == pytest.approx(1.0)


def test_get_response_time_of_a_curve_already_in_the_tube_is_zero():
    time = [0, 1, 2]
    curve = [1.0, 1.0, 1.0]

    result = common.get_response_time(0.05, time, curve, sim_t_event_start=0)

    assert result == pytest.approx(0.0)


def test_get_response_time_of_an_event_after_the_curve_is_zero():
    time = [0, 1, 2]
    curve = [1.0, 1.0, 1.0]

    result = common.get_response_time(0.05, time, curve, sim_t_event_start=5)

    # The event is outside the simulated window.
    assert result == 0


def test_get_response_time_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="different length"):
        common.get_response_time(0.05, [0, 1, 2], [1, 2], sim_t_event_start=1)


def test_get_settling_time_measures_the_time_and_the_tube():
    time = [0, 1, 2, 3]
    curve = [0.0, 0.0, 1.0, 1.0]

    ret_val, pos, tube_min, tube_max, tube_value = common.get_settling_time(
        0.05, time, curve, sim_t_event_start=0.5
    )

    assert ret_val == pytest.approx(0.5)
    assert pos == 1
    assert tube_min == pytest.approx(0.95)
    assert tube_max == pytest.approx(1.05)
    assert tube_value == pytest.approx(0.0)


def test_get_settling_time_of_an_event_after_the_curve_is_zero():
    time = [0, 1, 2]
    curve = [0.0, 1.0, 1.0]

    ret_val, pos, _, _, _ = common.get_settling_time(0.05, time, curve, sim_t_event_start=5)

    assert ret_val == 0
    assert pos == 0


def test_get_settling_time_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="different length"):
        common.get_settling_time(0.05, [0, 1, 2], [1, 2], sim_t_event_start=1)


# ---------------------------------------------------------------------------
# Reached time
# ---------------------------------------------------------------------------


def test_get_reached_time_of_a_rising_curve():
    time = [0, 1, 2, 3, 4, 5]
    curve = [2, 3, 5, 6, 8, 10]

    ret_val, objective_value = common.get_reached_time(0.5, time, curve, sim_t_event_start=1)

    # The target is 2 + 0.5 * (10 - 2) = 6, first reached at t = 3 s.
    assert ret_val == pytest.approx(2.0)
    assert objective_value == pytest.approx(6.0)


def test_get_reached_time_of_a_falling_curve():
    time = [0, 1, 2, 3]
    curve = [1.0, 1.0, 0.5, 0.0]

    ret_val, objective_value = common.get_reached_time(0.5, time, curve, sim_t_event_start=1)

    # The target is 1 + 0.5 * (0 - 1) = 0.5, first reached at t = 2 s.
    assert ret_val == pytest.approx(1.0)
    assert objective_value == pytest.approx(0.5)


def test_get_reached_time_of_a_flat_curve_offsets_the_target():
    time = [0, 1, 2]
    curve = [1.0, 1.0, 1.0]

    ret_val, objective_value = common.get_reached_time(0.5, time, curve, sim_t_event_start=1)

    # Without a variation the percentage is applied as an absolute offset.
    assert ret_val == pytest.approx(0.0)
    assert objective_value == pytest.approx(1.5)


def test_get_reached_time_of_an_unreachable_target_returns_the_last_instant():
    time = [0, 1, 2]
    curve = [0.0, 0.5, 1.0]

    ret_val, objective_value = common.get_reached_time(1.5, time, curve, sim_t_event_start=1)

    # A percentage above the whole variation is never reached, so the search is clamped.
    assert ret_val == pytest.approx(1.0)
    assert objective_value == pytest.approx(1.5)


def test_get_reached_time_of_an_event_after_the_curve_is_zero():
    time = [0, 1, 2]
    curve = [0, 1, 2]

    ret_val, _ = common.get_reached_time(0.9, time, curve, sim_t_event_start=5)

    assert ret_val == 0


def test_get_reached_time_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="different length"):
        common.get_reached_time(0.9, [0, 1, 2], [1, 2], sim_t_event_start=1)


# ---------------------------------------------------------------------------
# Overshoot
# ---------------------------------------------------------------------------


def test_get_overshoot_measures_the_peak_above_the_final_value():
    result = common.get_overshoot([1.0, 2.0, 3.5, 2.5, 2.0])

    assert result == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# Ideal ramp deviation
# ---------------------------------------------------------------------------


def test_get_value_error_of_a_curve_following_the_ideal_ramp_is_zero():
    time = np.linspace(0, 1, 5)
    curve = np.linspace(0, 1, 5)

    result = common.get_value_error(
        time, curve, sim_t_event_start=1, event_duration=1, freq0=0, freq_peak=1
    )

    assert result == pytest.approx(0.0)


def test_get_value_error_measures_the_deviation_from_the_ideal_ramp():
    time = [0.0, 1.0, 2.0, 3.0]
    curve = [1.0, 1.0, 1.1, 1.2]

    result = common.get_value_error(
        time, curve, sim_t_event_start=3, event_duration=1, freq0=1.0, freq_peak=0.2
    )

    # Only the sample at t = 2 s belongs to the ramp window, where the ideal value is 1.0 pu.
    assert result == pytest.approx(0.1)


def test_get_time_lag_of_an_evenly_sampled_ramp_is_zero():
    time = [0.0, 0.5, 1.0, 1.5, 2.0]
    curve = [1.0, 1.05, 1.10, 1.15, 1.20]

    result = common.get_time_lag(time, curve, sim_t_event_start=2.0, event_duration=2.0)

    assert result == pytest.approx(0.0)


def test_get_time_lag_measures_the_sampling_deviation():
    time = [0.0, 0.5, 1.5, 2.0]
    curve = [1.0, 1.05, 1.15, 1.20]

    result = common.get_time_lag(time, curve, sim_t_event_start=2.0, event_duration=2.0)

    # The ramp samples are compared against [0, 2/3, 4/3].
    assert result == pytest.approx(1.5 - 4 / 3)


def test_get_time_lag_restricts_the_comparison_to_the_ramp_window():
    time = [0.0, 1.0, 2.0, 3.0]
    curve = [1.0, 1.0, 1.1, 1.2]

    result = common.get_time_lag(time, curve, sim_t_event_start=3.0, event_duration=1.0)

    # Only the sample at t = 2 s belongs to the ramp window, and it is evenly sampled.
    assert result == pytest.approx(0.0)


def test_get_time_lag_raises_on_length_mismatch():
    with pytest.raises(ValueError, match="different length"):
        common.get_time_lag([0, 1, 2], [1, 2], sim_t_event_start=1, event_duration=1)
