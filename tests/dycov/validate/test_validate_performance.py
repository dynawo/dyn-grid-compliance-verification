from dycov.model.compliance import Compliance
from tests.dycov.utils import PERFORMANCE, execute_tool


def test_perf_sm_producer_curves():
    compliance = execute_tool(None, PERFORMANCE / "ProducerCurves" / "SM", None)
    assert [
        Compliance.NonCompliant,  # 0
        Compliance.NonCompliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
        Compliance.Compliant,  # 7
        Compliance.Compliant,  # 8
    ] == compliance


def test_perf_ppm_producer_curves():
    compliance = execute_tool(None, PERFORMANCE / "ProducerCurves" / "PPM", None)
    assert [
        Compliance.Compliant,  # 0
        Compliance.Compliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
    ] == compliance


def test_perf_bess_producer_curves():
    compliance = execute_tool(None, PERFORMANCE / "ProducerCurves" / "BESS", None)
    assert [
        Compliance.Compliant,  # 0
        Compliance.NonCompliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.NonCompliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
        Compliance.NonCompliant,  # 7
        Compliance.NonCompliant,  # 8
        Compliance.Compliant,  # 9
        Compliance.NonCompliant,  # 10
        Compliance.Compliant,  # 11
        Compliance.Compliant,  # 12
        Compliance.Compliant,  # 13
    ] == compliance
