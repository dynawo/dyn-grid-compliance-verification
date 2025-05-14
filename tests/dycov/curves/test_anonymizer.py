#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from dycov.curves.anonymizer import (
    _create_curves_files_ini_if_not_exists,
    _create_dict_file_if_not_exists,
    anonymize,
)


def create_minimal_csv_and_log(
    curves_dir, name="curve1", event_time=1.0, fault_duration=2.0, freq=50.0
):
    csv_path = curves_dir / f"{name}.csv"
    log_path = curves_dir / f"{name}.log"
    # Write CSV with time and one signal
    df = pd.DataFrame(
        {
            "time": np.linspace(0, 5, 6),
            "signal1": np.ones(6),
        }
    )
    df.to_csv(csv_path, sep=";", index=False)
    # Write log file with event metadata
    with open(log_path, "w") as f:
        f.write(f"sim_t_event_start={event_time}\n")
        f.write(f"fault_duration={fault_duration}\n")
        f.write(f"frequency_sampling={freq}\n")
    return csv_path, log_path


def test_anonymize_creates_anonymized_curves_with_noise():
    with tempfile.TemporaryDirectory() as tmpdir:
        curves_dir = Path(tmpdir) / "curves"
        output_dir = Path(tmpdir) / "output"
        curves_dir.mkdir()
        output_dir.mkdir()
        csv_path, log_path = create_minimal_csv_and_log(curves_dir)
        # Run anonymize
        anonymize(output_folder=output_dir, noisestd=0.1, frequency=10.0, curves_folder=curves_dir)
        # Check output .csv and .dict exist
        out_csv = output_dir / "curve1.csv"
        out_dict = output_dir / "curve1.dict"
        assert out_csv.exists()
        assert out_dict.exists()
        # Check noise was applied (signal1 not all ones)
        df = pd.read_csv(out_csv, sep=";")
        assert not np.allclose(df["signal1"].values, 1.0)
        # Check .dict contains correct metadata
        with open(out_dict) as f:
            dict_content = f.read()
        assert "sim_t_event_start" in dict_content
        assert "fault_duration" in dict_content
        assert "frequency_sampling" in dict_content


def test_create_curvesfiles_ini_and_dict_files_if_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        curves_dir = Path(tmpdir)
        csv_path, log_path = create_minimal_csv_and_log(curves_dir, name="curveA")
        # Remove CurvesFiles.ini and .dict if present
        ini_path = curves_dir / "CurvesFiles.ini"
        dict_path = curves_dir / "curveA.dict"
        if ini_path.exists():
            ini_path.unlink()
        if dict_path.exists():
            dict_path.unlink()
        # Prepare metadata for dict creation
        metadata = {
            "curveA": {
                "is_field_measurements": False,
                "sim_t_event_start": 1.0,
                "fault_duration": 2.0,
                "frequency_sampling": 50.0,
            }
        }
        _create_curves_files_ini_if_not_exists(curves_dir)
        _create_dict_file_if_not_exists(csv_path, metadata)
        # Check CurvesFiles.ini
        assert ini_path.exists()
        with open(ini_path) as f:
            ini_content = f.read()
        assert "curveA = curveA.csv" in ini_content
        # Check .dict file
        assert dict_path.exists()
        with open(dict_path) as f:
            dict_content = f.read()
        assert "is_field_measurements = False" in dict_content
        assert "sim_t_event_start = 1.0" in dict_content
        assert "fault_duration = 2.0" in dict_content
        assert "frequency_sampling = 50.0" in dict_content
        assert "signal1 = signal1" in dict_content


def test_no_noise_applied_when_noisestd_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        curves_dir = Path(tmpdir)
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()
        csv_path, log_path = create_minimal_csv_and_log(curves_dir, name="curveC")
        # Run anonymize with noisestd=None
        anonymize(
            output_folder=output_dir, noisestd=None, frequency=10.0, curves_folder=curves_dir
        )
        out_csv = output_dir / "curveC.csv"
        assert out_csv.exists()
        df = pd.read_csv(out_csv, sep=";")
        # Should be all ones (original data)
        assert np.allclose(df["signal1"].values, 1.0)


def test_handle_missing_curve_files_or_directories():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "output"
        # Directory does not exist, should be created
        anonymize(output_folder=output_dir, noisestd=None, frequency=10.0, curves_folder=None)
        assert output_dir.exists()
        # Now test missing curve files: nothing to process, should not raise
        # (No .csv or .log in output_dir)
        files = list(output_dir.glob("*"))
        assert (
            len(files) == 1 or len(files) == 0 or all(f.name == "CurvesFiles.ini" for f in files)
        )
