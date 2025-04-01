import shutil
from pathlib import Path

import pytest

from dycov.configuration.cfg import config
from dycov.core.execution_parameters import Parameters
from dycov.core.validation import Validation
from dycov.model.compliance import Compliance

PERFORMANCE = "../../examples/Performance"
MODEL = "../../examples/Model"
RESOURCES = "../resources"


def _execute_tool(producer_model_path, producer_curves_path, reference_curves_path):
    testpath = Path(__file__).resolve().parent
    output_dir = Path(__file__).resolve().parent / "tmp"
    output_dir.mkdir(exist_ok=True)
    assert output_dir.exists()
    if producer_model_path:
        assert (testpath / producer_model_path).exists()
    if producer_curves_path:
        assert (testpath / producer_curves_path).exists()
    if reference_curves_path:
        assert (testpath / reference_curves_path).exists()

    try:
        only_dtr = True
        if producer_model_path:
            if "Performance" in producer_model_path:
                sim_type = 0
            else:
                sim_type = 1
        else:
            if "Performance" in producer_curves_path:
                sim_type = 0
            else:
                sim_type = 1

        ep = Parameters(
            Path(shutil.which("dynawo.sh")).resolve() if shutil.which("dynawo.sh") else None,
            testpath / producer_model_path if producer_model_path else None,
            testpath / producer_curves_path if producer_curves_path else None,
            testpath / reference_curves_path if reference_curves_path else None,
            None,
            output_dir,
            only_dtr,
            sim_type,
        )
        md = Validation(ep)

        compliance = md.validate(True)
    except Exception as e:
        compliance = str(e)
    finally:
        shutil.rmtree(output_dir)
        return compliance


@pytest.mark.skipif(not shutil.which("dynawo.sh"), reason="Dynawo not installed")
def test_perf_sm_model():
    compliance = _execute_tool(
        f"{PERFORMANCE}/SingleAux/GeneratorSynchronousFourWindingsTGov1SexsPss2a/Dynawo",
        None,
        None,
    )
    assert [
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
    ] == compliance


def test_perf_sm_curves():
    compliance = _execute_tool(None, f"{PERFORMANCE}/ProducerCurves/GeneratorSynchronous/", None)
    assert [
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
    ] == compliance


@pytest.mark.skipif(not shutil.which("dynawo.sh"), reason="Dynawo not installed")
def test_perf_sm_complete():
    compliance = _execute_tool(
        f"{PERFORMANCE}/SingleAuxI/GeneratorSynchronousFourWindingsTGov1SexsPss2a/Dynawo",
        f"{PERFORMANCE}/ProducerCurves/GeneratorSynchronous",
        None,
    )
    assert [
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
    ] == compliance


@pytest.mark.skipif(not shutil.which("dynawo.sh"), reason="Dynawo not installed")
def test_perf_ppm_model():
    compliance = _execute_tool(f"{PERFORMANCE}/SingleAux/WECCB/Dynawo", None, None)
    assert [
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.SimulationTimeOut,
    ] == compliance


def test_perf_ppm_curves():
    compliance = _execute_tool(None, f"{PERFORMANCE}/ProducerCurves/Wind", None)
    assert [
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
    ] == compliance


@pytest.mark.skipif(not shutil.which("dynawo.sh"), reason="Dynawo not installed")
def test_perf_ppm_complete():
    compliance = _execute_tool(
        f"{PERFORMANCE}/SingleAux/IECB2020/Dynawo",
        f"{PERFORMANCE}/ProducerCurves/Wind",
        None,
    )
    assert [
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.FailedSimulation,
    ] == compliance


@pytest.mark.skipif(not shutil.which("dynawo.sh"), reason="Dynawo not installed")
def test_model_validation_wecca_model():
    compliance = _execute_tool(
        f"{MODEL}/Wind/WECCA/Dynawo",
        None,
        f"{MODEL}/Wind/WECCA/ReferenceCurves",
    )
    assert [
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.NonCompliant,
        Compliance.InvalidTest,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.SimulationTimeOut,
    ] == compliance


def test_model_validation_iec2015_curves():
    compliance = _execute_tool(
        None,
        f"{MODEL}/Wind/IECB2015/ProducerCurves",
        f"{MODEL}/Wind/IECB2015/ReferenceCurves",
    )
    assert [
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
    ] == compliance


@pytest.mark.skipif(not shutil.which("dynawo.sh"), reason="Dynawo not installed")
def test_model_validation_partial_reference():
    compliance = _execute_tool(
        f"{MODEL}/Wind/WECCB/Dynawo",
        None,
        f"{RESOURCES}/partial_reference_curves",
    )
    assert [
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.SimulationTimeOut,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.WithoutReferenceCurves,
        Compliance.NonCompliant,
        Compliance.WithoutReferenceCurves,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.WithoutReferenceCurves,
        Compliance.WithoutReferenceCurves,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.SimulationTimeOut,
    ] == compliance
