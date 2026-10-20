#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The Grid Forming tests a producer is given follow from what it is: a BESS gets the matrix of
the DTR Fiche I18, a PPM the four PCS agreed with RTE before the fiche existed. The values of the
I18 scenarios are checked against the tables of the fiche, which print them for its typical unit
(Xeff = 0.27 pu)."""

from __future__ import annotations

import configparser
import math
from pathlib import Path

import pytest

import dycov
from dycov.configuration.cfg import config

_GFM_TEMPLATES = Path(dycov.__file__).resolve().parent / "templates" / "PCS" / "gfm"
_XEFF = 0.27

# Scenario: (DTR value, SCR) for tests 1 and 2, (initial frequency, RoCoF, duration, SCR) for 4
_PHASE_JUMPS = {
    "S_VolAngStep1": (6.36, 10),
    "S_VolAngStep2": (-6.36, 10),
    "S_VolAngStep3": (13.24, 2),
    "S_VolAngStep4": (-13.24, 2),
    "S_VolAngStep5": (12.72, 10),
    "S_VolAngStep6": (-12.72, 10),
    "S_VolAngStep7": (26.47, 2),
    "S_VolAngStep8": (-26.47, 2),
    "S_VolAngStep9": (5.5, 20),
    "S_VolAngStep10": (-5.5, 20),
    "S_VolAngStep11": (11.0, 20),
    "S_VolAngStep12": (-11.0, 20),
}
_AMPLITUDE_STEPS = {
    "S_VolAmpStep1": (0.116, 2),
    "S_VolAmpStep2": (-0.116, 2),
    "S_VolAmpStep3": (0.056, 10),
    "S_VolAmpStep4": (-0.056, 10),
    "S_VolAmpStep5": (0.048, 20),
    "S_VolAmpStep6": (-0.048, 20),
}
_PROFILES = [(49.5, 0.5, 3.0), (50.5, -0.5, 3.0), (49.5, 2.0, 0.5), (50.5, -2.0, 0.5)]
_ROCOFS = {
    f"S_Rocof{4 * index + number}": (*profile, scr)
    for index, scr in enumerate((2, 10, 20))
    for number, profile in enumerate(_PROFILES, start=1)
}
_OPERATING_CONDITIONS = {
    "PCS_RTE-IGFM1": 5,
    "PCS_RTE-IGFM2": 7,
    "PCS_RTE-IGFM3": 5,
    "PCS_RTE-IGFM4": 5,
}


def _description(technology: str, pcs: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(_GFM_TEMPLATES / technology / pcs / "PCSDescription.ini", encoding="utf-8")
    return parser


def _benchmarks(parser: configparser.ConfigParser, pcs: str) -> list[str]:
    return parser.get("PCS-Benchmarks", pcs).split(",")


def _scr(parser: configparser.ConfigParser, section: str) -> float:
    return config.get_float("GFM", parser.get(section, "SCR"), 0.0)


def _times_total_reactance(definition: str, scr: float) -> float:
    multiplier, factor = definition.split("*")
    assert factor == "(Xeff+Xgrid)"
    return float(multiplier) * (_XEFF + 1 / scr)


@pytest.mark.parametrize("technology", ["PPM", "BESS"])
def test_each_technology_ships_the_four_gfm_pcs(technology):
    shipped = sorted(path.name for path in (_GFM_TEMPLATES / technology).glob("PCS_*"))

    assert shipped == sorted(_OPERATING_CONDITIONS)


@pytest.mark.parametrize("pcs", sorted(_OPERATING_CONDITIONS))
def test_i18_operating_conditions(pcs):
    parser = _description("BESS", pcs)
    expected = ",".join(f"OC{i}" for i in range(1, _OPERATING_CONDITIONS[pcs] + 1))

    for benchmark in _benchmarks(parser, pcs):
        assert parser.get("PCS-OperatingConditions", f"{pcs}.{benchmark}") == expected


def test_i18_phase_jumps():
    parser = _description("BESS", "PCS_RTE-IGFM1")

    assert _benchmarks(parser, "PCS_RTE-IGFM1") == list(_PHASE_JUMPS)
    for benchmark, (degrees, scr) in _PHASE_JUMPS.items():
        section = f"PCS_RTE-IGFM1.{benchmark}"
        jump = _times_total_reactance(parser.get(section, "DeltaPhase"), _scr(parser, section))
        assert _scr(parser, section) == scr
        assert math.degrees(jump) == pytest.approx(degrees, abs=0.01)


def test_i18_amplitude_steps():
    parser = _description("BESS", "PCS_RTE-IGFM2")

    assert _benchmarks(parser, "PCS_RTE-IGFM2") == list(_AMPLITUDE_STEPS)
    for benchmark, (step, scr) in _AMPLITUDE_STEPS.items():
        section = f"PCS_RTE-IGFM2.{benchmark}"
        definition = parser.get(section, "VoltageStepAtGrid")
        assert _scr(parser, section) == scr
        assert _times_total_reactance(definition, scr) == pytest.approx(step, abs=0.001)


def test_i18_scr_jumps():
    parser = _description("BESS", "PCS_RTE-IGFM3")
    jumps = {
        benchmark: (
            parser.getfloat(f"PCS_RTE-IGFM3.{benchmark}", "SCRinitial"),
            parser.getfloat(f"PCS_RTE-IGFM3.{benchmark}", "SCRfinal"),
        )
        for benchmark in _benchmarks(parser, "PCS_RTE-IGFM3")
    }

    assert jumps == {"S_SCRup1": (2, 20), "S_SCRdown1": (20, 2)}


def test_i18_rocofs():
    parser = _description("BESS", "PCS_RTE-IGFM4")

    assert _benchmarks(parser, "PCS_RTE-IGFM4") == list(_ROCOFS)
    for benchmark, (frequency, rocof, duration, scr) in _ROCOFS.items():
        section = f"PCS_RTE-IGFM4.{benchmark}"
        assert parser.getfloat(section, "Frequency0") == frequency
        assert parser.getfloat(section, "RoCoF") == rocof
        assert parser.getfloat(section, "RoCoFDuration") == duration
        assert _scr(parser, section) == scr


def test_i18_operating_points_are_given_in_pu_of_the_converter_rating():
    aliases = configparser.ConfigParser(interpolation=None)
    aliases.optionxform = str
    aliases.read(_GFM_TEMPLATES / "BESS" / "config_aliases.ini", encoding="utf-8")
    points = {
        section: (aliases.get(section, "P0"), aliases.get(section, "Q0"))
        for section in aliases.sections()
    }

    assert points == {
        "PlantOC1": ("0", "0"),
        "PlantOC2": ("0.5", "0"),
        "PlantOC3": ("-0.5", "0"),
        "PlantOC4": ("0.95", "0"),
        "PlantOC5": ("-0.95", "0"),
        "PlantOC6": ("0", "-Qmax"),
        "PlantOC7": ("0", "Qmax"),
    }
