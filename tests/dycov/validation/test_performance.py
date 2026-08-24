#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Unit tests for the electrical performance verification (PerformanceValidator)."""

from pathlib import Path

import pandas as pd
import pytest
from lxml import etree

from dycov.core.global_variables import (
    ELECTRIC_PERFORMANCE_PPM,
    ELECTRIC_PERFORMANCE_SM,
    MODEL_VALIDATION_PPM,
)
from dycov.model.parameters import DisconnectionModel, Stability
from dycov.validation.performance import (
    GENERATOR_DISCONNECT_MSG,
    IEC_DISCONNECT_PROTECTION_MSG,
    LOAD_DISCONNECT_MSG,
    PerformanceValidator,
    _check_compliance,
    _check_timeline,
    _is_disconnection_event,
)

PERFORMANCE_MODULE = "dycov.validation.performance"

RESOURCES_PATH = Path(__file__).resolve().parent / "resources"

THR_SS_TOL = 0.002


class DummyConfig:
    """Configuration stand-in returning the requested default, or a declared override."""

    def __init__(self, **overrides):
        self._overrides = overrides

    def get_float(self, section: str, key: str, default: float) -> float:
        return self._overrides.get(key, default)


class DummyProducer:
    def __init__(self, sim_type=ELECTRIC_PERFORMANCE_PPM, is_dynawo_model=True):
        self._sim_type = sim_type
        self._is_dynawo_model = is_dynawo_model

    def get_sim_type(self) -> int:
        return self._sim_type

    def is_dynawo_model(self) -> bool:
        return self._is_dynawo_model


class DummyCurvesManager:
    """Curves manager stand-in serving in-memory curves."""

    def __init__(self, calculated=None, reference=None):
        self._curves = {
            "calculated": pd.DataFrame() if calculated is None else calculated,
            "reference": pd.DataFrame() if reference is None else reference,
        }

    def get_curves(self, curve: str) -> pd.DataFrame:
        return self._curves[curve]


class DummyElement:
    def __init__(self, element_id):
        self.id = element_id


class RecordingLogger:
    """Logger stand-in collecting the emitted warnings and debug traces."""

    def __init__(self):
        self.warnings = []
        self.debugs = []

    def get_logger(self, name: str):
        return self

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def debug(self, message: str) -> None:
        self.debugs.append(message)


def _make_validator(
    validations=None,
    calculated=None,
    reference=None,
    sim_type=ELECTRIC_PERFORMANCE_PPM,
    is_dynawo_model=True,
):
    return PerformanceValidator(
        curves_manager=DummyCurvesManager(calculated=calculated, reference=reference),
        producer=DummyProducer(sim_type=sim_type, is_dynawo_model=is_dynawo_model),
        thr_ss_tol=THR_SS_TOL,
        validations=validations or [],
        is_field_measurements=False,
        pcs_name="PCS_RTE-I2",
        bm_name="USetPointStep",
    )


def _make_pdr_curves(voltage=None, active_power=None, reactive_power=None, **extra_columns):
    """PDR measurements of a voltage dip, with optional generator-side columns."""
    curves = {
        "time": [0.0, 1.0, 2.0, 3.0, 4.0],
        "BusPDR_BUS_Voltage": voltage or [0.5, 0.5, 0.96, 1.0, 1.0],
        "BusPDR_BUS_ActivePower": active_power or [0.5, 0.5, 0.1, 0.53, 0.5],
        "BusPDR_BUS_ReactivePower": reactive_power or [0.1, 0.1, 0.1, 0.1, 0.1],
    }
    curves.update(extra_columns)
    return pd.DataFrame(curves)


def _make_disconnection_model(gen_intline=True, auxload_xfmr=True):
    return DisconnectionModel(
        auxload=DummyElement("Aux_Load"),
        auxload_xfmr=DummyElement("AuxLoad_Xfmr") if auxload_xfmr else None,
        stepup_xfmrs=["StepUp_Xfmr"],
        gen_intline=DummyElement("Gen_IntLine") if gen_intline else None,
    )


@pytest.fixture(autouse=True)
def default_config(monkeypatch):
    """Serve the documented defaults regardless of the user configuration."""
    monkeypatch.setattr(f"{PERFORMANCE_MODULE}.config", DummyConfig())


# ---------------------------------------------------------------------------
# Compliance helper
# ---------------------------------------------------------------------------


def test_check_compliance_scales_the_value_before_checking_it():
    results = {"compliance": True}

    _check_compliance(results, 0.75, "metric", 2.0, 2.0)

    assert results["metric"] == pytest.approx(1.5)
    assert results["metric_check"] is True
    assert results["compliance"] is True


def test_check_compliance_without_a_threshold_only_stores_the_value():
    results = {"compliance": True}

    _check_compliance(results, 0.75, "metric", None)

    assert results["metric"] == pytest.approx(0.75)
    assert "metric_check" not in results
    assert results["compliance"] is True


def test_check_compliance_above_the_threshold_fails():
    results = {"compliance": True}

    _check_compliance(results, 2.0, "metric", 1.0)

    assert results["metric"] == pytest.approx(2.0)
    assert results["metric_check"] is False
    assert results["compliance"] is False


# ---------------------------------------------------------------------------
# Timeline disconnection events
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message, element_type, expected",
    [
        (GENERATOR_DISCONNECT_MSG, "gen", True),
        (f"{IEC_DISCONNECT_PROTECTION_MSG} undervoltage protection", "gen", True),
        (LOAD_DISCONNECT_MSG, "load", True),
        (LOAD_DISCONNECT_MSG, "gen", False),
        (GENERATOR_DISCONNECT_MSG, "load", False),
        ("Tap-changer : below minimum allowed value", "gen", False),
        ("Tap-changer : below minimum allowed value", "load", False),
    ],
)
def test_is_disconnection_event(message, element_type, expected):
    event = etree.Element("event")
    event.set("message", message)

    assert _is_disconnection_event(event, element_type) is expected


def test_check_timeline_without_disconnection_events():
    timeline_file = RESOURCES_PATH / "timeline_no_disconnections.xml"

    no_error, disconnection_list = _check_timeline(timeline_file, "gen")

    assert no_error is True
    assert disconnection_list == []


def test_check_timeline_collects_the_disconnected_models():
    timeline_file = RESOURCES_PATH / "timeline_disconnection.xml"

    no_error, disconnection_list = _check_timeline(timeline_file, "gen")

    assert no_error is False
    assert disconnection_list == ["Wind_Turbine"]


def test_check_timeline_ignores_the_generator_events_when_looking_for_loads():
    timeline_file = RESOURCES_PATH / "timeline_disconnection.xml"

    no_error, disconnection_list = _check_timeline(timeline_file, "load")

    assert no_error is True
    assert disconnection_list == []


# ---------------------------------------------------------------------------
# Stabilization tests
# ---------------------------------------------------------------------------


def test_run_common_tests_of_a_stable_power_park_module():
    validator = _make_validator(calculated=_make_pdr_curves())

    (
        steady_p,
        first_steady_pos_p,
        steady_q,
        first_steady_pos_q,
        steady_v,
        first_steady_pos_v,
        stable_theta,
        first_stable_pos_theta,
        pass_pi,
    ) = validator._PerformanceValidator__run_common_tests(THR_SS_TOL, is_ppm=True)

    assert (steady_p, steady_q, steady_v) == (True, True, True)
    assert (first_steady_pos_p, first_steady_pos_q, first_steady_pos_v) == (4, 0, 3)

    # The internal angle is only checked for synchronous machines.
    assert stable_theta is False
    assert first_stable_pos_theta == 0
    assert pass_pi is False


def test_run_common_tests_warns_about_every_curve_without_a_steady_state(monkeypatch):
    logger = RecordingLogger()
    monkeypatch.setattr(f"{PERFORMANCE_MODULE}.dycov_logging", logger)
    diverged = [0.5, 0.5, 0.5, 0.5, float("nan")]
    validator = _make_validator(
        calculated=_make_pdr_curves(
            voltage=diverged, active_power=diverged, reactive_power=diverged
        )
    )

    steady_p, _, steady_q, _, steady_v, _, _, _, _ = (
        validator._PerformanceValidator__run_common_tests(THR_SS_TOL, is_ppm=True)
    )

    assert (steady_p, steady_q, steady_v) == (False, False, False)
    assert logger.warnings == [
        "P has not reached steady state",
        "Q has not reached steady state",
        "V has not reached steady state",
    ]


def test_run_common_tests_of_a_synchronous_machine_checks_the_internal_angle():
    validator = _make_validator(
        calculated=_make_pdr_curves(Synch_Gen_InternalAngle=[0.5, 0.5, 0.5, 0.5, 0.5])
    )

    _, _, _, _, _, _, stable_theta, first_stable_pos_theta, pass_pi = (
        validator._PerformanceValidator__run_common_tests(THR_SS_TOL, is_ppm=False)
    )

    assert stable_theta is True
    assert first_stable_pos_theta == 0
    assert pass_pi is True


def test_check_theta_stability_without_internal_angles_is_stable():
    validator = _make_validator(calculated=_make_pdr_curves())

    stable_theta, first_stable_pos_theta, pass_pi = validator._check_theta_stability(THR_SS_TOL)

    # Without generator internal angles the position defaults to the end of the simulation.
    assert stable_theta is True
    assert first_stable_pos_theta == 5
    assert pass_pi is True


def test_check_theta_stability_of_an_unstable_internal_angle(monkeypatch):
    logger = RecordingLogger()
    monkeypatch.setattr(f"{PERFORMANCE_MODULE}.dycov_logging", logger)
    validator = _make_validator(
        calculated=_make_pdr_curves(
            Synch_Gen_InternalAngle=[0.5, 0.5, 0.5, 0.5, float("nan")]
        )
    )

    stable_theta, first_stable_pos_theta, pass_pi = validator._check_theta_stability(THR_SS_TOL)

    assert stable_theta is False
    assert first_stable_pos_theta == -1
    assert pass_pi is True
    assert logger.warnings == ["Theta has not reached stabilization"]


def test_check_theta_stability_of_an_internal_angle_beyond_pi(monkeypatch):
    logger = RecordingLogger()
    monkeypatch.setattr(f"{PERFORMANCE_MODULE}.dycov_logging", logger)
    validator = _make_validator(
        calculated=_make_pdr_curves(Synch_Gen_InternalAngle=[0.0, 3.5, 0.0, 0.0, 0.0])
    )

    stable_theta, _, pass_pi = validator._check_theta_stability(THR_SS_TOL)

    assert stable_theta is True
    assert pass_pi is False
    assert logger.warnings == ["Theta has not met the success criterion"]


# ---------------------------------------------------------------------------
# Time calculations
# ---------------------------------------------------------------------------


def test_calculate_simple_times_measures_the_voltage_and_power_recovery():
    validator = _make_validator(
        validations=["time_5U", "time_10U", "time_10Pfloor_clear"],
        calculated=_make_pdr_curves(),
    )
    compliance_values = {}

    validator._PerformanceValidator__calculate_simple_times(compliance_values, 1.0)

    # The 0.96 pu sample at t = 2 s is inside the 10% tube but outside the 5% one.
    assert compliance_values["time_5u"] == pytest.approx(1.0)
    assert compliance_values["time_10u"] == pytest.approx(0.0)
    assert compliance_values["time_10pfloor"] == pytest.approx(1.0)


def test_calculate_composed_times_measures_the_power_and_voltage_instants():
    validator = _make_validator(
        validations=["time_5P", "time_10P", "time_5P_85U"], calculated=_make_pdr_curves()
    )
    compliance_values = {}

    validator._PerformanceValidator__calculate_composed_times(compliance_values, 1.0)

    # The 0.53 pu sample at t = 3 s is inside the 10% tube but outside the 5% one.
    assert compliance_values["time_5p"] == pytest.approx(2.0)
    assert compliance_values["time_10p"] == pytest.approx(1.0)
    assert compliance_values["time_85u"] == pytest.approx(1.0)


def test_calculate_composed_times_for_the_power_floor_at_85_percent_voltage():
    validator = _make_validator(
        validations=["time_10Pfloor_85U"], calculated=_make_pdr_curves()
    )
    compliance_values = {}

    validator._PerformanceValidator__calculate_composed_times(compliance_values, 1.0)

    assert compliance_values["time_85u"] == pytest.approx(1.0)
    assert compliance_values["time_10pfloor"] == pytest.approx(1.0)


def test_calculate_times_covers_the_simple_and_the_composed_instants():
    validator = _make_validator(
        validations=["time_5U", "time_5P"], calculated=_make_pdr_curves()
    )
    compliance_values = {}

    validator._PerformanceValidator__calculate_times(compliance_values, 1.0)

    assert compliance_values["time_5u"] == pytest.approx(1.0)
    assert compliance_values["time_5p"] == pytest.approx(2.0)


def test_calculate_times_skips_the_disabled_validations():
    validator = _make_validator(calculated=_make_pdr_curves())
    compliance_values = {}

    validator._PerformanceValidator__calculate_times(compliance_values, 1.0)

    assert compliance_values == {}


# ---------------------------------------------------------------------------
# AVR and frequency calculations
# ---------------------------------------------------------------------------


def _make_avr_curves(first_magnitude, second_magnitude):
    return _make_pdr_curves(
        **{
            "G1_GEN_MagnitudeControlledByAVRPu": first_magnitude,
            "G1_GEN_VoltageSetpointPu": [1.0, 1.0, 1.0, 1.0, 1.0],
            "G2_GEN_MagnitudeControlledByAVRPu": second_magnitude,
            "G2_GEN_VoltageSetpointPu": [1.0, 1.0, 1.0, 1.0, 1.0],
        }
    )


def test_calculate_avr_of_generators_tracking_their_setpoint():
    tracking = [1.0, 1.0, 1.0, 1.0, 1.0]
    validator = _make_validator(
        validations=["AVR_5"], calculated=_make_avr_curves(tracking, tracking)
    )
    compliance_values = {}

    validator._PerformanceValidator__calculate_avr(compliance_values, 0.0)

    assert compliance_values["AVR_5_check"] is True
    assert compliance_values["AVR_5"] == -1
    assert compliance_values["AVR_5_crvs"] == [tracking, tracking]


def test_calculate_avr_reports_the_generator_losing_its_setpoint():
    validator = _make_validator(
        validations=["AVR_5"],
        calculated=_make_avr_curves(
            [1.0, 1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 2.0, 1.0, 1.0]
        ),
    )
    compliance_values = {}

    validator._PerformanceValidator__calculate_avr(compliance_values, 0.0)

    assert compliance_values["AVR_5_check"] is False
    assert compliance_values["AVR_5"] == pytest.approx(2.0)


def test_calculate_frequency_within_the_nominal_band():
    validator = _make_validator(
        validations=["freq_1"],
        calculated=_make_pdr_curves(G1_GEN_NetworkFrequencyPu=[1.0, 1.0, 1.01, 1.0, 1.0]),
    )
    compliance_values = {}

    validator._PerformanceValidator__calculate_frequency(compliance_values)

    # The band is 1/f_nom = 0.02 pu around the nominal frequency.
    assert compliance_values["check_freq1"] is True
    assert compliance_values["time_freq1"] == -1


def test_calculate_frequency_outside_the_nominal_band():
    validator = _make_validator(
        validations=["freq_1"],
        calculated=_make_pdr_curves(G1_GEN_NetworkFrequencyPu=[1.0, 1.0, 1.05, 1.0, 1.0]),
    )
    compliance_values = {}

    validator._PerformanceValidator__calculate_frequency(compliance_values)

    assert compliance_values["check_freq1"] is False
    assert compliance_values["time_freq1"] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Remaining calculations
# ---------------------------------------------------------------------------


def test_calculate_others_reports_a_valid_test():
    validator = _make_validator(calculated=_make_pdr_curves())
    compliance_values = {}

    validator._PerformanceValidator__calculate_others(compliance_values, 1.0)

    assert compliance_values["is_invalid_test"] is False


def test_calculate_others_reports_a_flat_test_as_invalid():
    flat = [0.5, 0.5, 0.5, 0.5, 0.5]
    validator = _make_validator(
        calculated=_make_pdr_curves(voltage=flat, active_power=flat, reactive_power=flat)
    )
    compliance_values = {}

    validator._PerformanceValidator__calculate_others(compliance_values, 1.0)

    assert compliance_values["is_invalid_test"] is True


def test_calculate_others_keeps_the_worst_static_difference():
    validator = _make_validator(
        validations=["static_diff"],
        calculated=_make_avr_curves(
            [1.0, 1.0, 1.0, 1.0, 1.001], [1.0, 1.0, 1.0, 1.0, 1.002]
        ),
    )
    compliance_values = {}

    validator._PerformanceValidator__calculate_others(compliance_values, 1.0)

    assert compliance_values["static_diff"] == pytest.approx(0.002)


def _make_injection_curves(active_current, reactive_current):
    return _make_pdr_curves(
        **{
            "G1_GEN_IpInjTerminal": active_current,
            "G1_GEN_IqInjTerminal": reactive_current,
        }
    )


def test_calculate_others_imax_reac_without_saturation():
    validator = _make_validator(
        validations=["imax_reac"],
        calculated=_make_injection_curves([0.1, 0.1, 0.2, 0.1, 0.1], [0.0] * 5),
    )
    validator.set_generators_imax({"G1": 1.0})
    compliance_values = {}

    validator._PerformanceValidator__calculate_others(compliance_values, 1.0)

    assert compliance_values["imax_reac_check"] is True
    assert compliance_values["imax_reac"] == -1


def test_calculate_others_imax_reac_detects_the_active_current_priority_violation():
    validator = _make_validator(
        validations=["imax_reac"],
        calculated=_make_injection_curves([0.2, 0.3, 0.4, 0.4, 0.4], [0.0] * 5),
    )
    validator.set_generators_imax({"G1": 0.2})
    compliance_values = {}

    validator._PerformanceValidator__calculate_others(compliance_values, 1.0)

    assert compliance_values["imax_reac_check"] is False
    assert compliance_values["imax_reac"] == pytest.approx(1.0)


def test_calculate_gathers_every_enabled_validation():
    validator = _make_validator(
        validations=["time_5U", "AVR_5", "freq_1"],
        calculated=_make_avr_curves([1.0] * 5, [1.0] * 5),
    )

    compliance_values = validator._PerformanceValidator__calculate(1.0)

    assert compliance_values["time_5u"] == pytest.approx(1.0)
    assert compliance_values["AVR_5_check"] is True
    assert compliance_values["check_freq1"] is True
    assert compliance_values["is_invalid_test"] is False


# ---------------------------------------------------------------------------
# Result creation
# ---------------------------------------------------------------------------


def test_create_results_without_a_critical_clearing_time():
    validator = _make_validator()

    results = validator._PerformanceValidator__create_results(
        1.0, {"is_invalid_test": False}
    )

    assert results["sim_t_event_start"] == 1.0
    assert results["compliance"] is True
    assert results["is_invalid_test"] is False
    assert "time_cct" not in results


def test_create_results_reports_the_critical_clearing_time():
    validator = _make_validator()
    validator.set_time_cct(0.15)

    results = validator._PerformanceValidator__create_results(
        1.0, {"is_invalid_test": False}
    )

    assert results["time_cct"] == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# Simple time checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "validation, magnitude, value, expected_check",
    [
        ("time_5U", "time_5u", 1.0, True),
        ("time_5U", "time_5u", 11.0, False),
        ("time_10U", "time_10u", 1.0, True),
        ("time_10U", "time_10u", 6.0, False),
        ("time_5P", "time_5p", 1.0, True),
        ("time_5P", "time_5p", 11.0, False),
        ("time_10P", "time_10p", 1.0, True),
        ("time_10P", "time_10p", 6.0, False),
    ],
)
def test_check_simple_times_against_their_thresholds(
    validation, magnitude, value, expected_check
):
    validator = _make_validator(validations=[validation])
    results = {"compliance": True}

    validator._PerformanceValidator__check_simple_times(
        results, 1.0, 2.0, {magnitude: value}
    )

    assert results[validation] == pytest.approx(value)
    assert results[f"{validation}_check"] is expected_check
    assert results["compliance"] is expected_check


@pytest.mark.parametrize(
    "validation, magnitude", [("time_5P_clear", "time_5p"), ("time_10P_clear", "time_10p")]
)
def test_check_simple_times_after_the_fault_clearing(validation, magnitude):
    validator = _make_validator(validations=[validation])
    results = {"compliance": True}

    validator._PerformanceValidator__check_simple_times(
        results, 1.0, 2.0, {magnitude: 3.0}
    )

    # The instants are measured from the end of the event.
    assert results["t_event_start"] == 2.0
    assert results[validation] == pytest.approx(2.0)
    assert results[f"{validation}_check"] is True
    assert results["compliance"] is True


# ---------------------------------------------------------------------------
# Composed time checks
# ---------------------------------------------------------------------------


def test_check_composed_times_5p_at_85_percent_voltage():
    validator = _make_validator(validations=["time_5P_85U"])
    results = {"compliance": True}

    validator._PerformanceValidator__check_composed_times(
        results, 1.0, 2.0, {"time_5p": 3.0, "time_85u": 1.0}
    )

    assert results["time_85U"] == pytest.approx(1.0)
    assert results["time_5P_85U"] == pytest.approx(2.0)
    assert results["time_5P_85U_check"] is True
    assert results["compliance"] is True


def test_check_composed_times_10p_at_85_percent_voltage():
    validator = _make_validator(validations=["time_10P_85U"])
    results = {"compliance": True}

    validator._PerformanceValidator__check_composed_times(
        results, 1.0, 2.0, {"time_10p": 3.0, "time_85u": 1.0}
    )

    assert results["time_85U"] == pytest.approx(1.0)
    assert results["time_10P"] == pytest.approx(3.0)
    assert results["time_10P_85U"] == pytest.approx(2.0)
    assert results["time_10P_85U_check"] is True


def test_check_composed_times_power_floor_at_85_percent_voltage_above_the_threshold():
    validator = _make_validator(validations=["time_10Pfloor_85U"])
    results = {"compliance": True}

    validator._PerformanceValidator__check_composed_times(
        results, 1.0, 2.0, {"time_10pfloor": 5.0, "time_85u": 1.0}
    )

    assert results["time_10Pfloor"] == pytest.approx(5.0)
    assert results["time_10Pfloor_85U"] == pytest.approx(4.0)
    assert results["time_10Pfloor_85U_check"] is False
    assert results["compliance"] is False


def test_check_composed_times_power_floor_after_the_fault_clearing():
    validator = _make_validator(validations=["time_10Pfloor_clear"])
    results = {"compliance": True}

    validator._PerformanceValidator__check_composed_times(
        results, 1.0, 2.0, {"time_10pfloor": 2.5}
    )

    assert results["t_event_start"] == 2.0
    assert results["time_10Pfloor_clear"] == pytest.approx(1.5)
    assert results["time_10Pfloor_clear_check"] is True


def test_check_composed_times_85u_before_10p():
    validator = _make_validator(validations=["time_85U_10P"])
    results = {"compliance": True}

    validator._PerformanceValidator__check_composed_times(
        results, 1.0, 2.0, {"time_10p": 3.0, "time_85u": 1.0}
    )

    assert results["time_85U_10P"] == pytest.approx(2.0)
    assert results["time_85U_10P_check"] is True


def test_check_times_covers_the_simple_and_the_composed_checks():
    validator = _make_validator(validations=["time_5U", "time_5P_85U"])
    results = {"compliance": True}

    validator._PerformanceValidator__check_times(
        results, 1.0, 2.0, {"time_5u": 1.0, "time_5p": 3.0, "time_85u": 1.0}
    )

    assert results["time_5U_check"] is True
    assert results["time_5P_85U_check"] is True


# ---------------------------------------------------------------------------
# Disconnection checks
# ---------------------------------------------------------------------------


def _patch_timeline(monkeypatch, disconnection_list):
    no_error = not disconnection_list
    monkeypatch.setattr(
        f"{PERFORMANCE_MODULE}._check_timeline",
        lambda timeline_file, element_type: (no_error, disconnection_list),
    )


def test_check_disconnections_without_generator_disconnections(monkeypatch, tmp_path):
    _patch_timeline(monkeypatch, [])
    validator = _make_validator(validations=["no_disconnection_gen"])
    validator._disconnection_model = _make_disconnection_model()
    results = {"compliance": True}

    validator._PerformanceValidator__check_disconnections(results, tmp_path, True)

    assert results["no_disconnection_gen"] is True
    assert results["compliance"] is True


def test_check_disconnections_of_a_stepup_transformer_fails(monkeypatch, tmp_path):
    _patch_timeline(monkeypatch, ["StepUp_Xfmr"])
    validator = _make_validator(validations=["no_disconnection_gen"])
    validator._disconnection_model = _make_disconnection_model()
    results = {"compliance": True}

    validator._PerformanceValidator__check_disconnections(results, tmp_path, True)

    assert results["no_disconnection_gen"] is False
    assert results["compliance"] is False


def test_check_disconnections_of_the_generator_internal_line_fails(monkeypatch, tmp_path):
    _patch_timeline(monkeypatch, ["Gen_IntLine"])
    validator = _make_validator(validations=["no_disconnection_gen"])
    validator._disconnection_model = _make_disconnection_model()
    results = {"compliance": True}

    validator._PerformanceValidator__check_disconnections(results, tmp_path, True)

    assert results["no_disconnection_gen"] is False
    assert results["compliance"] is False


def test_check_disconnections_of_an_unrelated_model_is_compliant(monkeypatch, tmp_path):
    _patch_timeline(monkeypatch, ["Wind_Turbine"])
    validator = _make_validator(validations=["no_disconnection_gen"])
    validator._disconnection_model = _make_disconnection_model()
    results = {"compliance": True}

    validator._PerformanceValidator__check_disconnections(results, tmp_path, True)

    # Only the generator internal line and the step-up transformers break the compliance.
    assert results["no_disconnection_gen"] is True
    assert results["compliance"] is True


def test_check_disconnections_without_a_generator_internal_line(monkeypatch, tmp_path):
    _patch_timeline(monkeypatch, ["Wind_Turbine"])
    validator = _make_validator(validations=["no_disconnection_gen"])
    validator._disconnection_model = _make_disconnection_model(gen_intline=False)
    results = {"compliance": True}

    validator._PerformanceValidator__check_disconnections(results, tmp_path, True)

    assert results["no_disconnection_gen"] is True


def test_check_disconnections_traces_the_disconnected_models(monkeypatch, tmp_path):
    logger = RecordingLogger()
    monkeypatch.setattr(f"{PERFORMANCE_MODULE}.dycov_logging", logger)
    _patch_timeline(monkeypatch, ["Wind_Turbine"])
    validator = _make_validator(validations=["no_disconnection_gen"])
    validator._disconnection_model = _make_disconnection_model()

    validator._PerformanceValidator__check_disconnections({"compliance": True}, tmp_path, True)

    assert logger.debugs == ["Timeline disconnection. Model: Wind_Turbine"]


def test_check_disconnections_of_the_auxiliary_load_fails(monkeypatch, tmp_path):
    _patch_timeline(monkeypatch, ["Aux_Load"])
    validator = _make_validator(validations=["no_disconnection_load"])
    validator._disconnection_model = _make_disconnection_model()
    results = {"compliance": True}

    validator._PerformanceValidator__check_disconnections(results, tmp_path, True)

    assert results["no_disconnection_load"] is False
    assert results["compliance"] is False


def test_check_disconnections_of_an_unrelated_load_is_compliant(monkeypatch, tmp_path):
    _patch_timeline(monkeypatch, ["Grid_Load"])
    validator = _make_validator(validations=["no_disconnection_load"])
    validator._disconnection_model = _make_disconnection_model()
    results = {"compliance": True}

    validator._PerformanceValidator__check_disconnections(results, tmp_path, True)

    assert results["no_disconnection_load"] is True
    assert results["compliance"] is True


def test_check_disconnections_without_an_auxiliary_load_transformer(monkeypatch, tmp_path):
    _patch_timeline(monkeypatch, ["Grid_Load"])
    validator = _make_validator(validations=["no_disconnection_load"])
    validator._disconnection_model = _make_disconnection_model(auxload_xfmr=False)
    results = {"compliance": True}

    validator._PerformanceValidator__check_disconnections(results, tmp_path, True)

    assert results["no_disconnection_load"] is True


def test_check_disconnections_skipped_without_a_dynamic_model(tmp_path):
    validator = _make_validator(
        validations=["no_disconnection_gen", "no_disconnection_load"]
    )
    results = {"compliance": True}

    validator._PerformanceValidator__check_disconnections(results, tmp_path, False)

    assert results == {"compliance": True}


# ---------------------------------------------------------------------------
# Remaining checks
# ---------------------------------------------------------------------------


def _make_stability(theta=True, pi=True):
    return Stability(p=True, q=True, v=True, theta=theta, pi=pi)


def test_check_others_static_diff_within_the_threshold():
    validator = _make_validator(validations=["static_diff"])
    results = {"compliance": True}

    validator._PerformanceValidator__check_others(
        results, _make_stability(), False, {"static_diff": 0.001}
    )

    # The static difference is reported as a percentage against a 0.2% threshold.
    assert results["static_diff"] == pytest.approx(0.1)
    assert results["static_diff_check"] is True
    assert results["compliance"] is True


def test_check_others_static_diff_above_the_threshold():
    validator = _make_validator(validations=["static_diff"])
    results = {"compliance": True}

    validator._PerformanceValidator__check_others(
        results, _make_stability(), False, {"static_diff": 0.01}
    )

    assert results["static_diff"] == pytest.approx(1.0)
    assert results["static_diff_check"] is False
    assert results["compliance"] is False


def test_check_others_stabilized_of_a_synchronous_machine_requires_the_internal_angle():
    validator = _make_validator(validations=["stabilized"])
    results = {"compliance": True}

    validator._PerformanceValidator__check_others(
        results, _make_stability(theta=False), False, {}
    )

    assert results["stabilized"] is False
    assert results["compliance"] is False


def test_check_others_stabilized_of_a_power_park_module_ignores_the_internal_angle():
    validator = _make_validator(validations=["stabilized"])
    results = {"compliance": True}

    validator._PerformanceValidator__check_others(
        results, _make_stability(theta=False, pi=False), True, {}
    )

    assert results["stabilized"] is True
    assert results["compliance"] is True


def test_check_others_imax_reac():
    validator = _make_validator(validations=["imax_reac"])
    results = {"compliance": True}

    validator._PerformanceValidator__check_others(
        results, _make_stability(), True, {"imax_reac": 0.5, "imax_reac_check": False}
    )

    assert results["imax_reac"] == pytest.approx(0.5)
    assert results["imax_reac_check"] is False
    assert results["compliance"] is False


def test_check_others_avr_and_frequency():
    validator = _make_validator(validations=["AVR_5", "freq_1"])
    results = {"compliance": True}
    compliance_values = {
        "AVR_5_check": True,
        "AVR_5": 0.3,
        "AVR_5_crvs": [[1.0, 1.0]],
        "time_freq1": 0.1,
        "check_freq1": False,
    }

    validator._PerformanceValidator__check_others(
        results, _make_stability(), True, compliance_values
    )

    assert results["AVR_5"] == pytest.approx(0.3)
    assert results["AVR_5_check"] is True
    assert results["AVR_5_crvs"] == [[1.0, 1.0]]
    assert results["freq1"] == pytest.approx(0.1)
    assert results["freq1_check"] is False
    assert results["compliance"] is False


# ---------------------------------------------------------------------------
# Validation orchestration
# ---------------------------------------------------------------------------


VALIDATE_EVENT_PARAMS = {"start_time": 1.0, "duration_time": 0.1}


def test_validate_a_power_park_module(tmp_path):
    validator = _make_validator(
        validations=["time_5U"],
        calculated=_make_pdr_curves(),
        sim_type=ELECTRIC_PERFORMANCE_PPM,
    )

    results = validator.validate("oc", tmp_path, "outputs", VALIDATE_EVENT_PARAMS)

    assert results["sim_t_event_start"] == 1.0
    assert results["is_invalid_test"] is False
    assert results["time_5U"] == pytest.approx(1.0)
    assert results["time_5U_check"] is True
    assert results["compliance"] is True
    # The internal angle is not part of the steady state of a power park module.
    assert results["first_steady_pos"] == 4
    assert results["curves"] is validator._get_calculated_curves()
    assert "reference_curves" not in results


def test_validate_a_model_validation_power_park_module(tmp_path):
    validator = _make_validator(
        calculated=_make_pdr_curves(), sim_type=MODEL_VALIDATION_PPM
    )

    results = validator.validate("oc", tmp_path, "outputs", VALIDATE_EVENT_PARAMS)

    assert results["compliance"] is True
    assert results["first_steady_pos"] == 4


def test_validate_a_synchronous_machine_includes_the_internal_angle(tmp_path):
    validator = _make_validator(
        calculated=_make_pdr_curves(Synch_Gen_InternalAngle=[0.5, 0.5, 0.5, 0.5, 0.5]),
        reference=_make_pdr_curves(),
        sim_type=ELECTRIC_PERFORMANCE_SM,
    )

    results = validator.validate("oc", tmp_path, "outputs", VALIDATE_EVENT_PARAMS)

    assert results["compliance"] is True
    assert results["first_steady_pos"] == 4
    assert results["reference_curves"] is validator._get_reference_curves()


def test_validate_checks_the_disconnections_of_a_dynamic_model(monkeypatch, tmp_path):
    _patch_timeline(monkeypatch, ["Gen_IntLine"])
    validator = _make_validator(
        validations=["no_disconnection_gen"], calculated=_make_pdr_curves()
    )
    validator._disconnection_model = _make_disconnection_model()

    results = validator.validate("oc", tmp_path, "outputs", VALIDATE_EVENT_PARAMS)

    assert results["no_disconnection_gen"] is False
    assert results["compliance"] is False


# ---------------------------------------------------------------------------
# Required measurements
# ---------------------------------------------------------------------------


def test_get_measurement_names():
    validator = _make_validator()

    names = validator.get_measurement_names()

    assert names == [
        "BusPDR_BUS_ActivePower",
        "BusPDR_BUS_ReactivePower",
        "BusPDR_BUS_Voltage",
    ]
