#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import math
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

import dycov
from dycov.configuration.cfg import config
from dycov.curves.curves import ProducerCurves
from dycov.curves.dynawo.io import table
from dycov.curves.dynawo.io.table import TableFile
from dycov.model.parameters import GenInit

_INFINITE_BUS_TABLE = (
    Path(dycov.__file__).parent
    / "model_lib/TSO_model/GridVWDisturbance_1Line_InfBusFromTab/TableInfiniteBus.txt"
)


class DummyProducer:
    def __init__(self):
        self.u_nom = 1.0
        self.p_max_pu = 1.0
        self.q_max_pu = 1.0


class DummyParameters:
    def get_producer(self):
        return DummyProducer()


class DummyProducerCurves(ProducerCurves):
    def __init__(self):
        super().__init__(DummyParameters())

    def get_solver(self):
        return {}

    def get_generators_imax(self):
        return {}

    def obtain_reference_curve(self, *args, **kwargs):
        return 0.0, None

    def obtain_simulated_curve(self, *args, **kwargs):
        return "", {}, 0, None, None

    def get_time_cct(self, *args, **kwargs):
        return 0.0

    def get_disconnection_model(self):
        return None


@pytest.fixture
def working_dir(tmp_path):
    file_path = tmp_path / "TableInfiniteBus.txt"
    file_path.write_text(
        "start_event={{ start_event }}\n"
        "end_event={{ end_event }}\n"
        "bus_u0pu={{ bus_u0pu }}\n"
        "bus_upu={{ bus_upu }}\n"
        "end_freq={{ end_freq }}\n"
    )
    return tmp_path


@pytest.fixture
def tso_gen():
    return GenInit(id="G1", p0=0.1, q0=0.2, u0=1.05, u_phase0=0.0)


@pytest.fixture
def event_params_base():
    return {
        "start_time": 10.0,
        "duration_time": 5.0,
        "connect_to": "VoltageSetpointPu",
        "step_value": "0.02",
    }


def test_complete_file_replaces_placeholders_successfully(working_dir, tso_gen, event_params_base):
    table = TableFile(DummyProducerCurves(), "BM", "OC")
    table.complete_file(working_dir, tso_gen, event_params_base)
    output = (working_dir / "TableInfiniteBus.txt").read_text()
    assert "start_event=10.0" in output
    assert "end_event=15.0" in output
    assert f"bus_u0pu={tso_gen.u0}" in output
    assert f"bus_upu={tso_gen.u0 + float(event_params_base['step_value'])}" in output


def test_complete_file_sets_bus_upu_for_avr_setpoint(working_dir, tso_gen, event_params_base):
    params = event_params_base.copy()
    params["connect_to"] = "VoltageSetpointPu"
    table = TableFile(DummyProducerCurves(), "BM", "OC")
    table.complete_file(working_dir, tso_gen, params)
    output = (working_dir / "TableInfiniteBus.txt").read_text()
    expected_value = tso_gen.u0 + float(params["step_value"])
    assert f"bus_upu={expected_value}" in output


def test_complete_file_sets_end_freq_for_network_frequency(
    working_dir, tso_gen, event_params_base
):
    params = event_params_base.copy()
    params["connect_to"] = "NetworkFrequencyPu"
    table = TableFile(DummyProducerCurves(), "BM", "OC")
    table.complete_file(working_dir, tso_gen, params)
    output = (working_dir / "TableInfiniteBus.txt").read_text()
    expected_value = 1.0 + float(params["step_value"])
    assert f"end_freq={expected_value}" in output


def test_complete_file_noop_when_file_missing(tmp_path, tso_gen, event_params_base):
    # Do not create TableInfiniteBus.txt
    table = TableFile(DummyProducerCurves(), "BM", "OC")
    # Should not raise or attempt to write
    table.complete_file(tmp_path, tso_gen, event_params_base)
    assert not (tmp_path / "TableInfiniteBus.txt").exists()


def test_complete_file_handles_invalid_step_value_type(working_dir, tso_gen, event_params_base):
    params = event_params_base.copy()
    params["step_value"] = "not_a_float"
    table = TableFile(DummyProducerCurves(), "BM", "OC")
    # Should raise ValueError when trying to convert step_value to float
    with pytest.raises(ValueError):
        table.complete_file(working_dir, tso_gen, params)


class _NumericCurves(DummyProducerCurves):
    def obtain_value(self, value_definition, origin=None):
        return float(value_definition)


@pytest.fixture
def grid_events(tmp_path):
    def write(**event):
        pcs = tmp_path / "PCSDescription.ini"
        pcs.write_text("[BM.OC.Event]\n" + "".join(f"{k} = {v}\n" for k, v in event.items()))
        config.load_pcs_config(pcs)
        table = tmp_path / "TableInfiniteBus.txt"
        table.write_text(
            "bus_upu={{ bus_upu }}\n"
            "bus_uphase={{ bus_uphase }}\n"
            "bus_omega0pu={{ bus_omega0pu }}\n"
            "bus_omegapu={{ bus_omegapu }}\n"
            "end_frequency_settling={{ end_frequency_settling }}\n"
        )
        return tmp_path

    yield write
    config.load_pcs_config(None)


def _completed(working_dir, tso_gen, duration=0.0):
    params = {"start_time": 20.0, "duration_time": duration, "connect_to": "", "step_value": 0}
    TableFile(_NumericCurves(), "BM", "OC").complete_file(working_dir, tso_gen, params)
    return dict(
        line.split("=") for line in (working_dir / "TableInfiniteBus.txt").read_text().split()
    )


def test_a_grid_without_events_holds_its_voltage_phase_and_frequency(grid_events, tso_gen):
    table = _completed(grid_events(), tso_gen)

    assert float(table["bus_upu"]) == pytest.approx(tso_gen.u0)
    assert float(table["bus_uphase"]) == 0.0
    assert float(table["bus_omega0pu"]) == pytest.approx(1.0)
    assert float(table["bus_omegapu"]) == pytest.approx(1.0)


def test_the_steps_of_the_grid_voltage_and_of_its_phase(grid_events, tso_gen):
    table = _completed(grid_events(grid_voltage_step=-0.05, grid_phase_jump=0.12), tso_gen)

    assert float(table["bus_upu"]) == pytest.approx(tso_gen.u0 - 0.05)
    assert float(table["bus_uphase"]) == pytest.approx(0.12)


def test_a_frequency_profile_starts_once_the_grid_has_settled_at_its_initial_frequency(
    grid_events, tso_gen
):
    table = _completed(grid_events(grid_frequency0=49.5, grid_rocof=0.5), tso_gen, duration=3.0)

    assert float(table["bus_omega0pu"]) == pytest.approx(49.5 / 50.0)
    assert float(table["bus_omegapu"]) == pytest.approx(51.0 / 50.0)
    assert float(table["end_frequency_settling"]) == pytest.approx(10.0)


class _Unit(DummyProducer):
    def __init__(self, lib):
        super().__init__()
        self.generators = [SimpleNamespace(lib=lib)]


class _UnitCurves(_NumericCurves):
    def __init__(self, lib):
        super().__init__()
        self._unit = _Unit(lib)

    def get_producer(self):
        return self._unit


def _infinite_bus_tables(tmp_path, tso_gen, lib, **event):
    shutil.copy(_INFINITE_BUS_TABLE, tmp_path)
    pcs = tmp_path / "PCSDescription.ini"
    pcs.write_text("[BM.OC.Event]\n" + "".join(f"{k} = {v}\n" for k, v in event.items()))
    config.load_pcs_config(pcs)
    params = {"start_time": 20.0, "duration_time": 3.0, "connect_to": "", "step_value": 0}
    try:
        TableFile(_UnitCurves(lib), "BM", "OC").complete_file(tmp_path, tso_gen, params)
    finally:
        config.load_pcs_config(None)
    return table._read_two_column_tables((tmp_path / "TableInfiniteBus.txt").read_text())


def test_a_unit_without_frequency_reference_sees_the_frequency_turn_the_grid_phase(
    tmp_path, tso_gen
):
    tables = _infinite_bus_tables(
        tmp_path, tso_gen, "GridFormingEpri", grid_frequency0=49.5, grid_rocof=0.5
    )

    omega_nom = 2 * math.pi * 50.0
    phase = dict(tables["TableUPhase"])
    stop = tables["TableUPhase"][-1][0]
    # 50 Hz -> 49.5 Hz over the first 10 s, held until the event at 20 s, then 0.5 Hz/s for 3 s
    assert phase[10.0] == pytest.approx(omega_nom * -0.05, abs=1e-6)
    assert phase[20.0] == pytest.approx(omega_nom * -0.15, abs=1e-6)
    assert phase[23.0] == pytest.approx(omega_nom * -0.135, abs=1e-6)
    assert phase[stop] == pytest.approx(omega_nom * (-0.135 + 0.02 * (stop - 23.0)), abs=1e-6)
    assert tables["TableOmegaRefPu"][-1][1] == pytest.approx(1.02)


def test_a_unit_that_takes_the_frequency_reference_keeps_the_grid_phase(tmp_path, tso_gen):
    tables = _infinite_bus_tables(
        tmp_path,
        tso_gen,
        "GridFormingConverterDroopControl",
        grid_frequency0=49.5,
        grid_rocof=0.5,
    )

    assert all(value == 0.0 for _, value in tables["TableUPhase"])
    assert len(tables["TableUPhase"]) == 4


def test_a_phase_jump_stays_a_step_on_top_of_the_turning_phase(tmp_path, tso_gen):
    tables = _infinite_bus_tables(
        tmp_path, tso_gen, "GridFormingEpri", grid_frequency0=50.5, grid_phase_jump=0.2
    )

    # The table smooths the step over 10 ms on each side of the event
    phase = dict(tables["TableUPhase"])
    assert phase[20.01] - phase[19.99] == pytest.approx(0.2, abs=1e-6)
    assert phase[19.99] == pytest.approx(2 * math.pi * 50.0 * 0.01 * 15.0, abs=1e-6)
