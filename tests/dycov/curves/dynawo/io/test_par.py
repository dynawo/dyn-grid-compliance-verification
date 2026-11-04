#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import shutil
from pathlib import Path

import pytest
from lxml import etree

import dycov
from dycov.configuration.cfg import Config
from dycov.core.global_variables import ELECTRIC_PERFORMANCE_PPM
from dycov.curves.curves import ProducerCurves
from dycov.curves.dynawo.io.par import ParFile
from dycov.model.parameters import GenInit

_FAULT_4_LINES = Path(dycov.__file__).parent / "model_lib" / "TSO_model" / "Fault_4Lines_InfBus"


# Helper: Minimal stub for Producer and Parameters for ProducerCurves
class DummyProducer:
    def __init__(self):
        self.p_max_pu = 1.0
        self.p_max_injection_pu = 0.75
        self.q_max_pu = 0.5
        self.u_nom = 400.0

    def get_sim_type(self):
        return ELECTRIC_PERFORMANCE_PPM

    def get_category(self):
        return "D"


class DummyParameters:
    def __init__(self):
        self.producer = DummyProducer()
        self.u_nom = self.producer.u_nom
        self.p_max_injection_pu = self.producer.p_max_injection_pu

    def get_sim_type(self):
        return self.producer.get_sim_type()

    def get_category(self):
        return self.producer.get_category()

    def get_producer(self):
        return self.producer


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
        "line_XFaultPu",
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
def tso_gen():
    return GenInit(id="G1", p0=0.8, q0=0.2, u0=1.05, u_phase0=0.0)


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
    working_dir_with_template, tso_gen, event_params
):
    par = ParFile(DummyProducerCurves(), "BM", "OC")
    par.complete_file(
        working_dir_with_template, 0.01, 0.02, 0.0, tso_gen, event_params, 225.0, 100.0
    )
    output = read_generated_file(working_dir_with_template / "TSOModel.par")
    assert "line_XPu = 0.02" in output
    assert "line_RPu = 0.01" in output
    assert "line_XFaultPu = 0.0" in output
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
    working_dir_with_template, tso_gen, event_params
):
    par = ParFile(DummyProducerCurves(), "BM", "OC")
    # Patch the dump_file implementation used by ParFile.complete_file to capture variables_dict
    captured = {}
    import dycov.curves.dynawo.io.par as par_module
    import dycov.files.replace_placeholders as rp

    orig_dump_par = getattr(par_module, "dump_file", None)
    orig_dump_rp = rp.dump_file

    def fake_dump_file(path, filename, variables_dict):
        captured.update(variables_dict)

    if orig_dump_par is not None:
        par_module.dump_file = fake_dump_file
    rp.dump_file = fake_dump_file
    try:
        par.complete_file(
            working_dir_with_template, 0.03, 0.04, 0.05, tso_gen, event_params, 225.0, 100.0
        )
    finally:
        if orig_dump_par is not None:
            par_module.dump_file = orig_dump_par
        rp.dump_file = orig_dump_rp
    assert captured["line_XPu"] == 0.04
    assert captured["line_RPu"] == 0.03
    assert captured["line_XFaultPu"] == 0.05
    assert captured["infiniteBus_U0Pu"] == tso_gen.u0
    assert captured["gen_P0Pu"] == tso_gen.p0
    assert captured["gen_Q0Pu"] == tso_gen.q0
    assert captured["gen_U0Pu"] == tso_gen.u0
    assert captured["gen_UPhase0"] == tso_gen.u_phase0
    assert captured["event_start"] == event_params["start_time"]
    assert captured["event_end"] == event_params["start_time"] + event_params["duration_time"]
    assert captured["event_pre_value"] == event_params["pre_value"]
    assert captured["event_step_value"] == event_params["step_value"]


@pytest.mark.parametrize("pmax", [40.0, -40.0])
def test_complete_file_rates_the_condenser_at_the_magnitude_of_pmax(
    tmp_path, tso_gen, event_params, pmax
):
    write_template_file(tmp_path, "TSOModel.par", ["inertialGrid_SNom"])
    par = ParFile(DummyProducerCurves(), "BM", "OC")

    par.complete_file(tmp_path, 0.01, 0.02, 0.0, tso_gen, event_params, 225.0, pmax)

    assert "inertialGrid_SNom = 40.0" in read_generated_file(tmp_path / "TSOModel.par")


def test_complete_file_calls_complete_parameters(working_dir_with_template, tso_gen, event_params):
    par = ParFile(DummyProducerCurves(), "BM", "OC")
    called = {"flag": False}
    original_complete_parameters = par.complete_parameters

    def spy_complete_parameters(variables_dict, event_params_):
        called["flag"] = True
        return original_complete_parameters(variables_dict, event_params_)

    par.complete_parameters = spy_complete_parameters
    par.complete_file(
        working_dir_with_template, 0.01, 0.02, 0.0, tso_gen, event_params, 225.0, 100.0
    )
    assert called["flag"]


def test_complete_file_tool_variables_not_overwritten(
    working_dir_with_template, tso_gen, event_params
):
    par = ParFile(DummyProducerCurves(), "BM", "OC")
    # Patch get_all_variables to return a dict with tool_variables pre-set to special values
    import dycov.curves.dynawo.io.par as par_module
    import dycov.files.replace_placeholders as rp

    orig_get_all_variables_par = getattr(par_module, "get_all_variables", None)
    orig_get_all_variables_rp = rp.get_all_variables

    def fake_get_all_variables(path, template_file):
        d = orig_get_all_variables_rp(path, template_file)
        d["line_XPu"] = "should_not_overwrite"
        d["line_XFaultPu"] = "should_not_overwrite"
        d["gen_P0Pu"] = "should_not_overwrite"
        d["event_start"] = "should_not_overwrite"
        return d

    if orig_get_all_variables_par is not None:
        par_module.get_all_variables = fake_get_all_variables
    rp.get_all_variables = fake_get_all_variables
    try:
        par.complete_file(
            working_dir_with_template, 0.01, 0.02, 0.0, tso_gen, event_params, 225.0, 100.0
        )
    finally:
        if orig_get_all_variables_par is not None:
            par_module.get_all_variables = orig_get_all_variables_par
        rp.get_all_variables = orig_get_all_variables_rp
    output = read_generated_file(working_dir_with_template / "TSOModel.par")
    # The tool_variables should be set to the correct values, not the pre-set ones
    assert "line_XPu = 0.02" in output
    assert "line_XFaultPu = 0.0" in output
    assert "gen_P0Pu = 0.8" in output
    assert "event_start = 10.0" in output


@pytest.mark.parametrize("fault_xpu", [0.0, 0.315])
def test_the_fault_of_the_four_lines_takes_the_reactance_of_the_test(
    tmp_path, tso_gen, event_params, fault_xpu
):
    """The bolted fault keeps a null reactance, and the impedant one gets its own."""
    shutil.copy(_FAULT_4_LINES / "TSOModel.par", tmp_path)
    par = ParFile(DummyProducerCurves(), "BM", "OC")

    par.complete_file(tmp_path, 0.0, 0.9, fault_xpu, tso_gen, event_params, 225.0, 100.0)

    assert _fault_reactance(tmp_path) == fault_xpu


def test_the_definition_of_the_reactance_does_not_replace_its_value(
    monkeypatch, tmp_path, tso_gen, event_params
):
    """The description names XFaultPu, and the PAR file gets the reactance it stands for."""
    values = {("BM.OC.Model", "line_XFaultPu"): "XFaultPu"}
    monkeypatch.setattr(Config, "has_option", lambda self, section, key: (section, key) in values)
    monkeypatch.setattr(
        Config, "get_value", lambda self, section, key, default=None: values[(section, key)]
    )
    shutil.copy(_FAULT_4_LINES / "TSOModel.par", tmp_path)
    par = ParFile(DummyProducerCurves(), "BM", "OC")

    par.complete_file(tmp_path, 0.0, 0.9, 0.315, tso_gen, event_params, 225.0, 100.0)

    assert _fault_reactance(tmp_path) == 0.315


def _fault_reactance(working_dir):
    root = etree.parse(working_dir / "TSOModel.par").getroot()
    namespace = {"dyn": etree.QName(root).namespace}
    fault = root.find("dyn:set[@id='LineFault']/dyn:par[@name='line_XFaultPu']", namespace)
    return float(fault.get("value"))
