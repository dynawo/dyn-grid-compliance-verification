import shutil
from pathlib import Path

import pytest

from dycov.core.execution_parameters import Parameters
from dycov.core.global_variables import ELECTRIC_PERFORMANCE, MODEL_VALIDATION
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
                sim_type = ELECTRIC_PERFORMANCE
            else:
                sim_type = MODEL_VALIDATION
        else:
            if "Performance" in producer_curves_path:
                sim_type = ELECTRIC_PERFORMANCE
            else:
                sim_type = MODEL_VALIDATION

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
        md.set_testing(True)
        compliance = md.validate(use_parallel=False, num_processes=4)
    except Exception as e:
        compliance = str(e)
    finally:
        shutil.rmtree(output_dir)
        print(compliance)
        return compliance


# @pytest.mark.skipif(not shutil.which("dynawo.sh"), reason="Dynawo not installed")
@pytest.mark.skip
def test_perf_sm_model():
    compliance = _execute_tool(
        f"{PERFORMANCE}/SingleAux/GeneratorSynchronousFourWindingsTGov1SexsPss2a/Dynawo",
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
        Compliance.Compliant,  # 6
        Compliance.Compliant,  # 7
        Compliance.Compliant,  # 8
    ] == compliance


def test_perf_sm_curves():
    compliance = _execute_tool(None, f"{PERFORMANCE}/ProducerCurves/GeneratorSynchronous/", None)
    assert [
        Compliance.Compliant,  # 0
        Compliance.NonCompliant,  # 1
        Compliance.NonCompliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
        Compliance.Compliant,  # 7
        Compliance.Compliant,  # 8
    ] == compliance


# @pytest.mark.skipif(not shutil.which("dynawo.sh"), reason="Dynawo not installed")
@pytest.mark.skip
def test_perf_sm_complete():
    compliance = _execute_tool(
        f"{PERFORMANCE}/SingleAuxI/GeneratorSynchronousFourWindingsTGov1SexsPss2a/Dynawo",
        f"{PERFORMANCE}/ProducerCurves/GeneratorSynchronous",
        None,
    )
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


# @pytest.mark.skipif(not shutil.which("dynawo.sh"), reason="Dynawo not installed")
@pytest.mark.skip
def test_perf_ppm_model():
    compliance = _execute_tool(f"{PERFORMANCE}/SingleAux/WECCB/Dynawo", None, None)
    assert [
        Compliance.NonCompliant,  # 0
        Compliance.NonCompliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.SimulationTimeOut,  # 6
    ] == compliance


def test_perf_ppm_curves():
    compliance = _execute_tool(None, f"{PERFORMANCE}/ProducerCurves/Wind", None)
    assert [
        Compliance.Compliant,  # 0
        Compliance.NonCompliant,  # 1
        Compliance.NonCompliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
    ] == compliance


# @pytest.mark.skipif(not shutil.which("dynawo.sh"), reason="Dynawo not installed")
@pytest.mark.skip
def test_perf_ppm_complete():
    compliance = _execute_tool(
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


# @pytest.mark.skipif(not shutil.which("dynawo.sh"), reason="Dynawo not installed")
@pytest.mark.skip
def test_model_validation_wecca_model():
    compliance = _execute_tool(
        f"{MODEL}/Wind/WECCA/Dynawo",
        None,
        f"{MODEL}/Wind/WECCA/ReferenceCurves",
    )
    assert [
        Compliance.Compliant,  # 0
        Compliance.Compliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
        Compliance.NonCompliant,  # 7
        Compliance.Compliant,  # 8
        Compliance.NonCompliant,  # 9
        Compliance.InvalidTest,  # 10
        Compliance.NonCompliant,  # 11
        Compliance.NonCompliant,  # 12
        Compliance.NonCompliant,  # 13
        Compliance.NonCompliant,  # 14
        Compliance.Compliant,  # 15
        Compliance.NonCompliant,  # 16
        Compliance.Compliant,  # 17
        Compliance.Compliant,  # 18
        Compliance.Compliant,  # 19
        Compliance.NonCompliant,  # 20
        Compliance.Compliant,  # 21
        Compliance.Compliant,  # 22
        Compliance.FailedSimulation,  # 23
    ] == compliance


def test_model_validation_iec2015_curves():
    compliance = _execute_tool(
        None,
        f"{MODEL}/Wind/IECB2015/ProducerCurves",
        f"{MODEL}/Wind/IECB2015/ReferenceCurves",
    )
    assert [
        Compliance.Compliant,  # 0
        Compliance.Compliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.NonCompliant,  # 6
        Compliance.NonCompliant,  # 7
        Compliance.NonCompliant,  # 8
        Compliance.NonCompliant,  # 9
        Compliance.NonCompliant,  # 10
        Compliance.NonCompliant,  # 11
        Compliance.NonCompliant,  # 12
        Compliance.NonCompliant,  # 13
        Compliance.NonCompliant,  # 14
        Compliance.Compliant,  # 15
        Compliance.Compliant,  # 16
        Compliance.NonCompliant,  # 17
        Compliance.Compliant,  # 18
        Compliance.Compliant,  # 19
        Compliance.Compliant,  # 20
        Compliance.Compliant,  # 21
        Compliance.Compliant,  # 22
        Compliance.Compliant,  # 23
    ] == compliance


# @pytest.mark.skipif(not shutil.which("dynawo.sh"), reason="Dynawo not installed")
@pytest.mark.skip
def test_model_validation_partial_reference():
    compliance = _execute_tool(
        f"{MODEL}/Wind/WECCB/Dynawo",
        None,
        f"{RESOURCES}/partial_reference_curves",
    )
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
        Compliance.NonCompliant,  # 9
        Compliance.WithoutReferenceCurves,  # 10
        Compliance.NonCompliant,  # 11
        Compliance.NonCompliant,  # 12
        Compliance.NonCompliant,  # 13
        Compliance.NonCompliant,  # 14
        Compliance.NonCompliant,  # 15
        Compliance.WithoutReferenceCurves,  # 16
        Compliance.WithoutReferenceCurves,  # 17
        Compliance.Compliant,  # 18
        Compliance.NonCompliant,  # 19
        Compliance.NonCompliant,  # 20
        Compliance.Compliant,  # 21
        Compliance.Compliant,  # 22
        Compliance.SimulationTimeOut,  # 23
    ] == compliance
