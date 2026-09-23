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

import pandas as pd
import pytest
from tests.dycov.curves.anonymizer.conftest import (
    create_flat_csv_and_log,
    create_nonflat_csv_and_log,
)

from dycov.curves.anonymizer import anonymize


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


def test_empty_folder_does_not_fail(tmp_path):
    curves = tmp_path / "empty"
    out = tmp_path / "out"

    curves.mkdir()
    out.mkdir()

    anonymize(out, noisestd=None, frequency=10.0, curves_folder=curves)

    assert out.exists()


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


def test_noise_costs_no_samples(tmp_dirs):
    curves, out = tmp_dirs
    create_nonflat_csv_and_log(curves, "nf")
    quiet = out.parent / "quiet"

    anonymize(out, noisestd=0.01, frequency=10.0, curves_folder=curves, compression=0.0001)
    anonymize(quiet, noisestd=0.0, frequency=10.0, curves_folder=curves, compression=0.0001)

    noisy_curve = pd.read_csv(out / "nf.csv", sep=";")
    quiet_curve = pd.read_csv(quiet / "nf.csv", sep=";")
    assert len(noisy_curve) == len(quiet_curve)


def test_zero_compression_keeps_every_sample(tmp_dirs):
    """Each stage is asked off with a zero, now that none of them defaults to off."""
    curves, out = tmp_dirs
    source = create_nonflat_csv_and_log(curves, "nf")
    original = pd.read_csv(source, sep=";")

    anonymize(out, noisestd=0.0, frequency=10.0, curves_folder=curves, compression=0)

    assert len(pd.read_csv(out / "nf.csv", sep=";")) == len(original)


def test_a_curve_the_set_does_not_carry_stays_declared_and_empty(tmp_dirs):
    curves, out = tmp_dirs
    stem = "PCS_RTE-I16z1.GridVoltageStep.Drop"
    (curves / f"{stem}.csv").write_text(
        "time;InternalNode1_BUS_Voltage\n" + "".join(f"{t / 10};1.0\n" for t in range(40)),
        encoding="utf-8",
    )
    (curves / f"{stem}.log").write_text(
        "sim_t_event_start=30.0\nfault_duration=0.0\nfrequency_sampling=15.0\n",
        encoding="utf-8",
    )

    anonymize(out, noisestd=0.0, frequency=10.0, curves_folder=curves)

    written = (out / f"{stem}.dict").read_text()
    # An empty right side names no column, and rewriting it as a pattern would match at every
    # word boundary and scatter the curve name through the file.
    assert "InternalNode1_BUS_Voltage = InternalNode1_BUS_Voltage" in written
    assert "PV_Array" not in written
    for line in written.splitlines():
        if line.startswith("_GEN_") or line.count("=") > 1:
            raise AssertionError(f"dictionary line damaged: {line}")
