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
        Compliance.Compliant,  # 0
        Compliance.Compliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
        Compliance.Compliant,  # 7
        Compliance.Compliant,  # 8
        Compliance.WithoutProducerCurves,  # 9
        Compliance.Compliant,  # 10
        Compliance.Compliant,  # 11
        Compliance.Compliant,  # 12
        Compliance.Compliant,  # 13
        Compliance.Compliant,  # 14
        Compliance.Compliant,  # 15
        Compliance.WithoutProducerCurves,  # 16
        Compliance.WithoutProducerCurves,  # 17
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
        Compliance.Compliant,  # 10
        Compliance.Compliant,  # 11
        Compliance.Compliant,  # 12
        Compliance.Compliant,  # 13
        Compliance.Compliant,  # 14
        Compliance.Compliant,  # 15
        Compliance.WithoutProducerCurves,  # 16
        Compliance.Compliant,  # 17
        Compliance.Compliant,  # 18
        Compliance.WithoutProducerCurves,  # 19
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
        Compliance.WithoutProducerCurves,  # 32
        Compliance.WithoutProducerCurves,  # 33
        Compliance.WithoutProducerCurves,  # 34
        Compliance.WithoutProducerCurves,  # 35
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
        Compliance.Compliant,  # 46
        Compliance.InvalidTest,  # 47
    ] == compliance
