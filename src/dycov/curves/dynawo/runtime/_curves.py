#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from dycov.core.global_variables import ABS_TOLERANCE_FACTOR, VOLTAGE_DIP_THRESHOLD

_FREQUENCY_PATTERNS = [
    r".*NetworkFrequencyPu$",
    r".*RotorSpeedPu$",
    r".*NetworkFrequencyReference$",
]


def _is_frequency_column(column_name: str) -> bool:
    return any(re.match(pattern, column_name) for pattern in _FREQUENCY_PATTERNS)


def _get_modulus(complex_list: list) -> list:
    return np.abs(complex_list).tolist()


def _drop_columns(df: pd.DataFrame, columns: list[str]) -> None:
    for col in columns:
        if col in df.columns:
            del df[col]


def load_raw_curves(input_file: Path) -> pd.DataFrame:
    """Load raw curves from a CSV file, removing any unnamed columns.

    Parameters
    ----------
    input_file : Path
        The path to the input CSV file containing the raw curves.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the raw curves, with unnamed columns removed.
    """
    df = pd.read_csv(input_file, sep=";")
    return df.loc[:, ~df.columns.str.contains("^Unnamed")]


def get_network_frequency_curve(curves_translation: dict) -> None:
    """Identify the network frequency curve in the curves translation and add it with a
    standardized name if found.

    Parameters
    ----------
    curves_translation : dict
        A dictionary mapping translated column names to their corresponding curve data. This
        function will search for any column that matches the frequency patterns and add it to the
        dictionary with the key "NetworkFrequencyPu" if found.
    """
    frequency_column_pattern = re.compile(r".*_NetworkFrequencyPu$")
    frequency_columns = list(filter(frequency_column_pattern.match, curves_translation.keys()))
    if frequency_columns:
        curves_translation["NetworkFrequencyPu"] = curves_translation[frequency_columns[0]]


def prepare_complex_column(
    column_name: str,
    column_size: int,
    df_curves: pd.DataFrame,
    translated_column: str,
    variable_translations: dict,
) -> list:
    """Prepare a complex column by combining its real and imaginary parts, applying the appropriate
    sign conventions.

    Parameters
    ----------
    column_name : str
        The base name of the complex variable (without the "_re" or "_im" suffix).
    column_size : int
        The number of rows in the curves DataFrame, used to initialize the complex array.
    df_curves : pd.DataFrame
        The DataFrame containing the raw curves, which includes the real and imaginary parts of the
        complex variable.
    translated_column : str
        The translated column name corresponding to the complex variable, used to look up sign
        conventions in the variable_translations dictionary.
    variable_translations : dict
        A dictionary mapping translated column names to their corresponding sign conventions. The
        function will look for entries with keys "{translated_column}Re" and
        "{translated_column}Im" to determine the signs for the real and imaginary parts,
        respectively.

    Returns
    -------
    list
        A list of complex numbers representing the combined real and imaginary parts with the
        appropriate sign conventions applied.

    """
    real_sign = f"{translated_column}Re"
    sign_real = variable_translations.get(real_sign, 1)
    imaginary_sign = f"{translated_column}Im"
    sign_imag = variable_translations.get(imaginary_sign, 1)

    complex_column_array = np.zeros(column_size, dtype=np.complex128)
    complex_column_array.real = np.multiply(df_curves[f"{column_name}re"], sign_real)
    complex_column_array.imag = np.multiply(df_curves[f"{column_name}im"], sign_imag)
    return complex_column_array.tolist()


def translate_complex_columns(
    variable_translations: dict,
    df_curves_imported: pd.DataFrame,
    curves_translation: dict,
    column: str,
    column_size: int,
) -> None:
    """Translate complex columns by preparing them using the real and imaginary parts, applying the
    appropriate sign conventions.

    Parameters
    ----------
    variable_translations : dict
        A dictionary mapping translated column names to their corresponding sign conventions.
    df_curves_imported : pd.DataFrame
        The DataFrame containing the raw curves.
    curves_translation : dict
        A dictionary to store the translated curve data.
    column : str
        The base name of the complex variable (without the "_re" or "_im" suffix).
    column_size : int
        The number of rows in the curves DataFrame.

    """
    for translated_column in variable_translations[column]:
        curves_translation[translated_column[:-2]] = prepare_complex_column(
            column[:-2],
            column_size,
            df_curves_imported,
            translated_column[:-2],
            variable_translations,
        )


def apply_sign_convention(
    variable_translations: dict,
    df_curves_imported: pd.DataFrame,
    curves_translation: dict,
    column: str,
) -> None:
    """Apply the sign convention to a non-complex column and store the translated curve data.

    Parameters
    ----------
    variable_translations : dict
        A dictionary mapping translated column names to their corresponding sign conventions.
    df_curves_imported : pd.DataFrame
        The DataFrame containing the raw curves.
    curves_translation : dict
        A dictionary to store the translated curve data.
    column : str
        The name of the column to which the sign convention should be applied.

    """
    for translated_column in variable_translations[column]:
        sign = variable_translations[translated_column]
        curves_translation[translated_column] = np.multiply(
            df_curves_imported[column], sign
        ).tolist()


def translate_curves(
    variable_translations: dict, df_curves_imported: pd.DataFrame
) -> pd.DataFrame:
    """Translate the raw curves by applying the appropriate sign conventions and combining real and
    imaginary parts for complex variables.

    Parameters
    ----------
    variable_translations : dict
        A dictionary mapping translated column names to their corresponding sign conventions.
    df_curves_imported : pd.DataFrame
        The DataFrame containing the raw curves, which includes the original column names and their
        corresponding data.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the translated curves, with the appropriate sign conventions applied
        and complex variables combined into single columns.
    """
    column_size = len(df_curves_imported["time"])
    curves_translation: dict = {"time": df_curves_imported["time"].tolist()}

    for column in variable_translations:
        if column not in df_curves_imported.columns:
            continue
        if column.endswith("_im"):
            continue
        if column.endswith("_re"):
            translate_complex_columns(
                variable_translations,
                df_curves_imported,
                curves_translation,
                column,
                column_size,
            )
        else:
            apply_sign_convention(
                variable_translations, df_curves_imported, curves_translation, column
            )

    get_network_frequency_curve(curves_translation)
    return pd.DataFrame(curves_translation)


def convert_columns(df_curves: pd.DataFrame, curves_dict: dict, f_nom: float) -> None:
    """Convert specific columns in the curves DataFrame to the appropriate units and store them in
    the curves dictionary.

    Parameters
    ----------
    df_curves : pd.DataFrame
        The DataFrame containing the translated curves, which includes the original column names
        and their corresponding data.
    curves_dict : dict
        A dictionary to store the converted curve data. The function will add entries to this
        dictionary for the converted columns.
    f_nom : float
        The nominal frequency, used to convert frequency-related columns to the appropriate units.

    """
    for col in df_curves.columns:
        if "_TE_" in col or col == "time":
            continue
        if _is_frequency_column(col):
            curves_dict[col] = (df_curves[col].astype(float) * f_nom).tolist()
        elif pd.api.types.is_complex_dtype(df_curves[col]):
            curves_dict[col] = _get_modulus(df_curves[col].tolist())
        else:
            curves_dict[col] = df_curves[col].tolist()


def _get_injector_terminal_curves(
    snref: float,
    snom: float,
    generators: list,
    df_curves: pd.DataFrame,
    curves_dict: dict,
) -> None:
    """Calculate the active and reactive current curves for generator injectors based on the
    voltage and power curves, applying the appropriate base conversion.

    Parameters
    ----------
    snref : float
        The reference apparent power, used for base conversion of the current curves.
    snom : float
        The nominal apparent power, used for base conversion of the current curves.
    generators : list
        A list of generator objects, which contain information about the generator IDs and their
        corresponding terminal curves.
    df_curves : pd.DataFrame
        The DataFrame containing the translated curves, which includes the voltage and power curves
        for the generator terminals.
    curves_dict : dict
        A dictionary to store the calculated current curves. The function will add entries to this
        dictionary for the active and reactive current curves of the generator injectors.
    """
    abs_tol = ABS_TOLERANCE_FACTOR * VOLTAGE_DIP_THRESHOLD
    columns_to_remove = []

    for generator in generators:
        voltage_col = f"{generator.id}_GEN_UPuInjTerminal"
        active_current_col = f"{generator.id}_GEN_IpInjTerminal"
        reactive_current_col = f"{generator.id}_GEN_IqInjTerminal"

        has_all_columns = (
            voltage_col in df_curves.columns
            and active_current_col in df_curves.columns
            and reactive_current_col in df_curves.columns
        )
        if not has_all_columns:
            continue

        active_current = np.multiply(
            df_curves[active_current_col].to_numpy(dtype=float), snref / snom
        )
        reactive_current = np.multiply(
            df_curves[reactive_current_col].to_numpy(dtype=float), snref / snom
        )
        voltage = _get_modulus(df_curves[voltage_col].tolist())
        voltage_array = np.array(voltage, dtype=float)

        curves_dict[voltage_col] = voltage
        valid_mask = np.isfinite(voltage_array) & (np.abs(voltage_array) > abs_tol)
        curves_dict[active_current_col] = np.divide(
            active_current, voltage_array, out=np.zeros_like(active_current), where=valid_mask
        ).tolist()
        curves_dict[reactive_current_col] = np.divide(
            reactive_current, voltage_array, out=np.zeros_like(reactive_current), where=valid_mask
        ).tolist()

        columns_to_remove.extend([voltage_col, active_current_col, reactive_current_col])

    _drop_columns(df_curves, columns_to_remove)


def _extract_and_scale_power_columns(
    df_curves: pd.DataFrame,
    curves_dict: dict,
    columns: dict[str, str],
    scale: float,
) -> None:
    for raw_col, canonical_col in columns.items():
        curves_dict[canonical_col] = np.multiply(
            df_curves[raw_col].to_numpy(dtype=float), scale
        ).tolist()
    _drop_columns(df_curves, list(columns.keys()))


def _get_tso_synchronous_condenser_curves(
    snref: float,
    snom: float,
    df_curves: pd.DataFrame,
    curves_dict: dict,
) -> None:
    frequency_col_raw = "SyncCompensator_GEN_FrequencyHz"
    active_power_col_raw = "SyncCompensator_GEN_ActivePower"
    reactive_power_col_raw = "SyncCompensator_GEN_ReactivePower"

    required = [frequency_col_raw, active_power_col_raw, reactive_power_col_raw]
    if not all(col in df_curves.columns for col in required):
        return

    curves_dict["SyncCompensator_GEN_TSO_FrequencyHz"] = (
        df_curves[frequency_col_raw].to_numpy(dtype=float).tolist()
    )
    _extract_and_scale_power_columns(
        df_curves,
        curves_dict,
        {
            active_power_col_raw: "SyncCompensator_GEN_TSO_ActivePower",
            reactive_power_col_raw: "SyncCompensator_GEN_TSO_ReactivePower",
        },
        snref / snom,
    )


def _get_tso_load_curves(
    snref: float,
    snom: float,
    df_curves: pd.DataFrame,
    curves_dict: dict,
) -> None:
    active_power_col_raw = "Main_load_LOAD_ActivePower"
    reactive_power_col_raw = "Main_load_LOAD_ReactivePower"

    required = [active_power_col_raw, reactive_power_col_raw]
    if not all(col in df_curves.columns for col in required):
        return

    _extract_and_scale_power_columns(
        df_curves,
        curves_dict,
        {
            active_power_col_raw: "Main_load_LOAD_TSO_ActivePower",
            reactive_power_col_raw: "Main_load_LOAD_TSO_ReactivePower",
        },
        snref / snom,
    )


def _get_magnitude_controlled_by_avr(
    generators: list, df_curves: pd.DataFrame, curves_dict: dict
) -> None:
    """Calculate the magnitude controlled by AVR curves for generators based on the available
    curves and the generator configurations, applying the appropriate sign conventions and
    combining real and imaginary parts if necessary.

    Parameters
    ----------
    generators : list
        A list of generator objects, which contain information about the generator IDs, their use
        of voltage droop, and the voltage droop factor.
    df_curves : pd.DataFrame
        The DataFrame containing the translated curves, which may include the magnitude controlled
        by AVR curves in different forms (e.g., separate real and imaginary parts, or combined).
    curves_dict : dict
        A dictionary to store the calculated magnitude controlled by AVR curves. The function will
        add entries to this dictionary for the magnitude controlled by AVR curves of the
        generators, andit will also keep track of any columns that should be removed from the
        DataFrame after processing.
    """
    columns_to_remove = []

    for generator in generators:
        variable = f"{generator.id}_GEN_MagnitudeControlledByAVRPu"
        u_variable = f"{generator.id}_GEN_MagnitudeControlledByAVRUPu"
        q_variable = f"{generator.id}_GEN_MagnitudeControlledByAVRQPu"

        has_u = u_variable in df_curves.columns
        if variable in df_curves.columns:
            curves_dict[variable] = df_curves[variable].tolist()
            columns_to_remove.append(variable)
        elif has_u:
            use_droop = generator.use_voltage_droop
            has_q = q_variable in df_curves.columns
            if use_droop and has_q:
                curve_u = df_curves[u_variable].to_numpy()
                curve_q = df_curves[q_variable].to_numpy()
                curves_dict[variable] = np.add(
                    curve_u, np.multiply(curve_q, generator.voltage_droop)
                ).tolist()
                columns_to_remove.extend([u_variable, q_variable])
            else:
                curves_dict[variable] = df_curves[u_variable].tolist()
                columns_to_remove.append(u_variable)
                if has_q:
                    columns_to_remove.append(q_variable)

    _drop_columns(df_curves, columns_to_remove)


def build_output_curves(
    df_curves: pd.DataFrame,
    df_curves_imported: pd.DataFrame,
    generators: list,
    s_nom: float,
    s_nref: float,
    f_nom: float,
) -> pd.DataFrame:
    """Build the output curves DataFrame by calculating the necessary curves based on the
    translated curves, the original imported curves, and the generator configurations, applying the
    appropriate base conversions and combining real and imaginary parts if necessary.

    Parameters
    ----------
    df_curves : pd.DataFrame
        The DataFrame containing the translated curves, which includes the original column names
        and their corresponding data after applying sign conventions and combining complex
        variables.
    df_curves_imported : pd.DataFrame
        The DataFrame containing the raw curves as imported from the CSV file, which includes the
        original column names and their corresponding data before translation.
    generators : list
        A list of generator objects, which contain information about the generator IDs, their use
        of voltage droop, and the voltage droop factor, used to calculate specific curves related
        to the generators.
    s_nom : float
        The nominal apparent power, used for base conversion of the power curves.
    s_nref : float
        The reference apparent power, used for base conversion of the power curves.
        f_nom : float
        The nominal frequency, used to convert frequency-related columns to the appropriate units.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the final output curves, with all necessary calculations and
        conversions applied, ready for use in the compliance assessment.
    """
    voltage_pu = df_curves["Measurements_BUS_Voltage"].to_numpy(dtype=float)

    active_power_pu = df_curves["Measurements_BUS_ActivePower"].to_numpy(dtype=float)
    reactive_power_pu = df_curves["Measurements_BUS_ReactivePower"].to_numpy(dtype=float)

    abs_tol = ABS_TOLERANCE_FACTOR * VOLTAGE_DIP_THRESHOLD
    power_base_factor = s_nref / s_nom
    active_power_pu = active_power_pu * power_base_factor
    reactive_power_pu = reactive_power_pu * power_base_factor

    curves_dict = {
        "time": df_curves_imported["time"].tolist(),
        "BusPDR_BUS_Voltage": voltage_pu.tolist(),
        "BusPDR_BUS_ActivePower": active_power_pu.tolist(),
        "BusPDR_BUS_ReactivePower": reactive_power_pu.tolist(),
    }

    curves_dict["BusPDR_BUS_ActiveCurrent"] = np.divide(
        active_power_pu,
        voltage_pu,
        out=np.zeros_like(active_power_pu),
        where=np.abs(voltage_pu) > abs_tol,
    ).tolist()

    curves_dict["BusPDR_BUS_ReactiveCurrent"] = np.divide(
        reactive_power_pu,
        voltage_pu,
        out=np.zeros_like(reactive_power_pu),
        where=np.abs(voltage_pu) > abs_tol,
    ).tolist()

    _get_magnitude_controlled_by_avr(generators, df_curves, curves_dict)
    _get_injector_terminal_curves(s_nref, s_nom, generators, df_curves, curves_dict)
    _get_tso_synchronous_condenser_curves(s_nref, s_nom, df_curves, curves_dict)
    _get_tso_load_curves(s_nref, s_nom, df_curves, curves_dict)
    convert_columns(df_curves, curves_dict, f_nom)

    return pd.DataFrame(curves_dict)


def create_curves(
    variable_translations: dict,
    input_file: Path,
    generators: list,
    s_nom: float,
    s_nref: float,
    f_nom: float,
) -> pd.DataFrame:
    """Create the final curves DataFrame by loading the raw curves, translating them, and building
    the output curves with all necessary calculations and conversions applied.

    Parameters
    ----------
    variable_translations : dict
        A dictionary mapping translated column names to their corresponding sign conventions, used
        to translate the raw curves and apply the appropriate sign conventions during the
        translation process.
    input_file : Path
        The path to the input CSV file containing the raw curves, which will be loaded and
        translated.
    generators : list
        A list of generator objects, which contain information about the generator IDs, their use
        of voltage droop, and the voltage droop factor, used to calculate specific curves related
        to the generators.
    s_nom : float
        The nominal apparent power, used for base conversion of the power curves.
    s_nref : float
        The reference apparent power, used for base conversion of the power curves.
    f_nom : float
        The nominal frequency, used to convert frequency-related columns to the appropriate units.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the final output curves, with all necessary calculations and
        conversions applied, ready for use in the compliance assessment.
    """

    df_curves_imported = load_raw_curves(input_file)
    df_curves = translate_curves(variable_translations, df_curves_imported)
    return build_output_curves(df_curves, df_curves_imported, generators, s_nom, s_nref, f_nom)
