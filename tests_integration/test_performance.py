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
        Compliance.NonCompliant,  # PCS_RTE-I2.USetPointStep.AReactance
        Compliance.NonCompliant,  # PCS_RTE-I2.USetPointStep.BReactance
        Compliance.Compliant,  # PCS_RTE-I3.LineTrip.2BReactance
        Compliance.Compliant,  # PCS_RTE-I4.ThreePhaseFault.TransientBolted
        Compliance.Compliant,  # PCS_RTE-I6.GridVoltageDip.Qzero
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMax
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMin
        Compliance.Compliant,  # PCS_RTE-I8.LoadShedDisturbance.PmaxQzero
        Compliance.NonCompliant,  # PCS_RTE-I10.Islanding.DeltaP10DeltaQ4
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
        Compliance.NonCompliant,  # PCS_RTE-I2.USetPointStep.AReactance
        Compliance.NonCompliant,  # PCS_RTE-I2.USetPointStep.BReactance
        Compliance.Compliant,  # PCS_RTE-I3.LineTrip.2BReactance
        Compliance.Compliant,  # PCS_RTE-I4.ThreePhaseFault.TransientBolted
        Compliance.Compliant,  # PCS_RTE-I6.GridVoltageDip.Qzero
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMax
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMin
        Compliance.Compliant,  # PCS_RTE-I8.LoadShedDisturbance.PmaxQzero
        Compliance.NonCompliant,  # PCS_RTE-I10.Islanding.DeltaP10DeltaQ4
    ] == compliance


def test_perf_ppm_dynawo_model():
    compliance = execute_tool(PERFORMANCE / "SingleAux" / "WECC4B" / "Dynawo", None, None)
    assert [
        Compliance.Compliant,  # PCS_RTE-I2.USetPointStep.AReactance
        Compliance.NonCompliant,  # PCS_RTE-I2.USetPointStep.BReactance
        Compliance.Compliant,  # PCS_RTE-I5.ThreePhaseFault.TransientBolted
        Compliance.Compliant,  # PCS_RTE-I6.GridVoltageDip.Qzero
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMax
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMin
        Compliance.NonCompliant,  # PCS_RTE-I10.Islanding.DeltaP10DeltaQ4
    ] == compliance


def test_perf_ppm_curves():
    compliance = execute_tool(None, PERFORMANCE / "ProducerCurves" / "PPM", None)

    if isinstance(compliance, str) and "Validation skipped" in compliance:
        pytest.skip("Validation skipped: DYNAWOPATH not set and dynawo.sh not found.")

    assert [
        Compliance.Compliant,  # PCS_RTE-I2.USetPointStep.AReactance
        Compliance.Compliant,  # PCS_RTE-I2.USetPointStep.BReactance
        Compliance.Compliant,  # PCS_RTE-I5.ThreePhaseFault.TransientBolted
        Compliance.Compliant,  # PCS_RTE-I6.GridVoltageDip.Qzero
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMax
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMin
        Compliance.Compliant,  # PCS_RTE-I10.Islanding.DeltaP10DeltaQ4
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
        Compliance.Compliant,  # PCS_RTE-I2.USetPointStep.AReactance
        Compliance.Compliant,  # PCS_RTE-I2.USetPointStep.BReactance
        Compliance.Compliant,  # PCS_RTE-I5.ThreePhaseFault.TransientBolted
        Compliance.Compliant,  # PCS_RTE-I6.GridVoltageDip.Qzero
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMax
        Compliance.NonCompliant,  # PCS_RTE-I7.GridVoltageSwell.QMin
        Compliance.NonCompliant,  # PCS_RTE-I10.Islanding.DeltaP10DeltaQ4
    ] == compliance
