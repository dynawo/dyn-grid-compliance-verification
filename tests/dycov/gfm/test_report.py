#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path

import pytest

from dycov.gfm import report as gfm_report
from dycov.gfm.report import GFMTestReport, PcsReport
from dycov.gfm.verification.curves_compliance import DampedMode, EnvelopeCheck
from dycov.model.compliance import Compliance
from dycov.report import report


def _test(compliance=None, envelope=None, modes=(), benchmark="S_VolAngStep1", oc="OC2"):
    return GFMTestReport(
        producer_name="Producer",
        pcs="PCS_RTE-IGFM1",
        benchmark=benchmark,
        operating_condition=oc,
        magnitude="Ip",
        parameters=["P0 = 0.500 pu", "Δθ_grid = 6.360°", "t_90% = 10.000 ms"],
        compliance=compliance,
        envelope=envelope,
        modes=list(modes),
    )


class _Producer:
    def get_sim_type_str(self):
        return "gfm/BESS"

    def get_producer_path(self):
        return Path("examples/GFM/Fusion")


class _Parameters:
    def __init__(self, tmp_path, curves_path=None):
        self._tmp_path = tmp_path
        self._curves_path = curves_path

    def get_working_dir(self):
        return self._tmp_path / "working"

    def get_output_dir(self):
        return self._tmp_path / "Results"

    def get_producer(self):
        return _Producer()

    def get_producer_curves_path(self):
        return self._curves_path

    def is_emt(self):
        return False


def test_parameters_are_set_in_latex():
    assert gfm_report._parameter_row("Δθ_grid = -6.360°") == [
        r"\ensuremath{\Delta}\ensuremath{\theta}\_grid",
        r"-6.360\ensuremath{^\circ}",
    ]
    assert gfm_report._parameter_row("t_90% = 10.000 ms") == [r"t\_90\%", "10.000 ms"]


def test_summary_without_producer_curves_gives_no_verdict(tmp_path):
    rows = gfm_report._summary_rows([_test()], _Parameters(tmp_path))

    assert rows == [
        ["Producer", r"PCS\_RTE-IGFM1", r"S\_VolAngStep1", "OC2", "Envelopes generated"]
    ]


def test_summary_with_producer_curves_gives_the_verdict(tmp_path):
    tests = [_test(Compliance.Compliant), _test(Compliance.NonCompliant, oc="OC3")]

    rows = gfm_report._summary_rows(tests, _Parameters(tmp_path, Path("Curves")))

    assert [row[2:] for row in rows] == [
        [r"S\_VolAngStep1", "OC2", "Compliant"],
        [r"S\_VolAngStep1", "OC3", r"\textcolor{red}{Non-compliant}"],
    ]


def test_page_of_a_test_without_producer_curves():
    values = gfm_report._test_map(_test())

    assert values["testname"] == r"S\_VolAngStep1.OC2"
    assert values["figure"] == (
        "../Producer/PCS_RTE-IGFM1/S_VolAngStep1/OC2/PCS_RTE-IGFM1.S_VolAngStep1.OC2.png"
    )
    assert (
        "run:../PCS_RTE-IGFM1/S_VolAngStep1/OC2/PCS_RTE-IGFM1.S_VolAngStep1.OC2.html"
        in (values["link"])
    )
    assert not values["checked"]
    assert values["envelope"] is None


def test_page_of_a_checked_test():
    values = gfm_report._test_map(
        _test(
            Compliance.NonCompliant,
            EnvelopeCheck(True, 0.0, 0.0, 4.998),
            [DampedMode("Ip", "after", 2.0, 0.1, 0.12), DampedMode("Iq", "after", 1.2, 0.5, 0.3)],
        )
    )

    assert values["checked"]
    assert values["envelope"][:4] == ["Ip", "0.000", "4.998", "0.0000"]
    assert [row[-1] for row in values["modes"]] == [r"\textcolor{red}{ False }", "{ True }"]
    assert values["waterMarkText"] == r"\SetWatermarkText{}"


@pytest.mark.parametrize("compliance", [Compliance.WithoutProducerCurves, Compliance.InvalidTest])
def test_page_of_a_test_whose_curves_cannot_be_checked_is_invalid(compliance):
    values = gfm_report._test_map(_test(compliance, None, []))

    assert values["notices"]
    assert values["waterMarkText"] == r"\SetWatermarkText{INVALID}"


def test_create_pdf_renders_every_test_of_every_pcs(monkeypatch, tmp_path):
    compiled = []

    def fake_pdflatex(working_path, name):
        compiled.append(name)
        (working_path / f"{name}.pdf").write_text("pdf")
        return type("Proc", (), {"returncode": 0, "stderr": b""})()

    monkeypatch.setattr(report, "run_pdflatex", fake_pdflatex)
    pcs_reports = [
        PcsReport("Producer", "PCS_RTE-IGFM1", "report.RTE-IGFM1.tex", [_test(), _test(oc="OC3")]),
        PcsReport("Producer", "PCS_RTE-IGFM2", "report.RTE-IGFM2.tex", []),
    ]

    gfm_report.create_pdf(pcs_reports, _Parameters(tmp_path))

    latex_path = tmp_path / "working" / "Latex"
    main = (latex_path / "report.tex").read_text()
    section = (latex_path / "Producer.report.RTE-IGFM1.tex").read_text()
    assert compiled == ["report", "report", "report"]
    assert (tmp_path / "Results" / "Reports" / "report.pdf").exists()
    assert r"\input{Producer.report.RTE-IGFM1}" in main
    assert "Producer.report.RTE-IGFM2" not in main
    assert "Dynawo~" not in main.split(r"\begin{document}")[0].split("lhead")[-1]
    assert "step_response_characteristics" not in main
    assert r"\input{Producer.report.PCS_RTE-IGFM1.S_VolAngStep1.OC3}" in section
    assert (latex_path / "Producer.report.PCS_RTE-IGFM1.S_VolAngStep1.OC2.tex").exists()


def test_create_pdf_fails_when_pdflatex_produces_no_report(monkeypatch, tmp_path):
    from dycov.report.LatexReportException import LatexReportException

    def failing_pdflatex(working_path, name):
        (working_path / f"{name}.log").write_text("! LaTeX Error")
        return type("Proc", (), {"returncode": 1, "stderr": b""})()

    monkeypatch.setattr(report, "run_pdflatex", failing_pdflatex)
    pcs_reports = [PcsReport("Producer", "PCS_RTE-IGFM1", "report.RTE-IGFM1.tex", [_test()])]

    with pytest.raises(LatexReportException):
        gfm_report.create_pdf(pcs_reports, _Parameters(tmp_path))
    assert (tmp_path / "Results" / "Reports" / "report.log").exists()
