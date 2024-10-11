#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from dgcv.report import printable


def _setpoint_tracking_error(results: dict, measurement: str, errors_map: list) -> None:
    if "setpoint_tracking_" + measurement + "_check" not in results:
        return

    before_mxe = printable.format_value(
        results,
        "before_mxe_tc_" + measurement + "_value",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    before_mxe_check = results["before_mxe_tc_" + measurement + "_check"]
    before_me = printable.format_value(
        results,
        "before_me_tc_" + measurement + "_value",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    before_me_check = results["before_me_tc_" + measurement + "_check"]
    before_mae = printable.format_value(
        results,
        "before_mae_tc_" + measurement + "_value",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    before_mae_check = results["before_mae_tc_" + measurement + "_check"]
    after_mxe = printable.format_value(
        results,
        "after_mxe_tc_" + measurement + "_value",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    after_mxe_check = results["after_mxe_tc_" + measurement + "_check"]
    after_me = printable.format_value(
        results,
        "after_me_tc_" + measurement + "_value",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    after_me_check = results["after_me_tc_" + measurement + "_check"]
    after_mae = printable.format_value(
        results,
        "after_mae_tc_" + measurement + "_value",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    after_mae_check = results["after_mae_tc_" + measurement + "_check"]
    name = str(results["setpoint_tracking_" + measurement + "_name"])
    check = printable.format_latex_check(results["setpoint_tracking_" + measurement + "_check"])
    if "during_mxe_tc_" + measurement + "_value" in results:
        during_mxe = printable.format_value(
            results,
            "during_mxe_tc_" + measurement + "_value",
            minimum_value=1.0e-8,
            apply_formatter=True,
            default_value="",
        )
        during_mxe_check = results["during_mxe_tc_" + measurement + "_check"]
        during_me = printable.format_value(
            results,
            "during_me_tc_" + measurement + "_value",
            minimum_value=1.0e-8,
            apply_formatter=True,
            default_value="",
        )
        during_me_check = results["during_me_tc_" + measurement + "_check"]
        during_mae = printable.format_value(
            results,
            "during_mae_tc_" + measurement + "_value",
            minimum_value=1.0e-8,
            apply_formatter=True,
            default_value="",
        )
        during_mae_check = results["during_mae_tc_" + measurement + "_check"]
        errors_map.append(
            [
                name,
                before_mxe if before_mxe_check else f"\\textcolor{{red}}{{ {before_mxe} }}",
                before_me if before_me_check else f"\\textcolor{{red}}{{ {before_me} }}",
                before_mae if before_mae_check else f"\\textcolor{{red}}{{ {before_mae} }}",
                during_mxe if during_mxe_check else f"\\textcolor{{red}}{{ {during_mxe} }}",
                during_me if during_me_check else f"\\textcolor{{red}}{{ {during_me} }}",
                during_mae if during_mae_check else f"\\textcolor{{red}}{{ {during_mae} }}",
                after_mxe if after_mxe_check else f"\\textcolor{{red}}{{ {after_mxe} }}",
                after_me if after_me_check else f"\\textcolor{{red}}{{ {after_me} }}",
                after_mae if after_mae_check else f"\\textcolor{{red}}{{ {after_mae} }}",
                check,
            ]
        )
    else:
        errors_map.append(
            [
                name,
                before_mxe if before_mxe_check else f"\\textcolor{{red}}{{ {before_mxe} }}",
                before_me if before_me_check else f"\\textcolor{{red}}{{ {before_me} }}",
                before_mae if before_mae_check else f"\\textcolor{{red}}{{ {before_mae} }}",
                after_mxe if after_mxe_check else f"\\textcolor{{red}}{{ {after_mxe} }}",
                after_me if after_me_check else f"\\textcolor{{red}}{{ {after_me} }}",
                after_mae if after_mae_check else f"\\textcolor{{red}}{{ {after_mae} }}",
                check,
            ]
        )


def _voltage_dips_error(results: dict, name: str, measurement: str, errors_map: list) -> None:
    if "voltage_dips_" + measurement + "_check" not in results:
        return

    before_mxe = printable.format_value(
        results,
        "before_mxe_" + measurement + "_value",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    before_mxe_check = results["before_mxe_" + measurement + "_check"]
    before_me = printable.format_value(
        results,
        "before_me_" + measurement + "_value",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    before_me_check = results["before_me_" + measurement + "_check"]
    before_mae = printable.format_value(
        results,
        "before_mae_" + measurement + "_value",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    before_mae_check = results["before_mae_" + measurement + "_check"]
    after_mxe = printable.format_value(
        results,
        "after_mxe_" + measurement + "_value",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    after_mxe_check = results["after_mxe_" + measurement + "_check"]
    after_me = printable.format_value(
        results,
        "after_me_" + measurement + "_value",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    after_me_check = results["after_me_" + measurement + "_check"]
    after_mae = printable.format_value(
        results,
        "after_mae_" + measurement + "_value",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    after_mae_check = results["after_mae_" + measurement + "_check"]
    check = printable.format_latex_check(results["voltage_dips_" + measurement + "_check"])
    if "during_mxe_" + measurement + "_value" in results:
        during_mxe = printable.format_value(
            results,
            "during_mxe_" + measurement + "_value",
            minimum_value=1.0e-8,
            apply_formatter=True,
            default_value="",
        )
        during_mxe_check = results["during_mxe_" + measurement + "_check"]
        during_me = printable.format_value(
            results,
            "during_me_" + measurement + "_value",
            minimum_value=1.0e-8,
            apply_formatter=True,
            default_value="",
        )
        during_me_check = results["during_me_" + measurement + "_check"]
        during_mae = printable.format_value(
            results,
            "during_mae_" + measurement + "_value",
            minimum_value=1.0e-8,
            apply_formatter=True,
            default_value="",
        )
        during_mae_check = results["during_mae_" + measurement + "_check"]
        errors_map.append(
            [
                name,
                before_mxe if before_mxe_check else f"\\textcolor{{red}}{{ {before_mxe} }}",
                before_me if before_me_check else f"\\textcolor{{red}}{{ {before_me} }}",
                before_mae if before_mae_check else f"\\textcolor{{red}}{{ {before_mae} }}",
                during_mxe if during_mxe_check else f"\\textcolor{{red}}{{ {during_mxe} }}",
                during_me if during_me_check else f"\\textcolor{{red}}{{ {during_me} }}",
                during_mae if during_mae_check else f"\\textcolor{{red}}{{ {during_mae} }}",
                after_mxe if after_mxe_check else f"\\textcolor{{red}}{{ {after_mxe} }}",
                after_me if after_me_check else f"\\textcolor{{red}}{{ {after_me} }}",
                after_mae if after_mae_check else f"\\textcolor{{red}}{{ {after_mae} }}",
                check,
            ]
        )
    else:
        errors_map.append(
            [
                name,
                before_mxe if before_mxe_check else f"\\textcolor{{red}}{{ {before_mxe} }}",
                before_me if before_me_check else f"\\textcolor{{red}}{{ {before_me} }}",
                before_mae if before_mae_check else f"\\textcolor{{red}}{{ {before_mae} }}",
                after_mxe if after_mxe_check else f"\\textcolor{{red}}{{ {after_mxe} }}",
                after_me if after_me_check else f"\\textcolor{{red}}{{ {after_me} }}",
                after_mae if after_mae_check else f"\\textcolor{{red}}{{ {after_mae} }}",
                check,
            ]
        )


def create_map(results: dict) -> list:
    """Creates a list to populate the signal error table in the LaTex reports

    Parameters
    ----------
    results: dict
        Results of the validations applied in the pcs

    Returns
    -------
    list
        Signal error table
    """
    errors_map = []
    _setpoint_tracking_error(results, "controlled_magnitude", errors_map)
    _setpoint_tracking_error(results, "active_power", errors_map)
    _setpoint_tracking_error(results, "reactive_power", errors_map)

    _voltage_dips_error(results, "V", "voltage", errors_map)
    _voltage_dips_error(results, "P", "active_power", errors_map)
    _voltage_dips_error(results, "Q", "reactive_power", errors_map)
    _voltage_dips_error(results, "$I_p$", "active_current", errors_map)
    _voltage_dips_error(results, "$I_q$", "reactive_current", errors_map)

    return errors_map
