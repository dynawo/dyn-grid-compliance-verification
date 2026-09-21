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

from dycov.curves.anonymizer.reduce import (
    MAX_RATE,
    MAX_RATE_EVENT,
    _interior_times,
    _rdp_mask_numpy,
    cap_rate,
    ensure_min_points,
    simplify_curves,
)


@pytest.fixture()
def bolted_fault_curve() -> pd.DataFrame:
    """Heavily compressed bolted fault: the duplicated t=30 carries the voltage collapse."""
    return pd.DataFrame(
        {
            "time": [0.0, 0.0, 30.0, 30.0, 100.0],
            "voltage": [1.0, 1.0, 1.0, 0.02, 0.02],
            "power": [0.83, 0.83, 0.83, 0.0, 0.0],
        }
    )


def test_ensure_min_points_returns_long_curve_untouched():
    df = pd.DataFrame({"time": np.linspace(0.0, 1.0, 12), "signal1": np.arange(12.0)})

    result = ensure_min_points(df, min_points=10)

    assert result is df


def test_ensure_min_points_keeps_every_original_instant(bolted_fault_curve):
    result = ensure_min_points(bolted_fault_curve, min_points=10)

    original_times = bolted_fault_curve["time"].to_numpy()
    assert len(result) == 10
    assert set(original_times).issubset(set(result["time"].to_numpy()))
    assert (result["time"].to_numpy() == 30.0).sum() == 2


def test_ensure_min_points_preserves_the_discontinuity(bolted_fault_curve):
    result = ensure_min_points(bolted_fault_curve, min_points=10)

    at_event = result[result["time"] == 30.0]
    assert list(at_event["voltage"]) == [1.0, 0.02]
    assert list(at_event["power"]) == [0.83, 0.0]


def test_ensure_min_points_does_not_move_existing_samples(bolted_fault_curve):
    result = ensure_min_points(bolted_fault_curve, min_points=10)

    kept = result[result["time"].isin(bolted_fault_curve["time"])]
    assert list(kept["voltage"]) == list(bolted_fault_curve["voltage"])
    assert list(kept["power"]) == list(bolted_fault_curve["power"])


def test_ensure_min_points_returns_a_sorted_grid(bolted_fault_curve):
    result = ensure_min_points(bolted_fault_curve, min_points=10)

    times = result["time"].to_numpy()
    assert list(times) == sorted(times)
    assert list(result.columns) == list(bolted_fault_curve.columns)


def test_ensure_min_points_interpolates_the_inserted_samples():
    df = pd.DataFrame({"time": [0.0, 10.0], "signal1": [0.0, 10.0]})

    result = ensure_min_points(df, min_points=6)

    assert list(result["time"]) == [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]
    assert list(result["signal1"]) == [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]


def test_ensure_min_points_favours_the_longest_intervals():
    df = pd.DataFrame({"time": [0.0, 1.0, 100.0], "signal1": [0.0, 1.0, 2.0]})

    result = ensure_min_points(df, min_points=6)

    inserted = [t for t in result["time"] if t not in (0.0, 1.0, 100.0)]
    assert len(inserted) == 3
    assert all(t > 1.0 for t in inserted)


def test_ensure_min_points_leaves_a_single_instant_curve_alone():
    df = pd.DataFrame({"time": [7.0, 7.0, 7.0], "signal1": [1.0, 2.0, 3.0]})

    result = ensure_min_points(df, min_points=10)

    assert result is df


def test_ensure_min_points_expands_a_one_sample_curve():
    df = pd.DataFrame({"time": [4.0], "signal1": [0.5]})

    result = ensure_min_points(df, min_points=10)

    assert len(result) == 10
    assert result["time"].iloc[0] == 4.0
    assert list(result.columns) == ["time", "signal1"]
    assert np.allclose(result["signal1"], 0.5)


def test_ensure_min_points_accepts_an_empty_curve():
    df = pd.DataFrame({"time": [], "signal1": []})

    result = ensure_min_points(df, min_points=10)

    assert result.empty


def test_ensure_min_points_keeps_the_tail_steady_under_downstream_resampling(bolted_fault_curve):
    result = ensure_min_points(bolted_fault_curve, min_points=10)

    tail = result[result["time"] > 30.0]["voltage"].to_numpy()
    assert len(tail) >= 4
    assert np.ptp(tail) == 0.0


def test_interior_times_splits_only_positive_intervals():
    t_grid = np.array([0.0, 0.0, 30.0, 30.0, 100.0])

    inserted = _interior_times(t_grid, min_points=10)

    assert len(inserted) == 5
    assert all(0.0 < t < 100.0 and t not in (0.0, 30.0) for t in inserted)
    assert list(inserted) == sorted(inserted)


def test_interior_times_is_empty_without_any_positive_interval():
    t_grid = np.array([2.0, 2.0, 2.0])

    inserted = _interior_times(t_grid, min_points=10)

    assert inserted.size == 0


def test_interior_times_minimises_the_widest_resulting_interval():
    t_grid = np.array([0.0, 10.0, 40.0])

    inserted = _interior_times(t_grid, min_points=6)

    widest = np.max(np.diff(np.sort(np.concatenate((t_grid, inserted)))))
    assert len(inserted) == 3
    assert widest == pytest.approx(10.0)


@pytest.fixture()
def step_curve() -> pd.DataFrame:
    """Dense flat-step-flat signal, the shape a bolted fault compresses down to."""
    t = np.linspace(0.0, 100.0, 10001)
    return pd.DataFrame({"time": t, "voltage": np.where(t < 30.0, 1.0, 0.02)})


def test_simplify_curves_collapses_flat_regions(step_curve):
    result = simplify_curves(step_curve, event_time=30.0, event_duration=0.0, compression=0.01)

    assert len(result) < 20
    assert result["time"].iloc[0] == pytest.approx(0.0)
    assert result["time"].iloc[-1] == pytest.approx(100.0)


def test_simplify_curves_keeps_the_step_edge(step_curve):
    result = simplify_curves(step_curve, event_time=30.0, event_duration=0.0, compression=0.01)

    voltages = result["voltage"].to_numpy()
    assert voltages[0] == pytest.approx(1.0)
    assert voltages[-1] == pytest.approx(0.02)
    assert np.ptp(voltages) == pytest.approx(0.98)


def test_simplify_curves_preserves_the_time_ordering(step_curve):
    result = simplify_curves(step_curve, event_time=30.0, event_duration=0.0, compression=0.01)

    times = result["time"].to_numpy()
    assert list(times) == sorted(times)


def test_simplify_curves_returns_short_segments_unchanged():
    df = pd.DataFrame({"time": [0.0, 1.0], "signal1": [0.0, 1.0]})

    result = simplify_curves(df, event_time=5.0, event_duration=1.0, compression=0.01)

    assert list(result["time"]) == [0.0, 1.0]
    assert list(result["signal1"]) == [0.0, 1.0]


def test_simplify_curves_keeps_more_points_with_a_tighter_compression(step_curve):
    loose = simplify_curves(step_curve, event_time=10.0, event_duration=80.0, compression=0.1)
    tight = simplify_curves(step_curve, event_time=10.0, event_duration=80.0, compression=1e-4)

    assert len(tight) >= len(loose)


@pytest.fixture()
def multi_signal_curve() -> pd.DataFrame:
    """Several signals sharing one time grid, the shape of a generated curve set."""
    t = np.linspace(0.0, 100.0, 5001)
    return pd.DataFrame(
        {
            "time": t,
            "voltage": np.where(t < 30.0, 1.0, 0.02),
            "power": 0.8 + 0.01 * np.sin(2 * np.pi * t / 10.0),
            "current": np.where(t < 30.0, 0.8, 1.2),
        }
    )


def test_simplify_curves_reduces_a_curve_of_several_signals(multi_signal_curve):
    result = simplify_curves(
        multi_signal_curve, event_time=30.0, event_duration=0.0, compression=0.01
    )

    assert len(result) < len(multi_signal_curve) / 10


@pytest.fixture()
def ramp_curve() -> pd.DataFrame:
    """A straight line, which RDP reduces to its two ends whatever the epsilon."""
    t = np.linspace(0.0, 100.0, 5001)
    return pd.DataFrame({"time": t, "voltage": 0.01 * t})


def test_simplify_curves_keeps_the_event_above_its_floor(ramp_curve):
    result = simplify_curves(
        ramp_curve,
        event_time=30.0,
        event_duration=5.0,
        compression=0.01,
        min_event_points=20,
    )

    event = result[(result["time"] > 30.0) & (result["time"] <= 35.0)]
    assert len(event) >= 20


def test_simplify_curves_refills_the_event_with_original_samples(ramp_curve):
    result = simplify_curves(
        ramp_curve,
        event_time=30.0,
        event_duration=5.0,
        compression=0.01,
        min_event_points=20,
    )

    event = result[(result["time"] > 30.0) & (result["time"] <= 35.0)]
    assert set(event["time"]).issubset(set(ramp_curve["time"]))


def test_simplify_curves_handles_a_constant_signal(step_curve):
    df = pd.DataFrame({"time": step_curve["time"], "voltage": np.ones(len(step_curve))})

    result = simplify_curves(df, event_time=30.0, event_duration=10.0, compression=0.01)

    assert np.ptp(result["voltage"].to_numpy()) == 0.0
    assert len(result) < len(df)


def test_rdp_mask_keeps_endpoints_and_the_corner():
    points = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 5.0], [3.0, 5.0]])

    mask = _rdp_mask_numpy(points, epsilon=0.5)

    assert mask[0] and mask[-1]
    assert mask.sum() > 2


def test_rdp_mask_drops_collinear_points():
    points = np.column_stack([np.arange(10.0), np.arange(10.0)])

    mask = _rdp_mask_numpy(points, epsilon=0.1)

    assert list(np.where(mask)[0]) == [0, 9]


def test_rdp_mask_measures_distance_to_a_degenerate_segment():
    points = np.array([[0.0, 0.0], [0.0, 5.0], [0.0, 0.0]])

    mask = _rdp_mask_numpy(points, epsilon=1.0)

    assert mask.sum() == 3


@pytest.fixture()
def dense_curve() -> pd.DataFrame:
    """A minute sampled every 0.2 ms, denser than any instrument would record."""
    t = np.arange(0.0, 60.0, 0.0002)
    return pd.DataFrame({"time": t, "signal1": np.where(t < 30.0, 1.0, 0.5)})


def samples_per_second(times: np.ndarray, low: float, high: float) -> float:
    return len(times[(times >= low) & (times <= high)]) / (high - low)


def test_cap_rate_holds_the_rate_away_from_the_event(dense_curve):
    result = cap_rate(dense_curve, event_time=30.0, event_duration=0.0)

    assert samples_per_second(result["time"].to_numpy(), 5.0, 25.0) <= MAX_RATE + 1


def test_cap_rate_samples_the_event_finer(dense_curve):
    result = cap_rate(dense_curve, event_time=30.0, event_duration=0.0)

    rate = samples_per_second(result["time"].to_numpy(), 31.0, 39.0)
    assert MAX_RATE < rate <= MAX_RATE_EVENT + 1


def test_cap_rate_bounds_an_event_that_never_clears(dense_curve):
    result = cap_rate(dense_curve, event_time=30.0, event_duration=9999.0)

    assert samples_per_second(result["time"].to_numpy(), 51.0, 59.0) <= MAX_RATE + 1


def test_cap_rate_keeps_both_ends_of_a_step():
    t = np.arange(0.0, 20.0, 0.0002)
    curve = pd.DataFrame({"time": t, "signal1": np.where(t < 5.0, 1.0, 0.2)})

    result = cap_rate(curve, event_time=15.0, event_duration=0.0)

    times = result["time"].to_numpy()
    edge = int(np.argmax(result["signal1"].to_numpy() < 1.0))
    assert times[edge] - times[edge - 1] == pytest.approx(0.0002, abs=1e-9)
