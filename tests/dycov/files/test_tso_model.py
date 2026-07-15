#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path
from unittest.mock import Mock, patch

from lxml import etree

from dycov.files.tso_file import (
    _add_setpoint_parameters,
    _connect_generator,
    _connect_generator_to_setpoint,
    _create_model,
    complete_setpoint,
)


def _make_root():
    ns = "http://test"
    root = etree.Element(f"{{{ns}}}root")
    return root, ns


def _make_generator():
    g = Mock()
    g.id = "gen1"
    g.lib = "lib"
    return g


# =========================
# Creation helpers
# =========================

def test_create_model():
    root, ns = _make_root()

    _create_model(root, ns, "id1", "lib", "file.par", "par_id")

    assert len(root) == 1
    el = root[0]
    assert el.get("id") == "id1"
    assert el.get("lib") == "lib"


def test_connect_generator():
    root, ns = _make_root()

    _connect_generator(root, ns, "g1", "v1", "g2", "v2")

    assert len(root) == 1
    el = root[0]
    assert el.get("id1") == "g1"


# =========================
# Setpoint helpers
# =========================

def test_connect_generator_to_setpoint():
    root, ns = _make_root()
    g = _make_generator()

    from dycov.curves.dynawo.dictionary.translator import Translator

    with patch.object(Translator, "get_dynawo_variable", return_value=(1, "var")):
        sign = _connect_generator_to_setpoint(root, ns, g, "ActivePowerSetpointPu")

    assert sign == 1
    assert len(root) == 2


def test_add_setpoint_parameters():
    root, ns = _make_root()

    g = _make_generator()

    event_params = {"start_time": 1.0}

    _add_setpoint_parameters(
        root,
        ns,
        g,
        event_params,
        pre_value=0.5,
        step_value=0.2,
    )

    assert len(root) == 1
    parset = root[0]
    assert len(parset) == 3


# =========================
# Complete setpoint
# =========================

def test_complete_setpoint_executes(tmp_path):
    dyd_content = """
    <root xmlns="http://test"></root>
    """

    par_content = """
    <root xmlns="http://test"></root>
    """

    dyd_file = tmp_path / "file.dyd"
    par_file = tmp_path / "file.par"

    dyd_file.write_text(dyd_content)
    par_file.write_text(par_content)

    g = _make_generator()
    generators = [g]

    event_params = {
        "start_time": 1.0,
        "connect_to": "ActivePowerSetpointPu",
        "pre_value": [0.5],
        "step_value": 0.2,
    }

    with patch("dycov.files.tso_file._connect_generator_to_setpoint", return_value=1):
        complete_setpoint(
            tmp_path,
            "file.dyd",
            "file.par",
            generators,
            "RefTracking_1Line_InfBus",
            event_params,
        )


def test_complete_setpoint_per_generator_step_value(tmp_path):
    """step_value may be a per-generator list (P/Q setpoint events, issue #359)."""
    dyd_file = tmp_path / "file.dyd"
    par_file = tmp_path / "file.par"
    dyd_file.write_text('<root xmlns="http://test"></root>')
    par_file.write_text('<root xmlns="http://test"></root>')

    g1 = _make_generator()
    g2 = _make_generator()
    g2.id = "gen2"

    event_params = {
        "start_time": 1.0,
        "connect_to": "ActivePowerSetpointPu",
        "pre_value": [0.5, 0.4],
        "step_value": [0.8, 0.6],
    }

    with patch("dycov.files.tso_file._connect_generator_to_setpoint", return_value=1):
        complete_setpoint(
            tmp_path,
            "file.dyd",
            "file.par",
            [g1, g2],
            "RefTracking_1Line_InfBus",
            event_params,
        )

    par_root = etree.parse(par_file).getroot()
    heights = {
        parset.get("id"): parset.xpath("./*[@name='step_Height']/@value")[0]
        for parset in par_root
    }
    assert heights == {"SetPoint_gen1": "0.8", "SetPoint_gen2": "0.6"}


def test_complete_setpoint_skip():
    complete_setpoint(
        Path("/tmp"),
        "file.dyd",
        "file.par",
        [],
        "OTHER_MODEL",
        {},
    )
