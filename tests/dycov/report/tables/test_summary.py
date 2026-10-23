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
from dycov.report.tables.summary import create_map


class DummySummary:
    def __init__(
        self,
        producer_name,
        pcs,
        benchmark,
        operating_condition,
        compliance,
        altered_criteria=(),
    ):
        self.producer_name = producer_name
        self.pcs = pcs
        self.benchmark = benchmark
        self.operating_condition = operating_condition
        self.compliance = compliance
        self.altered_criteria = altered_criteria


def test_create_map_with_standard_compliant_entries():
    summary_list = [
        DummySummary(
            producer_name="dummy_path",
            pcs="PCS1",
            benchmark="BenchmarkA",
            operating_condition="OC1",
            compliance=Compliance.Compliant,
        )
    ]
    result = create_map(summary_list)
    assert result == [["dummy\\_path", "PCS1", "BenchmarkA", "OC1", "Compliant"]]


def test_create_map_escapes_underscores_in_pcs():
    summary_list = [
        DummySummary(
            producer_name="dummy_path",
            pcs="PCS_1",
            benchmark="BenchmarkA",
            operating_condition="OC1",
            compliance=Compliance.Compliant,
        )
    ]
    result = create_map(summary_list)
    assert result[0][1] == "PCS\\_1"


def test_create_map_applies_red_text_for_non_compliant():
    summary_list = [
        DummySummary(
            producer_name="dummy_path",
            pcs="PCS1",
            benchmark="BenchmarkA",
            operating_condition="OC1",
            compliance=Compliance.NonCompliant,
        )
    ]
    result = create_map(summary_list)
    assert result[0][4] == "\\textcolor{red}{Non-compliant}"


def test_create_map_with_empty_fields():
    summary_list = [
        DummySummary(
            producer_name="",
            pcs="",
            benchmark="",
            operating_condition="",
            compliance=Compliance.Compliant,
        )
    ]
    result = create_map(summary_list)
    assert result == [["", "", "", "", "Compliant"]]


def test_create_map_with_invalid_compliance_value():
    class FakeCompliance:
        def to_str(self):
            return "Unknown compliance"

    summary_list = [
        DummySummary(
            producer_name="dummy_path",
            pcs="PCS1",
            benchmark="BenchmarkA",
            operating_condition="OC1",
            compliance=FakeCompliance(),
        )
    ]
    result = create_map(summary_list)
    # Since FakeCompliance is not Compliance.Compliant, should be wrapped in red
    assert result[0][4] == "\\textcolor{red}{Unknown compliance}"


def test_create_map_with_empty_summary_list():
    summary_list = []
    result = create_map(summary_list)
    assert result == []


def test_create_map_not_applicable_defines_footnote_once():
    summary_list = [
        DummySummary(
            producer_name="dummy_path",
            pcs="PCS1",
            benchmark="BenchmarkA",
            operating_condition="OC1",
            compliance=Compliance.NotApplicableTest,
        )
    ]
    result = create_map(summary_list)
    assert result[0][4] == (
        "\\textcolor{red}{Not applicable test}\\footnote{Not executed: incompatible control mode.}"
    )


def test_create_map_repeated_not_applicable_reuses_footnote():
    summary_list = [
        DummySummary(
            producer_name="dummy_path",
            pcs="PCS1",
            benchmark="BenchmarkA",
            operating_condition="OC1",
            compliance=Compliance.NotApplicableTest,
        ),
        DummySummary(
            producer_name="dummy_path",
            pcs="PCS2",
            benchmark="BenchmarkB",
            operating_condition="OC2",
            compliance=Compliance.NotApplicableTest,
        ),
    ]
    result = create_map(summary_list)
    assert "\\footnote{" in result[0][4]
    assert result[1][4] == (
        "\\textcolor{red}{Not applicable test}\\footnotemark[\\value{footnote}]"
    )


def test_create_map_marks_a_pcs_measured_with_altered_criteria():
    summary_list = [
        DummySummary(
            producer_name="dummy",
            pcs="PCS1",
            benchmark="BenchmarkA",
            operating_condition="OC1",
            compliance=Compliance.Compliant,
            altered_criteria=("thr_P_mxe_before of [GridCode]",),
        )
    ]

    pcs_cell = create_map(summary_list)[0][1]

    assert "Not a conformity check" in pcs_cell
    assert r"thr\_P\_mxe\_before of [GridCode]" in pcs_cell


def test_create_map_repeated_altered_criteria_reuse_the_note():
    entry = dict(
        producer_name="dummy",
        benchmark="BenchmarkA",
        operating_condition="OC1",
        compliance=Compliance.Compliant,
        altered_criteria=("u_fault of [PCS_RTE-I6.GridVoltageDip.Qzero.Model]",),
    )
    summary_list = [DummySummary(pcs="PCS1", **entry), DummySummary(pcs="PCS2", **entry)]

    first, second = (row[1] for row in create_map(summary_list))

    assert first.count(r"\footnote{") == 1
    assert second.endswith(r"\footnotemark[\value{footnote}]")


def test_create_map_leaves_an_untouched_pcs_unmarked():
    summary_list = [
        DummySummary(
            producer_name="dummy",
            pcs="PCS1",
            benchmark="BenchmarkA",
            operating_condition="OC1",
            compliance=Compliance.Compliant,
        )
    ]

    assert create_map(summary_list)[0][1] == "PCS1"
