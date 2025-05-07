#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import shutil
import tempfile
from pathlib import Path

import pytest

from dycov.core.execution_parameters import Parameters
from dycov.core.global_variables import (
    ELECTRIC_PERFORMANCE_PPM,
    ELECTRIC_PERFORMANCE_SM,
    REPORT_NAME,
)
from dycov.core.validation import Validation
from dycov.model.pcs import Pcs
from dycov.report.LatexReportException import LatexReportException


class DummyProducer:
    def __init__(self, sim_type=ELECTRIC_PERFORMANCE_SM):
        self._sim_type = sim_type
        self._is_dynawo_model = True
        self._is_user_curves = True
        self._has_reference_curves_path = True

    def get_sim_type(self):
        return self._sim_type

    def get_sim_type_str(self):
        return "SM"

    def set_zone(self, zone):
        pass

    def is_dynawo_model(self):
        return self._is_dynawo_model

    def is_user_curves(self):
        return self._is_user_curves

    def has_reference_curves_path(self):
        return self._has_reference_curves_path

    def get_producer_path(self):
        return Path("dummy_model_path")

    def get_reference_path(self):
        return Path("dummy_reference_path")


class DummyParameters(Parameters):
    def __init__(
        self,
        launcher_dwo=Path("dummy_launcher"),
        producer_model=Path("dummy_model"),
        producer_curves_path=Path("dummy_curves"),
        reference_curves_path=Path("dummy_reference"),
        selected_pcs="PCS1",
        output_dir=None,
        only_dtr=False,
        verification_type=0,
        sim_type=ELECTRIC_PERFORMANCE_SM,
    ):
        self._launcher_dwo = launcher_dwo
        self._selected_pcs = selected_pcs
        self._output_dir = output_dir or Path(tempfile.mkdtemp())
        self._only_dtr = only_dtr
        self._producer = DummyProducer(sim_type)
        self._working_dir = Path(tempfile.mkdtemp())
        self._verification_type = verification_type

    def get_launcher_dwo(self):
        return self._launcher_dwo

    def get_selected_pcs(self):
        return self._selected_pcs

    def get_producer(self):
        return self._producer

    def get_working_dir(self):
        return self._working_dir

    def get_output_dir(self):
        return self._output_dir

    def get_sim_type(self):
        return self._producer.get_sim_type()

    def get_only_dtr(self):
        return self._only_dtr


@pytest.fixture
def temp_dirs():
    dirs = []
    for _ in range(3):
        d = Path(tempfile.mkdtemp())
        dirs.append(d)
    yield dirs
    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)


def make_valid_pcs(name, parameters):
    class ValidPCS(Pcs):
        def __init__(self, pcs_name, parameters):
            super().__init__(pcs_name, parameters)
            self._has_pcs_config = True
            self._has_user_config = True
            self._id = 1
            self._zone = 1

        def is_valid(self):
            return True

        def validate(self, summary_list):
            summary = type(
                "Summary",
                (),
                {
                    "compliance": True,
                    "producer_file": "dummy_path",
                    "id": self._id,
                    "zone": self._zone,
                },
            )()
            summary_list.append(summary)
            return "report.tex", True, {"dummy": "result"}

    return ValidPCS(name, parameters)


def make_invalid_pcs(name, parameters):
    class InvalidPCS(Pcs):
        def __init__(self, pcs_name, parameters):
            super().__init__(pcs_name, parameters)
            self._has_pcs_config = False
            self._has_user_config = False
            self._id = 2
            self._zone = 2

        def is_valid(self):
            return False

        def get_name(self):
            return name

    return InvalidPCS(name, parameters)


def make_exception_pcs(name, parameters, exc):
    class ExceptionPCS(Pcs):
        def __init__(self, pcs_name, parameters):
            super().__init__(pcs_name, parameters)
            self._has_pcs_config = True
            self._has_user_config = True
            self._id = 3
            self._zone = 3

        def is_valid(self):
            return True

        def validate(self, summary_list):
            raise exc("PCS validation failed")

    return ExceptionPCS(name, parameters)


def make_latex_exception_report(monkeypatch):
    def fake_create_pdf(*args, **kwargs):
        raise LatexReportException("Latex error")

    monkeypatch.setattr("dycov.report.report.create_pdf", fake_create_pdf)


def make_report_file(output_dir):
    reports_dir = output_dir / "Reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    pdf_file = reports_dir / REPORT_NAME.replace("tex", "pdf")
    pdf_file.write_bytes(b"%PDF-1.4\n%Fake PDF\n")
    return pdf_file


def test_validation_populates_pcs_list_correctly(monkeypatch, temp_dirs):
    parameters = DummyParameters(
        output_dir=temp_dirs[0], selected_pcs="PCS2", sim_type=ELECTRIC_PERFORMANCE_PPM
    )
    monkeypatch.setattr(
        "dycov.core.validation.Pcs", lambda name, params: make_valid_pcs(name, params)
    )
    monkeypatch.setattr("dycov.report.report.create_pdf", lambda *a, **k: None)
    validation = Validation(parameters)
    pcs_names = [pcs.get_name() for pcs in validation._pcs_list]
    assert pcs_names == ["PCS2"]


def test_validation_exits_on_existing_output_dir(monkeypatch, temp_dirs):
    parameters = DummyParameters(output_dir=temp_dirs[0])
    # Patch check_output_dir to simulate user not wanting to overwrite
    monkeypatch.setattr("dycov.files.manage_files.check_output_dir", lambda path: True)
    monkeypatch.setattr(
        "dycov.core.validation.Pcs", lambda name, params: make_valid_pcs(name, params)
    )
    with pytest.raises(SystemExit):
        Validation(parameters)


def test_validation_exits_on_pcs_validation_exception(monkeypatch, temp_dirs):
    parameters = DummyParameters(output_dir=temp_dirs[0])
    pcs_list = [
        make_exception_pcs("PCS_EXCEPTION", parameters, FileNotFoundError),
    ]
    monkeypatch.setattr("dycov.core.validation.Pcs", lambda name, params: pcs_list[0])
    monkeypatch.setattr("dycov.report.report.create_pdf", lambda *a, **k: None)
    validation = Validation(parameters)
    validation._pcs_list = pcs_list
    validation.set_testing(True)
    with pytest.raises(SystemExit):
        validation.validate()


def test_validation_copies_output_files_to_user_directory(monkeypatch, temp_dirs):
    parameters = DummyParameters(output_dir=temp_dirs[0])
    copied = []

    def fake_copy_output_files(pcs_name, source_path, target_path):
        copied.append((pcs_name, str(source_path), str(target_path)))

    monkeypatch.setattr(
        "dycov.core.validation.Pcs", lambda name, params: make_valid_pcs(name, params)
    )
    monkeypatch.setattr("dycov.report.report.create_pdf", lambda *a, **k: None)
    monkeypatch.setattr("dycov.files.manage_files.copy_output_files", fake_copy_output_files)
    validation = Validation(parameters)
    validation.set_testing(False)
    validation.validate()
    pcs_name = parameters.get_selected_pcs()
    assert any(pcs_name in c[0] for c in copied)
    assert any("Reports" in c[0] for c in copied)
