#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import configparser
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dycov.configuration.cfg import config
from dycov.core.parameters import Parameters
from dycov.gfm.calculators.phase_jump import PhaseJump
from dycov.gfm.parameters import GFMParameters
from dycov.gfm.producer import GFMProducer

RESOURCES = Path(__file__).parent / "resources"

# The unit of RTE's example: 100 MVA, +/-120 MW, Xeff = 0.27 pu, H = 5 s
XEFF = 0.27
H = 5.0


def _phase_jump_params(p0: float, delta_phase: float, scr: float) -> str:
    return f"""
[DEFAULT]
P0={p0}
DeltaPhase={delta_phase}
SCR={scr}
RatioMin=0.7
RatioMax=1.3
Wb={2 * np.pi * 50}
U0=1.0
Ugr=1.0
MarginHigh=0.5
MarginLow=0.5
FinalAllowedTunnelVariation=0.05
FinalAllowedTunnelPn=0.02
Tpll=0.01
p_max_injection=1.2
p_min_injection=-1.2
[GFM Parameters]
Snom=1.0
"""


class ProducerHelper(GFMProducer):
    def __init__(self, config_str: str):
        self._config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        self._config.read_string(config_str)


class ParametersHelper(GFMParameters):
    def __init__(self, config_str: str):
        Parameters.__init__(self, None, "", None, False)
        self._emt = True
        self._producer = ProducerHelper(config_str)
        self._pcs_section = "DEFAULT"
        self._bm_section = "DEFAULT"
        self._oc_section = "DEFAULT"
        self._eval_sections = (self._oc_section, self._bm_section, self._pcs_section)

        config._pcs_default_config.read_string(config_str)


def _envelopes(
    params: str,
    D: float,
    time_array: np.ndarray,
    event_time: float = 0.0,
    emt: bool = False,
    inertia: float = H,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    test_params = ParametersHelper(params)
    test_params._emt = emt
    _, response, upper, lower = PhaseJump(gfm_params=test_params).calculate_envelopes(
        D=D, H=inertia, Xeff=XEFF, time_array=time_array, event_time=event_time
    )
    return response, upper, lower


def test_phase_jump_initialization():
    test_params = ParametersHelper(_phase_jump_params(0.95, np.deg2rad(30), 2))
    phase_jump = PhaseJump(gfm_params=test_params)

    assert phase_jump._delta_phase == pytest.approx(30)


@pytest.mark.parametrize(
    "title, p0, delta_phase, scr, D",
    [
        ("PhaseJump_RTE_SCR2_30deg_P095_D200", 0.95, np.deg2rad(30), 2, 200),
        ("PhaseJump_RTE_SCR2_30deg_P095_D350", 0.95, np.deg2rad(30), 2, 350),
        ("PhaseJump_RTE_SCR10_neg_Pm05_D95", -0.5, -0.3 * (XEFF + 0.1), 10, 95),
    ],
)
def test_phase_jump_reproduces_the_envelopes_of_rte(title, p0, delta_phase, scr, D):
    # RTE's notebook simulates from 1 s before the jump in steps of 5 ms
    time_array = np.linspace(-1, 5, 1201)
    response, upper, lower = _envelopes(_phase_jump_params(p0, delta_phase, scr), D, time_array)

    reference = pd.read_csv(RESOURCES / f"{title}.csv", sep=";")
    shown = (time_array >= -0.05 - 1e-9) & (time_array <= 4 + 1e-9)
    assert time_array[shown] == pytest.approx(reference["Time (s)"].to_numpy(), abs=1e-9)
    assert response[shown] == pytest.approx(reference["Ip PGU (pu)"].to_numpy(), abs=1e-6)
    assert upper[shown] == pytest.approx(reference["Ip upper (pu)"].to_numpy(), abs=1e-6)
    assert lower[shown] == pytest.approx(reference["Ip lower (pu)"].to_numpy(), abs=1e-6)


def test_phase_jump_envelopes_of_rte_on_a_time_vector_that_starts_at_the_jump():
    # DyCoV's own time vectors start at the jump, which the notebook ramps over its last 5 ms
    time_array = np.linspace(0, 4, 801)
    response, upper, lower = _envelopes(
        _phase_jump_params(0.95, np.deg2rad(30), 2), 200, time_array
    )

    reference = pd.read_csv(RESOURCES / "PhaseJump_RTE_SCR2_30deg_P095_D200.csv", sep=";")
    reference = reference[reference["Time (s)"] >= -1e-9]
    first_10_ms = time_array < 0.01
    assert upper[first_10_ms] == pytest.approx(
        reference["Ip upper (pu)"].to_numpy()[first_10_ms], abs=1e-6
    )
    assert response == pytest.approx(reference["Ip PGU (pu)"].to_numpy(), abs=0.015)
    assert upper == pytest.approx(reference["Ip upper (pu)"].to_numpy(), abs=0.015)
    assert lower == pytest.approx(reference["Ip lower (pu)"].to_numpy(), abs=0.015)


def test_phase_jump_envelopes_do_not_change_regime_at_critical_damping():
    scr = 2
    params = _phase_jump_params(0.5, np.deg2rad(30), scr)
    # The damping that made the formulas of the swing equation switch regime
    critical_damping = 2 / np.sqrt((XEFF + 1 / scr) / (2 * H * 2 * np.pi * 50))
    time_array = np.linspace(0, 5, 3000)

    _, upper_below, lower_below = _envelopes(params, critical_damping * 0.999, time_array)
    _, upper_above, lower_above = _envelopes(params, critical_damping * 1.001, time_array)

    assert upper_above == pytest.approx(upper_below, abs=1e-3)
    assert lower_above == pytest.approx(lower_below, abs=1e-3)


@pytest.mark.parametrize(
    "jump, dampings",
    [
        # Below D = 52 the peaks no longer fall to 5 % within the 5 s of the curves
        (0.6, np.arange(46, 58, 0.5)),
        # Below D = 1932 the response no longer has a peak below 5 % after its overshoot
        (0.3, np.arange(1912, 1952, 4.0)),
    ],
)
def test_phase_jump_envelopes_do_not_jump_where_the_peaks_stop_measuring_the_decay(jump, dampings):
    params = _phase_jump_params(0.0, jump * (XEFF + 1 / 2), 2)
    time_array = np.linspace(0, 5, 3000)

    envelopes = [_envelopes(params, D, time_array)[1:] for D in dampings]

    for (upper, lower), (next_upper, next_lower) in zip(envelopes, envelopes[1:]):
        assert next_upper == pytest.approx(upper, abs=0.02)
        assert next_lower == pytest.approx(lower, abs=0.02)


def test_phase_jump_envelopes_ignore_the_rounding_noise_of_a_settled_response():
    # The tail of this response, which does not oscillate, is rounding noise of about 1e-16
    params = _phase_jump_params(0.0, 0.3 * (XEFF + 1 / 10), 10)
    time_array = np.linspace(0, 5, 3000)

    envelopes = [_envelopes(params, D, time_array, inertia=2.0)[1:] for D in (369.9, 370, 370.1)]

    for (upper, lower), (next_upper, next_lower) in zip(envelopes, envelopes[1:]):
        assert next_upper == pytest.approx(upper, abs=0.01)
        assert next_lower == pytest.approx(lower, abs=0.01)


@pytest.mark.parametrize("D", [20.0, 200.0, 5000.0])
def test_phase_jump_envelopes_bound_the_response(D):
    time_array = np.linspace(0, 5, 3000)
    response, upper, lower = _envelopes(
        _phase_jump_params(0.5, -np.deg2rad(30), 10), D, time_array
    )

    # The envelopes stop at the limits of the unit, which the ideal response ignores
    limited_response = np.clip(response, -1.2, 1.2)
    assert np.isfinite(upper).all() and np.isfinite(lower).all()
    assert (lower <= limited_response + 1e-9).all()
    assert (limited_response <= upper + 1e-9).all()


def test_opposite_phase_jumps_give_mirrored_envelopes():
    time_array = np.linspace(0, 5, 3000)
    _, upper, lower = _envelopes(_phase_jump_params(0.0, np.deg2rad(20), 10), 200, time_array)
    _, upper_opposite, lower_opposite = _envelopes(
        _phase_jump_params(0.0, -np.deg2rad(20), 10), 200, time_array
    )

    assert upper_opposite == pytest.approx(-lower)
    assert lower_opposite == pytest.approx(-upper)


def test_phase_jump_envelopes_start_at_the_event():
    time_array = np.linspace(0, 5, 1001)
    event_index = 40

    response, upper, lower = _envelopes(
        _phase_jump_params(0.5, np.deg2rad(30), 2), 200, time_array, time_array[event_index]
    )

    assert (response[:event_index] == 0.5).all()
    assert (upper[:event_index] == 0.5).all() and (lower[:event_index] == 0.5).all()
    assert response[event_index] < 0.5
    assert (lower <= response + 1e-9).all() and (response <= upper + 1e-9).all()


def test_phase_jump_emt_delays_the_envelopes():
    params = _phase_jump_params(0.5, np.deg2rad(30), 2)
    time_array = np.linspace(0, 5, 1001)
    delay_samples = int(0.02 / (time_array[1] - time_array[0])) + 1

    response, upper, lower = _envelopes(params, 200, time_array)
    response_emt, upper_emt, lower_emt = _envelopes(params, 200, time_array, emt=True)

    assert (response_emt[:delay_samples] == 0.5).all()
    assert (upper_emt[:delay_samples] == 0.5).all() and (lower_emt[:delay_samples] == 0.5).all()
    assert response_emt[delay_samples:] == pytest.approx(response[:-delay_samples])
    assert upper_emt[delay_samples:] == pytest.approx(upper[:-delay_samples])
    assert lower_emt[delay_samples:] == pytest.approx(lower[:-delay_samples])
