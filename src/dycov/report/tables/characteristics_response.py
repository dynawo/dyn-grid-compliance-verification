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


def _ramp_error(
    results: dict,
    name: str,
    variable: str,
    thr_variable: str,
    check_variable: str,
    errors_map: list,
) -> None:
    if variable not in results:
        return

    value = printable.format_value(
        results,
        variable,
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    threshold = printable.format_value(
        results,
        thr_variable,
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    check = printable.format_latex_check(results[check_variable])
    errors_map.append(
        [
            name,
            "\\textemdash",
            "\\textemdash",
            value if results[check_variable] else f"\\textcolor{{red}}{{ {value} }}",
            threshold,
            check,
        ]
    )


def _time_error(
    results: dict, name: str, variable: str, errors_map: list, footnote_defined: bool = False
) -> bool:
    if "calc_" + variable not in results:
        return footnote_defined

    simulated_time = printable.format_value(
        results,
        "calc_" + variable,
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    reference_time = printable.format_value(
        results,
        "ref_" + variable,
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    abs_error, footnote_defined = printable.format_time_error(
        results,
        variable + "_error",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
        footnote_defined=footnote_defined,
    )
    threshold = printable.format_value(
        results,
        variable + "_thr",
        minimum_value=1.0e-8,
        apply_formatter=True,
        default_value="",
    )
    check = printable.format_compound_check(results[variable + "_check"])
    errors_map.append(
        [
            name,
            simulated_time,
            reference_time,
            abs_error if results[variable + "_check"] else f"\\textcolor{{red}}{{ {abs_error} }}",
            threshold,
            check,
        ]
    )
    return footnote_defined


def create_map(results: dict) -> list:
    """Creates a list to populate the characteristics table in the LaTex reports

    Parameters
    ----------
    results: dict
        Results of the validations applied in the pcs

    Returns
    -------
    list
        Characteristics table
    """
    errors_map = []
    footnote_defined = False
    footnote_defined = _time_error(
        results, "Reaction time", "reaction_time", errors_map, footnote_defined
    )
    footnote_defined = _time_error(
        results, "Rise time", "rise_time", errors_map, footnote_defined
    )
    footnote_defined = _time_error(
        results, "Settling time", "settling_time", errors_map, footnote_defined
    )
    footnote_defined = _time_error(
        results, "Overshoot", "overshoot", errors_map, footnote_defined
    )
    _ramp_error(
        results, "Ramp time lag", "ramp_time_lag", "ramp_time_thr", "ramp_time_check", errors_map
    )
    _ramp_error(
        results, "Ramp value error", "ramp_error", "ramp_error_thr", "ramp_error_check", errors_map
    )
    return errors_map
