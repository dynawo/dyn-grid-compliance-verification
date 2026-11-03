#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import numpy as np
import pytest

from dycov.sigpro import matrix_pencil

_TIME = np.arange(0.0, 5.0, 0.001)


def _modes(signal, time=_TIME, t_from=0.005, t_to=5.0, f_min=0.1, f_max=10.0):
    return matrix_pencil.oscillation_modes(time, signal, t_from, t_to, f_min, f_max, 0.005, 6)


def _damped_oscillation(damping_ratio: float, frequency: float = 2.0) -> np.ndarray:
    natural = 2 * np.pi * frequency
    damped = natural * np.sqrt(1 - damping_ratio**2)
    return 0.5 + 0.3 * np.exp(-damping_ratio * natural * _TIME) * np.cos(damped * _TIME)


@pytest.mark.parametrize("damping_ratio", [0.05, 0.2, 0.4, 0.6])
def test_damping_ratio_of_a_damped_oscillation(damping_ratio):
    [mode] = _modes(_damped_oscillation(damping_ratio))

    assert mode.damping_ratio == pytest.approx(damping_ratio, abs=0.01)
    assert mode.frequency == pytest.approx(2.0 * np.sqrt(1 - damping_ratio**2), rel=0.02)


def test_lightly_damped_oscillation_on_top_of_a_decay():
    decay = 0.5 + 0.3 * np.exp(-_TIME / 0.2)
    oscillation = 0.05 * np.exp(-0.1 * 2 * np.pi * 2 * _TIME) * np.sin(2 * np.pi * 2 * _TIME)

    modes = _modes(decay + oscillation)

    assert [round(mode.damping_ratio, 2) for mode in modes] == [0.1]


def test_the_amplitude_is_in_the_units_of_the_signal():
    oscillation = 0.05 * np.exp(-0.1 * 2 * np.pi * 2 * _TIME) * np.sin(2 * np.pi * 2 * _TIME)

    [mode] = _modes(0.5 + oscillation)

    assert mode.amplitude == pytest.approx(0.05, rel=0.02)


def test_aperiodic_decay_does_not_oscillate():
    assert _modes(0.5 + 0.3 * np.exp(-_TIME / 0.2)) == []


def test_flat_signal_does_not_oscillate():
    assert _modes(np.full_like(_TIME, 0.5)) == []


def test_a_ramp_up_to_a_limit_does_not_oscillate():
    assert _modes(np.clip(_TIME / 0.5, 0.0, 1.0) * 0.5) == []


def test_oscillation_outside_the_band_is_ignored():
    assert _modes(_damped_oscillation(0.1), f_min=5.0) == []


def test_oscillation_outside_the_window_is_ignored():
    signal = np.where(_TIME < 2.0, 0.5 + 0.1 * np.sin(2 * np.pi * 2 * _TIME), 0.5)

    assert _modes(signal, t_from=2.005) == []


def test_window_with_too_few_samples_for_the_pencil_has_no_mode():
    assert _modes(_damped_oscillation(0.1), t_to=0.05) == []


@pytest.mark.parametrize("time", [np.array([]), np.array([1.0])])
def test_signal_without_two_instants_has_no_mode(time):
    assert _modes(np.ones_like(time), time=time) == []
