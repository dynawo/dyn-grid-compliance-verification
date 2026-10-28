#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Naming of the connection-point bus in user-facing outputs.

Internally the tool models the connection bus as ``BusPDR`` for every zone. In the
outputs, "PDR" is reserved for the real connection point to the grid (Zone 3 and
electrical performance), while the internal connection point of the Zone 1 unit
model is named ``InternalNode1`` (called "Node1" in the DTR). The converter-output
node of the Zone 1 unit model, between the unit and its transformer, is named
``InternalNode2`` (called "Node2" in the DTR); the generator curves named after
``Node2`` are measured there.

Those curves used to be named after the injector terminal, and the powers at the node the
converter controls ended in ``ControlledPu``; the dictionaries of curves that name them so
are still read.

The network frequency is named ``NetworkFrequencyPu`` in every curve set the tool compares,
simulated or imported, so the figure that draws it finds it on both sides.
"""

import pandas as pd

INTERNAL_BUS_PREFIX = "BusPDR_BUS_"
ZONE1_BUS_PREFIX = "InternalNode1_BUS_"

ZONE1_BUS_LABEL = "InternalNode1"
ZONE1_INJECTOR_NODE_LABEL = "InternalNode2"
PDR_BUS_LABEL = "PDR Bus"

NETWORK_FREQUENCY = "NetworkFrequencyPu"

_GENERATOR_SELECTOR = "_GEN_"
_PHASE_SUFFIXES = ("_a", "_b", "_c")
_LEGACY_GENERATOR_VARIABLES = {
    "VoltageInjTerminal": "VoltageNode2",
    "ActiveCurrentInjTerminal": "ActiveCurrentNode2",
    "ReactiveCurrentInjTerminal": "ReactiveCurrentNode2",
    "ActivePowerControlledPu": "ActivePowerControlledNode",
    "ReactivePowerControlledPu": "ReactivePowerControlledNode",
}


def get_bus_label(zone: int) -> str:
    """Get the user-facing label of the connection-point bus for a zone.

    Parameters
    ----------
    zone: int
        Validation zone (1 for Zone1, 3 for Zone3, 0 otherwise)

    Returns
    -------
    str
        "InternalNode1" for Zone 1, "PDR Bus" otherwise
    """
    return ZONE1_BUS_LABEL if zone == 1 else PDR_BUS_LABEL


def to_output_name(curve_name: str, zone: int) -> str:
    """Translate an internal curve name to its user-facing name for a zone.

    Parameters
    ----------
    curve_name: str
        Internal curve name (e.g. "BusPDR_BUS_Voltage")
    zone: int
        Validation zone

    Returns
    -------
    str
        The Zone 1 output name (e.g. "InternalNode1_BUS_Voltage"), or the input
        name unchanged for other zones or non-bus curves
    """
    if zone == 1 and curve_name.startswith(INTERNAL_BUS_PREFIX):
        return ZONE1_BUS_PREFIX + curve_name[len(INTERNAL_BUS_PREFIX) :]
    return curve_name


def to_internal_name(curve_name: str) -> str:
    """Translate a user-facing Zone 1 curve name back to its internal name.

    Parameters
    ----------
    curve_name: str
        Curve name (e.g. "InternalNode1_BUS_Voltage")

    Returns
    -------
    str
        The internal name (e.g. "BusPDR_BUS_Voltage"), or the input name
        unchanged if it does not use the Zone 1 bus prefix
    """
    if curve_name.startswith(ZONE1_BUS_PREFIX):
        return INTERNAL_BUS_PREFIX + curve_name[len(ZONE1_BUS_PREFIX) :]
    return curve_name


def from_legacy_name(curve_name: str) -> str:
    """Translate a generator curve name of the previous naming to the current one.

    Parameters
    ----------
    curve_name: str
        Curve name (e.g. "Wind_Turbine_GEN_VoltageInjTerminal"), possibly one phase of a
        three-phase signal (e.g. "Wind_Turbine_GEN_VoltageInjTerminal_a")

    Returns
    -------
    str
        The current name (e.g. "Wind_Turbine_GEN_VoltageNode2"), or the input name
        unchanged if it is not a generator curve of the previous naming
    """
    head, selector, variable = curve_name.rpartition(_GENERATOR_SELECTOR)
    phase = variable[-2:] if variable[-2:] in _PHASE_SUFFIXES else ""
    current = _LEGACY_GENERATOR_VARIABLES.get(variable[: len(variable) - len(phase)])
    if not selector or current is None:
        return curve_name
    return head + selector + current + phase


def rename_columns_for_output(curves: pd.DataFrame, zone: int) -> pd.DataFrame:
    """Return a copy of curves with its columns renamed to user-facing names.

    Parameters
    ----------
    curves: DataFrame
        Curves with internal column names
    zone: int
        Validation zone

    Returns
    -------
    DataFrame
        Curves with Zone 1 bus columns renamed, or the input unchanged for
        other zones
    """
    if zone != 1:
        return curves
    return curves.rename(columns={col: to_output_name(col, zone) for col in curves.columns})


def get_network_frequency_curve(curves: dict | pd.DataFrame) -> None:
    """Name the network frequency NetworkFrequencyPu after the first frequency a unit measures,
    unless the curves already carry it under that name.

    Parameters
    ----------
    curves: dict | DataFrame
        Curves by name, which gain the NetworkFrequencyPu curve when one of them is a
        ``*_NetworkFrequencyPu``
    """
    if NETWORK_FREQUENCY in curves:
        return
    unit_frequencies = [name for name in curves.keys() if name.endswith(f"_{NETWORK_FREQUENCY}")]
    if unit_frequencies:
        curves[NETWORK_FREQUENCY] = curves[unit_frequencies[0]]
