#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import logging
import shutil
import tempfile
from pathlib import Path

import pytest

from dycov.core.global_variables import (
    ELECTRIC_PERFORMANCE_PPM,
    ELECTRIC_PERFORMANCE_SM,
    REPORT_NAME,
)
from dycov.model.pcs import Pcs
from dycov.report.LatexReportException import LatexReportException
from dycov.validate.parameters import ValidationParameters
from dycov.validate.validation import Validation


# ---- Logger fixture: force Report logger level != DEBUG (deterministic cleanup) ----
@pytest.fixture(autouse=True)
def _patch_report_logger(monkeypatch):
    class _Logger:
        def __init__(self, name):
            self._name = name

        def getEffectiveLevel(self):
            # Force INFO so Latex folder is removed in __create_report
            return logging.INFO

        # minimal interface for .info/.warning/.error used across code
        def info(self, *a, **k):
            pass

        def warning(self, *a, **k):
            pass

        def error(self, *a, **k):
            pass

        def debug(self, *a, **k):
            pass

    def _get_logger(name):
        return _Logger(name)

    monkeypatch.setattr(
        "dycov.logging.logging.dycov_logging.get_logger",
        _get_logger,
        raising=True,
    )


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

    def set_zone(self, zone, producer_name):
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

    def get_filenames(self, zone=None):
        # keep interface compatible
        return ["dummy_file1", "dummy_file2"]


class DummyParameters(ValidationParameters):
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


def make_valid_pcs(producer, name, parameters):
    class ValidPCS(Pcs):
        def __init__(self, producer, pcs_name, parameters):
            super().__init__(producer, pcs_name, parameters)
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
                    "producer_name": "dummy_path",
                    "id": self._id,
                    "zone": self._zone,
                },
            )()
            summary_list.append(summary)
            return "report.tex", True, {"dummy": "result", "producer": "Producer", "pcs": self}

    return ValidPCS(producer, name, parameters)


def make_latex_exception_report(monkeypatch):
    from dycov.report.LatexReportException import LatexReportException

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
        "dycov.validate.validation.Pcs",
        lambda producer, name, params: make_valid_pcs(producer, name, params),
    )
    monkeypatch.setattr("dycov.report.report.create_pdf", lambda *a, **k: None)

    validation = Validation(parameters)
    pcs_names = [pcs_name for _, pcs_name, _, _ in validation._pcs_list]
    assert pcs_names == ["PCS2", "PCS2"]


def test_validation_exits_on_existing_output_dir(monkeypatch, temp_dirs):
    parameters = DummyParameters(output_dir=temp_dirs[0])
    # Simulate user not wanting to overwrite
    monkeypatch.setattr("dycov.files.manage_files.check_output_dir", lambda path: True)
    monkeypatch.setattr(
        "dycov.validate.validation.Pcs",
        lambda producer, name, params: make_valid_pcs(producer, name, params),
    )
    with pytest.raises(SystemExit):
        Validation(parameters)


def test_validation_copies_output_files_to_user_directory(monkeypatch, temp_dirs):
    parameters = DummyParameters(output_dir=temp_dirs[0])
    renamed, removed = [], []

    def fake_rename_path(source_path, target_path):
        renamed.append((str(source_path), str(target_path)))

    def fake_remove_dir(path):
        removed.append(str(path))

    monkeypatch.setattr(
        "dycov.validate.validation.Pcs",
        lambda producer, name, params: make_valid_pcs(producer, name, params),
    )
    monkeypatch.setattr("dycov.report.report.create_pdf", lambda *a, **k: None)
    monkeypatch.setattr("dycov.files.manage_files.remove_dir", fake_remove_dir)
    monkeypatch.setattr("dycov.files.manage_files.rename_path", fake_rename_path)

    validation = Validation(parameters)
    validation.set_testing(False)
    validation.validate(use_parallel=False, num_processes=4)

    assert len(renamed) == 1
    assert len(removed) == 1
    assert any("Latex" in c for c in removed)
