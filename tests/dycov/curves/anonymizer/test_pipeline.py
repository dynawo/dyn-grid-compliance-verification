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

from pathlib import Path

import pandas as pd
import pytest
from tests.dycov.curves.anonymizer.conftest import (
    create_flat_csv_and_log,
    create_nonflat_csv_and_log,
)

from dycov.curves.anonymizer import anonymize, pipeline
from dycov.curves.anonymizer.pipeline import _anonymized_index


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


def test_curves_named_before_the_dtr_nodes_come_out_under_their_current_names(tmp_dirs):
    curves, out = tmp_dirs
    stem = "PCS_RTE-I16z1.SetPointStep.Active"
    previous = ("Wind_Turbine_GEN_VoltageInjTerminal", "Wind_Turbine_GEN_ActivePowerControlledPu")
    (curves / f"{stem}.csv").write_text(
        "time;" + ";".join(previous) + "\n" + "".join(f"{t / 10};1.0;0.5\n" for t in range(40)),
        encoding="utf-8",
    )
    (curves / f"{stem}.log").write_text(
        "sim_t_event_start=3.0\nfault_duration=0.0\nfrequency_sampling=15.0\n",
        encoding="utf-8",
    )

    anonymize(out, noisestd=0.0, frequency=10.0, curves_folder=curves)

    columns = (out / f"{stem}.csv").read_text().splitlines()[0].split(";")
    written = (out / f"{stem}.dict").read_text()
    for name in ("Wind_Turbine_GEN_VoltageNode2", "Wind_Turbine_GEN_ActivePowerControlledNode"):
        assert name in columns
        assert f"{name} = {name}" in written
    assert "InjTerminal" not in written
    assert "ControlledPu" not in written


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


def _snapshot(folder: Path) -> dict:
    return {
        path.relative_to(folder): path.read_bytes() for path in folder.rglob("*") if path.is_file()
    }


def _producer_tree(curves: Path) -> None:
    for producer in ("ProducerA", "ProducerB"):
        (curves / producer).mkdir()
        create_nonflat_csv_and_log(curves / producer, f"{producer}_curve")


def test_a_tree_of_one_folder_per_producer_comes_out_as_the_same_tree(tmp_dirs):
    """#864: only the output directory was created, and writing the first producer failed."""
    curves, out = tmp_dirs
    _producer_tree(curves)

    anonymize(out, noisestd=0.0, frequency=10.0, curves_folder=curves)

    for producer in ("ProducerA", "ProducerB"):
        assert (out / producer / f"{producer}_curve.csv").is_file()
        assert (out / producer / f"{producer}_curve.dict").is_file()
        assert (
            f"{producer}_curve = {producer}_curve.csv"
            in (out / producer / "CurvesFiles.ini").read_text()
        )
    assert sorted(path.name for path in out.iterdir()) == ["ProducerA", "ProducerB"]


@pytest.mark.parametrize("tree", [False, True])
def test_the_source_of_the_curves_is_left_as_it_was(tmp_dirs, tree):
    curves, out = tmp_dirs
    if tree:
        _producer_tree(curves)
    else:
        create_nonflat_csv_and_log(curves, "curve1")
        (curves / "curve1.dict").write_text(
            "[Curves-Metadata]\nsim_t_event_start = 1.0\nfault_duration = 2.0\n"
            "[Curves-Dictionary]\ntime = time\nsignal1 = signal1  # mine\n"
        )
    before = _snapshot(curves)

    anonymize(out, noisestd=0.01, frequency=10.0, curves_folder=curves)

    assert _snapshot(curves) == before


def test_the_index_of_a_flat_set_is_written_next_to_its_curves(tmp_dirs):
    curves, out = tmp_dirs
    create_nonflat_csv_and_log(curves, "curve1")

    anonymize(out, noisestd=0.0, frequency=10.0, curves_folder=curves)

    assert "curve1 = curve1.csv" in (out / "CurvesFiles.ini").read_text()
    assert not (curves / "CurvesFiles.ini").exists()


def test_the_index_names_the_csv_each_curve_file_became(tmp_path):
    """An entry whose file was not anonymized, as one in a subfolder or elsewhere on the disk,
    would lead the validation to the producer's own file, and the dictionaries of the index
    would carry the names of the producer's columns."""
    index = tmp_path / "CurvesFiles.ini"
    index.write_text(
        "[Curves-Files]\n"
        "# a comment = kept\n"
        "PCS.Bm.Exp = PCS.Bm.Exp.EXP\n"
        "PCS.Bm.Csv = Rise_noFRT.csv\n"
        "PCS.Bm.Sub = sub/PCS.Bm.Sub.csv\n"
        "PCS.Bm.Abs = /elsewhere/PCS.Bm.Abs.csv\n"
        "\n"
        "[Curves-Dictionary]\n"
        "# a comment\n"
        "InternalNode1_BUS_Voltage = Vpcc_of_the_producer\n"
    )
    out = tmp_path / "out"
    out.mkdir()
    for name in ("PCS.Bm.Exp.csv", "Rise_noFRT.csv"):
        (out / name).write_text("time;x\n")

    assert _anonymized_index(index, out) == (
        "[Curves-Files]\n"
        "# a comment = kept\n"
        "PCS.Bm.Exp = PCS.Bm.Exp.csv\n"
        "PCS.Bm.Csv = Rise_noFRT.csv\n"
        "\n"
        "[Curves-Dictionary]\n"
        "# a comment\n"
    )


def test_the_curves_are_prepared_outside_the_output(tmp_dirs, monkeypatch):
    """A run ended by a signal Python does not unwind leaves the copy it prepares the curves in:
    there, it would put the producer's own curves among the anonymized ones."""
    curves, out = tmp_dirs
    create_nonflat_csv_and_log(curves, "curve1")
    staged_in = []
    real_process_curves = pipeline._process_curves

    def spy(curves_folder, output_folder, *args):
        staged_in.append(curves_folder)
        real_process_curves(curves_folder, output_folder, *args)

    monkeypatch.setattr(pipeline, "_process_curves", spy)

    anonymize(out, noisestd=0.0, frequency=10.0, curves_folder=curves)

    assert out not in staged_in[0].parents
    assert sorted(path.name for path in out.parent.iterdir()) == ["curves", "out"]


def test_a_run_removes_the_copy_an_interrupted_run_into_the_same_output_left(tmp_dirs):
    curves, out = tmp_dirs
    create_nonflat_csv_and_log(curves, "curve1")
    left = out.parent / ".out.staging.abc123"
    left.mkdir()
    (left / "curve1.csv").write_text("time;signal1\n")
    other = out.parent / ".other.staging.abc123"
    other.mkdir()

    anonymize(out, noisestd=0.0, frequency=10.0, curves_folder=curves)

    assert not left.exists()
    assert other.exists()
