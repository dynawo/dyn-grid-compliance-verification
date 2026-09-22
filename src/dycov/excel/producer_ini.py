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

# u_nom_at_PDR is the nominal voltage of the node the zone connects at: Un1 for Zone1, whose node
# is internal to the plant and free of the DTR's level list (dycov#477), and Un_PDR for Zone3, the
# actual connection point.
_LIMITS = {
    "p_max_injection_at_PDR": "p_max_injection",
    "u_nom_at_PDR": "u_nom",
    "q_max_at_PDR": "q_max",
    "q_min_at_PDR": "q_min",
}
# Storage declares the consumption limit in both zones, and DyCoV rejects an INI without it. Each
# zone takes its own row: the Zone1a one is per unit, the Zone3 one is the whole plant.
_CONSUMPTION_KEY = "p_max_consumption_at_PDR"


def write_ini(
    root: Path,
    producer_name: str,
    topology: str,
    generators: list[dict],
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
    generators: list[dict]
        Information needed to build the topology for each generating unit.
    zone3: dict
        Rows of the ``Zone3`` sheet.
    include_consumption: bool
        True for storage models, the only ones that declare a consumption limit.
    """
    z3_value = P.values("Zone3", zone3)

    sharing = {}
    for gen in generators:
        gen_id = gen["gen_id"]
        z1_value = P.values("Zone1", gen["zone1_data"])
        sharing[gen_id] = (z1_value("p_sharing"), z1_value("q_sharing"))

    z1_base_value = P.values("Zone1", generators[0]["zone1_data"])

    values = {
        "Zone1": {key: z1_base_value(row) for key, row in _LIMITS.items()},
        "Zone3": {key: z3_value(row) for key, row in _LIMITS.items()},
    }

    if include_consumption:
        values["Zone1"][_CONSUMPTION_KEY] = z1_base_value("p_max_consumption")
        values["Zone3"][_CONSUMPTION_KEY] = z3_value("p_max_consumption")

    for zone, zone_topology, number in (("Zone1", "S", 1), ("Zone3", topology, 3)):
        write_producer_ini_file(
            root / zone,
            f"{producer_name}.ini",
            zone_topology,
            values[zone],
            gen_sharing=sharing,
            include_consumption=include_consumption,
            zone=number,
        )
