from dycov.model.compliance import Compliance
from tests.dycov.utils import PERFORMANCE, execute_tool


def test_perf_sm_model(dynawo_latest):
    compliance = execute_tool(
        f"{PERFORMANCE}/SingleAux/GeneratorSynchronousFourWindingsTGov1SexsPss2a/Dynawo",
        None,
        None,
    )
    assert [
        Compliance.NonCompliant,  # 0
        Compliance.NonCompliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.FailedSimulation,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
        Compliance.Compliant,  # 7
        Compliance.Compliant,  # 8
    ] == compliance


def test_perf_sm_complete(dynawo_latest):
    compliance = execute_tool(
        f"{PERFORMANCE}/SingleAuxI/GeneratorSynchronousFourWindingsTGov1SexsPss2a/Dynawo",
        f"{PERFORMANCE}/ProducerCurves/GeneratorSynchronous",
        None,
    )
    assert [
        Compliance.NonCompliant,  # 0
        Compliance.NonCompliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.FailedSimulation,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
        Compliance.Compliant,  # 7
        Compliance.Compliant,  # 8
    ] == compliance


def test_perf_ppm_model(dynawo_latest):
    compliance = execute_tool(f"{PERFORMANCE}/SingleAux/WECC4B/Dynawo", None, None)
    assert [
        Compliance.NonCompliant,  # 0
        Compliance.NonCompliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.FailedSimulation,  # 6
    ] == compliance


def test_perf_ppm_complete(dynawo_latest):
    compliance = execute_tool(
        f"{PERFORMANCE}/SingleAux/IECB2020/Dynawo",
        f"{PERFORMANCE}/ProducerCurves/Wind",
        None,
    )
    assert [
        Compliance.Compliant,  # 0
        Compliance.Compliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.FailedSimulation,  # 6
    ] == compliance
