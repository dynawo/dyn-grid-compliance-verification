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

from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from dycov.configuration.cfg import config
from dycov.curves.dynawo.runtime.dynawo import DynawoSimulator
from dycov.curves.dynawo.runtime.run_types import DynawoRunInputs


class DynamicSimulator:
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
        """
        Executes a baseline Dynawo run through DynawoSimulator using configured limits.

        Parameters
        ----------
        run : DynawoRunInputs
            Run inputs (PCS name, launcher, curves map, generators, S_nom, S_nref).
        output_dir : Path
            Final output directory of the simulation.
        working_oc_dir : Path
            Working directory for the operational condition.
        jobs_output_dir : Path
            Output directory declared by the jobs file.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        max_sim_time : float, optional
            Maximum allowed simulation time; if None, read from configuration.

        Returns
        -------
        Tuple[bool, bool, str, pd.DataFrame, float]
            (success, time_exceeds, log_message, curves_dataframe, sim_time_s)
        """
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
        # Stateless: do not write-back to DynawoCurves here.
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
        """
        Executes a thin Dynawo run wrapper (no retry strategy), useful for CCT flows.

        Parameters
        ----------
        pcs_name : str
            PCS name.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        launcher_dwo : str
            Dynawo launcher path or command.
        curves_dict : dict
            Curves definition dictionary for CRV.
        working_oc_dir : Path
            Working directory for the attempt run.
        jobs_output_dir : Path
            Output directory declared by the jobs file.
        generators : list
            Generators participating in the simulation.
        s_nom : float
            Producer nominal apparent power.
        s_nref : float
            Reference nominal apparent power.
        simulation_limit : float
            Maximum allowed simulation time for this run.
        save_file : bool, optional
            Whether to request Dynawo to produce output files (CSV, etc.), by default False.

        Returns
        -------
        Tuple[bool, bool, str, pd.DataFrame, float]
            (success, time_exceeds, log_message, curves_dataframe, sim_time_s)
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
            save_file=save_file,
            simulation_limit=simulation_limit,
        )

    @staticmethod
    def check_voltage_dip(
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        curves_df: pd.DataFrame,
        fault_start: float,
        fault_duration: float,
        target_dip_abs: float,
    ) -> int:
        """
        Checks the achieved voltage dip against a target using Dynawo post-processing.

        Parameters
        ----------
        pcs_name : str
            PCS name.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        curves_df : pd.DataFrame
            DataFrame with curves computed by Dynawo.
        fault_start : float
            Fault start time (s).
        fault_duration : float
            Fault duration (s).
        target_dip_abs : float
            Target voltage dip in pu (absolute value).

        Returns
        -------
        int
            Comparison result:
            -  1 if required dip is greater than obtained,
            - -1 if required dip is less than obtained,
            -  0 if dip is achieved.
        """
        return DynawoSimulator().check_voltage_dip(
            pcs_name,
            bm_name,
            oc_name,
            curves_df,
            fault_start,
            fault_duration,
            target_dip_abs,
        )
