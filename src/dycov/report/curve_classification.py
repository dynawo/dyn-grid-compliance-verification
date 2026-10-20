#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from dataclasses import dataclass

from dycov.curves.naming import ZONE1_INJECTOR_NODE_LABEL, get_bus_label

_BUS_PREFIX = "BusPDR_BUS_"
_GEN_SUFFIX = "_GEN_"
_SYNCCOND_SUFFIX = "_GEN_TSO_"
_LOAD_SUFFIX = "_LOAD_TSO_"
_XFMR_SUFFIX = "_XFMR_"
_SETPOINT_SUFFIX = "SetpointPu"

_VARIABLE_LABELS = {
    "ActiveCurrentInjTerminal": "Ip",
    "ReactiveCurrentInjTerminal": "Iq",
    "ActivePowerSetpointPu": "Active Power Setpoint",
    "ReactivePowerSetpointPu": "Reactive Power Setpoint",
    "VoltageSetpointPu": "Plant-level voltage regulation Setpoint",
    "MagnitudeControlledByAVRPu": "Plant-level voltage regulation Magnitude",
    "VoltageInjTerminal": "Voltage",
    "RotorSpeedPu": "Rotor Speed",
    "NetworkFrequencyPu": "Frequency",
    "InternalAngle": "Internal Angle",
    "Tap": "Tap",
    "ActivePower": "Active Power",
    "ReactivePower": "Reactive Power",
    "ActiveCurrent": "Active Current",
    "ReactiveCurrent": "Reactive Current",
    "Voltage": "Voltage",
}

# Zone 1 has no plant-level voltage regulation: its voltage setpoint is the unit's own.
_VARIABLE_LABELS_BY_ZONE = {1: {"VoltageSetpointPu": "Voltage Setpoint"}}


@dataclass(frozen=True)
class CurveStyle:
    """Visual style definition for a curve (color and line style)."""

    color: str
    style: str


def is_setpoint(variable_name: str) -> bool:
    """Whether a curve is a setpoint, which a figure draws over the magnitude it drives."""
    return variable_name.endswith(_SETPOINT_SUFFIX)


def get_curve_style(variable_name: str, is_reference: bool = False) -> CurveStyle:
    """Determine the plotting style for a curve based on its variable name and role.

    Parameters
    ----------
    variable_name: str
        Full internal variable name (e.g., "BusPDR_BUS_ActivePower", "modIInjTerminal")
    is_reference: bool
        Whether the curve corresponds to a reference trajectory (e.g., from a reference solution or
        a baseline method)

    Returns
    -------
    CurveStyle
        The color and line style to use for plotting the curve
    """
    if is_setpoint(variable_name):
        if is_reference:
            return CurveStyle(color="#dd8452", style="--")
        return CurveStyle(color="#8c8c8c", style=":")
    if is_reference:
        return CurveStyle(color="#dd8452", style="-")
    if "modIInjTerminal" in variable_name:
        return CurveStyle(color="#e2c22e", style="-")
    if "ActiveCurrentInjTerminal" in variable_name:
        return CurveStyle(color="#64b5cd", style="-")
    if "ReactiveCurrentInjTerminal" in variable_name:
        return CurveStyle(color="#8172b3", style="-")
    return CurveStyle(color="#4c72b0", style="-")


def get_variable_label(variable_name: str, zone: int = 0) -> str:
    """Determine a human-readable label for a variable based on its internal name.

    Parameters
    ----------
    variable_name: str
        Full internal variable name (e.g., "BusPDR_BUS_ActivePower", "modIInjTerminal")
    zone: int
        Validation zone (1 for Zone1, 3 for Zone3, 0 otherwise)

    Returns
    -------
    str
        A human-readable label for the variable (e.g., "Active Power", "|I|")
    """
    if "modIInjTerminal" in variable_name:
        return "|I|"
    for labels in (_VARIABLE_LABELS_BY_ZONE.get(zone, {}), _VARIABLE_LABELS):
        for key, label in labels.items():
            if key in variable_name:
                return label
    return variable_name.replace(_BUS_PREFIX, "")


def get_equipment_label(curve_name: str, zone: int = 0) -> str:
    """Determine a human-readable label for the equipment associated with a curve based on its
    internal name.

    Parameters
    ----------
    curve_name: str
        Full internal curve name
    zone: int
        Validation zone (1 for Zone1, 3 for Zone3, 0 otherwise)

    Returns
    -------
    str
        A human-readable label for the equipment (e.g., "PDR Bus", "GEN", "XFMR")
    """
    if _SYNCCOND_SUFFIX in curve_name:
        return curve_name.split(_SYNCCOND_SUFFIX)[0]
    if _LOAD_SUFFIX in curve_name:
        return curve_name.split(_LOAD_SUFFIX)[0]
    if _GEN_SUFFIX in curve_name:
        return curve_name.split(_GEN_SUFFIX)[0]
    if _XFMR_SUFFIX in curve_name:
        return curve_name.split(_XFMR_SUFFIX)[0]
    if curve_name.startswith(_BUS_PREFIX):
        return get_bus_label(zone)
    return ""


def build_curve_label(
    curve_name: str, role: str, show_equipment: bool = False, zone: int = 0
) -> str:
    """Build a human-readable legend label for a curve.

    Parameters
    ----------
    curve_name: str
        Full internal curve name
    role: str
        Curve role: "calculated" or "reference"
    show_equipment: bool
        Whether to include the equipment id in the label
    zone: int
        Validation zone (1 for Zone1, 3 for Zone3, 0 otherwise)

    Returns
    -------
    str
        A human-readable label for the curve (e.g., "Active Power — GEN calculated",
        "Active Power Setpoint — GEN reference")
    """
    variable_label = get_variable_label(curve_name, zone)
    if show_equipment:
        equipment = get_equipment_label(curve_name, zone)
        if equipment:
            return f"{variable_label} — {equipment} {role}"
    return f"{variable_label} {role}"


def build_figure_title(variables: str | list[dict], zone: int = 0) -> str:
    """Build a human-readable figure title from FigureDescription.variables.

    Parameters
    ----------
    variables: str | list[dict]
        The variables field from FigureDescription, which can be a single variable name or a list
        of dicts with "variable" and "type" keys.
    zone: int
        Validation zone (1 for Zone1, 3 for Zone3, 0 otherwise)

    Returns
    -------
    str
        A human-readable figure title (e.g., "Active Power — GEN", "Voltage — PDR Bus")
    """
    if isinstance(variables, str):
        return f"{get_variable_label(variables)} — {get_bus_label(zone)}"

    variable_labels = list(
        dict.fromkeys(
            get_variable_label(v["variable"]) for v in variables if not is_setpoint(v["variable"])
        )
    )
    magnitude = " / ".join(variable_labels)

    equipment_type = variables[0]["type"]
    if equipment_type == "bus":
        equipment = get_bus_label(zone)
    elif equipment_type == "sync_condenser":
        equipment = "Synchronous Condenser"
    elif zone == 1 and _is_injector_terminal_figure(variables):
        equipment = ZONE1_INJECTOR_NODE_LABEL
    else:
        equipment = equipment_type.capitalize()

    return f"{magnitude} — {equipment}"


def _is_injector_terminal_figure(variables: list[dict]) -> bool:
    return all("InjTerminal" in v["variable"] for v in variables if not is_setpoint(v["variable"]))
