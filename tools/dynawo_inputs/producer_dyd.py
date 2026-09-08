#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The DYD side: the topology DyCoV builds, and the concrete libs and terminals filled into it."""

from __future__ import annotations

import re
from pathlib import Path

import parse as P
from lxml import etree

from dycov.files.producer_dyd_file import (
    GROUP_XFMR_ID,
    MAIN_XFMR_ID,
    create_producer_dyd_file,
    fill_producer_dyd,
    write_producer_dyd,
)

# Generator block id must pass topology_checks._is_valid_generator.
GEN_ID_BY_TECH = {"PV": "PV_Array", "Wind": "Wind_Turbine", "BESS": "Bess"}

_LIB_XFMR_OLTC = "TransformerRatioTapChanger"
_LIB_XFMR_FIXED = "TransformerFixedRatio"
_LIB_LINE = "Line"
_LIB_LOAD = "LoadAlphaBeta"
_LIB_BUS = "Bus"

_SUPPORTED_TOPOLOGIES = ("S", "S+i", "S+Aux", "S+Aux+i")

# The network blocks a topology may contain, with the lib each one takes.
_NETWORK_LIBS = {
    "AuxLoad_Xfmr": _LIB_XFMR_FIXED,
    "Aux_Load": _LIB_LOAD,
    "IntNetwork_Line": _LIB_LINE,
    "Int_Bus": _LIB_BUS,
}
# The transformer each zone has of its own: the unit's step-up, and the plant's regulated one.
_ZONE_XFMR = {
    "Zone1": (GROUP_XFMR_ID, _LIB_XFMR_FIXED),
    "Zone3": (MAIN_XFMR_ID, _LIB_XFMR_OLTC),
}

_XFMR_TERMINAL2 = "transformer_terminal2"


def checked_topology(zone3: dict) -> str:
    """Read the ``Topologie`` row, as DyCoV spells it.

    DyCoV matches the topology string exactly ("S+Aux"), while the template's own legend spells
    it "S + Aux", so the spaces are dropped rather than failing on a faithful copy of the legend.

    Parameters
    ----------
    zone3: dict
        Rows of the ``Zone3`` sheet.

    Returns
    -------
    str
        The topology name, in DyCoV's spelling.
    """
    topology = re.sub(r"\s+", "", P.zone_text(zone3, "Topologie"))
    if topology not in _SUPPORTED_TOPOLOGIES:
        raise ValueError(
            f"topology {topology!r} in sheet {P.sheet_of(zone3)!r} is not generated yet; "
            f"supported: {', '.join(_SUPPORTED_TOPOLOGIES)}. The 'M' family describes several "
            f"generating units and the tool emits one, so it is refused rather than truncated."
        )
    return topology


def write_dyd(
    root: Path,
    producer_name: str,
    topology: str,
    template: str,
    resolved: dict,
    gen_id: str,
    rename: dict,
) -> None:
    """Write both zones' DYD: DyCoV's topology, with the resolved model filled in.

    Parameters
    ----------
    root: Path
        The ``Dynawo`` directory holding both zones.
    producer_name: str
        Base name of the input files.
    topology: str
        Topology name, as ``checked_topology`` returns it.
    template: str
        DyCoV input template (``model_PPM`` or ``model_BESS``).
    resolved: dict
        Libs and prefixes of both zones, as ``parse.resolve_models`` returns them.
    gen_id: str
        Id the generator block takes, by technology.
    rename: dict
        Block ids to rename first, when the template's generator id is not *gen_id*.
    """
    create_producer_dyd_file(root, topology, template)
    for zone, (xfmr_id, xfmr_lib) in _ZONE_XFMR.items():
        lib = resolved["zone1_lib"] if zone == "Zone1" else resolved["zone3_lib"]
        prefix = resolved["zone1_prefix"] if zone == "Zone1" else resolved["zone3_prefix"]
        fill_producer_dyd(
            root / zone / f"{producer_name}.dyd",
            libs={**_NETWORK_LIBS, xfmr_id: xfmr_lib, gen_id: lib},
            terminals={gen_id: f"{prefix}terminal"},
            rename=rename,
        )


def drop_group_transformer(dyd_file: Path, gen_id: str, gen_terminal: str) -> None:
    """Remove the group transformer and wire the generator to the node it fed.

    The unit's own transformer already reaches the internal node when
    ``ConverterLVControl = false``, so modelling an external one as well would put two
    transformers in series.

    Parameters
    ----------
    dyd_file: Path
        The Zone1 DYD to edit in place.
    gen_id: str
        Id of the generator block.
    gen_terminal: str
        Terminal of the generator block, prefixed by its model.
    """
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(dyd_file), parser)
    root = tree.getroot()
    ns = etree.QName(root).namespace

    downstream = None
    for connect in list(root.iterfind(f"{{{ns}}}connect")):
        id1, var1, id2, var2 = (connect.get(k) for k in ("id1", "var1", "id2", "var2"))
        if id1 == GROUP_XFMR_ID and var1 == _XFMR_TERMINAL2:
            downstream = (id2, var2)
        elif id2 == GROUP_XFMR_ID and var2 == _XFMR_TERMINAL2:
            downstream = (id1, var1)
        if GROUP_XFMR_ID in (id1, id2):
            root.remove(connect)
    for bbmodel in list(root.iterfind(f"{{{ns}}}blackBoxModel")):
        if bbmodel.get("id") == GROUP_XFMR_ID:
            root.remove(bbmodel)
    if downstream:
        etree.SubElement(
            root, f"{{{ns}}}connect",
            id1=gen_id, var1=gen_terminal, id2=downstream[0], var2=downstream[1],
        )
    write_producer_dyd(root, dyd_file)
