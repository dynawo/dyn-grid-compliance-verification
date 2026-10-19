"""Electrical performance verification driven entirely by curves: the producer delivers its own
and there is nothing to simulate, so no Dynawo.

What is asserted here is what the commit decides — which tests the fiches declare for each kind
of producer, and that every one of them concludes. The verdict is not: it belongs to the curves,
which arrive with a release or with a regeneration. See curves_invariants.py.
"""

from tests.dycov.utils import PERFORMANCE, execute_tool_summary

from tests_integration.curves_invariants import assert_run_is_sound

SM_CURVES = PERFORMANCE / "ProducerCurves" / "SM"
PPM_CURVES = PERFORMANCE / "ProducerCurves" / "PPM"
BESS_CURVES = PERFORMANCE / "ProducerCurves" / "BESS"

SM_TESTS = [
    "PCS_RTE-I2.USetPointStep.AReactance",
    "PCS_RTE-I2.USetPointStep.BReactance",
    "PCS_RTE-I3.LineTrip.2BReactance",
    "PCS_RTE-I4.ThreePhaseFault.TransientBolted",
    "PCS_RTE-I6.GridVoltageDip.Qzero",
    "PCS_RTE-I7.GridVoltageSwell.QMax",
    "PCS_RTE-I7.GridVoltageSwell.QMin",
    "PCS_RTE-I8.LoadShedDisturbance.PmaxQzero",
    "PCS_RTE-I10.Islanding.DeltaP10DeltaQ4",
]

PPM_TESTS = [
    "PCS_RTE-I2.USetPointStep.AReactance",
    "PCS_RTE-I2.USetPointStep.BReactance",
    "PCS_RTE-I5.ThreePhaseFault.TransientBolted",
    "PCS_RTE-I6.GridVoltageDip.Qzero",
    "PCS_RTE-I7.GridVoltageSwell.QMax",
    "PCS_RTE-I7.GridVoltageSwell.QMin",
    "PCS_RTE-I10.Islanding.DeltaP10DeltaQ4",
]

BESS_TESTS = [
    "PCS_RTE-I2.USetPointStep.AReactanceInjection",
    "PCS_RTE-I2.USetPointStep.BReactanceInjection",
    "PCS_RTE-I2.USetPointStep.AReactanceConsumption",
    "PCS_RTE-I2.USetPointStep.BReactanceConsumption",
    "PCS_RTE-I5.ThreePhaseFault.TransientBoltedInjection",
    "PCS_RTE-I5.ThreePhaseFault.TransientBoltedConsumption",
    "PCS_RTE-I6.GridVoltageDip.QzeroInjection",
    "PCS_RTE-I6.GridVoltageDip.QzeroConsumption",
    "PCS_RTE-I7.GridVoltageSwell.QMaxInjection",
    "PCS_RTE-I7.GridVoltageSwell.QMinInjection",
    "PCS_RTE-I7.GridVoltageSwell.QMaxConsumption",
    "PCS_RTE-I7.GridVoltageSwell.QMinConsumption",
    "PCS_RTE-I10.Islanding.DeltaP10DeltaQ4Injection",
    "PCS_RTE-I10.Islanding.DeltaP10DeltaQ4Consumption",
]


def test_perf_sm_producer_curves():
    assert_run_is_sound(execute_tool_summary(None, SM_CURVES, None), SM_TESTS, SM_CURVES)


def test_perf_ppm_producer_curves():
    assert_run_is_sound(execute_tool_summary(None, PPM_CURVES, None), PPM_TESTS, PPM_CURVES)


def test_perf_bess_producer_curves():
    assert_run_is_sound(execute_tool_summary(None, BESS_CURVES, None), BESS_TESTS, BESS_CURVES)
