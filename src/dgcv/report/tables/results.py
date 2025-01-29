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


def _iterate_variables(results: dict, results_map: list):
    variables = [
        ["voltage", "V"],
        ["active_power", "P"],
        ["reactive_power", "Q"],
        ["active_current", "$I_p$"],
        ["reactive_current", "$I_q$"],
    ]

    for variable, col in variables:
        if "before_mxe_" + variable + "_value" in results:
            before_mxe = printable.format_value(
                results,
                "before_mxe_" + variable + "_value",
                minimum_value=1.0e-8,
                apply_formatter=True,
                default_value="",
            )
            before_me = printable.format_value(
                results,
                "before_me_" + variable + "_value",
                minimum_value=1.0e-8,
                apply_formatter=True,
                default_value="",
            )
            before_mae = printable.format_value(
                results,
                "before_mae_" + variable + "_value",
                minimum_value=1.0e-8,
                apply_formatter=True,
                default_value="",
            )
            after_mxe = printable.format_value(
                results,
                "after_mxe_" + variable + "_value",
                minimum_value=1.0e-8,
                apply_formatter=True,
                default_value="",
            )
            after_me = printable.format_value(
                results,
                "after_me_" + variable + "_value",
                minimum_value=1.0e-8,
                apply_formatter=True,
                default_value="",
            )
            after_mae = printable.format_value(
                results,
                "after_mae_" + variable + "_value",
                minimum_value=1.0e-8,
                apply_formatter=True,
                default_value="",
            )
            if "during_mxe_" + variable + "_value" in results:
                during_mxe = printable.format_value(
                    results,
                    "during_mxe_" + variable + "_value",
                    minimum_value=1.0e-8,
                    apply_formatter=True,
                    default_value="",
                )
                during_me = printable.format_value(
                    results,
                    "during_me_" + variable + "_value",
                    minimum_value=1.0e-8,
                    apply_formatter=True,
                    default_value="",
                )
                during_mae = printable.format_value(
                    results,
                    "during_mae_" + variable + "_value",
                    minimum_value=1.0e-8,
                    apply_formatter=True,
                    default_value="",
                )
                results_map.append(
                    [
                        col,
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
                results_map.append(
                    [col, before_mxe, before_me, before_mae, after_mxe, after_me, after_mae]
                )


def create_map(results: dict) -> list:
    """Creates a list to populate the results table in the LaTex reports

    Parameters
    ----------
    results: dict
        Results of the validations applied in the pcs

    Returns
    -------
    list
        Results table
    """
    results_map = []

    if "time_10U" in results:
        time_10U = printable.format_value(results, "time_10U", apply_formatter=True)
        results_map.append(["$T_{10U}$", time_10U + " s"])
    if "time_5U" in results:
        time_5U = printable.format_value(results, "time_5U", apply_formatter=True)
        results_map.append(["$T_{5U}$", time_5U + " s"])
    if "time_10P" in results:
        time_10P = printable.format_value(results, "time_10P", apply_formatter=True)
        results_map.append(["$T_{10P}$", time_10P + " s"])
    if "time_10Pfloor" in results:
        time_10Pfloor = printable.format_value(results, "time_10Pfloor", apply_formatter=True)
        results_map.append(["$T_{10P_{floor}}$", time_10Pfloor + " s"])
    if "time_5P" in results:
        time_5P = printable.format_value(results, "time_5P", apply_formatter=True)
        results_map.append(["$T_{5P}$", time_5P + " s"])
    if "time_85U" in results:
        time_85U = printable.format_value(results, "time_85U", apply_formatter=True)
        results_map.append(["$T_{85U}$", time_85U + " s"])
    if "time_cct" in results:
        time_cct = printable.format_value(results, "time_cct", apply_formatter=True)
        results_map.append(["$T_{cct}$", time_cct + " s"])
    if "static_diff" in results:
        static_diff = printable.format_value(results, "static_diff", apply_formatter=True)
        results_map.append(["$\epsilon$", static_diff])

    _iterate_variables(results, results_map)

    return results_map
