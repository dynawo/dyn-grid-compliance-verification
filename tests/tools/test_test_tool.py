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
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "tools" / "scripts"

_FAKE_DYCOV = """#!/bin/bash
echo "$*" >> "$FAKE_DYCOV_CALLS"
for argument in "$@"; do
    case "$argument" in
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


def _model_examples() -> list[str]:
    listing = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{_SCRIPTS / "models.sh"}"; '
            'printf "%s\\n" "${MODEL_EXAMPLES_IEC[@]}" "${MODEL_EXAMPLES_WECC[@]}"',
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return listing.stdout.split()


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


def test_a_failed_run_fails_the_runner_once_every_phase_has_run(runner):
    run = runner(fail="IECB2015")

    assert run.returncode != 0
    assert any("generate_gfm_envelopes" in call for call in runner.calls())
    assert runner.summary.is_file()
    assert "ERROR" in runner.log()
    assert "IECB2015" in runner.log().split("ERROR", 1)[1]


def test_a_failed_envelope_generation_fails_the_runner(runner):
    run = runner("-g", fail="Underdamped")

    assert run.returncode != 0
    assert len([call for call in runner.calls() if "generate_gfm_envelopes" in call]) == 3


def test_a_run_with_incomplete_inputs_does_not_stop_the_others(runner):
    """dycov ends with 255 when its inputs are incomplete, and xargs stops launching jobs at the
    first 255 it sees."""
    examples = _model_examples()

    run = runner("-v", fail=examples[0], code=255)

    assert run.returncode != 0
    validated = [call for call in runner.calls() if call.startswith("validate")]
    assert len(validated) == len(examples)
