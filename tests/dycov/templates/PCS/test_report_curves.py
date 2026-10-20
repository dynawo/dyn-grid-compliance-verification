#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the figures the PCS descriptions shipped with the tool enable in the report."""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

import dycov

_PACKAGE_ROOT = Path(dycov.__file__).resolve().parent
_ZONE_1_DESCRIPTIONS = sorted(
    (_PACKAGE_ROOT / "templates" / "PCS" / "model").glob("*/PCS_RTE-*z1/PCSDescription.ini")
)
_I16_ZONE_1_DESCRIPTIONS = sorted(
    (_PACKAGE_ROOT / "templates" / "PCS" / "model").glob("*/PCS_RTE-I16z1/PCSDescription.ini")
)


def read_option(ini_path: Path, section: str, option: str) -> str:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.read(ini_path, encoding="utf-8")
    return parser.get(section, option, fallback="")


def read_list(ini_path: Path, section: str, option: str) -> list[str]:
    return [value.strip() for value in read_option(ini_path, section, option).split(",")]


def test_the_zone_1_descriptions_are_found():
    assert _ZONE_1_DESCRIPTIONS


@pytest.mark.parametrize("ini_path", _ZONE_1_DESCRIPTIONS, ids=lambda p: p.parent.parent.name)
def test_zone_1_enables_no_ustator_figure(ini_path):
    assert read_option(ini_path, "ReportCurves", "fig_Ustator").strip() == ""


def test_the_i16_zone_1_descriptions_are_found():
    assert len(_I16_ZONE_1_DESCRIPTIONS) == 2


@pytest.mark.parametrize("figure", ["fig_InternalNode1P", "fig_InternalNode1Q"])
@pytest.mark.parametrize("ini_path", _I16_ZONE_1_DESCRIPTIONS, ids=lambda p: p.parent.parent.name)
def test_i16_zone_1_draws_the_internal_node1_power_in_every_benchmark(ini_path, figure):
    """#553: the DTR sets the operating point of every Zone 1 test at InternalNode1."""
    benchmarks = read_list(ini_path, "PCS-Benchmarks", "PCS_RTE-I16z1")

    declared = read_list(ini_path, "ReportCurves", figure)

    assert declared == [f"PCS_RTE-I16z1.{benchmark}" for benchmark in benchmarks]


@pytest.mark.parametrize("curve", ["MagnitudeControlledByAVRPu", "VoltageSetpointPu"])
def test_zone_1_does_not_compute_the_ustator_curves_in_every_test(curve):
    """#554: the voltage setpoint is asked for only in the test that steps it, which draws it
    over the voltage of the node the converter controls, never next to the plant-level
    magnitude fig_Ustator pairs it with."""
    zone_1_curves = read_option(
        _PACKAGE_ROOT / "configuration" / "defaultConfig.ini",
        "CurvesVariables",
        "ModelValidationZ1",
    )
    assert curve not in [name.strip() for name in zone_1_curves.split(",")]
