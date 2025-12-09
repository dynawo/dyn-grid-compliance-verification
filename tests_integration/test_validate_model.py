import pytest

from dycov.model.compliance import Compliance
from tests_integration.utils import MODEL, RESOURCES, execute_tool


def test_model_validation_wecca_model():
    compliance = execute_tool(
        f"{MODEL}/Wind/WECCA/Dynawo",
        None,
        f"{MODEL}/Wind/WECCA/ReferenceCurves",
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
        Compliance.Compliant,  # 7
        Compliance.Compliant,  # 8
        Compliance.Compliant,  # 9
        Compliance.InvalidTest,  # 10
        Compliance.NonCompliant,  # 11
        Compliance.Compliant,  # 12
        Compliance.NonCompliant,  # 13
        Compliance.NonCompliant,  # 14
        Compliance.Compliant,  # 15
        Compliance.Compliant,  # 16
        Compliance.Compliant,  # 17
        Compliance.NonCompliant,  # 18
        Compliance.Compliant,  # 19
        Compliance.Compliant,  # 20
        Compliance.Compliant,  # 21
        Compliance.Compliant,  # 22
        Compliance.SimulationTimeOut,  # 23
    ] == compliance


def test_model_validation_iec2015_curves():
    compliance = execute_tool(
        None,
        f"{MODEL}/Wind/IECB2015/ProducerCurves",
        f"{MODEL}/Wind/IECB2015/ReferenceCurves",
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
        Compliance.Compliant,  # 7
        Compliance.Compliant,  # 8
        Compliance.Compliant,  # 9
        Compliance.InvalidTest,  # 10
        Compliance.Compliant,  # 11
        Compliance.Compliant,  # 12
        Compliance.Compliant,  # 13
        Compliance.Compliant,  # 14
        Compliance.Compliant,  # 15
        Compliance.Compliant,  # 16
        Compliance.Compliant,  # 17
        Compliance.Compliant,  # 18
        Compliance.Compliant,  # 19
        Compliance.Compliant,  # 20
        Compliance.Compliant,  # 21
        Compliance.Compliant,  # 22
        Compliance.Compliant,  # 23
    ] == compliance


def test_model_validation_partial_reference():
    compliance = execute_tool(
        f"{MODEL}/Wind/WECCB/Dynawo",
        None,
        f"{RESOURCES}/partial_reference_curves",
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
        Compliance.NonCompliant,  # 7
        Compliance.WithoutReferenceCurves,  # 8
        Compliance.Compliant,  # 9
        Compliance.WithoutReferenceCurves,  # 10
        Compliance.NonCompliant,  # 11
        Compliance.Compliant,  # 12
        Compliance.NonCompliant,  # 13
        Compliance.NonCompliant,  # 14
        Compliance.NonCompliant,  # 15
        Compliance.WithoutReferenceCurves,  # 16
        Compliance.WithoutReferenceCurves,  # 17
        Compliance.NonCompliant,  # 18
        Compliance.Compliant,  # 19
        Compliance.Compliant,  # 20
        Compliance.Compliant,  # 21
        Compliance.Compliant,  # 22
        Compliance.WithoutReferenceCurves,  # 23
    ] == compliance
