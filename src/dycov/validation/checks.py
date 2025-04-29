#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
import pandas as pd

from dycov.logging.logging import dycov_logging
from dycov.validation import common, threshold_variables


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


def _check_value_by_threshold(mxre: float, threshold: float) -> bool:
    return mxre < threshold


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


def _save_measurement_errors_by_error(
    compliance_values: dict,
    measurement: str,
    error: str,
    results: dict,
) -> None:
    _save_measurement_errors_by_error_window(
        compliance_values, measurement, error, "before", results
    )
    _save_measurement_errors_by_error_window(
        compliance_values, measurement, error, "after", results
    )
    _save_measurement_errors_by_error_window(
        compliance_values, measurement, error, "during", results
    )


def _save_measurement_errors_by_error_window(
    compliance_values: dict,
    measurement: str,
    error: str,
    window: str,
    results: dict,
) -> None:
    if compliance_values[window + "_" + error + "_" + measurement + "_value"] is not None:
        results[window + "_" + error + "_" + measurement + "_value"] = compliance_values[
            window + "_" + error + "_" + measurement + "_value"
        ]
        results[window + "_" + error + "_" + measurement + "_position"] = compliance_values[
            window + "_" + error + "_" + measurement + "_position"
        ]


def _check_measurement_by_error(
    compliance_values: dict,
    measurement: str,
    error: str,
    results: dict,
) -> None:
    _check_measurement_by_error_window(compliance_values, measurement, error, "before", results)
    _check_measurement_by_error_window(compliance_values, measurement, error, "after", results)
    _check_measurement_by_error_window(compliance_values, measurement, error, "during", results)


def _check_measurement_by_error_window(
    compliance_values: dict,
    measurement: str,
    error: str,
    window: str,
    results: dict,
) -> None:
    if compliance_values[window + "_" + error + "_" + measurement + "_check"] is not None:
        results[window + "_" + error + "_" + measurement + "_check"] = compliance_values[
            window + "_" + error + "_" + measurement + "_check"
        ]
        results["voltage_dips_" + measurement + "_check"] &= results[
            window + "_" + error + "_" + measurement + "_check"
        ]
        results["compliance"] &= results[window + "_" + error + "_" + measurement + "_check"]


def calculate_errors(
    curves: tuple[pd.DataFrame, pd.DataFrame],
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
    calculated_curves = curves[0]
    reference_curves = curves[1]
    results = {}
    if len(calculated_curves["time"]) == 0:
        return results

    for key in reference_curves:
        if key == "time":
            continue

        if key not in measurement_names:
            continue

        if key not in calculated_curves:
            dycov_logging.error(f"Curve {key} not found in simulation results.")
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


def complete_setpoint_tracking(
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


def save_measurement_errors(
    compliance_values: dict,
    measurement: str,
    results: dict,
) -> None:
    _save_measurement_errors_by_error(compliance_values, measurement, "mae", results)
    _save_measurement_errors_by_error(compliance_values, measurement, "me", results)
    _save_measurement_errors_by_error(compliance_values, measurement, "mxe", results)


def check_measurement(
    compliance_values: dict,
    measurement: str,
    results: dict,
) -> None:
    results["voltage_dips_" + measurement + "_check"] = True
    _check_measurement_by_error(compliance_values, measurement, "mae", results)
    _check_measurement_by_error(compliance_values, measurement, "me", results)
    _check_measurement_by_error(compliance_values, measurement, "mxe", results)


def calculate_curves_errors(
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
