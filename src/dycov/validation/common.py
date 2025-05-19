#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import math

import numpy as np

from dycov.configuration.cfg import config
from dycov.logging.logging import dycov_logging

# when magnitudes are smaller than atol, switch to absolute error
ATOL = 1.0e-6


def _show_error(calculated_value: float, reference_value: float, rtol: float, atol: float) -> bool:
    if rtol * max(abs(calculated_value), abs(reference_value)) > atol and reference_value != 0.0:
        return True
    return False


def check_time(
    calculated_time: float, reference_time: float, rtol: float, atol: float = ATOL
) -> tuple[float, bool]:
    """Check if the calculated time is within the tolerances of the reference time.

    Parameters
    ----------
    calculated_time: float
        Calculated time
    reference_time: float
        Reference time
    rtol: float
        Relative tolerance
    atol: float
        Aboslute tolerance

    Returns
    -------
    float
        Relative error between the calculated and reference time
    bool
        True if the calculated time is within the tolerances of the reference time, False otherwise

    """
    # when magnitudes are smaller than atol, switch to absolute error
    time_check = math.isclose(
        calculated_time,
        reference_time,
        rel_tol=rtol,
        abs_tol=atol,
    )
    if _show_error(calculated_time, reference_time, rtol, atol):
        return 100 * (abs(calculated_time - reference_time) / reference_time), time_check
    else:
        return "-", time_check


def is_invalid_test(
    time: list, voltage: list, active: list, reactive: list, t_event: float, log_title: str
):
    """Check if the results of a step-response test are completely flat (no response).
    This is used for checking for a common error, i.e., the event not producing any effect.

    Parameters
    ----------
    time: list
        List of time instants that make up the curve
    voltage: list
        PDR Voltage curve
    active: list
        PDR Active Power curve
    reactive: list
        PDR Reactive Power curve
    t_event: float
        Time at which the event takes place

    Returns
    -------
    bool
        True if all three curves (V, P, Q) are completely flat after the event
    """
    thr_ss_tol = config.get_float("GridCode", "thr_ss_tol", 0.002)

    # Calculate the point of the curves at which the event takes place
    # (-1 to make sure it's *before* the event, in case the closest point is right after)
    # TODO: we should assert(t_event >= time[0]), but not here -- do it at init time
    idx_t_event = np.argmin(abs(np.array(time) - t_event)) - 1
    dycov_logging.get_logger("Common Validation").debug(
        f"{log_title} Start values: V: {voltage[0]}, P: {active[0]}, Q: {reactive[0]}"
    )

    # Get the steady-state value right before the event
    v_init = voltage[idx_t_event]
    p_init = active[idx_t_event]
    q_init = reactive[idx_t_event]
    dycov_logging.get_logger("Common Validation").debug(
        f"{log_title} Steady-state values: V: {v_init}, P: {p_init}, Q: {q_init}"
    )

    # Get max diff between values after event vs the steady-state value right before
    v_max_diff = max(abs(np.array(voltage[idx_t_event:]) - v_init))
    p_max_diff = max(abs(np.array(active[idx_t_event:]) - p_init))
    q_max_diff = max(abs(np.array(reactive[idx_t_event:]) - q_init))
    dycov_logging.get_logger("Common Validation").debug(
        f"{log_title} Max diff: V: {v_max_diff}, P: {p_max_diff}, Q: {q_max_diff}"
    )

    # Check if this max diff is smaller than the tolerances
    rtol = thr_ss_tol  # i.e., 0.2% relative error
    atol = 0.1 * rtol  # i.e., when magnitudes are near 0.01, switch to abs error
    v_flat = math.isclose(v_max_diff, 0.0, rel_tol=rtol, abs_tol=atol)
    p_flat = math.isclose(p_max_diff, 0.0, rel_tol=rtol, abs_tol=atol)
    q_flat = math.isclose(q_max_diff, 0.0, rel_tol=rtol, abs_tol=atol)
    dycov_logging.get_logger("Common Validation").debug(
        f"{log_title} Flat Curves: V: {v_flat}, P: {p_flat}, Q: {q_flat}"
    )

    return v_flat and p_flat and q_flat


def is_stable(time: list, curve: list, stable_time: float) -> tuple[bool, int]:
    """Check if the stabilization is reached.
    The curve is considered to have stabilized if, for the given minimum duration (stable_time),
    the curve does not have variations exceeding the given relative tolerance.

    Parameters
    ----------
    time: list
        List of time instants that make up the curve
    curve: list
        List of values that make up the curve
    stable_time: float
        Minimum duration required to consider stability reached (measured from the tail)

    Returns
    -------
    bool
        True if the stabilization is reached, False otherwise
    int
        The position where the stabilization is reached in the given lists
        -1 if the stabilization is not reached
    """

    thr_ss_tol = config.get_float("GridCode", "thr_ss_tol", 0.002)

    if len(time) != len(curve):
        raise ValueError("the curve values and its time series have different length")
    if stable_time <= 0:
        raise ValueError("stable_time should be > 0")

    # Get the index of the time series where the minimum SS duration "tail window" starts
    tail_window_start = time[-1] - stable_time
    if tail_window_start < time[0]:
        raise ValueError("stable_time is longer than the whole simulation time")
    idx_time = np.argmin(abs(np.array(time) - tail_window_start))

    # Stability == all values in the tail are close to the end value (within tolerances)
    atol = 0.01 * thr_ss_tol
    curve_tail = curve[idx_time:]
    stable = True
    for val in curve_tail:
        if not math.isclose(val, curve_tail[-1], rel_tol=thr_ss_tol, abs_tol=atol):
            stable = False
            break

    # If stable, get the index of time at which it first becomes stable
    idx_first_stable = -1
    if stable:
        for i in range(idx_time, 0, -1):
            if not math.isclose(curve[i], curve[-1], rel_tol=thr_ss_tol, abs_tol=atol):
                idx_first_stable = i
                break

    return stable, idx_first_stable


def theta_pi(time: list, curve: list) -> bool:
    """Check if the stabilization is reached.
    The curve is considered to have stabilized if the curve does not exceed PI.

    Parameters
    ----------
    time: list
        List of time instants that make up the curve
    curve: list
        List of values that make up the curve

    Returns
    -------
    bool
        True if the stabilization is reached, False otherwise
    """
    # Get curves file and stable time
    if len(time) != len(curve):
        raise ValueError("curve values and time values have different length")

    # Get the first position of pi
    pi_value = True
    for i in range(len(curve)):
        pos = len(curve) - (i + 1)
        if curve[pos] < -3.141592 or curve[pos] > 3.141592:
            pi_value = False
            break

    # returns true if the stabilization is reached
    return pi_value


def get_static_diff(primary_voltages: list, voltage_setpoint: list) -> float:
    """Gets the static difference between the controlled quantity injected into the primary voltage
    regulator and the voltage adjustment setpoint.

    Parameters
    ----------
    primary_voltages: list
        the controlled quantity injected into the primary voltage regulator
    voltage_setpoint: list
        the voltage adjustment setpoint

    Returns
    -------
    float
        percentage value
    """

    end_val = primary_voltages[-1]
    cons_val = voltage_setpoint[-1]
    return math.fabs((end_val - cons_val) / cons_val)


def get_txu_relative(percent: float, time: list, curve: list, sim_t_event_end: float) -> float:
    """Gets the time when the curve reaches a value equivalent to a percentage of the
    difference between the end and the initial value.

    Parameters
    ----------
    percent: float
        Percentage of the target value
    time: list
        List of time instants that make up the curve
    curve: list
        List of values that make up the curve
    sim_t_event_end: float
        Instant of time when the event is triggered

    Returns
    -------
    float
        Time when the percent is reached after the event
    """
    # Get curves file and stable time
    if len(time) != len(curve):
        raise ValueError("curve values and time values have different length")

    # Get the tube
    mean_val = curve[-1] - curve[0]
    mean_val_max = curve[-1] + abs(percent * mean_val)
    mean_val_min = curve[-1] - abs(percent * mean_val)

    for i in range(len(curve)):
        pos = len(curve) - (i + 1)
        if curve[pos] < mean_val_min or curve[pos] > mean_val_max:
            break

    # Returns the time when the percent is reached after the event
    if time[pos] < sim_t_event_end:
        ret_val = 0
    else:
        ret_val = time[pos] - sim_t_event_end
    return ret_val


def get_txp(percent: float, time: list, curve: list, sim_t_event_end: float) -> float:
    """Gets the time when the curve reaches a value equivalent to a percentage of its target value.

    Parameters
    ----------
    percent: float
        Percentage of the target value
    time: list
        List of time instants that make up the curve
    curve: list
        List of values that make up the curve
    sim_t_event_end: float
        Instant of time when the event is triggered

    Returns
    -------
    float
        Time when the percent is reached after the event
    """
    # Get curves file and stable time
    if len(time) != len(curve):
        raise ValueError("curve values and time values have different length")

    # Get the tube
    if abs(curve[-1]) <= 1:
        mean_val_max = curve[-1] + percent
        mean_val_min = curve[-1] - percent

    # If the value is more than 1, we use relative value
    else:
        mean_val = curve[-1]
        mean_val_max = mean_val + abs(percent * mean_val)
        mean_val_min = mean_val - abs(percent * mean_val)

    for i in range(len(curve)):
        pos = len(curve) - (i + 1)
        if curve[pos] < mean_val_min or curve[pos] > mean_val_max:
            break

    # Returns the time when the percent is reached after the event
    if time[pos] < sim_t_event_end:
        ret_val = 0
    else:
        ret_val = time[pos] - sim_t_event_end
    return ret_val


def get_txpfloor(percent: float, time: list, curve: list, sim_t_event_end: float) -> float:
    """Gets the time when the curve reaches a value equivalent to a percentage of its target value,
    only applies to the minimum value.

    Parameters
    ----------
    percent: float
        Percentage of the target value
    time: list
        List of time instants that make up the curve
    curve: list
        List of values that make up the curve
    sim_t_event_end: float
        Instant of time when the event is triggered

    Returns
    -------
    float
        Time when the percent is reached after the event
    """
    # Get curves file and steady time
    if len(time) != len(curve):
        raise ValueError("curve values and time values have different length")

    # Get the tube
    if abs(curve[-1]) <= 1:
        mean_val_min = curve[-1] - percent

    # If the value is more than 1, we use relative value
    else:
        mean_val = curve[-1]
        mean_val_min = mean_val - abs(percent * mean_val)

    for i in range(len(curve)):
        pos = len(curve) - (i + 1)
        if curve[pos] < mean_val_min:
            break

    # Returns the time when the percent is reached after the event
    if time[pos] < sim_t_event_end:
        ret_val = 0
    else:
        ret_val = time[pos] - sim_t_event_end
    return ret_val


def get_txu(threshold: float, time: list, curve: list, sim_t_event_end: float) -> float:
    """Gets the time when the curve reaches a given threshold.

    Parameters
    ----------
    threshold: float
        Threshold that the curve must reach
    time: list
        List of time instants that make up the curve
    curve: list
        List of values that make up the curve
    sim_t_event_end: float
        Instant of time when the event is triggered

    Returns
    -------
    float
        Time when the percent is reached after the event
    """
    # Get curves file and stable time
    if len(time) != len(curve):
        raise ValueError("curve values and time values have different length")

    pos_t_event = 0
    while sim_t_event_end > time[pos_t_event] and pos_t_event < len(time) - 1:
        pos_t_event += 1

    # Cut list values
    time = time[pos_t_event - 1 :]
    curve = curve[pos_t_event - 1 :]

    pos = 0
    while pos < len(curve) and abs(curve[pos]) < threshold:
        pos += 1

    if pos == len(curve):
        pos = len(curve) - 1

    # Returns the time when the percent is reached after the event
    if time[pos] < sim_t_event_end:
        ret_val = 0
    else:
        ret_val = time[pos] - sim_t_event_end
    return ret_val


def check_generator_imax(
    imax: float, time: list, injected_current: list, injected_active_current: list
) -> tuple[int, bool]:
    """Check that, if Imax is reached, reactive support is priorized over active power supply.

    Parameters
    ----------
    imax: float
        IMax value of the generator
    time: list
        List of time instants that make up the curve
    injected_current: list
        Curve of the injected current
    injected_active_current: float
        Curve of the injected active current

    Returns
    -------
    int
        The position where the injected active current increases despite having reached Imax
    bool
        True if the injected active current does not increase, False otherwise
    """
    # Get curves file and steady time
    if len(time) != len(injected_current):
        raise ValueError("curve values and time values have different length")

    pos = 0
    while pos < len(injected_current) and injected_current[pos] < imax:
        pos += 1

    if pos >= len(injected_current):
        pos = len(injected_current) - 1

    id_max = injected_active_current[pos]

    # Cut list values
    injected_active_current = injected_active_current[pos:]
    time = time[pos:]

    id_not_increase = True
    first_id_value = -1
    for i in range(len(injected_active_current)):
        pos = len(injected_active_current) - (i + 1)
        if injected_active_current[pos] > id_max:
            first_id_value = time[pos]
            id_not_increase = False
            break

    return first_id_value, id_not_increase


def get_AVR_x(
    time: list, curve: list, target_values: list, sim_t_event_end: float
) -> tuple[bool, float]:
    """Gets the time required, from the trigger of the event, for the values of the curve to be
    within 5% of the values of a target curve.

    Parameters
    ----------
    time: list
        List of time instants that make up the curve
    curve: list
        List of values that make up the curve
    target_values: list
        List of target values that make up the curve
    sim_t_event_end: float
        Instant of time when the event is triggered

    Returns
    -------
    bool
        True if the curve is within 5% of the target value, False otherwise
    int
        Time in which the curve values are not within 5% of the values of a target curve
    """
    pos_t_event = 0
    while sim_t_event_end > time[pos_t_event]:
        pos_t_event += 1

    # Cut list values
    curve = curve[pos_t_event:]
    target_values = target_values[pos_t_event:]
    time = time[pos_t_event:]

    pass_AVR_check = True
    error_time = -1
    for i in range(len(curve)):
        if 0.05 < abs(curve[i] - target_values[i]) / target_values[i]:
            pass_AVR_check = False
            error_time = time[i] - sim_t_event_end
            break

    return pass_AVR_check, error_time


def check_frequency(threshold: float, frequency: list, time: list) -> tuple[bool, float]:
    """Gets the time when the frequency is within the given threshold.

    Parameters
    ----------
    threshold: float
        Threshold that the curve must reach
    frequency: list
        Frequency curve
    time: list
        List of time instants that make up the curve

    Returns
    -------
    bool
        True if the frequency is within the given threshold, False otherwise
    float
        time when the frequency is not within the given threshold
    """
    error_time = -1
    pass_test = True
    for i in range(len(frequency)):
        if frequency[i] > (1.0 + threshold) or frequency[i] < (1.0 - threshold):
            pass_test = False
            error_time = time[i]
            break

    return pass_test, error_time


def mean_error(signal: list, reference: list, step_magnitude: float) -> float:
    """Gets the mean error between two signals.

    Parameters
    ----------
    signal: list
        Input signal
    reference: list
        Reference signal
    step_magnitude: float
        Magnitude of the variation

    Returns
    -------
    float
        The mean error
    """
    if len(signal) != len(reference):
        raise ValueError("signal and reference values have different length")

    # Only the array is needed for error calculations, it is not required to modify values so
    # it is not necessary to make a copy of the list.
    return (np.asarray(signal) - np.asarray(reference)).mean() / step_magnitude


def mean_absolute_error(signal: list, reference: list, step_magnitude: float) -> float:
    """Gets the mean absolute error between two signals.

    Parameters
    ----------
    signal: list
        Input signal
    reference: list
        Reference signal
    step_magnitude: float
        Magnitude of the variation

    Returns
    -------
    float
        The mean absolute error
    """
    if len(signal) != len(reference):
        raise ValueError("signal and reference values have different length")

    # Only the array is needed for error calculations, it is not required to modify values so
    # it is not necessary to make a copy of the list.
    return abs(np.asarray(signal) - np.asarray(reference)).mean() / step_magnitude


def maximum_error(signal: list, reference: list, step_magnitude: float) -> float:
    """Gets the maximum error between two signals.

    Parameters
    ----------
    signal: list
        Input signal
    reference: list
        Reference signal
    step_magnitude: float
        Magnitude of the variation

    Returns
    -------
    float
        The maximum error
    """
    if len(signal) != len(reference):
        raise ValueError("signal and reference values have different length")

    total_values = len(signal)
    if total_values == 0:
        return 0

    return max(abs(signal - reference)) / step_magnitude


def maximum_error_position(time: list, signal: list, reference: list) -> tuple[float, float]:
    """Gets the position of the maximum error between two signals.

    Parameters
    ----------
    time: list
        Input signal
    signal: list
        Input signal
    reference: list
        Reference signal

    Returns
    -------
    float
        Time in the maximum error
    float
        Signal value in the maximum error
    """
    if len(signal) != len(reference):
        raise ValueError(
            "signal and reference values have different length: "
            f"{len(signal)} != {len(reference)}."
        )

    total_values = len(signal)
    if total_values == 0:
        return 0

    errors = abs(signal - reference)
    pos = errors.idxmax()
    return time.iloc[pos], signal.iloc[pos]


def get_response_time(percent: float, time: list, curve: list, sim_t_event_start: float) -> float:
    """Gets the time when the curve reaches a value equivalent to a percentage of its target value
    for the first time.

    Parameters
    ----------
    percent: float
        Percentage of the target value
    time: list
        List of time instants that make up the curve
    curve: list
        List of values that make up the curve
    sim_t_event_start: float
        Instant of time when the event is triggered

    Returns
    -------
    float
        Time when the percent is reached after the event
    """
    # Get curves file and stable time
    if len(time) != len(curve):
        raise ValueError("curve values and time values have different length")

    pos_t_event = 0
    while sim_t_event_start > time[pos_t_event] and pos_t_event < len(time) - 1:
        pos_t_event += 1

    # Cut list values
    time = time[pos_t_event:]
    curve = curve[pos_t_event:]

    # Get the tube
    mean_val = curve[-1]
    mean_val_max = mean_val + abs(percent * mean_val)
    mean_val_min = mean_val - abs(percent * mean_val)

    for pos in range(len(curve)):
        if mean_val_min < curve[pos] < mean_val_max:
            pos -= 1
            break

    if pos < 0:
        pos = 0

    # Returns the time when the percent is reached after the event
    if time[pos] < sim_t_event_start:
        ret_val = 0
    else:
        ret_val = time[pos] - sim_t_event_start
    return ret_val


def get_settling_time(
    percent: float, time: list, curve: list, sim_t_event_start: float
) -> tuple[float, int, float, float, float]:
    """Gets the time when the curve reaches a value equivalent to a percentage of its target value.

    Parameters
    ----------
    percent: float
        Percentage of the target value
    time: list
        List of time instants that make up the curve
    curve: list
        List of values that make up the curve
    sim_t_event_start: float
        Instant of time when the event is triggered

    Returns
    -------
    float
        Time when the percent is reached after the event
    int
        Position in the curve
    float
        Min value in the tolerance tube
    float
        Max value in the tolerance tube
    float
        First value in the tolerance tube
    """
    # Get curves file and stable time
    if len(time) != len(curve):
        raise ValueError("curve values and time values have different length")

    # Get the tube
    mean_val = curve[-1]
    mean_val_max = mean_val + abs(percent * mean_val)
    mean_val_min = mean_val - abs(percent * mean_val)

    for i in range(len(curve)):
        pos = len(curve) - (i + 1)
        if curve[pos] < mean_val_min or curve[pos] > mean_val_max:
            break

    # Returns the time when the percent is reached after the event
    if time[pos] < sim_t_event_start:
        ret_val = 0
    else:
        ret_val = time[pos] - sim_t_event_start
    return ret_val, pos, mean_val_min, mean_val_max, curve[pos]


def get_reached_time(
    percentage: float, time: list, curve: list, sim_t_event_start: float
) -> tuple[float, float]:
    """Gets the time when the curve reaches a given threshold.

    Parameters
    ----------
    percentage: float
        Percentage of the final value that the curve must reach
    time: list
        List of time instants that make up the curve
    curve: list
        List of values that make up the curve
    sim_t_event_start: float
        Instant of time when the event is triggered

    Returns
    -------
    float
        Time when the percent is reached after the event
    float
        Target value
    """
    # Get curves file and stable time
    if len(time) != len(curve):
        raise ValueError("curve values and time values have different length")

    pos_t_event = 0
    while sim_t_event_start > time[pos_t_event] and pos_t_event < len(time) - 1:
        pos_t_event += 1

    stable_value = curve[pos_t_event - 1]

    difference_val = curve[-1] - stable_value
    objective_value = stable_value + percentage * difference_val

    # Cut list values
    time = time[pos_t_event:]
    curve = curve[pos_t_event:]

    pos = 0
    if difference_val > 0:
        while pos < len(curve) and curve[pos] < objective_value:
            pos += 1
    else:
        while pos < len(curve) and curve[pos] > objective_value:
            pos += 1

    if pos == len(curve):
        pos = len(curve) - 1

    # Returns the time when the percent is reached after the event
    if time[pos] < sim_t_event_start:
        ret_val = 0
    else:
        ret_val = time[pos] - sim_t_event_start
    return ret_val, objective_value


def get_overshoot(curve: list) -> float:
    """Gets the difference between the peak of the curve and the mean stability value

    Parameters
    ----------
    curve: list
        List of values that make up the curve

    Returns
    -------
    float
        Overshoot of the curve compared to the mean stability value
    """
    overshoot = max(curve) - curve[-1]
    return overshoot


def get_value_error(
    time: list,
    curve: list,
    sim_t_event_start: float,
    event_duration: float,
    freq0: float,
    freq_peak: float,
) -> float:
    """Gets the difference between the curve and the ideal ramp values

    Parameters
    ----------
    time: list
        List of time instants that make up the curve
    curve: list
        List of values that make up the curve
    sim_t_event_start: float
        Instant of time when the event is triggered
    event_duration: float
        Duration of the event
    freq0: float
        Initial frequency in pu
    freq_peak: float
        Frequency peak in pu

    Returns
    -------
    float
        Ramp error of the curve compared to the ideal ramp
    """
    # Get start and ending indexes of the ramp
    ind = 0
    while sim_t_event_start - event_duration > time[ind] and ind < len(time) - 1:
        ind += 1

    ind_fin = 0
    while sim_t_event_start > time[ind_fin] and ind_fin < len(time) - 1:
        ind_fin += 1

    # Cut list values
    curve = curve[ind:ind_fin]

    # Frequency ramp from +500 mHz to 2 Hz/s on the AC source
    ideal_ramp = np.linspace(freq0, freq0 + freq_peak, len(curve), False)
    ramp_error = max(abs(curve - ideal_ramp))
    return ramp_error


def get_time_lag(
    time: list,
    curve: list,
    sim_t_event_start: float,
    event_duration: float,
) -> float:
    """Gets the difference between the calculated time of the curve and the ideal time values

    Parameters
    ----------
    time: list
        List of time instants that make up the curve
    curve: list
        List of values that make up the curve
    sim_t_event_start: float
        Instant of time when the event is triggered
    event_duration: float
        Duration of the event

    Returns
    -------
    float
        Ramp time error of the curve
    """
    # Get curves file and stable time
    if len(time) != len(curve):
        raise ValueError("curve values and time values have different length")

    # Get start and ending indexes of the ramp
    ind = 0
    while sim_t_event_start - event_duration > time[ind] and ind < len(time) - 1:
        ind += 1

    ind_fin = 0
    while sim_t_event_start > time[ind_fin] and ind_fin < len(time) - 1:
        ind_fin += 1

    # Cut list values
    time = time[ind:ind_fin]

    ideal_time = np.linspace(
        sim_t_event_start - event_duration, sim_t_event_start, len(time), False
    )
    # The curves now are not in per unit => the error is big
    ramp_time_lag = max(abs(time - ideal_time))
    return ramp_time_lag
