from pathlib import Path

import pytest
from tests.dycov.utils import MODEL, execute_tool

from dycov.model.compliance import Compliance

RESOURCES = Path(__file__).resolve().parent / "resources"


def test_model_validation_ppm_dynawo_model():
    compliance = execute_tool(
        MODEL / "Wind" / "WECC4A" / "Dynawo",
        None,
        MODEL / "Wind" / "WECC4A" / "ReferenceCurves",
    )

    if isinstance(compliance, str) and "Validation skipped" in compliance:
        pytest.skip("Validation skipped: DYNAWOPATH not set and dynawo.sh not found.")

    assert [
        Compliance.Compliant,  # 0
        Compliance.Compliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
        Compliance.NotApplicableTest,  # 7
        Compliance.Compliant,  # 8
        Compliance.NotApplicableTest,  # 9
        Compliance.NonCompliant,  # 10
        Compliance.Compliant,  # 11
        Compliance.NonCompliant,  # 12
        Compliance.NonCompliant,  # 13
        Compliance.Compliant,  # 14
        Compliance.Compliant,  # 15
        Compliance.Compliant,  # 16
        Compliance.Compliant,  # 17
        Compliance.Compliant,  # 18
        Compliance.Compliant,  # 19
        Compliance.NonCompliant,  # 20
        Compliance.Compliant,  # 21
        Compliance.NonCompliant,  # 22
        Compliance.NonCompliant,  # 23
    ] == compliance


def test_model_validation_bess_dynawo_model():
    compliance = execute_tool(
        MODEL / "BESS" / "WECC" / "Dynawo",
        None,
        MODEL / "BESS" / "WECC" / "ReferenceCurves",
    )

    if isinstance(compliance, str) and "Validation skipped" in compliance:
        pytest.skip("Validation skipped: DYNAWOPATH not set and dynawo.sh not found.")

    assert [
        Compliance.NonCompliant,  # 0
        Compliance.NonCompliant,  # 1
        Compliance.NonCompliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
        Compliance.NonCompliant,  # 7
        Compliance.NonCompliant,  # 8
        Compliance.NonCompliant,  # 9
        Compliance.Compliant,  # 10
        Compliance.Compliant,  # 11
        Compliance.Compliant,  # 12
        Compliance.Compliant,  # 13
        Compliance.NotApplicableTest,  # 14
        Compliance.Compliant,  # 15
        Compliance.NotApplicableTest,  # 16
        Compliance.NotApplicableTest,  # 17
        Compliance.Compliant,  # 18
        Compliance.NotApplicableTest,  # 19
        Compliance.NonCompliant,  # 20
        Compliance.Compliant,  # 21
        Compliance.NonCompliant,  # 22
        Compliance.Compliant,  # 23
        Compliance.NonCompliant,  # 24
        Compliance.NonCompliant,  # 25
        Compliance.NonCompliant,  # 26
        Compliance.NonCompliant,  # 27
        Compliance.Compliant,  # 28
        Compliance.Compliant,  # 29
        Compliance.Compliant,  # 30
        Compliance.Compliant,  # 31
        Compliance.Compliant,  # 32
        Compliance.NonCompliant,  # 33
        Compliance.Compliant,  # 34
        Compliance.Compliant,  # 35
        Compliance.Compliant,  # 36
        Compliance.Compliant,  # 37
        Compliance.Compliant,  # 38
        Compliance.Compliant,  # 39
        Compliance.NonCompliant,  # 40
        Compliance.Compliant,  # 41
        Compliance.Compliant,  # 42
        Compliance.Compliant,  # 43
        Compliance.NonCompliant,  # 44
        Compliance.NonCompliant,  # 45
        Compliance.NonCompliant,  # 46
        Compliance.InvalidTest,  # 47
    ] == compliance
