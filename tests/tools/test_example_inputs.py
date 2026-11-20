#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the announcement of the records of the F16 tests the examples declare
(``tools/scripts/example_inputs.py``), the first stage of the curve regeneration."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_TOOL_DIR = _REPO / "tools" / "scripts"
sys.path.insert(0, str(_TOOL_DIR))

import example_inputs  # noqa: E402

_MODEL = _REPO / "examples" / "Model" / "Wind" / "IECB2015" / "Dynawo"


def test_the_announcement_writes_the_index_of_the_records_and_no_record(tmp_path):
    reference = tmp_path / "ReferenceCurves"

    assert example_inputs.announce_delivery(reference, _MODEL, "PPM") is True

    assert [path.name for path in (reference / "Producer").iterdir()] == ["CurvesFiles.ini"]


def test_the_announcement_keeps_an_index_already_there(tmp_path):
    producer = tmp_path / "ReferenceCurves" / "Producer"
    producer.mkdir(parents=True)
    (producer / "CurvesFiles.ini").write_text("[Curves-Files]\n", encoding="utf-8")

    assert example_inputs.announce_delivery(producer.parent, _MODEL, "PPM") is False

    assert (producer / "CurvesFiles.ini").read_text(encoding="utf-8") == "[Curves-Files]\n"
