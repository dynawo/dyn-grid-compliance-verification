#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the DYD side (``dycov/excel/producer_dyd.py``): topology and wiring."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from dycov.excel import producer_dyd as dyd
from dycov.excel.units import GeneratingUnit
from dycov.files.producer_dyd_file import create_producer_dyd_file

_WECC4 = Path(__file__).resolve().parents[3] / "examples" / "Model" / "Wind" / "WECC4" / "Dynawo"


def _wind_unit(variant: str, number: int) -> GeneratingUnit:
    """A unit of ``examples/Model/Wind/WECC4``, whose two units take different models."""
    return GeneratingUnit(
        zone1={},
        model={
            "zone3_lib": f"WTG{variant}WeccCurrentSource",
            "zone3_prefix": f"WTG{variant}_",
            "zone1_lib": f"WT{variant}WeccCurrentSource",
            "zone1_prefix": f"WT{variant}_",
        },
        zone1_file=f"Producer_G{number}",
        gen_id="Wind_Turbine",
        plant_id=f"Wind_Turbine{number}",
    )


def _structure(dyd_path):
    """The ``(id, lib, parFile)`` of every block and the wiring of a DYD."""
    root = etree.parse(str(dyd_path)).getroot()
    ns = etree.QName(root).namespace
    blocks = {
        (b.get("id"), b.get("lib"), b.get("parFile"))
        for b in root.iterfind(f"{{{ns}}}blackBoxModel")
    }
    connects = {
        (c.get("id1"), c.get("var1"), c.get("id2"), c.get("var2"))
        for c in root.iterfind(f"{{{ns}}}connect")
    }
    return blocks, connects


def test_checked_topology_drops_the_legend_spacing(zone3):
    zone3["Topologie"] = "S + Aux"

    assert dyd.checked_topology(zone3) == "S+Aux"


def test_checked_topology_accepts_the_multiple_unit_family(zone3):
    zone3["Topologie"] = "M + Aux"

    assert dyd.checked_topology(zone3) == "M+Aux"


def test_checked_topology_refuses_an_unknown_string(zone3):
    zone3["Topologie"] = "S+Foo"

    with pytest.raises(ValueError, match="'S[+]Foo' .* is not one DyCoV knows"):
        dyd.checked_topology(zone3)


def test_write_dyd_fills_the_resolved_libs_and_terminals(tmp_path):
    resolved = {
        "zone3_lib": "PhotovoltaicsWeccCurrentSource",
        "zone3_prefix": "photovoltaics_",
        "zone1_lib": "PhotovoltaicsWeccCurrentSourceNoPlantControl",
        "zone1_prefix": "photovoltaics_",
    }
    for zone in ("Zone1", "Zone3"):
        (tmp_path / zone).mkdir()
    unit = GeneratingUnit({}, resolved, "Producer", gen_id="PV_Array", plant_id="PV_Array")

    dyd.write_dyd(tmp_path, "Producer", "S+Aux", "model_PPM", [unit])

    zone3 = (tmp_path / "Zone3" / "Producer.dyd").read_text(encoding="utf-8")
    assert 'id="PV_Array" lib="PhotovoltaicsWeccCurrentSource"' in zone3
    assert 'lib="TransformerRatioTapChanger"' in zone3  # the main transformer regulates
    assert "photovoltaics_terminal" in zone3
    zone1 = (tmp_path / "Zone1" / "Producer.dyd").read_text(encoding="utf-8")
    assert 'id="Group_Xfmr" lib="TransformerFixedRatio"' in zone1
    assert "PPM_DYNAMIC_MODEL" not in zone1 and "MODEL_PREFIX" not in zone1


def test_write_dyd_gives_each_unit_its_own_model_as_the_wecc4_example_does(tmp_path):
    for zone in ("Zone1", "Zone3"):
        (tmp_path / zone).mkdir()
    units = [_wind_unit("4A", 1), _wind_unit("4B", 2)]

    dyd.write_dyd(tmp_path, "Producer", "M+Aux", "model_PPM", units)

    for name in ("Zone1/Producer_G1.dyd", "Zone1/Producer_G2.dyd", "Zone3/Producer.dyd"):
        assert _structure(tmp_path / name) == _structure(_WECC4 / name), name
    assert not (tmp_path / "Zone1" / "Producer.dyd").exists()


def test_drop_group_transformer_when_no_lv_control(tmp_path):
    # ConverterLVControl=False: no gen transformer -> Group_Xfmr removed, gen wired downstream.
    for zone in ("Zone1", "Zone3"):
        (tmp_path / zone).mkdir()
    create_producer_dyd_file(tmp_path, "S", "model_PPM")
    dyd_file = tmp_path / "Zone1" / "Producer.dyd"
    gen = "Wind_Turbine"  # builder's S gen id

    dyd.drop_group_transformer(dyd_file, gen, "photovoltaics_terminal")

    root = etree.parse(str(dyd_file)).getroot()
    ns = etree.QName(root).namespace
    ids = [b.get("id") for b in root.iterfind(f"{{{ns}}}blackBoxModel")]
    assert "Group_Xfmr" not in ids
    connections = [
        (c.get("id1"), c.get("var1"), c.get("id2"), c.get("var2"))
        for c in root.iterfind(f"{{{ns}}}connect")
    ]
    assert not any("Group_Xfmr" in (c[0], c[2]) for c in connections)
    # generator now connects directly to what the transformer fed (BusPDR in S)
    assert (gen, "photovoltaics_terminal", "BusPDR", "bus_terminal") in connections
