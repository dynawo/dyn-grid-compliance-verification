#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The INI side: the connection-point limits each zone declares to DyCoV."""

from __future__ import annotations

from pathlib import Path

from dycov.excel import parse as P
from dycov.files.producer_ini_file import write_producer_ini_file

# u_nom is the nominal voltage of the node the zone connects at: Un1 for Zone1, whose node
# is internal to the plant and free of the DTR's level list (dycov#477), and Un_PDR for Zone3, the
# actual connection point.
_LIMITS = ("p_max_injection", "u_nom", "q_max", "q_min")
# Storage declares the consumption limit in both zones, and DyCoV rejects an INI without it. Each
# zone takes its own row: the Zone1<x> one is per unit, the Zone3 one is the whole plant.
_CONSUMPTION_KEY = "p_max_consumption"
# The minimum powers are the starting points of the on-site tests of the DTR Fiche F16, which only
# Zone3 runs, and a plant may leave them empty.
_ZONE3_MINIMUMS = ("p_min_injection",)
_ZONE3_CONSUMPTION_MINIMUMS = ("p_min_consumption",)
# A unit is alone in its Zone1 test, so it takes the whole of the power there; the P_share and
# Q_share rows say how the plant spreads its own among the units, which is Zone3's business.
_WHOLE_SHARE = "1.0"


def write_ini(
    root: Path,
    producer_name: str,
    topology: str,
    units: list,
    zone3: dict,
    include_consumption: bool,
) -> None:
    """Write both zones' INI: limits, nominal voltage, topology and the per-unit power sharing.

    Parameters
    ----------
    root: Path
        The ``Dynawo`` directory holding both zones.
    producer_name: str
        Base name of the input files.
    topology: str
        Topology of the plant; Zone1 is always a single unit connected to its internal node.
    units: list
        The ``units.GeneratingUnit`` of the plant, each with an INI of its own in Zone1.
    zone3: dict
        Rows of the ``Zone3`` sheet.
    include_consumption: bool
        True for storage models, the only ones that declare a consumption limit.
    """
    for unit in units:
        write_producer_ini_file(
            root / "Zone1",
            f"{unit.zone1_file}.ini",
            "S",
            _limits("Zone1", unit.zone1, include_consumption),
            gen_sharing={unit.gen_id: (_WHOLE_SHARE, _WHOLE_SHARE)},
            include_consumption=include_consumption,
            zone=1,
        )

    values = _limits("Zone3", zone3, include_consumption)
    minimums = _ZONE3_MINIMUMS + (_ZONE3_CONSUMPTION_MINIMUMS if include_consumption else ())
    for name in minimums:
        value = P.optional_value("Zone3", zone3, name)
        if value is not None:
            values[name] = value
    sharing = {}
    for unit in units:
        z1_value = P.values("Zone1", unit.zone1)
        sharing[unit.plant_id] = (z1_value("p_sharing"), z1_value("q_sharing"))
    write_producer_ini_file(
        root / "Zone3",
        f"{producer_name}.ini",
        topology,
        values,
        gen_sharing=sharing,
        include_consumption=include_consumption,
        zone=3,
    )


def _limits(zone_key: str, zone: dict, include_consumption: bool) -> dict:
    """The connection-point limits and nominal voltage a zone sheet declares."""
    value = P.values(zone_key, zone)
    limits = {name: value(name) for name in _LIMITS}
    if include_consumption:
        limits[_CONSUMPTION_KEY] = value("p_max_consumption")
    return limits
