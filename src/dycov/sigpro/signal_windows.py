#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from collections import namedtuple

import numpy as np
import pandas as pd

from dycov.configuration.cfg import config
from dycov.sanity_checks import parameter_checks

Exclusion_zones = namedtuple(
    "Exclusion_zones",
    [
        "t_windowLPF_excl_start",
        "t_windowLPF_excl_end",
        "t_integrator_tol",
        "t_faultLPF_excl",
        "t_faultQS_excl",
        "t_clearQS_excl",
    ],
)


def _get_exclusion_zones(
    setpoint_tracking_controlled_magnitude: bool,
) -> Exclusion_zones:
    t_windowLPF_excl_start = config.get_float("GridCode", "t_windowLPF_excl_start", 0.020)
    t_windowLPF_excl_end = config.get_float("GridCode", "t_windowLPF_excl_end", 0.020)
    t_integrator_tol = config.get_float("GridCode", "t_integrator_tol", 0.000001)
    if setpoint_tracking_controlled_magnitude:
        t_faultQS_excl = max(0.0, t_windowLPF_excl_start)
        t_clearQS_excl = max(0.0, t_windowLPF_excl_start)
    else:
        t_faultQS_excl = max(
            config.get_float("GridCode", "t_faultQS_excl", 0.020), t_windowLPF_excl_start
        )
        t_clearQS_excl = max(
            config.get_float("GridCode", "t_clearQS_excl", 0.060), t_windowLPF_excl_start
        )
    t_faultLPF_excl = max(
        config.get_float("GridCode", "t_faultLPF_excl", 0.050), t_windowLPF_excl_end
    )

    return Exclusion_zones(
        t_windowLPF_excl_start,
        t_windowLPF_excl_end,
        t_integrator_tol,
        t_faultLPF_excl,
        t_faultQS_excl,
        t_clearQS_excl,
    )


def _get_windows_times(
    time_values: list,
    t_fault: float,
    fault_duration: float,
    exclusion_zones: Exclusion_zones,
) -> tuple[float, float, float, float, float, float]:
    if fault_duration > time_values[-1]:
        fault_duration = 0.0

    t_clear = t_fault + fault_duration

    # This is what the current DTR Fiche I16 says:
    # On the second page (which is page 170 on footer):
    # "Les fenêtres d’observation doivent être adaptées. Conformément à la norme IEC 61400-27-2
    # nous préconisons 1 secondes pour la période avant événement (régime établi initial) et
    # 5 secondes après événement."
    pre_windows_len = 1.0
    parameter_checks.check_t_fault(time_values[0], t_fault, pre_windows_len)

    t_w1_end = t_fault - exclusion_zones.t_integrator_tol - exclusion_zones.t_faultLPF_excl
    t_w1_init = t_w1_end - pre_windows_len
    if t_w1_init < time_values[0]:
        t_w1_init = time_values[0]

    t_w2_init = t_fault + exclusion_zones.t_integrator_tol + exclusion_zones.t_faultQS_excl
    t_w2_end = t_clear - exclusion_zones.t_integrator_tol - exclusion_zones.t_windowLPF_excl_end

    t_w3_init = t_clear + exclusion_zones.t_integrator_tol + exclusion_zones.t_clearQS_excl
    t_w3_end = time_values[-1] - exclusion_zones.t_windowLPF_excl_end

    return t_w1_init, t_w1_end, t_w2_init, t_w2_end, t_w3_init, t_w3_end


def filter_windows(time_values: list, t_fault: float, fault_duration: float) -> dict:
    """Calculate the windows that the low-pass filter treats separately.

    Each event is a discontinuity of the signal, so the filter is applied between consecutive
    events and never across one: before the event, while it lasts and after it.

    Parameters
    ----------
    time_values: list
        list with all time values
    t_fault: float
        Start time of an event in the curve
    fault_duration: float
        Duration of the event in the curve

    Returns
    -------
    dict
        The "before", "during" and "after" windows, each as a (t_from, t_to) tuple.
    """
    if fault_duration > time_values[-1]:
        fault_duration = 0.0

    t_clear = t_fault + fault_duration

    return {
        "before": (time_values[0], t_fault),
        "during": (t_fault, t_clear),
        "after": (t_clear, time_values[-1]),
    }


def calculate(
    time_values: list,
    t_fault: float,
    fault_duration: float,
    setpoint_tracking_controlled_magnitude: bool,
) -> dict:
    """Calculate validation and signal-processing time windows for an event.

    This function computes the "before", "during", and "after" time windows used
    both for validation checks and for signal processing (e.g. low-pass filtering),
    taking into account exclusion zones defined by the Grid Code configuration.

    The exclusion rules depend on whether the setpoint tracking concerns a
    controlled magnitude.


    Parameters
    ----------
    time_values: list
        list with all time values
    t_fault: float
        Start time of an event in the simulated curve
    fault_duration: float
        Duration of the event in the simulated curve
    t_integrator_tol: float
        Numerical integrator time tolerance
    setpoint_tracking_controlled_magnitude: bool
        Setpoint tracking controlled magnitude.

    Returns
    -------
    dict
        Dictionary with the windows positions of the windows.
    """

    exclusion_zones = _get_exclusion_zones(
        setpoint_tracking_controlled_magnitude,
    )

    t_w1_init, t_w1_end, t_w2_init, t_w2_end, t_w3_init, t_w3_end = _get_windows_times(
        time_values,
        t_fault,
        fault_duration,
        exclusion_zones,
    )

    return {
        "validate": {
            "before": (t_w1_init, t_w1_end),
            "during": (t_w2_init, t_w2_end),
            "after": (t_w3_init, t_w3_end),
        },
        "sigpro": filter_windows(time_values, t_fault, fault_duration),
        "exclusion-data": {  # Exclusion data for the windows for debugging purposes
            "t_windowLPF_excl_start": exclusion_zones.t_windowLPF_excl_start,
            "t_windowLPF_excl_end": exclusion_zones.t_windowLPF_excl_end,
            "t_integrator_tol": exclusion_zones.t_integrator_tol,
            "t_faultLPF_excl": exclusion_zones.t_faultLPF_excl,
            "t_faultQS_excl": exclusion_zones.t_faultQS_excl,
            "t_clearQS_excl": exclusion_zones.t_clearQS_excl,
        },
    }


def get(curves: pd.DataFrame, t_from: float, t_to: float) -> pd.DataFrame:
    """Obtain the curves in the given range from the input curves.

    Parameters
    ----------
    curves: DataFrame
        Curves to be windowed.
    t_from: float
        Start time of the range
    t_to: float
        End time of the range

    Returns
    -------
    DataFrame
        Curves in the range.
    """
    time_values = list(curves["time"])
    w_init_pos = np.searchsorted(time_values, t_from)
    w_end_pos = np.searchsorted(time_values, t_to)

    # Create the new curves file
    wcurves = dict()
    for key in curves:
        wcurves[key] = list(curves[key])[w_init_pos:w_end_pos]

    return pd.DataFrame(wcurves)
