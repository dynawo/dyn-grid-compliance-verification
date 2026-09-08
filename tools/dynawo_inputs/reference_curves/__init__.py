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


def _copy_curves(signals, target: Path) -> tuple[int, list]:
    copied, missing = 0, []
    for test in signals.tests:
        source = Path(signals.folder) / test.curves_file if signals.folder else None
        if source is not None and source.is_file():
            shutil.copy(source, target / test.curves_file)
            copied += 1
        else:
            missing.append(test.curves_file)
    return copied, missing


def write_reference_curves(outdir: Path, producer: str, signals_by_zone: dict) -> dict:
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
        how many ``.csv`` were ``copied`` and which ones are still ``missing``.
    """
    described = {zone: signals for zone, signals in signals_by_zone.items() if signals.tests}
    if not described:
        return {"target": None, "tests": 0, "copied": 0, "missing": []}

    target = outdir / "ReferenceCurves" / producer
    target.mkdir(parents=True, exist_ok=True)
    (target / "CurvesFiles.ini").write_text(curves_files.text(described), encoding="utf-8")

    tests, copied, missing = 0, 0, []
    for signals in described.values():
        for test in signals.tests:
            (target / ("%s.dict" % test.name)).write_text(dicts.text(signals), encoding="utf-8")
            tests += 1
        zone_copied, zone_missing = _copy_curves(signals, target)
        copied += zone_copied
        missing += zone_missing
    return {"target": target, "tests": tests, "copied": copied, "missing": missing}
