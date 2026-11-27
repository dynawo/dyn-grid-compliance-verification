#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#
"""Whether a record of curves runs far enough past its event to be compared."""

import pandas as pd

from dycov.configuration.cfg import config
from dycov.logging import dycov_logging
from dycov.sigpro import signal_windows, sigpro


def _seconds(value: float) -> str:
    return f"{value:.10g} s"


def _end_the_comparison_needs(
    curves: pd.DataFrame, event_start: float, fault_duration: float
) -> float:
    """The instant the curves must reach for the comparison to keep a window after the event:
    the end of the event, one that lasts past the last instant their resampling to a fixed step
    keeps being permanent and counting as none, the exclusion zones around that window and two
    steps of the common time grid, all of it before that last instant."""
    end_of_curves = curves["time"].max()
    last_resampled = (
        sigpro.resample_to_fixed_step(curves[["time"]])["time"].iloc[-1]
        if curves["time"].nunique() > 1
        else end_of_curves
    )
    event_end = event_start + (fault_duration if fault_duration <= last_resampled else 0.0)
    exclusion = signal_windows._get_exclusion_zones(False)
    return (
        event_end
        + exclusion.t_integrator_tol
        + exclusion.t_clearQS_excl
        + 2 * config.get_float("GridCode", "t_com", 0.002)
        + exclusion.t_windowLPF_excl_end
        + (end_of_curves - last_resampled)
    )


def curves_reach_past_the_event(
    cfg_oc_name: str, kind: str, event_start: float, fault_duration: float, curves: pd.DataFrame
) -> bool:
    """Whether *curves* run far enough past their event to be compared, saying why they do not.

    Parameters
    ----------
    cfg_oc_name: str
        Name of the test, ``PCS.Benchmark.OperatingCondition``, that of its dictionary.
    kind: str
        Which curves they are, ``reference`` or ``producer``.
    event_start: float
        Instant of the event, in s.
    fault_duration: float
        Duration of the event, in s; one longer than the curves is a permanent event.
    curves: pd.DataFrame
        The curves, with their ``time`` column.

    Returns
    -------
    bool
        True when they can be compared.
    """
    required_end = _end_the_comparison_needs(curves, event_start, fault_duration)
    end_of_curves = curves["time"].max()
    if end_of_curves >= required_end:
        return True
    dycov_logging.get_logger("Curves Importer").warning(
        f"The {kind} curves of '{cfg_oc_name}.dict' place the event at {_seconds(event_start)}, "
        f"but end at {_seconds(end_of_curves)}: the comparison needs them to reach "
        f"{_seconds(required_end)}, so the test runs as if it had no {kind} curves"
    )
    return False
