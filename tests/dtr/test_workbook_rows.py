#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The rows of the producer's workbook map to the tests each revision of the DTR runs.

A revision that changes the operating conditions of a fiche writes its own mapping of the
rows; one that has none reads the mapping of the base, and would run without a reference the
tests the base does not have.
"""

import configparser

import pytest

from dycov.configuration.cfg import config
from dycov.excel import names
from tests.dtr.conftest import PACKAGE_ROOT


def _revisions() -> list:
    parser = configparser.ConfigParser(inline_comment_prefixes=("#",))
    parser.read(PACKAGE_ROOT / "configuration" / "defaultConfig.ini")
    return [revision.strip() for revision in parser.get("DTR", "available").split(",")]


def _tests_of(pcs: str) -> set:
    return {
        f"{pcs}.{benchmark}.{condition}"
        for benchmark in config.get_list("PCS-Benchmarks", pcs)
        for condition in config.get_list("PCS-OperatingConditions", f"{pcs}.{benchmark}")
    }


@pytest.mark.parametrize("revision_name", _revisions())
@pytest.mark.parametrize("zone, pcs", [("Zone1", "PCS_RTE-I16z1"), ("Zone3", "PCS_RTE-I16z3")])
def test_the_workbook_has_a_row_for_every_test_the_revision_runs_and_no_other(
    revision, description, revision_name, zone, pcs
):
    revision(revision_name)
    description("model", "PPM", pcs)

    assert set(names.tests(zone).values()) == _tests_of(pcs)
