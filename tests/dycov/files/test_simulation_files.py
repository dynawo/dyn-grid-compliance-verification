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
