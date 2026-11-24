#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import math
from typing import Callable, Optional

from dycov.configuration.cfg import config
from dycov.curves.voltage_dip import NO_FAULT_SENTINEL

_POWER_UNITS = {"ActivePowerSetpointPu": "MW", "ReactivePowerSetpointPu": "Mvar"}
_IN_PU_OF_SNREF = (
    "pdr_P",
    "pdr_Q",
    "Zcc",
    "line_RPu",
    "line_XPu",
    "switched_line_RPu",
    "switched_line_XPu",
    "fault_RPu",
    "fault_XPu",
)


def _s_nref() -> float:
    return config.get_float("Dynawo", "s_nref", 100.0)


def _numeric(write: Callable[[float, dict], str]) -> Callable[[object, dict], Optional[str]]:
    """A writer of a number, which writes nothing for a value that is not a finite one."""

    def written(value: object, conditions: dict) -> Optional[str]:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return write(number, conditions) if math.isfinite(number) else None

    return written


def _in(unit: str) -> Callable[[object, dict], Optional[str]]:
    return _numeric(lambda value, conditions: f"{value:.4g}{unit}")


def _power(unit: str) -> Callable[[object, dict], Optional[str]]:
    return _numeric(lambda value, conditions: f"{value * _s_nref():.4g} {unit} ({value:.4g} pu)")


def _step(value: object, conditions: dict) -> Optional[str]:
    unit = _POWER_UNITS.get(conditions.get("connect_event_to"))
    return _power(unit)(value, conditions) if unit else _in(" pu")(value, conditions)


def _duration(value: object, conditions: dict) -> Optional[str]:
    try:
        permanent = float(value) >= NO_FAULT_SENTINEL
    except (TypeError, ValueError):
        return None
    return "permanent" if permanent else _in(" s")(value, conditions)


def _frequency_step(value: object, conditions: dict) -> Optional[str]:
    f_nom = config.get_float("Dynawo", "f_nom", 50.0)
    return _numeric(lambda step, _: f"{step * f_nom:.4g} Hz ({step:.4g} pu)")(value, conditions)


def _setpoint(value: object, conditions: dict) -> Optional[str]:
    return rf"\texttt{{\detokenize{{{value}}}}}" if value else None


_angle = _numeric(
    lambda value, conditions: rf"{math.degrees(value):.4g}$^\circ$ ({value:.4g} rad)"
)


def _grid_line(magnitude: str) -> Callable[[dict], str]:
    def label(conditions: dict) -> str:
        lines = int(conditions.get("grid_lines", 1))
        if lines > 1:
            return f"{magnitude} of each of the {lines} lines of the grid"
        return f"{magnitude} of the line of the grid"

    return label


def _fixed(label: str) -> Callable[[dict], str]:
    return lambda conditions: label


def _short_circuit_impedance(conditions: dict) -> str:
    """A grid without lines has its infinite bus at the bus of the test, which the impedance
    the test defines then does not separate."""
    if "grid_lines" in conditions:
        return "Short-circuit impedance of the grid"
    return "Short-circuit impedance of the grid, not modelled"


# Each condition, by the option of the PCS that defines it, in the order the table lists them:
# how it is named, where {bus} is the bus of the operating point, and how its value is written.
_CONDITIONS = {
    "pdr_P": (_fixed("$P$ at {bus}"), _power("MW")),
    "pdr_Q": (_fixed("$Q$ at {bus}"), _power("Mvar")),
    "pdr_U": (_fixed("$U$ at {bus}"), _in(" pu")),
    "SCR": (_fixed("SCR of the grid"), _in("")),
    "switched_SCR": (_fixed("SCR with the switched line in service"), _in("")),
    "Zcc": (_short_circuit_impedance, _in(" pu")),
    "line_RPu": (_grid_line("Resistance"), _in(" pu")),
    "line_XPu": (_grid_line("Reactance"), _in(" pu")),
    "switched_line_RPu": (_fixed("Resistance of the switched line"), _in(" pu")),
    "switched_line_XPu": (_fixed("Reactance of the switched line"), _in(" pu")),
    "fault_RPu": (_fixed("Resistance of the fault"), _in(" pu")),
    "fault_XPu": (_fixed("Reactance of the fault"), _in(" pu")),
    "sim_t_event_start": (_fixed("Start of the event"), _in(" s")),
    "fault_duration": (_fixed("Duration of the event"), _duration),
    "connect_event_to": (_fixed("Stepped setpoint"), _setpoint),
    "setpoint_step_value": (_fixed("Step of the setpoint"), _step),
    "hiz_dip": (_fixed("Voltage dip the fault search aims at"), _in(" pu")),
    "grid_phase_jump": (_fixed("Phase jump of the grid voltage"), _angle),
    "grid_voltage_step": (_fixed("Step of the grid voltage"), _in(" pu")),
    "grid_frequency_step": (_fixed("Step of the grid frequency"), _frequency_step),
    "grid_frequency0": (_fixed("Grid frequency before the event"), _in(" Hz")),
    "grid_rocof": (_fixed("Rate of change of the grid frequency"), _in(" Hz/s")),
    "u_fault": (_fixed("Grid voltage during the fault"), _in(" pu")),
    "u_clear": (_fixed("Grid voltage when the fault clears"), _in(" pu")),
    "u_swell": (_fixed("Grid voltage during the swell"), _in(" pu")),
    "u_rec1": (_fixed("Grid voltage at the first stage of recovery"), _in(" pu")),
    "u_rec2": (_fixed("Grid voltage at the second stage of recovery"), _in(" pu")),
    "u_rec3": (_fixed("Grid voltage at the third stage of recovery"), _in(" pu")),
}


def format_value(key: str, conditions: dict) -> Optional[str]:
    """The value a test ran with for the option of its PCS that defines a condition, written
    for the LaTeX reports.

    Parameters
    ----------
    key: str
        The option that defines the condition
    conditions: dict
        The conditions the test ran with, by the option that defines each one

    Returns
    -------
    Optional[str]
        The value with its unit, None when the test did not run with that condition
    """
    if key not in _CONDITIONS or key not in conditions:
        return None
    return _CONDITIONS[key][1](conditions[key], conditions)


def create_map(results: dict, bus: str) -> list:
    """Creates a list to populate the table of the conditions a test ran with in the LaTeX
    reports, once the definitions of its description are resolved.

    Parameters
    ----------
    results: dict
        Results of the validations applied in the test
    bus: str
        The bus the operating point of the test is set at

    Returns
    -------
    list
        The label and the value of each condition the simulation of the test ran with, and
        the base of the values in pu; empty when nothing was simulated
    """
    conditions = results.get("ran_with") or {}
    rows = []
    for key, (label, _) in _CONDITIONS.items():
        value = format_value(key, conditions)
        if value is not None:
            rows.append([label(conditions).format(bus=bus), value])
    if any(key in conditions for key in _IN_PU_OF_SNREF):
        rows.append(["Base of the pu values", f"{_s_nref():g} MVA, nominal voltage"])
    return rows
