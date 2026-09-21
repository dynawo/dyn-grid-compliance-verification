from tests.dycov.utils import MODEL, execute_tool

from dycov.model.compliance import Compliance

RESOURCES = "./resources"


def test_model_validation_ppm_producer_curves():
    compliance = execute_tool(
        None,
        MODEL / "ProducerCurves" / "PPM",
        MODEL / "Wind" / "IECB2015" / "ReferenceCurves",
    )
    assert [
        Compliance.InvalidTest,  # 0
        Compliance.InvalidTest,  # 1
        Compliance.InvalidTest,  # 2
        Compliance.InvalidTest,  # 3
        Compliance.InvalidTest,  # 4
        Compliance.InvalidTest,  # 5
        Compliance.InvalidTest,  # 6
        Compliance.InvalidTest,  # 7
        Compliance.InvalidTest,  # 8
        Compliance.WithoutCurves,  # 9
        Compliance.Compliant,  # 10
        Compliance.Compliant,  # 11
        Compliance.Compliant,  # 12
        Compliance.Compliant,  # 13
        Compliance.Compliant,  # 14
        Compliance.Compliant,  # 15
        Compliance.WithoutCurves,  # 16
        Compliance.WithoutCurves,  # 17
        Compliance.Compliant,  # 18
        Compliance.Compliant,  # 19
        Compliance.Compliant,  # 20
        Compliance.Compliant,  # 21
        Compliance.NonCompliant,  # 22
        Compliance.Compliant,  # 23
    ] == compliance


def test_model_validation_bess_producer_curves():
    compliance = execute_tool(
        None,
        MODEL / "ProducerCurves" / "BESS",
        MODEL / "BESS" / "WECC" / "ReferenceCurves",
    )
    assert [
        Compliance.InvalidTest,  # 0
        Compliance.InvalidTest,  # 1
        Compliance.InvalidTest,  # 2
        Compliance.InvalidTest,  # 3
        Compliance.InvalidTest,  # 4
        Compliance.InvalidTest,  # 5
        Compliance.InvalidTest,  # 6
        Compliance.InvalidTest,  # 7
        Compliance.InvalidTest,  # 8
        Compliance.InvalidTest,  # 9
        Compliance.InvalidTest,  # 10
        Compliance.InvalidTest,  # 11
        Compliance.InvalidTest,  # 12
        Compliance.InvalidTest,  # 13
        Compliance.InvalidTest,  # 14
        Compliance.InvalidTest,  # 15
        Compliance.WithoutCurves,  # 16
        Compliance.InvalidTest,  # 17
        Compliance.InvalidTest,  # 18
        Compliance.WithoutCurves,  # 19
        Compliance.Compliant,  # 20
        Compliance.Compliant,  # 21
        Compliance.Compliant,  # 22
        Compliance.Compliant,  # 23
        Compliance.Compliant,  # 24
        Compliance.Compliant,  # 25
        Compliance.Compliant,  # 26
        Compliance.Compliant,  # 27
        Compliance.Compliant,  # 28
        Compliance.Compliant,  # 29
        Compliance.Compliant,  # 30
        Compliance.Compliant,  # 31
        Compliance.WithoutCurves,  # 32
        Compliance.WithoutCurves,  # 33
        Compliance.WithoutCurves,  # 34
        Compliance.WithoutCurves,  # 35
        Compliance.Compliant,  # 36
        Compliance.Compliant,  # 37
        Compliance.Compliant,  # 38
        Compliance.Compliant,  # 39
        Compliance.Compliant,  # 40
        Compliance.Compliant,  # 41
        Compliance.Compliant,  # 42
        Compliance.Compliant,  # 43
        Compliance.NonCompliant,  # 44
        Compliance.NonCompliant,  # 45
        Compliance.NonCompliant,  # 46
        Compliance.Compliant,  # 47
    ] == compliance
