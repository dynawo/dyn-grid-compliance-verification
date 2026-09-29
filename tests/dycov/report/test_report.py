#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import pandas as pd
import pytest

from dycov.report import report
from dycov.report.types import FigureDescription


@pytest.fixture
def oc_results():
    return {
        "curves": pd.DataFrame(
            {"time": [0.0, 1.0, 2.0], "BusPDR_BUS_ActivePower": [0.0, 0.5, 1.0]}
        )
    }


@pytest.fixture
def figures_description():
    return {
        "PCS.Benchmark": [
            FigureDescription(
                name="fig_P",
                variables=[{"type": "bus", "variable": "ActivePower"}],
                ylabel="P [pu]",
            )
        ]
    }


def test_generate_figures_passes_zone_to_html(
    monkeypatch, tmp_path, oc_results, figures_description
):
    seen_zones = []
    monkeypatch.setattr(report.figure, "create_plot", lambda *a, **k: None)
    monkeypatch.setattr(
        report.html,
        "plotly_figures",
        lambda *a, **k: seen_zones.append(k.get("zone")) or ([], "", ""),
    )

    report._generate_figures(
        tmp_path,
        "Producer",
        figures_description,
        "PCS.Benchmark",
        oc_results,
        "PCS.Benchmark.OC",
        0.0,
        2.0,
        zone=1,
    )

    assert seen_zones == [1]


def test_generate_figures_default_zone(monkeypatch, tmp_path, oc_results, figures_description):
    seen_zones = []
    monkeypatch.setattr(report.figure, "create_plot", lambda *a, **k: None)
    monkeypatch.setattr(
        report.html,
        "plotly_figures",
        lambda *a, **k: seen_zones.append(k.get("zone")) or ([], "", ""),
    )

    report._generate_figures(
        tmp_path,
        "Producer",
        figures_description,
        "PCS.Benchmark",
        oc_results,
        "PCS.Benchmark.OC",
        0.0,
        2.0,
    )

    assert seen_zones == [0]


def test_generate_figures_passes_zone_to_the_pdf(
    monkeypatch, tmp_path, oc_results, figures_description
):
    seen_zones = []
    monkeypatch.setattr(
        report.figure, "create_plot", lambda *a, **k: seen_zones.append(k.get("zone"))
    )
    monkeypatch.setattr(report.html, "plotly_figures", lambda *a, **k: ([], "", ""))

    report._generate_figures(
        tmp_path,
        "Producer",
        figures_description,
        "PCS.Benchmark",
        oc_results,
        "PCS.Benchmark.OC",
        0.0,
        2.0,
        zone=1,
    )

    assert seen_zones == [1]


@pytest.mark.parametrize("in_pdf, expected_pdf_figures", [(True, ["fig_P"]), (False, [])])
def test_generate_figures_sends_every_figure_to_the_html_and_to_the_pdf_only_if_asked(
    monkeypatch, tmp_path, oc_results, in_pdf, expected_pdf_figures
):
    """#553: the power at InternalNode1 is always drawn in the HTML, and in the PDF only when
    it does not repeat the controlled power."""
    pdf_figures, html_figures = [], []
    monkeypatch.setattr(
        report.figure,
        "create_plot",
        lambda time, description, *a, **k: pdf_figures.append(description.name),
    )
    monkeypatch.setattr(
        report.html,
        "plotly_figures",
        lambda description, *a, **k: html_figures.append(description.name) or ([], "", ""),
    )
    figures_description = {
        "PCS.Benchmark": [
            FigureDescription(
                name="fig_P", variables="BusPDR_BUS_ActivePower", ylabel="P", in_pdf=in_pdf
            )
        ]
    }

    report._generate_figures(
        tmp_path,
        "Producer",
        figures_description,
        "PCS.Benchmark",
        oc_results,
        "PCS.Benchmark.OC",
        0.0,
        2.0,
        zone=1,
    )

    assert pdf_figures == expected_pdf_figures
    assert html_figures == ["fig_P"]


def test_build_oc_notices_without_missing_or_warnings():
    notices, watermark = report._build_oc_notices({"missed_columns": []})

    assert notices == ""
    assert watermark == "\\SetWatermarkText{}"


def test_build_oc_notices_with_missed_columns():
    notices, watermark = report._build_oc_notices(
        {"missed_columns": ["Wind_Turbine_GEN_ActiveCurrentInjTerminal"]}
    )

    assert "\\noindent\\textcolor{red}{Missing curves:}" in notices
    assert "\\item \\textcolor{red}{Wind\\_Turbine\\_GEN\\_ActiveCurrentInjTerminal}" in notices
    assert watermark == "\\SetWatermarkText{INVALID}"


def test_build_oc_notices_without_reference_curves():
    notices, watermark = report._build_oc_notices(
        {"missed_columns": [], "incomplete_curves": True}
    )

    assert "\\noindent\\textcolor{red}{Missing curves:}" in notices
    assert "no reference curves" in notices
    assert watermark == "\\SetWatermarkText{INVALID}"


def test_build_oc_notices_without_reference_curves_and_with_missed_columns():
    notices, watermark = report._build_oc_notices(
        {"missed_columns": ["BusPDR_BUS_Voltage"], "incomplete_curves": True}
    )

    assert notices.count("Missing curves:") == 1
    assert "\\item \\textcolor{red}{BusPDR\\_BUS\\_Voltage}" in notices
    assert watermark == "\\SetWatermarkText{INVALID}"


def test_a_stable_test_is_labelled_as_such():
    assert report._stability_label(True) == "stable"


def test_an_unstable_test_is_labelled_with_a_latex_command_in_red():
    label = report._stability_label(False)

    assert label == r"\textcolor{red}{unstable}"
    assert "\t" not in label
