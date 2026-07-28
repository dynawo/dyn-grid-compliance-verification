#!/usr/bin/env python3
# Copyright (c) 2024-2026, RTE (https://www.rte-france.com)
# SPDX-License-Identifier: MPL-2.0
"""Electrical computations for the Excel -> DyCoV input generator.

Pure, standard-agnostic helpers implementing the conversions of the design doc
(``docs/design/DyCoV_input_generation_from_excel_design.md`` section 9): transformer
short-circuit impedance and OLTC taps, per-unit base changes, and collector-line impedance.

Dynawo transformer/line impedances are per-unit on ``SnRef = 100 MVA`` (voltage base = the
element's own nominal, so only the power base changes). No third-party dependency.
"""

from __future__ import annotations

import math

# Dynawo default apparent-power base (MVA) for network-element per-unit values.
SN_REF = 100.0


def short_circuit_rx(z_cc: float, rx_ratio: float) -> tuple[float, float]:
    """Split a short-circuit impedance ``Z_cc`` into ``(R, X)`` given ``k = R/X``.

    ``Z_cc = sqrt(R^2 + X^2)`` and ``R = k * X`` give ``X = Z_cc / sqrt(1 + k^2)``. Values are on
    the same per-unit base as ``z_cc`` (no base change here).
    """
    x = z_cc / math.sqrt(1.0 + rx_ratio**2)
    r = rx_ratio * x
    return r, x


def rebase(value_pu: float, s_nom: float, s_ref: float = SN_REF) -> float:
    """Rebase a per-unit impedance from ``s_nom`` to ``s_ref`` (voltage base unchanged)."""
    return value_pu * s_ref / s_nom


def transformer_impedance(
    z_cc: float, rx_ratio: float, s_nom: float, s_ref: float = SN_REF
) -> tuple[float, float]:
    """Transformer ``(RPu, XPu)`` on ``s_ref`` from ``Z_cc`` (pu on ``s_nom``) and ``k = R/X``."""
    r, x = short_circuit_rx(z_cc, rx_ratio)
    return rebase(r, s_nom, s_ref), rebase(x, s_nom, s_ref)


def transformer_taps(n_prises: int, r_min: float, r_max: float) -> dict:
    """OLTC tap parameters from the Excel's ``N_prises`` / ``r_min`` / ``r_max``.

    ``NbTap = N_prises + 1``; the nominal ratio is 1 at the middle tap ``Tap0 = (NbTap - 1) // 2``
    (the DTR taps are symmetric about nominal, i.e. ``N_prises`` is even -> ``NbTap`` odd).
    """
    nb_tap = int(n_prises) + 1
    return {
        "NbTap": nb_tap,
        "Tap0": (nb_tap - 1) // 2,
        "RatioTfoMinPu": r_min,
        "RatioTfoMaxPu": r_max,
        "RatioTfo0Pu": 1.0,
    }


def line_impedance(
    r_ohm: float,
    x_ohm: float,
    b_siemens: float,
    g_siemens: float,
    u_nom: float,
    s_ref: float = SN_REF,
) -> dict:
    """Collector-line (PI model) per-unit values on ``s_ref``.

    ``Zbase = u_nom^2 / s_ref`` (``u_nom`` in kV, ``s_ref`` in MVA -> ohms). Series R/X divide by
    ``Zbase``; shunt B/G (in 1/ohm) multiply by ``Zbase``.
    """
    z_base = u_nom**2 / s_ref
    return {
        "RPu": r_ohm / z_base,
        "XPu": x_ohm / z_base,
        "BPu": b_siemens * z_base,
        "GPu": g_siemens * z_base,
    }


def load_pu(p_mw: float, q_mvar: float, s_ref: float = SN_REF) -> tuple[float, float]:
    """Auxiliary-load ``(PRefPu, QRefPu)`` on ``s_ref`` from active/reactive power in MW/MVAr."""
    return p_mw / s_ref, q_mvar / s_ref
