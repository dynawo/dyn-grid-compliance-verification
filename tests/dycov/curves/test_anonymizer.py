#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dycov.curves.anonymizer import (
    _create_curves_files_ini_if_not_exists,
    _create_dict_file_if_not_exists,
    _ensure_min_points,
    _get_event_period_indices,
    _interior_times,
    _is_nearly_flat,
    _rdp_mask_numpy,
    _save_curve,
    _simplify_curves,
    anonymize,
)

# ---------------------------
# Helpers
# ---------------------------


def create_flat_csv_and_log(curves_dir: Path, name="curve_flat"):
    t = np.linspace(0.0, 5.0, 6)
    df = pd.DataFrame({"time": t, "signal1": np.ones_like(t)})
    csv = curves_dir / f"{name}.csv"
    log = curves_dir / f"{name}.log"

    df.to_csv(csv, sep=";", index=False)
    log.write_text(
        "sim_t_event_start=1.0\nfault_duration=2.0\nfrequency_sampling=50.0\n",
        encoding="utf-8",
    )
    return csv


def create_nonflat_csv_and_log(curves_dir: Path, name="curve_nf"):
    t = np.linspace(0.0, 5.0, 256)
    signal = 1.0 + 0.05 * np.sin(2 * np.pi * t / 5.0)
    df = pd.DataFrame({"time": t, "signal1": signal})

    csv = curves_dir / f"{name}.csv"
    log = curves_dir / f"{name}.log"

    df.to_csv(csv, sep=";", index=False)
    log.write_text(
        "sim_t_event_start=1.0\nfault_duration=2.0\nfrequency_sampling=50.0\n",
        encoding="utf-8",
    )
    return csv


@pytest.fixture()
def tmp_dirs(tmp_path: Path):
    curves = tmp_path / "curves"
    out = tmp_path / "out"
    curves.mkdir()
    out.mkdir()
    return curves, out


# ---------------------------
# Core behaviour tests
# ---------------------------


def test_anonymize_creates_output_files(tmp_dirs):
    curves, out = tmp_dirs

    create_nonflat_csv_and_log(curves, "curve1")

    anonymize(out, noisestd=0.1, frequency=10.0, curves_folder=curves)

    assert (out / "curve1.csv").exists()
    assert (out / "curve1.dict").exists()


def test_minimum_points_enforced(tmp_dirs):
    curves, out = tmp_dirs

    create_flat_csv_and_log(curves, "short")

    anonymize(out, noisestd=0.0, frequency=10.0, curves_folder=curves)

    df = pd.read_csv(out / "short.csv", sep=";")

    assert len(df) >= 10, "Curves must have at least 10 points"


def test_noise_applied_on_nonflat_signal(tmp_dirs):
    curves, out = tmp_dirs

    src_csv = create_nonflat_csv_and_log(curves, "nf")
    src = pd.read_csv(src_csv, sep=";")["signal1"].values

    anonymize(out, noisestd=0.1, frequency=10.0, curves_folder=curves)

    out_sig = pd.read_csv(out / "nf.csv", sep=";")["signal1"].values

    assert not np.allclose(out_sig[: len(src)], src, atol=1e-6)


@pytest.mark.parametrize("noisestd", [None, 0.0])
def test_no_noise_when_disabled(tmp_dirs, noisestd):
    curves, out = tmp_dirs

    src_csv = create_flat_csv_and_log(curves, "flat")
    src_mean = pd.read_csv(src_csv, sep=";")["signal1"].mean()

    anonymize(out, noisestd=noisestd, frequency=10.0, curves_folder=curves)

    out_sig = pd.read_csv(out / "flat.csv", sep=";")["signal1"].values

    assert np.std(out_sig) < 1e-6
    assert abs(out_sig.mean() - src_mean) < 1e-6


def test_no_noise_on_almost_flat_signal(tmp_dirs):
    curves, out = tmp_dirs

    # Señal realmente "almost flat" según threshold=1e-4
    t = np.linspace(0.0, 5.0, 6)
    signal = 1.0 + 1e-5 * np.sin(2 * np.pi * t / 5.0)
    df = pd.DataFrame({"time": t, "signal1": signal})

    csv_path = curves / "almost_flat.csv"
    log_path = curves / "almost_flat.log"

    df.to_csv(csv_path, sep=";", index=False)
    log_path.write_text(
        "sim_t_event_start=1.0\nfault_duration=2.0\nfrequency_sampling=50.0\n",
        encoding="utf-8",
    )

    src_sig = df["signal1"].values

    anonymize(out, noisestd=0.2, frequency=10.0, curves_folder=curves)

    out_sig = pd.read_csv(out / "almost_flat.csv", sep=";")["signal1"].values

    assert np.std(out_sig) < 1e-6
    assert np.ptp(out_sig) < 1e-5
    assert abs(out_sig.mean() - src_sig.mean()) < 1e-6
    assert len(out_sig) >= 10


# ---------------------------
# File generation tests
# ---------------------------


def test_ini_and_dict_created(tmp_path):
    curves = tmp_path / "curves"
    curves.mkdir()

    csv = create_flat_csv_and_log(curves, "curveA")

    metadata = {
        "curveA": {
            "is_field_measurements": False,
            "sim_t_event_start": 1.0,
            "fault_duration": 2.0,
            "frequency_sampling": 50.0,
        }
    }

    _create_curves_files_ini_if_not_exists(curves)
    _create_dict_file_if_not_exists(csv, metadata)

    assert (curves / "CurvesFiles.ini").exists()
    assert (curves / "curveA.dict").exists()


def test_empty_folder_does_not_fail(tmp_path):
    curves = tmp_path / "empty"
    out = tmp_path / "out"

    curves.mkdir()
    out.mkdir()

    anonymize(out, noisestd=None, frequency=10.0, curves_folder=curves)

    assert out.exists()


# ---------------------------
# Minimum-points densification
# ---------------------------


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

    result = _ensure_min_points(df, min_points=10)

    assert result is df


def test_ensure_min_points_keeps_every_original_instant(bolted_fault_curve):
    result = _ensure_min_points(bolted_fault_curve, min_points=10)

    original_times = bolted_fault_curve["time"].to_numpy()
    assert len(result) == 10
    assert set(original_times).issubset(set(result["time"].to_numpy()))
    assert (result["time"].to_numpy() == 30.0).sum() == 2


def test_ensure_min_points_preserves_the_discontinuity(bolted_fault_curve):
    result = _ensure_min_points(bolted_fault_curve, min_points=10)

    at_event = result[result["time"] == 30.0]
    assert list(at_event["voltage"]) == [1.0, 0.02]
    assert list(at_event["power"]) == [0.83, 0.0]


def test_ensure_min_points_does_not_move_existing_samples(bolted_fault_curve):
    result = _ensure_min_points(bolted_fault_curve, min_points=10)

    kept = result[result["time"].isin(bolted_fault_curve["time"])]
    assert list(kept["voltage"]) == list(bolted_fault_curve["voltage"])
    assert list(kept["power"]) == list(bolted_fault_curve["power"])


def test_ensure_min_points_returns_a_sorted_grid(bolted_fault_curve):
    result = _ensure_min_points(bolted_fault_curve, min_points=10)

    times = result["time"].to_numpy()
    assert list(times) == sorted(times)
    assert list(result.columns) == list(bolted_fault_curve.columns)


def test_ensure_min_points_interpolates_the_inserted_samples():
    df = pd.DataFrame({"time": [0.0, 10.0], "signal1": [0.0, 10.0]})

    result = _ensure_min_points(df, min_points=6)

    assert list(result["time"]) == [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]
    assert list(result["signal1"]) == [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]


def test_ensure_min_points_favours_the_longest_intervals():
    df = pd.DataFrame({"time": [0.0, 1.0, 100.0], "signal1": [0.0, 1.0, 2.0]})

    result = _ensure_min_points(df, min_points=6)

    inserted = [t for t in result["time"] if t not in (0.0, 1.0, 100.0)]
    assert len(inserted) == 3
    assert all(t > 1.0 for t in inserted)


def test_ensure_min_points_leaves_a_single_instant_curve_alone():
    df = pd.DataFrame({"time": [7.0, 7.0, 7.0], "signal1": [1.0, 2.0, 3.0]})

    result = _ensure_min_points(df, min_points=10)

    assert result is df


def test_ensure_min_points_expands_a_one_sample_curve():
    df = pd.DataFrame({"time": [4.0], "signal1": [0.5]})

    result = _ensure_min_points(df, min_points=10)

    assert len(result) == 10
    assert result["time"].iloc[0] == 4.0
    assert list(result.columns) == ["time", "signal1"]
    assert np.allclose(result["signal1"], 0.5)


def test_ensure_min_points_accepts_an_empty_curve():
    df = pd.DataFrame({"time": [], "signal1": []})

    result = _ensure_min_points(df, min_points=10)

    assert result.empty


def test_ensure_min_points_keeps_the_tail_steady_under_downstream_resampling(bolted_fault_curve):
    result = _ensure_min_points(bolted_fault_curve, min_points=10)

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


# ---------------------------
# Curve simplification
# ---------------------------


@pytest.fixture()
def step_curve() -> pd.DataFrame:
    """Dense flat-step-flat signal, the shape a bolted fault compresses down to."""
    t = np.linspace(0.0, 100.0, 10001)
    return pd.DataFrame({"time": t, "voltage": np.where(t < 30.0, 1.0, 0.02)})


def test_simplify_curves_collapses_flat_regions(step_curve):
    result = _simplify_curves(step_curve, event_time=30.0, event_duration=0.0, compression=0.01)

    assert len(result) < 20
    assert result["time"].iloc[0] == pytest.approx(0.0)
    assert result["time"].iloc[-1] == pytest.approx(100.0)


def test_simplify_curves_keeps_the_step_edge(step_curve):
    result = _simplify_curves(step_curve, event_time=30.0, event_duration=0.0, compression=0.01)

    voltages = result["voltage"].to_numpy()
    assert voltages[0] == pytest.approx(1.0)
    assert voltages[-1] == pytest.approx(0.02)
    assert np.ptp(voltages) == pytest.approx(0.98)


def test_simplify_curves_preserves_the_time_ordering(step_curve):
    result = _simplify_curves(step_curve, event_time=30.0, event_duration=0.0, compression=0.01)

    times = result["time"].to_numpy()
    assert list(times) == sorted(times)


def test_simplify_curves_returns_short_segments_unchanged():
    df = pd.DataFrame({"time": [0.0, 1.0], "signal1": [0.0, 1.0]})

    result = _simplify_curves(df, event_time=5.0, event_duration=1.0, compression=0.01)

    assert list(result["time"]) == [0.0, 1.0]
    assert list(result["signal1"]) == [0.0, 1.0]


def test_simplify_curves_keeps_more_points_with_a_tighter_compression(step_curve):
    loose = _simplify_curves(step_curve, event_time=10.0, event_duration=80.0, compression=0.1)
    tight = _simplify_curves(step_curve, event_time=10.0, event_duration=80.0, compression=1e-4)

    assert len(tight) >= len(loose)


def test_simplify_curves_handles_a_constant_signal(step_curve):
    df = pd.DataFrame({"time": step_curve["time"], "voltage": np.ones(len(step_curve))})

    result = _simplify_curves(df, event_time=30.0, event_duration=10.0, compression=0.01)

    assert np.ptp(result["voltage"].to_numpy()) == 0.0
    assert len(result) < len(df)


# ---------------------------
# Simplification internals
# ---------------------------


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


@pytest.mark.parametrize(
    ("series", "expected"),
    [
        (np.ones(50), True),
        (np.linspace(0.0, 1e-6, 50), True),
        (np.linspace(0.0, 1.0, 50), False),
    ],
)
def test_is_nearly_flat(series, expected):
    assert bool(_is_nearly_flat(series, threshold=1e-4)) is expected


def test_get_event_period_indices_splits_the_window():
    df = pd.DataFrame({"time": np.arange(0.0, 10.0, 1.0)})

    before, during, after = _get_event_period_indices(df, 2.0, 5.0)

    assert (before, during, after) == (3, 3, 4)
    assert before + during + after == len(df)


def test_save_curve_writes_time_first_with_the_requested_precision(tmp_path):
    df = pd.DataFrame({"signal1": [1.5, 2.5], "time": [0.0, 0.25]})
    path = tmp_path / "curve.csv"

    _save_curve(df, path, precision=3)

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == "time;signal1"
    assert lines[1].startswith("0.000;")
    assert lines[2].startswith("0.250;")


def test_save_curve_does_not_modify_the_input(tmp_path):
    df = pd.DataFrame({"time": [0.0, 1.0], "signal1": [1.0, 2.0]})

    _save_curve(df, tmp_path / "curve.csv")

    assert df["time"].dtype == np.float64


# ---------------------------
# Compression through the CLI entry point
# ---------------------------


def test_anonymize_with_compression_enforces_the_minimum(tmp_dirs):
    curves, out = tmp_dirs

    create_flat_csv_and_log(curves, "compressed")

    anonymize(out, noisestd=0.0, frequency=10.0, curves_folder=curves, compression=0.01)

    df = pd.read_csv(out / "compressed.csv", sep=";")
    assert len(df) >= 10


def test_anonymize_with_compression_keeps_the_time_range(tmp_dirs):
    curves, out = tmp_dirs

    src_csv = create_nonflat_csv_and_log(curves, "ranged")
    src = pd.read_csv(src_csv, sep=";")

    anonymize(out, noisestd=None, frequency=10.0, curves_folder=curves, compression=0.05)

    df = pd.read_csv(out / "ranged.csv", sep=";")
    assert df["time"].iloc[0] == pytest.approx(src["time"].iloc[0])
    assert df["time"].iloc[-1] == pytest.approx(src["time"].iloc[-1])
    assert len(df) <= len(src)
