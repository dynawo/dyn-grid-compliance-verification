#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the runner of the examples (``tools/scripts/test_tool.sh``).

The script is run as it is, with a ``dycov`` of the test first on the PATH: it records every
command it is given, rejects the commands the tool does not have as the real one does, and fails
the runs whose arguments name the example the test chooses.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "tools" / "scripts"

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="the script needs bash 4.3 or later and GNU find"
)

_FAKE_DYCOV = """#!/bin/bash
echo "$*" >> "$FAKE_DYCOV_CALLS"
value=""
for argument in "$@"; do
    if [ -n "$value" ]; then value=""; continue; fi
    case "$argument" in
        --user-config | --dtr) value=yes ;;
        -*) ;;
        validate | performance | generate_gfm_envelopes) break ;;
        *) echo "dycov: error: argument command: invalid choice: '$argument'" >&2; exit 2 ;;
    esac
done
if [ -n "${FAKE_DYCOV_FAIL:-}" ] && [[ "$*" == *"$FAKE_DYCOV_FAIL"* ]]; then
    exit "${FAKE_DYCOV_CODE:-1}"
fi
exit 0
"""


@pytest.fixture
def runner(tmp_path: Path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    dycov = bin_dir / "dycov"
    dycov.write_text(_FAKE_DYCOV)
    dycov.chmod(dycov.stat().st_mode | stat.S_IXUSR)
    (tmp_path / "examples").mkdir()
    calls = tmp_path / "calls.txt"
    calls.touch()

    def run(*options: str, fail: str = "", code: int = 1) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
        env["FAKE_DYCOV_CALLS"] = str(calls)
        env["FAKE_DYCOV_FAIL"] = fail
        env["FAKE_DYCOV_CODE"] = str(code)
        return subprocess.run(
            ["bash", str(_SCRIPTS / "test_tool.sh"), "-j", "1"]
            + ["-e", str(tmp_path / "examples"), "-o", str(tmp_path / "Results"), *options],
            env=env,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )

    run.calls = lambda: calls.read_text().splitlines()
    run.log = lambda: (tmp_path / "Results" / "test_tool.log").read_text()
    run.summary = tmp_path / "Results" / "test_tool.log.overall_result_counts.csv"
    return run


def test_the_envelope_phase_runs_the_command_the_tool_has(runner):
    run = runner("-g")

    assert run.returncode == 0, run.stderr
    generations = [call for call in runner.calls() if "generate_gfm_envelopes" in call]
    assert len(generations) == 3
    assert all(" -e " in call for call in generations)
    assert not [call for call in runner.calls() if "generateEnvelopes" in call]


def test_the_runner_succeeds_when_every_run_does(runner):
    run = runner()

    assert run.returncode == 0, runner.log()
    commands = {call.split()[0] for call in runner.calls()}
    assert commands == {"validate", "performance", "generate_gfm_envelopes"}
    assert runner.summary.is_file()


def test_the_envelope_phase_gets_the_options_of_every_run(runner, tmp_path):
    config = tmp_path / "user.ini"
    config.touch()

    run = runner("-g", "-d", "--user-config", str(config), "--dtr", "20240215")

    assert run.returncode == 0, run.stderr
    generations = [call for call in runner.calls() if "generate_gfm_envelopes" in call]
    assert len(generations) == 3
    prefix = f"-d --user-config {config} --dtr 20240215 generate_gfm_envelopes"
    assert all(call.startswith(prefix) for call in generations)


def test_a_failed_run_fails_the_runner_once_every_phase_has_run(runner):
    run = runner(fail="IECB2015")

    assert run.returncode != 0
    assert any("generate_gfm_envelopes" in call for call in runner.calls())
    assert runner.summary.is_file()
    assert "ERROR" in runner.log()
    assert "IECB2015" in runner.log().split("ERROR", 1)[1]


@pytest.mark.parametrize(
    "fail, phase",
    [
        ("/Performance/Single/", "performance verification"),
        ("/Dynawo/Zone3", "performance verification of the Model examples"),
    ],
    ids=["Performance examples", "Model examples"],
)
def test_a_failed_performance_run_fails_the_runner_naming_its_phase(runner, fail, phase):
    run = runner("-p", fail=fail)

    assert run.returncode != 0
    assert f"some dycov runs failed, in: {phase}. " in runner.log()


def test_a_failed_envelope_generation_fails_the_runner(runner):
    run = runner("-g", fail="Underdamped")

    assert run.returncode != 0
    assert len([call for call in runner.calls() if "generate_gfm_envelopes" in call]) == 3


def test_a_run_ending_with_255_does_not_stop_the_others(runner):
    """xargs launches no further job once one ends with 255, whatever made the run end so."""
    first_example = "IECA2015"

    run = runner("-v", fail=f"/{first_example}/", code=255)

    assert run.returncode != 0
    announced = runner.log().split("Model validation of: ", 1)[1].splitlines()[0].split()
    assert announced[0].endswith(first_example)
    validated = [call for call in runner.calls() if call.startswith("validate")]
    assert len(validated) == len(announced)
