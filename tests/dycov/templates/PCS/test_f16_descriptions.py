#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The shipped F16 descriptions declare no test, because the DTR Fiche F16 fixes none: next to
each one ships the F16Description.ini template that a producer copies beside the reference
curves and completes with the recorded tests, at the active power levels the fiche does fix."""

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


def _declaration_template(ini_path: Path) -> configparser.ConfigParser:
    """The F16Description.ini shipped next to the description of the PCS."""
    return _parse((ini_path.parent / "F16Description.ini").read_text(encoding="utf-8"))


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
def test_the_declaration_template_names_the_pcs_it_declares(ini_path):
    parser = _declaration_template(ini_path)

    assert parser.get("PCS-Benchmarks", _pcs_name(ini_path)) != ""
    assert not parser.has_section(_pcs_name(ini_path))


@pytest.mark.parametrize("ini_path", _F16_DESCRIPTIONS, ids=_description_id)
def test_the_declaration_template_runs_every_test_at_the_levels_of_the_fiche(ini_path):
    parser = _declaration_template(ini_path)
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
    parser = _declaration_template(ini_path)
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


@pytest.mark.parametrize("ini_path", _F16_DESCRIPTIONS, ids=_description_id)
def test_the_declaration_template_applies_the_checks_of_the_fiche(ini_path):
    parser = _declaration_template(ini_path)
    pcs = _pcs_name(ini_path)
    benchmarks = {
        f"{pcs}.{benchmark}" for benchmark in parser.get("PCS-Benchmarks", pcs).split(",")
    }

    for check in _F16_CHECKS:
        assert set(parser.get("Model-Validations", check).split(",")) == benchmarks, check
