#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the DYD side (``tools/dynawo_inputs/producer_dyd.py``): topology and wiring."""

from __future__ import annotations

import producer_dyd as dyd
import pytest
from lxml import etree

from dycov.files.producer_dyd_file import PPM_ID, create_producer_dyd_file


def test_checked_topology_drops_the_legend_spacing(zone3):
    zone3["Topologie"] = "S + Aux"

    assert dyd.checked_topology(zone3) == "S+Aux"


def test_checked_topology_refuses_the_multiple_unit_family(zone3):
    zone3["Topologie"] = "M+Aux"

    with pytest.raises(ValueError, match="topology 'M[+]Aux' .* is not generated yet"):
        dyd.checked_topology(zone3)


def test_checked_topology_refuses_an_unknown_string(zone3):
    zone3["Topologie"] = "S+Foo"

    with pytest.raises(ValueError, match="supported: S, S[+]i, S[+]Aux, S[+]Aux[+]i"):
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

    dyd.write_dyd(
        tmp_path,
        "Producer",
        "S+Aux",
        "model_PPM",
        resolved,
        "PV_Array",
        rename={PPM_ID: "PV_Array"},
    )

    zone3 = (tmp_path / "Zone3" / "Producer.dyd").read_text(encoding="utf-8")
    assert 'id="PV_Array" lib="PhotovoltaicsWeccCurrentSource"' in zone3
    assert 'lib="TransformerRatioTapChanger"' in zone3  # the main transformer regulates
    assert "photovoltaics_terminal" in zone3
    zone1 = (tmp_path / "Zone1" / "Producer.dyd").read_text(encoding="utf-8")
    assert 'id="Group_Xfmr" lib="TransformerFixedRatio"' in zone1
    assert "PPM_DYNAMIC_MODEL" not in zone1 and "MODEL_PREFIX" not in zone1


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
