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

_BUS_PREFIX = "BusPDR_BUS_"
_GEN_SUFFIX = "_GEN_"
_XFMR_SUFFIX = "_XFMR_"

_VARIABLE_LABELS = {
    "IpInjTerminal": "Ip",
    "IqInjTerminal": "Iq",
    "AVRSetpointPu": "AVR Setpoint",
    "MagnitudeControlledByAVRPu": "AVR Magnitude",
    "UPuInjTerminal": "Voltage",
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


@dataclass(frozen=True)
class CurveStyle:
    color: str
    style: str


def is_controlled_magnitude(curve_name: str, column_name: str) -> bool:
    if curve_name == "BusPDR_BUS_ActivePower":
        return column_name == "P"
    if curve_name == "BusPDR_BUS_ReactivePower":
        return column_name == "Q"
    if curve_name == "BusPDR_BUS_ActiveCurrent":
        return column_name == "P"
    if curve_name == "BusPDR_BUS_ReactiveCurrent":
        return column_name == "Q"
    if "IpInjTerminal" in curve_name:
        return column_name == "P"
    if "IqInjTerminal" in curve_name:
        return column_name == "Q"
    if "UPuInjTerminal" in curve_name:
        return column_name == "V"
    if curve_name == "BusPDR_BUS_Voltage":
        return column_name == "V"
    if curve_name == "NetworkFrequencyPu":
        return column_name == "$\\omega"

    return False


def get_measurement_type(curve_name: str) -> str:
    if curve_name == "BusPDR_BUS_ActivePower":
        return "active_power"
    if curve_name == "BusPDR_BUS_ReactivePower":
        return "reactive_power"
    if curve_name == "BusPDR_BUS_ActiveCurrent":
        return "active_current"
    if curve_name == "BusPDR_BUS_ReactiveCurrent":
        return "reactive_current"
    if "IpInjTerminal" in curve_name:
        return "active_current"
    if "IqInjTerminal" in curve_name:
        return "reactive_current"
    if "UPuInjTerminal" in curve_name:
        return "voltage"
    if curve_name == "BusPDR_BUS_Voltage":
        return "voltage"
    if curve_name == "NetworkFrequencyPu":
        return "frequency"

    return ""


def get_curve_style(variable_name: str, is_reference: bool = False) -> CurveStyle:
    if is_reference:
        return CurveStyle(color="#dd8452", style="-")
    if "IpInjTerminal" in variable_name:
        return CurveStyle(color="#64b5cd", style="-")
    if "IqInjTerminal" in variable_name:
        return CurveStyle(color="#8172b3", style="-")
    if "AVRSetpointPu" in variable_name:
        return CurveStyle(color="#8c8c8c", style=":")
    return CurveStyle(color="#4c72b0", style="-")


def get_variable_label(variable_name: str) -> str:
    for key, label in _VARIABLE_LABELS.items():
        if key in variable_name:
            return label
    return variable_name.replace(_BUS_PREFIX, "")


def get_equipment_label(curve_name: str) -> str:
    if _GEN_SUFFIX in curve_name:
        return curve_name.split(_GEN_SUFFIX)[0]
    if _XFMR_SUFFIX in curve_name:
        return curve_name.split(_XFMR_SUFFIX)[0]
    if curve_name.startswith(_BUS_PREFIX):
        return "PDR Bus"
    return ""


def build_curve_label(curve_name: str, role: str, show_equipment: bool = False) -> str:
    """Build a human-readable legend label for a curve.

    Parameters
    ----------
    curve_name: str
        Full internal curve name
    role: str
        Curve role: "calculated", "reference", "setpoint"
    show_equipment: bool
        Whether to include the equipment id in the label
    """
    variable_label = get_variable_label(curve_name)
    if show_equipment:
        equipment = get_equipment_label(curve_name)
        if equipment:
            return f"{variable_label} — {equipment} {role}"
    return f"{variable_label} {role}"


def build_figure_title(variables) -> str:
    """Build a human-readable figure title from FigureDescription.variables."""
    if isinstance(variables, str):
        return f"{get_variable_label(variables)} — PDR Bus"

    variable_labels = list(
        dict.fromkeys(
            get_variable_label(v["variable"])
            for v in variables
            if v["variable"] != "AVRSetpointPu"
        )
    )
    magnitude = " / ".join(variable_labels)

    equipment_type = variables[0]["type"]
    equipment = "PDR Bus" if equipment_type == "bus" else equipment_type.capitalize()

    return f"{magnitude} — {equipment}"
