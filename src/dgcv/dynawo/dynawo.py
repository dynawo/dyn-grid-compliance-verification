#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import os
import re
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
from lxml import etree

from dgcv.configuration.cfg import config
from dgcv.logging.logging import dgcv_logging
from dgcv.validation.common import is_stable


def _compile_model_name(models_path: Path, model_name: str):
    model_tree = etree.parse(models_path / model_name, etree.XMLParser(remove_blank_text=True))
    model_root = model_tree.getroot()
    dyn = etree.QName(model_root).namespace
    modelica_model = model_root.find(f"{{{dyn}}}modelicaModel")
    if modelica_model is not None:
        return modelica_model.get("id")
    return None


def _precompile_model(
    launcher_dwo: Path,
    models_path: Path,
    model_name: str,
    output_path: Path,
) -> None:
    compiled_model = _compile_model_name(models_path, model_name)
    if os.name == "nt":
        extension = ".dll"
    else:
        extension = ".so"

    if compiled_model is not None and (output_path / (compiled_model + extension)).is_file():
        dgcv_logging.get_logger("Dynawo").debug(f"{compiled_model} was compiled")
        return

    dgcv_logging.get_logger("Dynawo").info(f"Precompile {model_name}")
    with open(output_path / "compile.log", "a") as log_file:
        if os.name == "nt":
            dgcv_logging.get_logger("Dynawo").info(
                "cd "
                + str(Path(__file__).parent.resolve())
                + " && "
                + "Vsx64.cmd"
                + " "
                + str(models_path)
                + " "
                + str(launcher_dwo)
                + " "
                + str(model_name)
                + " "
                + str(output_path)
                + " "
                + str(compiled_model + extension)
                + " "
                + str(compiled_model + ".desc.xml")
                + ""
            )
            subprocess.run(
                [
                    Path(__file__).parent.resolve() / "Vsx64.cmd",
                    models_path,
                    launcher_dwo,
                    model_name,
                    output_path,
                    compiled_model + extension,
                    compiled_model + ".desc.xml",
                ],
                cwd=Path(__file__).parent.resolve(),
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
        else:
            dgcv_logging.get_logger("Dynawo").info(
                "cd "
                + str(models_path)
                + " && "
                + str(launcher_dwo)
                + " jobs --generate-preassembled --model-list "
                + str(model_name)
                + " --non-recursive-modelica-models-dir . --output-dir "
                + str(output_path)
                + " && "
                + "cd "
                + str(output_path)
                + " && "
                + str(launcher_dwo)
                + " jobs --dump-model --model-file "
                + str(compiled_model + extension)
                + " --output-file "
                + str(compiled_model)
                + ".desc.xml"
            )
            subprocess.run(
                [
                    launcher_dwo,
                    "jobs",
                    "--generate-preassembled",
                    "--model-list",
                    model_name,
                    "--non-recursive-modelica-models-dir",
                    ".",
                    "--output-dir",
                    output_path,
                ],
                cwd=models_path,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
            subprocess.run(
                [
                    launcher_dwo,
                    "jobs",
                    "--dump-model",
                    "--model-file",
                    compiled_model + extension,
                    "--output-file",
                    compiled_model + ".desc.xml",
                ],
                cwd=output_path,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )

    with open(output_path / "dynawo.version", "w") as version_file:
        version_file.write(get_dynawo_version(launcher_dwo))

    if compiled_model is not None and (output_path / (compiled_model + extension)).is_file():
        dgcv_logging.get_logger("Dynawo").info(f"Compilation of {compiled_model} succeeded")
    else:
        dgcv_logging.get_logger("Dynawo").error(f"Compilation of {compiled_model} failed")


def _has_error_timeline(log_path: Path) -> bool:
    with open(log_path, "r") as log:
        for line in log:
            if "ERROR" not in line:
                continue

            dgcv_logging.get_logger("Dynawo").debug(f"Error found in: {line}")
            return True

    return False


def _run_dynawo(
    launcher_dwo: Path,
    jobs_filename: str,
    inputs_path: Path,
) -> tuple[bool, str]:
    tic = time.time()
    simulation_limit = config.get_float("Dynawo", "simulation_limit", 300.0)

    proc = subprocess.Popen(
        [
            launcher_dwo,
            "jobs",
            str(jobs_filename) + ".jobs",
        ],
        cwd=inputs_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    toc = time.time()
    while (toc - tic) < simulation_limit and proc.poll() is None:
        toc = time.time()

    if proc.poll() is None:
        dgcv_logging.get_logger("Dynawo").warning("Execution terminated due to timeout")
        stderr = "Execution terminated due to timeout"
        ret_value = False
        if os.name == "nt":
            # It has to be killed in this way because proc.terminate/proc.kill doesn't
            # work on Windows
            subprocess.run(
                "taskkill /F /T /PID " + str(proc.pid),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        else:
            proc.terminate()
    else:
        stderr = proc.stderr.read().decode("utf-8")
        if "succeeded" in stderr:
            ret_value = True
        else:
            ret_value = False

    return ret_value, stderr


def _create_complex_zero_array(shape: int) -> np.ndarray:
    return np.zeros(shape, dtype=np.complex128)


def _prepare_complex_column(
    column_name: str,
    column_size: int,
    df_curves: pd.DataFrame,
    translated_column: str,
    variable_translations: dict,
) -> list:
    # Apply the tool sign convention to Dynawo curves
    real_sign = f"{translated_column}Re"
    if real_sign in variable_translations:
        sign_real = variable_translations[real_sign]
    else:
        sign_real = 1
    imaginary_sign = f"{translated_column}Im"
    if real_sign in variable_translations:
        sign_imag = variable_translations[imaginary_sign]
    else:
        sign_imag = 1

    complex_column = _create_complex_zero_array(column_size)
    complex_column.real = np.multiply(df_curves[f"{column_name}re"], sign_real).tolist()
    complex_column.imag = np.multiply(df_curves[f"{column_name}im"], sign_imag).tolist()
    return complex_column.tolist()


def _get_injected_current_curve(column_size: int, curves_translation: dict):
    cols = curves_translation.keys()
    idPu_re = re.compile(".*_InjectedActiveCurrent$")
    iqPu_re = re.compile(".*_InjectedReactiveCurrent$")
    idPu_list = list(filter(idPu_re.match, cols))
    iqPu_list = list(filter(iqPu_re.match, cols))
    if len(iqPu_list) != 0 and len(idPu_list) != 0:
        for i in range(len(iqPu_list)):
            for j in range(len(idPu_list)):
                if iqPu_list[i].replace("_InjectedReactiveCurrent", "") == idPu_list[j].replace(
                    "_InjectedActiveCurrent", ""
                ):
                    # Save the "InjectedCurrent" curve as complex curve
                    complex_column = _create_complex_zero_array(column_size)
                    complex_column.real = curves_translation[f"{idPu_list[j]}"]
                    complex_column.imag = curves_translation[f"{iqPu_list[i]}"]

                    # Add the "InjectedCurrent" curve to the curves dictionary
                    key = iqPu_list[i].replace("_InjectedReactiveCurrent", "_InjectedCurrent")
                    curves_translation[key] = complex_column.tolist()


def _get_network_frequency_curve(column_size: int, curves_translation: dict):
    """The tool expects the frequency curve from the model, however this curve cannot be
    obtained from a generic dynamic model, so we must create a new curve to represent the
    "NetworkFrequencyPu" curve by copying it from the dynamic model that generated it"""
    cols = curves_translation.keys()
    network_frequency = re.compile(".*_NetworkFrequencyPu$")
    network_frequency_list = list(filter(network_frequency.match, cols))
    if len(network_frequency_list) != 0:
        curves_translation["NetworkFrequencyPu"] = curves_translation[network_frequency_list[0]]


def _get_pdr_voltage(df_curves: pd.DataFrame) -> list:
    voltage_columns_regex = re.compile(".*_TE_.*_Voltage$")
    voltage_columns_list = list(filter(voltage_columns_regex.match, df_curves.columns))
    if len(voltage_columns_list) == 0:
        return []

    for voltage_column in voltage_columns_list:
        pdr_voltage = df_curves[voltage_column]
        return pdr_voltage.tolist()


def _get_pdr_current(df_curves: pd.DataFrame, column_size: int) -> list:
    current_columns_regex = re.compile(".*_TE_.*_Current$")
    current_columns_list = list(filter(current_columns_regex.match, df_curves.columns))
    if len(current_columns_list) == 0:
        return []

    # The tool's sign convention is applied in the calculation of power flow.
    pdr_current = _create_complex_zero_array(column_size)
    for current_column in current_columns_list:
        pdr_current = np.add(
            pdr_current,
            list(df_curves[current_column]),
        )

    return pdr_current.tolist()


def _get_pdr_active_power(pdr_voltage: list, pdr_current: list) -> list:
    # Apply the tool's sign convention
    return (np.real(pdr_voltage * np.conjugate(pdr_current)) * -1).tolist()


def _get_pdr_reactive_power(pdr_voltage: list, pdr_current: list) -> list:
    # Apply the tool's sign convention
    return (np.imag(pdr_voltage * np.conjugate(pdr_current)) * -1).tolist()


def _get_modulus(complex_list: list) -> list:
    return np.abs(complex_list).tolist()


def _translate_curves(
    variable_translations: dict, df_curves_imported: pd.DataFrame
) -> pd.DataFrame:
    column_size = len(df_curves_imported["time"])
    cols = list(df_curves_imported.columns)
    for i in cols:
        if i[:7] == "Unnamed":
            del df_curves_imported[i]

    # Some variables of the tool are modeled in a single parameter of the dynamic model,
    # to avoid conflicts the Dynawo output does not contain duplicate curves, so the tool
    # must manage duplicate curves to always have the expected number of curves.
    curves_translation = dict()
    curves_translation["time"] = list(df_curves_imported["time"])
    for column in variable_translations:
        if column in df_curves_imported.columns:
            if column.endswith("_im"):
                continue
            else:
                if column.endswith("_re"):
                    for translated_column in variable_translations[column]:
                        curves_translation[translated_column[:-2]] = _prepare_complex_column(
                            column[:-2],
                            column_size,
                            df_curves_imported,
                            translated_column[:-2],
                            variable_translations,
                        )
                else:
                    for translated_column in variable_translations[column]:
                        # Apply the tool sign convention to Dynawo curves
                        sign = variable_translations[translated_column]
                        curves_translation[translated_column] = np.multiply(
                            df_curves_imported[column], sign
                        ).tolist()

    _get_injected_current_curve(column_size, curves_translation)
    _get_network_frequency_curve(column_size, curves_translation)

    return pd.DataFrame(curves_translation)


def _create_curves(variable_translations: dict, input_file: Path) -> pd.DataFrame:
    """From the curve file generated by the Dynawo dynamic simulator, a new file is created
    where the values of the different curves are expressed in the units specified in the file
    and/or different curves are added to obtain the required curves.

    Parameters
    ----------
    variable_translations: dict
        Dictionary with correspondences between tool variables and Dynawo variables
    input_file: Path
        Curve file created by Dynawo

    Returns
    -------
    DataFrame
        A DataFrame with the transformed curves
    """
    # Get curves file
    df_curves_imported = pd.read_csv(input_file, sep=";")
    df_curves = _translate_curves(variable_translations, df_curves_imported)
    column_size = len(df_curves_imported["time"])

    # Calculate PDR Voltage, Power and Current
    del df_curves["BusPDR_BUS_Voltage"]
    pdr_voltage = _get_pdr_voltage(df_curves)
    pdr_voltage_modulus = _get_modulus(pdr_voltage)
    pdr_current = _get_pdr_current(df_curves, column_size)
    pdr_active_power = _get_pdr_active_power(pdr_voltage, pdr_current)
    pdr_reactive_power = _get_pdr_reactive_power(pdr_voltage, pdr_current)

    # Create the new curves file
    curves_dict = dict()
    curves_dict["BusPDR_BUS_Voltage"] = pdr_voltage_modulus
    curves_dict["BusPDR_BUS_ActivePower"] = pdr_active_power
    curves_dict["BusPDR_BUS_ActiveCurrent"] = np.divide(
        pdr_active_power, pdr_voltage_modulus
    ).tolist()

    curves_dict["BusPDR_BUS_ReactivePower"] = pdr_reactive_power
    curves_dict["BusPDR_BUS_ReactiveCurrent"] = np.divide(
        pdr_reactive_power, pdr_voltage_modulus
    ).tolist()

    for i in df_curves.columns:
        if "_TE_" in i:
            continue
        if pd.api.types.is_complex_dtype(df_curves[i]):
            curves_dict[i] = _get_modulus(list(df_curves[i]))
        else:
            curves_dict[i] = list(df_curves[i])

    return pd.DataFrame(curves_dict)


def _trim_curves(
    time_values: list,
    voltage_values: list,
    fault_start: float,
    fault_duration: float,
) -> tuple[list, list, list, list]:
    pre_idx = 0
    start_idx = 0
    end_idx = -1
    for i in range(len(time_values)):
        if time_values[i] - fault_start < -0.0001:
            pre_idx = i
        elif fault_start - time_values[i] > 0.0001:
            start_idx = i
        elif time_values[i] - (fault_start + fault_duration) < -0.0001:
            end_idx = i

    pre_time_values = time_values[:pre_idx]
    pre_voltage_values = voltage_values[:pre_idx]
    post_time_values = time_values[start_idx:end_idx]
    post_voltage_values = voltage_values[start_idx:end_idx]

    return pre_time_values, post_time_values, pre_voltage_values, post_voltage_values


def get_dynawo_version(
    launcher_dwo: Path,
) -> str:
    """Get the version of the Dynawo launcher in string format.

    Parameters
    ----------
    launcher_dwo: Path
        Path to the Dynawo launcher

    Returns
    -------
    str
        The Dynawo launcher version
    """

    return subprocess.run(
        [launcher_dwo, "version"],
        capture_output=True,
        text=True,
    ).stdout.strip("\n")


def precompile_models(
    launcher_dwo: Path,
    models_path: Path,
    user_dir: Path,
    model_name: str,
    output_path: Path,
) -> None:
    """Compiles the tool models.

    Parameters
    ----------
    launcher_dwo: Path
        Path to the Dynawo launcher
    models_path: Path
        Directory where the tool models are stored
    user_dir: Path
        Directory where the user models are stored
    model_name: str
        Name of the model, set to None to compile all models
    output_path: Path
        Directory where the compiled tool models will be stored
    """

    if model_name is not None:
        if os.name == "nt":
            extension = ".dll"
        else:
            extension = ".so"
        if (models_path / model_name).is_file():
            compiled_model = _compile_model_name(models_path, model_name)
            if (
                compiled_model is not None
                and (output_path / (compiled_model + extension)).is_file()
            ):
                (output_path / (compiled_model + extension)).unlink()
            _precompile_model(launcher_dwo, models_path, model_name, output_path)
        if (user_dir / model_name).is_file():
            compiled_model = _compile_model_name(user_dir, model_name)
            if (
                compiled_model is not None
                and (output_path / (compiled_model + extension)).is_file()
            ):
                (output_path / (compiled_model + extension)).unlink()
            _precompile_model(launcher_dwo, user_dir, model_name, output_path)

    else:
        for model in models_path.glob("*.[xX][mM][lL]"):
            _precompile_model(launcher_dwo, models_path, model.name, output_path)

        for model in user_dir.glob("*.[xX][mM][lL]"):
            _precompile_model(launcher_dwo, user_dir, model.name, output_path)


def run_base_dynawo(
    launcher_dwo: Path,
    jobs_filename: str,
    variable_translations: dict,
    inputs_path: Path,
    output_path: Path,
    save_file: bool = True,
) -> tuple[bool, float, str, bool]:
    """Run a Dynamic Simulation with Dynawo.

    Parameters
    ----------
    launcher_dwo: Path
        Path to the Dynawo launcher
    jobs_filename: str
        Name of the JOBS file
    variable_translations: dict
        Dictionary with correspondences between tool variables and Dynawo variables
    inputs_path: Path
        Directory with Dynawo inputs
    output_path: Path
        Dynawo simulation output directory
    save_file: bool
        If True save the calculated curves file

    Returns
    -------
    bool
        True if the simulation ends successfully, False otherwise
    str
        Log output
    bool
        Error in timeline
    DataFrame
        A DataFrame with the transformed curves

    """
    success, stderr = _run_dynawo(launcher_dwo, jobs_filename, inputs_path)
    dynawo_output_dir = inputs_path / output_path

    log = None
    has_error = False
    if _has_error_timeline(dynawo_output_dir / "logs/dynawo.log"):
        has_error = True
        success = False
    if not success:
        log = stderr

    curves_calculated = None
    if (dynawo_output_dir / "curves/curves.csv").exists() and success and save_file:
        # Create the expected curves
        curves_calculated = _create_curves(
            variable_translations,
            dynawo_output_dir / "curves/curves.csv",
        )

    return success, log, has_error, curves_calculated


def check_voltage_dip(
    is_simulation_success: bool,
    curves: pd.DataFrame,
    fault_start: float,
    fault_duration: float,
    dip: float,
) -> int:
    """Check if desired voltage drop has ocurred.

    Parameters
    ----------
    is_simulation_success: bool
        Simulation result, True if success, Folse otherwise
    curves: DataFrame
        Dataframe with the simulated curves
    fault_start: float
        Fault start time in seconds
    fault_duration: float
        Fault duration in seconds
    dip: float
        Required voltage drop

    Returns
    -------
    int
        -1 if the voltage drop is less than required
         1 if the voltage drop is greater than required
         0 if the voltage drop is equal to that required
    """
    bus_pdr_voltage = "BusPDR" + "_BUS_" + "Voltage"

    if dip == 0.0:
        return 0

    if not is_simulation_success:
        return -1

    time_values = list(curves["time"])
    voltage_values = list(curves[bus_pdr_voltage])

    if fault_duration > time_values[-1]:
        fault_duration = time_values[-1] - fault_start

    # trim curves to the fault zone
    pre_time_values, post_time_values, pre_voltage_values, post_voltage_values = _trim_curves(
        time_values, voltage_values, fault_start, fault_duration
    )

    # Get the stable value before the failure, if it has been initialized correctly it will be
    # a flat curve, and the method returns a ValueError, in this case the first point of the
    # curve is used as the stable value
    try:
        _, pre_pos = is_stable(pre_time_values, pre_voltage_values, fault_duration / 10)
    except ValueError:
        pre_pos = 0
    # gET the stable value after the failure taking into account its duration
    _, post_pos = is_stable(post_time_values, post_voltage_values, fault_duration / 10)

    if pre_voltage_values[pre_pos] - post_voltage_values[post_pos] > dip:
        return 1
    elif pre_voltage_values[pre_pos] - post_voltage_values[post_pos] < dip:
        return -1
    else:
        return 0
