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

from collections import namedtuple
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

DynawoResult = namedtuple("DynawoResult", "succeeded log has_timeline_error curves sim_time")


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
            - bool: True if the simulation completed successfully.
            - str | None: Log output from stderr if an error occurred, otherwise None.
            - bool: True if an error was found in the Dynamic timeline log.
            - pd.DataFrame: Transformed and calculated curves, empty on failure.
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
            Subdirectory where the simulation outputs will be stored.
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
            - bool: True if the simulation completed successfully.
            - str | None: Log output from stderr if an error occurred, otherwise None.
            - bool: True if an error was found in the Dynamic timeline log.
            - pd.DataFrame: Transformed and calculated curves, empty on failure.
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
            - bool: True if the simulation completed successfully.
            - str | None: Log output from stderr if an error occurred, otherwise None.
            - bool: True if an error was found in the Dynamic timeline log.
            - pd.DataFrame: Transformed and calculated curves, empty on failure.
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
