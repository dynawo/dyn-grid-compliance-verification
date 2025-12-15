#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from dycov.report import printable


def create_map(results: dict) -> list:
    """Creates a list to populate the active power recovery error table in the LaTeX reports

    Parameters
    ----------
    results: dict
        Results of the validations applied in the pcs

    Returns
    -------
    list
        active power recovery error table
    """
    apr_map = []
    if "t_P90_error" in results:
        apr_map.append(
            [
                r"$Err_{T_\\text{90P}} < min(10\% T_\\text{$90P_\\text{ref}$}, 100ms)$",
                printable.format_value(
                    results,
                    "t_P90_error",
                    minimum_value=1.0e-8,
                    apply_formatter=True,
                    default_value="",
                ),
                printable.format_value(
                    results,
                    "t_P90_threshold",
                    minimum_value=1.0e-8,
                    apply_formatter=True,
                    default_value="",
                ),
                printable.format_latex_check(results["t_P90_check"]),
            ]
        )
    return apr_map
