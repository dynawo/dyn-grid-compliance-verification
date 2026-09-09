#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""PAR sets of the transformers: the group one, the main one (with its OLTC) and the auxiliary."""

from __future__ import annotations

import electrical as el
import parse as P

PU_BASE_NOTE = "impedances in pu, base SnRef = 100 MVA"


def _impedance_params(r_pu: float, x_pu: float) -> list:
    return [
        {"name": "transformer_RPu", "type": "DOUBLE", "value": r_pu, "comments": [PU_BASE_NOTE]},
        {"name": "transformer_XPu", "type": "DOUBLE", "value": x_pu},
        {"name": "transformer_BPu", "type": "DOUBLE", "value": 0.0},
        {"name": "transformer_GPu", "type": "DOUBLE", "value": 0.0},
    ]


def group_par_set(par_id: str, zone1: dict, s_nom) -> tuple:
    """Build the generating unit's step-up transformer (``TransformerFixedRatio``).

    Parameters
    ----------
    par_id: str
        Id of the set, matching the transformer's block in the DYD.
    zone1: dict
        Rows of the ``Zone1a`` sheet, which hold ``Z_cc_TG`` and its ratio ``r_TG``.
    s_nom: str or float
        Impedance base: ``SnZone1`` in Zone1, ``SnZone3`` in Zone3.

    Returns
    -------
    tuple
        ``(set id, parameters)``.
    """
    number = P.numbers("Zone1", zone1)
    r_pu, x_pu = el.transformer_impedance(
        number("group_impedance"), number("group_rx_ratio"), float(s_nom)
    )
    return par_id, _impedance_params(r_pu, x_pu) + [
        {"name": "transformer_rTfoPu", "type": "DOUBLE", "value": number("group_ratio")},
    ]


def main_par_set(par_id: str, zone3: dict) -> tuple:
    """Build the plant's main transformer (``TransformerRatioTapChanger``): impedance and taps.

    Parameters
    ----------
    par_id: str
        Id of the set, matching the transformer's block in the DYD.
    zone3: dict
        Rows of the ``Zone3`` sheet: ``Z_cc_TP``, the tap range and the starting tap.

    Returns
    -------
    tuple
        ``(set id, parameters)``.
    """
    number = P.numbers("Zone3", zone3)
    s_nom = number("s_nom")
    r_pu, x_pu = el.transformer_impedance(number("main_impedance"), number("main_rx_ratio"), s_nom)
    taps = el.transformer_taps(
        int(number("taps")),
        number("tap_ratio_min"),
        number("tap_ratio_max"),
        tap_0=P.optional_number("Zone3", zone3, "starting_tap"),
        r_0=P.optional_number("Zone3", zone3, "starting_ratio"),
    )
    return par_id, [
        {"name": "transformer_SNom", "type": "DOUBLE", "value": s_nom, "comments": [PU_BASE_NOTE]},
        {"name": "transformer_RPu", "type": "DOUBLE", "value": r_pu},
        {"name": "transformer_XPu", "type": "DOUBLE", "value": x_pu},
        {"name": "transformer_BPu", "type": "DOUBLE", "value": 0.0},
        {"name": "transformer_GPu", "type": "DOUBLE", "value": 0.0},
        {"name": "transformer_AlphaTfo0", "type": "DOUBLE", "value": 0.0},
        {"name": "transformer_RatioTfo0Pu", "type": "DOUBLE", "value": taps["RatioTfo0Pu"]},
        {"name": "transformer_RatioTfoMaxPu", "type": "DOUBLE", "value": taps["RatioTfoMaxPu"]},
        {"name": "transformer_RatioTfoMinPu", "type": "DOUBLE", "value": taps["RatioTfoMinPu"]},
        {"name": "transformer_NbTap", "type": "INT", "value": taps["NbTap"]},
        {"name": "transformer_Tap0", "type": "INT", "value": taps["Tap0"]},
    ]


def aux_par_set(par_id: str, zone3: dict) -> tuple:
    """Build the auxiliary-load transformer (``TransformerFixedRatio``), on the ``Sn_A`` base.

    Parameters
    ----------
    par_id: str
        Id of the set, matching the transformer's block in the DYD.
    zone3: dict
        Rows of the ``Zone3`` sheet: ``Z_cc_TA``, its ratio and the auxiliary rating.

    Returns
    -------
    tuple
        ``(set id, parameters)``.
    """
    number = P.numbers("Zone3", zone3)
    r_pu, x_pu = el.transformer_impedance(
        number("aux_impedance"), number("aux_rx_ratio"), number("aux_s_nom")
    )
    return par_id, _impedance_params(r_pu, x_pu) + [
        {"name": "transformer_rTfoPu", "type": "DOUBLE", "value": number("aux_ratio")},
    ]
