#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Id-agnostic structural golden: the tool's output vs the authoritative ``examples/Model/**``.

The fixture ``WECCSample_full.xlsx`` is a PV ``S+Aux`` case matching
``examples/Model/Photovoltaics/WECCCurrentSource``; values are invented, so we compare **structure
only** (``blackBoxModel`` libs + ``connect`` wiring), normalizing the generator block id (tool
``PV_Array`` vs the example's legacy ``Wind_Turbine``)."""

from __future__ import annotations

from pathlib import Path

import generate_inputs as G
import pytest
from lxml import etree

_REPO = Path(__file__).resolve().parents[2]
_FIXTURE = _REPO / "tools" / "dynawo_inputs" / "examples" / "WECCSample_full.xlsx"
_EXAMPLE = _REPO / "examples" / "Model" / "Photovoltaics" / "WECCCurrentSource" / "Dynawo"

# Generator block ids to canonicalize before comparison (tool tech-specific vs example legacy).
_GEN_IDS = {"PV_Array", "Wind_Turbine", "Bess", "Power_Park", "Storage"}


def _norm(block_id):
    return "GEN" if block_id in _GEN_IDS else block_id


def _parse(dyd_path):
    root = etree.parse(str(dyd_path)).getroot()
    return root, etree.QName(root).namespace


def _libs(dyd_path):
    """Set of ``(block id, lib)`` in a DYD, generator id normalized to ``GEN``."""
    root, ns = _parse(dyd_path)
    return frozenset(
        (_norm(b.get("id")), b.get("lib")) for b in root.iterfind(f"{{{ns}}}blackBoxModel")
    )


def _connects(dyd_path):
    """Set of ``(id1, var1, id2, var2)`` connects in a DYD, generator id normalized."""
    root, ns = _parse(dyd_path)
    return frozenset(
        (_norm(c.get("id1")), c.get("var1"), _norm(c.get("id2")), c.get("var2"))
        for c in root.iterfind(f"{{{ns}}}connect")
    )


def _diff(zone, kind, got, exp):
    return f"{zone} {kind} differ:\n  only in tool: {got - exp}\n  only in example: {exp - got}"


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp("gen")
    G.generate(_FIXTURE, out)
    return out / "Dynawo"


@pytest.mark.parametrize("zone", ["Zone1", "Zone3"])
def test_connects_match_example(generated, zone):
    # The wiring is what DyCoV actually validates, so it must match the authoritative example.
    got = _connects(generated / zone / "Producer.dyd")
    exp = _connects(_EXAMPLE / zone / "Producer.dyd")
    assert got == exp, _diff(zone, "connects", got, exp)


@pytest.mark.parametrize("zone", ["Zone1", "Zone3"])
def test_libs_match_example(generated, zone):
    # The transformers included: Zone1's group one has a fixed ratio, Zone3's main one a
    # tap changer.
    got = _libs(generated / zone / "Producer.dyd")
    exp = _libs(_EXAMPLE / zone / "Producer.dyd")
    assert got == exp, _diff(zone, "libs", got, exp)
