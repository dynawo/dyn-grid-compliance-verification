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
    _create_dict_file,
    create_curves_files_ini,
    extract_metadata_from_logs,
)

ZONE1_COLUMNS = (
    "time;InternalNode1_BUS_Voltage;PV_Array_GEN_VoltageInjTerminal;"
    "PV_Array_GEN_ActivePowerControlledPu;PV_Array_GEN_ReactivePowerControlledPu;"
    "PV_Array_GEN_ActiveCurrentInjTerminal;PV_Array_GEN_ReactiveCurrentInjTerminal\n"
)


def _make_zone1_curves(folder, columns=ZONE1_COLUMNS):
    """A Zone 1 curve file, named as its PCS names it so the zone can be read off the name."""
    csv = folder / "PCS_RTE-I16z1.GridVoltageStep.Drop.csv"
    csv.write_text(columns + "0.0;1.0;1.0;0.5;0.1;0.5;0.1\n", encoding="utf-8")
    return csv


def _curves_section(dict_file):
    section = dict_file.read_text().split("[Curves-Dictionary]")[-1]
    return [
        line for line in section.splitlines() if line.strip() and not line.strip().startswith("#")
    ]


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
    _create_dict_file(csv, metadata)

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
        _create_dict_file(csv, {})

    assert "No simulation record found" in caplog.text
    assert "sim_t_event_start = 0.0" in (curves / "curveA.dict").read_text()


def test_metadata_without_a_simulation_record_is_empty(tmp_path):
    curves = tmp_path / "curves"
    curves.mkdir()
    (curves / "curveA.csv").write_text("time;signal1\n0.0;1.0\n", encoding="utf-8")

    metadata = extract_metadata_from_logs(curves)

    assert metadata == {}


def test_the_dictionary_asks_for_every_curve_the_zone_compares(tmp_path):
    curves = tmp_path / "curves"
    curves.mkdir()
    csv = _make_zone1_curves(curves)

    _create_dict_file(csv, {})

    assert _curves_section(csv.with_suffix(".dict")) == [
        "time = time",
        "NetworkFrequencyPu = ",
        "InternalNode1_BUS_Voltage = InternalNode1_BUS_Voltage",
        "PV_Array_GEN_VoltageInjTerminal = PV_Array_GEN_VoltageInjTerminal",
        "PV_Array_GEN_ActivePowerControlledPu = PV_Array_GEN_ActivePowerControlledPu",
        "PV_Array_GEN_ReactivePowerControlledPu = PV_Array_GEN_ReactivePowerControlledPu",
        "PV_Array_GEN_ActiveCurrentInjTerminal = PV_Array_GEN_ActiveCurrentInjTerminal",
        "PV_Array_GEN_ReactiveCurrentInjTerminal = PV_Array_GEN_ReactiveCurrentInjTerminal",
    ]


def test_an_existing_dictionary_is_repointed_at_the_file_just_written(tmp_path):
    curves = tmp_path / "curves"
    curves.mkdir()
    csv = _make_zone1_curves(curves)
    # The dictionary of a run whose generating unit went by another name.
    csv.with_suffix(".dict").write_text(
        "[Curves-Metadata]\nsim_t_event_start = 30.0\n\n"
        "[Curves-Dictionary]\n"
        "PV_Array_GEN_VoltageInjTerminal = Wind_Turbine_GEN_VoltageInjTerminal\n",
        encoding="utf-8",
    )

    _create_dict_file(csv, {})

    assert "PV_Array_GEN_VoltageInjTerminal = PV_Array_GEN_VoltageInjTerminal" in _curves_section(
        csv.with_suffix(".dict")
    )
    assert "Wind_Turbine" not in csv.with_suffix(".dict").read_text()


def test_an_existing_dictionary_keeps_the_metadata_it_states(tmp_path):
    curves = tmp_path / "curves"
    curves.mkdir()
    csv = _make_zone1_curves(curves)
    csv.with_suffix(".dict").write_text(
        "[Curves-Metadata]\nsim_t_event_start = 30.0\nis_field_measurements = True\n",
        encoding="utf-8",
    )

    _create_dict_file(csv, {})

    written = csv.with_suffix(".dict").read_text()
    assert "sim_t_event_start = 30.0" in written
    assert "is_field_measurements = True" in written


def test_a_curve_the_file_does_not_carry_is_left_empty_and_warned(tmp_path, caplog):
    curves = tmp_path / "curves"
    curves.mkdir()
    columns = ZONE1_COLUMNS.replace(";PV_Array_GEN_ActivePowerControlledPu", "")
    csv = curves / "PCS_RTE-I16z1.GridVoltageStep.Drop.csv"
    csv.write_text(columns + "0.0;1.0;1.0;0.1;0.5;0.1\n", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        _create_dict_file(csv, {})

    assert "PV_Array_GEN_ActivePowerControlledPu = " in _curves_section(csv.with_suffix(".dict"))
    assert "PV_Array_GEN_ActivePowerControlledPu" in caplog.text
    assert "does not carry" in caplog.text
