#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The tables the IEC template lays out, read as the points of their blocks and checked against
the models of the Dynawo the tool runs, when there is one."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from tests.dycov.utils import _resolve_dynawo_sh

from dycov.excel import parse as P
from dycov.excel import workbook as W

TEMPLATE = Path(__file__).resolve().parents[3] / "workbooks" / "Producer_IEC.xlsx"
_DYNAWO_NS = "{http://www.rte-france.com/dynawo}"

TABLES_OF_THE_TEMPLATE = {
    "Contrôle de parc": {
        "TablePwpBiasfwpFiltCom": 7,
        "TableQwpMaxPwpFiltCom": 3,
        "TableQwpMinPwpFiltCom": 3,
        "TableQwpUErr": 3,
    },
    "Limiteurs": {
        "TableIqMaxUwt": 8,
        "TableIpMaxUwt": 7,
        "TableQMaxUwtcFilt": 6,
        "TableQMaxPwtcFilt": 4,
        "TableQMinUwtcFilt": 4,
        "TableQMinPwtcFilt": 4,
    },
    "Mesures et protections": {
        "TabletUunderUwtfilt": 7,
        "TabletUoverUwtfilt": 8,
        "Tabletfunderfwtfilt": 6,
        "Tabletfoverfwtfilt": 4,
    },
}


@pytest.fixture(scope="module")
def template():
    return W.read_workbook(TEMPLATE)


def _tables(template, sheet):
    grid = template[sheet]
    return W._find_tables(grid, W._find_header_row(grid))


@pytest.mark.parametrize("sheet", TABLES_OF_THE_TEMPLATE)
def test_the_template_lays_out_the_tables_of_the_models(template, sheet):
    tables = {table.name: len(table.points) for table in _tables(template, sheet)}

    assert tables == TABLES_OF_THE_TEMPLATE[sheet]


def test_the_points_of_the_protection_tables_are_not_parameters_of_their_own(template):
    variants = W.parse_variants(template)

    assert [p.name for p in variants["GridProtection"].parameters] == [
        "UOverPu",
        "UUnderPu",
        "fOverPu",
        "fUnderPu",
    ]


@pytest.fixture(scope="module")
def descriptors() -> Path:
    dynawo_sh = _resolve_dynawo_sh()
    if dynawo_sh is None or not (dynawo_sh.parent / "ddb").is_dir():
        pytest.skip("No Dynawo installation: set DYNAWOPATH or put dynawo.sh on the PATH")
    return dynawo_sh.parent / "ddb"


def _settable_parameters(descriptor: Path) -> set[str]:
    return {
        element.get("name")
        for element in ET.parse(descriptor).getroot().iter(f"{_DYNAWO_NS}parameter")
        if element.get("readOnly") != "true"
    }


def test_every_point_of_a_table_is_a_parameter_of_a_model_of_the_template(template, descriptors):
    models = [
        (row[f"{zone}_lib"], row[f"{zone}_prefix"])
        for row in P._read_model_map(template).values()
        for zone in ("zone1", "zone3")
    ]
    settable = set().union(
        *(
            {
                name.removeprefix(prefix)
                for name in _settable_parameters(descriptors / f"{lib}.desc.xml")
            }
            for lib, prefix in models
        )
    )

    points = {
        f"{table.name}{index}{axis}"
        for sheet in TABLES_OF_THE_TEMPLATE
        for table in _tables(template, sheet)
        for index in range(1, len(table.points) + 1)
        for axis in (1, 2)
    }

    assert points - settable == set()
