#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

from dgcv.configuration.cfg import config
from dgcv.core.execution_parameters import Parameters
from dgcv.core.validator import Validator
from dgcv.logging.logging import dgcv_logging
from dgcv.sigpro import signal_windows, sigpro
from dgcv.validation import common, compliance_list, sanity_checks, threshold_variables


def _get_ss_tolerance(setpoint_variation: float) -> float:
    tolerance = config.get_float("GridCode", "thr_ss_tol", 0.002)
    if setpoint_variation > 0.0:
        tolerance = setpoint_variation * tolerance
    return tolerance


def _check_measure_curve_error(
    compliance_values: dict,
    measurement: str,
    error_type: str,
    threshold: float,
) -> tuple[float, bool]:
    error_value = compliance_values[measurement][error_type]
    if threshold:
        error_check = _check_value_by_threshold(error_value, threshold)
    else:
        error_check = None
    if "t" + error_type in compliance_values[measurement]:
        terror = compliance_values[measurement]["t" + error_type]
        yerror = compliance_values[measurement]["y" + error_type]
    else:
        terror = None
        yerror = None

    return error_value, error_check, terror, yerror


def _check_measure_curve_error_by_event(
    compliance_values: dict,
    measure: str,
    error: str,
    window_thresholds: dict,
) -> tuple[float, bool]:
    curve_value_error, curve_check_error, curve_terror, curve_yerror = _check_measure_curve_error(
        compliance_values,
        measure,
        error,
        threshold=window_thresholds[error],
    )
    return curve_value_error, curve_check_error, curve_terror, curve_yerror


def _check_setpoint_tracking_by_window(
    compliance_values: dict,
    measure: str,
    error: str,
) -> tuple[float, bool, float, bool, float, bool]:
    windows_thresholds = threshold_variables.get_setpoint_tracking_threshold_values()
    (
        before_value,
        before_check,
        before_t,
        before_y,
    ) = _check_measure_curve_error_by_event(
        compliance_values["before"],
        measure=measure,
        error=error,
        window_thresholds=windows_thresholds["before"],
    )

    if not compliance_values["during"]:
        during_value = None
        during_check = None
        during_t = None
        during_y = None
    else:
        (
            during_value,
            during_check,
            during_t,
            during_y,
        ) = _check_measure_curve_error_by_event(
            compliance_values["during"],
            measure=measure,
            error=error,
            window_thresholds=windows_thresholds["during"],
        )

    (
        after_value,
        after_check,
        after_t,
        after_y,
    ) = _check_measure_curve_error_by_event(
        compliance_values["after"],
        measure=measure,
        error=error,
        window_thresholds=windows_thresholds["after"],
    )
    return (
        before_value,
        before_check,
        [before_t, before_y],
        during_value,
        during_check,
        [during_t, during_y],
        after_value,
        after_check,
        [after_t, after_y],
    )


def _check_setpoint_tracking(
    compliance_values: dict,
    modified_setpoint: str,
    error: str,
):
    return _check_setpoint_tracking_by_window(
        compliance_values,
        _get_measurement_name(modified_setpoint),
        error,
    )


def _complete_setpoint_tracking_by_error(
    compliance_values: dict,
    modified_setpoint: str,
    measurement: str,
    error: str,
    results: dict,
) -> None:
    (
        before_value,
        before_check,
        before_position,
        during_value,
        during_check,
        during_position,
        after_value,
        after_check,
        after_position,
    ) = _check_setpoint_tracking(
        compliance_values,
        modified_setpoint=modified_setpoint,
        error=error,
    )
    if "setpoint_tracking_" + measurement + "_check" not in results:
        results["setpoint_tracking_" + measurement + "_check"] = True

    results["before_" + error + "_tc_" + measurement + "_value"] = before_value
    results["before_" + error + "_tc_" + measurement + "_check"] = before_check
    results["before_" + error + "_tc_" + measurement + "_position"] = before_position
    results["setpoint_tracking_" + measurement + "_check"] &= before_check
    results["compliance"] &= before_check

    results["after_" + error + "_tc_" + measurement + "_value"] = after_value
    results["after_" + error + "_tc_" + measurement + "_check"] = after_check
    results["after_" + error + "_tc_" + measurement + "_position"] = after_position
    results["setpoint_tracking_" + measurement + "_check"] &= after_check
    results["compliance"] &= after_check

    if during_value is not None:
        results["during_" + error + "_tc_" + measurement + "_value"] = during_value
        results["during_" + error + "_tc_" + measurement + "_check"] = during_check
        results["during_" + error + "_tc_" + measurement + "_position"] = during_position
        results["setpoint_tracking_" + measurement + "_check"] &= during_check
        results["compliance"] &= during_check


def _complete_setpoint_tracking(
    compliance_values: dict,
    modified_setpoint: str,
    measurement: str,
    results: dict,
) -> None:
    # MAE
    _complete_setpoint_tracking_by_error(
        compliance_values,
        modified_setpoint,
        measurement,
        "mae",
        results,
    )

    # ME
    _complete_setpoint_tracking_by_error(
        compliance_values,
        modified_setpoint,
        measurement,
        "me",
        results,
    )

    # MXE
    _complete_setpoint_tracking_by_error(
        compliance_values,
        modified_setpoint,
        measurement,
        "mxe",
        results,
    )


def _check_voltage_dips(
    compliance_values: dict,
    measure: str,
    error: str,
    is_field_measurements: bool = True,
) -> tuple[float, bool, float, bool, float, bool]:
    windows_thresholds = threshold_variables.get_voltage_dip_threshold_values(
        measure, is_field_measurements
    )
    (
        before_value,
        before_check,
        before_t,
        before_y,
    ) = _check_measure_curve_error_by_event(
        compliance_values["before"],
        measure=measure,
        error=error,
        window_thresholds=windows_thresholds["before"],
    )

    if not compliance_values["during"]:
        during_value = None
        during_check = None
        during_t = None
        during_y = None
    else:
        (
            during_value,
            during_check,
            during_t,
            during_y,
        ) = _check_measure_curve_error_by_event(
            compliance_values["during"],
            measure=measure,
            error=error,
            window_thresholds=windows_thresholds["during"],
        )

    (
        after_value,
        after_check,
        after_t,
        after_y,
    ) = _check_measure_curve_error_by_event(
        compliance_values["after"],
        measure=measure,
        error=error,
        window_thresholds=windows_thresholds["after"],
    )
    return (
        before_value,
        before_check,
        [before_t, before_y],
        during_value,
        during_check,
        [during_t, during_y],
        after_value,
        after_check,
        [after_t, after_y],
    )


def _calculate_curve_errors(
    measurement_name: str,
    measurement_type: str,
    is_field_measurements: bool,
    results: dict,
) -> None:
    # MAE
    (
        results[f"before_mae_{measurement_type}_value"],
        results[f"before_mae_{measurement_type}_check"],
        results[f"before_mae_{measurement_type}_position"],
        results[f"during_mae_{measurement_type}_value"],
        results[f"during_mae_{measurement_type}_check"],
        results[f"during_mae_{measurement_type}_position"],
        results[f"after_mae_{measurement_type}_value"],
        results[f"after_mae_{measurement_type}_check"],
        results[f"after_mae_{measurement_type}_position"],
    ) = _check_voltage_dips(
        results,
        measure=measurement_name,
        error="mae",
        is_field_measurements=is_field_measurements,
    )

    # ME
    (
        results[f"before_me_{measurement_type}_value"],
        results[f"before_me_{measurement_type}_check"],
        results[f"before_me_{measurement_type}_position"],
        results[f"during_me_{measurement_type}_value"],
        results[f"during_me_{measurement_type}_check"],
        results[f"during_me_{measurement_type}_position"],
        results[f"after_me_{measurement_type}_value"],
        results[f"after_me_{measurement_type}_check"],
        results[f"after_me_{measurement_type}_position"],
    ) = _check_voltage_dips(
        results,
        measure=measurement_name,
        error="me",
        is_field_measurements=is_field_measurements,
    )

    # MXE
    (
        results[f"before_mxe_{measurement_type}_value"],
        results[f"before_mxe_{measurement_type}_check"],
        results[f"before_mxe_{measurement_type}_position"],
        results[f"during_mxe_{measurement_type}_value"],
        results[f"during_mxe_{measurement_type}_check"],
        results[f"during_mxe_{measurement_type}_position"],
        results[f"after_mxe_{measurement_type}_value"],
        results[f"after_mxe_{measurement_type}_check"],
        results[f"after_mxe_{measurement_type}_position"],
    ) = _check_voltage_dips(
        results,
        measure=measurement_name,
        error="mxe",
        is_field_measurements=is_field_measurements,
    )


def _save_measurement_errors(
    compliance_values: dict,
    measurement: str,
    results: dict,
) -> None:
    _save_measurement_errors_by_error(compliance_values, measurement, "mae", results)
    _save_measurement_errors_by_error(compliance_values, measurement, "me", results)
    _save_measurement_errors_by_error(compliance_values, measurement, "mxe", results)


def _save_measurement_errors_by_error(
    compliance_values: dict,
    measurement: str,
    error: str,
    results: dict,
) -> None:
    results["before_" + error + "_" + measurement + "_value"] = compliance_values[
        "before_" + error + "_" + measurement + "_value"
    ]
    results["before_" + error + "_" + measurement + "_position"] = compliance_values[
        "before_" + error + "_" + measurement + "_position"
    ]
    results["after_" + error + "_" + measurement + "_value"] = compliance_values[
        "after_" + error + "_" + measurement + "_value"
    ]
    results["after_" + error + "_" + measurement + "_position"] = compliance_values[
        "after_" + error + "_" + measurement + "_position"
    ]

    if compliance_values["during_" + error + "_" + measurement + "_value"] is not None:
        results["during_" + error + "_" + measurement + "_value"] = compliance_values[
            "during_" + error + "_" + measurement + "_value"
        ]
        results["during_" + error + "_" + measurement + "_position"] = compliance_values[
            "during_" + error + "_" + measurement + "_position"
        ]


def _check_measurement(
    compliance_values: dict,
    measurement: str,
    results: dict,
) -> None:
    _check_measurement_by_error(compliance_values, measurement, "mae", results)
    _check_measurement_by_error(compliance_values, measurement, "me", results)
    _check_measurement_by_error(compliance_values, measurement, "mxe", results)


def _check_measurement_by_error(
    compliance_values: dict,
    measurement: str,
    error: str,
    results: dict,
) -> None:
    results["before_" + error + "_" + measurement + "_check"] = compliance_values[
        "before_" + error + "_" + measurement + "_check"
    ]
    results["voltage_dips_" + measurement + "_check"] = results[
        "before_" + error + "_" + measurement + "_check"
    ]
    results["compliance"] &= results["before_" + error + "_" + measurement + "_check"]

    results["after_" + error + "_" + measurement + "_check"] = compliance_values[
        "after_" + error + "_" + measurement + "_check"
    ]
    results["voltage_dips_" + measurement + "_check"] &= results[
        "after_" + error + "_" + measurement + "_check"
    ]
    results["compliance"] &= results["after_" + error + "_" + measurement + "_check"]

    if compliance_values["during_" + error + "_" + measurement + "_check"] is not None:
        results["during_" + error + "_" + measurement + "_check"] = compliance_values[
            "during_" + error + "_" + measurement + "_check"
        ]
        results["voltage_dips_" + measurement + "_check"] &= results[
            "during_" + error + "_" + measurement + "_check"
        ]
        results["compliance"] &= results["during_" + error + "_" + measurement + "_check"]


def _calculate_curves_errors(
    zone: int,
    is_field_measurements: bool,
    results: dict,
) -> None:
    _calculate_curve_errors(
        "BusPDR_BUS_ActivePower", "active_power", is_field_measurements, results
    )
    _calculate_curve_errors(
        "BusPDR_BUS_ReactivePower", "reactive_power", is_field_measurements, results
    )
    _calculate_curve_errors(
        "BusPDR_BUS_ActiveCurrent", "active_current", is_field_measurements, results
    )
    _calculate_curve_errors(
        "BusPDR_BUS_ReactiveCurrent", "reactive_current", is_field_measurements, results
    )
    _calculate_curve_errors("BusPDR_BUS_Voltage", "voltage", is_field_measurements, results)
    if zone == 3:
        _calculate_curve_errors("NetworkFrequencyPu", "frequency", is_field_measurements, results)


def _calculate_errors(
    calculated_curves: pd.DataFrame,
    reference_curves: pd.DataFrame,
    step_magnitude: float,
) -> dict:
    measurement_names = [
        "BusPDR_BUS_ActivePower",
        "BusPDR_BUS_ReactivePower",
        "BusPDR_BUS_ActiveCurrent",
        "BusPDR_BUS_ReactiveCurrent",
        "BusPDR_BUS_Voltage",
        "NetworkFrequencyPu",
    ]
    results = {}
    if len(calculated_curves["time"]) == 0:
        return results

    for key in reference_curves:
        if key == "time":
            continue

        if key not in measurement_names:
            continue

        if key not in calculated_curves:
            dgcv_logging.error(f"Curve {key} not found in simulation results.")
            continue

        tmxe, ymxe = common.maximum_error_position(
            calculated_curves["time"],
            calculated_curves[key],
            reference_curves[key],
        )

        results[key] = {
            "me": common.mean_error(
                calculated_curves[key],
                reference_curves[key],
                step_magnitude,
            ),
            "mae": common.mean_absolute_error(
                calculated_curves[key],
                reference_curves[key],
                step_magnitude,
            ),
            "mxe": common.maximum_error(
                calculated_curves[key],
                reference_curves[key],
                step_magnitude,
            ),
            "tmxe": tmxe,
            "ymxe": ymxe,
        }

    return results


def _check_value_by_threshold(mxre: float, threshold: float) -> bool:
    return mxre < threshold


def _get_column_name(
    modified_setpoint: str,
) -> str:
    if modified_setpoint == "ActivePowerSetpointPu":
        return "P"
    if modified_setpoint == "ReactivePowerSetpointPu":
        return "Q"
    if modified_setpoint == "AVRSetpointPu":
        return "V"
    if modified_setpoint == "NetworkFrequencyPu":
        return "$\\omega"

    return "Q"


def _get_measurement_name(
    modified_setpoint: str,
) -> str:
    if modified_setpoint == "ActivePowerSetpointPu":
        return "BusPDR_BUS_ActivePower"
    if modified_setpoint == "ReactivePowerSetpointPu":
        return "BusPDR_BUS_ReactivePower"
    if modified_setpoint == "AVRSetpointPu":
        return "BusPDR_BUS_Voltage"
    if modified_setpoint == "NetworkFrequencyPu":
        return "NetworkFrequencyPu"

    return "BusPDR_BUS_ReactivePower"


class ModelValidator(Validator):
    def __init__(
        self,
        pcs_bm_name: str,
        parameters: Parameters,
        validations: list,
        is_field_measurements: bool,
    ):
        super().__init__(validations, is_field_measurements)
        self._pcs_bm_name = pcs_bm_name
        self._producer = parameters.get_producer()

    def __active_power_recovery_error(
        self,
        calculated_curves: pd.DataFrame,
        reference_curves: pd.DataFrame,
        start_event: float,
        results: dict,
    ):
        if not compliance_list.contains_key(["active_power_recovery"], self._validations):
            return

        measurement_name = "BusPDR_BUS_ActivePower"
        t_P90_calc, _ = common.get_reached_time(
            0.9,
            list(calculated_curves["time"]),
            list(calculated_curves[measurement_name]),
            start_event,
        )
        t_P90_ref, _ = common.get_reached_time(
            0.9,
            list(reference_curves["time"]),
            list(reference_curves[measurement_name]),
            start_event,
        )

        results["t_P90_ref"] = t_P90_ref
        results["t_P90_error"] = abs(t_P90_ref - t_P90_calc)

    def __compare_event_times(
        self,
        measurement_name: str,
        calculated_curves: pd.DataFrame,
        reference_curves: pd.DataFrame,
        start_event: float,
        setpoint_variation: float,
        results: dict,
    ) -> None:
        results["t_event_start"] = start_event

        if compliance_list.contains_key(["reaction_time"], self._validations):
            res_reaction_time, res_reaction_target = common.get_reached_time(
                0.1,
                list(calculated_curves["time"]),
                list(calculated_curves[measurement_name]),
                start_event,
            )
            ref_reaction_time, ref_reaction_target = common.get_reached_time(
                0.1,
                list(reference_curves["time"]),
                list(reference_curves[measurement_name]),
                start_event,
            )
            results["calc_reaction_time"] = res_reaction_time
            results["ref_reaction_time"] = ref_reaction_time
            results["calc_reaction_target"] = {measurement_name: res_reaction_target}
            if ref_reaction_time != 0.0:
                results["reaction_time_error"] = (
                    abs(res_reaction_time - ref_reaction_time) / ref_reaction_time
                )
            else:
                results["reaction_time_error"] = "-"

        if compliance_list.contains_key(["rise_time"], self._validations):
            res_rise_time, res_rise_target = common.get_reached_time(
                0.9,
                list(calculated_curves["time"]),
                list(calculated_curves[measurement_name]),
                start_event,
            )
            ref_rise_time, ref_rise_target = common.get_reached_time(
                0.9,
                list(reference_curves["time"]),
                list(reference_curves[measurement_name]),
                start_event,
            )
            results["calc_rise_time"] = res_rise_time
            results["ref_rise_time"] = ref_rise_time
            results["calc_rise_target"] = {measurement_name: res_rise_target}
            if ref_rise_time != 0.0:
                results["rise_time_error"] = abs(res_rise_time - ref_rise_time) / ref_rise_time
            else:
                results["rise_time_error"] = "-"

        if compliance_list.contains_key(["response_time"], self._validations):
            res_response_time = common.get_response_time(
                _get_ss_tolerance(setpoint_variation),
                list(calculated_curves["time"]),
                list(calculated_curves[measurement_name]),
                start_event,
            )
            ref_response_time = common.get_response_time(
                _get_ss_tolerance(setpoint_variation),
                list(reference_curves["time"]),
                list(reference_curves[measurement_name]),
                start_event,
            )
            results["calc_response_time"] = res_response_time
            results["ref_response_time"] = ref_response_time
            if ref_response_time != 0.0:
                results["response_time_error"] = (
                    abs(res_response_time - ref_response_time) / ref_response_time
                )
            else:
                results["response_time_error"] = "-"

        if compliance_list.contains_key(["settling_time"], self._validations):
            (
                res_settling_time,
                _,
                res_settling_min,
                res_settling_max,
                calc_ss_value,
            ) = common.get_settling_time(
                _get_ss_tolerance(setpoint_variation),
                list(calculated_curves["time"]),
                list(calculated_curves[measurement_name]),
                start_event,
            )
            ref_settling_time, _, _, _, _ = common.get_settling_time(
                _get_ss_tolerance(setpoint_variation),
                list(reference_curves["time"]),
                list(reference_curves[measurement_name]),
                start_event,
            )
            results["calc_settling_time"] = res_settling_time
            results["calc_ss_value"] = calc_ss_value
            results["ref_settling_time"] = ref_settling_time
            results["calc_settling_tube"] = {
                measurement_name: [res_settling_min, res_settling_max]
            }
            if ref_settling_time != 0.0:
                results["settling_time_error"] = (
                    abs(res_settling_time - ref_settling_time) / ref_settling_time
                )
            else:
                results["settling_time_error"] = "-"

        if compliance_list.contains_key(["overshoot"], self._validations):
            res_overshoot = common.get_overshoot(
                list(calculated_curves[measurement_name]),
            )
            ref_overshoot = common.get_overshoot(
                list(reference_curves[measurement_name]),
            )
            results["calc_overshoot"] = res_overshoot
            results["ref_overshoot"] = ref_overshoot

    def __compare_ideal_ramp(
        self,
        measurement_name: str,
        calculated_curves: pd.DataFrame,
        t_event_start: float,
        t_event_duration: float,
        freq0: float,
        freq_peak: float,
        results: dict,
    ) -> None:

        if compliance_list.contains_key(["ramp_time_lag"], self._validations):
            ramp_time_lag = common.get_time_lag(
                list(calculated_curves["time"]),
                list(calculated_curves[measurement_name]),
                t_event_start,
                t_event_duration,
            )

            results["ramp_time_lag"] = ramp_time_lag

        # ramp variables from tableinfinitebus.txt
        if compliance_list.contains_key(["ramp_error"], self._validations):
            ramp_error = common.get_value_error(
                list(calculated_curves["time"]),
                list(calculated_curves[measurement_name]),
                t_event_start,
                t_event_duration,
                freq0,
                freq_peak,
            )

            results["ramp_error"] = ramp_error

    def __calculate_mean_absolute_error(
        self,
        measurement_name: str,
        calculated_curves: pd.DataFrame,
        reference_curves: pd.DataFrame,
        setpoint_variation: float,
        results: dict,
    ) -> None:
        _, ref_settlin_t_pos, _, _, _ = common.get_settling_time(
            _get_ss_tolerance(setpoint_variation),
            list(reference_curves["time"]),
            list(reference_curves[measurement_name]),
            reference_curves["time"][0],
        )

        _, res_settlin_t_pos, _, _, _ = common.get_settling_time(
            _get_ss_tolerance(setpoint_variation),
            list(calculated_curves["time"]),
            list(calculated_curves[measurement_name]),
            calculated_curves["time"][0],
        )

        if compliance_list.contains_key(["mean_absolute_error_voltage"], self._validations):
            calculated_curve = list(calculated_curves["BusPDR_BUS_Voltage"])[res_settlin_t_pos:]
            reference_curve = list(reference_curves["BusPDR_BUS_Voltage"])[res_settlin_t_pos:]
            results["mae_voltage_1P"] = common.mean_absolute_error(
                calculated_curve,
                reference_curve,
                1.0,
            )

            calculated_ss = np.average(
                list(calculated_curves["BusPDR_BUS_Voltage"])[res_settlin_t_pos:]
            )
            reference_ss = np.average(
                list(reference_curves["BusPDR_BUS_Voltage"])[ref_settlin_t_pos:]
            )
            results["ss_error_voltage_1P"] = abs(calculated_ss - reference_ss)

        if compliance_list.contains_key(["mean_absolute_error_power_1P"], self._validations):
            calculated_curve = list(calculated_curves["BusPDR_BUS_ActivePower"])[
                res_settlin_t_pos:
            ]
            reference_curve = list(reference_curves["BusPDR_BUS_ActivePower"])[res_settlin_t_pos:]
            results["mae_active_power_1P"] = common.mean_absolute_error(
                calculated_curve,
                reference_curve,
                1.0,
            )

            calculated_ss = np.average(
                list(calculated_curves["BusPDR_BUS_ActivePower"])[res_settlin_t_pos:]
            )
            reference_ss = np.average(
                list(reference_curves["BusPDR_BUS_ActivePower"])[ref_settlin_t_pos:]
            )
            results["ss_error_active_power_1P"] = abs(calculated_ss - reference_ss)

            calculated_curve = list(calculated_curves["BusPDR_BUS_ReactivePower"])[
                res_settlin_t_pos:
            ]
            reference_curve = list(reference_curves["BusPDR_BUS_ReactivePower"])[
                res_settlin_t_pos:
            ]
            results["mae_reactive_power_1P"] = common.mean_absolute_error(
                calculated_curve,
                reference_curve,
                1.0,
            )

            calculated_ss = np.average(
                list(calculated_curves["BusPDR_BUS_ReactivePower"])[res_settlin_t_pos:]
            )
            reference_ss = np.average(
                list(reference_curves["BusPDR_BUS_ReactivePower"])[ref_settlin_t_pos:]
            )
            results["ss_error_reactive_power_1P"] = abs(calculated_ss - reference_ss)

        if compliance_list.contains_key(["mean_absolute_error_injection_1P"], self._validations):
            calculated_curve = list(calculated_curves["BusPDR_BUS_ActiveCurrent"])[
                res_settlin_t_pos:
            ]
            reference_curve = list(reference_curves["BusPDR_BUS_ActiveCurrent"])[
                res_settlin_t_pos:
            ]
            results["mae_active_current_1P"] = common.mean_absolute_error(
                calculated_curve,
                reference_curve,
                1.0,
            )

            calculated_ss = np.average(
                list(calculated_curves["BusPDR_BUS_ActiveCurrent"])[res_settlin_t_pos:]
            )
            reference_ss = np.average(
                list(reference_curves["BusPDR_BUS_ActiveCurrent"])[ref_settlin_t_pos:]
            )
            results["ss_error_active_current_1P"] = abs(calculated_ss - reference_ss)

            calculated_curve = list(calculated_curves["BusPDR_BUS_ReactiveCurrent"])[
                res_settlin_t_pos:
            ]
            reference_curve = list(reference_curves["BusPDR_BUS_ReactiveCurrent"])[
                res_settlin_t_pos:
            ]
            results["mae_reactive_current_1P"] = common.mean_absolute_error(
                calculated_curve,
                reference_curve,
                1.0,
            )

            calculated_ss = np.average(
                list(calculated_curves["BusPDR_BUS_ReactiveCurrent"])[res_settlin_t_pos:]
            )
            reference_ss = np.average(
                list(reference_curves["BusPDR_BUS_ReactiveCurrent"])[ref_settlin_t_pos:]
            )
            results["ss_error_reactive_current_1P"] = abs(calculated_ss - reference_ss)

    def __calculate(
        self,
        zone: int,
        calculated_curves: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame],
        reference_curves: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame],
        start_event: float,
        duration_event: float,
        freq0: float,
        freq_peak: float,
        modified_setpoint: str,
        setpoint_variation: float,
    ) -> dict:
        step_magnitude = setpoint_variation
        if setpoint_variation == 0.0:
            step_magnitude = 1.0
        results = {
            "before": _calculate_errors(calculated_curves[0], reference_curves[0], step_magnitude),
            "during": _calculate_errors(calculated_curves[1], reference_curves[1], step_magnitude),
            "after": _calculate_errors(calculated_curves[2], reference_curves[2], step_magnitude),
            "is_invalid_test": common.is_invalid_test(
                list(calculated_curves[3]["time"]),
                list(calculated_curves[3]["BusPDR_BUS_Voltage"]),
                list(calculated_curves[3]["BusPDR_BUS_ActivePower"]),
                list(calculated_curves[3]["BusPDR_BUS_ReactivePower"]),
                start_event,
            ),
        }

        self.__active_power_recovery_error(
            calculated_curves[3],
            reference_curves[3],
            start_event,
            results,
        )

        measurement_name = _get_measurement_name(modified_setpoint)
        self.__compare_event_times(
            measurement_name,
            calculated_curves[3],
            reference_curves[3],
            start_event,
            setpoint_variation,
            results,
        )
        self.__compare_ideal_ramp(
            measurement_name,
            calculated_curves[3],
            start_event,
            duration_event,
            freq0,
            freq_peak,
            results,
        )
        _calculate_curves_errors(zone, self._is_field_measurements, results)
        self.__calculate_mean_absolute_error(
            measurement_name,
            calculated_curves[2],
            reference_curves[2],
            setpoint_variation,
            results,
        )

        return results

    def __create_results(
        self,
        compliance_values: dict,
    ) -> dict:
        return {
            "compliance": True,
            "times_check": True,
            "sim_t_event_start": compliance_values["t_event_start"],
            "is_invalid_test": compliance_values["is_invalid_test"],
            "curves_error": compliance_values,
        }

    def __check_times(
        self,
        check_results: dict,
        compliance_values: dict,
    ):
        if compliance_list.contains_key(["reaction_time"], self._validations):
            check_results["calc_reaction_target"] = compliance_values["calc_reaction_target"]
            check_results["calc_reaction_time"] = compliance_values["calc_reaction_time"]
            check_results["ref_reaction_time"] = compliance_values["ref_reaction_time"]
            thr_reaction_time = config.get_float("GridCode", "thr_reaction_time", 0.10)
            check_results["reaction_time_thr"] = thr_reaction_time * 100
            if compliance_values["reaction_time_error"] != "-":
                check_results["reaction_time_error"] = (
                    compliance_values["reaction_time_error"] * 100
                )
                check_results["reaction_time_check"] = (
                    compliance_values["reaction_time_error"] <= thr_reaction_time
                )
                check_results["times_check"] &= check_results["reaction_time_check"]
                check_results["compliance"] &= check_results["reaction_time_check"]
            else:
                check_results["reaction_time_error"] = compliance_values["reaction_time_error"]
                check_results["reaction_time_check"] = "N/A"

        if compliance_list.contains_key(["rise_time"], self._validations):
            check_results["calc_rise_target"] = compliance_values["calc_rise_target"]
            check_results["calc_rise_time"] = compliance_values["calc_rise_time"]
            check_results["ref_rise_time"] = compliance_values["ref_rise_time"]
            thr_rise_time = config.get_float("GridCode", "thr_rise_time", 0.10)
            check_results["rise_time_thr"] = thr_rise_time * 100
            if compliance_values["rise_time_error"] != "-":
                check_results["rise_time_error"] = compliance_values["rise_time_error"] * 100
                check_results["rise_time_check"] = (
                    compliance_values["rise_time_error"] <= thr_rise_time
                )
                check_results["times_check"] &= check_results["rise_time_check"]
                check_results["compliance"] &= check_results["rise_time_check"]
            else:
                check_results["rise_time_error"] = compliance_values["rise_time_error"]
                check_results["rise_time_check"] = "N/A"

        if compliance_list.contains_key(["settling_time"], self._validations):
            check_results["calc_settling_tube"] = compliance_values["calc_settling_tube"]
            check_results["calc_settling_time"] = compliance_values["calc_settling_time"]
            check_results["calc_ss_value"] = compliance_values["calc_ss_value"]
            check_results["ref_settling_time"] = compliance_values["ref_settling_time"]
            thr_settling_time = config.get_float("GridCode", "thr_settling_time", 0.10)
            check_results["settling_time_thr"] = thr_settling_time * 100
            if compliance_values["settling_time_error"] != "-":
                check_results["settling_time_error"] = (
                    compliance_values["settling_time_error"] * 100
                )
                check_results["settling_time_check"] = (
                    compliance_values["settling_time_error"] <= thr_settling_time
                )
                check_results["times_check"] &= check_results["settling_time_check"]
                check_results["compliance"] &= check_results["settling_time_check"]
            else:
                check_results["settling_time_error"] = compliance_values["settling_time_error"]
                check_results["settling_time_check"] = "N/A"

        if compliance_list.contains_key(["overshoot"], self._validations):
            calc_overshoot = compliance_values["calc_overshoot"]
            ref_overshoot = compliance_values["ref_overshoot"]
            thr_overshoot = config.get_float("GridCode", "thr_overshoot", 0.15)
            # Check if the overshoot values differ less than the relative threshold:
            rtol = thr_overshoot  # e.g., 15% relative error (0.15 per unit)
            atol = 0.01  # e.g, when magnitudes are below 0.01, switch to abs error
            check_results["overshoot_thr"] = thr_overshoot * 100
            check_results["overshoot_check"] = math.isclose(
                calc_overshoot,
                ref_overshoot,
                rel_tol=rtol,
                abs_tol=atol,
            )
            # We only calculate the % error if math.isclose() used relative tolerance:
            check_results["calc_overshoot"] = calc_overshoot
            check_results["ref_overshoot"] = ref_overshoot
            if rtol * max(abs(calc_overshoot), abs(ref_overshoot)) > atol and ref_overshoot != 0.0:
                check_results["overshoot_error"] = 100 * (
                    abs(calc_overshoot - ref_overshoot) / ref_overshoot
                )
            else:
                check_results["overshoot_error"] = "-"

    def __check_ramp(
        self,
        check_results: dict,
        compliance_values: dict,
    ):
        if compliance_list.contains_key(["ramp_time_lag"], self._validations):
            check_results["ramp_time_lag"] = compliance_values["ramp_time_lag"] * 100
            thr_ramp_time_lag = config.get_float("GridCode", "thr_ramp_time_lag", 0.10)
            check_results["ramp_time_thr"] = thr_ramp_time_lag * 100
            check_results["ramp_time_check"] = (
                compliance_values["ramp_time_lag"] <= thr_ramp_time_lag
            )
            check_results["times_check"] &= check_results["ramp_time_check"]
            check_results["compliance"] &= check_results["ramp_time_check"]

        if compliance_list.contains_key(["ramp_error"], self._validations):
            check_results["ramp_error"] = compliance_values["ramp_error"] * 100
            thr_ramp_error = config.get_float("GridCode", "thr_ramp_error", 0.10)
            check_results["ramp_error_thr"] = thr_ramp_error * 100
            check_results["ramp_error_check"] = compliance_values["ramp_error"] <= thr_ramp_error
            check_results["times_check"] &= check_results["ramp_error_check"]
            check_results["compliance"] &= check_results["ramp_error_check"]

    def __check_mae(
        self,
        check_results: dict,
        compliance_values: dict,
    ):
        thr_final_ss_mae = config.get_float("GridCode", "thr_final_ss_mae", 0.01)
        if compliance_list.contains_key(["mean_absolute_error_voltage"], self._validations):
            check_results["mae_voltage_1P"] = compliance_values["mae_voltage_1P"]
            check_results["ss_error_voltage_1P"] = compliance_values["ss_error_voltage_1P"]
            check_results["mae_voltage_1P_check"] = _check_value_by_threshold(
                compliance_values["mae_voltage_1P"], thr_final_ss_mae
            )

        if compliance_list.contains_key(["mean_absolute_error_power_1P"], self._validations):
            check_results["mae_active_power_1P"] = compliance_values["mae_active_power_1P"]
            check_results["ss_error_active_power_1P"] = compliance_values[
                "ss_error_active_power_1P"
            ]
            check_results["mae_active_power_1P_check"] = _check_value_by_threshold(
                compliance_values["mae_active_power_1P"], thr_final_ss_mae
            )
            check_results["compliance"] &= check_results["mae_active_power_1P_check"]

            check_results["mae_reactive_power_1P"] = compliance_values["mae_reactive_power_1P"]
            check_results["ss_error_reactive_power_1P"] = compliance_values[
                "ss_error_reactive_power_1P"
            ]
            check_results["mae_reactive_power_1P_check"] = _check_value_by_threshold(
                compliance_values["mae_reactive_power_1P"], thr_final_ss_mae
            )
            check_results["compliance"] &= check_results["mae_reactive_power_1P_check"]

        if compliance_list.contains_key(["mean_absolute_error_injection_1P"], self._validations):
            check_results["mae_active_current_1P"] = compliance_values["mae_active_current_1P"]
            check_results["ss_error_active_current_1P"] = compliance_values[
                "ss_error_active_current_1P"
            ]
            check_results["mae_active_current_1P_check"] = _check_value_by_threshold(
                compliance_values["mae_active_current_1P"], thr_final_ss_mae
            )
            check_results["compliance"] &= check_results["mae_active_current_1P_check"]

            check_results["mae_reactive_current_1P"] = compliance_values["mae_reactive_current_1P"]
            check_results["ss_error_reactive_current_1P"] = compliance_values[
                "ss_error_reactive_current_1P"
            ]
            check_results["mae_reactive_current_1P_check"] = _check_value_by_threshold(
                compliance_values["mae_reactive_current_1P"], thr_final_ss_mae
            )
            check_results["compliance"] &= check_results["mae_reactive_current_1P_check"]

    def __check(
        self,
        compliance_values: dict,
        modified_setpoint: str,
    ) -> dict:
        check_results = self.__create_results(compliance_values)

        self.__check_times(check_results, compliance_values)
        self.__check_ramp(check_results, compliance_values)
        self.__check_mae(check_results, compliance_values)

        _save_measurement_errors(compliance_values, "voltage", check_results)

        _save_measurement_errors(compliance_values, "active_power", check_results)
        if compliance_list.contains_key(["voltage_dips_active_power"], self._validations):
            _check_measurement(compliance_values, "active_power", check_results)

        _save_measurement_errors(compliance_values, "reactive_power", check_results)
        if compliance_list.contains_key(["voltage_dips_reactive_power"], self._validations):
            _check_measurement(compliance_values, "reactive_power", check_results)

        _save_measurement_errors(compliance_values, "active_current", check_results)
        if compliance_list.contains_key(["voltage_dips_active_current"], self._validations):
            _check_measurement(compliance_values, "active_current", check_results)

        _save_measurement_errors(compliance_values, "reactive_current", check_results)
        if compliance_list.contains_key(["voltage_dips_reactive_current"], self._validations):
            _check_measurement(compliance_values, "reactive_current", check_results)

        if compliance_list.contains_key(
            ["setpoint_tracking_controlled_magnitude"], self._validations
        ):
            _complete_setpoint_tracking(
                compliance_values,
                modified_setpoint,
                "controlled_magnitude",
                check_results,
            )
            check_results["setpoint_tracking_controlled_magnitude_name"] = _get_column_name(
                modified_setpoint
            )

        if compliance_list.contains_key(["setpoint_tracking_active_power"], self._validations):
            _complete_setpoint_tracking(
                compliance_values,
                "ActivePowerSetpointPu",
                "active_power",
                check_results,
            )
            check_results["setpoint_tracking_active_power_name"] = "P"

        if compliance_list.contains_key(["setpoint_tracking_reactive_power"], self._validations):
            _complete_setpoint_tracking(
                compliance_values,
                "ReactivePowerSetpointPu",
                "reactive_power",
                check_results,
            )
            check_results["setpoint_tracking_reactive_power_name"] = "Q"

        if compliance_list.contains_key(["active_power_recovery"], self._validations):
            check_results["t_P90_error"] = compliance_values["t_P90_error"]
            t_P90_threshold = min(compliance_values["t_P90_ref"] * 0.1, 100 / 1000)
            check_results["t_P90_threshold"] = t_P90_threshold
            check_results["t_P90_check"] = compliance_values["t_P90_error"] < t_P90_threshold
            check_results["compliance"] &= check_results["t_P90_check"]

        return check_results

    def validate(
        self,
        oc_name: str,
        working_path: Path,
        sim_output_path: str,
        event_params: dict,
        fs: float,
        curves: dict,
    ) -> dict:
        """Model Validation.

        Parameters
        ----------
        oc_name: str
            Operating condition name.
        working_path: Path
            Working path.
        sim_output_path: str
            Simulator output path (Not used in this validator).
        event_params: dict
            Event parameters
        fs: float
            Frequency sampling.

        Returns
        -------
        dict
            Compliance results
        """
        # Activate this code to use the curve calculated as a reference curve,
        # only for debug cases without reference curves.
        # if reference_curves is None:
        #     reference_curves = calculated_curves

        csv_calculated_curves = curves["calculated"]
        csv_calculated_curves.to_csv(working_path / "curves_calculated.csv", sep=";")
        if not curves["reference"].empty:
            csv_reference_curves = curves["reference"]
            csv_reference_curves.to_csv(working_path / "curves_reference.csv", sep=";")
        else:
            csv_reference_curves = None

        t_com = config.get_float("GridCode", "t_com", 0.002)
        cutoff = config.get_float("GridCode", "cutoff", 15.0)
        sanity_checks.check_sampling_interval(t_com, cutoff)

        resampling_fs = 1 / t_com

        # First resampling: Ensure constant time step signal.
        calculated_curves = sigpro.resampling_signal(csv_calculated_curves, resampling_fs)
        calculated_curves = sigpro.lowpass_signal(calculated_curves, cutoff, resampling_fs)

        reference_curves = sigpro.ensure_rms_signals(csv_reference_curves, fs)
        reference_curves = sigpro.resampling_signal(reference_curves, resampling_fs)
        reference_curves = sigpro.lowpass_signal(reference_curves, cutoff, resampling_fs)

        # Second resampling: Ensure same time grid for both signals.
        calculated_curves, reference_curves = sigpro.interpolate_same_time_grid(
            calculated_curves, reference_curves
        )

        t_integrator_tol = config.get_float("GridCode", "t_integrator_tol", 0.000001)
        if compliance_list.contains_key(
            ["setpoint_tracking_controlled_magnitude"], self._validations
        ):
            t_faultQS_excl = 0.0
            t_clearQS_excl = 0.0
        else:
            t_faultQS_excl = config.get_float("GridCode", "t_faultQS_excl", 0.020)
            t_clearQS_excl = config.get_float("GridCode", "t_clearQS_excl", 0.060)

        t_faultLP_excl = config.get_float("GridCode", "t_faultLP_excl", 0.050)
        before_calculated, during_calculated, after_calculated = signal_windows.get(
            calculated_curves,
            signal_windows.calculate(
                list(calculated_curves["time"]),
                event_params["start_time"],
                event_params["duration_time"],
                t_integrator_tol,
                t_faultLP_excl,
                t_faultQS_excl,
                t_clearQS_excl,
            ),
        )
        sanity_checks.check_pre_stable(
            list(before_calculated["time"]), list(before_calculated["BusPDR_BUS_Voltage"])
        )

        before_reference, during_reference, after_reference = signal_windows.get(
            reference_curves,
            signal_windows.calculate(
                list(reference_curves["time"]),
                event_params["start_time"],
                event_params["duration_time"],
                t_integrator_tol,
                t_faultLP_excl,
                t_faultQS_excl,
                t_clearQS_excl,
            ),
        )

        if dgcv_logging.getEffectiveLevel() == logging.DEBUG:
            calculated_curves.to_csv(working_path / "signal.csv", sep=";")
            reference_curves.to_csv(working_path / "reference.csv", sep=";")

        freq0 = 1.0
        freq_peak = 0.0
        if event_params["connect_to"] == "NetworkFrequencyPu":
            freq_peak = float(event_params["step_value"])

        model_results = self.__calculate(
            self._producer.get_zone(),
            (before_calculated, during_calculated, after_calculated, calculated_curves),
            (before_reference, during_reference, after_reference, reference_curves),
            event_params["start_time"],
            event_params["duration_time"],
            freq0,
            freq_peak,
            event_params["connect_to"],
            abs(self._setpoint_variation),
        )

        results = self.__check(
            model_results,
            event_params["connect_to"],
        )

        if not compliance_list.contains_key(
            ["setpoint_tracking_controlled_magnitude"], self._validations
        ):
            excl1_t0 = before_calculated["time"].iloc[-1]
            if len(during_calculated["time"]):
                excl1_t = during_calculated["time"].iloc[0]
                excl2_t0 = during_calculated["time"].iloc[-1]
                excl2_t = after_calculated["time"].iloc[0]
                results["excl1_t0"] = excl1_t0
                results["excl1_t"] = excl1_t
                results["excl2_t0"] = excl2_t0
                results["excl2_t"] = excl2_t
            else:
                excl1_t = after_calculated["time"].iloc[0]
                results["excl1_t0"] = excl1_t0
                results["excl1_t"] = excl1_t

        results["curves"] = calculated_curves
        if reference_curves is not None:
            results["reference_curves"] = reference_curves

        return results

    def get_measurement_names(self) -> list:
        """Get the list of required curves for the validation

        Returns
        -------
        list
            Required curves for the validation
        """
        if self._producer.get_zone() == 3:
            return [
                "BusPDR_BUS_ActivePower",
                "BusPDR_BUS_ReactivePower",
                "BusPDR_BUS_ActiveCurrent",
                "BusPDR_BUS_ReactiveCurrent",
                "BusPDR_BUS_Voltage",
                "NetworkFrequencyPu",
            ]
        return [
            "BusPDR_BUS_ActivePower",
            "BusPDR_BUS_ReactivePower",
            "BusPDR_BUS_ActiveCurrent",
            "BusPDR_BUS_ReactiveCurrent",
            "BusPDR_BUS_Voltage",
        ]
