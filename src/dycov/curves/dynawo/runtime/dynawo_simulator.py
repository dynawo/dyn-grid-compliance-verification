#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from __future__ import annotations

import math
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from dycov.configuration.cfg import config
from dycov.curves.dynawo.runtime.run_types import DynawoRunInputs
from dycov.files import manage_files
from dycov.logging.logging import dycov_logging
from dycov.validation.common import is_stable

VOLTAGE_DIP_THRESHOLD = 0.002


class DynawoSimulator:
    # -------------------------
    # Public wrappers (API estable)
    # -------------------------
    @staticmethod
    def run_base(
        run: DynawoRunInputs,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        bm_name: str,
        oc_name: str,
        max_sim_time: Optional[float] = None,
    ) -> Tuple[bool, bool, str, pd.DataFrame, float]:
        """Baseline execution with configured limits."""
        if max_sim_time is None:
            max_sim_time = config.get_float("Dynawo", "simulation_limit", 30.0)

        success, log, has_error, curves_calculated, sim_time = DynawoSimulator().run_base_dynawo(
            run.pcs_name,
            bm_name,
            oc_name,
            run.launcher_dwo,
            "TSOModel",
            run.curves_dict,
            working_oc_dir,
            jobs_output_dir,
            run.generators,
            run.s_nom,
            run.s_nref,
            simulation_limit=max_sim_time,
        )

        time_exceeds = False
        if has_error:
            log_file = output_dir / jobs_output_dir / "logs/dynawo.log"
            log = f"Simulation Fails, logs in {str(log_file)}"

        if sim_time > max_sim_time:
            success = False
            time_exceeds = True

        return success, time_exceeds, log, curves_calculated, sim_time

    @staticmethod
    def run_simple(
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        launcher_dwo: str,
        curves_dict: dict,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        generators: list,
        s_nom: float,
        s_nref: float,
        simulation_limit: float,
        save_file: bool = False,
    ) -> Tuple[bool, bool, str, pd.DataFrame, float]:
        """Thin wrapper without retry (useful for CCT flows)."""
        return DynawoSimulator().run_base_dynawo(
            pcs_name,
            bm_name,
            oc_name,
            launcher_dwo,
            "TSOModel",
            curves_dict,
            working_oc_dir,
            jobs_output_dir,
            generators,
            s_nom,
            s_nref,
            save_file=save_file,
            simulation_limit=simulation_limit,
        )

    @staticmethod
    def check_voltage_dip(
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
            dycov_logging.get_logger("DynawoSimulator").error(
                f"'{bus_pdr_voltage_column}' not found in curves DataFrame."
            )
            return -2  # Indicate an error if the column is missing

        time_values = curves["time"].tolist()
        voltage_values = curves[bus_pdr_voltage_column].tolist()

        # Ensure fault_duration does not exceed the simulation time
        # if fault_duration == 9999.0 there is no fault
        if fault_start + fault_duration > time_values[-1]:
            dycov_logging.get_logger("DynawoSimulator").warning(
                "Fault duration extends beyond simulation time. Adjusting fault_duration "
                f"from {fault_duration} to {time_values[-1] - fault_start:.4f}."
            )
            fault_duration = time_values[-1] - fault_start

        pre_time, post_time, pre_voltage, post_voltage = DynawoSimulator._trim_curves(
            time_values, voltage_values, fault_start, fault_duration
        )

        # Get the stable voltage before/after fault
        try:
            _, pre_stable_idx = is_stable(pre_time, pre_voltage, fault_duration / 10)
        except ValueError:
            pre_stable_idx = len(pre_voltage) - 1 if pre_voltage else 0

        _, post_stable_idx = is_stable(post_time, post_voltage, fault_duration / 10)

        pre_fault_voltage = pre_voltage[pre_stable_idx] if pre_voltage else 0.0
        post_fault_voltage = post_voltage[post_stable_idx] if post_voltage else 0.0
        voltage_dip = pre_fault_voltage - post_fault_voltage

        dycov_logging.get_logger("DynawoSimulator").debug(
            f"{pcs_name}.{bm_name}.{oc_name}: "
            f"Calculated Voltage dip: {voltage_dip:.4f}, Expected dip: {expected_dip:.4f}"
        )

        rtol = VOLTAGE_DIP_THRESHOLD
        atol = 0.1 * rtol
        if math.isclose(voltage_dip, expected_dip, rel_tol=rtol, abs_tol=atol):
            return 0
        elif expected_dip < voltage_dip:
            return 1
        else:
            return -1

    # -------------------------
    # Engine (migrado desde dynamic_simulator.py)
    # -------------------------
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
        Runs a dynamic simulation with Dynamic and processes the results.
        Parameters
        ----------
        pcs_name : str
            Power System Case name for logging.
        bm_name : str
            Benchmark name for logging.
        oc_name : str
            Operational Condition name for logging.
        launcher_dwo : Path
            Path to the Dynamic launcher executable.
        jobs_filename : str
            Name of the JOBS file (without .jobs extension).
        variable_translations : dict
            Dictionary mapping tool variables to Dynamic variables for curve translation.
        inputs_path : Path
            Directory containing Dynamic input files.
        output_path : Path
            Directory where Dynamic simulation outputs will be written.
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
            - bool: True if an error was found in the Dynamic timeline log, False otherwise.
            - pd.DataFrame: A DataFrame with the transformed and calculated curves. Empty
              if save_file is False or simulation failed.
            - float: The actual time taken for the simulation.
        """
        # Clean previous Dynawo output
        dynawo_output_full_path = inputs_path / output_path
        manage_files.remove_dir(dynawo_output_full_path)

        success, stderr, sim_time = self._run_dynawo_process(
            launcher_dwo, jobs_filename, inputs_path, simulation_limit
        )

        log_file_path = dynawo_output_full_path / "logs/dynawo.log"
        has_error_in_timeline = self._has_error_timeline(pcs_name, bm_name, oc_name, log_file_path)

        if has_error_in_timeline:
            success = False  # mark as failed on timeline error

        log_output = stderr if not success else None
        curves_calculated = pd.DataFrame()
        curves_csv_path = dynawo_output_full_path / "curves/curves.csv"

        if curves_csv_path.exists() and success and save_file:
            curves_calculated = self._create_curves(
                variable_translations, curves_csv_path, generators, s_nom, s_nref
            )

        return success, log_output, has_error_in_timeline, curves_calculated, sim_time

    def _run_dynawo_process(
        self,
        launcher_dwo: Path,
        jobs_filename: str,
        inputs_path: Path,
        simulation_limit: Optional[float],
    ) -> tuple[bool, str, float]:
        dycov_logging.get_logger("DynawoSimulator").debug(
            f"Simulation limit: {simulation_limit} seconds."
        )
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
            time.sleep(0.1)

        if proc.poll() is None:
            stderr_output = "Execution terminated due to timeout."
            if os.name == "nt":
                subprocess.run(
                    f"taskkill /F /T /PID {proc.pid}",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait()
        else:
            stderr_output = proc.stderr.read().decode("utf-8")
            if "succeeded" in stderr_output:
                ret_value = True

        return ret_value, stderr_output, time.time() - start_time

    def _has_error_timeline(
        self, pcs_name: str, bm_name: str, oc_name: str, log_path: Path
    ) -> bool:
        if not log_path.is_file():
            dycov_logging.get_logger("DynawoSimulator").warning(
                f"Log file not found at {log_path}"
            )
            return False
        with open(log_path, "r") as log:
            for line in log:
                if "ERROR" in line:
                    dycov_logging.get_logger("DynawoSimulator").debug(
                        f"{pcs_name}.{bm_name}.{oc_name}: Error found in: {line.strip()}"
                    )
                    return True
        return False

    # ----- Curves translation & augmentation -----
    def _create_curves(
        self,
        variable_translations: dict,
        input_file: Path,
        generators: list,
        snom: float,
        snref: float,
    ) -> pd.DataFrame:
        df_curves_imported = pd.read_csv(input_file, sep=";")
        df_curves_imported = df_curves_imported.loc[
            :, ~df_curves_imported.columns.str.contains("^Unnamed")
        ]

        df_curves = self._translate_curves(variable_translations, df_curves_imported)
        column_size = len(df_curves_imported["time"])

        # Remove PDR voltage if present; we'll add our computed one
        if "BusPDR_BUS_Voltage" in df_curves.columns:
            del df_curves["BusPDR_BUS_Voltage"]

        pdr_voltage_complex = self._get_pdr_voltage(df_curves)
        pdr_voltage_modulus = self._get_modulus(pdr_voltage_complex)
        pdr_current_complex = self._get_pdr_current(df_curves, column_size)

        pdr_active_power = self._get_pdr_active_power(
            np.array(pdr_voltage_complex), np.array(pdr_current_complex), snom, snref
        )
        pdr_reactive_power = self._get_pdr_reactive_power(
            np.array(pdr_voltage_complex), np.array(pdr_current_complex), snom, snref
        )

        rtol = 0.002
        atol = 0.1 * rtol

        curves_dict = {
            "time": df_curves_imported["time"].tolist(),
            "BusPDR_BUS_Voltage": pdr_voltage_modulus,
            "BusPDR_BUS_ActivePower": pdr_active_power,
            "BusPDR_BUS_ReactivePower": pdr_reactive_power,
        }

        active_power_arr = np.array(pdr_active_power)
        reactive_power_arr = np.array(pdr_reactive_power)
        voltage_modulus_arr = np.array(pdr_voltage_modulus)

        curves_dict["BusPDR_BUS_ActiveCurrent"] = np.divide(
            active_power_arr,
            voltage_modulus_arr,
            out=np.zeros_like(active_power_arr, dtype=float),
            where=np.abs(voltage_modulus_arr) > atol,
        ).tolist()

        curves_dict["BusPDR_BUS_ReactiveCurrent"] = np.divide(
            reactive_power_arr,
            voltage_modulus_arr,
            out=np.zeros_like(reactive_power_arr, dtype=float),
            where=np.abs(voltage_modulus_arr) > atol,
        ).tolist()

        self._get_magnitude_controlled_by_avr(generators, df_curves, curves_dict)

        for col in df_curves.columns:
            if "_TE_" in col or col == "time":
                continue
            if pd.api.types.is_complex_dtype(df_curves[col]):
                curves_dict[col] = self._get_modulus(df_curves[col].tolist())
            else:
                curves_dict[col] = df_curves[col].tolist()

        return pd.DataFrame(curves_dict)

    def _translate_curves(
        self, variable_translations: dict, df_curves_imported: pd.DataFrame
    ) -> pd.DataFrame:
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

    def _translate_complex_columns(
        self,
        variable_translations: dict,
        df_curves_imported: pd.DataFrame,
        curves_translation: dict,
        column: str,
        column_size: int,
    ) -> None:
        for translated_column in variable_translations[column]:
            curves_translation[translated_column[:-2]] = self._prepare_complex_column(
                column[:-2],
                column_size,
                df_curves_imported,
                translated_column[:-2],
                variable_translations,
            )

    def _apply_sign_convention(
        self,
        variable_translations: dict,
        df_curves_imported: pd.DataFrame,
        curves_translation: dict,
        column: str,
    ) -> None:
        for translated_column in variable_translations[column]:
            sign = variable_translations[translated_column]
            curves_translation[translated_column] = np.multiply(
                df_curves_imported[column], sign
            ).tolist()

    def _prepare_complex_column(
        self,
        column_name: str,
        column_size: int,
        df_curves: pd.DataFrame,
        translated_column: str,
        variable_translations: dict,
    ) -> list:
        real_sign = f"{translated_column}Re"
        sign_real = variable_translations.get(real_sign, 1)
        imaginary_sign = f"{translated_column}Im"
        sign_imag = variable_translations.get(imaginary_sign, 1)

        complex_column_array = np.zeros(column_size, dtype=np.complex128)
        complex_column_array.real = np.multiply(df_curves[f"{column_name}re"], sign_real)
        complex_column_array.imag = np.multiply(df_curves[f"{column_name}im"], sign_imag)
        return complex_column_array.tolist()

    def _get_injected_current_curve(self, column_size: int, curves_translation: dict) -> None:
        cols = curves_translation.keys()
        idpu_re = re.compile(r".*_InjectedActiveCurrent$")
        iqpu_re = re.compile(r".*_InjectedReactiveCurrent$")
        idpu_list = list(filter(idpu_re.match, cols))
        iqpu_list = list(filter(iqpu_re.match, cols))

        for iqpu_col in iqpu_list:
            base_name = iqpu_col.replace("_InjectedReactiveCurrent", "")
            for idpu_col in idpu_list:
                if idpu_col.replace("_InjectedActiveCurrent", "") == base_name:
                    complex_column = np.zeros(column_size, dtype=np.complex128)
                    complex_column.real = curves_translation[idpu_col]
                    complex_column.imag = curves_translation[iqpu_col]
                    key = f"{base_name}_InjectedCurrent"
                    curves_translation[key] = complex_column.tolist()
                    break

    def _get_network_frequency_curve(self, curves_translation: dict) -> None:
        cols = curves_translation.keys()
        network_frequency_re = re.compile(r".*_NetworkFrequencyPu$")
        network_frequency_list = list(filter(network_frequency_re.match, cols))
        if network_frequency_list:
            curves_translation["NetworkFrequencyPu"] = curves_translation[
                network_frequency_list[0]
            ]

    def _get_pdr_voltage(self, df_curves: pd.DataFrame) -> list:
        voltage_columns_regex = re.compile(r".*_TE_.*_Voltage$")
        voltage_columns_list = list(filter(voltage_columns_regex.match, df_curves.columns))
        if voltage_columns_list:
            return df_curves[voltage_columns_list[0]].tolist()
        return []

    def _get_pdr_current(self, df_curves: pd.DataFrame, column_size: int) -> list:
        current_columns_regex = re.compile(r".*_TE_.*_Current$")
        current_columns_list = list(filter(current_columns_regex.match, df_curves.columns))
        if not current_columns_list:
            return []
        pdr_current_base_snref = np.zeros(column_size, dtype=np.complex128)
        for current_column in current_columns_list:
            pdr_current_base_snref = np.add(
                pdr_current_base_snref, list(df_curves[current_column])
            )
        return pdr_current_base_snref.tolist()

    def _get_pdr_active_power(
        self, pdr_voltage: list, pdr_current: list, snom: float, snref: float
    ) -> list:
        pdr_active_power_base_snref = np.real(pdr_voltage * np.conjugate(pdr_current)) * -1
        pdr_active_power = pdr_active_power_base_snref * (snref / snom)
        return pdr_active_power.tolist()

    def _get_pdr_reactive_power(
        self, pdr_voltage: list, pdr_current: list, snom: float, snref: float
    ) -> list:
        pdr_reactive_power_base_snref = np.imag(pdr_voltage * np.conjugate(pdr_current)) * -1
        pdr_reactive_power = pdr_reactive_power_base_snref * (snref / snom)
        return pdr_reactive_power.tolist()

    def _get_magnitude_controlled_by_avr(
        self, generators: list, df_curves: pd.DataFrame, curves_dict: dict
    ) -> None:
        delete_columns = []
        for generator in generators:
            variable = f"{generator.id}_GEN_MagnitudeControlledByAVRPu"
            u_variable = f"{generator.id}_GEN_MagnitudeControlledByAVRUPu"
            q_variable = f"{generator.id}_GEN_MagnitudeControlledByAVRQPu"

            if variable in df_curves.columns:
                curves_dict[variable] = df_curves[variable].tolist()
                delete_columns.append(variable)
            elif u_variable in df_curves.columns:
                if (
                    getattr(generator, "UseVoltageDroop", False)
                    and q_variable in df_curves.columns
                ):
                    curve_u = df_curves[u_variable].to_numpy()
                    curve_q = df_curves[q_variable].to_numpy()
                    voltage_drop = float(getattr(generator, "VoltageDroop", 0.0))
                    curves_dict[variable] = np.add(
                        curve_u, np.multiply(curve_q, voltage_drop)
                    ).tolist()
                    delete_columns.extend([u_variable, q_variable])
                else:
                    curves_dict[variable] = df_curves[u_variable].tolist()
                    delete_columns.append(u_variable)
                    if q_variable in df_curves.columns:
                        delete_columns.append(q_variable)

        for column in delete_columns:
            if column in df_curves.columns:
                del df_curves[column]

    def _get_modulus(self, complex_list: list) -> list:
        return np.abs(complex_list).tolist()

    @staticmethod
    def _trim_curves(
        time_values: list[float],
        voltage_values: list[float],
        fault_start: float,
        fault_duration: float,
    ) -> tuple[list[float], list[float], list[float], list[float]]:
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
        post_time_values = time_values[start_idx + 1 : end_idx + 1]
        post_voltage_values = voltage_values[start_idx + 1 : end_idx + 1]
        return pre_time_values, post_time_values, pre_voltage_values, post_voltage_values
