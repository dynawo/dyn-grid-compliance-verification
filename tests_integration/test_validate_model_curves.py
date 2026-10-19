"""Model validation driven entirely by curves: the producer delivers its own, and the example
provides the reference. No simulation, and so no Dynawo.

What is asserted here is what the commit decides — which tests the examples declare, that each
one concludes, and that the ones that cannot are exactly the ones whose curve is not delivered.
The verdict is not: it belongs to the curves, which arrive with a release or with a regeneration.
See curves_invariants.py.
"""

from tests.dycov.utils import MODEL, execute_tool_summary

from tests_integration.curves_invariants import assert_run_is_sound

PPM_PRODUCER_CURVES = MODEL / "ProducerCurves" / "PPM"
PPM_REFERENCE_CURVES = MODEL / "Wind" / "IECB2015" / "ReferenceCurves"
BESS_PRODUCER_CURVES = MODEL / "ProducerCurves" / "BESS"
BESS_REFERENCE_CURVES = MODEL / "BESS" / "WECC" / "ReferenceCurves"

PPM_TESTS = [
    "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3",
    "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR10",
    "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3Qmin",
    "PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800",
    "PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc500",
    "PCS_RTE-I16z1.ThreePhaseFault.PermanentBolted",
    "PCS_RTE-I16z1.ThreePhaseFault.PermanentHiZ",
    "PCS_RTE-I16z1.SetPointStep.Active",
    "PCS_RTE-I16z1.SetPointStep.Reactive",
    "PCS_RTE-I16z1.SetPointStep.Voltage",
    "PCS_RTE-I16z1.GridVoltageStep.Rise",
    "PCS_RTE-I16z1.GridVoltageStep.Drop",
    "PCS_RTE-I16z3.USetPointStep.AReactance",
    "PCS_RTE-I16z3.USetPointStep.BReactance",
    "PCS_RTE-I16z3.PSetPointStep.Dec40",
    "PCS_RTE-I16z3.PSetPointStep.Inc40",
    "PCS_RTE-I16z3.QSetPointStep.Inc10",
    "PCS_RTE-I16z3.QSetPointStep.Dec20",
    "PCS_RTE-I16z3.ThreePhaseFault.TransientBolted",
    "PCS_RTE-I16z3.GridVoltageDip.Qzero",
    "PCS_RTE-I16z3.GridVoltageSwell.QMax",
    "PCS_RTE-I16z3.GridVoltageSwell.QMin",
    "PCS_RTE-I16z3.GridFreqRamp.W500mHz250ms",
    "PCS_RTE-I16z3.Islanding.DeltaP10DeltaQ4",
    "PCS_RTE-F16z3.PSetPointStep.Pmin",
    "PCS_RTE-F16z3.PSetPointStep.P50",
    "PCS_RTE-F16z3.PSetPointStep.Pmax",
    "PCS_RTE-F16z3.USetPointStep.Pmin",
    "PCS_RTE-F16z3.USetPointStep.P50",
    "PCS_RTE-F16z3.USetPointStep.Pmax",
]

BESS_TESTS = [
    "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3Injection",
    "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR10Injection",
    "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3QminInjection",
    "PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800Injection",
    "PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc500Injection",
    "PCS_RTE-I16z1.ThreePhaseFault.PermanentBoltedInjection",
    "PCS_RTE-I16z1.ThreePhaseFault.PermanentHiZInjection",
    "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3Consumption",
    "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR10Consumption",
    "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3QminConsumption",
    "PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800Consumption",
    "PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc500Consumption",
    "PCS_RTE-I16z1.ThreePhaseFault.PermanentBoltedConsumption",
    "PCS_RTE-I16z1.ThreePhaseFault.PermanentHiZConsumption",
    "PCS_RTE-I16z1.SetPointStep.ActiveInjection",
    "PCS_RTE-I16z1.SetPointStep.ReactiveInjection",
    "PCS_RTE-I16z1.SetPointStep.VoltageInjection",
    "PCS_RTE-I16z1.SetPointStep.ActiveConsumption",
    "PCS_RTE-I16z1.SetPointStep.ReactiveConsumption",
    "PCS_RTE-I16z1.SetPointStep.VoltageConsumption",
    "PCS_RTE-I16z1.GridVoltageStep.RiseInjection",
    "PCS_RTE-I16z1.GridVoltageStep.DropInjection",
    "PCS_RTE-I16z1.GridVoltageStep.RiseConsumption",
    "PCS_RTE-I16z1.GridVoltageStep.DropConsumption",
    "PCS_RTE-I16z3.USetPointStep.AReactanceInjection",
    "PCS_RTE-I16z3.USetPointStep.BReactanceInjection",
    "PCS_RTE-I16z3.USetPointStep.AReactanceConsumption",
    "PCS_RTE-I16z3.USetPointStep.BReactanceConsumption",
    "PCS_RTE-I16z3.PSetPointStep.Dec40Injection",
    "PCS_RTE-I16z3.PSetPointStep.Inc40Injection",
    "PCS_RTE-I16z3.PSetPointStep.Dec40Consumption",
    "PCS_RTE-I16z3.PSetPointStep.Inc40Consumption",
    "PCS_RTE-I16z3.QSetPointStep.Inc10Injection",
    "PCS_RTE-I16z3.QSetPointStep.Dec20Injection",
    "PCS_RTE-I16z3.QSetPointStep.Inc10Consumption",
    "PCS_RTE-I16z3.QSetPointStep.Dec20Consumption",
    "PCS_RTE-I16z3.ThreePhaseFault.TransientBoltedInjection",
    "PCS_RTE-I16z3.ThreePhaseFault.TransientBoltedConsumption",
    "PCS_RTE-I16z3.GridVoltageDip.QzeroInjection",
    "PCS_RTE-I16z3.GridVoltageDip.QzeroConsumption",
    "PCS_RTE-I16z3.GridVoltageSwell.QMaxInjection",
    "PCS_RTE-I16z3.GridVoltageSwell.QMinInjection",
    "PCS_RTE-I16z3.GridVoltageSwell.QMaxConsumption",
    "PCS_RTE-I16z3.GridVoltageSwell.QMinConsumption",
    "PCS_RTE-I16z3.GridFreqRamp.W500mHz250msInjection",
    "PCS_RTE-I16z3.GridFreqRamp.W500mHz250msConsumption",
    "PCS_RTE-I16z3.Islanding.DeltaP10DeltaQ4Injection",
    "PCS_RTE-I16z3.Islanding.DeltaP10DeltaQ4Consumption",
    "PCS_RTE-F16z3.PSetPointStep.ConsumptionPmax",
    "PCS_RTE-F16z3.PSetPointStep.ConsumptionP50",
    "PCS_RTE-F16z3.PSetPointStep.InjectionP50",
    "PCS_RTE-F16z3.PSetPointStep.InjectionPmax",
    "PCS_RTE-F16z3.USetPointStep.ConsumptionPmax",
    "PCS_RTE-F16z3.USetPointStep.ConsumptionP50",
    "PCS_RTE-F16z3.USetPointStep.InjectionP50",
    "PCS_RTE-F16z3.USetPointStep.InjectionPmax",
]


def test_model_validation_ppm_producer_curves():
    summaries = execute_tool_summary(None, PPM_PRODUCER_CURVES, PPM_REFERENCE_CURVES)
    assert_run_is_sound(summaries, PPM_TESTS, PPM_PRODUCER_CURVES, PPM_REFERENCE_CURVES)


def test_model_validation_bess_producer_curves():
    summaries = execute_tool_summary(None, BESS_PRODUCER_CURVES, BESS_REFERENCE_CURVES)
    assert_run_is_sound(summaries, BESS_TESTS, BESS_PRODUCER_CURVES, BESS_REFERENCE_CURVES)
