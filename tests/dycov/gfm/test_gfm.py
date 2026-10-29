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
from dycov.logging import clear_test_context, set_test_context
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
        / "templates/revisions/20260723/PCS/gfm/BESS"
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
    time = envelopes["Time (s)"].to_numpy()
    curves_path.mkdir(parents=True)
    (curves_path / "CurvesFiles.ini").write_text(
        "[Curves-Dictionary]\ntime = t\n\n[Curves-Dictionary-Zone1]\n"
        "InternalNode1_BUS_ActiveCurrent = ip\nInternalNode1_BUS_ReactiveCurrent = iq\n"
        "InternalNode1_BUS_Voltage = u\n\n[Curves-Dictionary-Zone3]\n"
    )
    pd.DataFrame(
        {
            "t": time + _EVENT_IN_CURVES,
            "ip": envelopes["Ip PGU (pu)"],
            "iq": np.zeros_like(time),
            "u": np.ones_like(time),
        }
    ).to_csv(curves_path / f"{_TEST}.csv", sep=";", index=False)
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


def _set_section(parameters):
    parameters.set_section(_PCS, _BM, _OC)
    return parameters


def test_the_fiche_fixes_the_effective_reactance_and_the_inertia(tmp_path, i18_description):
    parameters = _set_section(
        _parameters(tmp_path, _UNIT + _GFM_PARAMETERS.replace("Xeff = 0.27", "Xeff = 0.15"))
    )

    assert parameters.get_effective_reactance() == pytest.approx(0.27)
    assert parameters.get_inertia_constant() == pytest.approx(5.0)


def test_a_higher_effective_reactance_of_the_producer_is_kept(tmp_path, i18_description):
    parameters = _set_section(
        _parameters(tmp_path, _UNIT + _GFM_PARAMETERS.replace("Xeff = 0.27", "Xeff = 0.35"))
    )

    assert parameters.get_effective_reactance() == pytest.approx(0.35)


def test_the_pgu_is_described_apart_from_the_installation(tmp_path, i18_description):
    pgu = "p_max_injection = 4.5\np_max_consumption = 4.5\nq_max = 2\nq_min = -2\n"
    installation = _UNIT.replace("p_max_injection = 100", "p_max_injection = 40")
    parameters = _set_section(
        _parameters(
            tmp_path, installation + _GFM_PARAMETERS.replace("Snom = 100", "Snom = 5") + pgu
        )
    )

    assert parameters.get_max_active_power() == pytest.approx(0.9)
    assert parameters.get_min_active_power() == pytest.approx(-0.9)
    assert parameters.get_max_reactive_power() == pytest.approx(0.4)
    assert parameters.get_min_reactive_power() == pytest.approx(-0.4)


def test_the_minimum_power_of_the_pgu_wins_over_the_consumption_of_the_installation(
    tmp_path, i18_description
):
    installation = _UNIT.replace("p_max_consumption = 100", "p_max_consumption = 45")
    pgu = _GFM_PARAMETERS.replace("Snom = 100", "Snom = 5") + "p_min_injection = -6\n"
    parameters = _set_section(_parameters(tmp_path, installation + pgu))

    assert parameters.get_min_active_power() == pytest.approx(-1.2)


def test_a_verification_warns_of_a_pgu_given_the_limits_of_the_installation(
    tmp_path, i18_description, caplog
):
    pgu = _GFM_PARAMETERS.replace("Snom = 100", "Snom = 5")
    parameters = _set_section(
        _parameters(tmp_path, _UNIT + pgu, producer_curves=tmp_path / "Curves")
    )

    parameters.get_max_active_power()
    parameters.get_max_active_power()

    warnings = [record for record in caplog.records if "p_max_injection of 100" in record.message]
    assert len(warnings) == 1


def test_the_effective_reactance_below_the_fiche_is_warned_of_once(
    tmp_path, i18_description, caplog
):
    parameters = _parameters(
        tmp_path, _UNIT + _GFM_PARAMETERS.replace("Xeff = 0.27", "Xeff = 0.15")
    )
    try:
        for oc in ("OC2", "OC3"):
            set_test_context(pcs=_PCS, benchmark=_BM, oc=oc, producer="Producer")
            parameters.set_section(_PCS, _BM, oc)
            parameters.get_effective_reactance()
    finally:
        clear_test_context()

    assert sum("Xeff of 0.15" in record.message for record in caplog.records) == 1


def test_a_unit_whose_parameters_are_incomplete_has_an_invalid_test(tmp_path, i18_description):
    test_report = _generate(
        _parameters(tmp_path, _UNIT + _GFM_PARAMETERS.replace("Snom = 100\n", "")),
        tmp_path / "test",
    )

    assert test_report.compliance == Compliance.InvalidTest


@pytest.mark.parametrize("magnitude, expected", [(None, "P"), ("Ip", "Ip")])
def test_the_rocof_bounds_the_power_unless_the_pcs_names_the_current(
    tmp_path, monkeypatch, magnitude, expected
):
    parameters = _parameters(tmp_path, _UNIT + _GFM_PARAMETERS)
    monkeypatch.setattr(
        GFMParameters,
        "_GFMParameters__get_value",
        lambda self, option: magnitude if option == "envelope_magnitude" else None,
    )

    assert parameters.get_envelope_magnitude("P") == expected


def test_a_user_description_naming_the_old_scr_max_is_warned(tmp_path, caplog):
    description = (
        Path(dycov.__file__).resolve().parent
        / "templates/revisions/20260723/PCS/gfm/BESS"
        / _PCS
        / "PCSDescription.ini"
    )
    user_description = tmp_path / "PCSDescription.ini"
    user_description.write_text(f"[{_TEST}]\nSCR = SCRmax\n")
    config.load_pcs_config(description, user_description)
    try:
        parameters = _set_section(_parameters(tmp_path, _UNIT + _GFM_PARAMETERS))

        assert parameters.get_scr() == pytest.approx(20.0)
    finally:
        config.load_pcs_config(None)
    assert any("names SCRmax" in record.getMessage() for record in caplog.records)
