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


def tap_of_ratio(ratio: float, n_prises: int, r_min: float, r_max: float) -> int:
    """The tap whose ratio is *ratio*, refusing a ratio that lies between two taps."""
    if r_max == r_min:
        raise ValueError("'r_max' and 'r_min' are equal, so no tap has ratio %s" % ratio)
    exact = (ratio - r_min) / (r_max - r_min) * int(n_prises)
    tap = round(exact)
    if abs(exact - tap) > 1e-6 or not 0 <= tap <= int(n_prises):
        raise ValueError(
            "ratio %s is not on a tap: (r_0 - r_min) / (r_max - r_min) * N_prises = %s, which is "
            "not a whole number between 0 and %s" % (ratio, exact, int(n_prises))
        )
    return tap


def ratio_of_tap(tap: int, n_prises: int, r_min: float, r_max: float) -> float:
    """The ratio of tap *tap*, as Dynawo derives it (TransformerRatioTapChanger.mo)."""
    return r_min + (r_max - r_min) * int(tap) / int(n_prises)


def transformer_taps(
    n_prises: int, r_min: float, r_max: float, tap_0=None, r_0=None
) -> dict:
    """OLTC tap parameters from the Excel's ``N_prises`` / ``r_min`` / ``r_max`` / ``Tap_0``|``r_0``.

    ``NbTap = N_prises + 1``. The starting tap comes from ``Tap_0``, or from ``r_0`` when only the
    ratio is given, and defaults to the middle tap (nominal ratio, the DTR taps being symmetric
    about it). Dynawo derives the starting ratio from the tap, so both rows must agree.
    """
    nb_tap = int(n_prises) + 1
    if tap_0 is None and r_0 is None:
        tap = (nb_tap - 1) // 2
    elif tap_0 is None:
        tap = tap_of_ratio(r_0, n_prises, r_min, r_max)
    else:
        tap = int(tap_0)
        if not 0 <= tap <= int(n_prises):
            raise ValueError("'Tap_0' is %s, outside 0..N_prises (%s)" % (tap, int(n_prises)))
        if r_0 is not None and abs(ratio_of_tap(tap, n_prises, r_min, r_max) - r_0) > 1e-6:
            raise ValueError(
                "'Tap_0' (%s) and 'r_0' (%s) disagree: tap %s has ratio %s. Fill in one of the "
                "two rows, or make them consistent."
                % (tap, r_0, tap, ratio_of_tap(tap, n_prises, r_min, r_max))
            )
    return {
        "NbTap": nb_tap,
        "Tap0": tap,
        "RatioTfoMinPu": r_min,
        "RatioTfoMaxPu": r_max,
        "RatioTfo0Pu": ratio_of_tap(tap, n_prises, r_min, r_max),
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
