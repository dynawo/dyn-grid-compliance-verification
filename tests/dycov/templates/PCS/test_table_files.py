#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Every table a shipped PCS hands to Dynawo declares the rows it holds: Dynawo aborts when a
header announces more rows than follow it."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import dycov

_TEMPLATES = Path(dycov.__file__).resolve().parent / "templates" / "PCS"
_TABLE_FILES = sorted(_TEMPLATES.rglob("Table*.txt"))
_HEADER = re.compile(r"^\s*double\s+(\w+)\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*$")


def _table_id(path: Path) -> str:
    return path.relative_to(_TEMPLATES).as_posix()


def _blocks(text: str) -> list[tuple[str, int, int, list[list[str]]]]:
    blocks = []
    for line in text.splitlines():
        header = _HEADER.match(line)
        if header:
            name, rows, columns = header.groups()
            blocks.append((name, int(rows), int(columns), []))
        elif blocks and line.strip() and not line.lstrip().startswith("#"):
            blocks[-1][3].append(line.split())
    return blocks


@pytest.mark.parametrize("table_file", _TABLE_FILES, ids=_table_id)
def test_every_table_declares_the_rows_and_columns_it_holds(table_file: Path):
    blocks = _blocks(table_file.read_text(encoding="utf-8"))

    table = _table_id(table_file)
    assert blocks, f"{table} declares no table"
    for name, rows, columns, data in blocks:
        assert len(data) == rows, f"{table}: {name} declares {rows} rows, holds {len(data)}"
        widths = {len(row) for row in data}
        assert widths == {columns}, f"{table}: {name} declares {columns} columns, holds {widths}"
