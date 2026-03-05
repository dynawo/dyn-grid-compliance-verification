#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from dycov.validation import threshold_variables


def _setpoint_tracking_thresholds(results: dict, measurement: str, thresholds_map: list) -> None:
    windows_thresholds = threshold_variables.get_setpoint_tracking_threshold_values()

    if "setpoint_tracking_" + measurement + "_check" not in results:
        return

    before_mxe = windows_thresholds["before"]["mxe"]
    before_me = windows_thresholds["before"]["me"]
    before_mae = windows_thresholds["before"]["mae"]
    after_mxe = windows_thresholds["after"]["mxe"]
    after_me = windows_thresholds["after"]["me"]
    after_mae = windows_thresholds["after"]["mae"]
    name = str(results["setpoint_tracking_" + measurement + "_name"])
    if "during_mxe_" + measurement + "_value" in results:
        during_mxe = windows_thresholds["during"]["mxe"]
        during_me = windows_thresholds["during"]["me"]
        during_mae = windows_thresholds["during"]["mae"]
        thresholds_map.append(
            [
                name,
                before_mxe,
                before_me,
                before_mae,
                during_mxe,
                during_me,
                during_mae,
                after_mxe,
                after_me,
                after_mae,
            ]
        )
    else:
        thresholds_map.append(
            [
                name,
                before_mxe,
                before_me,
                before_mae,
                after_mxe,
                after_me,
                after_mae,
            ]
        )


def _get_measurement_name(
    measurement: str,
) -> str:
    if measurement == "active_power":
        return "BusPDR_BUS_ActivePower"
    if measurement == "reactive_power":
        return "BusPDR_BUS_ReactivePower"
    if measurement == "active_current":
        return "BusPDR_BUS_ActiveCurrent"
    if measurement == "reactive_current":
        return "BusPDR_BUS_ReactiveCurrent"
    if measurement == "voltage":
        return "BusPDR_BUS_Voltage"
    if measurement == "frequency":
        return "NetworkFrequencyPu"


def _voltage_dips_thresholds(
    results: dict, name: str, measurement: str, is_field_measurements: bool, thresholds_map: list
) -> None:
    windows_thresholds = threshold_variables.get_voltage_dip_threshold_values(
        _get_measurement_name(measurement), is_field_measurements
    )

    if "voltage_dips_" + measurement + "_check" not in results:
        return

    before_mxe = windows_thresholds["before"]["mxe"]
    before_me = windows_thresholds["before"]["me"]
    before_mae = windows_thresholds["before"]["mae"]
    after_mxe = windows_thresholds["after"]["mxe"]
    after_me = windows_thresholds["after"]["me"]
    after_mae = windows_thresholds["after"]["mae"]
    if "during_mxe_" + measurement + "_value" in results:
        during_mxe = windows_thresholds["during"]["mxe"]
        during_me = windows_thresholds["during"]["me"]
        during_mae = windows_thresholds["during"]["mae"]
        thresholds_map.append(
            [
                name,
                before_mxe,
                before_me,
                before_mae,
                during_mxe,
                during_me,
                during_mae,
                after_mxe,
                after_me,
                after_mae,
            ]
        )
    else:
        thresholds_map.append(
            [
                name,
                before_mxe,
                before_me,
                before_mae,
                after_mxe,
                after_me,
                after_mae,
            ]
        )


def create_map(results: dict, is_field_measurements: bool) -> list:
    """Creates a list to populate the signal thresholds table in the LaTex reports

    Parameters
    ----------
    results: dict
        Results of the validations applied in the pcs
    is_field_measurements: bool
        True if the reference signals are field measurements.

    Returns
    -------
    list
        Signal thresholds table
    """
    thresholds_map = []
    _setpoint_tracking_thresholds(results, "controlled_magnitude", thresholds_map)
    _setpoint_tracking_thresholds(results, "active_power", thresholds_map)
    _setpoint_tracking_thresholds(results, "reactive_power", thresholds_map)

    _voltage_dips_thresholds(results, "V", "voltage", is_field_measurements, thresholds_map)
    _voltage_dips_thresholds(results, "P", "active_power", is_field_measurements, thresholds_map)
    _voltage_dips_thresholds(results, "Q", "reactive_power", is_field_measurements, thresholds_map)
    _voltage_dips_thresholds(
        results, "$I_p$", "active_current", is_field_measurements, thresholds_map
    )
    _voltage_dips_thresholds(
        results, "$I_q$", "reactive_current", is_field_measurements, thresholds_map
    )

    return thresholds_map
