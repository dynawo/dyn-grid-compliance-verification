import shutil
from pathlib import Path

from dgcv.configuration.cfg import config
from dgcv.core.execution_parameters import Parameters
from dgcv.core.model_validation import ModelValidation
from dgcv.model.compliance import Compliance


def _execute_tool(producer_model, producer_curves, reference_curves):
    testpath = Path(__file__).resolve().parent
    output_dir = Path(__file__).resolve().parent / "tmp"
    output_dir.mkdir(exist_ok=True)

    try:
        config._default_config.set("Dynawo", "simulation_limit", "120")
        only_dtr = True
        if producer_model:
            if "SM" in producer_model:
                sim_type = 0
            elif "PPM" in producer_model:
                sim_type = 0
            else:
                sim_type = 1
        else:
            if "SM" in producer_curves:
                sim_type = 0
            elif "PPM" in producer_curves:
                sim_type = 0
            else:
                sim_type = 1

        ep = Parameters(
            Path(shutil.which("dynawo.sh")).resolve(),
            testpath / producer_model if producer_model else None,
            testpath / producer_curves if producer_curves else None,
            testpath / reference_curves if reference_curves else None,
            None,
            output_dir,
            only_dtr,
            sim_type,
        )
        md = ModelValidation(ep)

        compliance = md.validate(True)
        print(f"{compliance}")
    except Exception as e:
        compliance = str(e)
    finally:
        shutil.rmtree(output_dir)
        return compliance


def test_perf_sm_model():
    compliance = _execute_tool("../../examples/SM/Dynawo/SingleAux", None, None)
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
    compliance = _execute_tool(None, "../../examples/SM/ProducerCurves/", None)
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


def test_perf_sm_complete():
    compliance = _execute_tool(
        "../../examples/SM/Dynawo/SingleAuxI", "../../examples/SM/ProducerCurves/", None
    )
    assert [
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
    ] == compliance


def test_perf_ppm_model():
    compliance = _execute_tool("../../examples/PPM/Dynawo/SingleAux/WECC", None, None)
    assert [
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.FailedSimulation,
    ] == compliance


def test_perf_ppm_curves():
    compliance = _execute_tool(None, "../../examples/PPM/ProducerCurves/", None)
    assert [
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
    ] == compliance


def test_perf_ppm_complete():
    compliance = _execute_tool(
        "../../examples/PPM/Dynawo/SingleAux/IEC2020",
        "../../examples/PPM/ProducerCurves/",
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


def test_model_validation_wecc_model():
    compliance = _execute_tool(
        "../../examples/Model/Wind/WECC/Dynawo",
        None,
        "../../examples/Model/Wind/WECC/ReferenceCurves",
    )
    assert [
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.NonCompliant,
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
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.FailedSimulation,
    ] == compliance


def test_model_validation_iec2015_model():
    compliance = _execute_tool(
        "../../examples/Model/Wind/IEC2015/Dynawo",
        None,
        "../../examples/Model/Wind/IEC2015/ReferenceCurves",
    )
    assert [
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.FailedSimulation,
    ] == compliance


def test_model_validation_iec2020_model():
    compliance = _execute_tool(
        "../../examples/Model/Wind/IEC2020/Dynawo",
        None,
        "../../examples/Model/Wind/IEC2020/ReferenceCurves",
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
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.FailedSimulation,
    ] == compliance


def test_model_validation_wecc_curves():
    compliance = _execute_tool(
        None,
        "../../examples/Model/Wind/WECC/ProducerCurves",
        "../../examples/Model/Wind/WECC/ReferenceCurves",
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
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
    ] == compliance


def test_model_validation_iec2015_curves():
    compliance = _execute_tool(
        None,
        "../../examples/Model/Wind/IEC2015/ProducerCurves",
        "../../examples/Model/Wind/IEC2015/ReferenceCurves",
    )
    assert [
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
    ] == compliance


def test_model_validation_iec2020_curves():
    compliance = _execute_tool(
        None,
        "../../examples/Model/Wind/IEC2020/ProducerCurves",
        "../../examples/Model/Wind/IEC2020/ReferenceCurves",
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
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
        Compliance.Compliant,
    ] == compliance


def test_model_validation_partial_reference():
    compliance = _execute_tool(
        "../../examples/Model/Wind/WECC/Dynawo",
        None,
        "../partial_reference_curves",
    )
    assert [
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
        Compliance.NonCompliant,
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
        Compliance.WithoutReferenceCurves,
    ] == compliance
