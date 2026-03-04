from dycov.model.compliance import Compliance
from tests.dycov.utils import PERFORMANCE, execute_tool


def test_perf_sm_curves():
    compliance = execute_tool(None, PERFORMANCE / "ProducerCurves" / "GeneratorSynchronous", None)
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


def test_perf_ppm_curves():
    compliance = execute_tool(None, PERFORMANCE / "ProducerCurves" / "Wind", None)
    assert [
        Compliance.NonCompliant,  # 0
        Compliance.NonCompliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
    ] == compliance
