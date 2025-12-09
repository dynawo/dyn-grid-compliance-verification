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

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from dycov.configuration.cfg import config
from dycov.curves.dynawo.runtime.dynawo_simulator import DynawoSimulator
from dycov.curves.dynawo.runtime.run_types import DynawoRunInputs, SolverParams
from dycov.files import replace_placeholders
from dycov.logging.logging import dycov_logging


@dataclass
class RetrySettings:
    step_divisor: float = 10.0
    accuracy_multiplier: float = 10.0
    add_parameters_small_network: bool = True
    enable_solver_flip: bool = True

    @staticmethod
    def from_config() -> "RetrySettings":
        return RetrySettings(
            step_divisor=config.get_float("Dynawo", "retry_step_divisor", 10.0),
            accuracy_multiplier=config.get_float("Dynawo", "retry_accuracy_multiplier", 10.0),
            add_parameters_small_network=config.get_boolean(
                "Dynawo", "retry_add_parameters_small_network", True
            ),
            enable_solver_flip=config.get_boolean("Dynawo", "retry_solver_flip", True),
        )


class SolverRetryStrategy:
    def __init__(self, settings: Optional[RetrySettings] = None):
        self.settings = settings or RetrySettings.from_config()

    def run(
        self,
        run: DynawoRunInputs,
        solver: SolverParams,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        bm_name: str,
        oc_name: str,
        max_sim_time: Optional[float],
    ) -> Tuple[bool, bool, str, pd.DataFrame, float]:
        logger = dycov_logging.get_logger("ProducerCurves")
        title = f"{run.pcs_name}.{bm_name}.{oc_name}:"

        # 1) Baseline
        success, time_exceeds, log, curves_df, sim_time = DynawoSimulator.run_base(
            run, output_dir, working_oc_dir, jobs_output_dir, bm_name, oc_name, max_sim_time
        )
        if success:
            return success, time_exceeds, log, curves_df, sim_time

        # 2) Reduce min step
        logger.warning(f"{title} Retry: reducing minimum time step")
        self._reduce_min_step(solver, working_oc_dir)
        success, time_exceeds, log, curves_df, sim_time = DynawoSimulator.run_base(
            run, output_dir, working_oc_dir, jobs_output_dir, bm_name, oc_name, max_sim_time
        )
        if success:
            return success, time_exceeds, log, curves_df, sim_time

        # 3) Increase required accuracy
        logger.warning(f"{title} Retry: increasing required accuracy")
        self._increase_accuracy(solver, working_oc_dir)
        success, time_exceeds, log, curves_df, sim_time = DynawoSimulator.run_base(
            run, output_dir, working_oc_dir, jobs_output_dir, bm_name, oc_name, max_sim_time
        )
        if success:
            return success, time_exceeds, log, curves_df, sim_time

        # 4) Add parameters for small networks
        if self.settings.add_parameters_small_network:
            logger.warning(f"{title} Retry: adding parameters for small networks")
            self._add_parameters_small_networks(solver, working_oc_dir)
            success, time_exceeds, log, curves_df, sim_time = DynawoSimulator.run_base(
                run, output_dir, working_oc_dir, jobs_output_dir, bm_name, oc_name, max_sim_time
            )
            if success:
                return success, time_exceeds, log, curves_df, sim_time

        # 5) Flip solver type
        if self.settings.enable_solver_flip:
            logger.warning(f"{title} Retry: flipping solver type SIM <-> IDA")
            self._flip_solver(solver)
            replace_placeholders.modify_jobs_file(
                working_oc_dir, "TSOModel.jobs", solver.solver_id, solver.solver_lib
            )
            success, time_exceeds, log, curves_df, sim_time = DynawoSimulator.run_base(
                run, output_dir, working_oc_dir, jobs_output_dir, bm_name, oc_name, max_sim_time
            )

        if time_exceeds:
            logger.warning(f"{title} Simulation time exceeds the maximum allowed ({max_sim_time})")
        return success, time_exceeds, log, curves_df, sim_time

    # --- mutations & file updates ---
    def _reduce_min_step(self, solver: SolverParams, working_oc_dir: Path) -> None:
        solver.minimum_time_step /= self.settings.step_divisor
        solver.minimal_acceptable_step /= self.settings.step_divisor
        param_name_min_step = "minStep" if solver.solver_id == "IDA" else "hMin"
        replace_placeholders.modify_par_file(
            working_oc_dir, "solvers.par", param_name_min_step, solver.minimum_time_step
        )
        replace_placeholders.modify_par_file(
            working_oc_dir, "solvers.par", "minimalAcceptableStep", solver.minimal_acceptable_step
        )

    def _increase_accuracy(self, solver: SolverParams, working_oc_dir: Path) -> None:
        if solver.relAccuracy is not None:
            solver.relAccuracy *= self.settings.accuracy_multiplier
        solver.absAccuracy *= self.settings.accuracy_multiplier
        if solver.solver_id == "IDA":
            if solver.relAccuracy is not None:
                replace_placeholders.modify_par_file(
                    working_oc_dir, "solvers.par", "relAccuracy", solver.relAccuracy
                )
            replace_placeholders.modify_par_file(
                working_oc_dir, "solvers.par", "absAccuracy", solver.absAccuracy
            )
        else:  # SIM
            replace_placeholders.modify_par_file(
                working_oc_dir, "solvers.par", "fnormtol", solver.absAccuracy
            )

    def _add_parameters_small_networks(self, solver: SolverParams, working_oc_dir: Path) -> None:
        if solver.solver_id == "IDA":
            replace_placeholders.add_parameters(
                working_oc_dir,
                "solvers.par",
                solver.solver_id,
                [
                    {"type": "INT", "name": "maximumNumberSlowStepIncrease", "value": "100"},
                    {"type": "INT", "name": "mxiterAlg", "value": "30"},
                    {"type": "INT", "name": "mxiterAlgInit", "value": "30"},
                    {"type": "INT", "name": "mxiterAlgJ", "value": "30"},
                    {"type": "INT", "name": "msbsetAlg", "value": "1"},
                ],
            )
        else:  # SIM
            replace_placeholders.add_parameters(
                working_oc_dir,
                "solvers.par",
                solver.solver_id,
                [
                    {"type": "INT", "name": "maximumNumberSlowStepIncrease", "value": "100"},
                    {"type": "INT", "name": "maxNewtonTry", "value": "30"},
                    {"type": "INT", "name": "msbset", "value": "1"},
                ],
            )

    def _flip_solver(self, solver: SolverParams) -> None:
        if solver.solver_id == "SIM":
            solver.solver_id = "IDA"
            solver.solver_lib = "dynawo_SolverIDA"
            solver.minimum_time_step = config.get_float("Dynawo", "ida_minStep", 1e-6)
            solver.minimal_acceptable_step = config.get_float(
                "Dynawo", "ida_minimalAcceptableStep", 1e-6
            )
            solver.absAccuracy = config.get_float("Dynawo", "ida_absAccuracy", 1e-6)
            solver.relAccuracy = config.get_float("Dynawo", "ida_relAccuracy", 1e-4)
        else:
            solver.solver_id = "SIM"
            solver.solver_lib = "dynawo_SolverSIM"
            solver.minimum_time_step = config.get_float("Dynawo", "sim_hMin", 1e-6)
            solver.minimal_acceptable_step = config.get_float(
                "Dynawo", "sim_minimalAcceptableStep", 1e-6
            )
            solver.absAccuracy = config.get_float("Dynawo", "sim_fnormtol", 1e-4)
            solver.relAccuracy = None
