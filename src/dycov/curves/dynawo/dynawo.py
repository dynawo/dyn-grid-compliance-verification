#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import math
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from lxml import etree

from dycov.files import manage_files
from dycov.logging.logging import dycov_logging
from dycov.validation.common import is_stable

VOLTAGE_DIP_THRESHOLD = 0.002


class DynawoSimulator:
    """
    A class to manage Dynawo simulations, including model compilation, execution,
    and result processing.
    """

    def __init__(self):
        """
        Initializes the DynawoSimulator.
        """
        self.logger = dycov_logging.get_logger("Dynawo")

    def _compile_model_name(self, models_path: Path, model_name: str) -> Optional[str]:
        """
        Extracts the compiled model name (Modelica model ID) from a Dynawo model XML file.

        Parameters
        ----------
        models_path : Path
            The directory where the model XML file is located.
        model_name : str
            The name of the model XML file.

        Returns
        -------
        Optional[str]
            The Modelica model ID if found, otherwise None.
        """
        model_tree = etree.parse(models_path / model_name, etree.XMLParser(remove_blank_text=True))
        model_root = model_tree.getroot()
        dyn_namespace = etree.QName(model_root).namespace
        modelica_model = model_root.find(f"{{{dyn_namespace}}}modelicaModel")
        return modelica_model.get("id") if modelica_model is not None else None

    def _precompile_model(
        self,
        launcher_dwo: Path,
        models_path: Path,
        model_name: str,
        output_path: Path,
    ) -> None:
        """
        Precompiles a Dynawo model.

        Parameters
        ----------
        launcher_dwo : Path
            Path to the Dynawo launcher executable.
        models_path : Path
            Directory where the model XML file is located.
        model_name : str
            Name of the model XML file to compile.
        output_path : Path
            Directory where the compiled model and related files will be stored.
        """
        compiled_model = self._compile_model_name(models_path, model_name)
        extension = ".dll" if os.name == "nt" else ".so"

        if compiled_model and (output_path / (compiled_model + extension)).is_file():
            self.logger.debug(f"{compiled_model} was already compiled. Skipping precompilation.")
            return

        self.logger.info(f"Precompiling {model_name}...")
        with open(output_path / "compile.log", "a") as log_file:
            if os.name == "nt":
                cmd = [
                    Path(__file__).parent.resolve() / "Vsx64.cmd",
                    models_path,
                    launcher_dwo,
                    model_name,
                    output_path,
                    compiled_model + extension,
                    compiled_model + ".desc.xml",
                ]
                cwd = Path(__file__).parent.resolve()
            else:
                cmd = [
                    launcher_dwo,
                    "jobs",
                    "--generate-preassembled",
                    "--model-list",
                    model_name,
                    "--non-recursive-modelica-models-dir",
                    ".",
                    "--output-dir",
                    output_path,
                ]
                cwd = models_path

            self.logger.info(f"Running command: {' '.join(map(str, cmd))}")
            subprocess.run(cmd, cwd=cwd, stdout=log_file, stderr=subprocess.STDOUT, check=False)

            if os.name != "nt":
                # Additional step for Linux to dump model description
                dump_cmd = [
                    launcher_dwo,
                    "jobs",
                    "--dump-model",
                    "--model-file",
                    compiled_model + extension,
                    "--output-file",
                    compiled_model + ".desc.xml",
                ]
                self.logger.info(f"Running command: {' '.join(map(str, dump_cmd))}")
                subprocess.run(
                    dump_cmd,
                    cwd=output_path,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    check=False,
                )

        with open(output_path / "dynawo.version", "w") as version_file:
            version_file.write(self.get_dynawo_version(launcher_dwo))

        if compiled_model and (output_path / (compiled_model + extension)).is_file():
            self.logger.info(f"Compilation of {compiled_model} succeeded.")
        else:
            self.logger.error(f"Compilation of {compiled_model} failed.")

    def precompile_models(
        self,
        launcher_dwo: Path,
        models_path: Path,
        user_dir: Path,
        model_name: Optional[str],
        output_path: Path,
    ) -> None:
        """
        Compiles the Dynawo models.

        If `model_name` is provided, only that specific model from either `models_path`
        or `user_dir` will be compiled. If `model_name` is None, all XML models
        in both directories will be compiled.

        Parameters
        ----------
        launcher_dwo : Path
            Path to the Dynawo launcher executable.
        models_path : Path
            Directory where the tool's default models are stored.
        user_dir : Path
            Directory where user-defined models are stored.
        model_name : Optional[str]
            Name of the model to compile. If None, all models in `models_path`
            and `user_dir` will be compiled.
        output_path : Path
            Directory where the compiled models will be stored.
        """
        output_path.mkdir(parents=True, exist_ok=True)  # Ensure output directory exists

        models_to_compile = []
        if model_name:
            if (models_path / model_name).is_file():
                models_to_compile.append((models_path, model_name))
            if (user_dir / model_name).is_file():
                models_to_compile.append((user_dir, model_name))
        else:
            for model in models_path.glob("*.[xX][mM][lL]"):
                models_to_compile.append((models_path, model.name))
            for model in user_dir.glob("*.[xX][mM][lL]"):
                models_to_compile.append((user_dir, model.name))

        extension = ".dll" if os.name == "nt" else ".so"
        for current_models_path, current_model_name in models_to_compile:
            compiled_model = self._compile_model_name(current_models_path, current_model_name)
            if compiled_model and (output_path / (compiled_model + extension)).is_file():
                # Remove existing compiled model to force recompilation if explicitly requested
                # or if a new compilation is needed.
                # The original code only removes if model_name is not None
                # so keeping that behavior.
                if model_name:
                    self.logger.debug(
                        "Removing existing compiled model: "
                        f"{output_path / (compiled_model + extension)}"
                    )
                    (output_path / (compiled_model + extension)).unlink()
            self._precompile_model(
                launcher_dwo, current_models_path, current_model_name, output_path
            )

    def _has_error_timeline(
        self, pcs_name: str, bm_name: str, oc_name: str, log_path: Path
    ) -> bool:
        """
        Checks if the Dynawo simulation log file contains any "ERROR" messages.

        Parameters
        ----------
        pcs_name : str
            Power System Case name for logging.
        bm_name : str
            Benchmark name for logging.
        oc_name : str
            Operational Condition name for logging.
        log_path : Path
            Path to the Dynawo simulation log file.

        Returns
        -------
        bool
            True if an "ERROR" is found in the log, False otherwise.
        """
        if not log_path.is_file():
            self.logger.warning(f"Log file not found at {log_path}")
            return False

        with open(log_path, "r") as log:
            for line in log:
                if "ERROR" in line:
                    self.logger.debug(
                        f"{pcs_name}.{bm_name}.{oc_name}: Error found in: {line.strip()}"
                    )
                    return True
        return False

    def _run_dynawo_process(
        self,
        launcher_dwo: Path,
        jobs_filename: str,
        inputs_path: Path,
        simulation_limit: Optional[float],
    ) -> tuple[bool, str, float]:
        """
        Executes the Dynawo simulation process.

        Parameters
        ----------
        launcher_dwo : Path
            Path to the Dynawo launcher executable.
        jobs_filename : str
            The name of the .jobs file to execute.
        inputs_path : Path
            The working directory for the Dynawo simulation.
        simulation_limit : Optional[float]
            Maximum time (in seconds) allowed for the simulation to run.
            If None, no timeout is applied.

        Returns
        -------
        tuple[bool, str, float]
            A tuple containing:
            - bool: True if the simulation process exited successfully, False otherwise.
            - str: Standard error output from the Dynawo process, or a timeout message.
            - float: The actual time taken for the simulation process.
        """
        self.logger.debug(f"Simulation limit: {simulation_limit} seconds.")

        proc = subprocess.Popen(
            [launcher_dwo, "jobs", f"{jobs_filename}.jobs"],
            cwd=inputs_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid if os.name != "nt" else None,
        )

        start_time = time.time()
        current_time = start_time
        ret_value = False
        stderr_output = ""

        while (
            simulation_limit is None or (current_time - start_time) < simulation_limit
        ) and proc.poll() is None:
            current_time = time.time()
            time.sleep(0.1)  # Small delay to avoid busy-waiting

        if proc.poll() is None:
            stderr_output = "Execution terminated due to timeout."
            if os.name == "nt":
                # On Windows, taskkill is used to terminate the process tree
                subprocess.run(
                    f"taskkill /F /T /PID {proc.pid}",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
            else:
                # On Unix-like systems, send SIGTERM to the process group
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait()  # Wait for the process to actually terminate
        else:
            stderr_output = proc.stderr.read().decode("utf-8")
            if "succeeded" in stderr_output:
                ret_value = True

        return ret_value, stderr_output, time.time() - start_time

    def run_base_dynawo(
        self,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        launcher_dwo: Path,
        jobs_filename: str,
        variable_translations: dict,
        inputs_path: Path,
        output_path: Path,
        generators: list,
        s_nom: float,
        s_nref: float,
        save_file: bool = True,
        simulation_limit: Optional[float] = None,
    ) -> tuple[bool, Optional[str], bool, pd.DataFrame, float]:
        """
        Runs a dynamic simulation with Dynawo and processes the results.

        Parameters
        ----------
        pcs_name : str
            Power System Case name for logging.
        bm_name : str
            Benchmark name for logging.
        oc_name : str
            Operational Condition name for logging.
        launcher_dwo : Path
            Path to the Dynawo launcher executable.
        jobs_filename : str
            Name of the JOBS file (without .jobs extension).
        variable_translations : dict
            Dictionary mapping tool variables to Dynawo variables for curve translation.
        inputs_path : Path
            Directory containing Dynawo input files.
        output_path : Path
            Directory where Dynawo simulation outputs will be written.
        generators : list
            List of generator objects, used for specific curve calculations.
        s_nom : float
            Nominal apparent power of the system.
        s_nref : float
            System-wide S base (SnRef).
        save_file : bool, optional
            If True, the calculated curves DataFrame will be created and returned.
            Defaults to True.
        simulation_limit : Optional[float], optional
            Maximum time (in seconds) allowed for the simulation to run.
            If None, no timeout is applied. Defaults to None.

        Returns
        -------
        tuple[bool, Optional[str], bool, pd.DataFrame, float]
            A tuple containing:
            - bool: True if the simulation completed successfully (no errors in log,
            no timeout, "succeeded" in stderr).
            - Optional[str]: Log output from stderr if an error occurred or timeout,
            otherwise None.
            - bool: True if an error was found in the Dynawo timeline log, False otherwise.
            - pd.DataFrame: A DataFrame with the transformed and calculated curves. Empty
            if save_file is False or simulation failed.
            - float: The actual time taken for the simulation.
        """
        # Remove previous output directory (Dynawo does not remove old output directories)
        dynawo_output_full_path = inputs_path / output_path
        manage_files.remove_dir(dynawo_output_full_path)

        success, stderr, sim_time = self._run_dynawo_process(
            launcher_dwo, jobs_filename, inputs_path, simulation_limit
        )

        log_file_path = dynawo_output_full_path / "logs/dynawo.log"

        has_error_in_timeline = self._has_error_timeline(pcs_name, bm_name, oc_name, log_file_path)
        if has_error_in_timeline:
            success = False  # Mark as failed if timeline error detected

        log_output = (
            stderr if not success else None
        )  # Only return stderr if simulation didn't succeed

        curves_calculated = pd.DataFrame()
        curves_csv_path = dynawo_output_full_path / "curves/curves.csv"

        if curves_csv_path.exists() and success and save_file:
            curves_calculated = self._create_curves(
                variable_translations, curves_csv_path, generators, s_nom, s_nref
            )

        return success, log_output, has_error_in_timeline, curves_calculated, sim_time

    def _create_complex_zero_array(self, shape: int) -> np.ndarray:
        """
        Creates a NumPy array of zeros with complex128 dtype.

        Parameters
        ----------
        shape : int
            The desired shape (size) of the array.

        Returns
        -------
        np.ndarray
            A NumPy array of zeros with complex128 dtype.
        """
        return np.zeros(shape, dtype=np.complex128)

    def _prepare_complex_column(
        self,
        column_name: str,
        column_size: int,
        df_curves: pd.DataFrame,
        translated_column: str,
        variable_translations: dict,
    ) -> list:
        """
        Prepares a complex column from real and imaginary parts in the DataFrame,
        applying tool-specific sign conventions.

        Parameters
        ----------
        column_name : str
            The base name of the column (e.g., "Voltage").
        column_size : int
            The number of rows in the DataFrame.
        df_curves : pd.DataFrame
            The DataFrame containing the real and imaginary parts.
        translated_column : str
            The name of the translated complex column (e.g., "VoltagePu").
        variable_translations : dict
            Dictionary containing sign conventions for real and imaginary parts.

        Returns
        -------
        list
            A list of complex numbers representing the prepared column.
        """
        # Apply the tool sign convention to Dynawo curves
        real_sign = f"{translated_column}Re"
        sign_real = variable_translations.get(real_sign, 1)

        imaginary_sign = f"{translated_column}Im"
        sign_imag = variable_translations.get(imaginary_sign, 1)

        complex_column_array = self._create_complex_zero_array(column_size)
        complex_column_array.real = np.multiply(df_curves[f"{column_name}re"], sign_real)
        complex_column_array.imag = np.multiply(df_curves[f"{column_name}im"], sign_imag)
        return complex_column_array.tolist()

    def _get_injected_current_curve(self, column_size: int, curves_translation: dict) -> None:
        """
        Calculates and adds the "InjectedCurrent" complex curve to the translated curves
        dictionary.

        This function searches for "_InjectedActiveCurrent" and "_InjectedReactiveCurrent"
        curves and combines them into a single complex "InjectedCurrent" curve.

        Parameters
        ----------
        column_size : int
            The number of data points in the curves.
        curves_translation : dict
            The dictionary where translated curves are stored.
        """
        cols = curves_translation.keys()
        idpu_re = re.compile(r".*_InjectedActiveCurrent$")
        iqpu_re = re.compile(r".*_InjectedReactiveCurrent$")
        idpu_list = list(filter(idpu_re.match, cols))
        iqpu_list = list(filter(iqpu_re.match, cols))

        for iqpu_col in iqpu_list:
            base_name = iqpu_col.replace("_InjectedReactiveCurrent", "")
            for idpu_col in idpu_list:
                if idpu_col.replace("_InjectedActiveCurrent", "") == base_name:
                    complex_column = self._create_complex_zero_array(column_size)
                    complex_column.real = curves_translation[idpu_col]
                    complex_column.imag = curves_translation[iqpu_col]

                    key = f"{base_name}_InjectedCurrent"
                    curves_translation[key] = complex_column.tolist()
                    break

    def _get_network_frequency_curve(self, curves_translation: dict) -> None:
        """
        Adds the "NetworkFrequencyPu" curve to the translated curves dictionary.

        This function looks for a curve ending with "_NetworkFrequencyPu" and, if found,
        copies its values to a new "NetworkFrequencyPu" key. The tool expects
        "NetworkFrequencyPu" curve.

        Parameters
        ----------
        curves_translation : dict
            The dictionary where translated curves are stored.
        """
        cols = curves_translation.keys()
        network_frequency_re = re.compile(r".*_NetworkFrequencyPu$")
        network_frequency_list = list(filter(network_frequency_re.match, cols))
        if network_frequency_list:
            curves_translation["NetworkFrequencyPu"] = curves_translation[
                network_frequency_list[0]
            ]

    def _get_pdr_voltage(self, df_curves: pd.DataFrame) -> list:
        """
        Extracts the PDR (Point of Design Reference) voltage curve from the DataFrame.

        Parameters
        ----------
        df_curves : pd.DataFrame
            DataFrame containing simulation curves.

        Returns
        -------
        list
            A list of voltage values for the PDR bus, or an empty list if not found.
        """
        voltage_columns_regex = re.compile(r".*_TE_.*_Voltage$")
        voltage_columns_list = list(filter(voltage_columns_regex.match, df_curves.columns))
        if voltage_columns_list:
            # Assuming there's only one relevant PDR voltage column or the first one is sufficient
            return df_curves[voltage_columns_list[0]].tolist()
        return []

    def _get_pdr_current(self, df_curves: pd.DataFrame, column_size: int) -> list:
        """
        Calculates the PDR (Point of Design Reference) total current from individual
        current curves.

        Parameters
        ----------
        df_curves : pd.DataFrame
            DataFrame containing simulation curves.
        column_size : int
            The number of data points in the curves.

        Returns
        -------
        list
            A list of complex current values for the PDR bus, or an empty list if no
            current columns are found.
        """
        current_columns_regex = re.compile(r".*_TE_.*_Current$")
        current_columns_list = list(filter(current_columns_regex.match, df_curves.columns))
        if not current_columns_list:
            return []

        pdr_current_base_snref = self._create_complex_zero_array(column_size)
        for current_column in current_columns_list:
            pdr_current_base_snref = np.add(
                pdr_current_base_snref,
                list(df_curves[current_column]),
            )
        return pdr_current_base_snref.tolist()

    def _get_pdr_active_power(
        self, pdr_voltage: list, pdr_current: list, snom: float, snref: float
    ) -> list:
        """
        Calculates the PDR (Point of Design Reference) active power.

        Parameters
        ----------
        pdr_voltage : list
            List of complex voltage values.
        pdr_current : list
            List of complex current values.
        snom : float
            Nominal apparent power.
        snref : float
            System-wide S base (SnRef).

        Returns
        -------
        list
            A list of active power values.
        """
        # Apply the tool's sign convention
        pdr_active_power_base_snref = np.real(pdr_voltage * np.conjugate(pdr_current)) * -1
        # Calculate the active power in the base SNom
        pdr_active_power = pdr_active_power_base_snref * (snref / snom)
        return pdr_active_power.tolist()

    def _get_pdr_reactive_power(
        self, pdr_voltage: list, pdr_current: list, snom: float, snref: float
    ) -> list:
        """
        Calculates the PDR (Point of Design Reference) reactive power.

        Parameters
        ----------
        pdr_voltage : list
            List of complex voltage values.
        pdr_current : list
            List of complex current values.
        snom : float
            Nominal apparent power.
        snref : float
            System-wide S base (SnRef).

        Returns
        -------
        list
            A list of reactive power values.
        """
        # Apply the tool's sign convention
        pdr_reactive_power_base_snref = np.imag(pdr_voltage * np.conjugate(pdr_current)) * -1
        # Calculate the reactive power in the base SNom
        pdr_reactive_power = pdr_reactive_power_base_snref * (snref / snom)
        return pdr_reactive_power.tolist()

    def _get_modulus(self, complex_list: list) -> list:
        """
        Calculates the modulus (magnitude) of a list of complex numbers.

        Parameters
        ----------
        complex_list : list
            A list of complex numbers.

        Returns
        -------
        list
            A list of the magnitudes of the complex numbers.
        """
        return np.abs(complex_list).tolist()

    def _apply_sign_convention(
        self,
        variable_translations: dict,
        df_curves_imported: pd.DataFrame,
        curves_translation: dict,
        column: str,
    ) -> None:
        """
        Applies sign convention to a given column and adds it to the translated curves.

        Parameters
        ----------
        variable_translations : dict
            Dictionary with correspondences and sign conventions.
        df_curves_imported : pd.DataFrame
            Original DataFrame with imported curves.
        curves_translation : dict
            Dictionary to store translated curves.
        column : str
            The name of the column to process.
        """
        for translated_column in variable_translations[column]:
            # Apply the tool sign convention to Dynawo curves
            sign = variable_translations[translated_column]
            curves_translation[translated_column] = np.multiply(
                df_curves_imported[column], sign
            ).tolist()

    def _translate_complex_columns(
        self,
        variable_translations: dict,
        df_curves_imported: pd.DataFrame,
        curves_translation: dict,
        column: str,
        column_size: int,
    ) -> None:
        """
        Translates complex columns (with '_re' and '_im' suffixes) into single complex columns.

        Parameters
        ----------
        variable_translations : dict
            Dictionary with correspondences and sign conventions.
        df_curves_imported : pd.DataFrame
            Original DataFrame with imported curves.
        curves_translation : dict
            Dictionary to store translated curves.
        column : str
            The name of the real part column (e.g., "Voltage_re").
        column_size : int
            The number of data points in the curves.
        """
        for translated_column in variable_translations[column]:
            curves_translation[translated_column[:-2]] = self._prepare_complex_column(
                column[:-2],
                column_size,
                df_curves_imported,
                translated_column[:-2],
                variable_translations,
            )

    def _translate_curves(
        self, variable_translations: dict, df_curves_imported: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Translates raw Dynawo curves into the format expected by the tool, handling
        sign conventions and complex number reconstruction.

        Parameters
        ----------
        variable_translations : dict
            Dictionary with correspondences between tool variables and Dynawo variables,
            including sign conventions.
        df_curves_imported : pd.DataFrame
            The DataFrame containing the raw curves imported from Dynawo.

        Returns
        -------
        pd.DataFrame
            A DataFrame with the translated curves.
        """
        column_size = len(df_curves_imported["time"])
        curves_translation: dict = {"time": df_curves_imported["time"].tolist()}

        for column in variable_translations:
            if column not in df_curves_imported.columns:
                continue

            if column.endswith("_im"):
                continue

            if column.endswith("_re"):
                self._translate_complex_columns(
                    variable_translations,
                    df_curves_imported,
                    curves_translation,
                    column,
                    column_size,
                )
            else:
                self._apply_sign_convention(
                    variable_translations, df_curves_imported, curves_translation, column
                )

        self._get_injected_current_curve(column_size, curves_translation)
        self._get_network_frequency_curve(curves_translation)

        return pd.DataFrame(curves_translation)

    def _get_magnitude_controlled_by_avr(
        self, generators: list, df_curves: pd.DataFrame, curves_dict: dict
    ) -> None:
        """
        Calculates and adds the 'MagnitudeControlledByAVRPu' curve for each generator.

        This function handles cases where the magnitude is directly available or needs
        to be calculated using 'MagnitudeControlledByAVRUPu' and 'MagnitudeControlledByAVRQPu'
        along with a voltage drop.

        Parameters
        ----------
        generators : list
            A list of generator objects, each potentially having 'UseVoltageDroop' and
            'VoltageDroop' attributes.
        df_curves : pd.DataFrame
            The DataFrame containing the original curves from Dynawo.
        curves_dict : dict
            The dictionary where calculated curves will be added.
        """
        delete_columns = []
        for generator in generators:
            variable = f"{generator.id}_GEN_MagnitudeControlledByAVRPu"
            u_variable = f"{generator.id}_GEN_MagnitudeControlledByAVRUPu"
            q_variable = f"{generator.id}_GEN_MagnitudeControlledByAVRQPu"

            if variable in df_curves.columns:
                curves_dict[variable] = df_curves[variable].tolist()
                delete_columns.append(variable)
            elif u_variable in df_curves.columns:
                if generator.UseVoltageDroop and q_variable in df_curves.columns:
                    curve_u = df_curves[u_variable].to_numpy()
                    curve_q = df_curves[q_variable].to_numpy()
                    voltage_drop = float(generator.VoltageDroop)
                    curves_dict[variable] = np.add(
                        curve_u, np.multiply(curve_q, voltage_drop)
                    ).tolist()
                    delete_columns.extend([u_variable, q_variable])
                else:
                    curves_dict[variable] = df_curves[u_variable].tolist()
                    delete_columns.append(u_variable)
                    if q_variable in df_curves.columns:
                        delete_columns.append(
                            q_variable
                        )  # Ensure q_variable is also removed if u_variable is used

        for column in delete_columns:
            if column in df_curves.columns:
                del df_curves[column]

    def _create_curves(
        self,
        variable_translations: dict,
        input_file: Path,
        generators: list,
        snom: float,
        snref: float,
    ) -> pd.DataFrame:
        """
        Transforms and augments the raw Dynawo curve data into a standardized DataFrame
        with calculated and translated curves.

        Parameters
        ----------
        variable_translations : dict
            Dictionary with correspondences between tool variables and Dynawo variables.
        input_file : Path
            Path to the curve file generated by Dynawo.
        generators : list
            List of generator objects.
        snom : float
            Nominal apparent power.
        snref : float
            System-wide S base (SnRef).

        Returns
        -------
        pd.DataFrame
            A DataFrame with the transformed curves ready for analysis.
        """
        df_curves_imported = pd.read_csv(input_file, sep=";")
        # Remove unnamed columns which can appear during CSV parsing
        df_curves_imported = df_curves_imported.loc[
            :, ~df_curves_imported.columns.str.contains("^Unnamed")
        ]

        df_curves = self._translate_curves(variable_translations, df_curves_imported)
        column_size = len(df_curves_imported["time"])

        # Calculate PDR Voltage, Power and Current
        # BusPDR_BUS_Voltage is handled separately, so delete it from the translated curves for now
        if "BusPDR_BUS_Voltage" in df_curves.columns:
            del df_curves["BusPDR_BUS_Voltage"]

        pdr_voltage_complex = self._get_pdr_voltage(df_curves)  # Use imported for TE_ Voltage
        pdr_voltage_modulus = self._get_modulus(pdr_voltage_complex)
        pdr_current_complex = self._get_pdr_current(
            df_curves, column_size
        )  # Use imported for TE_ Current

        pdr_active_power = self._get_pdr_active_power(
            np.array(pdr_voltage_complex), np.array(pdr_current_complex), snom, snref
        )
        pdr_reactive_power = self._get_pdr_reactive_power(
            np.array(pdr_voltage_complex), np.array(pdr_current_complex), snom, snref
        )

        rtol = 0.002  # 0.2% relative error
        atol = 0.1 * rtol  # When magnitudes are near 0.01, switch to abs error

        curves_dict = {
            "time": df_curves_imported["time"].tolist(),  # Ensure time is always the first column
            "BusPDR_BUS_Voltage": pdr_voltage_modulus,
            "BusPDR_BUS_ActivePower": pdr_active_power,
            "BusPDR_BUS_ReactivePower": pdr_reactive_power,
        }

        # Calculate Active Current and Reactive Current, handling division by zero
        active_power_arr = np.array(pdr_active_power)
        reactive_power_arr = np.array(pdr_reactive_power)
        voltage_modulus_arr = np.array(pdr_voltage_modulus)

        curves_dict["BusPDR_BUS_ActiveCurrent"] = np.divide(
            active_power_arr,
            voltage_modulus_arr,
            out=np.zeros_like(active_power_arr, dtype=float),  # Ensure output is float
            where=np.abs(voltage_modulus_arr)
            > atol,  # Condition for division, use absolute tolerance near zero
        ).tolist()

        curves_dict["BusPDR_BUS_ReactiveCurrent"] = np.divide(
            reactive_power_arr,
            voltage_modulus_arr,
            out=np.zeros_like(reactive_power_arr, dtype=float),  # Ensure output is float
            where=np.abs(voltage_modulus_arr)
            > atol,  # Condition for division, use absolute tolerance near zero
        ).tolist()

        self._get_magnitude_controlled_by_avr(generators, df_curves, curves_dict)

        # Add remaining translated columns from df_curves to curves_dict
        for col in df_curves.columns:
            if "_TE_" in col or col == "time":
                continue  # Skip TE_ columns as they are handled or not needed in final output

            if pd.api.types.is_complex_dtype(df_curves[col]):
                curves_dict[col] = self._get_modulus(df_curves[col].tolist())
            else:
                curves_dict[col] = df_curves[col].tolist()

        return pd.DataFrame(curves_dict)

    def _trim_curves(
        self,
        time_values: list[float],
        voltage_values: list[float],
        fault_start: float,
        fault_duration: float,
    ) -> tuple[list[float], list[float], list[float], list[float]]:
        """
        Trims the time and voltage curves to extract pre-fault and post-fault sections.

        Parameters
        ----------
        time_values : list[float]
            List of time values from the simulation.
        voltage_values : list[float]
            List of voltage values from the simulation.
        fault_start : float
            The start time of the fault.
        fault_duration : float
            The duration of the fault.

        Returns
        -------
        tuple[list[float], list[float], list[float], list[float]]
            A tuple containing:
            - pre_time_values: Time values before the fault.
            - post_time_values: Time values during and after the fault.
            - pre_voltage_values: Voltage values before the fault.
            - post_voltage_values: Voltage values during and after the fault.
        """
        pre_idx = 0
        start_idx = 0
        end_idx = -1

        for i, t in enumerate(time_values):
            if t - fault_start < -0.0001:
                pre_idx = i
            if fault_start - t > 0.0001:
                start_idx = i
            if t - (fault_start + fault_duration) < -0.0001:
                end_idx = i

        pre_time_values = time_values[: pre_idx + 1]
        pre_voltage_values = voltage_values[: pre_idx + 1]

        # Ensure post_time_values captures the fault duration correctly
        post_time_values = time_values[start_idx + 1 : end_idx + 1]
        post_voltage_values = voltage_values[start_idx + 1 : end_idx + 1]

        return pre_time_values, post_time_values, pre_voltage_values, post_voltage_values

    def get_dynawo_version(self, launcher_dwo: Path) -> str:
        """
        Retrieves the version of the Dynawo launcher.

        Parameters
        ----------
        launcher_dwo : Path
            Path to the Dynawo launcher executable.

        Returns
        -------
        str
            The Dynawo launcher version string.
        """
        result = subprocess.run(
            [launcher_dwo, "version"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip()

    def check_voltage_dip(
        self,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        curves: pd.DataFrame,
        fault_start: float,
        fault_duration: float,
        expected_dip: float,
    ) -> int:
        """
        Checks if the desired voltage dip has occurred during the simulation.

        Parameters
        ----------
        pcs_name : str
            Power System Case name for logging.
        bm_name : str
            Benchmark name for logging.
        oc_name : str
            Operational Condition name for logging.
        curves : pd.DataFrame
            DataFrame containing the simulated curves, specifically "BusPDR_BUS_Voltage".
        fault_start : float
            The start time of the fault in seconds.
        fault_duration : float
            The duration of the fault in seconds.
        expected_dip : float
            The required voltage drop (positive value).

        Returns
        -------
        int
            -1 if the actual voltage dip is less than the required dip.
             1 if the actual voltage dip is greater than the required dip.
             0 if the actual voltage dip is approximately equal to the required dip.
        """
        if expected_dip == 0.0:
            return 0

        bus_pdr_voltage_column = "BusPDR_BUS_Voltage"
        if bus_pdr_voltage_column not in curves.columns:
            self.logger.error(f"'{bus_pdr_voltage_column}' not found in curves DataFrame.")
            return -2  # Indicate an error if the column is missing

        time_values = curves["time"].tolist()
        voltage_values = curves[bus_pdr_voltage_column].tolist()

        # Ensure fault_duration does not exceed the simulation time
        if fault_start + fault_duration > time_values[-1]:
            self.logger.warning(
                "Fault duration extends beyond simulation time. Adjusting fault_duration "
                f"from {fault_duration} to {time_values[-1] - fault_start:.4f}."
            )
            fault_duration = time_values[-1] - fault_start

        # Trim curves to the fault zone
        pre_time, post_time, pre_voltage, post_voltage = self._trim_curves(
            time_values, voltage_values, fault_start, fault_duration
        )

        # Get the stable voltage value before the fault
        try:
            # The is_stable method may raise ValueError if the curve is not stable or too short
            _, pre_stable_idx = is_stable(pre_time, pre_voltage, fault_duration / 10)
        except ValueError:
            # If is_stable fails, use the last point of the pre-fault curve as the stable value
            pre_stable_idx = len(pre_voltage) - 1 if pre_voltage else 0

        # Get the stable voltage value after the fault, considering its duration
        _, post_stable_idx = is_stable(post_time, post_voltage, fault_duration / 10)

        pre_fault_voltage = pre_voltage[pre_stable_idx] if pre_voltage else 0.0
        post_fault_voltage = post_voltage[post_stable_idx] if post_voltage else 0.0

        voltage_dip = pre_fault_voltage - post_fault_voltage

        self.logger.debug(
            f"{pcs_name}.{bm_name}.{oc_name}: "
            f"Calculated Voltage dip: {voltage_dip:.4f}, Expected dip: {expected_dip:.4f}"
        )

        rtol = VOLTAGE_DIP_THRESHOLD
        atol = 0.1 * rtol  # When magnitudes are near 0.01, switch to abs error

        if math.isclose(voltage_dip, expected_dip, rel_tol=rtol, abs_tol=atol):
            return 0
        elif expected_dip < voltage_dip:
            return 1
        else:  # expected_dip > voltage_dip
            return -1
