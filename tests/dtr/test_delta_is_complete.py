#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""What a delta of the DTR must hold, whichever revision writes it.

A report template states the conditions of the test it reports in its prose. A revision
that changes those conditions and keeps the shipped template gives a report that states
one value while the simulation uses another. These tests read every delta the tool ships,
so a revision that arrives answers for itself.
"""

import configparser
from pathlib import Path

import pytest

import dycov
from dycov.configuration.cfg import config

TEMPLATES = Path(dycov.__file__).resolve().parent / "templates"
REVISIONS = sorted(path for path in (TEMPLATES / "revisions").glob("*") if path.is_dir())


def _read(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(inline_comment_prefixes=("#",))
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    return parser


def _tests_of(description: Path) -> list[str]:
    """The name of every test a description writes, as <pcs>.<benchmark>.<oc>."""
    parser = _read(description)
    names = []
    for section in parser.sections():
        parts = section.split(".")
        if len(parts) >= 3 and ".".join(parts[:3]) not in names:
            names.append(".".join(parts[:3]))
    return names


def _descriptions(revision: Path) -> list[Path]:
    return sorted(revision.glob("PCS/*/*/*/PCSDescription.ini"))


@pytest.mark.parametrize("revision", REVISIONS, ids=lambda path: path.name)
def test_a_revision_the_tool_ships_a_delta_for_is_one_it_implements(revision):
    """A delta nothing can select is a delta nobody reads."""
    available = [value.strip() for value in config.get_list("DTR", "available")]

    assert revision.name in available


@pytest.mark.parametrize("revision", REVISIONS, ids=lambda path: path.name)
def test_every_test_a_delta_changes_carries_its_report_template(revision):
    """The delta of a test and the template of that test travel together."""
    missing = []
    for description in _descriptions(revision):
        pcs = description.relative_to(revision / "PCS").parent
        shipped = _read(TEMPLATES / "PCS" / pcs / "PCSDescription.ini")
        delta = _read(description)

        for test in _tests_of(description):
            report = delta.get(test, "report_name", fallback=None) or shipped.get(
                test, "report_name", fallback=None
            )
            assert report is not None, f"{test} names no report"
            if not (revision / "reports" / pcs / report).is_file():
                missing.append(f"{pcs}/{report} of {test}")

    assert not missing, (
        "the delta changes these tests and keeps the shipped template: " + ", ".join(missing)
    )


@pytest.mark.parametrize("revision", REVISIONS, ids=lambda path: path.name)
def test_a_delta_describes_a_PCS_the_tool_ships(revision):
    """A delta overlays a description; it does not invent the directory of a PCS."""
    for description in _descriptions(revision):
        pcs = description.relative_to(revision / "PCS").parent

        assert (TEMPLATES / "PCS" / pcs / "PCSDescription.ini").is_file(), (
            f"the tool ships no description for {pcs}"
        )
