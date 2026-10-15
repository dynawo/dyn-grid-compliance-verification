#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Bring a producer's INI files to the magnitude names DyCoV reads."""

from __future__ import annotations

import re
from pathlib import Path

from dycov.files.producer_ini_file import MAGNITUDE_KEYS, RETIRED_SUFFIX

_RETIRED_KEY = re.compile(
    rf"^\s*(#\s*)?(?P<key>\w+){RETIRED_SUFFIX}\s*[=:]",
    re.IGNORECASE,
)


def _rename_keys(text: str) -> tuple[str, list[str]]:
    """Rename the retired keys of an INI, returning the new text and the keys renamed."""
    lines = text.splitlines(keepends=True)
    renamed = []
    for index, line in enumerate(lines):
        match = _RETIRED_KEY.match(line)
        if match is None or match.group("key").lower() not in MAGNITUDE_KEYS:
            continue
        cut = match.end("key")
        lines[index] = line[:cut] + line[cut + len(RETIRED_SUFFIX) :]
        renamed.append(match.group("key") + RETIRED_SUFFIX)
    return "".join(lines), renamed


def _ini_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(path.rglob("*.[iI][nN][iI]"))


def migrate(path: Path, dry_run: bool = False) -> dict[Path, list[str]]:
    """Rename the retired magnitude keys of every INI file under a path.

    Only the key of a declaration is rewritten, a commented-out one included; values, comments
    and layout are left as they are, so a file DyCoV already reads comes back untouched.

    Parameters
    ----------
    path: Path
        The producer's input directory, searched recursively, or a single INI file.
    dry_run: bool
        Report what would be renamed without writing anything.

    Returns
    -------
    dict[Path, list[str]]
        The retired keys found in each file that carries them, in the order they appear.
    """
    renamed = {}
    for ini_file in _ini_files(path):
        text, keys = _rename_keys(ini_file.read_text())
        if not keys:
            continue
        if not dry_run:
            ini_file.write_text(text)
        renamed[ini_file] = keys
    return renamed
