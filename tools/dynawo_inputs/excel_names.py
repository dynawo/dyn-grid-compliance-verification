#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

"""The names the generator looks for in the workbook, read from ``excel_names.ini``.

Sheets, rows, header anchors and markers all live in that file, so a renamed sheet or row is a
change there and not in the code. Curve names and test ids come from the same place: the workbook
carries the values, this file carries what each row of it means.
"""

from __future__ import annotations

import configparser
import unicodedata
from functools import lru_cache
from pathlib import Path

NAMES_FILE = Path(__file__).resolve().parent / "excel_names.ini"

GENERATOR_PLACEHOLDER = "{gen}"


def normalize(text) -> str:
    """Lower-case *text* and strip its accents, the form every name is matched in."""
    if not isinstance(text, str):
        return ""
    stripped = unicodedata.normalize("NFKD", text)
    return "".join(c for c in stripped if not unicodedata.combining(c)).strip().lower()


@lru_cache(maxsize=1)
def _parsed() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None, delimiters=("=",))
    parser.optionxform = str
    read = parser.read(NAMES_FILE, encoding="utf-8")
    if not read:
        raise ValueError(f"the names file is missing: {NAMES_FILE}")
    return parser


def _option(section: str, key: str) -> str:
    parser = _parsed()
    if not parser.has_option(section, key):
        raise ValueError(
            f"'{key}' is not defined under [{section}] in {NAMES_FILE.name}: the generator needs "
            f"it to find its way around the workbook."
        )
    return " ".join(parser.get(section, key).split())


def sheet(key: str) -> str:
    """The sheet name for a tool concept (``zone1``, ``model_map``, ``signals_zone3``…)."""
    return _option("Sheets", key)


def anchor(key: str) -> str:
    """The header text a table is located by, normalized, first alternative of the list."""
    return anchors(key)[0]


def anchors(key: str) -> tuple:
    """Every spelling accepted for a header, normalized, in the order the file lists them."""
    return tuple(normalize(value) for value in _option("Anchors", key).split(","))


def marker(key: str) -> str:
    """A single-valued marker (``not_applicable``, ``converter_voltage``)."""
    return _option("Markers", key)


def markers(key: str) -> set:
    """A comma-separated marker list (``no_block``), normalized, with the empty value included."""
    return {normalize(value) for value in _option("Markers", key).split(",")} | {""}


def row(zone: str, key: str) -> str:
    """The row name of a tool concept in a zone sheet, e.g. ``row("Zone3", "main_impedance")``."""
    return _option(f"{zone}-Rows", key)


def curves(zone: str, generator_id: str) -> dict:
    """``{normalized row label -> curve name}`` of a signal sheet, for this generator block."""
    parser = _parsed()
    section = f"{zone}-Curves"
    if not parser.has_section(section):
        return {}
    mapped = {}
    for label, curve in parser.items(section):
        name = " ".join(curve.split())
        if name:
            mapped[normalize(label)] = name.replace(GENERATOR_PLACEHOLDER, generator_id)
    return mapped


def tests(zone: str) -> dict:
    """``{normalized test key -> PCS.Benchmark.OperatingCondition}`` of a signal sheet.

    The key is the DTR case number in Zone 1, and the DTR sheet plus its position among the rows
    of that same sheet in Zone 3 (``I2/1``, ``I2/2``…).
    """
    parser = _parsed()
    section = f"{zone}-Tests"
    if not parser.has_section(section):
        return {}
    return {
        normalize(key): " ".join(test.split())
        for key, test in parser.items(section)
        if test.strip()
    }
