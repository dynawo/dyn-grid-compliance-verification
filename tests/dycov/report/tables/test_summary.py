#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from dycov.model.compliance import Compliance
from src.dycov.report.tables.summary import create_map


class DummySummary:
    def __init__(self, pcs, benchmark, operating_condition, compliance):
        self.pcs = pcs
        self.benchmark = benchmark
        self.operating_condition = operating_condition
        self.compliance = compliance


def test_create_map_with_standard_compliant_entries():
    summary_list = [
        DummySummary(
            pcs="PCS1",
            benchmark="BenchmarkA",
            operating_condition="OC1",
            compliance=Compliance.Compliant,
        )
    ]
    result = create_map(summary_list)
    assert result == [["PCS1", "BenchmarkA", "OC1", "Compliant"]]


def test_create_map_escapes_underscores_in_pcs():
    summary_list = [
        DummySummary(
            pcs="PCS_1",
            benchmark="BenchmarkA",
            operating_condition="OC1",
            compliance=Compliance.Compliant,
        )
    ]
    result = create_map(summary_list)
    assert result[0][0] == "PCS\\_1"


def test_create_map_applies_red_text_for_non_compliant():
    summary_list = [
        DummySummary(
            pcs="PCS1",
            benchmark="BenchmarkA",
            operating_condition="OC1",
            compliance=Compliance.NonCompliant,
        )
    ]
    result = create_map(summary_list)
    assert result[0][3] == "\\textcolor{red}{Non-compliant}"


def test_create_map_with_empty_fields():
    summary_list = [
        DummySummary(
            pcs="",
            benchmark="",
            operating_condition="",
            compliance=Compliance.Compliant,
        )
    ]
    result = create_map(summary_list)
    assert result == [["", "", "", "Compliant"]]


def test_create_map_with_invalid_compliance_value():
    class FakeCompliance:
        def to_str(self):
            return "Unknown compliance"

    summary_list = [
        DummySummary(
            pcs="PCS1",
            benchmark="BenchmarkA",
            operating_condition="OC1",
            compliance=FakeCompliance(),
        )
    ]
    result = create_map(summary_list)
    # Since FakeCompliance is not Compliance.Compliant, should be wrapped in red
    assert result[0][3] == "\\textcolor{red}{Unknown compliance}"


def test_create_map_with_empty_summary_list():
    summary_list = []
    result = create_map(summary_list)
    assert result == []
