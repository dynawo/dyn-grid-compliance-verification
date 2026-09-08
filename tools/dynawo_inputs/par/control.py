#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The control sheets turned into PAR parameters, and split per zone."""

from __future__ import annotations

import parse as P
import workbook as wb


def control_params(workbook: dict, lv_control: bool) -> list:
    """Read every selected variant's parameters, flat, in workbook order.

    Parameters
    ----------
    workbook: dict
        The whole workbook, as ``{sheet name -> grid}``.
    lv_control: bool
        Whether the converter controls at its own output, which fixes the base the template
        annotates as "Un1 ou Un2".

    Returns
    -------
    list
        Parameters as dicts of block/name/type/value/comments, the order the PAR will keep.
    """
    return P.parse_control_params(workbook, "Un2" if lv_control else "Un1")


def for_zone(params: list, zones: dict, zone: str) -> list:
    """Select the parameters a zone's PAR carries.

    A control block enters a zone only if it declares that zone in ``Général``, so a block with
    no declared zone enters neither.

    Parameters
    ----------
    params: list
        Control parameters of every selected variant.
    zones: dict
        Zones each block declares, e.g. ``{"REEC": ["Zone1", "Zone3"]}``.
    zone: str
        Zone being emitted, ``Zone1`` or ``Zone3``.

    Returns
    -------
    list
        The parameters of that zone, without the provenance label the PAR does not carry.
    """
    return [
        {k: v for k, v in p.items() if k != "block"}
        for p in params
        if zone in zones.get(p["block"], [])
    ]


def empty_zone1_reason(config) -> str:
    """Explain why Zone1 came out without control parameters.

    Zone1 is never generated silently incomplete: either no selected block declares it, or the
    blocks that do declare it have no values in their sheets.

    Parameters
    ----------
    config: workbook.Config
        Parsed contents of the ``Général`` sheet.

    Returns
    -------
    str
        The message the tool refuses with.
    """
    declared = [
        block for block, choice in config.selections
        if wb._strip_accents(choice) not in wb._NO_BLOCK
        and "Zone1" in config.zones.get(block, [])
    ]
    if not declared:
        return (
            "no selected control block declares Zone1 (see the 'Zone' column in 'Général'); "
            "refusing to generate an incomplete Zone1."
        )
    return (
        f"the Zone1 control blocks ({', '.join(declared)}) carry no parameter values — the "
        f"parameter sheets look unfilled; refusing to generate an incomplete Zone1."
    )
