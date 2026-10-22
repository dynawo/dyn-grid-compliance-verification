#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The envelopes of a test are generated from the parameters of the unit, or read back from where
an envelope generation wrote them, and the producer curves are checked against them alike."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import dycov
from dycov.configuration.cfg import config
from dycov.gfm.gfm import GridForming
from dycov.gfm.parameters import GFMParameters
from dycov.gfm.producer import GFMProducer
from dycov.model.compliance import Compliance

_PCS, _BM, _OC = "PCS_RTE-I18z1", "S_VolAngStep1", "OC2"
_TEST = f"{_PCS}.{_BM}.{_OC}"
_UNIT = """[DEFAULT]
generator_type = BESS
p_max_injection = 100
p_max_consumption = 100
q_max = 30
q_min = -30
"""
_GFM_PARAMETERS = """[GFM Parameters]
Snom = 100
Xeff = 0.27
D = 150
H = 5
"""
_EVENT_IN_CURVES = 1.0


@pytest.fixture
def i18_description():
    description = (
        Path(dycov.__file__).resolve().parent
        / "templates/PCS/gfm/BESS"
        / _PCS
        / "PCSDescription.ini"
    )
    config.load_pcs_config(description)
    yield
    config.load_pcs_config(None)


class _Run:
    def __init__(self, path: Path):
        self._path = path

    def get_working_dir(self):
        return self._path

    def get_output_dir(self):
        return self._path / "Results"


def _parameters(tmp_path, unit_text, **kwargs):
    tmp_path.mkdir(parents=True, exist_ok=True)
    ini = tmp_path / "Producer.ini"
    ini.write_text(unit_text)
    return GFMParameters(_Run(tmp_path), GFMProducer(ini), **kwargs)


def _generate(parameters, working_path):
    working_path.mkdir(parents=True, exist_ok=True)
    return GridForming().generate(working_path, parameters, _PCS, _BM, _OC, "Producer")


def _write_producer_curves(curves_path: Path, envelopes_csv: Path):
    """The ideal response of the envelopes, delivered as the producer curves of the test."""
    envelopes = pd.read_csv(envelopes_csv, sep=";")
    time = np.arange(0.0, 5.0, 0.001)
    ip = np.interp(time, envelopes["Time (s)"], envelopes["Ip PGU (pu)"])
    curves_path.mkdir(parents=True)
    (curves_path / "CurvesFiles.ini").write_text(
        "[Curves-Dictionary]\ntime = t\n\n[Curves-Dictionary-Zone1]\n"
        "InternalNode1_BUS_ActiveCurrent = ip\nInternalNode1_BUS_ReactiveCurrent = iq\n\n"
        "[Curves-Dictionary-Zone3]\n"
    )
    pd.DataFrame({"t": time + _EVENT_IN_CURVES, "ip": ip, "iq": np.zeros_like(time)}).to_csv(
        curves_path / f"{_TEST}.csv", sep=";", index=False
    )
    (curves_path / f"{_TEST}.dict").write_text(
        f"[Curves-Metadata]\nsim_t_event_start = {_EVENT_IN_CURVES}\n\n[Curves-Dictionary]\n"
    )


def test_envelopes_read_back_check_the_curves_as_the_generated_ones(tmp_path, i18_description):
    generation = tmp_path / "generation"
    generated = _generate(
        _parameters(generation, _UNIT + _GFM_PARAMETERS), generation / _PCS / _BM / _OC
    )
    results = json.loads((generation / _PCS / _BM / _OC / "results.json").read_text())
    _write_producer_curves(
        tmp_path / "Curves" / "Producer", generation / _PCS / _BM / _OC / f"{_TEST}.csv"
    )

    # The unit of the validation declares no parameters: its envelopes are those given
    validation = tmp_path / "validation"
    checked = _generate(
        _parameters(
            validation,
            _UNIT,
            producer_curves=tmp_path / "Curves",
            envelopes=generation,
        ),
        validation / "Producer" / _PCS / _BM / _OC,
    )

    assert generated.compliance is None
    assert results["magnitude"] == "Ip"
    assert results["parameters"] == generated.parameters
    assert checked.compliance == Compliance.Compliant
    assert checked.parameters == generated.parameters
    assert (validation / "Producer" / _PCS / _BM / _OC / f"{_TEST}.png").exists()


def test_a_unit_without_parameters_nor_envelopes_has_no_envelopes(tmp_path, i18_description):
    test_report = _generate(
        _parameters(tmp_path, _UNIT, producer_curves=tmp_path / "Curves"), tmp_path / "test"
    )

    assert test_report.compliance == Compliance.WithoutEnvelopes
    assert list((tmp_path / "test").iterdir()) == []


def test_a_test_missing_from_the_envelopes_given_has_no_envelopes(tmp_path, i18_description):
    (tmp_path / "Envelopes").mkdir()

    test_report = _generate(
        _parameters(
            tmp_path,
            _UNIT + _GFM_PARAMETERS,
            producer_curves=tmp_path / "Curves",
            envelopes=tmp_path / "Envelopes",
        ),
        tmp_path / "test",
    )

    assert test_report.compliance == Compliance.WithoutEnvelopes
