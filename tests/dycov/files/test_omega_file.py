#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the omega DYD/PAR completion helpers."""

import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from lxml import etree

import dycov
from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.files.omega_file import (
    _add_generator_weight,
    _connect_generator,
    _connect_generator_by_lib,
    _connect_generator_to_dynmodelomegaref,
    _connect_generator_to_infinitebus,
    _connect_generator_to_ramp,
    _connect_generator_to_setpoint,
    complete_omega,
)

_EVENT = {"start_time": 25.0, "duration_time": 0.5, "step_value": -0.02}


def _make_root():
    ns = "http://test"
    root = etree.Element(f"{{{ns}}}root")
    return root, ns


def _make_generator():
    g = Mock()
    g.id = "gen1"
    g.lib = "lib"
    return g


# ---------------------------------------------------------------------------
# Connect helpers
# ---------------------------------------------------------------------------


def test_connect_generator():
    root, ns = _make_root()

    _connect_generator(root, ns, "g1", "v1", "g2", "v2")

    assert len(root) == 1
    el = root[0]
    assert el.get("id1") == "g1"
    assert el.get("var2") == "v2"


def test_connect_generator_to_infinitebus():
    root, ns = _make_root()
    g = _make_generator()

    with patch.object(type(dynawo_translator), "get_dynawo_variable", return_value=(None, "var")):
        _connect_generator_to_infinitebus(root, ns, g)

    assert len(root) == 1


def test_connect_generator_to_setpoint():
    root, ns = _make_root()
    g = _make_generator()

    with patch.object(type(dynawo_translator), "get_dynawo_variable", return_value=(None, "var")):
        _connect_generator_to_setpoint(root, ns, g)

    assert len(root) == 1


def test_connect_generator_to_ramp():
    root, ns = _make_root()
    g = _make_generator()

    with patch.object(type(dynawo_translator), "get_dynawo_variable", return_value=(None, "var")):
        _connect_generator_to_ramp(root, ns, g, grp=0)

    assert len(root) == 1


def test_a_model_without_frequency_reference_is_connected_to_no_omega_model():
    root, ns = _make_root()
    g = _make_generator()
    g.lib = "GridFormingEpri"

    _connect_generator_to_infinitebus(root, ns, g)
    _connect_generator_to_ramp(root, ns, g, grp=0)
    _connect_generator_to_setpoint(root, ns, g)

    assert len(root) == 0


def test_connect_generator_to_dynmodelomegaref(monkeypatch):
    root, ns = _make_root()
    g = _make_generator()
    variables = {
        "RotorSpeedPu": "v1",
        "NetworkFrequencyReference": "v2",
        "Running": "v3",
    }
    monkeypatch.setattr(
        type(dynawo_translator),
        "get_dynawo_variable",
        lambda _self, _lib, name: (None, variables[name]),
    )

    _connect_generator_to_dynmodelomegaref(root, ns, g, grp=1)

    assert [(el.get("var1"), el.get("var2")) for el in root] == [
        ("v1", "omega_grp_1_"),
        ("v2", "omegaRef_grp_1_"),
        ("v3", "running_grp_1_"),
    ]


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def test_connect_generator_by_lib_none():
    root, ns = _make_root()
    g = _make_generator()

    with patch("dycov.files.omega_file._connect_generator_to_infinitebus") as f:
        _connect_generator_by_lib(root, ns, None, g, 0)

    f.assert_called_once()


def test_connect_generator_by_lib_dynmodel():
    root, ns = _make_root()
    g = _make_generator()

    with patch("dycov.files.omega_file._connect_generator_to_dynmodelomegaref") as f:
        _connect_generator_by_lib(root, ns, "DYNModelOmegaRef", g, 1)

    f.assert_called_once()


def test_connect_generator_by_lib_setpoint():
    root, ns = _make_root()
    g = _make_generator()

    with patch("dycov.files.omega_file._connect_generator_to_setpoint") as f:
        _connect_generator_by_lib(root, ns, "SetPoint", g, 1)

    f.assert_called_once()


def test_connect_generator_by_lib_ramp():
    root, ns = _make_root()
    g = _make_generator()

    with patch("dycov.files.omega_file._connect_generator_to_ramp") as f:
        _connect_generator_by_lib(root, ns, "Ramp", g, 1)

    f.assert_called_once()


# ---------------------------------------------------------------------------
# Weight
# ---------------------------------------------------------------------------


def test_add_generator_weight_none():
    root, ns = _make_root()

    res = _add_generator_weight(root, ns, None)

    assert res is None
    assert len(root) == 0


def test_add_generator_weight_valid():
    root, ns = _make_root()

    res = _add_generator_weight(root, ns, 2)

    assert res == 3
    assert len(root) == 1


# ---------------------------------------------------------------------------
# Complete omega
# ---------------------------------------------------------------------------


def test_complete_omega_executes(tmp_path):
    dyd_content = """
    <root xmlns="http://test">
        <blackBoxModel id="OmegaRef" lib="SetPoint" parId="p1"/>
    </root>
    """

    par_content = """
    <root xmlns="http://test">
        <set id="p1">
            <par name="nbGen" value="2"/>
        </set>
    </root>
    """

    dyd_file = tmp_path / "file.dyd"
    par_file = tmp_path / "file.par"

    dyd_file.write_text(dyd_content)
    par_file.write_text(par_content)

    generators = [_make_generator()]

    with patch("dycov.files.omega_file._connect_generator_by_lib") as f:
        complete_omega(tmp_path, "file.dyd", "file.par", generators, _EVENT)

    f.assert_called()


def _omega_template(tmp_path, model: str) -> dict:
    """The parameters an Omega model of the package is given for the event of the test."""
    template = Path(dycov.__file__).parent / "model_lib" / "Omega" / model
    for name in ("Omega.dyd", "Omega.par"):
        shutil.copy(template / name, tmp_path / name)

    complete_omega(tmp_path, "Omega.dyd", "Omega.par", [], _EVENT)

    par = etree.parse(str(tmp_path / "Omega.par"))
    return {node.get("name"): node.get("value") for node in par.iter("{*}par")}


def test_the_ramp_of_the_grid_frequency_is_the_event_of_the_test(tmp_path):
    """#816: the ramp starts, lasts and rises as the PCS description of the test declares, not
    as values written in the template."""
    parameters = _omega_template(tmp_path, "Ramp")

    assert float(parameters["ramp_startTime"]) == 25.0
    assert float(parameters["ramp_duration"]) == 0.5
    assert float(parameters["ramp_height"]) == -0.02
    assert float(parameters["ramp_offset"]) == 1.0


def test_an_omega_model_that_applies_no_event_keeps_its_parameters(tmp_path):
    assert _omega_template(tmp_path, "SetPoint") == {"setPoint_Value0": "1"}
