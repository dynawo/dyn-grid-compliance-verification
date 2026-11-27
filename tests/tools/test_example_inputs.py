#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the inputs of the example curve directories (``tools/scripts/example_inputs.py``):
the announcement of the records of the F16 tests the examples declare, the declaration of those
tests, and the maximum current the fault tests read, as the revision of the DTR the regeneration
follows writes them."""

from __future__ import annotations

import configparser
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_TOOL_DIR = _REPO / "tools" / "scripts"
sys.path.insert(0, str(_TOOL_DIR))

import example_inputs  # noqa: E402

_MODEL = _REPO / "examples" / "Model" / "Wind" / "IECB2015" / "Dynawo"


def test_the_announcement_writes_the_index_of_the_records_and_no_record(tmp_path):
    reference = tmp_path / "ReferenceCurves"

    assert example_inputs.announce_delivery(reference, _MODEL, "PPM") is True

    assert [path.name for path in (reference / "Producer").iterdir()] == ["CurvesFiles.ini"]


def test_the_announcement_keeps_an_index_already_there(tmp_path):
    producer = tmp_path / "ReferenceCurves" / "Producer"
    producer.mkdir(parents=True)
    (producer / "CurvesFiles.ini").write_text("[Curves-Files]\n", encoding="utf-8")

    assert example_inputs.announce_delivery(producer.parent, _MODEL, "PPM") is False

    assert (producer / "CurvesFiles.ini").read_text(encoding="utf-8") == "[Curves-Files]\n"


_REVISIONS = example_inputs._names_in(
    example_inputs._read_ini(example_inputs.PACKAGE / "configuration" / "defaultConfig.ini").get(
        "DTR", "available"
    )
)


def _template_tree(tmp_path: Path, monkeypatch) -> Path:
    """A copy of the templates the tool ships, which a test can give a revision of its own."""
    templates = tmp_path / "templates"
    for kind in ("PPM", "BESS"):
        inside = Path("PCS", "model", kind, "PCS_RTE-F16z3", "F16Description.ini")
        (templates / inside).parent.mkdir(parents=True)
        (templates / inside).write_text((example_inputs.TEMPLATES / inside).read_text())
    monkeypatch.setattr(example_inputs, "TEMPLATES", templates)
    return templates


@pytest.mark.parametrize("kind", ["PPM", "BESS"])
def test_the_f16_declaration_takes_the_levels_checks_and_figures_of_the_template(kind):
    template = example_inputs._read_ini(
        example_inputs.TEMPLATES / "PCS" / "model" / kind / "PCS_RTE-F16z3" / "F16Description.ini"
    )
    declaration = configparser.ConfigParser(interpolation=None)
    declaration.optionxform = str
    declaration.read_string(example_inputs.f16_declaration(kind, "20260723"))

    levels = template.get("PCS-OperatingConditions", "PCS_RTE-F16z3.RecordedTest")
    for benchmark in ("PSetPointStep", "USetPointStep"):
        assert declaration.get("PCS-OperatingConditions", f"PCS_RTE-F16z3.{benchmark}") == levels
        for level in levels.split(","):
            assert declaration.get(
                f"PCS_RTE-F16z3.{benchmark}.{level}.Model", "pdr_P"
            ) == template.get(f"PCS_RTE-F16z3.RecordedTest.{level}.Model", "pdr_P")
    assert declaration.options("Model-Validations") == template.options("Model-Validations")
    assert declaration.options("ReportCurves") == template.options("ReportCurves")


@pytest.mark.parametrize("kind", ["PPM", "BESS"])
def test_no_revision_the_tool_implements_writes_the_f16_declaration_differently(kind):
    declarations = {example_inputs.f16_declaration(kind, revision) for revision in _REVISIONS}

    assert len(declarations) == 1


def test_the_f16_declaration_follows_a_revision_that_rewrites_its_template(tmp_path, monkeypatch):
    templates = _template_tree(tmp_path, monkeypatch)
    rewritten = templates / "revisions" / "20990101" / "PCS" / "model" / "PPM" / "PCS_RTE-F16z3"
    rewritten.mkdir(parents=True)
    (rewritten / "F16Description.ini").write_text(
        "[PCS-OperatingConditions]\nPCS_RTE-F16z3.RecordedTest = P50,Pmax\n\n"
        "[PCS_RTE-F16z3.RecordedTest.P50.Model]\npdr_P = 0.6*Pmax\n\n"
        "[ReportCurves]\nfig_W = PCS_RTE-F16z3.RecordedTest\n"
    )

    declaration = example_inputs.f16_declaration("PPM", "20990101")

    assert "PCS_RTE-F16z3.PSetPointStep = P50,Pmax\n" in declaration
    assert "[PCS_RTE-F16z3.PSetPointStep.Pmin]" not in declaration
    assert "pdr_P = 0.6*Pmax\n" in declaration
    assert "fig_W = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep\n" in declaration


def test_a_check_a_revision_withdraws_from_the_template_is_not_declared(tmp_path, monkeypatch):
    templates = _template_tree(tmp_path, monkeypatch)
    rewritten = templates / "revisions" / "20990101" / "PCS" / "model" / "PPM" / "PCS_RTE-F16z3"
    rewritten.mkdir(parents=True)
    (rewritten / "F16Description.ini").write_text("[Model-Validations]\nreaction_time = none\n")

    declaration = example_inputs.f16_declaration("PPM", "20990101")

    assert "reaction_time" not in declaration
    assert "rise_time = PCS_RTE-F16z3.PSetPointStep,PCS_RTE-F16z3.USetPointStep\n" in declaration


def test_a_level_the_configuration_gives_no_step_stops_the_declaration(tmp_path, monkeypatch):
    templates = _template_tree(tmp_path, monkeypatch)
    rewritten = templates / "revisions" / "20990101" / "PCS" / "model" / "PPM" / "PCS_RTE-F16z3"
    rewritten.mkdir(parents=True)
    (rewritten / "F16Description.ini").write_text(
        "[PCS-OperatingConditions]\nPCS_RTE-F16z3.RecordedTest = Pmin,P75\n"
    )

    with pytest.raises(SystemExit, match="gives no step to the level P75"):
        example_inputs.f16_declaration("PPM", "20990101")


def _records(producer: Path, *tests: str) -> None:
    producer.mkdir(parents=True)
    for test in tests:
        (producer / f"{test}.dict").write_text("[Curves-Dictionary]\n", encoding="utf-8")


_BESS_FAULTS = [
    f"PCS_RTE-I5.ThreePhaseFault.Transient{kind}{mode}"
    for kind in ("Bolted", "Impedant")
    for mode in ("Injection", "Consumption")
]


@pytest.mark.parametrize("revision, written", [("20240215", 2), ("20260723", 4)])
def test_the_maximum_current_goes_into_the_tests_the_revision_runs(tmp_path, revision, written):
    """The impedant fault of the Fiche I5 is a test from the revision 20251013 on."""
    producer = tmp_path / "Producer"
    _records(producer, *_BESS_FAULTS)

    assert example_inputs.declare_imax(producer, "BESS", revision) == written

    declared = sorted(
        record.stem
        for record in producer.iterdir()
        if "MaxInjectedCurrentPu" in record.read_text()
    )
    assert declared == sorted(_BESS_FAULTS[:written])


def test_a_test_the_revision_runs_without_its_record_stops_the_maximum_current(tmp_path):
    producer = tmp_path / "Producer"
    _records(producer, *_BESS_FAULTS[:2])

    with pytest.raises(SystemExit, match="has no record"):
        example_inputs.declare_imax(producer, "BESS", "20260723")


def test_the_regeneration_follows_the_revision_release_ini_names_unless_asked_for_another():
    release = example_inputs._read_ini(example_inputs.RELEASE).get("DTR", "current")

    assert example_inputs.dtr_revision() == release
    assert example_inputs.dtr_revision("20251013") == "20251013"
    with pytest.raises(SystemExit, match="not a revision of the DTR the tool implements"):
        example_inputs.dtr_revision("20990101")
