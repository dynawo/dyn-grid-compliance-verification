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

from dycov.configuration.cfg import config
from dycov.curves.dynawo.runtime._process import (
    find_timeline_error,
    run_dynawo_process,
    terminate_all_children,
)
from dycov.curves.dynawo.runtime.run_types import DynawoRunInputs
from dycov.files import manage_files

DynawoResult = namedtuple("DynawoResult", "succeeded log timeline_error curves_file sim_time")


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
            - str | None: The error Dynawo reported in its log, if it reported one.
            - Path | None: The curves file Dynawo wrote, None when it wrote none.
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
            working_oc_dir,
            jobs_output_dir,
            simulation_limit=max_sim_time,
        )

        time_exceeds = result.sim_time > max_sim_time
        log = result.log
        succeeded = result.succeeded and not time_exceeds

        if result.timeline_error:
            log_path = str(output_dir / jobs_output_dir / "logs/dynawo.log")
            log = f"Simulation Fails: {result.timeline_error}, logs in {log_path}"

        return DynawoResult(
            succeeded=succeeded,
            log=log,
            timeline_error=result.timeline_error,
            curves_file=result.curves_file,
            sim_time=result.sim_time,
        )

    @staticmethod
    def run_simple(
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        launcher_dwo: str,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        simulation_limit: float,
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
        working_oc_dir : Path
            Directory containing the operational condition files for the simulation.
        jobs_output_dir : Path
            Subdirectory where the simulation outputs will be stored.
        simulation_limit : float
            Maximum time (in seconds) allowed for the simulation to run.

        Returns
        -------
        DynawoResult
            A named tuple containing:
            - bool: True if the simulation completed successfully.
            - str | None: Log output from stderr if an error occurred, otherwise None.
            - str | None: The error Dynawo reported in its log, if it reported one.
            - Path | None: The curves file Dynawo wrote, None when it wrote none.
            - float: The actual time taken for the simulation.
        """
        return DynawoSimulator().run_base_dynawo(
            pcs_name,
            bm_name,
            oc_name,
            launcher_dwo,
            "TSOModel",
            working_oc_dir,
            jobs_output_dir,
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
        inputs_path: Path,
        output_path: Path,
        simulation_limit: float | None = None,
    ) -> DynawoResult:
        """
        Runs a dynamic simulation with Dynawo and reports what Dynawo did.

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
        inputs_path : Path
            Directory containing Dynamic input files.
        output_path : Path
            Directory where Dynamic simulation outputs will be written.
        simulation_limit : float | None, optional
            Maximum time (in seconds) allowed for the simulation to run.
            If None, no timeout is applied. Defaults to None.

        Returns
        -------
        DynawoResult
            A named tuple containing:
            - bool: True if the simulation completed successfully.
            - str | None: Log output from stderr if an error occurred, otherwise None.
            - str | None: The error Dynawo reported in its log, if it reported one.
            - Path | None: The curves file Dynawo wrote, None when it wrote none.
            - float: The actual time taken for the simulation.
        """
        dynawo_output_full_path = inputs_path / output_path
        manage_files.remove_dir(dynawo_output_full_path)

        outcome = run_dynawo_process(launcher_dwo, jobs_filename, inputs_path, simulation_limit)

        log_file_path = dynawo_output_full_path / "logs/dynawo.log"
        timeline_error = find_timeline_error(log_file_path)

        succeeded = outcome.completed_successfully and not timeline_error
        log = outcome.stderr if not succeeded else None

        curves_path = dynawo_output_full_path / "curves/curves.csv"
        return DynawoResult(
            succeeded=succeeded,
            log=log,
            timeline_error=timeline_error,
            curves_file=curves_path if curves_path.exists() else None,
            sim_time=outcome.elapsed_seconds,
        )
