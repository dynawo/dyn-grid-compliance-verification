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


def _add_simple_times(results: dict, compliance_map: list):
    if "time_5U" in results:
        time_5U = printable.format_value(results, "time_5U", apply_formatter=True)
        check = printable.format_value(results, "time_5U_check")
        compliance_map.append(["$T_{5U} < 10 s$", time_5U, check])
    if "time_10U" in results:
        time_10U = printable.format_value(results, "time_10U", apply_formatter=True)
        check = printable.format_value(results, "time_10U_check")
        compliance_map.append(["$T_{10U} < 5 s$", time_10U, check])
    if "time_5P" in results and not ("time_5P_85U" in results or "time_5P_clear" in results):
        time_5P = printable.format_value(results, "time_5P", apply_formatter=True)
        check = printable.format_value(results, "time_5P_check")
        compliance_map.append(["$T_{5P} < 10 s$", time_5P, check])
    if "time_5P_clear" in results:
        time_5P_clear = printable.format_value(results, "time_5P_clear", apply_formatter=True)
        check = printable.format_value(results, "time_5P_clear_check")
        compliance_map.append(["$T_{5P}  - T_{clear} < 10 s$", time_5P_clear, check])
    if "time_10P" in results and not ("time_10P_85U" in results or "time_10P_clear" in results):
        time_10P = printable.format_value(results, "time_10P", apply_formatter=True)
        check = printable.format_value(results, "time_10P_check")
        compliance_map.append(["$T_{10P} < 5 s$", time_10P, check])
    if "time_10P_clear" in results:
        time_10P_clear = printable.format_value(results, "time_10P_clear", apply_formatter=True)
        check = printable.format_value(results, "time_10P_clear_check")
        compliance_map.append(["$T_{10P}  - T_{clear} < 5 s$", time_10P_clear, check])
    if "time_10Pfloor_clear" in results:
        time_10Pfloor_clear = printable.format_value(
            results, "time_10Pfloor_clear", apply_formatter=True
        )
        check = printable.format_value(results, "time_10Pfloor_clear_check")
        compliance_map.append(["$T_{10P_{floor}} - T_{clear} < 2 s$", time_10Pfloor_clear, check])


def _add_composed_times(results: dict, compliance_map: list):
    if "time_5P_85U" in results:
        time_5P_85U = printable.format_value(results, "time_5P_85U", apply_formatter=True)
        check = printable.format_value(results, "time_5P_85U_check")
        compliance_map.append(["$T_{5P}  - T_{85U} < 10 s$", time_5P_85U, check])
    if "time_10P_85U" in results:
        time_10P_85U = printable.format_value(results, "time_10P_85U", apply_formatter=True)
        check = printable.format_value(results, "time_10P_85U_check")
        compliance_map.append(["$T_{10P}  - T_{85U} < 5 s$", time_10P_85U, check])
    if "time_10Pfloor_85U" in results:
        time_10Pfloor_85U = printable.format_value(
            results, "time_10Pfloor_85U", apply_formatter=True
        )
        check = printable.format_value(results, "time_10Pfloor_85U_check")
        compliance_map.append(["$T_{10P_{floor}} - T_{85U} < 2 s$", time_10Pfloor_85U, check])


def _add_times(results: dict, compliance_map: list):
    _add_simple_times(results, compliance_map)
    _add_composed_times(results, compliance_map)


def create_map(results: dict) -> list:
    """Creates a list to populate the compliance table in the LaTeX reports

    Parameters
    ----------
    results: dict
        Results of the validations applied in the pcs

    Returns
    -------
    list
        Compliance table
    """

    compliance_map = []
    if "no_disconnection_gen" in results:
        no_disconnection_gen = printable.format_value(results, "no_disconnection_gen")
        compliance_map.append(
            ["Unit not disconnected by protections", "\\textemdash", no_disconnection_gen]
        )
    if "stabilized" in results:
        stabilized = printable.format_value(results, "stabilized")
        compliance_map.append(
            ["Unit remains stable (rotor stability)", "\\textemdash", stabilized]
        )
    if "no_disconnection_load" in results:
        no_disconnection_load = printable.format_value(results, "no_disconnection_load")
        compliance_map.append(
            ["Aux not disconnected by protections", "\\textemdash", no_disconnection_load]
        )
    if "freq1" in results:
        freq1 = printable.format_value(results, "freq1", add_seconds_unit=True)
        check = printable.format_value(results, "freq1_check")
        compliance_map.append(
            [
                "Frequency remains within [49, 51] Hz",
                f"\\footnote{{If non-compliant, time at which this happens.}}{freq1}",
                check,
            ]
        )
    if "AVR_5" in results:
        AVR_5 = printable.format_value(
            results, "AVR_5", apply_formatter=True, add_seconds_unit=True
        )
        check = printable.format_value(results, "AVR_5_check")
        compliance_map.append(
            [
                r"Stator voltage within $\pm 5\%$ of setpoint",
                f"\\footnote{{If non-compliant, time at which this happens.}}{AVR_5}",
                check,
            ]
        )
    if "static_diff" in results:
        static_diff = printable.format_value(results, "static_diff", apply_formatter=True)
        check = printable.format_value(results, "static_diff_check")
        compliance_map.append([r"$\epsilon < 0.2 \%$", static_diff, check])
    if "imax_reac" in results:
        imax_reac = printable.format_value(
            results, "imax_reac", apply_formatter=True, add_seconds_unit=True
        )
        check = printable.format_value(results, "imax_reac_check")
        compliance_map.append(
            [
                r"Reactive inj.\ prioritized if Imax reached",
                f"\\footnote{{If non-compliant, time at which this happens.}}{imax_reac}",
                check,
            ]
        )

    _add_times(results, compliance_map)

    return compliance_map
