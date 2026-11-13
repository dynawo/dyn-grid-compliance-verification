#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The version of the template a workbook follows (#701): the shipped templates carry the one
this release reads, a template that changes changes it, and a workbook written on another one
is told."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from workbooks import make_workbook

from dycov.excel import generator
from dycov.excel import workbook as W

WORKBOOKS = Path(__file__).resolve().parents[3] / "workbooks"

# What each template holds, besides its version cell, for the version it carries. A template
# that changes fails here until it carries a new version in TEMPLATE_VERSIONS and in its cell.
TEMPLATE_CONTENTS = {
    ("IEC", "1.4.0"): "d420091b957600cbd820cba0825ebb7a8e3f840dc2c3e8743f88f5bc7c0b310c",
    ("WECC", "1.3.0"): "28de818a1a3fd7cb2a484765587713dfe62fd97d6b750a08763478795884a8c1",
}


def _number_or_text(value) -> str:
    """A number as its value, so that a spreadsheet that writes 1.1000000000000001 for 1.1 on
    saving leaves the content as it was."""
    try:
        return f"{float(value):.12g}"
    except (TypeError, ValueError):
        return str(value)


def _content(book: dict) -> str:
    cells = [
        (name, row_idx, col_idx, _number_or_text(value))
        for name, grid in book.items()
        for row_idx, row in enumerate(grid)
        for col_idx, value in enumerate(row)
        if value is not None
        and not (name.lower().startswith("infos") and (row_idx, col_idx) == (1, 0))
    ]
    return hashlib.sha256(json.dumps(cells, ensure_ascii=False).encode()).hexdigest()


@pytest.mark.parametrize("standard", ["IEC", "WECC"])
def test_a_template_carries_the_version_this_release_reads(standard):
    book = W.read_workbook(WORKBOOKS / f"Producer_{standard}.xlsx")

    assert W.parse_template_format(book) == (W.TEMPLATE_VERSIONS[standard], standard)


@pytest.mark.parametrize("standard", ["IEC", "WECC"])
def test_a_template_that_changes_changes_its_version(standard):
    """A changed template needs a new version, or the workbooks written on the old one pass
    unwarned: give it one in TEMPLATE_VERSIONS and in its cell, then record its content here."""
    book = W.read_workbook(WORKBOOKS / f"Producer_{standard}.xlsx")
    version = W.TEMPLATE_VERSIONS[standard]

    assert _content(book) == TEMPLATE_CONTENTS[(standard, version)]


def _information(version, standard) -> dict:
    return {"Infos générales ->": [["format_version", "standard"], [version, standard]]}


def test_the_information_sheet_gives_the_version_and_the_standard():
    assert W.parse_template_format(_information(" 0.0.1 ", "WECC")) == ("0.0.1", "WECC")
    assert W.parse_template_format(_information(None, "IEC")) == (None, "IEC")
    assert W.parse_template_format({"Général": [["Type de bloc", "Choix"]]}) == (None, None)


@pytest.mark.parametrize(
    "version, standard, warned",
    [
        (W.TEMPLATE_VERSIONS["IEC"], "IEC", None),
        ("0.0.1", "IEC", "follows the IEC template of DyCoV 0.0.1"),
        (None, "WECC", "names no version of the WECC template"),
        (W.TEMPLATE_VERSIONS["IEC"], None, "giving its standard and format_version"),
        (W.TEMPLATE_VERSIONS["IEC"], "IEEE", "names IEEE as its standard"),
        (W.TEMPLATE_VERSIONS["WECC"], "wecc", None),
    ],
)
def test_a_workbook_on_another_template_is_told(caplog, version, standard, warned):
    generator._check_template_version(Path("Producer.xlsx"), _information(version, standard))

    if warned is None:
        assert "template" not in caplog.text
    else:
        assert warned in caplog.text


@pytest.mark.parametrize("version, warned", [(W.TEMPLATE_VERSIONS["IEC"], False), ("0.0.1", True)])
def test_the_inputs_of_a_workbook_on_another_template_are_written_with_a_warning(
    tmp_path, monkeypatch, caplog, version, warned
):
    book = make_workbook()
    book.update(_information(version, "IEC"))
    monkeypatch.setattr(generator.wb, "read_workbook", lambda _path: book)

    generator.generate(Path("Producer.xlsx"), tmp_path)

    assert ("follows the IEC template of DyCoV 0.0.1" in caplog.text) is warned
    assert (tmp_path / "Dynawo" / "Zone3" / "Producer.par").is_file()
