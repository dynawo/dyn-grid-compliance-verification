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

# Absolute tolerance used when a magnitude is near zero and dividing by it directly
# would be unstable (e.g. get_static_diff, get_AVR_x).
ATOL = 1.0e-6
# Threshold below which relative tolerance becomes meaningless
TUBE_TARGET_THRESHOLD = 0.01
# Absolute tolerance used when target is small
TUBE_ABSOLUTE_TOL = 0.02


def get_ss_tolerance(setpoint_variation: float) -> float:
    tolerance = config.get_float("GridCode", "thr_ss_tol", 0.002)
    if setpoint_variation > 0.0:
        tolerance = setpoint_variation * tolerance
    return tolerance


def _compute_tube(target: float, percent: float) -> tuple[float, float]:
    """Compute tolerance tube around target value.

    If target is near zero (<TUBE_TARGET_THRESHOLD), use absolute ±TUBE_ABSOLUTE_TOL.
    Otherwise, use relative tolerance based on percent.
    """
    if abs(target) < TUBE_TARGET_THRESHOLD:
        return target - TUBE_ABSOLUTE_TOL, target + TUBE_ABSOLUTE_TOL
    else:
        delta = abs(percent * target)
        return target - delta, target + delta


def check_relative_error(
    calculated_value: float,
    reference_value: float,
    rtol: float,
    zero_reference_atol: float,
) -> tuple[float, bool]:
    """Check if the calculated value is within the relative-error tolerance of the
    reference value, per the DTR's Fiche I16 criteria (temps de reaction/montee/
    etablissement, depassement) -- used for reaction/rise/settling time as well as
    overshoot, which is a magnitude, not a time. All are expressed by the DTR as a
    relative error in %, but the DTR defines no criterion for when the reference value
    is exactly zero (dividing by it is undefined). This is a realistic case, not just a
    corner case -- e.g. a reference curve with no overshoot at all (a well-damped,
    monotonic response) has reference_value == 0 -- so it falls back to an absolute
    tolerance instead: a calculated value close enough to zero is still compliant, even
    though no relative error can be computed.

    Parameters
    ----------
    calculated_value: float
        Calculated value
    reference_value: float
        Reference value
    rtol: float
        Relative tolerance (fraction, e.g. 0.10 for 10%)
    zero_reference_atol: float
        Absolute tolerance used only when reference_value == 0.0. Not derived from the
        DTR -- tentative, unit-specific (seconds for reaction/rise/settling time, pu for
        overshoot), pending confirmation with RTE.

    Returns
    -------
    float
        Relative error (in %) between the calculated and reference value; or the
        absolute value of calculated_value if reference_value == 0.0.
    bool
        True if the calculated value is within tolerance of the reference: below rtol
        when reference_value != 0.0, or within zero_reference_atol otherwise.
    """
    if reference_value == 0.0:
        return abs(calculated_value), abs(calculated_value) <= zero_reference_atol

    relative_error = 100 * abs(calculated_value - reference_value) / reference_value
    return relative_error, relative_error < rtol * 100


def is_invalid_test(
    time: list, voltage: list, active: list, reactive: list, t_event: float
) -> bool:
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
        f"Start values: V: {voltage[0]}, P: {active[0]}, Q: {reactive[0]}"
    )

    # Get the steady-state value right before the event
    v_init = voltage[idx_t_event]
    p_init = active[idx_t_event]
    q_init = reactive[idx_t_event]
    dycov_logging.get_logger("Common Validation").debug(
        f"Steady-state values: V: {v_init}, P: {p_init}, Q: {q_init}"
    )

    # Get max diff between values after event vs the steady-state value right before
    v_max_diff = max(abs(np.array(voltage[idx_t_event:]) - v_init))
    p_max_diff = max(abs(np.array(active[idx_t_event:]) - p_init))
    q_max_diff = max(abs(np.array(reactive[idx_t_event:]) - q_init))
    dycov_logging.get_logger("Common Validation").debug(
        f"Max diff: V: {v_max_diff}, P: {p_max_diff}, Q: {q_max_diff}"
    )

    # Check if this max diff is smaller than the tolerances
    rtol = thr_ss_tol  # i.e., 0.2% relative error
    atol = 0.1 * rtol  # i.e., when magnitudes are near 0.01, switch to abs error
    v_flat = math.isclose(v_max_diff, 0.0, rel_tol=rtol, abs_tol=atol)
    p_flat = math.isclose(p_max_diff, 0.0, rel_tol=rtol, abs_tol=atol)
    q_flat = math.isclose(q_max_diff, 0.0, rel_tol=rtol, abs_tol=atol)
    dycov_logging.get_logger("Common Validation").debug(
        f"Flat Curves: V: {v_flat}, P: {p_flat}, Q: {q_flat}"
    )

    return v_flat and p_flat and q_flat


def is_stable(time: list, curve: list, thr_ss_tol: float = 0.002) -> tuple[bool, int]:
    """
    Detects whether the signal reaches a steady-state and returns the
    first index from which it remains within tolerance until the end.

    Stability is defined as:
    The signal enters the tolerance band and never leaves it afterwards.

    Parameters
    ----------
    time: list
        List of time instants that make up the curve
    curve: list
        List of values that make up the curve
    thr_ss_tol: float
        Tolerance defining the steady-state band around the final value.

    Returns
    -------
    bool
        True if steady-state is reached, False otherwise
    int
        Index where steady-state begins, or -1 if not reached
    """
    atol = 0.01 * thr_ss_tol

    if len(time) != len(curve):
        raise ValueError("the curve values and its time series have different length")

    final_value = curve[-1]
    n = len(curve)

    for i in range(n):
        stable = True

        for j in range(i, n):
            if not math.isclose(curve[j], final_value, rel_tol=thr_ss_tol, abs_tol=atol):
                stable = False
                break

        if stable:
            return True, i

    return False, -1


def theta_pi(time: list, curve: list) -> bool:
    """Check whether the angle remains within the ±pi bounds.

    This check ensures that the angle does not exceed ±π during the simulation.

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
    if abs(cons_val) < ATOL:
        return math.fabs(end_val - cons_val)
    else:
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
    if abs(mean_val) < ATOL:
        mean_val_min = curve[-1] - abs(percent)
        mean_val_max = curve[-1] + abs(percent)
    else:
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
    mean_val = curve[-1]
    mean_val_min, mean_val_max = _compute_tube(mean_val, percent)

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
    mean_val = curve[-1]
    mean_val_min, _ = _compute_tube(mean_val, percent)

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
    imax: float,
    time: list,
    current_at_converter: list,
    active_current_at_converter: list,
) -> tuple[float, bool]:
    """Check that, when the generator current reaches Imax, reactive current is
    prioritized over active current (Id should not increase while saturated).

    Parameters
    ----------
    imax : float
        IMax value of the generator
    time : list
        Time vector
    current_at_converter : list
        Total current magnitude |I|
    active_current_at_converter : list
        Active current Id

    Returns
    -------
    float
        Time where Id increases while |I| >= Imax. -1 if no issue detected.
    bool
        True if the condition is respected, False otherwise
    """
    if not (len(time) == len(current_at_converter) == len(active_current_at_converter)):
        raise ValueError("All input lists must have the same length")

    TOL = 1e-3

    in_saturation = False
    id_ref = None
    first_id_value = -1
    id_not_increase = True

    for i in range(len(time)):
        Im = current_at_converter[i]
        Id = active_current_at_converter[i]

        if Im >= imax - TOL:
            # Entering saturation
            if not in_saturation:
                in_saturation = True
                id_ref = Id
            else:
                # Check condition only while saturated
                if Id > id_ref + TOL:
                    first_id_value = time[i]
                    id_not_increase = False
                    break

                # Update reference (Id should not increase, allow decrease)
                id_ref = min(id_ref, Id)

        else:
            # Leave saturation → reset logic
            in_saturation = False
            id_ref = None

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
        if abs(target_values[i]) < ATOL:
            error = abs(curve[i] - target_values[i])
        else:
            error = abs(curve[i] - target_values[i]) / target_values[i]
        if 0.05 < error:
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


def maximum_error_position(
    time: list, signal: list, reference: list, name: str
) -> tuple[float, float, float]:
    """Gets the position of the maximum error between two signals.

    Parameters
    ----------
    time: list
        Time values corresponding to the signals
    signal: list
        Input signal
    reference: list
        Reference signal
    name: str
        Signal name

    Returns
    -------
    float
        Time in the maximum error
    float
        Signal value in the maximum error
    float
        Reference value in the maximum error
    """
    if np.isnan(reference).all():
        dycov_logging.get_logger("Common Validation").warning(f"No reference values in {name}")
        return 0, 0.0

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
    return time.iloc[pos], signal.iloc[pos], reference.iloc[pos]


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
    mean_val_min, mean_val_max = _compute_tube(mean_val, percent)

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
    mean_val_min, mean_val_max = _compute_tube(mean_val, percent)

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
    if abs(difference_val) < ATOL:
        objective_value = stable_value + percentage
    else:
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
