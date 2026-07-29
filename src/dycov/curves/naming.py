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
``InternalNode2`` (called "Node2" in the DTR); the injector-terminal curves are
measured there.
"""
import pandas as pd

INTERNAL_BUS_PREFIX = "BusPDR_BUS_"
ZONE1_BUS_PREFIX = "InternalNode1_BUS_"

ZONE1_BUS_LABEL = "InternalNode1"
ZONE1_INJECTOR_NODE_LABEL = "InternalNode2"
PDR_BUS_LABEL = "PDR Bus"


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
