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
