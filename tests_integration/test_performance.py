import pytest
from tests.dycov.utils import PERFORMANCE, execute_tool

from dycov.model.compliance import Compliance


def test_perf_sm_dynawo_model():
    compliance = execute_tool(
        PERFORMANCE / "SingleAux" / "GeneratorSynchronousFourWindingsTGov1SexsPss2a" / "Dynawo",
        None,
        None,
    )
    assert [
        Compliance.NonCompliant,  # 0
        Compliance.NonCompliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.NonCompliant,  # 6
        Compliance.Compliant,  # 7
        Compliance.NonCompliant,  # 8
    ] == compliance


def test_perf_sm_complete():
    compliance = execute_tool(
        PERFORMANCE / "SingleAuxI" / "GeneratorSynchronousFourWindingsTGov1SexsPss2a" / "Dynawo",
        PERFORMANCE / "ProducerCurves" / "SM",
        None,
    )

    if isinstance(compliance, str) and "Validation skipped" in compliance:
        pytest.skip("Validation skipped: DYNAWOPATH not set and dynawo.sh not found.")

    assert [
        Compliance.NonCompliant,  # 0
        Compliance.NonCompliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.NonCompliant,  # 6
        Compliance.Compliant,  # 7
        Compliance.NonCompliant,  # 8
    ] == compliance


def test_perf_ppm_dynawo_model():
    compliance = execute_tool(PERFORMANCE / "SingleAux" / "WECC4B" / "Dynawo", None, None)
    assert [
        Compliance.Compliant,  # 0
        Compliance.NonCompliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.NonCompliant,  # 6
    ] == compliance


def test_perf_ppm_curves():
    compliance = execute_tool(None, PERFORMANCE / "ProducerCurves" / "PPM", None)

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
    ] == compliance


def test_perf_ppm_complete():
    compliance = execute_tool(
        PERFORMANCE / "SingleAux" / "IECB2020" / "Dynawo",
        PERFORMANCE / "ProducerCurves" / "PPM",
        None,
    )

    if isinstance(compliance, str) and "Validation skipped" in compliance:
        pytest.skip("Validation skipped: DYNAWOPATH not set and dynawo.sh not found.")

    assert [
        Compliance.Compliant,  # 0
        Compliance.Compliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.NonCompliant,  # 5
        Compliance.NonCompliant,  # 6
    ] == compliance
