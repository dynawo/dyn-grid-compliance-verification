#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#

import numpy as np
import pytest

from dycov.gfm.calculators.amplitude_step import AmplitudeStep
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.calculators.rocof import RoCoF
from dycov.gfm.calculators.scr_jump import SCRJump

_CALCULATORS = (AmplitudeStep, RoCoF, SCRJump)


class _AnyParameters:
    """Answers every getter of the GFM parameters with the same value, in EMT."""

    def is_emt(self) -> bool:
        return True

    def __getattr__(self, name):
        return lambda *args, **kwargs: 1.0


def _calculate(calculator, time):
    return calculator(_AnyParameters()).calculate_envelopes(20.0, 2.0, 0.27, time, 0.0)


@pytest.mark.parametrize("calculator", _CALCULATORS)
@pytest.mark.parametrize(
    "time",
    [
        0.5,
        np.float64(0.5),
        np.array(0.5),
        [0.0, 0.1, 0.2],
        np.zeros((2, 3)),
        np.array(["0.0", "0.1"]),
        np.array([True, False]),
        np.array([0.0, 0.1, 0.2]) + 0j,
        np.array([0, 1, 2], dtype="timedelta64[ms]"),
        np.arange(6, dtype=np.uint8),
        np.arange(3000, 0, -1).astype(np.uint16),
    ],
)
def test_calculators_reject_a_time_that_is_not_a_vector_of_numbers(calculator, time):
    with pytest.raises(TypeError, match="one-dimensional array of floats or signed integers"):
        _calculate(calculator, time)


@pytest.mark.parametrize("time", [list(range(3000)), np.zeros((1000, 1))])
def test_the_time_error_does_not_reproduce_the_time(time):
    with pytest.raises(TypeError) as error:
        _calculate(SCRJump, time)
    assert len(str(error.value)) < 150


@pytest.mark.parametrize("calculator", _CALCULATORS)
@pytest.mark.parametrize(
    "time, message",
    [
        (np.array([0.0]), "at least two points"),
        (np.array([3.0, 0.05, 0.1, 0.2, 2.0, -1.0]), "strictly increasing"),
        (np.array([5.0, 4.0, 3.0, 2.0, 1.0]), "strictly increasing"),
        (np.array([0.0, 0.1, 0.1, 0.2]), "strictly increasing"),
        (np.array([0.0, np.nan, 0.2]), "finite"),
        (np.array([0.0, 0.1, np.inf]), "finite"),
        (np.concatenate((np.linspace(0, 0.001, 50), np.linspace(0.01, 5, 200))), "evenly"),
        (np.array([0.0, 0.1, 0.3, 0.4]), "evenly"),
    ],
)
def test_calculators_reject_an_unusable_time_vector(calculator, time, message):
    with pytest.raises(ValueError, match=message):
        _calculate(calculator, time)


@pytest.mark.parametrize(
    "time",
    [
        np.linspace(0.0, 5.0, 3000),
        np.linspace(-1.0, 5.0, 3000),
        np.linspace(0.0, 5.0, 3000, dtype=np.float32),
        np.linspace(-1.0, 5.0, 3000, dtype=np.float32),
        np.linspace(1e4, 1e4 + 0.001, 600),
        np.linspace(1e5, 1e5 + 0.01, 3000),
        np.linspace(1e6, 1e6 + 1.0, 10001),
        np.arange(0, 3000),
        np.array([0.0, 0.1]),
    ],
)
def test_evenly_spaced_time_vectors_are_accepted_in_any_precision(time):
    GFMCalculator._check_time_array(time)
