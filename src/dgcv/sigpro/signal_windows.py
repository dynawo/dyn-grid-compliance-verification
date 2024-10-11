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


def calculate(
    time_values: list,
    t_fault: float,
    fault_duration: float,
    t_integrator_tol: float,
    t_faultLP_excl: float,
    t_faultQS_excl: float,
    t_clearQS_excl: float,
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
    t_faultLP_excl: float
        Exclusion windows on transients when inserting the fault to mitigate the effect
        of LP filtering (in seconds)
    t_faultQS_excl: float
        Exclusion windows on transients on insertion of the fault (in seconds)
    t_clearQS_excl: float
        Exclusion windows on transients on elimination of the fault (in seconds)

    Returns
    -------
    dict
        Dictionary with the event windows
    """

    if fault_duration > time_values[-1]:
        fault_duration = 0.0

    t_clear = t_fault + fault_duration

    # This is what the current DTR Fiche I16 says:
    # On the second page (which is page 170 on footer):
    # "Les fenêtres d’observation doivent être adaptées. Conformément à la norme IEC 61400-27-2
    # nous préconisons 1 secondes pour la période avant événement (régime établi initial) et
    # 5 secondes après événement."
    pre_windows_len = 1.0
    t_init = t_fault - t_integrator_tol - t_faultLP_excl - pre_windows_len
    if t_init < time_values[0]:
        t_init = time_values[0]

    w1_init_pos = np.searchsorted(time_values, t_init)
    w1_end_pos = np.searchsorted(time_values, t_fault - t_integrator_tol - t_faultLP_excl)

    w2_init_pos = np.searchsorted(time_values, t_fault + t_integrator_tol + t_faultQS_excl)
    w2_end_pos = np.searchsorted(time_values, t_clear - t_integrator_tol)

    w3_init_pos = np.searchsorted(time_values, t_clear + t_integrator_tol + t_clearQS_excl)
    w3_end_pos = len(time_values)

    return {
        "before": slice(w1_init_pos, w1_end_pos - 1),
        "during": slice(w2_init_pos, w2_end_pos - 1),
        "after": slice(w3_init_pos, w3_end_pos - 1),
    }


def get(
    curves: pd.DataFrame, event_windows: dict
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Create the new curves file
    before = dict()
    during = dict()
    after = dict()
    before_range = event_windows["before"]
    during_range = event_windows["during"]
    after_range = event_windows["after"]
    for key in curves:
        before[key] = list(curves[key])[before_range]
        during[key] = list(curves[key])[during_range]
        after[key] = list(curves[key])[after_range]

    return pd.DataFrame(before), pd.DataFrame(during), pd.DataFrame(after)
