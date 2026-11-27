#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the revision of the DTR the curve regeneration follows (``tools/scripts``).

The scripts are run as they are, from a directory laid out as the root of the repository, with a
``dycov`` of the test first on the PATH: it records every command it is given, says in its log
which revision its configuration names, as the real one does, and anonymizes into records with
nothing in them.
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
    sys.platform != "linux", reason="the scripts need bash 4.3 or later and GNU sed"
)

_FAKE_DYCOV = """#!/bin/bash
echo "$*" >> "$FAKE_DYCOV_CALLS"
configuration=""
output=""
previous=""
for argument in "$@"; do
    case "$previous" in
        --user-config) configuration=$argument ;;
        --output | -o) output=$argument ;;
    esac
    previous=$argument
done
revision=$(sed -n 's/^current *= *//p' "$configuration")
echo "x | Validating against the DTR revision $revision."
if [[ " $* " == *" performance "* || " $* " == *" validate "* ]]; then
    mkdir -p "$output"
fi
if [[ " $* " == *" anonymize "* ]]; then
    mkdir -p "$output/Producer"
    : > "$output/Producer/record.csv"
    for case in BoltedInjection BoltedConsumption ImpedantInjection ImpedantConsumption \\
            Bolted Impedant; do
        record="$output/Producer/PCS_RTE-I5.ThreePhaseFault.Transient$case.dict"
        printf '[Curves-Dictionary]\\n' > "$record"
    done
fi
exit 0
"""

_MODEL_RUNS = ("Wind/IECB2015", "BESS/WECC")

# The python3 of the scripts, which leaves out the coverage guard: the fake dycov runs no test.
_FAKE_PYTHON = """#!/bin/bash
[[ "$1" == *declared_tests.py ]] && exit 0
exec {python} "$@"
"""


def _model_examples() -> list:
    listed = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{_SCRIPTS}/models.sh"; printf "%s\\n" "${{MODEL_EXAMPLES_IEC[@]}}" '
            '"${MODEL_EXAMPLES_WECC[@]}" "${MODEL_EXAMPLES_GFM[@]}"',
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return listed.stdout.split()


@pytest.fixture
def repository(tmp_path: Path):
    """A directory laid out as the root of the repository, with a fake dycov on the PATH."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    dycov = bin_dir / "dycov"
    dycov.write_text(_FAKE_DYCOV)
    dycov.chmod(dycov.stat().st_mode | stat.S_IXUSR)
    python = bin_dir / "python3"
    python.write_text(_FAKE_PYTHON.format(python=sys.executable))
    python.chmod(python.stat().st_mode | stat.S_IXUSR)
    root = tmp_path / "repository"
    (root / "examples" / "Model").mkdir(parents=True)
    calls = tmp_path / "calls.txt"
    calls.touch()

    def run(script: str, *options: str, state_dir: Path = None) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
        env["FAKE_DYCOV_CALLS"] = str(calls)
        if state_dir is not None:
            env["DYCOV_STATE_DIR"] = str(state_dir)
        return subprocess.run(
            ["bash", str(_SCRIPTS / script), *options],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )

    run.root = root
    run.working_path = tmp_path / "RegeneratedCurves"
    run.calls = lambda: calls.read_text().splitlines()
    return run


def _common(script: str, *arguments: str) -> subprocess.CompletedProcess:
    """Runs one function of curves_common.sh, sourced as the stages source it."""
    return subprocess.run(
        [
            "bash",
            "-c",
            f'set -o nounset -o errexit; script_dir="{_SCRIPTS}"; '
            f'source "{_SCRIPTS}/curves_common.sh"; {script} "$@"',
            "_",
            *arguments,
        ],
        capture_output=True,
        text=True,
    )


def _revision_named_in(configuration: str) -> str:
    for line in Path(configuration).read_text().splitlines():
        if line.startswith("current"):
            return line.split("=", 1)[1].strip()
    return ""


def _release_revision() -> str:
    return _revision_named_in(str(_SCRIPTS / "release.ini"))


def _log_of_a_run(log: Path, revision: str) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(f"x | Validating against the DTR revision {revision}.\n")


def _model_run(working_path: Path, revision: str, examples=_MODEL_RUNS) -> None:
    """What the reference curves leave for the producer curves: the anonymized curves of the
    Model examples and the logs of their runs."""
    for example in examples:
        producer = working_path / "Curves" / "Model" / example / "Producer"
        producer.mkdir(parents=True)
        (producer / "record.csv").touch()
        log = working_path / "Results" / "Model" / f"{example}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"x | Validating against the DTR revision {revision}.\n")


def test_the_revision_release_ini_names_is_read_from_release_ini_itself(tmp_path):
    result = _common("run_configuration", str(tmp_path), _release_revision())

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(_SCRIPTS / "release.ini")
    assert not list(tmp_path.iterdir())


def test_another_revision_is_written_into_a_copy_of_release_ini_in_the_working_path(tmp_path):
    result = _common("run_configuration", str(tmp_path / "work"), "20251013")

    assert result.returncode == 0, result.stderr
    configuration = Path(result.stdout.strip())
    assert configuration.parent == tmp_path / "work"
    assert _revision_named_in(str(configuration)) == "20251013"
    release = (_SCRIPTS / "release.ini").read_text().splitlines()
    copy = configuration.read_text().splitlines()
    assert [line for line in copy if line not in release] == ["current = 20251013"]
    assert [path.name for path in configuration.parent.iterdir()] == [configuration.name]


def test_a_revision_the_tool_does_not_implement_stops_the_regeneration():
    result = _common("dtr_revision", "20990101")

    assert result.returncode != 0
    assert "20990101: not a revision of the DTR the tool implements" in result.stderr


def test_the_revision_of_a_run_is_the_one_its_log_names(tmp_path):
    log = tmp_path / "run.log"
    log.write_text("start\n2026 | INFO | Validating against the DTR revision 20250801.\nend\n")

    assert _common("revision_of_run", str(log)).stdout.strip() == "20250801"


def test_an_example_runs_with_the_revision_asked_for(repository):
    (repository.root / "examples" / "Model" / "Wind" / "IECB2015" / "Dynawo").mkdir(parents=True)

    run = repository(
        "regenerate_one_example.sh",
        "-o",
        str(repository.working_path),
        "--dtr",
        "20251013",
        "Wind/IECB2015",
    )

    validations = [call for call in repository.calls() if " validate " in call]
    assert len(validations) == 1
    configuration = validations[0].split("--user-config ", 1)[1].split()[0]
    assert run.returncode == 0, run.stdout + run.stderr
    assert _revision_named_in(configuration) == "20251013"
    assert Path(configuration).parent == repository.working_path


def test_an_example_asked_for_no_revision_runs_with_release_ini(repository):
    (repository.root / "examples" / "Model" / "Wind" / "IECB2015" / "Dynawo").mkdir(parents=True)

    repository("regenerate_one_example.sh", "-o", str(repository.working_path), "Wind/IECB2015")

    validations = [call for call in repository.calls() if " validate " in call]
    assert validations[0].startswith(f"--user-config {_SCRIPTS / 'release.ini'} validate")


def test_the_producer_curves_follow_the_revision_of_the_run_of_the_reference_curves(repository):
    _model_run(repository.working_path, "20240215")

    run = repository("regenerate_producer_curves.sh", "-o", str(repository.working_path))

    assert run.returncode == 0, run.stdout + run.stderr
    runs = [call for call in repository.calls() if " performance " in call]
    assert len(runs) == 3
    for call in runs + [call for call in repository.calls() if " anonymize " in call]:
        configuration = call.split("--user-config ", 1)[1].split()[0]
        assert _revision_named_in(configuration) == "20240215"
    records = repository.root / "examples" / "Performance" / "ProducerCurves" / "BESS" / "Producer"
    written = sorted(
        record.stem.rsplit(".", 1)[1]
        for record in records.glob("*.dict")
        if "MaxInjectedCurrentPu" in record.read_text()
    )
    assert written == ["TransientBoltedConsumption", "TransientBoltedInjection"]
    performance_log = repository.working_path / "Results" / "Performance" / "BESS.log"
    assert "Validating against the DTR revision 20240215." in performance_log.read_text()


def test_the_producer_curves_asked_for_another_revision_than_their_model_run_stop(repository):
    _model_run(repository.working_path, "20240215")

    run = repository(
        "regenerate_producer_curves.sh", "-o", str(repository.working_path), "--dtr", "20251013"
    )

    assert run.returncode != 0
    assert "follow the DTR revision 20240215, not 20251013" in run.stderr
    assert repository.calls() == []


def test_the_producer_curves_without_the_log_of_the_model_run_stop(repository):
    _model_run(repository.working_path, "20240215")
    (repository.working_path / "Results" / "Model" / "BESS" / "WECC.log").unlink()

    run = repository("regenerate_producer_curves.sh", "-o", str(repository.working_path))

    assert run.returncode != 0
    assert "There is no log of the run to reuse in" in run.stderr
    assert "BESS/WECC.log" in run.stderr
    assert repository.calls() == []


def test_a_regeneration_asked_for_a_revision_the_tool_does_not_implement_runs_nothing(repository):
    run = repository(
        "regenerate_curves.sh", "-o", str(repository.working_path), "--dtr", "20990101"
    )

    assert run.returncode != 0
    assert "20990101: not a revision of the DTR the tool implements" in run.stderr
    assert repository.calls() == []
    assert not list((repository.root / "examples" / "Model").iterdir())


def test_a_reused_run_of_another_revision_than_the_one_asked_for_stops_the_example(repository):
    (repository.root / "examples" / "Model" / "Wind" / "IECB2015" / "Dynawo").mkdir(parents=True)
    _model_run(repository.working_path, "20240215")
    (repository.working_path / "Results" / "Model" / "Wind" / "IECB2015").mkdir(parents=True)

    state = repository.working_path / "state"
    state.mkdir(parents=True)

    run = repository(
        "regenerate_one_example.sh",
        "-o",
        str(repository.working_path),
        "--reuse",
        "--dtr",
        "20251013",
        "Wind/IECB2015",
        state_dir=state,
    )

    assert run.returncode != 0
    assert "followed the DTR revision 20240215, not 20251013" in run.stderr
    assert repository.calls() == []
    assert (state / "Wind__IECB2015").read_text().strip() == "failed"


def test_reference_curves_reused_from_runs_of_several_revisions_stop(repository):
    examples = _model_examples()
    for example in examples:
        _log_of_a_run(repository.working_path / "Results" / "Model" / f"{example}.log", "20240215")
    _log_of_a_run(
        repository.working_path / "Results" / "Model" / f"{examples[-1]}.log", "20251013"
    )

    run = repository(
        "regenerate_reference_curves.sh", "-o", str(repository.working_path), "--reuse"
    )

    assert run.returncode != 0
    assert "followed the DTR revisions 20240215 and 20251013" in run.stderr
    assert repository.calls() == []


def test_a_regeneration_that_reuses_runs_of_another_revision_writes_nothing(repository):
    for example in _model_examples():
        _log_of_a_run(repository.working_path / "Results" / "Model" / f"{example}.log", "20240215")

    run = repository(
        "regenerate_curves.sh", "-o", str(repository.working_path), "--reuse", "--dtr", "20251013"
    )

    assert run.returncode != 0
    assert "followed the DTR revision 20240215, not 20251013" in run.stderr
    assert repository.calls() == []
    assert not list((repository.root / "examples" / "Model").iterdir())


def test_producer_curves_reused_from_a_performance_run_of_another_revision_stop(repository):
    _model_run(repository.working_path, "20260723")
    for family in ("SM", "PPM", "BESS"):
        performance = repository.working_path / "Results" / "Performance"
        (performance / family).mkdir(parents=True)
        _log_of_a_run(
            performance / f"{family}.log", "20251013" if family == "BESS" else "20260723"
        )

    run = repository(
        "regenerate_producer_curves.sh", "-o", str(repository.working_path), "--reuse"
    )

    assert run.returncode != 0
    assert "The BESS performance run" in run.stderr
    assert repository.calls() == []
