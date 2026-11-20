#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from dycov.configuration.cfg import config

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


def create_map(operating_condition: str) -> list:
    """Creates a list to populate the table of the conditions of a test in the LaTeX reports,
    for a page shared by several tests, which cannot spell them out itself.

    Parameters
    ----------
    operating_condition: str
        PCS.Benchmark.OperatingCondition name of the test

    Returns
    -------
    list
        The label and the definition of each condition the PCS description gives the test
    """
    conditions = []
    for suffix, key, label in _CONDITIONS:
        definition = config.get_value(operating_condition + suffix, key)
        if definition:
            conditions.append([label, rf"\texttt{{\detokenize{{{definition}}}}}"])
    return conditions
