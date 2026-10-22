#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The model validation of a storage gives its Zone 1 units the Grid Forming tests of the DTR
Fiche I18, which are not simulated: the producer curves among the reference curves are checked
against envelopes, read from the directory given or else generated from the INI file of the
unit."""

from pathlib import Path

import pytest

from dycov.core.global_variables import MODEL_VALIDATION_BESS, MODEL_VALIDATION_PPM
from dycov.gfm.parameters import GFMParameters
from dycov.gfm.report import GFMTestReport
from dycov.model.compliance import Compliance
from dycov.validate import validation
from dycov.validate.validation import Validation, _validate_pcs

_I18 = "PCS_RTE-I18z1"
_GFM_PARAMETERS = "[GFM Parameters]\nSnom = 1\nXeff = 0.27\nD = 100\nH = 5\n"


class _Producer:
    """A storage with a Zone 1 unit and the plant of Zone 3."""

    def __init__(self, tmp_path: Path, sim_type: int, gfm_parameters: str):
        self._sim_type = sim_type
        self._zone1 = tmp_path / "Dynawo" / "Zone1"
        self._zone1.mkdir(parents=True)
        (self._zone1 / "Producer_G1.ini").write_text(
            f"[DEFAULT]\np_max_injection = 1\nq_max = 0.3\nq_min = -0.3\n{gfm_parameters}"
        )
        self._reference = tmp_path / "ReferenceCurves"

    def get_sim_type(self):
        return self._sim_type

    def get_filenames(self, zone=0):
        return {1: ["Producer_G1"], 3: ["Producer"]}.get(zone, ["Producer_G1", "Producer"])

    def get_producer_ini(self, zone, filename):
        return self._zone1 / f"{filename}.ini"

    def get_reference_curves_path(self):
        return self._reference


class _Parameters:
    def __init__(self, tmp_path, sim_type, gfm_parameters=_GFM_PARAMETERS, envelopes=None):
        self._producer = _Producer(tmp_path, sim_type, gfm_parameters)
        self._working_dir = tmp_path / "working"
        self._output_dir = tmp_path / "Results"
        self._envelopes = envelopes

    def get_producer(self):
        return self._producer

    def get_sim_type(self):
        return self._producer.get_sim_type()

    def get_selected_pcs(self):
        return None

    def get_only_dtr(self):
        # The PCS of the user's configuration directory stay out of the tests
        return True

    def get_working_dir(self):
        return self._working_dir

    def get_output_dir(self):
        return self._output_dir

    def get_gfm_envelopes_path(self):
        return self._envelopes


def _pcs_list(parameters):
    return [(pcs, producer, args) for args, pcs, producer, _ in Validation(parameters)._pcs_list]


def test_the_zone_1_units_of_a_storage_are_given_the_grid_forming_pcs(tmp_path):
    parameters = _Parameters(tmp_path, MODEL_VALIDATION_BESS)

    pcs_list = _pcs_list(parameters)

    units = {(pcs, producer) for pcs, producer, _ in pcs_list}
    assert (_I18, "Producer_G1") in units
    assert not any(pcs == _I18 and producer == "Producer" for pcs, producer in units)
    gfm_parameters = next(args for pcs, _, args in pcs_list if pcs == _I18)
    assert isinstance(gfm_parameters, GFMParameters)
    assert gfm_parameters.get_producer().get_sim_type_str() == "gfm/BESS"
    assert gfm_parameters.get_producer_curves_path() == tmp_path / "ReferenceCurves"
    assert gfm_parameters.get_working_dir() == parameters.get_working_dir()
    assert all(args is parameters for pcs, _, args in pcs_list if pcs != _I18)


def test_a_power_park_module_is_given_no_grid_forming_pcs(tmp_path):
    pcs_list = _pcs_list(_Parameters(tmp_path, MODEL_VALIDATION_PPM))

    assert not any(isinstance(args, GFMParameters) for _, _, args in pcs_list)


@pytest.mark.parametrize("by_unit", [True, False])
def test_the_envelopes_of_a_unit_are_its_own_directory_or_the_one_given(tmp_path, by_unit):
    envelopes = tmp_path / "Envelopes"
    unit_envelopes = envelopes / "Producer_G1" if by_unit else envelopes
    unit_envelopes.mkdir(parents=True)
    parameters = _Parameters(tmp_path, MODEL_VALIDATION_BESS, envelopes=envelopes)

    gfm_parameters = next(args for pcs, _, args in _pcs_list(parameters) if pcs == _I18)

    assert gfm_parameters.get_envelopes_path() == unit_envelopes


def test_a_unit_without_parameters_nor_envelopes_is_warned(tmp_path, caplog):
    parameters = _Parameters(tmp_path, MODEL_VALIDATION_BESS, gfm_parameters="")

    gfm_parameters = next(args for pcs, _, args in _pcs_list(parameters) if pcs == _I18)

    warnings = [record.getMessage() for record in caplog.records if record.levelname == "WARNING"]
    warning = (
        f"{tmp_path / 'Dynawo' / 'Zone1' / 'Producer_G1.ini'} declares no [GFM Parameters] and "
        "no Grid Forming envelopes are given, so the Grid Forming tests of Producer_G1 cannot "
        "be checked"
    )
    assert not gfm_parameters.declares_unit_parameters()
    # The message may carry the prefix of the test context an earlier test left
    assert len([message for message in warnings if message.endswith(warning)]) == 1


def _test(oc, compliance):
    return GFMTestReport(
        producer_name="Producer_G1",
        pcs=_I18,
        benchmark="S_VolAngStep1",
        operating_condition=oc,
        magnitude="Ip",
        parameters=[],
        compliance=compliance,
        envelope=None,
        modes=[],
    )


def test_a_grid_forming_pcs_is_checked_instead_of_simulated(tmp_path, monkeypatch):
    tests = [
        _test("OC1", Compliance.Compliant),
        _test("OC2", Compliance.NonCompliant),
        _test("OC3", Compliance.WithoutProducerCurves),
        _test("OC4", Compliance.WithoutEnvelopes),
    ]

    class GridFormingPcs:
        def __init__(self, producer_name, pcs_name, parameters):
            self._producer_name = producer_name
            self._name = pcs_name

        def is_valid(self):
            return True

        def declares_tests(self):
            return True

        def get_producer_name(self):
            return self._producer_name

        def get_name(self):
            return self._name

        def get_id(self):
            return 18

        def get_zone(self):
            return 1

        def get_report_name(self):
            return "report.RTE-I18z1.tex"

        def generate(self):
            return tests

        def validate(self, summary_list):
            raise AssertionError("a Grid Forming test is not simulated")

    sections = []
    monkeypatch.setattr(validation, "Pcs", GridFormingPcs)
    monkeypatch.setattr(
        validation.gfm_report,
        "prepare_pcs_report",
        lambda pcs_report, *args, **kwargs: sections.append((pcs_report, kwargs)),
    )
    parameters = _Parameters(tmp_path, MODEL_VALIDATION_BESS)
    gfm_parameters = next(args for pcs, _, args in _pcs_list(parameters) if pcs == _I18)

    producer, pcs, summary_list, pcs_results = _validate_pcs(
        (gfm_parameters, _I18, "Producer_G1", Path("latex"))
    )

    assert (producer, pcs) == ("Producer_G1", _I18)
    assert [(item.id, item.zone, item.compliance) for item in summary_list] == [
        (18, 1, test.compliance) for test in tests
    ]
    assert pcs_results == {"producer": "Producer_G1", "report_name": "report.RTE-I18z1.tex"}
    # Only the tests whose curves were judged get a page, as the simulated tests do
    pcs_report, kwargs = sections[0]
    assert [test.operating_condition for test in pcs_report.tests] == ["OC1", "OC2"]
    assert kwargs == {"outputs_by_producer": True}
