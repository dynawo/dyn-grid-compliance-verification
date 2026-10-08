#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dycov.curves.anonymizer import anonymize
from dycov.curves.anonymizer.deripple import _remove_spikes, _ripple_spans, deripple_curves


@pytest.fixture()
def rippled_curve() -> pd.DataFrame:
    """A step, then half a second of the oscillation a converter model adds to it."""
    t = np.arange(0.0, 10.0, 1e-3)
    burst = (t >= 5.0) & (t < 5.5)
    return pd.DataFrame(
        {
            "time": t,
            "signal1": np.where(t < 5.0, 1.0, 0.5) + burst * 0.4 * np.sin(2 * np.pi * 15.0 * t),
        }
    )


def test_ripple_spans_finds_the_oscillation(rippled_curve):
    spans = _ripple_spans(rippled_curve["time"].to_numpy(), rippled_curve["signal1"].to_numpy())

    assert len(spans) == 1
    assert spans[0][0] >= 5.0
    assert spans[0][1] <= 5.6


@pytest.fixture()
def response_that_dies_out() -> pd.DataFrame:
    """A step answered by an oscillation that swings fast for a third of a second while it rings
    down, as a converter does when a fault clears."""
    t = np.arange(0.0, 10.0, 1e-3)
    after = np.clip(t - 5.0, 0.0, None)
    ring_down = 0.4 * np.exp(-after / 0.1) * (t >= 5.0) * np.sin(2 * np.pi * 10.0 * after)
    return pd.DataFrame({"time": t, "signal1": np.where(t < 5.0, 1.0, 0.5) + ring_down})


def test_ripple_spans_ignores_a_curve_that_only_steps():
    t = np.arange(0.0, 10.0, 1e-3)
    values = np.where(t < 5.0, 1.0, 0.5)

    assert _ripple_spans(t, values) == []


def test_ripple_spans_ignores_a_response_that_dies_out(response_that_dies_out):
    spans = _ripple_spans(
        response_that_dies_out["time"].to_numpy(), response_that_dies_out["signal1"].to_numpy()
    )

    assert spans == []


def test_ripple_spans_ignores_a_burst_too_short_to_be_sustained():
    t = np.arange(0.0, 10.0, 1e-3)
    burst = (t >= 5.0) & (t < 5.15)
    values = 0.5 + burst * 0.4 * np.sin(2 * np.pi * 40.0 * (t - 5.0))

    assert _ripple_spans(t, values) == []


def test_deripple_curves_leaves_a_response_that_dies_out_untouched(response_that_dies_out):
    result = deripple_curves(response_that_dies_out, cutoff=5.0, event_time=5.0)

    original = response_that_dies_out["signal1"].to_numpy()
    assert np.array_equal(result["signal1"].to_numpy(), original)


def test_remove_spikes_replaces_a_one_sample_excursion():
    values = np.array([1.0, 1.0, 1.0, 2.5, 1.0, 1.0])

    without_spikes = _remove_spikes(values)

    assert without_spikes[3] == pytest.approx(1.0)
    assert list(without_spikes[:3]) == [1.0, 1.0, 1.0]


def test_remove_spikes_keeps_a_step():
    values = np.array([1.0, 1.0, 1.0, 0.5, 0.5, 0.5])

    assert list(_remove_spikes(values)) == list(values)


def test_deripple_curves_removes_the_oscillation(rippled_curve):
    result = deripple_curves(rippled_curve, cutoff=5.0, event_time=5.0)

    assert _ripple_spans(result["time"].to_numpy(), result["signal1"].to_numpy()) == []


def test_deripple_curves_leaves_the_rest_of_the_curve_alone(rippled_curve):
    result = deripple_curves(rippled_curve, cutoff=5.0, event_time=5.0)

    time = rippled_curve["time"].to_numpy()
    away = (time < 4.8) | (time > 5.8)
    difference = np.abs(
        result["signal1"].to_numpy()[away] - rippled_curve["signal1"].to_numpy()[away]
    )
    assert float(difference.max()) < 1e-3


def test_deripple_curves_keeps_every_sample(rippled_curve):
    result = deripple_curves(rippled_curve, cutoff=5.0, event_time=5.0)

    assert list(result["time"]) == list(rippled_curve["time"])
    assert list(result.columns) == list(rippled_curve.columns)


def test_deripple_curves_change_nothing_before_the_event(rippled_curve):
    result = deripple_curves(rippled_curve, cutoff=5.0, event_time=5.0)

    time = rippled_curve["time"].to_numpy()
    before = time < 5.0
    assert list(result["signal1"].to_numpy()[before]) == list(
        rippled_curve["signal1"].to_numpy()[before]
    )


def test_deripple_curves_still_smooths_a_ripple_of_its_own(rippled_curve):
    """An oscillation that does not come from the event is filtered where it sits."""
    result = deripple_curves(rippled_curve, cutoff=5.0, event_time=9.0)

    time = rippled_curve["time"].to_numpy()
    burst = (time >= 5.0) & (time < 5.5)
    assert float(np.ptp(result["signal1"].to_numpy()[burst])) < float(
        np.ptp(rippled_curve["signal1"].to_numpy()[burst])
    )


def test_anonymize_deripples_the_curves_when_asked(tmp_dirs, rippled_curve):
    curves, out = tmp_dirs
    rippled_curve.to_csv(curves / "rippled.csv", sep=";", index=False)
    (curves / "rippled.log").write_text(
        "sim_t_event_start=5.0\nfault_duration=0.5\nfrequency_sampling=50.0\n", encoding="utf-8"
    )

    anonymize(out, noisestd=0.0, frequency=10.0, curves_folder=curves, deripple=5.0)

    result = pd.read_csv(out / "rippled.csv", sep=";")
    assert _ripple_spans(result["time"].to_numpy(), result["signal1"].to_numpy()) == []


def test_anonymize_keeps_the_oscillation_when_asked_for_no_deripple(tmp_dirs, rippled_curve):
    curves, out = tmp_dirs
    rippled_curve.to_csv(curves / "rippled.csv", sep=";", index=False)
    (curves / "rippled.log").write_text(
        "sim_t_event_start=5.0\nfault_duration=0.5\nfrequency_sampling=50.0\n", encoding="utf-8"
    )

    anonymize(out, noisestd=0.0, frequency=10.0, curves_folder=curves, deripple=0, compression=0)

    result = pd.read_csv(out / "rippled.csv", sep=";")
    assert _ripple_spans(result["time"].to_numpy(), result["signal1"].to_numpy()) != []
