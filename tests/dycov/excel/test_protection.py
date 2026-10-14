#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the ride-through capability curves the protection reads from a table file."""

from __future__ import annotations

import pytest
from workbooks import make_workbook

from dycov.excel import protection

PARAMS = [
    {"name": "lhvrt_TabletUoverUfilt", "type": "STRING", "value": "hvrt"},
    {"name": "lhvrt_TabletUunderUfilt", "type": "STRING", "value": "lvrt"},
]


def test_read_curves_takes_the_points_in_sheet_order():
    curves = protection.read_curves(make_workbook())

    assert curves["undervoltage_curve"] == [(0.0, 0.25), (0.5, 1.0)]
    assert curves["overvoltage_curve"] == [(0.0, 1000000.0), (1.5, 0.5)]


def test_write_table_file_names_its_tables_as_the_parameters_do(tmp_path):
    written = protection.write_table_file(make_workbook(), PARAMS, tmp_path)

    assert written == "LHVRT.txt"
    assert (tmp_path / "LHVRT.txt").read_text() == (
        "#1\n"
        "double lvrt(2,2)\n"
        "  0        0.25\n"
        "  0.5      1\n"
        "\n"
        "double hvrt(2,2)\n"
        "  0        1e+06\n"
        "  1.5      0.5\n"
    )


def test_write_table_file_without_curves_writes_nothing(tmp_path):
    book = make_workbook()
    del book["Protection de tension"]

    assert protection.write_table_file(book, PARAMS, tmp_path) is None
    assert list(tmp_path.iterdir()) == []


def test_write_table_file_refuses_a_curve_whose_table_is_not_named(tmp_path):
    unnamed = [p for p in PARAMS if not p["name"].endswith("TabletUoverUfilt")]

    with pytest.raises(ValueError, match="no 'TabletUoverUfilt' parameter"):
        protection.write_table_file(make_workbook(), unnamed, tmp_path)


def test_written_parameters_carry_the_file_and_the_flag_that_reads_it():
    assert protection.written_parameters(make_workbook()) == [
        {"name": "lhvrt_TablesFile", "type": "STRING", "value": "LHVRT.txt", "comments": []},
        {"name": "lhvrt_TablesOnFile", "type": "BOOL", "value": "true", "comments": []},
    ]


def test_written_parameters_are_empty_without_curves():
    book = make_workbook()
    del book["Protection de tension"]

    assert protection.written_parameters(book) == []
