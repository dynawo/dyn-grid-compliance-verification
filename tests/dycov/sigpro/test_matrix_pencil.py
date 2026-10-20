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


def _damped_oscillation(damping_ratio: float, frequency: float = 2.0) -> np.ndarray:
    natural = 2 * np.pi * frequency
    damped = natural * np.sqrt(1 - damping_ratio**2)
    return 0.5 + 0.3 * np.exp(-damping_ratio * natural * _TIME) * np.cos(damped * _TIME)


@pytest.mark.parametrize("damping_ratio", [0.05, 0.2, 0.4, 0.6])
def test_damping_ratio_of_a_damped_oscillation(damping_ratio):
    noise = 1e-4 * np.random.default_rng(0).standard_normal(len(_TIME))

    modes = matrix_pencil.oscillation_modes(
        _TIME, _damped_oscillation(damping_ratio) + noise, 0.1, 10.0, 1e-3
    )

    assert len(modes) == 1
    assert modes[0].damping_ratio == pytest.approx(damping_ratio, abs=0.01)
    assert modes[0].frequency == pytest.approx(2.0 * np.sqrt(1 - damping_ratio**2), rel=0.02)


def test_lightly_damped_oscillation_on_top_of_a_decay():
    decay = 0.5 + 0.3 * np.exp(-_TIME / 0.2)
    oscillation = 0.05 * np.exp(-0.1 * 2 * np.pi * 2 * _TIME) * np.sin(2 * np.pi * 2 * _TIME)

    modes = matrix_pencil.oscillation_modes(_TIME, decay + oscillation, 0.1, 10.0, 1e-3)

    assert [round(mode.damping_ratio, 2) for mode in modes] == [0.1]


def test_aperiodic_decay_does_not_oscillate():
    signal = 0.5 + 0.3 * np.exp(-_TIME / 0.2)

    assert matrix_pencil.oscillation_modes(_TIME, signal, 0.1, 10.0, 1e-3) == []


def test_flat_signal_does_not_oscillate():
    assert matrix_pencil.oscillation_modes(_TIME, np.full_like(_TIME, 0.5), 0.1, 10.0, 1e-3) == []


def test_oscillation_outside_the_band_is_ignored():
    assert matrix_pencil.oscillation_modes(_TIME, _damped_oscillation(0.1), 5.0, 10.0, 1e-3) == []


@pytest.mark.parametrize("time", [np.array([]), np.array([1.0]), np.arange(0.0, 0.05, 0.001)])
def test_window_shorter_than_a_period_does_not_oscillate(time):
    assert matrix_pencil.oscillation_modes(time, np.sin(time), 0.1, 10.0, 1e-3) == []


@pytest.mark.parametrize("noise", [1e-6, 1e-5, 1e-4])
def test_numerical_noise_of_a_flat_signal_does_not_oscillate(noise):
    signal = 0.5 + noise * np.random.default_rng(1).standard_normal(len(_TIME))

    assert matrix_pencil.oscillation_modes(_TIME, signal, 0.1, 10.0, 1e-3) == []
