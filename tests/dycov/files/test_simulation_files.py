#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the readers and writers of the Dynawo case files of a run."""

import math

from lxml import etree

from dycov.files import simulation_files
from dycov.model.parameters import PdrParams

_NS = "http://www.rte-france.com/dynawo"


def _make_root(ns=_NS):
    return etree.Element(f"{{{ns}}}root", nsmap={None: ns})


def _write_xml(root, path):
    etree.ElementTree(root).write(
        str(path), pretty_print=True, xml_declaration=True, encoding="utf-8"
    )


def test_get_event_times_normal(tmp_path):
    root = _make_root()
    etree.SubElement(root, f"{{{_NS}}}par", name="fault_tBegin", value="1.5")
    etree.SubElement(root, f"{{{_NS}}}par", name="event_tEvent", value="2.5")
    _write_xml(root, tmp_path / "case1.par")

    t1, t2 = simulation_files.get_event_times(tmp_path, "case1", 0.5, 10.0)

    assert t1 == 1.5
    assert t2 == 2.5


def test_get_event_times_missing_values(tmp_path):
    root = _make_root()
    etree.SubElement(root, f"{{{_NS}}}par", name="step_tStep", value="{step}")
    _write_xml(root, tmp_path / "case2.par")

    t1, t2 = simulation_files.get_event_times(tmp_path, "case2", 0.5, 10.0)

    assert math.isnan(t1)
    assert math.isnan(t2)


def test_find_output_dir(tmp_path):
    root = _make_root()
    etree.SubElement(root, f"{{{_NS}}}outputs", directory="outdir")
    _write_xml(root, tmp_path / "file.jobs")

    res = simulation_files.find_output_dir(tmp_path, "file")

    assert res == "outdir"


def test_write_pdr_comment_adds_the_parameters_of_the_connection_point(tmp_path):
    _write_xml(_make_root(), tmp_path / "TSOModel.par")
    pdr = PdrParams(u=1.02, u_phase=0.1, s=1.0, p=0.8, q=0.2)

    simulation_files.write_pdr_comment(tmp_path, "TSOModel.par", pdr)

    comments = etree.parse(str(tmp_path / "TSOModel.par")).getroot().xpath("//comment()")
    assert [comment.text for comment in comments] == [
        "PDR parameters: U=1.02, UPhase=0.1, S=1.0, P=0.8, Q=0.2"
    ]


def test_write_pdr_comment_updates_the_comment_of_a_previous_run(tmp_path):
    _write_xml(_make_root(), tmp_path / "TSOModel.par")
    simulation_files.write_pdr_comment(
        tmp_path, "TSOModel.par", PdrParams(u=1.02, u_phase=0.1, s=1.0, p=0.8, q=0.2)
    )

    simulation_files.write_pdr_comment(
        tmp_path, "TSOModel.par", PdrParams(u=0.98, u_phase=0.2, s=1.0, p=0.5, q=0.1)
    )

    comments = etree.parse(str(tmp_path / "TSOModel.par")).getroot().xpath("//comment()")
    assert [comment.text for comment in comments] == [
        "PDR parameters: U=0.98, UPhase=0.2, S=1.0, P=0.5, Q=0.1"
    ]


_PAR = """<?xml version="1.0" encoding="UTF-8"?>
<parametersSet xmlns="http://www.rte-france.com/dynawo">
{sets}
</parametersSet>
"""


def _par_with(tmp_path, *sets):
    """A PAR file of a TSO model with the given sets, each an id and its parameters."""
    body = "".join(
        f'  <set id="{set_id}">'
        + "".join(f'<par type="DOUBLE" name="{n}" value="{v}"/>' for n, v in parameters.items())
        + "</set>\n"
        for set_id, parameters in sets
    )
    path = tmp_path / "TSOModel.par"
    path.write_text(_PAR.format(sets=body))
    return path


def test_the_grid_ran_with_the_impedance_of_its_line_and_of_the_fault_at_a_node(tmp_path):
    par = _par_with(
        tmp_path,
        ("InfiniteBus", {"infiniteBus_UPu": 1.0}),
        ("Line", {"line_RPu": 0.8292, "line_XPu": 8.292}),
        ("NodeFault", {"fault_RPu": 0.2539, "fault_XPu": 2.5391, "fault_tBegin": 30}),
    )

    assert simulation_files.grid_impedances(par) == {
        "line_RPu": 0.8292,
        "line_XPu": 8.292,
        "grid_lines": 1,
        "fault_RPu": 0.2539,
        "fault_XPu": 2.5391,
    }


def test_a_grid_of_several_lines_and_a_fault_along_one_of_them(tmp_path):
    lines = [(f"Line{n}", {"line_RPu": 0.0, "line_XPu": 0.4}) for n in (1, 2, 3)]
    fault = {"line_RPu": 0.0, "line_XPu": 0.4, "line_RFaultPu": 0.0, "line_XFaultPu": 0.05}
    par = _par_with(tmp_path, *lines, ("LineFault", fault))

    assert simulation_files.grid_impedances(par) == {
        "line_RPu": 0.0,
        "line_XPu": 0.4,
        "grid_lines": 4,
        "fault_RPu": 0.0,
        "fault_XPu": 0.05,
    }


def test_the_line_a_jump_of_the_short_circuit_ratio_switches_is_not_a_line_of_the_grid(tmp_path):
    par = _par_with(
        tmp_path,
        ("Line", {"line_RPu": 0.01, "line_XPu": 0.5}),
        ("SwitchedLine", {"line_RPu": 0.002, "line_XPu": 0.1}),
    )

    assert simulation_files.grid_impedances(par) == {
        "line_RPu": 0.01,
        "line_XPu": 0.5,
        "grid_lines": 1,
        "switched_line_RPu": 0.002,
        "switched_line_XPu": 0.1,
    }


def test_a_grid_without_lines_or_a_value_not_filled_in_gives_nothing(tmp_path):
    par = _par_with(tmp_path, ("Line", {"line_RPu": "{{line_RPu}}"}), ("Main_Load", {"P": 1}))

    assert simulation_files.grid_impedances(par) == {}
    assert simulation_files.grid_impedances(tmp_path / "missing.par") == {}
