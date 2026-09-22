#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""``CurvesFiles.ini``: the ``.csv`` of every test and the per-zone curve dictionaries."""

from __future__ import annotations

from .common import ABC_HELP, dictionary_lines, time_line

_ZONE_SECTIONS = {"Zone1": "Curves-Dictionary-Zone1", "Zone3": "Curves-Dictionary-Zone3"}


def text(signals_by_zone: dict) -> str:
    """Render the whole file for the zones the workbook describes.

    Parameters
    ----------
    signals_by_zone: dict
        ``{zone -> signals.ZoneSignals}``, only the zones that describe tests.

    Returns
    -------
    str
        The file contents, ready to write.
    """
    lines = ["[Curves-Files]"]
    for zone, signals in signals_by_zone.items():
        if not signals.tests:
            continue
        lines.append("#Curves for %s" % zone)
        for test in signals.tests:
            lines.append("%s = %s" % (test.name, test.curves_file))

    lines += ["", "[Curves-Dictionary]"] + ABC_HELP + [time_line()]
    for zone, signals in signals_by_zone.items():
        if not signals.curves:
            continue
        lines += ["", "[%s]" % _ZONE_SECTIONS[zone]] + dictionary_lines(signals.curves)
    return "\n".join(lines) + "\n"
