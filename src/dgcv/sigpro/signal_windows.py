#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import numpy as np
import pandas as pd

from dgcv.configuration.cfg import config
from dgcv.validation import sanity_checks


def _get_exclusion_zones(
    t_windowLPF_excl_start: float,
    t_windowLPF_excl_end: float,
    setpoint_tracking_controlled_magnitude: bool,
) -> tuple:
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

    return t_integrator_tol, t_faultLPF_excl, t_faultQS_excl, t_clearQS_excl


def _get_windows_times(
    time_values: list,
    t_fault: float,
    fault_duration: float,
    setpoint_tracking_controlled_magnitude: bool,
) -> tuple[float, float, float, float, float, float]:

    t_windowLPF_excl_start = config.get_float("GridCode", "t_windowLPF_excl_start", 0.020)
    t_windowLPF_excl_end = config.get_float("GridCode", "t_windowLPF_excl_end", 0.020)
    t_integrator_tol, t_faultLPF_excl, t_faultQS_excl, t_clearQS_excl = _get_exclusion_zones(
        t_windowLPF_excl_start,
        t_windowLPF_excl_end,
        setpoint_tracking_controlled_magnitude,
    )

    if fault_duration > time_values[-1]:
        fault_duration = 0.0

    t_clear = t_fault + fault_duration

    # This is what the current DTR Fiche I16 says:
    # On the second page (which is page 170 on footer):
    # "Les fenêtres d’observation doivent être adaptées. Conformément à la norme IEC 61400-27-2
    # nous préconisons 1 secondes pour la période avant événement (régime établi initial) et
    # 5 secondes après événement."
    pre_windows_len = 1.0
    sanity_checks.check_t_fault(time_values[0], t_fault, pre_windows_len)

    t_w1_init = t_fault - t_integrator_tol - t_faultLPF_excl - pre_windows_len
    if t_w1_init < time_values[0]:
        t_w1_init = time_values[0]
    t_w1_end = t_fault - t_integrator_tol - t_faultLPF_excl

    t_w2_init = t_fault + t_integrator_tol + t_faultQS_excl
    t_w2_end = t_clear - t_integrator_tol - t_windowLPF_excl_end

    t_w3_init = t_clear + t_integrator_tol + t_clearQS_excl
    t_w3_end = time_values[-1] - t_windowLPF_excl_end

    return t_w1_init, t_w1_end, t_w2_init, t_w2_end, t_w3_init, t_w3_end


def calculate(
    time_values: list,
    t_fault: float,
    fault_duration: float,
    setpoint_tracking_controlled_magnitude: bool,
) -> dict:
    """Calculate the positions to the windows.

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

    # Get the windows time values
    t_w1_init, t_w1_end, t_w2_init, t_w2_end, t_w3_init, t_w3_end = _get_windows_times(
        time_values, t_fault, fault_duration, setpoint_tracking_controlled_magnitude
    )

    w1_init_pos = np.searchsorted(time_values, t_w1_init)
    w1_end_pos = np.searchsorted(time_values, t_w1_end)

    w2_init_pos = np.searchsorted(time_values, t_w2_init)
    w2_end_pos = np.searchsorted(time_values, t_w2_end)

    w3_init_pos = np.searchsorted(time_values, t_w3_init)
    w3_end_pos = np.searchsorted(time_values, t_w3_end)

    return {
        "before": slice(w1_init_pos, w1_end_pos - 1),
        "during": slice(w2_init_pos, w2_end_pos - 1),
        "after": slice(w3_init_pos, w3_end_pos - 1),
        "times": {  # For debugging purposes
            "before": (t_w1_init, t_w1_end),
            "during": (t_w2_init, t_w2_end),
            "after": (t_w3_init, t_w3_end),
        },
    }


def get(curves: pd.DataFrame, range: slice) -> pd.DataFrame:
    """Obtain the curves in the given range from the input curves.

    Parameters
    ----------
    curves: DataFrame
        Curves to be windowed.
    range: slice
        Range to be extracted.

    Returns
    -------
    DataFrame
        Curves in the range.
    """
    # Create the new curves file
    wcurves = dict()
    for key in curves:
        wcurves[key] = list(curves[key])[range]

    return pd.DataFrame(wcurves)
