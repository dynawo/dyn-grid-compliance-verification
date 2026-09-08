#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
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
    """Split a short-circuit impedance into its resistance and reactance.

    ``Z_cc = sqrt(R^2 + X^2)`` and ``R = k * X`` give ``X = Z_cc / sqrt(1 + k^2)``.

    Parameters
    ----------
    z_cc: float
        Short-circuit impedance, in pu.
    rx_ratio: float
        Ratio ``k = R/X`` of the same impedance.

    Returns
    -------
    tuple[float, float]
        ``(R, X)`` on the same per-unit base as *z_cc*: this changes no base.
    """
    x = z_cc / math.sqrt(1.0 + rx_ratio**2)
    r = rx_ratio * x
    return r, x


def rebase(value_pu: float, s_nom: float, s_ref: float = SN_REF) -> float:
    """Rebase a per-unit impedance onto another apparent-power base.

    Parameters
    ----------
    value_pu: float
        Impedance in pu on *s_nom*.
    s_nom: float
        Base the value comes on, in MVA.
    s_ref: float
        Base the value is taken to, in MVA.

    Returns
    -------
    float
        The impedance in pu on *s_ref*; the voltage base is unchanged.
    """
    return value_pu * s_ref / s_nom


def transformer_impedance(
    z_cc: float, rx_ratio: float, s_nom: float, s_ref: float = SN_REF
) -> tuple[float, float]:
    """Split a transformer's short-circuit impedance and rebase it.

    Parameters
    ----------
    z_cc: float
        Short-circuit impedance, in pu on *s_nom*.
    rx_ratio: float
        Ratio ``k = R/X`` of the same impedance.
    s_nom: float
        Base the impedance comes on, in MVA.
    s_ref: float
        Base the network element is written on, in MVA.

    Returns
    -------
    tuple[float, float]
        ``(RPu, XPu)`` on *s_ref*.
    """
    r, x = short_circuit_rx(z_cc, rx_ratio)
    return rebase(r, s_nom, s_ref), rebase(x, s_nom, s_ref)


def tap_of_ratio(ratio: float, n_prises: int, r_min: float, r_max: float) -> int:
    """Find the tap that gives a ratio.

    Parameters
    ----------
    ratio: float
        Transformation ratio, in pu.
    n_prises: int
        Number of taps of the changer.
    r_min: float
        Ratio of the lowest tap.
    r_max: float
        Ratio of the highest tap.

    Returns
    -------
    int
        The tap holding *ratio*; a ratio between two taps is refused.
    """
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
    """Compute the ratio of a tap, the way Dynawo derives it.

    Parameters
    ----------
    tap: int
        Tap position, from 0 to *n_prises*.
    n_prises: int
        Number of taps of the changer.
    r_min: float
        Ratio of the lowest tap.
    r_max: float
        Ratio of the highest tap.

    Returns
    -------
    float
        The ratio of that tap, as ``TransformerRatioTapChanger.mo`` computes it.
    """
    return r_min + (r_max - r_min) * int(tap) / int(n_prises)


def transformer_taps(
    n_prises: int, r_min: float, r_max: float, tap_0=None, r_0=None
) -> dict:
    """Build the OLTC parameters of a transformer from the workbook's tap rows.

    ``NbTap = N_prises + 1``, and the starting tap defaults to the middle one (nominal ratio, the
    DTR taps being symmetric about it). Dynawo derives the starting ratio from the tap, so when
    both rows are filled in they must agree.

    Parameters
    ----------
    n_prises: int
        Number of taps of the changer.
    r_min: float
        Ratio of the lowest tap.
    r_max: float
        Ratio of the highest tap.
    tap_0: int, optional
        Tap the simulation starts at.
    r_0: float, optional
        Ratio the simulation starts at, when the tap itself is not given.

    Returns
    -------
    dict
        The tap parameters Dynawo reads: ``NbTap``, ``Tap0``, ``RatioTfoMinPu``,
        ``RatioTfoMaxPu`` and the derived ``RatioTfo0Pu``.
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
    """Convert a collector line (PI model) to per-unit values.

    ``Zbase = u_nom^2 / s_ref`` (*u_nom* in kV, *s_ref* in MVA, so ohms): the series values divide
    by it and the shunt ones multiply by it.

    Parameters
    ----------
    r_ohm: float
        Series resistance, in ohms.
    x_ohm: float
        Series reactance, in ohms.
    b_siemens: float
        Shunt susceptance, in siemens.
    g_siemens: float
        Shunt conductance, in siemens.
    u_nom: float
        Nominal voltage of the node the line connects to, in kV.
    s_ref: float
        Base the network element is written on, in MVA.

    Returns
    -------
    dict
        ``RPu``, ``XPu``, ``BPu`` and ``GPu`` on *s_ref*.
    """
    z_base = u_nom**2 / s_ref
    return {
        "RPu": r_ohm / z_base,
        "XPu": x_ohm / z_base,
        "BPu": b_siemens * z_base,
        "GPu": g_siemens * z_base,
    }


def load_pu(p_mw: float, q_mvar: float, s_ref: float = SN_REF) -> tuple[float, float]:
    """Convert a load's power to per-unit values.

    Parameters
    ----------
    p_mw: float
        Active power, in MW.
    q_mvar: float
        Reactive power, in MVAr.
    s_ref: float
        Base the network element is written on, in MVA.

    Returns
    -------
    tuple[float, float]
        ``(PRefPu, QRefPu)`` on *s_ref*.
    """
    return p_mw / s_ref, q_mvar / s_ref
