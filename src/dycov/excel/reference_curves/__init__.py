#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Reference-curve inputs, written into ``<outdir>/ReferenceCurves/<producer>/``.

That is the layout DyCoV reads: ``CurvesFiles.ini`` names the ``.csv`` of every test and holds the
per-zone curve dictionaries, each test's ``.dict`` repeats its own dictionary next to the metadata
that says how to read that file, and the ``.csv`` themselves sit alongside.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from . import curves_files, dicts


def _curves_folder(signals, base: Path) -> Path | None:
    """Where the user's ``.csv`` files are.

    A relative path in the sheet is relative to the workbook, not to the directory the command
    happens to run from, so a workbook that travels with its curves keeps working anywhere.
    """
    if not signals.folder:
        return None
    folder = Path(signals.folder)
    return folder if folder.is_absolute() or base is None else base / folder


def _copy_curves(signals, target: Path, base: Path = None) -> tuple[int, list]:
    copied, missing = 0, []
    folder = _curves_folder(signals, base)
    for test in signals.tests:
        source = folder / test.curves_file if folder else None
        if source is not None and source.is_file():
            destination = target / test.curves_file
            if not (destination.is_file() and source.samefile(destination)):
                shutil.copy(source, destination)
            copied += 1
        else:
            missing.append(test.curves_file)
    return copied, missing


def write_reference_curves(
    outdir: Path, producer: str, signals_by_zone: dict, base: Path = None
) -> dict:
    """Write the reference-curve tree, copying in the ``.csv`` files that are available.

    Parameters
    ----------
    outdir: Path
        Directory the generation writes into, alongside its ``Dynawo`` tree.
    producer: str
        Producer name, which names the subdirectory DyCoV looks for.
    signals_by_zone: dict
        ``{zone -> signals.ZoneSignals}``, as ``signals.parse_signals`` returns them.

    Returns
    -------
    dict
        ``target`` directory (None when nothing was described), how many ``tests`` were written,
        how many ``.csv`` were ``copied``, which ones are still ``missing`` and, in
        ``missing_from``, each folder a sheet names (None when it names none) with the files
        missing from it, the tests whose
        metadata the workbook left ``unfilled`` — DyCoV refuses to run those — and the tests of
        the revision of the DTR the workbook has no row for, ``without_row``.
    """
    described = {zone: signals for zone, signals in signals_by_zone.items() if signals.tests}
    if not described:
        return {
            "target": None,
            "tests": 0,
            "copied": 0,
            "missing": [],
            "missing_from": [],
            "unfilled": [],
            "without_row": [],
        }

    target = outdir / "ReferenceCurves" / producer
    target.mkdir(parents=True, exist_ok=True)
    (target / "CurvesFiles.ini").write_text(curves_files.text(described), encoding="utf-8")

    tests, copied, missing, missing_from, unfilled = 0, 0, [], [], []
    for signals in described.values():
        for test in signals.tests:
            (target / ("%s.dict" % test.name)).write_text(
                dicts.text(signals, test), encoding="utf-8"
            )
            tests += 1
            if any(key not in test.metadata for key in dicts.METADATA_HELP):
                unfilled.append(test.name)
        zone_copied, zone_missing = _copy_curves(signals, target, base)
        copied += zone_copied
        missing += zone_missing
        if zone_missing:
            missing_from.append((_curves_folder(signals, base), zone_missing))
    return {
        "target": target,
        "tests": tests,
        "copied": copied,
        "missing": missing,
        "missing_from": missing_from,
        "unfilled": unfilled,
        "without_row": [name for signals in described.values() for name in signals.without_row],
    }
