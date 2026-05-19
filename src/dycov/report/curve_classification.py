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
_SYNCCOND_SUFFIX = "_GEN_TSO_"
_LOAD_SUFFIX = "_LOAD_TSO_"
_XFMR_SUFFIX = "_XFMR_"

_VARIABLE_LABELS = {
    "IpInjTerminal": "Ip",
    "IqInjTerminal": "Iq",
    "VoltageSetpointPu": "Plant-level voltage regulation Setpoint",
    "MagnitudeControlledByAVRPu": "Plant-level voltage regulation Magnitude",
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
    """Visual style definition for a curve (color and line style)."""

    color: str
    style: str


def is_controlled_magnitude(curve_name: str, column_name: str) -> bool:
    """Determine if a curve corresponds to a controlled magnitude (for setpoint tracking
    evaluation).

    Parameters
    ----------
    curve_name: str
        Full internal curve name
    column_name: str
        Column name (e.g., "P", "Q", "V") for multi-column curves

    Returns
    -------
    bool
        True if the curve corresponds to a controlled magnitude, False otherwise
    """
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
    """Determine the type of measurement for a given curve name.

    Parameters
    ----------
    curve_name: str
        Full internal curve name

    Returns
    -------
    str
        The type of measurement
    """
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
    if is_reference:
        return CurveStyle(color="#dd8452", style="-")
    if "modIInjTerminal" in variable_name:
        return CurveStyle(color="#e2c22e", style="-")
    if "IpInjTerminal" in variable_name:
        return CurveStyle(color="#64b5cd", style="-")
    if "IqInjTerminal" in variable_name:
        return CurveStyle(color="#8172b3", style="-")
    if "VoltageSetpointPu" in variable_name:
        return CurveStyle(color="#8c8c8c", style=":")
    return CurveStyle(color="#4c72b0", style="-")


def get_variable_label(variable_name: str) -> str:
    """Determine a human-readable label for a variable based on its internal name.

    Parameters
    ----------
    variable_name: str
        Full internal variable name (e.g., "BusPDR_BUS_ActivePower", "modIInjTerminal")
    Returns
    -------
    str
        A human-readable label for the variable (e.g., "Active Power", "|I|")
    """
    if "modIInjTerminal" in variable_name:
        return "|I|"
    for key, label in _VARIABLE_LABELS.items():
        if key in variable_name:
            return label
    return variable_name.replace(_BUS_PREFIX, "")


def get_equipment_label(curve_name: str) -> str:
    """Determine a human-readable label for the equipment associated with a curve based on its
    internal name.

    Parameters
    ----------
    curve_name: str

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

    Returns
    -------
    str
        A human-readable label for the curve (e.g., "Active Power — GEN calculated",
        "Voltage Setpoint — PDR Bus setpoint")
    """
    variable_label = get_variable_label(curve_name)
    if show_equipment:
        equipment = get_equipment_label(curve_name)
        if equipment:
            return f"{variable_label} — {equipment} {role}"
    return f"{variable_label} {role}"


def build_figure_title(variables: str | list[dict]) -> str:
    """Build a human-readable figure title from FigureDescription.variables.

    Parameters
    ----------
    variables: str | list[dict]
        The variables field from FigureDescription, which can be a single variable name or a list
        of dicts with "variable" and "type" keys.

    Returns
    -------
    str
        A human-readable figure title (e.g., "Active Power — GEN", "Voltage — PDR Bus")
    """
    if isinstance(variables, str):
        return f"{get_variable_label(variables)} — PDR Bus"

    variable_labels = list(
        dict.fromkeys(
            get_variable_label(v["variable"])
            for v in variables
            if v["variable"] != "VoltageSetpointPu"
        )
    )
    magnitude = " / ".join(variable_labels)

    equipment_type = variables[0]["type"]
    if equipment_type == "bus":
        equipment = "PDR Bus"
    elif equipment_type == "sync_condenser":
        equipment = "Synchronous Condenser"
    else:
        equipment = equipment_type.capitalize()

    return f"{magnitude} — {equipment}"
