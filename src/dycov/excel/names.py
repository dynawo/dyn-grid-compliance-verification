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

Two files are read, as with the rest of DyCoV's configuration: the one shipped in the package and
the user's own copy under the configuration directory, which wins key by key. A template that
renames a sheet therefore needs an edited copy, not a patched release.
"""

from __future__ import annotations

import configparser
import unicodedata
from functools import lru_cache
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.logging import dycov_logging

NAMES_FILENAME = "excel_names.ini"
PACKAGE_NAMES_FILE = Path(__file__).resolve().parent / "dictionary" / NAMES_FILENAME

GENERATOR_PLACEHOLDER = "{gen}"


def normalize(text) -> str:
    """Lower-case *text* and strip its accents, the form every name is matched in."""
    if not isinstance(text, str):
        return ""
    stripped = unicodedata.normalize("NFKD", text)
    return "".join(c for c in stripped if not unicodedata.combining(c)).strip().lower()


def user_names_file() -> Path:
    """The user's own copy, which the configuration directory holds."""
    return config.get_config_dir() / NAMES_FILENAME


def _read(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None, delimiters=("=",))
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    return parser


def _report_unknown(shipped: configparser.ConfigParser, path: Path) -> None:
    """Warn about what the user's copy defines and the tool no longer reads."""
    user = _read(path)
    unknown = []
    for section in user.sections():
        if not shipped.has_section(section):
            unknown.append(section)
            continue
        unknown += [
            f"{section}.{key}"
            for key in user.options(section)
            if not shipped.has_option(section, key) and not _is_data_section(section)
        ]
    if unknown:
        dycov_logging.get_logger("Excel names").warning(
            f"{path} defines names the tool does not read: {', '.join(unknown[:8])}"
        )


def _is_data_section(section: str) -> bool:
    """Sections whose keys are the user's own data, not a fixed set of concepts."""
    return section.endswith(("-Curves", "-Tests"))


@lru_cache(maxsize=1)
def _parsed() -> configparser.ConfigParser:
    shipped = _read(PACKAGE_NAMES_FILE)
    if not shipped.sections():
        raise ValueError(f"the names file is missing: {PACKAGE_NAMES_FILE}")
    user_file = user_names_file()
    if not user_file.is_file():
        return shipped
    _report_unknown(shipped, user_file)
    parser = _read(PACKAGE_NAMES_FILE)
    parser.read(user_file, encoding="utf-8")
    return parser


def _option(section: str, key: str) -> str:
    parser = _parsed()
    if not parser.has_option(section, key):
        raise ValueError(
            f"'{key}' is not defined under [{section}] in {NAMES_FILENAME}: the generator needs "
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


def metadata_columns() -> dict:
    """``{metadata key -> normalized column header}`` of the curve-metadata block."""
    parser = _parsed()
    section = "Metadata-Columns"
    if not parser.has_section(section):
        return {}
    return {key: normalize(header) for key, header in parser.items(section) if header.strip()}


def metadata_booleans() -> tuple:
    """The metadata keys DyCoV reads as a boolean."""
    return tuple(key.strip() for key in _option("Metadata-Values", "booleans").split(","))


def metadata_true_values() -> set:
    """The cell values meaning ``True`` for a boolean metadata key, normalized."""
    return {normalize(value) for value in _option("Metadata-Values", "true").split(",")}


def test_suffixes() -> tuple:
    """The suffixes a storage plant's operating conditions carry, verbatim: they name files."""
    return tuple(value.strip() for value in _option("Storage", "test_suffixes").split(","))


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
