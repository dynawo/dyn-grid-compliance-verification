#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The IEC examples spell out the current limits of their turbines, in their workbooks and in the
PAR files those give, with the values their models take by default."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from functools import lru_cache
from pathlib import Path

import pytest
from tests.dycov.utils import _resolve_dynawo_sh

from dycov.excel import workbook as W

EXAMPLES = Path(__file__).resolve().parents[3] / "examples"
CURRENT_TABLES = {"TableIpMaxUwt": 7, "TableIqMaxUwt": 8}
_DYNAWO_NS = "{http://www.rte-france.com/dynawo}"


def _iec_workbooks() -> list[Path]:
    return sorted(
        book
        for book in EXAMPLES.glob("**/Excel/Producer.xlsx")
        if b'name="Limiteurs"' in zipfile.ZipFile(book).read("xl/workbook.xml")
    )


def _producer_pars(book: Path) -> list[Path]:
    dynawo = book.parent.parent / "Dynawo"
    return sorted(dynawo.glob("Zone*/Producer.par")) or [dynawo / "Producer.par"]


def _current_points(par: Path) -> dict[str, tuple[str, float]]:
    """The points of the current tables the PAR gives, by parameter name, with the library of
    the model its set is for."""
    libs = {
        model.get("parId"): model.get("lib")
        for model in ET.parse(par.with_suffix(".dyd")).getroot().iter()
        if model.get("parId") and model.get("lib")
    }
    return {
        par_element.get("name"): (libs[par_set.get("id")], float(par_element.get("value")))
        for par_set in ET.parse(par).getroot()
        for par_element in par_set
        if re.fullmatch(r"\w+_(TableIpMaxUwt|TableIqMaxUwt)\d\d", par_element.get("name") or "")
    }


@pytest.mark.parametrize(
    "book", _iec_workbooks(), ids=lambda book: str(book.parent.parent.relative_to(EXAMPLES))
)
def test_an_iec_example_gives_every_point_of_the_current_tables(book):
    grid = W.read_workbook(book)["Limiteurs"]
    tables = {table.name: table for table in W._find_tables(grid, W._find_header_row(grid))}

    for name, size in CURRENT_TABLES.items():
        assert len(tables[name].points) == size
        assert all(x and y for x, y in tables[name].points), name
    for par in _producer_pars(book):
        names = {re.sub(r"^\w+?_", "", name) for name in _current_points(par)}
        assert names == {
            f"{table}{index}{axis}"
            for table, size in CURRENT_TABLES.items()
            for index in range(1, size + 1)
            for axis in (1, 2)
        }, par


@pytest.fixture(scope="module")
def descriptors() -> Path:
    dynawo_sh = _resolve_dynawo_sh()
    if dynawo_sh is None or not (dynawo_sh.parent / "ddb").is_dir():
        pytest.skip("No Dynawo installation: set DYNAWOPATH or put dynawo.sh on the PATH")
    return dynawo_sh.parent / "ddb"


@lru_cache
def _defaults(descriptor: Path) -> dict[str, str]:
    return {
        element.get("name"): element.get("defaultValue")
        for element in ET.parse(descriptor).getroot().iter(f"{_DYNAWO_NS}parameter")
    }


@pytest.mark.parametrize(
    "book", _iec_workbooks(), ids=lambda book: str(book.parent.parent.relative_to(EXAMPLES))
)
def test_the_current_tables_of_an_iec_example_are_the_defaults_of_its_model(book, descriptors):
    for par in _producer_pars(book):
        for name, (lib, value) in _current_points(par).items():
            default = float(_defaults(descriptors / f"{lib}.desc.xml")[name])
            assert value == pytest.approx(default), (par, name)
