#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the coverage guard of the curve regeneration (``tools/scripts``).

The guard stops the regeneration when a run did not cover every test the PCS declare. Which
tests those are depends on the revision of the DTR the run followed, and the guard reads that
revision from the log of the run itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_TOOL_DIR = _REPO / "tools" / "scripts"
sys.path.insert(0, str(_TOOL_DIR))

import declared_tests as dt  # noqa: E402

from dycov.configuration.cfg import config  # noqa: E402

BASE_REVISION = "20240215"
REVISION = "20260723"


@pytest.fixture(autouse=True)
def no_revision_left_behind():
    """The category reads the thresholds of a revision through the configuration of the
    process, which the script owns and a test shares: the base leaves that layer empty."""
    yield
    config.load_dtr_delta_config(BASE_REVISION)


_VERDICT_AT = dt.VERDICT_AT


def _summary_line(pcs: str, benchmark: str, oc: str, verdict: str) -> str:
    """One line of the summary table of a run, with the columns the guard reads."""
    line = f"{'Producer':<20}{pcs:<15}{benchmark:<25}{oc:<40}"
    assert len(line) == _VERDICT_AT
    return line + verdict


def _log(tmp_path: Path, revision: str, example: str, tests: list) -> Path:
    lines = [f"INFO | Validating against the DTR revision {revision}."]
    lines.append(f"***Model dir: /x/examples/Model/{example}/Dynawo***")
    lines.extend(_summary_line(*test) for test in tests)
    path = tmp_path / "run.log"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "value, names",
    [
        ("QMax,QMin", ["QMax", "QMin"]),
        ("none", []),
        ("None", []),
        ("", []),
        (None, []),
    ],
)
def test_the_word_none_names_a_list_with_nothing_in_it(value, names):
    """A revision that withdraws a fiche writes ``none``, which an empty value cannot say."""
    assert dt.names_in(value) == names


def test_the_delta_of_a_description_mirrors_the_shipped_templates(monkeypatch):
    monkeypatch.chdir(_REPO)
    description = dt.TEMPLATES / "PPM" / "PCS_RTE-I16z3" / "PCSDescription.ini"

    delta = dt.delta_of(description, REVISION)

    assert delta == (
        dt.PACKAGE_TEMPLATES
        / "revisions"
        / REVISION
        / "PCS/model/PPM/PCS_RTE-I16z3/PCSDescription.ini"
    )


def test_the_base_revision_writes_no_delta(monkeypatch):
    monkeypatch.chdir(_REPO)
    description = dt.TEMPLATES / "PPM" / "PCS_RTE-I16z3" / "PCSDescription.ini"

    assert dt.delta_of(description, BASE_REVISION) is None


def test_a_description_outside_the_templates_has_no_delta():
    """The example declares its F16 tests beside its curves, where no revision writes."""
    assert dt.delta_of(Path("examples/Model/Wind/WECC4B/F16Description.ini"), REVISION) is None


@pytest.mark.parametrize(
    "revision, swell",
    [
        (BASE_REVISION, {"QMax", "QMin"}),
        (REVISION, {"Qzero"}),
    ],
)
def test_the_declared_tests_follow_the_revision_of_the_run(monkeypatch, revision, swell):
    """20260723 tests the overvoltage at zero reactive power, and the guard must ask for that."""
    monkeypatch.chdir(_REPO)

    declared = dt.declared_tests("PPM", "Wind/WECC4B", revision)

    conditions = {
        oc
        for pcs, benchmark, oc in declared
        if (pcs, benchmark) == ("PCS_RTE-I16z3", "GridVoltageSwell")
    }
    assert conditions == swell


def test_the_guard_reads_the_revision_from_the_log(tmp_path):
    path = _log(
        tmp_path,
        REVISION,
        "Wind/WECC4B",
        [("PCS_RTE-I16z3", "ThreePhaseFault", "TransientBolted", "Compliant")],
    )

    executed, fell_over, revision = dt.executed_tests(path)

    assert revision == REVISION
    assert executed["Wind/WECC4B"] == {
        ("PCS_RTE-I16z3", "ThreePhaseFault", "TransientBolted"),
    }
    assert not fell_over


def test_a_test_that_fell_over_is_named_with_its_verdict(tmp_path):
    """A test that ran and fell over has no curve to ship, and the rest are still written."""
    path = _log(
        tmp_path,
        REVISION,
        "Wind/WECC4B",
        [("PCS_RTE-I16z3", "GridVoltageDip", "Qzero", "Simulation time out")],
    )

    _, fell_over, _ = dt.executed_tests(path)

    assert fell_over["Wind/WECC4B"] == {
        ("PCS_RTE-I16z3.GridVoltageDip.Qzero", "Simulation time out"),
    }


@pytest.mark.parametrize("revision", [BASE_REVISION, REVISION])
@pytest.mark.parametrize(
    "example, category",
    [("BESS/WECC", "B"), ("BESS/GridFormingDroop", "C"), ("BESS/GridFormingEpri", "C")],
)
def test_the_category_of_an_example_is_the_one_its_zone3_gives(
    monkeypatch, revision, example, category
):
    """15 MW at 225 kV is a storage of type B, 40 MW a type C, under either revision."""
    monkeypatch.chdir(_REPO)

    assert dt.installation_category(example, revision) == category


@pytest.mark.parametrize(
    "revision, category, versions",
    [(REVISION, "C", ["TypeCD.ini"]), (REVISION, "B", []), (BASE_REVISION, "C", [])],
)
def test_a_version_by_category_is_the_one_the_revision_writes(
    monkeypatch, revision, category, versions
):
    monkeypatch.chdir(_REPO)
    description = dt.TEMPLATES / "BESS" / "PCS_RTE-I16z1" / "PCSDescription.ini"

    assert [path.name for path in dt.version_of(description, revision, category)] == versions


def test_a_test_run_only_with_its_reference_is_not_one_that_must_run(monkeypatch):
    """The Fiche I16.2 asks for the tests of the Fiche I18 at OC2 and OC3, and at the others
    only when the producer records them."""
    monkeypatch.chdir(_REPO)

    declared = dt.declared_tests("BESS", "BESS/GridFormingDroop", REVISION)

    angle_steps = {oc for pcs, benchmark, oc in declared if benchmark == "S_VolAngStep1"}
    assert angle_steps == {"OC2", "OC3"}


def test_the_base_revision_gives_a_storage_of_type_c_the_fiche_i16(monkeypatch):
    monkeypatch.chdir(_REPO)

    declared = dt.declared_tests("BESS", "BESS/GridFormingDroop", BASE_REVISION)

    zone1 = {benchmark for pcs, benchmark, oc in declared if pcs == "PCS_RTE-I16z1"}
    assert zone1 == {"ThreePhaseFault", "SetPointStep", "GridVoltageStep"}
