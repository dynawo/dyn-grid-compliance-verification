#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from __future__ import annotations

import configparser
from pathlib import Path

import pytest

import dycov

_PACKAGE_ROOT = Path(dycov.__file__).resolve().parent
_ZONE_1_DESCRIPTIONS = sorted(
    (_PACKAGE_ROOT / "templates" / "PCS" / "model").glob("*/PCS_RTE-I16z1/PCSDescription.ini")
)
_USTATOR_CURVES = ("MagnitudeControlledByAVRPu", "VoltageSetpointPu")


def read_option(ini_path: Path, section: str, option: str) -> str:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.read(ini_path, encoding="utf-8")
    return parser.get(section, option, fallback="")


def test_the_zone_1_descriptions_are_found():
    assert _ZONE_1_DESCRIPTIONS


@pytest.mark.parametrize("ini_path", _ZONE_1_DESCRIPTIONS, ids=lambda p: p.parent.parent.name)
def test_zone_1_enables_no_ustator_figure(ini_path):
    assert read_option(ini_path, "ReportCurves", "fig_Ustator").strip() == ""


@pytest.mark.parametrize("curve", _USTATOR_CURVES)
def test_zone_1_computes_none_of_the_ustator_curves(curve):
    zone_1_curves = read_option(
        _PACKAGE_ROOT / "configuration" / "defaultConfig.ini",
        "CurvesVariables",
        "ModelValidationZ1",
    )
    assert curve not in [name.strip() for name in zone_1_curves.split(",")]
