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

from dycov.curves.anonymizer.save import save_curve
from dycov.sigpro.sigpro import resample_to_fixed_step


def test_save_curve_writes_time_first_with_the_requested_precision(tmp_path):
    df = pd.DataFrame({"signal1": [1.5, 2.5], "time": [0.0, 0.25]})
    path = tmp_path / "curve.csv"

    save_curve(df, path, precision=3)

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == "time;signal1"
    assert lines[1].startswith("0.000;")
    assert lines[2].startswith("0.250;")


def test_save_curve_writes_the_time_with_microsecond_precision(tmp_path):
    df = pd.DataFrame({"time": [0.0, 0.0005], "signal1": [1.0, 1.0]})
    path = tmp_path / "curve.csv"

    save_curve(df, path)

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert lines[1].startswith("0.000000;")
    assert lines[2].startswith("0.000500;")


def test_save_curve_does_not_modify_the_input(tmp_path):
    df = pd.DataFrame({"time": [0.0, 1.0], "signal1": [1.0, 2.0]})

    save_curve(df, tmp_path / "curve.csv")

    assert df["time"].dtype == np.float64


def test_save_curve_gives_a_step_two_instants(tmp_path):
    df = pd.DataFrame({"time": [0.0, 1.0, 1.0, 2.0], "signal1": [1.0, 1.0, 0.0, 0.0]})

    save_curve(df, tmp_path / "step.csv")

    saved = pd.read_csv(tmp_path / "step.csv", sep=";")
    assert list(saved["time"]) == [0.0, 1.0, 1.000001, 2.0]
    assert list(saved["signal1"]) == [1.0, 1.0, 0.0, 0.0]


def test_save_curve_separates_a_step_that_lands_on_the_next_sample(tmp_path):
    """Separating a pair can collide with the sample that follows it, one microsecond away."""
    df = pd.DataFrame(
        {
            "time": [19.999996, 19.999996, 19.999997, 19.999998],
            "signal1": [1.0, 0.5, 0.5, 0.5],
        }
    )

    save_curve(df, tmp_path / "chain.csv")

    saved = pd.read_csv(tmp_path / "chain.csv", sep=";")
    instants = saved["time"].to_numpy()
    assert len(set(instants)) == len(instants)
    assert list(instants) == sorted(instants)


def test_save_curve_separates_instants_that_the_precision_would_merge(tmp_path):
    df = pd.DataFrame({"time": [0.0, 1.0000001, 1.0000002], "signal1": [1.0, 1.0, 0.0]})

    save_curve(df, tmp_path / "rounded.csv")

    instants = pd.read_csv(tmp_path / "rounded.csv", sep=";")["time"].to_numpy()
    assert len(set(instants)) == 3


def test_save_curve_keeps_what_the_step_leaves_behind(tmp_path):
    """The resampling of the validation drops repeated instants, so a step written on one
    instant loses the value the curve holds after it."""
    time = [0.0, 30.0, 30.0, 100.0]
    df = pd.DataFrame({"time": time, "signal1": [1.0, 1.0, 0.0, 0.0]})

    save_curve(df, tmp_path / "trip.csv")

    saved = pd.read_csv(tmp_path / "trip.csv", sep=";")
    resampled = resample_to_fixed_step(saved, fs_max=1000)
    tail = resampled[resampled["time"] > 60.0]["signal1"].to_numpy()
    assert float(np.abs(tail).max()) == pytest.approx(0.0, abs=1e-9)
