#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import os
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from dycov.dynawo.dynawo import _create_curves, run_base_dynawo


class DummyLogger:
    def __init__(self):
        self.messages = []

    def get_logger(self, name):
        return self

    def debug(self, msg):
        self.messages.append(("debug", msg))

    def info(self, msg):
        self.messages.append(("info", msg))

    def error(self, msg):
        self.messages.append(("error", msg))


@pytest.fixture(autouse=True)
def patch_dycov_logging(monkeypatch):
    dummy_logger = DummyLogger()
    monkeypatch.setattr("dycov.dynawo.dynawo.dycov_logging", dummy_logger)
    return dummy_logger


def create_minimal_model_xml(tmp_path, model_name, model_id="TestModel"):
    xml_content = f"""<root xmlns="http://www.dynawo.org/DynawoModel">
        <modelicaModel id="{model_id}"/>
    </root>"""
    model_path = tmp_path / model_name
    with open(model_path, "w") as f:
        f.write(xml_content)
    return model_path


def create_dummy_launcher(tmp_path, version="1.2.3"):
    launcher = tmp_path / "launcher_dwo"
    with open(launcher, "w") as f:
        f.write("#!/bin/sh\n")
        f.write(f'if [ "$1" = "version" ]; then echo "{version}"; exit 0; fi\n')
        f.write("touch $5\n")  # For jobs --generate-preassembled, create output file
        f.write("exit 0\n")
    os.chmod(launcher, 0o755)
    return launcher


def create_dummy_compile_script(tmp_path):
    script = tmp_path / "Vsx64.cmd"
    with open(script, "w") as f:
        f.write("@echo off\n")
        f.write("echo Compiling...\n")
        f.write("exit /b 0\n")
    os.chmod(script, 0o755)
    return script


def test_is_stable_raises_on_length_mismatch():
    # Import from correct location
    from dycov.validation.common import is_stable

    time = [0.0, 0.1, 0.2]
    curve = [1.0, 1.1]
    stable_time = 0.1
    with pytest.raises(ValueError) as excinfo:
        is_stable(time, curve, stable_time)
    assert "different length" in str(excinfo.value)


def test_run_base_dynawo_simulation_timeout(tmp_path, patch_dycov_logging):
    # Setup
    launcher = create_dummy_launcher(tmp_path)
    jobs_filename = "testjob"
    inputs_path = tmp_path / "inputs"
    output_path = Path("output")
    dynawo_output_dir = inputs_path / output_path
    (dynawo_output_dir / "logs").mkdir(parents=True)
    (dynawo_output_dir / "curves").mkdir(parents=True)
    # Write dummy log file (no error)
    with open(dynawo_output_dir / "logs/dynawo.log", "w") as f:
        f.write("INFO: Simulation started\n")
    # Variable translations
    variable_translations = {
        "BusPDR_BUS_Voltage": ["BusPDR_BUS_Voltage"],
        "BusPDR_BUS_ActivePower": ["BusPDR_BUS_ActivePower"],
        "BusPDR_BUS_ReactivePower": ["BusPDR_BUS_ReactivePower"],
        "time": ["time"],
    }

    class DummyGen:
        id = "G1"
        UseVoltageDrop = False

    generators = [DummyGen()]
    s_nom = 1.0
    s_nref = 1.0
    # Write dummy jobs file
    with open(inputs_path / (jobs_filename + ".jobs"), "w") as f:
        f.write("<jobs></jobs>")
    # Patch subprocess.Popen to simulate a process that never finishes
    orig_popen = subprocess.Popen

    class DummyProc:
        def __init__(self, *a, **kw):
            self._poll = None
            self.pid = 12345
            self.stderr = tempfile.TemporaryFile()
            self.stderr.write(b"timeout\n")
            self.stderr.seek(0)

        def poll(self):
            return None

        def terminate(self):
            self._poll = 1

        def wait(self, timeout=None):
            return 0

    subprocess.Popen = lambda *a, **kw: DummyProc()
    orig_run = subprocess.run
    subprocess.run = lambda *a, **kw: type("DummyRun", (), {"stdout": "1.2.3\n"})()
    try:
        success, log, has_error, curves_calculated, sim_time = run_base_dynawo(
            launcher,
            jobs_filename,
            variable_translations,
            inputs_path,
            output_path,
            generators,
            s_nom,
            s_nref,
            save_file=True,
            simulation_limit=0.01,
        )
    finally:
        subprocess.Popen = orig_popen
        subprocess.run = orig_run
    assert success is False
    assert "timeout" in (log or "").lower() or "terminated" in (log or "").lower()
    assert isinstance(curves_calculated, pd.DataFrame)
    assert sim_time >= 0


def test_create_curves_handles_missing_or_malformed_file(tmp_path):
    # Setup
    variable_translations = {
        "BusPDR_BUS_Voltage": ["BusPDR_BUS_Voltage"],
        "BusPDR_BUS_ActivePower": ["BusPDR_BUS_ActivePower"],
        "BusPDR_BUS_ReactivePower": ["BusPDR_BUS_ReactivePower"],
        "time": ["time"],
    }

    class DummyGen:
        id = "G1"
        UseVoltageDrop = False

    generators = [DummyGen()]
    snom = 1.0
    snref = 1.0
    # Case 1: Missing file
    missing_file = tmp_path / "missing.csv"
    with pytest.raises(FileNotFoundError):
        _create_curves(variable_translations, missing_file, generators, snom, snref)
    # Case 2: Malformed file
    malformed_file = tmp_path / "malformed.csv"
    with open(malformed_file, "w") as f:
        f.write("not,a,valid,csv\n1,2,3\n")
    with pytest.raises(Exception):
        _create_curves(variable_translations, malformed_file, generators, snom, snref)
