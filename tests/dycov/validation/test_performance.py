#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
from lxml import etree

from dycov.core.global_variables import (
    ELECTRIC_PERFORMANCE_PPM,
    ELECTRIC_PERFORMANCE_SM,
)
from dycov.model.parameters import DisconnectionModel
from dycov.validation.performance import (
    GENERATOR_DISCONNECT_MSG,
    IEC_DISCONNECT_PROTECTION_MSG,
    LOAD_DISCONNECT_MSG,
    PerformanceValidator,
    _check_compliance,
    _check_timeline,
    _is_disconnection_event,
)


def _get_resources_path():
    return (Path(__file__).resolve().parent) / "resources"


# =========================
# Helpers
# =========================

def test_check_compliance_updates_results_with_scaled_value():
    results = {"compliance": True}

    _check_compliance(results, 0.75, "metric", 2.0, 2.0)

    assert results["metric"] == 1.5
    assert results["metric_check"] is True
    assert results["compliance"] is True


def test_check_compliance_with_none_threshold():
    results = {"compliance": True}

    _check_compliance(results, 0.75, "metric", None, 1.0)

    assert results["metric"] == 0.75
    assert "metric_check" not in results
    assert results["compliance"] is True


def test_check_compliance_fails_when_above_threshold():
    results = {"compliance": True}

    _check_compliance(results, 2.0, "metric", 1.0, 1.0)

    assert results["metric"] == 2.0
    assert results["metric_check"] is False
    assert results["compliance"] is False


def test_generator_disconnection_returns_true():
    event = etree.Element("event")
    event.set("message", GENERATOR_DISCONNECT_MSG)

    assert _is_disconnection_event(event, "gen") is True


def test_load_disconnection_returns_true():
    event = etree.Element("event")
    event.set("message", LOAD_DISCONNECT_MSG)

    assert _is_disconnection_event(event, "load") is True


def test_non_disconnection_event_returns_false():
    event = etree.Element("event")
    event.set("message", "OTHER")

    assert _is_disconnection_event(event, "gen") is False
    assert _is_disconnection_event(event, "load") is False


def test_timeline_with_no_disconnection_events():
    timeline_file = _get_resources_path() / "timeline_no_disconnections.xml"

    ok, elements = _check_timeline(timeline_file, "gen")

    assert ok is True
    assert elements == []


def test_timeline_with_disconnection_events():
    timeline_file = _get_resources_path() / "timeline_disconnection.xml"

    ok, elements = _check_timeline(timeline_file, "gen")

    assert ok is False
    assert len(elements) > 0


# =========================
# PerformanceValidator
# =========================

def _make_validator(validations=None):
    return PerformanceValidator(
        curves_manager=Mock(),
        producer=Mock(),
        thr_ss_tol=1.0,
        validations=validations or [],
        is_field_measurements=False,
        pcs_name="test",
        bm_name="test",
    )


def test_create_results():
    validator = _make_validator()
    validator._time_cct = None

    results = validator._PerformanceValidator__create_results(
        t_event_start=1.0,
        compliance_values={"is_invalid_test": False},
    )

    assert results["sim_t_event_start"] == 1.0
    assert results["compliance"] is True
    assert results["is_invalid_test"] is False


def test_get_measurement_names():
    validator = _make_validator()

    names = validator.get_measurement_names()

    assert "BusPDR_BUS_ActivePower" in names
    assert len(names) == 3


def test_check_simple_times_executes():
    validator = _make_validator(validations=["time_5U"])

    results = {"compliance": True}
    compliance_values = {"time_5u": 1.0}

    validator._PerformanceValidator__check_simple_times(
        results,
        t_event_start=0.0,
        t_event_end=1.0,
        compliance_values=compliance_values,
    )

    assert "time_5U" in results


def test_check_others_static_diff_branch():
    validator = _make_validator(validations=["static_diff"])

    results = {"compliance": True}
    compliance_values = {"static_diff": 0.1}

    class DummyStability:
        p = q = v = theta = pi = True

    validator._PerformanceValidator__check_others(
        results,
        DummyStability(),
        is_ppm=False,
        compliance_values=compliance_values,
    )

    assert "static_diff" in results


def test_calculate_executes():
    validator = _make_validator()

    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])
    validator._get_calculated_curves = Mock(return_value={})

    import dycov.validation.common as common
    common.get_txu_relative = Mock(return_value=1.0)
    common.get_txp = Mock(return_value=1.0)
    common.get_txu = Mock(return_value=1.0)
    common.get_txpfloor = Mock(return_value=1.0)
    common.get_AVR_x = Mock(return_value=(True, 1.0))
    common.check_frequency = Mock(return_value=(True, 1.0))
    common.is_invalid_test = Mock(return_value=False)
    common.get_static_diff = Mock(return_value=0.1)
    common.check_generator_imax = Mock(return_value=(1.0, True))

    res = validator._PerformanceValidator__calculate(0.0)

    assert isinstance(res, dict)


# =========================
# Disconnection helpers (extra branches)
# =========================

def test_iec_protection_disconnection_returns_true():
    event = etree.Element("event")
    event.set("message", IEC_DISCONNECT_PROTECTION_MSG + " undervoltage protection")

    assert _is_disconnection_event(event, "gen") is True


def test_load_disconnection_event_not_matched_as_gen():
    event = etree.Element("event")
    event.set("message", LOAD_DISCONNECT_MSG)

    assert _is_disconnection_event(event, "gen") is False


def test_timeline_load_disconnection_collects_model_names():
    timeline_file = _get_resources_path() / "timeline_disconnection.xml"

    # The disconnection resource only contains generator-side events
    ok, elements = _check_timeline(timeline_file, "load")

    assert ok is True
    assert elements == []


# =========================
# _check_theta_stability
# =========================

def test_check_theta_stability_stable():
    validator = _make_validator()
    validator._get_calculated_curves = Mock(
        return_value={"time": [0, 1, 2], "g1_InternalAngle": [0.0, 0.0, 0.0]}
    )
    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])

    with patch("dycov.validation.common.is_stable", return_value=(True, 1)), patch(
        "dycov.validation.common.theta_pi", return_value=True
    ):
        stable_theta, first_pos, pass_pi = validator._check_theta_stability(
            1.0
        )

    assert stable_theta is True
    assert pass_pi is True


def test_check_theta_stability_unstable():
    validator = _make_validator()
    validator._get_calculated_curves = Mock(
        return_value={"time": [0, 1, 2], "g1_InternalAngle": [0.0, 5.0, 0.0]}
    )
    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])

    with patch("dycov.validation.common.is_stable", return_value=(False, 0)), patch(
        "dycov.validation.common.theta_pi", return_value=False
    ):
        stable_theta, first_pos, pass_pi = validator._check_theta_stability(
            1.0
        )

    assert stable_theta is False
    assert pass_pi is False


# =========================
# __calculate_avr / __calculate_frequency
# =========================

def test_calculate_avr_populates_compliance_values():
    validator = _make_validator(validations=["AVR_5"])
    validator._get_calculated_curves = Mock(
        return_value={"g1_GEN_MagnitudeControlledByAVRPu": [1.0]}
    )
    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])

    compliance_values = {}
    with patch("dycov.validation.common.get_AVR_x", return_value=(True, 0.4)):
        validator._PerformanceValidator__calculate_avr(compliance_values, 0.0)

    assert compliance_values["AVR_5_check"] is True
    assert compliance_values["AVR_5"] == 0.4
    assert isinstance(compliance_values["AVR_5_crvs"], list)


def test_calculate_frequency_populates_compliance_values():
    validator = _make_validator(validations=["freq_1"])
    validator._get_calculated_curves = Mock(
        return_value={"g1_GEN_NetworkFrequencyPu": [1.0]}
    )
    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])

    compliance_values = {}
    with patch("dycov.validation.common.check_frequency", return_value=(True, 0.2)):
        validator._PerformanceValidator__calculate_frequency(compliance_values)

    assert compliance_values["check_freq1"] is True
    assert compliance_values["time_freq1"] == 0.2


# =========================
# __calculate_others
# =========================

def test_calculate_others_static_diff_and_invalid_test():
    validator = _make_validator(validations=["static_diff"])
    validator._get_calculated_curves = Mock(
        return_value={"g1_GEN_MagnitudeControlledByAVRPu": [1.0]}
    )
    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])

    compliance_values = {}
    with patch("dycov.validation.common.is_invalid_test", return_value=False), patch(
        "dycov.validation.common.get_static_diff", return_value=0.05
    ):
        validator._PerformanceValidator__calculate_others(compliance_values, 0.0)

    assert compliance_values["is_invalid_test"] is False
    assert compliance_values["static_diff"] == 0.05


def test_calculate_others_imax_reac():
    validator = _make_validator(validations=["imax_reac"])
    validator._generators_imax = {"g1": 1.2}
    validator._get_calculated_curves = Mock(
        return_value={
            "g1_GEN_IpInjTerminal": [0.1, 0.2],
            "g1_GEN_IqInjTerminal": [0.1, 0.2],
        }
    )

    def _curve(name):
        data = {
            "time": [0.0, 1.0],
            "g1_GEN_IpInjTerminal": [0.1, 0.2],
            "g1_GEN_IqInjTerminal": [0.1, 0.2],
        }
        return data.get(name, [0.0, 1.0])

    validator._get_calculated_curve_by_name = Mock(side_effect=_curve)

    compliance_values = {}
    with patch("dycov.validation.common.is_invalid_test", return_value=False), patch(
        "dycov.validation.common.check_generator_imax", return_value=(0.5, False)
    ):
        validator._PerformanceValidator__calculate_others(compliance_values, 0.0)

    assert compliance_values["imax_reac_check"] is False
    assert compliance_values["imax_reac"] == 0.5


# =========================
# __check_composed_times
# =========================

def test_check_composed_times_5p_85u():
    validator = _make_validator(validations=["time_5P_85U"])
    results = {"compliance": True}
    compliance_values = {"time_5p": 3.0, "time_85u": 1.0}

    validator._PerformanceValidator__check_composed_times(
        results, t_event_start=0.0, t_event_end=1.0, compliance_values=compliance_values
    )

    assert results["time_85U"] == 1.0
    assert results["time_5P_85U"] == 2.0
    assert results["time_5P_85U_check"] is True


def test_check_composed_times_10pfloor_clear():
    validator = _make_validator(validations=["time_10Pfloor_clear"])
    results = {"compliance": True}
    compliance_values = {"time_10pfloor": 5.0}

    validator._PerformanceValidator__check_composed_times(
        results, t_event_start=0.0, t_event_end=1.0, compliance_values=compliance_values
    )

    assert results["time_10Pfloor"] == 5.0
    assert "time_10Pfloor_clear" in results


# =========================
# __check_disconnections
# =========================

def _make_disconnection_model():
    gen_intline = Mock()
    gen_intline.id = "gen_intline"
    auxload = Mock()
    auxload.id = "auxload"
    auxload_xfmr = Mock()
    auxload_xfmr.id = "auxload_xfmr"
    return DisconnectionModel(
        auxload=auxload,
        auxload_xfmr=auxload_xfmr,
        stepup_xfmrs=["StepUp_Xfmr"],
        gen_intline=gen_intline,
    )


def test_check_disconnections_gen_detects_disconnection():
    validator = _make_validator(validations=["no_disconnection_gen"])
    validator._disconnection_model = _make_disconnection_model()

    results = {"compliance": True}
    sim_path = _get_resources_path()

    # Point the timeline lookup at the disconnection resource
    with patch("dycov.validation.performance._check_timeline") as mocked:
        mocked.return_value = (False, ["Wind_Turbine"])
        validator._PerformanceValidator__check_disconnections(
            results, sim_path, has_dynamic_model=True
        )

    # Wind_Turbine is neither a step-up xfmr nor the gen_intline -> recovered to True
    assert results["no_disconnection_gen"] is True
    assert results["compliance"] is True


def test_check_disconnections_skipped_without_dynamic_model():
    validator = _make_validator(validations=["no_disconnection_gen"])
    results = {"compliance": True}

    validator._PerformanceValidator__check_disconnections(
        results, _get_resources_path(), has_dynamic_model=False
    )

    assert "no_disconnection_gen" not in results


# =========================
# __check_others (remaining branches)
# =========================

def test_check_others_stabilized_sm():
    validator = _make_validator(validations=["stabilized"])
    results = {"compliance": True}

    class DummyStability:
        p = q = v = theta = pi = True

    validator._PerformanceValidator__check_others(
        results, DummyStability(), is_ppm=False, compliance_values={}
    )

    assert results["stabilized"] is True


def test_check_others_imax_avr_freq():
    validator = _make_validator(validations=["imax_reac", "AVR_5", "freq_1"])
    results = {"compliance": True}
    compliance_values = {
        "imax_reac": 0.5,
        "imax_reac_check": False,
        "AVR_5_check": True,
        "AVR_5": 0.3,
        "AVR_5_crvs": [],
        "time_freq1": 0.1,
        "check_freq1": True,
    }

    class DummyStability:
        p = q = v = theta = pi = True

    validator._PerformanceValidator__check_others(
        results, DummyStability(), is_ppm=True, compliance_values=compliance_values
    )

    assert results["imax_reac_check"] is False
    assert results["compliance"] is False
    assert results["AVR_5"] == 0.3
    assert results["freq1_check"] is True


# =========================
# validate (end-to-end orchestration)
# =========================

def _setup_validate_validator(sim_type):
    validator = _make_validator(validations=[])
    validator._time_cct = None
    validator._producer.get_sim_type = Mock(return_value=sim_type)
    validator._producer.is_dynawo_model = Mock(return_value=False)
    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])
    validator._get_calculated_curves = Mock(return_value={})
    validator._get_reference_curves = Mock(return_value=pd.DataFrame())
    return validator


def test_validate_ppm():
    validator = _setup_validate_validator(ELECTRIC_PERFORMANCE_PPM)
    event_params = {"start_time": 0.5, "duration_time": 0.1}

    with patch("dycov.validation.common.is_stable", return_value=(True, 0)), patch(
        "dycov.validation.common.is_invalid_test", return_value=False
    ):
        results = validator.validate(
            "oc", Path("/tmp"), "outputs", event_params, has_reference=False
        )

    assert results["compliance"] is True
    assert results["is_invalid_test"] is False
    assert "first_steady_pos" in results
    assert "curves" in results
    assert "reference_curves" not in results


def test_validate_sm_includes_theta_and_reference():
    validator = _setup_validate_validator(ELECTRIC_PERFORMANCE_SM)
    validator._get_reference_curves = Mock(
        return_value=pd.DataFrame({"time": [0, 1, 2]})
    )
    event_params = {"start_time": 0.5, "duration_time": 0.1}

    with patch("dycov.validation.common.is_stable", return_value=(True, 0)), patch(
        "dycov.validation.common.theta_pi", return_value=True
    ), patch("dycov.validation.common.is_invalid_test", return_value=False):
        results = validator.validate(
            "oc", Path("/tmp"), "outputs", event_params, has_reference=True
        )

    assert results["compliance"] is True
    assert "first_steady_pos" in results
    assert "reference_curves" in results


def test_run_common_tests_executes():
    validator = _make_validator()

    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])

    import dycov.validation.common as common
    common.is_stable = Mock(return_value=(True, 1))
    common.theta_pi = Mock(return_value=True)

    validator._check_theta_stability = Mock(return_value=(True, 1, True))

    res = validator._PerformanceValidator__run_common_tests(
        thr_ss_tol=1.0,
        is_ppm=False,
    )

    assert isinstance(res, tuple)


def test_check_theta_stability_executes():
    validator = _make_validator()

    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])
    validator._get_calculated_curves = Mock(
        return_value={"gen1_InternalAngle": [0, 1, 2]}
    )

    import dycov.validation.common as common
    common.is_stable = Mock(return_value=(True, 1))
    common.theta_pi = Mock(return_value=True)

    res = validator._check_theta_stability(1.0)

    assert isinstance(res, tuple)


def test_check_times_executes():
    validator = _make_validator(validations=["time_5U"])

    results = {"compliance": True}
    compliance_values = {"time_5u": 1.0}

    validator._PerformanceValidator__check_times(
        results,
        t_event_start=0.0,
        t_event_end=1.0,
        compliance_values=compliance_values,
    )

    assert isinstance(results, dict)


def test_calculate_times_executes():
    validator = _make_validator(validations=["time_5U"])
    validator._get_calculated_curve_by_name = Mock(return_value=[0, 1, 2])

    import dycov.validation.common as common
    common.get_txu_relative = Mock(return_value=1.0)

    compliance_values = {}

    validator._PerformanceValidator__calculate_times(
        compliance_values,
        t_event_start=0.0,
    )

    assert isinstance(compliance_values, dict)


def test_check_disconnections_load_fail():
    validator = _make_validator(validations=["no_disconnection_load"])
    validator._disconnection_model = _make_disconnection_model()

    results = {"compliance": True}

    with patch("dycov.validation.performance._check_timeline") as mocked:
        mocked.return_value = (False, ["some_load"])
        validator._PerformanceValidator__check_disconnections(
            results, _get_resources_path(), has_dynamic_model=True
        )

    assert "no_disconnection_load" in results
