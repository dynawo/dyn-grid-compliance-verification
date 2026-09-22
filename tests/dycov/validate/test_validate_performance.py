from tests.dycov.utils import PERFORMANCE, execute_tool

from dycov.model.compliance import Compliance


def test_perf_sm_producer_curves():
    compliance = execute_tool(None, PERFORMANCE / "ProducerCurves" / "SM", None)
    assert [
        Compliance.NonCompliant,  # PCS_RTE-I2.USetPointStep.AReactance
        Compliance.NonCompliant,  # PCS_RTE-I2.USetPointStep.BReactance
        Compliance.Compliant,  # PCS_RTE-I3.LineTrip.2BReactance
        Compliance.Compliant,  # PCS_RTE-I4.ThreePhaseFault.TransientBolted
        Compliance.Compliant,  # PCS_RTE-I6.GridVoltageDip.Qzero
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMax
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMin
        Compliance.Compliant,  # PCS_RTE-I8.LoadShedDisturbance.PmaxQzero
        Compliance.Compliant,  # PCS_RTE-I10.Islanding.DeltaP10DeltaQ4
    ] == compliance


def test_perf_ppm_producer_curves():
    compliance = execute_tool(None, PERFORMANCE / "ProducerCurves" / "PPM", None)
    assert [
        Compliance.Compliant,  # PCS_RTE-I2.USetPointStep.AReactance
        Compliance.Compliant,  # PCS_RTE-I2.USetPointStep.BReactance
        Compliance.Compliant,  # PCS_RTE-I5.ThreePhaseFault.TransientBolted
        Compliance.Compliant,  # PCS_RTE-I6.GridVoltageDip.Qzero
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMax
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMin
        Compliance.Compliant,  # PCS_RTE-I10.Islanding.DeltaP10DeltaQ4
    ] == compliance


def test_perf_bess_producer_curves():
    compliance = execute_tool(None, PERFORMANCE / "ProducerCurves" / "BESS", None)
    assert [
        Compliance.Compliant,  # PCS_RTE-I2.USetPointStep.AReactanceInjection
        Compliance.NonCompliant,  # PCS_RTE-I2.USetPointStep.BReactanceInjection
        Compliance.Compliant,  # PCS_RTE-I2.USetPointStep.AReactanceConsumption
        Compliance.NonCompliant,  # PCS_RTE-I2.USetPointStep.BReactanceConsumption
        Compliance.Compliant,  # PCS_RTE-I5.ThreePhaseFault.TransientBoltedInjection
        Compliance.Compliant,  # PCS_RTE-I5.ThreePhaseFault.TransientBoltedConsumption
        Compliance.Compliant,  # PCS_RTE-I6.GridVoltageDip.QzeroInjection
        Compliance.NonCompliant,  # PCS_RTE-I6.GridVoltageDip.QzeroConsumption
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMaxInjection
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMinInjection
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMaxConsumption
        Compliance.Compliant,  # PCS_RTE-I7.GridVoltageSwell.QMinConsumption
        Compliance.Compliant,  # PCS_RTE-I10.Islanding.DeltaP10DeltaQ4Injection
        Compliance.Compliant,  # PCS_RTE-I10.Islanding.DeltaP10DeltaQ4Consumption
    ] == compliance
