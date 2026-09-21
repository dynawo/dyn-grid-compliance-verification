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
from tests.dycov.curves.anonymizer.conftest import (
    create_flat_csv_and_log,
    create_nonflat_csv_and_log,
)

from dycov.curves.anonymizer import anonymize
from dycov.curves.anonymizer.noise import _is_nearly_flat, apply_noise_to_curves


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


@pytest.fixture()
def long_curve() -> pd.DataFrame:
    """A hundred seconds of a moving signal, with its event at t = 20 s."""
    t = np.arange(0.0, 100.0, 0.01)
    return pd.DataFrame({"time": t, "signal1": np.where(t < 20.0, 1.0, 0.5) + 0.01 * np.sin(t)})


def test_noise_reaches_the_event(long_curve):
    noisy = long_curve.copy()

    apply_noise_to_curves(noisy, 0.1, 10.0, event_time=20.0, event_duration=0.5)

    during = (long_curve["time"] >= 20.0) & (long_curve["time"] <= 20.5)
    difference = np.abs(noisy["signal1"].to_numpy() - long_curve["signal1"].to_numpy())
    assert difference[during].max() > 0.0


def test_no_noise_away_from_the_event(long_curve):
    noisy = long_curve.copy()

    apply_noise_to_curves(noisy, 0.1, 10.0, event_time=20.0, event_duration=0.5)

    away = (long_curve["time"] < 18.0) | (long_curve["time"] > 35.0)
    difference = np.abs(noisy["signal1"].to_numpy() - long_curve["signal1"].to_numpy())
    assert difference[away].max() == 0.0


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
