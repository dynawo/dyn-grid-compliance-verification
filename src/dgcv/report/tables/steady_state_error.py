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


def _steady_state_error(results: dict, name: str, measurement: str, errors_map: list) -> None:
    if "mae_" + measurement + "_1P_check" not in results:
        return

    mae_error = printable.format_value(
        results,
        "mae_" + measurement + "_1P",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    ss_error = printable.format_value(
        results,
        "ss_error_" + measurement + "_1P",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    check = printable.format_latex_check(results["mae_" + measurement + "_1P_check"])
    errors_map.append(
        [
            name,
            (
                mae_error
                if results["mae_" + measurement + "_1P_check"]
                else f"\\textcolor{{red}}{{ {mae_error} }}"
            ),
            ss_error,
            check,
        ]
    )


def create_map(results: dict) -> list:
    """Creates a list to populate the steady state error table in the LaTeX reports

    Parameters
    ----------
    results: dict
        Results of the validations applied in the pcs

    Returns
    -------
    list
        Steady state error table
    """
    errors_map = []
    _steady_state_error(results, "V", "voltage", errors_map)
    _steady_state_error(results, "P", "active_power", errors_map)
    _steady_state_error(results, "Q", "reactive_power", errors_map)
    _steady_state_error(results, "$I_p$", "active_current", errors_map)
    _steady_state_error(results, "$I_q$", "reactive_current", errors_map)

    return errors_map
