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

from lxml import etree

from dycov.excel import parse as P
from dycov.files.producer_dyd_file import (
    BESS_ID,
    GROUP_XFMR_ID,
    MAIN_XFMR_ID,
    PPM_ID,
    create_producer_dyd_file,
    fill_producer_dyd,
    unit_ids,
    write_producer_dyd,
)

# Generator block id must pass topology_checks._is_valid_generator.
GEN_ID_BY_TECH = {"PV": "PV_Array", "Wind": "Wind_Turbine", "BESS": "Bess"}

_LIB_XFMR_OLTC = "TransformerRatioTapChanger"
_LIB_XFMR_FIXED = "TransformerFixedRatio"
_LIB_LINE = "Line"
_LIB_LOAD = "LoadAlphaBeta"
_LIB_BUS = "Bus"

_SUPPORTED_TOPOLOGIES = ("S", "S+i", "S+Aux", "S+Aux+i", "M", "M+i", "M+Aux", "M+Aux+i")

# The network blocks a topology may contain, with the lib each one takes.
_NETWORK_LIBS = {
    "AuxLoad_Xfmr": _LIB_XFMR_FIXED,
    "Aux_Load": _LIB_LOAD,
    "IntNetwork_Line": _LIB_LINE,
    "Int_Bus": _LIB_BUS,
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
    topology = re.sub(r"\s+", "", P.texts("Zone3", zone3)("topology"))
    if topology not in _SUPPORTED_TOPOLOGIES:
        raise ValueError(
            f"topology {topology!r} in sheet {P.sheet_of(zone3)!r} is not one DyCoV knows; "
            f"supported: {', '.join(_SUPPORTED_TOPOLOGIES)}."
        )
    return topology


def write_dyd(
    root: Path,
    producer_name: str,
    topology: str,
    template: str,
    units: list,
) -> None:
    """Write both zones' DYD: DyCoV's topology, with the resolved model of each unit filled in.

    Each unit has a Zone1 DYD of its own, with its step-up transformer, and a block in the Zone3
    one, behind the plant's regulated transformer.

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
    units: list
        The ``units.GeneratingUnit`` of the plant.
    """
    create_producer_dyd_file(root, topology, template, n_generators=len(units))
    template_id = BESS_ID if template == "model_BESS" else PPM_ID
    for unit in units:
        fill_producer_dyd(
            root / "Zone1" / f"{unit.zone1_file}.dyd",
            libs={
                **_NETWORK_LIBS,
                GROUP_XFMR_ID: _LIB_XFMR_FIXED,
                unit.gen_id: unit.model["zone1_lib"],
            },
            terminals={unit.gen_id: f"{unit.model['zone1_prefix']}terminal"},
            rename={template_id: unit.gen_id},
        )
    fill_producer_dyd(
        root / "Zone3" / f"{producer_name}.dyd",
        libs={
            **_NETWORK_LIBS,
            MAIN_XFMR_ID: _LIB_XFMR_OLTC,
            **{unit.plant_id: unit.model["zone3_lib"] for unit in units},
        },
        terminals={unit.plant_id: f"{unit.model['zone3_prefix']}terminal" for unit in units},
        rename=dict(zip(unit_ids(template_id, len(units)), (unit.plant_id for unit in units))),
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
            root,
            f"{{{ns}}}connect",
            id1=gen_id,
            var1=gen_terminal,
            id2=downstream[0],
            var2=downstream[1],
        )
    write_producer_dyd(root, dyd_file)
