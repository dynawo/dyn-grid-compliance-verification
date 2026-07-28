# Copyright (c) 2024-2026, RTE (https://www.rte-france.com)
# SPDX-License-Identifier: MPL-2.0
"""Tests for the electrical computations of the Excel -> DyCoV input generator
(``tools/dynawo_inputs/electrical.py``), per design doc section 9."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# The tool lives under tools/ (outside the dycov package); import it by path.
_TOOL_DIR = Path(__file__).resolve().parents[2] / "tools" / "dynawo_inputs"
sys.path.insert(0, str(_TOOL_DIR))

import electrical as el  # noqa: E402


def test_short_circuit_rx_purely_reactive():
    r, x = el.short_circuit_rx(0.1, 0.0)
    assert r == 0.0
    assert x == pytest.approx(0.1)


def test_short_circuit_rx_equal_r_x():
    # k = 1 -> R == X and Z = sqrt(2) * X
    r, x = el.short_circuit_rx(1.0, 1.0)
    assert r == pytest.approx(x)
    assert math.hypot(r, x) == pytest.approx(1.0)


def test_short_circuit_rx_recovers_zcc_and_ratio():
    z_cc, k = 0.18, 0.1
    r, x = el.short_circuit_rx(z_cc, k)
    assert math.hypot(r, x) == pytest.approx(z_cc)
    assert r / x == pytest.approx(k)


def test_rebase_scales_with_power_base():
    # pu impedance grows with the target power base
    assert el.rebase(0.1, 50.0) == pytest.approx(0.2)  # 0.1 * 100 / 50
    assert el.rebase(0.1, 100.0) == pytest.approx(0.1)


def test_transformer_impedance_reactive_rebased():
    r_pu, x_pu = el.transformer_impedance(0.1, 0.0, s_nom=50.0)
    assert r_pu == 0.0
    assert x_pu == pytest.approx(0.2)


def test_transformer_impedance_with_ratio():
    r_pu, x_pu = el.transformer_impedance(0.1, 0.1, s_nom=100.0)
    r, x = el.short_circuit_rx(0.1, 0.1)
    assert (r_pu, x_pu) == pytest.approx((r, x))  # s_nom == s_ref -> no rebase


def test_transformer_taps_matches_reference_example():
    taps = el.transformer_taps(20, 0.9, 1.1)
    assert taps == {
        "NbTap": 21,
        "Tap0": 10,
        "RatioTfoMinPu": 0.9,
        "RatioTfoMaxPu": 1.1,
        "RatioTfo0Pu": 1.0,
    }


def test_line_impedance_pu():
    # Un = 33 kV, SnRef = 100 MVA -> Zbase = 33^2 / 100 = 10.89 ohm
    out = el.line_impedance(0.2, 1.0, 0.0, 0.0, u_nom=33.0)
    z_base = 33.0**2 / 100.0
    assert out["RPu"] == pytest.approx(0.2 / z_base)
    assert out["XPu"] == pytest.approx(1.0 / z_base)
    assert out["BPu"] == 0.0
    assert out["GPu"] == 0.0


def test_line_impedance_shunt_multiplies_by_zbase():
    z_base = 63.0**2 / 100.0
    out = el.line_impedance(0.0, 0.0, 1e-4, 2e-4, u_nom=63.0)
    assert out["BPu"] == pytest.approx(1e-4 * z_base)
    assert out["GPu"] == pytest.approx(2e-4 * z_base)


def test_load_pu_matches_reference_example():
    # examples/Model Aux_Load: P_A = 1 MW -> load_PRefPu = 0.01, Q_A = 0.5 MVAr -> 0.005
    p_ref, q_ref = el.load_pu(1.0, 0.5)
    assert p_ref == pytest.approx(0.01)
    assert q_ref == pytest.approx(0.005)
