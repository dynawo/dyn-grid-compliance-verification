#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#


def format_time_error(
    results: dict,
    key: str,
    minimum_value: float = 1.0e-4,
    apply_formatter: bool = False,
    add_seconds_unit: bool = False,
    default_value: str = "\\textemdash",
) -> str:
    """Gets a value for its key and formats it, if it is the character '-', add a
    footnote to the value.

    Parameters
    ----------
    results: dict
        Results of the validations applied.
    key: str
        Searched value key.
    minimum_value: float
        Minimum value allowed, any lower value will be considered 0.
    apply_formatter: bool
        True to apply floating point format.
    add_seconds_unit: bool
        Add units of seconds.
    default_value: str
        Default return value if the key does not exist.

    Returns
    -------
    str
        A formatted value
    """
    if results[key] == "-":
        return (
            f"\\footnote{{Not Calculated because the reference value "
            f"is exactly zero or very close to zero.}}{results[key]}".strip()
        )
    else:
        return format_value(
            results, key, minimum_value, apply_formatter, add_seconds_unit, default_value
        )


def format_value(
    results: dict,
    key: str,
    minimum_value: float = 1.0e-4,
    apply_formatter: bool = False,
    add_seconds_unit: bool = False,
    default_value: str = "\\textemdash",
) -> str:
    """Gets a value for its key and formats it.

    Parameters
    ----------
    results: dict
        Results of the validations applied.
    key: str
        Searched value key.
    minimum_value: float
        Minimum value allowed, any lower value will be considered 0.
    apply_formatter: bool
        True to apply floating point format.
    add_seconds_unit: bool
        Add units of seconds.
    default_value: str
        Default return value if the key does not exist.

    Returns
    -------
    str
        A formatted value
    """
    ret_val = default_value
    if key in results and results[key] != -1:
        if apply_formatter:
            if results[key] < minimum_value:
                ret_val = f"{0.0}"
            else:
                ret_val = f"{results[key]:.3g}".strip()
        else:
            if "_check" in key:
                ret_val = format_latex_check(results[key])
            else:
                ret_val = f"{results[key]}".strip()
        if add_seconds_unit:
            ret_val = ret_val + "s"

    return ret_val


def format_compound_check(value: str) -> str:
    if value == "N/A":
        return f"{{ {value} }}"
    else:
        return format_latex_check(value)


def format_latex_check(value: bool) -> str:
    """Formats a boolean variable based on its value.
    * If True return the boolean value as string
    * If False return the boolean value as red string

    Parameters
    ----------
    value: bool
        Value to format.

    Returns
    -------
    str
        The boolean value in the default color string if True, and red string if False
    """
    if value:
        return f"{{ {str(value)} }}"
    else:
        return f"\\textcolor{{red}}{{ {str(value)} }}"
