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
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR10
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3Qmin
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc500
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.PermanentBolted
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.PermanentHiZ
        Compliance.Compliant,  # PCS_RTE-I16z1.SetPointStep.Active
        Compliance.Compliant,  # PCS_RTE-I16z1.SetPointStep.Reactive
        Compliance.WithoutCurves,  # PCS_RTE-I16z1.SetPointStep.Voltage
        Compliance.Compliant,  # PCS_RTE-I16z1.GridVoltageStep.Rise
        Compliance.Compliant,  # PCS_RTE-I16z1.GridVoltageStep.Drop
        Compliance.Compliant,  # PCS_RTE-I16z3.USetPointStep.AReactance
        Compliance.Compliant,  # PCS_RTE-I16z3.USetPointStep.BReactance
        Compliance.Compliant,  # PCS_RTE-I16z3.PSetPointStep.Dec40
        Compliance.Compliant,  # PCS_RTE-I16z3.PSetPointStep.Inc40
        Compliance.WithoutCurves,  # PCS_RTE-I16z3.QSetPointStep.Inc10
        Compliance.WithoutCurves,  # PCS_RTE-I16z3.QSetPointStep.Dec20
        Compliance.Compliant,  # PCS_RTE-I16z3.ThreePhaseFault.TransientBolted
        Compliance.Compliant,  # PCS_RTE-I16z3.GridVoltageDip.Qzero
        Compliance.Compliant,  # PCS_RTE-I16z3.GridVoltageSwell.QMax
        Compliance.Compliant,  # PCS_RTE-I16z3.GridVoltageSwell.QMin
        Compliance.NonCompliant,  # PCS_RTE-I16z3.GridFreqRamp.W500mHz250ms
        Compliance.Compliant,  # PCS_RTE-I16z3.Islanding.DeltaP10DeltaQ4
        Compliance.Compliant,  # PCS_RTE-F16z1.PSetPointStep.Pmin
        Compliance.Compliant,  # PCS_RTE-F16z1.PSetPointStep.P50
        Compliance.Compliant,  # PCS_RTE-F16z1.PSetPointStep.Pmax
        Compliance.Compliant,  # PCS_RTE-F16z1.QSetPointStep.Pmin
        Compliance.Compliant,  # PCS_RTE-F16z1.QSetPointStep.P50
        Compliance.Compliant,  # PCS_RTE-F16z1.QSetPointStep.Pmax
        Compliance.Compliant,  # PCS_RTE-F16z3.PSetPointStep.Pmin
        Compliance.Compliant,  # PCS_RTE-F16z3.PSetPointStep.P50
        Compliance.Compliant,  # PCS_RTE-F16z3.PSetPointStep.Pmax
        Compliance.Compliant,  # PCS_RTE-F16z3.USetPointStep.Pmin
        Compliance.Compliant,  # PCS_RTE-F16z3.USetPointStep.P50
        Compliance.Compliant,  # PCS_RTE-F16z3.USetPointStep.Pmax
    ] == compliance


def test_model_validation_bess_producer_curves():
    compliance = execute_tool(
        None,
        MODEL / "ProducerCurves" / "BESS",
        MODEL / "BESS" / "WECC" / "ReferenceCurves",
    )
    assert [
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3Injection
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR10Injection
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3QminInjection
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800Injection
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc500Injection
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.PermanentBoltedInjection
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.PermanentHiZInjection
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3Consumption
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR10Consumption
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3QminConsumption
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800Consumption
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc500Consumption
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.PermanentBoltedConsumption
        Compliance.Compliant,  # PCS_RTE-I16z1.ThreePhaseFault.PermanentHiZConsumption
        Compliance.Compliant,  # PCS_RTE-I16z1.SetPointStep.ActiveInjection
        Compliance.Compliant,  # PCS_RTE-I16z1.SetPointStep.ReactiveInjection
        Compliance.WithoutCurves,  # PCS_RTE-I16z1.SetPointStep.VoltageInjection
        Compliance.Compliant,  # PCS_RTE-I16z1.SetPointStep.ActiveConsumption
        Compliance.Compliant,  # PCS_RTE-I16z1.SetPointStep.ReactiveConsumption
        Compliance.WithoutCurves,  # PCS_RTE-I16z1.SetPointStep.VoltageConsumption
        Compliance.Compliant,  # PCS_RTE-I16z1.GridVoltageStep.RiseInjection
        Compliance.Compliant,  # PCS_RTE-I16z1.GridVoltageStep.DropInjection
        Compliance.Compliant,  # PCS_RTE-I16z1.GridVoltageStep.RiseConsumption
        Compliance.Compliant,  # PCS_RTE-I16z1.GridVoltageStep.DropConsumption
        Compliance.Compliant,  # PCS_RTE-I16z3.USetPointStep.AReactanceInjection
        Compliance.Compliant,  # PCS_RTE-I16z3.USetPointStep.BReactanceInjection
        Compliance.Compliant,  # PCS_RTE-I16z3.USetPointStep.AReactanceConsumption
        Compliance.Compliant,  # PCS_RTE-I16z3.USetPointStep.BReactanceConsumption
        Compliance.Compliant,  # PCS_RTE-I16z3.PSetPointStep.Dec40Injection
        Compliance.Compliant,  # PCS_RTE-I16z3.PSetPointStep.Inc40Injection
        Compliance.Compliant,  # PCS_RTE-I16z3.PSetPointStep.Dec40Consumption
        Compliance.Compliant,  # PCS_RTE-I16z3.PSetPointStep.Inc40Consumption
        Compliance.WithoutCurves,  # PCS_RTE-I16z3.QSetPointStep.Inc10Injection
        Compliance.WithoutCurves,  # PCS_RTE-I16z3.QSetPointStep.Dec20Injection
        Compliance.WithoutCurves,  # PCS_RTE-I16z3.QSetPointStep.Inc10Consumption
        Compliance.WithoutCurves,  # PCS_RTE-I16z3.QSetPointStep.Dec20Consumption
        Compliance.Compliant,  # PCS_RTE-I16z3.ThreePhaseFault.TransientBoltedInjection
        Compliance.Compliant,  # PCS_RTE-I16z3.ThreePhaseFault.TransientBoltedConsumption
        Compliance.Compliant,  # PCS_RTE-I16z3.GridVoltageDip.QzeroInjection
        Compliance.Compliant,  # PCS_RTE-I16z3.GridVoltageDip.QzeroConsumption
        Compliance.Compliant,  # PCS_RTE-I16z3.GridVoltageSwell.QMaxInjection
        Compliance.Compliant,  # PCS_RTE-I16z3.GridVoltageSwell.QMinInjection
        Compliance.Compliant,  # PCS_RTE-I16z3.GridVoltageSwell.QMaxConsumption
        Compliance.Compliant,  # PCS_RTE-I16z3.GridVoltageSwell.QMinConsumption
        Compliance.NonCompliant,  # PCS_RTE-I16z3.GridFreqRamp.W500mHz250msInjection
        Compliance.NonCompliant,  # PCS_RTE-I16z3.GridFreqRamp.W500mHz250msConsumption
        Compliance.NonCompliant,  # PCS_RTE-I16z3.Islanding.DeltaP10DeltaQ4Injection
        Compliance.Compliant,  # PCS_RTE-I16z3.Islanding.DeltaP10DeltaQ4Consumption
        Compliance.Compliant,  # PCS_RTE-F16z1.PSetPointStep.ConsumptionPmax
        Compliance.Compliant,  # PCS_RTE-F16z1.PSetPointStep.ConsumptionP50
        Compliance.Compliant,  # PCS_RTE-F16z1.PSetPointStep.InjectionP50
        Compliance.Compliant,  # PCS_RTE-F16z1.PSetPointStep.InjectionPmax
        Compliance.Compliant,  # PCS_RTE-F16z1.QSetPointStep.ConsumptionPmax
        Compliance.Compliant,  # PCS_RTE-F16z1.QSetPointStep.ConsumptionP50
        Compliance.Compliant,  # PCS_RTE-F16z1.QSetPointStep.InjectionP50
        Compliance.Compliant,  # PCS_RTE-F16z1.QSetPointStep.InjectionPmax
        Compliance.Compliant,  # PCS_RTE-F16z3.PSetPointStep.ConsumptionPmax
        Compliance.Compliant,  # PCS_RTE-F16z3.PSetPointStep.ConsumptionP50
        Compliance.Compliant,  # PCS_RTE-F16z3.PSetPointStep.InjectionP50
        Compliance.Compliant,  # PCS_RTE-F16z3.PSetPointStep.InjectionPmax
        Compliance.Compliant,  # PCS_RTE-F16z3.USetPointStep.ConsumptionPmax
        Compliance.Compliant,  # PCS_RTE-F16z3.USetPointStep.ConsumptionP50
        Compliance.Compliant,  # PCS_RTE-F16z3.USetPointStep.InjectionP50
        Compliance.Compliant,  # PCS_RTE-F16z3.USetPointStep.InjectionPmax
    ] == compliance
