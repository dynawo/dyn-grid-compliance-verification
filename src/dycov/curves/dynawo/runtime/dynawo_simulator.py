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
from collections import namedtuple
from enum import IntEnum
from pathlib import Path

import pandas as pd

from dycov.configuration.cfg import config
from dycov.curves.dynawo.runtime._curves import create_curves
from dycov.curves.dynawo.runtime._process import (
    has_error_timeline,
    run_dynawo_process,
    terminate_all_children,
)
from dycov.curves.dynawo.runtime.run_types import DynawoRunInputs
from dycov.files import manage_files
from dycov.logging.logging import dycov_logging
from dycov.validation.common import is_stable

VOLTAGE_DIP_THRESHOLD = 0.002
NO_FAULT_SENTINEL = 9999.0
ABS_TOLERANCE_FACTOR = 0.1
TIME_EPSILON = 1e-4

DynawoResult = namedtuple("DynawoResult", "succeeded log has_timeline_error curves sim_time")
TrimmedCurves = namedtuple("TrimmedCurves", "pre_time post_time pre_voltage post_voltage")


class VoltDipResult(IntEnum):
    """Result codes for voltage dip comparison."""

    COLUMN_MISSING = -2  # Error: BusPDR_BUS_Voltage column not found
    DIP_TOO_SMALL = -1  # Actual dip < expected (need more impedance)
    DIP_CORRECT = 0  # Actual dip ≈ expected (within tolerance)
    DIP_TOO_LARGE = 1  # Actual dip > expected (need less impedance)


class DynawoSimulator:
    @staticmethod
    def run_base(
        run: DynawoRunInputs,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        bm_name: str,
        oc_name: str,
        max_sim_time: float | None = None,
    ) -> DynawoResult:
        """
        Baseline execution with configured limits.

        Parameters
        ----------
        run : DynawoRunInputs
            Structured input containing all necessary parameters for the simulation.
        output_dir : Path
            Base directory for all outputs, used for logging reference.
        working_oc_dir : Path
            Directory containing the operational condition files for the simulation.
        jobs_output_dir : Path
            Subdirectory under output_dir where the simulation outputs (logs, curves)
            will be stored.
        bm_name : str
            Benchmark name for logging purposes.
        oc_name : str
            Operational Condition name for logging purposes.
        max_sim_time : float | None, optional
            Maximum time (in seconds) allowed for the simulation to run. If None, it will be
            read from configuration. Defaults to None.

        Returns
        -------
        DynawoResult
            A named tuple containing:
            - bool: True if the simulation completed successfully (no errors in log,
              no timeout, "succeeded" in stderr).
            - str | None: Log output from stderr if an error occurred or timeout,
              otherwise None.
            - bool: True if an error was found in the Dynamic timeline log, False otherwise.
            - pd.DataFrame: A DataFrame with the transformed and calculated curves. Empty
              if save_file is False or simulation failed.
            - float: The actual time taken for the simulation.
        """
        if max_sim_time is None:
            max_sim_time = config.get_float("Dynawo", "simulation_limit", 30.0)

        result = DynawoSimulator().run_base_dynawo(
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
            run.f_nom,
            simulation_limit=max_sim_time,
        )

        time_exceeds = result.sim_time > max_sim_time
        log = result.log
        succeeded = result.succeeded and not time_exceeds

        if result.has_timeline_error:
            log_path = str(output_dir / jobs_output_dir / "logs/dynawo.log")
            log = f"Simulation Fails, logs in {log_path}"

        return DynawoResult(
            succeeded=succeeded,
            log=log,
            has_timeline_error=result.has_timeline_error,
            curves=result.curves,
            sim_time=result.sim_time,
        )

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
        f_nom: float,
        simulation_limit: float,
        save_file: bool = False,
    ) -> DynawoResult:
        """
        Thin wrapper without retry (useful for CCT flows).

        Parameters
        ----------
        pcs_name : str
            Power System Case name for logging.
        bm_name : str
            Benchmark name for logging.
        oc_name : str
            Operational Condition name for logging.
        launcher_dwo : str
            Path to the Dynamic launcher executable.
        curves_dict : dict
            Dictionary of curves to be passed to the simulator.
        working_oc_dir : Path
            Directory containing the operational condition files for the simulation.
        jobs_output_dir : Path
            Subdirectory under output_dir where the simulation outputs (logs, curves)
            will be stored.
        generators : list
            List of generator objects, used for specific curve calculations.
        s_nom : float
            Nominal apparent power of the system.
        s_nref : float
            System-wide S base (SnRef).
        f_nom : float
            Nominal frequency of the system.
        simulation_limit : float
            Maximum time (in seconds) allowed for the simulation to run.
        save_file : bool, optional
            If True, the calculated curves DataFrame will be created and returned.
            Defaults to False.

        Returns
        -------
        DynawoResult
            A named tuple containing:
            - bool: True if the simulation completed successfully (no errors in log,
              no timeout, "succeeded" in stderr).
            - str | None: Log output from stderr if an error occurred or timeout,
              otherwise None.
            - bool: True if an error was found in the Dynamic timeline log, False otherwise.
            - pd.DataFrame: A DataFrame with the transformed and calculated curves. Empty
              if save_file is False or simulation failed.
            - float: The actual time taken for the simulation.
        """
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
            f_nom,
            save_file=save_file,
            simulation_limit=simulation_limit,
        )

    @staticmethod
    def measure_voltage_dip(
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        curves: pd.DataFrame,
        fault_start: float,
        fault_duration: float,
    ) -> float | None:
        """
        Measures the voltage dip magnitude from the simulated curves.

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

        Returns
        -------
        float | None
            The measured voltage dip (pre_fault_voltage - post_fault_voltage), or None
            if the required voltage column is missing from the curves.
        """
        if fault_duration == 0.0:
            return None

        return DynawoSimulator._compute_voltage_dip(
            pcs_name, bm_name, oc_name, curves, fault_start, fault_duration
        )

    @staticmethod
    def classify_voltage_dip(
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        curves: pd.DataFrame,
        fault_start: float,
        fault_duration: float,
        expected_dip: float,
    ) -> int:
        """
        Classifies the voltage dip magnitude relative to expected value.

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
        VoltDipResult
            Classification of the voltage dip:
            - COLUMN_MISSING: Required column not found in curves
            - DIP_TOO_SMALL: Increase fault impedance
            - DIP_CORRECT: Within tolerance
            - DIP_TOO_LARGE: Decrease fault impedance
        """
        if expected_dip == 0.0:
            return VoltDipResult.DIP_CORRECT

        voltage_dip = DynawoSimulator._compute_voltage_dip(
            pcs_name, bm_name, oc_name, curves, fault_start, fault_duration
        )
        if voltage_dip is None:
            return VoltDipResult.COLUMN_MISSING

        dycov_logging.get_logger("DynawoSimulator").debug(
            f"Calculated Voltage dip: {voltage_dip:.4f}, Expected dip: {expected_dip:.4f}"
        )

        rtol = VOLTAGE_DIP_THRESHOLD
        atol = ABS_TOLERANCE_FACTOR * rtol
        if math.isclose(voltage_dip, expected_dip, rel_tol=rtol, abs_tol=atol):
            return VoltDipResult.DIP_CORRECT
        if expected_dip < voltage_dip:
            return VoltDipResult.DIP_TOO_LARGE
        return VoltDipResult.DIP_TOO_SMALL

    @staticmethod
    def terminate_all_children(timeout: float = 5.0) -> None:
        """Gracefully stop all child processes started by DynawoSimulator.
        Idempotent and best-effort: never raises.
        """
        terminate_all_children(timeout)

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
        f_nom: float,
        save_file: bool = True,
        simulation_limit: float | None = None,
    ) -> DynawoResult:
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
        f_nom : float
            Nominal frequency of the system.
        save_file : bool, optional
            If True, the calculated curves DataFrame will be created and returned.
            Defaults to True.
        simulation_limit : float | None, optional
            Maximum time (in seconds) allowed for the simulation to run.
            If None, no timeout is applied. Defaults to None.

        Returns
        -------
        DynawoResult
            A named tuple containing:
            - bool: True if the simulation completed successfully (no errors in log,
              no timeout, "succeeded" in stderr).
            - str | None: Log output from stderr if an error occurred or timeout,
              otherwise None.
            - bool: True if an error was found in the Dynamic timeline log, False otherwise.
            - pd.DataFrame: A DataFrame with the transformed and calculated curves. Empty
              if save_file is False or simulation failed.
            - float: The actual time taken for the simulation.
        """
        dynawo_output_full_path = inputs_path / output_path
        manage_files.remove_dir(dynawo_output_full_path)

        outcome = run_dynawo_process(launcher_dwo, jobs_filename, inputs_path, simulation_limit)

        log_file_path = dynawo_output_full_path / "logs/dynawo.log"
        timeline_error = has_error_timeline(pcs_name, bm_name, oc_name, log_file_path)

        succeeded = outcome.completed_successfully and not timeline_error
        log = outcome.stderr if not succeeded else None

        curves_path = dynawo_output_full_path / "curves/curves.csv"
        curves_calculated = self._load_curves_if_available(
            curves_path,
            variable_translations,
            generators,
            s_nom,
            s_nref,
            f_nom,
            save_file,
            succeeded,
        )

        return DynawoResult(
            succeeded=succeeded,
            log=log,
            has_timeline_error=timeline_error,
            curves=curves_calculated,
            sim_time=outcome.elapsed_seconds,
        )

    def _load_curves_if_available(
        self,
        path: Path,
        variable_translations: dict,
        generators: list,
        s_nom: float,
        s_nref: float,
        f_nom: float,
        save_file: bool,
        succeeded: bool,
    ) -> pd.DataFrame:
        if not path.exists() or not succeeded or not save_file:
            return pd.DataFrame()
        return create_curves(variable_translations, path, generators, s_nom, s_nref, f_nom)

    @staticmethod
    def _compute_voltage_dip(
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        curves: pd.DataFrame,
        fault_start: float,
        fault_duration: float,
    ) -> float | None:
        bus_pdr_voltage_column = "BusPDR_BUS_Voltage"
        if bus_pdr_voltage_column not in curves.columns:
            return None

        time_values = curves["time"].tolist()
        voltage_values = curves[bus_pdr_voltage_column].tolist()
        clamped_duration = DynawoSimulator._clamp_fault_duration(
            pcs_name, bm_name, oc_name, fault_start, fault_duration, time_values
        )
        trimmed = DynawoSimulator._trim_curves(
            time_values, voltage_values, fault_start, clamped_duration
        )

        try:
            _, pre_stable_idx = is_stable(
                trimmed.pre_time, trimmed.pre_voltage, clamped_duration / 10
            )
        except ValueError:
            pre_stable_idx = len(trimmed.pre_voltage) - 1 if trimmed.pre_voltage else 0

        _, post_stable_idx = is_stable(
            trimmed.post_time, trimmed.post_voltage, clamped_duration / 10
        )

        pre_fault_voltage = trimmed.pre_voltage[pre_stable_idx] if trimmed.pre_voltage else 0.0
        post_fault_voltage = trimmed.post_voltage[post_stable_idx] if trimmed.post_voltage else 0.0
        return pre_fault_voltage - post_fault_voltage

    @staticmethod
    def _clamp_fault_duration(
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        fault_start: float,
        fault_duration: float,
        time_values: list[float],
    ) -> float:
        simulation_end = time_values[-1]
        if fault_duration == NO_FAULT_SENTINEL:
            return simulation_end - fault_start
        if fault_start + fault_duration > simulation_end:
            clamped = simulation_end - fault_start
            dycov_logging.get_logger("DynawoSimulator").warning(
                f"{pcs_name}.{bm_name}.{oc_name}: "
                "Fault duration extends beyond simulation time. Adjusting fault_duration "
                f"from {fault_duration} to {clamped:.4f}."
            )
            return clamped
        return fault_duration

    @staticmethod
    def _trim_curves(
        time_values: list[float],
        voltage_values: list[float],
        fault_start: float,
        fault_duration: float,
    ) -> TrimmedCurves:
        pre_idx = 0
        start_idx = 0
        end_idx = -1
        for i, t in enumerate(time_values):
            if t - fault_start < -TIME_EPSILON:
                pre_idx = i
            if fault_start - t > TIME_EPSILON:
                start_idx = i
            if t - (fault_start + fault_duration) < -TIME_EPSILON:
                end_idx = i

        return TrimmedCurves(
            pre_time=time_values[: pre_idx + 1],
            post_time=time_values[start_idx + 1 : end_idx + 1],
            pre_voltage=voltage_values[: pre_idx + 1],
            post_voltage=voltage_values[start_idx + 1 : end_idx + 1],
        )
