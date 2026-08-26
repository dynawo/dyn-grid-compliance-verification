#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import numpy as np
import pandas as pd

from dycov.core.global_variables import ABS_TOLERANCE_FACTOR, VOLTAGE_DIP_THRESHOLD
from dycov.curves.naming import ZONE1_INJECTOR_NODE_LABEL
from dycov.logging import dycov_logging
from dycov.validation import common, threshold_variables

# Reported when a magnitude is absent from the curves, so its check cannot be computed
NOT_COMPUTABLE = "N/A"


def _get_measurement_name(
    modified_setpoint: str,
) -> str:
    if modified_setpoint == "ActivePowerSetpointPu":
        return "BusPDR_BUS_ActivePower"
    if modified_setpoint == "ReactivePowerSetpointPu":
        return "BusPDR_BUS_ReactivePower"
    if modified_setpoint == "VoltageSetpointPu":
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
) -> tuple[float, bool, float, bool] | None:
    """Returns None when the measurement is missing from the window: its error is then not
    computable, which is a different outcome from computable and out of threshold.
    """
    if measurement not in compliance_values:
        return None

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
) -> tuple[float, bool, float, bool] | None:
    return _check_measure_curve_error(
        compliance_values,
        measure,
        error,
        threshold=window_thresholds[error],
    )


def _aggregate_check(results: dict, key: str, check: bool | str | None) -> None:
    if check is None:
        return

    if NOT_COMPUTABLE in (check, results[key]):
        results[key] = NOT_COMPUTABLE
        return

    results[key] &= check


def _check_setpoint_tracking_by_window(
    compliance_values: dict,
    measure: str,
    error: str,
) -> dict:
    """Returns the error of every applicable window. The "during" window is absent from the
    result when the event has no such window; a window mapped to None holds a measurement whose
    error is not computable.
    """
    windows_thresholds = threshold_variables.get_setpoint_tracking_threshold_values()
    windows = {
        window: _check_measure_curve_error_by_event(
            compliance_values[window],
            measure=measure,
            error=error,
            window_thresholds=windows_thresholds[window],
        )
        for window in ("before", "after")
    }
    if compliance_values["during"]:
        windows["during"] = _check_measure_curve_error_by_event(
            compliance_values["during"],
            measure=measure,
            error=error,
            window_thresholds=windows_thresholds["during"],
        )
    return windows


def _check_setpoint_tracking(
    compliance_values: dict,
    modified_setpoint: str,
    error: str,
) -> dict:
    return _check_setpoint_tracking_by_window(
        compliance_values,
        _get_measurement_name(modified_setpoint),
        error,
    )


def _complete_setpoint_tracking_by_window(
    window_error: tuple | None,
    prefix: str,
    tracking_check: str,
    results: dict,
) -> None:
    if window_error is None:
        results[prefix + "_check"] = NOT_COMPUTABLE
        results[tracking_check] = NOT_COMPUTABLE
        results["compliance"] = False
        return

    error_value, error_check, terror, yerror = window_error
    results[prefix + "_value"] = error_value
    results[prefix + "_check"] = error_check
    results[prefix + "_position"] = [terror, yerror]
    _aggregate_check(results, tracking_check, error_check)
    _aggregate_check(results, "compliance", error_check)


def _complete_setpoint_tracking_by_error(
    compliance_values: dict,
    modified_setpoint: str,
    measurement: str,
    error: str,
    results: dict,
) -> None:
    windows = _check_setpoint_tracking(
        compliance_values,
        modified_setpoint=modified_setpoint,
        error=error,
    )
    tracking_check = "setpoint_tracking_" + measurement + "_check"
    results.setdefault(tracking_check, True)

    for window in ("before", "after", "during"):
        if window not in windows:
            continue

        _complete_setpoint_tracking_by_window(
            windows[window],
            f"{window}_{error}_tc_{measurement}",
            tracking_check,
            results,
        )


def _check_voltage_dips(
    compliance_values: dict,
    measure: str,
    error: str,
    is_field_measurements: bool = True,
) -> tuple[float, bool, list, float, bool, list, float, bool, list]:
    windows_thresholds = threshold_variables.get_voltage_dip_threshold_values(
        measure, is_field_measurements
    )
    checked_windows = []
    for window in ("before", "during", "after"):
        if compliance_values[window]:
            window_error = _check_measure_curve_error_by_event(
                compliance_values[window],
                measure=measure,
                error=error,
                window_thresholds=windows_thresholds[window],
            )
        else:
            window_error = None

        error_value, error_check, terror, yerror = window_error or (None, None, None, None)
        checked_windows += [error_value, error_check, [terror, yerror]]

    return tuple(checked_windows)


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
    if window + "_" + error + "_" + measurement + "_value" not in compliance_values:
        return

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
    check_key = window + "_" + error + "_" + measurement + "_check"
    dips_check = "voltage_dips_" + measurement + "_check"
    if check_key not in compliance_values:
        results[check_key] = NOT_COMPUTABLE
        results[dips_check] = NOT_COMPUTABLE
        results["compliance"] = False
        return

    if compliance_values[check_key] is not None:
        results[check_key] = compliance_values[check_key]
        _aggregate_check(results, dips_check, results[check_key])
        _aggregate_check(results, "compliance", results[check_key])


def calculate_errors(
    curves: tuple[pd.DataFrame, pd.DataFrame],
    step_magnitude: float,
) -> dict:
    """Calculates the error metrics (ME, MAE, MXE) and their associated positions by comparing
    the calculated curves with the reference curves.

    Parameters
    ----------
    curves : tuple[pd.DataFrame, pd.DataFrame]
        A tuple containing the calculated curves and the reference curves as pandas DataFrames.
    step_magnitude : float
        The magnitude of the step change applied to the setpoint, used for normalizing the error
        values.

    Returns
    -------
    dict
        A dictionary containing the error values for each measurement.
    """
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

        error_position = common.maximum_error_position(
            calculated_curves["time"],
            calculated_curves[key],
            reference_curves[key],
            key,
        )
        if error_position is None:
            continue

        tmxe, ymxe, yref = error_position
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
            "yref": yref,
        }

    return results


def complete_setpoint_tracking(
    compliance_values: dict,
    modified_setpoint: str,
    measurement: str,
    results: dict,
) -> None:
    """Completes the setpoint tracking results for a specific measurement and error type by
    checking the compliance values and updating the results dictionary accordingly.

    Parameters
    ----------
    compliance_values : dict
        A dictionary containing the calculated error values and their compliance status for the
        specified measurement and error type.
    modified_setpoint : str
        The name of the modified setpoint being analyzed (e.g., "ActivePowerSetpointPu",
        "VoltageSetpointPu", etc.).
    measurement : str
        The name of the measurement being checked (e.g., "active_power", "voltage", etc.).
    results : dict
        A dictionary to store the completed setpoint tracking results for the measurement. The
        function will update this dictionary with the compliance status and error values for each
        error type (MAE, ME, MXE) and for each time window (before, during, after).
    """
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
    """Saves the calculated error values for a specific measurement and error type into the results
     dictionary.

    Parameters
    ----------
    compliance_values : dict
        A dictionary containing the calculated error values for the specified measurement and error
        type.
    measurement : str
        The name of the measurement for which the error values are being saved (e.g., "voltage",
        "active_power", etc.).
    results : dict
        A dictionary to store the error values for the measurement. The function will update this
        dictionary with the error values for each error type (MAE, ME, MXE).
    """
    _save_measurement_errors_by_error(compliance_values, measurement, "mae", results)
    _save_measurement_errors_by_error(compliance_values, measurement, "me", results)
    _save_measurement_errors_by_error(compliance_values, measurement, "mxe", results)


def check_measurement(
    compliance_values: dict,
    measurement: str,
    results: dict,
) -> None:
    """Checks the compliance of a specific measurement against the defined thresholds for MAE, ME,
    and MXE errors, and updates the results dictionary with the compliance status.

    Parameters
    ----------
    compliance_values : dict
        A dictionary containing the calculated error values and their compliance status for the
        specified measurement.
    measurement : str
        The name of the measurement being checked (e.g., "voltage", "active_power", etc.).
    results : dict
        A dictionary to store the compliance check results for the measurement. The function will
        update this dictionary with the compliance status for each error type (MAE, ME, MXE)

    """
    results["voltage_dips_" + measurement + "_check"] = True
    _check_measurement_by_error(compliance_values, measurement, "mae", results)
    _check_measurement_by_error(compliance_values, measurement, "me", results)
    _check_measurement_by_error(compliance_values, measurement, "mxe", results)


def calculate_curves_errors(
    zone: int,
    is_field_measurements: bool,
    results: dict,
) -> None:
    """Calculates and checks the errors for the relevant curves based on the specified zone and
    measurement type.

    Parameters
    ----------
    zone : int
        The zone for which to calculate the errors (e.g., 1, or 3).
    is_field_measurements : bool
        Indicates whether the measurements are field measurements or not.
    results : dict
        A dictionary to store the calculated error values and compliance checks.
    """

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


def _has_voltage_below_guard(curves: pd.DataFrame, abs_tol: float) -> bool:
    for column in curves.columns:
        if not column.endswith("_GEN_UPuInjTerminal"):
            continue
        voltage = np.abs(curves[column].to_numpy(dtype=float))
        finite_voltage = voltage[np.isfinite(voltage)]
        if finite_voltage.size and finite_voltage.min() <= abs_tol:
            return True
    return False


def get_injector_voltage_guard_warnings(
    calculated_curves: pd.DataFrame,
    reference_curves: pd.DataFrame,
) -> list[str]:
    """Warns when an injector terminal voltage falls below the numerical guard used to
    compute the terminal currents (Ip = P/U, Iq = Q/U), which zeroes them out.

    Parameters
    ----------
    calculated_curves : pd.DataFrame
        Calculated curves.
    reference_curves : pd.DataFrame
        Reference curves.

    Returns
    -------
    list[str]
        One warning message per curve set whose injector terminal voltage crosses the guard.
    """
    abs_tol = ABS_TOLERANCE_FACTOR * VOLTAGE_DIP_THRESHOLD
    warnings = []
    for label, curves in (("calculated", calculated_curves), ("reference", reference_curves)):
        if curves is None or curves.empty:
            continue
        if _has_voltage_below_guard(curves, abs_tol):
            warnings.append(
                f"Computation of Ip/Iq at {ZONE1_INJECTOR_NODE_LABEL} is probably not "
                f"consistent for this test: the {label} injector terminal voltage falls "
                f"below the {abs_tol:.1e} pu numerical guard; check the transformer "
                "impedance value."
            )
    return warnings
