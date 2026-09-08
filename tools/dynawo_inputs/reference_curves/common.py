#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Pieces the two reference-curve files share: the time curve and DyCoV's own guidance."""

from __future__ import annotations

TIME_CURVE = "time"

# The guidance DyCoV's own dictionaries carry, kept so a hand-edited file reads the same.
ABC_HELP = [
    "# To represent a signal that is in raw abc three-phase form, the affected signal must be",
    "# tripled and the suffixes _a, _b and _c must be added as in the following example:",
    "#    SignalName_a =",
    "#    SignalName_b =",
    "#    SignalName_c =",
]


def dictionary_lines(curves: dict) -> list:
    """Render a curve dictionary: DyCoV's name on the left, the ``.csv`` column on the right.

    Parameters
    ----------
    curves: dict
        ``{DyCoV curve name -> column in the .csv}``.

    Returns
    -------
    list
        One assignment per curve.
    """
    return ["%s = %s" % (name, column) for name, column in curves.items()]


def time_line() -> str:
    """The time assignment every dictionary opens with.

    Returns
    -------
    str
        ``time = time``.
    """
    return "%s = %s" % (TIME_CURVE, TIME_CURVE)
