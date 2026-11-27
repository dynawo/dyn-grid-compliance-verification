#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from typing import Optional

from dycov.configuration.cfg import config
from dycov.report.tables import ran_with

_CONDITIONS = (
    (".Model", "SCR", "SCR"),
    (".Model", "switched_SCR", "SCR with the switched line in service"),
    (".Model", "line_XPu", "Line reactance (pu)"),
    (".Model", "pdr_P", "$P$"),
    (".Model", "pdr_Q", "$Q$"),
    (".Model", "pdr_U", "$U$"),
    (".Event", "connect_event_to", "Stepped setpoint"),
    (".Event", "setpoint_step_value", "Step (or depth of the voltage dip)"),
    (".Event", "grid_phase_jump", "Phase jump of the grid voltage (rad)"),
    (".Event", "grid_voltage_step", "Step of the grid voltage (pu)"),
    (".Event", "grid_frequency0", "Grid frequency before the event (Hz)"),
    (".Event", "grid_rocof", "Rate of change of the grid frequency (Hz/s)"),
    (".Event", "sim_t_event_start", "Start of the event (s)"),
    (".Event", "fault_duration", "Duration of the event (s)"),
)


# The value a definition gives, stored under the name of the event that applies it: the step of a
# high-impedance fault is the dip its search aims at, that of the grid frequency its own step.
_STORED_AS = {"setpoint_step_value": ("setpoint_step_value", "hiz_dip", "grid_frequency_step")}


def _value(key: str, ran_with_conditions: dict) -> str:
    stored = (
        ran_with.format_value(name, ran_with_conditions) for name in _STORED_AS.get(key, (key,))
    )
    return next((value for value in stored if value), "")


def create_map(operating_condition: str, ran_with_conditions: Optional[dict] = None) -> list:
    """Creates a list to populate the table of the conditions of a test in the LaTeX reports,
    for a page shared by several tests, which cannot spell them out itself.

    Parameters
    ----------
    operating_condition: str
        PCS.Benchmark.OperatingCondition name of the test
    ran_with_conditions: Optional[dict]
        The conditions the simulation of the test ran with, once those definitions are
        resolved, by the option that defines each one

    Returns
    -------
    list
        The label and the definition of each condition the PCS description gives the test,
        and the value the test ran with, empty when it did not run
    """
    conditions = []
    for suffix, key, label in _CONDITIONS:
        definition = config.get_value(operating_condition + suffix, key)
        if definition:
            value = _value(key, ran_with_conditions or {})
            conditions.append([label, rf"\texttt{{\detokenize{{{definition}}}}}", value])
    return conditions
