from pathlib import Path

from dycov.model.compliance import Compliance
from tests.dycov.utils import MODEL, execute_tool

RESOURCES = Path(__file__).resolve().parent / "resources"


def test_model_validation_ppm_dynawo_model(dynawo_latest):
    compliance = execute_tool(
        MODEL / "Wind" / "WECC4A1" / "Dynawo",
        None,
        MODEL / "Wind" / "WECC4A1" / "ReferenceCurves",
    )
    assert [
        Compliance.Compliant,  # 0
        Compliance.Compliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
        Compliance.Compliant,  # 7
        Compliance.NonCompliant,  # 8
        Compliance.Compliant,  # 9
        Compliance.InvalidTest,  # 10
        Compliance.NonCompliant,  # 11
        Compliance.NonCompliant,  # 12
        Compliance.NonCompliant,  # 13
        Compliance.NonCompliant,  # 14
        Compliance.Compliant,  # 15
        Compliance.Compliant,  # 16
        Compliance.Compliant,  # 17
        Compliance.NonCompliant,  # 18
        Compliance.Compliant,  # 19
        Compliance.NonCompliant,  # 20
        Compliance.Compliant,  # 21
        Compliance.Compliant,  # 22
        Compliance.FailedSimulation,  # 23
    ] == compliance


def test_model_validation_ppm_dynawo_model_partial_reference(dynawo_latest):
    compliance = execute_tool(
        MODEL / "Wind" / "WECC4B" / "Dynawo",
        None,
        RESOURCES / "partial_reference_curves",
    )
    assert [
        Compliance.Compliant,  # 0
        Compliance.Compliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
        Compliance.Compliant,  # 7
        Compliance.WithoutReferenceCurves,  # 8
        Compliance.Compliant,  # 9
        Compliance.WithoutReferenceCurves,  # 10
        Compliance.NonCompliant,  # 11
        Compliance.NonCompliant,  # 12
        Compliance.NonCompliant,  # 13
        Compliance.NonCompliant,  # 14
        Compliance.Compliant,  # 15
        Compliance.WithoutReferenceCurves,  # 16
        Compliance.WithoutReferenceCurves,  # 17
        Compliance.NonCompliant,  # 18
        Compliance.Compliant,  # 19
        Compliance.NonCompliant,  # 20
        Compliance.Compliant,  # 21
        Compliance.Compliant,  # 22
        Compliance.WithoutReferenceCurves,  # 23
    ] == compliance
