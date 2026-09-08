#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Pieces the PAR builders share: one comment and the per-zone numeric accessor."""

from __future__ import annotations

from functools import partial

import parse as P

PU_BASE_NOTE = "impedances in pu, base SnRef = 100 MVA"


def number_of(zone: dict):
    """Bind the numeric accessor to one zone sheet, so a builder reads its rows by name alone.

    Parameters
    ----------
    zone: dict
        Rows of a zone sheet, as ``parse.parse_zone`` returns them.

    Returns
    -------
    callable
        ``name -> float``, raising with the sheet and row named when a value is unusable.
    """
    return partial(P.zone_number, zone)
