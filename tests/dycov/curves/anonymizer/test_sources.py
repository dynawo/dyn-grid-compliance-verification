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

import logging

from tests.dycov.curves.anonymizer.conftest import create_flat_csv_and_log

from dycov.curves.anonymizer.sources import (
    _create_dict_file_if_not_exists,
    create_curves_files_ini,
    extract_metadata_from_logs,
)


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

    create_curves_files_ini(curves)
    _create_dict_file_if_not_exists(csv, metadata)

    assert (curves / "CurvesFiles.ini").exists()
    assert (curves / "curveA.dict").exists()


def test_metadata_comes_from_the_simulation_record(tmp_path):
    curves = tmp_path / "curves"
    curves.mkdir()

    create_flat_csv_and_log(curves, "curveA")
    metadata = extract_metadata_from_logs(curves)

    assert metadata["curveA"]["sim_t_event_start"] == 1.0
    assert metadata["curveA"]["fault_duration"] == 2.0
    assert metadata["curveA"]["frequency_sampling"] == 50.0


def test_dict_created_without_a_simulation_record_warns(tmp_path, caplog):
    curves = tmp_path / "curves"
    curves.mkdir()
    csv = curves / "curveA.csv"
    csv.write_text("time;signal1\n0.0;1.0\n", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        _create_dict_file_if_not_exists(csv, {})

    assert "No simulation record found" in caplog.text
    assert "sim_t_event_start = 0.0" in (curves / "curveA.dict").read_text()


def test_metadata_without_a_simulation_record_is_empty(tmp_path):
    curves = tmp_path / "curves"
    curves.mkdir()
    (curves / "curveA.csv").write_text("time;signal1\n0.0;1.0\n", encoding="utf-8")

    metadata = extract_metadata_from_logs(curves)

    assert metadata == {}
