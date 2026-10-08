#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The shipped F16 descriptions declare no test, because the DTR Fiche F16 fixes none: they
carry a declaration template, commented out, that a producer completes with the recorded tests
at the active power levels the fiche does fix."""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

import dycov

_PACKAGE_ROOT = Path(dycov.__file__).resolve().parent
_F16_DESCRIPTIONS = sorted(
    (_PACKAGE_ROOT / "templates" / "PCS" / "model").glob("*/PCS_RTE-F16z*/PCSDescription.ini")
)
_ACTIVE_POWER_LEVELS = {
    "PPM": {"Pmin", "0.5*Pmax", "Pmax"},
    "BESS": {"PmaxConsumption", "0.5*PmaxConsumption", "0.5*PmaxInjection", "PmaxInjection"},
}
_F16_CHECKS = {
    "reaction_time",
    "rise_time",
    "settling_time",
    "overshoot",
    "mean_absolute_error_power_1P",
    "mean_absolute_error_injection_1P",
    "mean_absolute_error_voltage",
    "setpoint_tracking_controlled_magnitude",
}


def _parse(text: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    parser.read_string(text)
    return parser


def _pcs_name(ini_path: Path) -> str:
    return ini_path.parent.name


def _technology(ini_path: Path) -> str:
    return ini_path.parent.parent.name


def _description_id(ini_path: Path) -> str:
    return f"{_technology(ini_path)}/{_pcs_name(ini_path)}"


def _completed_declaration(ini_path: Path) -> configparser.ConfigParser:
    """The description with its declaration template uncommented, as a producer leaves it: a
    template line starts with a single '#', a comment with '# '."""
    lines = []
    for line in ini_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") and not line.startswith("# "):
            line = line[1:]
        lines.append(line)
    return _parse("\n".join(lines))


def _operating_conditions(parser: configparser.ConfigParser, pcs: str):
    for benchmark in parser.get("PCS-Benchmarks", pcs).split(","):
        for oc in parser.get("PCS-OperatingConditions", f"{pcs}.{benchmark}").split(","):
            yield benchmark, oc


def test_every_technology_has_an_f16_description_of_zone_3():
    assert {(_technology(p), _pcs_name(p)) for p in _F16_DESCRIPTIONS} == {
        ("PPM", "PCS_RTE-F16z3"),
        ("BESS", "PCS_RTE-F16z3"),
    }


@pytest.mark.parametrize("ini_path", _F16_DESCRIPTIONS, ids=_description_id)
def test_the_shipped_description_declares_no_test(ini_path):
    parser = _parse(ini_path.read_text(encoding="utf-8"))

    assert parser.get("PCS-Benchmarks", _pcs_name(ini_path)) == ""
    assert not parser.has_section("GridCode")


@pytest.mark.parametrize("ini_path", _F16_DESCRIPTIONS, ids=_description_id)
def test_the_description_applies_the_on_site_thresholds_to_the_controlled_magnitude(ini_path):
    parser = _parse(ini_path.read_text(encoding="utf-8"))

    assert parser.get(_pcs_name(ini_path), "setpoint_tracking_thresholds") == "FT"


@pytest.mark.parametrize("ini_path", _F16_DESCRIPTIONS, ids=_description_id)
def test_the_declaration_template_runs_every_test_at_the_levels_of_the_fiche(ini_path):
    parser = _completed_declaration(ini_path)
    pcs = _pcs_name(ini_path)

    levels_by_benchmark = {}
    for benchmark, oc in _operating_conditions(parser, pcs):
        levels_by_benchmark.setdefault(benchmark, set()).add(
            parser.get(f"{pcs}.{benchmark}.{oc}.Model", "pdr_P")
        )

    assert levels_by_benchmark
    for benchmark, levels in levels_by_benchmark.items():
        assert levels == _ACTIVE_POWER_LEVELS[_technology(ini_path)], benchmark


@pytest.mark.parametrize("ini_path", _F16_DESCRIPTIONS, ids=_description_id)
def test_the_declaration_template_leaves_the_test_itself_to_the_producer(ini_path):
    parser = _completed_declaration(ini_path)
    pcs = _pcs_name(ini_path)

    for benchmark, oc in _operating_conditions(parser, pcs):
        event = parser[f"{pcs}.{benchmark}.{oc}.Event"]
        assert event["connect_event_to"] == ""
        assert event["sim_t_event_start"] == ""
        assert event["setpoint_step_value"] == ""
        assert (
            parser.get(f"{pcs}.{benchmark}.{oc}", "report_name")
            == f"report.F16{pcs[-2:]}.DeclaredTest.tex"
        )


@pytest.mark.parametrize("figure", ["fig_InternalNode1P", "fig_InternalNode1Q"])
@pytest.mark.parametrize(
    "ini_path",
    [path for path in _F16_DESCRIPTIONS if _pcs_name(path).endswith("z1")],
    ids=_description_id,
)
def test_the_zone_1_declaration_template_draws_the_internal_node1_power(ini_path, figure):
    """#553: the operating point of a Zone 1 test is the one at InternalNode1."""
    parser = _completed_declaration(ini_path)
    pcs = _pcs_name(ini_path)
    benchmarks = {
        f"{pcs}.{benchmark}" for benchmark in parser.get("PCS-Benchmarks", pcs).split(",")
    }

    assert set(parser.get("ReportCurves", figure).split(",")) == benchmarks


@pytest.mark.parametrize("ini_path", _F16_DESCRIPTIONS, ids=_description_id)
def test_the_declaration_template_applies_the_checks_of_the_fiche(ini_path):
    parser = _completed_declaration(ini_path)
    pcs = _pcs_name(ini_path)
    benchmarks = {
        f"{pcs}.{benchmark}" for benchmark in parser.get("PCS-Benchmarks", pcs).split(",")
    }

    for check in _F16_CHECKS:
        assert set(parser.get("Model-Validations", check).split(",")) == benchmarks, check
