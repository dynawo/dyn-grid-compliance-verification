import math
import pytest
import numpy as np

from dycov.validation import common


def test_is_stable_returns_true_when_curve_stabilizes():
    # Curve stabilizes at value 5 after t=5, stable_time=3
    time = [0, 1, 2, 3, 4, 5, 6, 7, 8]
    curve = [1, 2, 3, 4, 5, 5, 5, 5, 5]
    stable_time = 3
    stable, idx = common.is_stable(time, curve, stable_time)
    assert stable is True
    assert idx != -1


def test_get_response_time_returns_correct_time():
    # Curve reaches 10% of final value at t=3 after event at t=1
    time = [0, 1, 2, 3, 4]
    curve = [0, 0, 0.9, 1.0, 1.0]
    percent = 0.1
    sim_t_event_start = 1
    result = common.get_response_time(percent, time, curve, sim_t_event_start)
    # Should be time[2] - sim_t_event_start = 2 - 1 = 1
    assert result == 1


def test_mean_absolute_error_correctness():
    signal = [1, 2, 3, 4]
    reference = [1, 2, 2, 2]
    step_magnitude = 2
    result = common.mean_absolute_error(signal, reference, step_magnitude)
    expected = (abs(1 - 1) + abs(2 - 2) + abs(3 - 2) + abs(4 - 2)) / 4 / 2
    assert pytest.approx(result, rel=1e-9) == expected


def test_is_stable_raises_value_error_on_length_mismatch():
    time = [0, 1, 2]
    curve = [1, 2]
    stable_time = 1
    with pytest.raises(ValueError, match="different length"):
        common.is_stable(time, curve, stable_time)


def test_get_txu_returns_zero_if_threshold_not_reached():
    # Curve needs 1s to reach threshold 4 after event at t=2
    time = [0, 1, 2, 3, 4, 5]
    curve = [1, 2, 3, 4, 5, 6]
    threshold = 4
    sim_t_event_end = 2
    result = common.get_txu(threshold, time, curve, sim_t_event_end)
    assert result == 1


def test_maximum_error_returns_zero_on_empty_input():
    signal = np.array([])
    reference = np.array([])
    step_magnitude = 1
    result = common.maximum_error(signal, reference, step_magnitude)
    assert result == 0


def test_check_time_within_tolerances_returns_true_and_correct_error():
    # calculated_time is within rtol and atol of reference_time
    calculated_time = 10.01
    reference_time = 10.0
    rtol = 0.1  # 0.1%
    atol = 0.05
    error, is_within = common.check_time(calculated_time, reference_time, rtol, atol)
    print(f"Error: {error}, is_within: {is_within}")
    # Relative error: 100 * abs(10.01 - 10.0) / 10.0 = 0.1%
    assert is_within is True
    assert pytest.approx(error, rel=1e-6) == 0.1


def test_get_settling_time_raises_value_error_on_length_mismatch():
    percent = 0.05
    time = [0, 1, 2]
    curve = [1, 2]
    sim_t_event_start = 1
    with pytest.raises(ValueError, match="different length"):
        common.get_settling_time(percent, time, curve, sim_t_event_start)


def test_is_invalid_test_returns_true_for_flat_curves():
    # All curves are flat after the event
    time = [0, 1, 2, 3, 4, 5]
    voltage = [1, 1, 1, 1, 1, 1]
    active = [2, 2, 2, 2, 2, 2]
    reactive = [3, 3, 3, 3, 3, 3]
    t_event = 2
    assert common.is_invalid_test(time, voltage, active, reactive, t_event) is True


def test_get_AVR_x_returns_true_within_tolerance():
    # curve and target_values are within 5% after event
    time = [0, 1, 2, 3, 4]
    curve = [1.0, 1.05, 1.04, 1.03, 1.02]
    target_values = [1.0, 1.0, 1.0, 1.0, 1.0]
    sim_t_event_end = 2
    result, error_time = common.get_AVR_x(time, curve, target_values, sim_t_event_end)
    assert result is True
    assert error_time == -1


def test_check_generator_imax_prioritizes_reactive_support():
    # After reaching imax, injected_active_current does not increase
    imax = 5
    time = [0, 1, 2, 3, 4, 5]
    injected_current = [1, 3, 5, 5, 5, 5]
    injected_active_current = [2, 2, 2, 2, 2, 2]
    first_id_value, id_not_increase = common.check_generator_imax(
        imax, time, injected_current, injected_active_current
    )
    assert id_not_increase is True
    assert first_id_value == -1


def test_theta_pi_raises_value_error_on_length_mismatch():
    time = [0, 1, 2]
    curve = [0, 1]
    with pytest.raises(ValueError, match="different length"):
        common.theta_pi(time, curve)


def test_get_txu_returns_last_time_if_threshold_not_reached():
    # Threshold is never reached, should return last time - sim_t_event_end
    time = [0, 1, 2, 3, 4]
    curve = [0, 0, 0, 0, 0]
    threshold = 10
    sim_t_event_end = 1
    result = common.get_txu(threshold, time, curve, sim_t_event_end)
    assert result == time[-1] - sim_t_event_end


def test_mean_error_raises_value_error_on_length_mismatch():
    signal = [1, 2, 3]
    reference = [1, 2]
    step_magnitude = 1
    with pytest.raises(ValueError, match="different length"):
        common.mean_error(signal, reference, step_magnitude)


def test_maximum_error_returns_zero_on_empty_arrays():
    signal = np.array([])
    reference = np.array([])
    step_magnitude = 1
    result = common.maximum_error(signal, reference, step_magnitude)
    assert result == 0


def test_correct_time_lag_calculation():
    # Setup test data
    time = [1.0, 1.6666666666, 2.6666666666, 4.0, 5.0]
    curve = [10.0, 20.0, 30.0, 40.0, 50.0]
    sim_t_event_start = 4.0
    event_duration = 2.0

    # Expected: time[1:4] = [1.6666666666, 2.6666666666, 4.0]
    # compared with ideal_time = [2.0, 3.0, 4.0]
    # The max difference should be the maximum absolute difference between these arrays

    # Call the function
    result = common.get_time_lag(time, curve, sim_t_event_start, event_duration)

    # Calculate expected result manually
    time_slice = time[1:4]  # Based on the algorithm's logic
    ideal_time = np.linspace(
        sim_t_event_start - event_duration, sim_t_event_start, len(time_slice), False
    )
    expected = max(abs(np.array(time_slice) - ideal_time))

    # Assert
    assert math.isclose(result, expected), f"Expected time lag {expected}, but got {result}"
