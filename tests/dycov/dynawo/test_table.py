#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import pytest

from dycov.curves.curves import ProducerCurves
from dycov.dynawo.table import TableFile
from dycov.model.parameters import Gen_init


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
    # Create a dummy TableInfiniteBus.txt file
    file_path = tmp_path / "TableInfiniteBus.txt"
    file_path.write_text(
        "start_event={{ start_event }}\nend_event={{ end_event }}\nbus_u0pu={{ bus_u0pu }}\nbus_upu={{ bus_upu }}\nend_freq={{ end_freq }}\n"
    )
    return tmp_path


@pytest.fixture
def rte_gen():
    return Gen_init(id="G1", P0=0.1, Q0=0.2, U0=1.05, UPhase0=0.0)


@pytest.fixture
def event_params_base():
    return {
        "start_time": 10.0,
        "duration_time": 5.0,
        "connect_to": "AVRSetpointPu",
        "step_value": "0.02",
    }


def test_complete_file_replaces_placeholders_successfully(working_dir, rte_gen, event_params_base):
    table = TableFile(DummyProducerCurves(), "BM", "OC")
    table.complete_file(working_dir, rte_gen, event_params_base)
    output = (working_dir / "TableInfiniteBus.txt").read_text()
    assert "start_event=10.0" in output
    assert "end_event=15.0" in output
    assert f"bus_u0pu={rte_gen.U0}" in output
    assert f"bus_upu={rte_gen.U0 + float(event_params_base['step_value'])}" in output


def test_complete_file_sets_bus_upu_for_avr_setpoint(working_dir, rte_gen, event_params_base):
    params = event_params_base.copy()
    params["connect_to"] = "AVRSetpointPu"
    table = TableFile(DummyProducerCurves(), "BM", "OC")
    table.complete_file(working_dir, rte_gen, params)
    output = (working_dir / "TableInfiniteBus.txt").read_text()
    expected_value = rte_gen.U0 + float(params["step_value"])
    assert f"bus_upu={expected_value}" in output


def test_complete_file_sets_end_freq_for_network_frequency(
    working_dir, rte_gen, event_params_base
):
    params = event_params_base.copy()
    params["connect_to"] = "NetworkFrequencyPu"
    table = TableFile(DummyProducerCurves(), "BM", "OC")
    table.complete_file(working_dir, rte_gen, params)
    output = (working_dir / "TableInfiniteBus.txt").read_text()
    expected_value = 1.0 + float(params["step_value"])
    assert f"end_freq={expected_value}" in output


def test_complete_file_noop_when_file_missing(tmp_path, rte_gen, event_params_base):
    # Do not create TableInfiniteBus.txt
    table = TableFile(DummyProducerCurves(), "BM", "OC")
    # Should not raise or attempt to write
    table.complete_file(tmp_path, rte_gen, event_params_base)
    assert not (tmp_path / "TableInfiniteBus.txt").exists()


def test_complete_file_handles_invalid_step_value_type(working_dir, rte_gen, event_params_base):
    params = event_params_base.copy()
    params["step_value"] = "not_a_float"
    table = TableFile(DummyProducerCurves(), "BM", "OC")
    # Should raise ValueError when trying to convert step_value to float
    with pytest.raises(ValueError):
        table.complete_file(working_dir, rte_gen, params)
