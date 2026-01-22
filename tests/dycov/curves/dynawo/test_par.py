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
from dycov.curves.dynawo.io.par import ParFile
from dycov.model.parameters import Gen_init


# Helper: Minimal stub for Producer and Parameters for ProducerCurves
class DummyProducer:
    def __init__(self):
        self.p_max_pu = 1.0
        self.q_max_pu = 0.5
        self.u_nom = 400.0


class DummyParameters:
    def get_producer(self):
        return DummyProducer()


class DummyProducerCurves(ProducerCurves):
    def __init__(self):
        super().__init__(DummyParameters())


# Helper: Write a minimal template file with placeholders
def write_template_file(path, filename, variables):
    content = "\n".join([f"{var} = {{{{{var}}}}}" for var in variables])
    with open(path / filename, "w") as f:
        f.write(content)


@pytest.fixture
def working_dir_with_template(tmp_path):
    variables = [
        "line_XPu",
        "line_RPu",
        "infiniteBus_U0Pu",
        "gen_P0Pu",
        "gen_Q0Pu",
        "gen_U0Pu",
        "gen_UPhase0",
        "event_start",
        "event_end",
        "event_pre_value",
        "event_step_value",
    ]
    write_template_file(tmp_path, "TSOModel.par", variables)
    return tmp_path


@pytest.fixture
def rte_gen():
    return Gen_init(id="G1", P0=0.8, Q0=0.2, U0=1.05, UPhase0=0.0)


@pytest.fixture
def event_params():
    return {
        "start_time": 10.0,
        "duration_time": 5.0,
        "pre_value": 0.9,
        "step_value": 1.1,
    }


def read_generated_file(path):
    with open(path, "r") as f:
        return f.read()


def test_complete_file_replaces_placeholders_successfully(
    working_dir_with_template, rte_gen, event_params
):
    par = ParFile(DummyProducerCurves(), "BM", "OC")
    par.complete_file(working_dir_with_template, 0.01, 0.02, rte_gen, 90, 1.0, event_params)
    output = read_generated_file(working_dir_with_template / "TSOModel.par")
    assert "line_XPu = 0.02" in output
    assert "line_RPu = 0.01" in output
    assert "infiniteBus_U0Pu = 1.05" in output
    assert "gen_P0Pu = 0.8" in output
    assert "gen_Q0Pu = 0.2" in output
    assert "gen_U0Pu = 1.05" in output
    assert "gen_UPhase0 = 0.0" in output
    assert "event_start = 10.0" in output
    assert "event_end = 15.0" in output
    assert "event_pre_value = 0.9" in output
    assert "event_step_value = 1.1" in output


def test_complete_file_populates_variables_dict_correctly(
    working_dir_with_template, rte_gen, event_params
):
    par = ParFile(DummyProducerCurves(), "BM", "OC")
    # Patch replace_placeholders.dump_file to capture variables_dict
    captured = {}
    import dycov.files.replace_placeholders as rp

    orig_dump = rp.dump_file

    def fake_dump_file(path, filename, variables_dict):
        captured.update(variables_dict)

    rp.dump_file = fake_dump_file
    try:
        par.complete_file(working_dir_with_template, 0.03, 0.04, rte_gen, 90, 1.0, event_params)
    finally:
        rp.dump_file = orig_dump
    assert captured["line_XPu"] == 0.04
    assert captured["line_RPu"] == 0.03
    assert captured["infiniteBus_U0Pu"] == rte_gen.U0
    assert captured["gen_P0Pu"] == rte_gen.P0
    assert captured["gen_Q0Pu"] == rte_gen.Q0
    assert captured["gen_U0Pu"] == rte_gen.U0
    assert captured["gen_UPhase0"] == rte_gen.UPhase0
    assert captured["event_start"] == event_params["start_time"]
    assert captured["event_end"] == event_params["start_time"] + event_params["duration_time"]
    assert captured["event_pre_value"] == event_params["pre_value"]
    assert captured["event_step_value"] == event_params["step_value"]


def test_complete_file_calls_complete_parameters(working_dir_with_template, rte_gen, event_params):
    class ParFileWithSpy(ParFile):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.called = False

        def complete_parameters(self, variables_dict, event_params_):
            self.called = True
            super().complete_parameters(variables_dict, event_params_)

    par = ParFileWithSpy(DummyProducerCurves(), "BM", "OC")
    par.complete_file(working_dir_with_template, 0.01, 0.02, rte_gen, 90, 1.0, event_params)
    assert par.called


def test_complete_file_tool_variables_not_overwritten(
    working_dir_with_template, rte_gen, event_params
):
    par = ParFile(DummyProducerCurves(), "BM", "OC")
    # Patch get_all_variables to return a dict with tool_variables pre-set to special values
    import dycov.files.replace_placeholders as rp

    orig_get_all_variables = rp.get_all_variables

    def fake_get_all_variables(path, template_file):
        d = orig_get_all_variables(path, template_file)
        d["line_XPu"] = "should_not_overwrite"
        d["gen_P0Pu"] = "should_not_overwrite"
        d["event_start"] = "should_not_overwrite"
        return d

    rp.get_all_variables = fake_get_all_variables
    try:
        par.complete_file(working_dir_with_template, 0.01, 0.02, rte_gen, 90, 1.0, event_params)
    finally:
        rp.get_all_variables = orig_get_all_variables
    output = read_generated_file(working_dir_with_template / "TSOModel.par")
    # The tool_variables should be set to the correct values, not the pre-set ones
    assert "line_XPu = 0.02" in output
    assert "gen_P0Pu = 0.8" in output
    assert "event_start = 10.0" in output
