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

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.curves.dynawo.runtime.dynawo_simulator import DynawoResult, DynawoSimulator
from dycov.curves.dynawo.runtime.run_types import DynawoRunInputs, SolverParams
from dycov.files import replace_placeholders
from dycov.logging import dycov_logging

Remedy = Callable[[SolverParams, Path], str]
"""A change tried on the solver, which reports what it changed."""

_SMALL_NETWORK_PARAMETERS = {
    "IDA": [
        {"type": "INT", "name": "maximumNumberSlowStepIncrease", "value": "100"},
        {"type": "INT", "name": "mxiterAlg", "value": "30"},
        {"type": "INT", "name": "mxiterAlgInit", "value": "30"},
        {"type": "INT", "name": "mxiterAlgJ", "value": "30"},
        {"type": "INT", "name": "msbsetAlg", "value": "1"},
    ],
    "SIM": [
        {"type": "INT", "name": "maximumNumberSlowStepIncrease", "value": "100"},
        {"type": "INT", "name": "maxNewtonTry", "value": "30"},
        {"type": "INT", "name": "msbset", "value": "1"},
    ],
}


@dataclass
class RetrySettings:
    step_divisor: float = 10.0
    accuracy_multiplier: float = 10.0
    add_parameters_small_network: bool = True
    enable_solver_flip: bool = True
    allowed_retries: int = 4
    attempt_count: int = 0
    disable_retry_logs: bool = False

    @staticmethod
    def from_config(disable_retry_logs: bool) -> "RetrySettings":
        return RetrySettings(
            step_divisor=config.get_float("Dynawo", "retry_step_divisor", 10.0),
            accuracy_multiplier=config.get_float("Dynawo", "retry_accuracy_multiplier", 10.0),
            add_parameters_small_network=config.get_boolean(
                "Dynawo", "retry_add_parameters_small_network", True
            ),
            enable_solver_flip=config.get_boolean("Dynawo", "retry_solver_flip", True),
            allowed_retries=config.get_int("Debug", "max_simulation_retries", 4),
            disable_retry_logs=disable_retry_logs,
        )


class SolverRetryStrategy:
    def __init__(self, settings: RetrySettings | None = None):
        self.settings = settings or RetrySettings.from_config(disable_retry_logs=False)

    def run(
        self,
        run: DynawoRunInputs,
        solver: SolverParams,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        bm_name: str,
        oc_name: str,
        max_sim_time: float | None,
    ) -> DynawoResult:
        result = self._attempt(
            run, output_dir, working_oc_dir, jobs_output_dir, bm_name, oc_name, max_sim_time
        )
        for remedy in self._remedies():
            if result.succeeded or self._retries_exhausted():
                return result

            self._warn(
                f"Retry {self.settings.attempt_count}/{self.settings.allowed_retries}: "
                f"{remedy(solver, working_oc_dir)} "
                f"(previous attempt: {self._why_it_failed(result, max_sim_time)})"
            )
            result = self._attempt(
                run, output_dir, working_oc_dir, jobs_output_dir, bm_name, oc_name, max_sim_time
            )

        if result.sim_time > (max_sim_time or float("inf")):
            self._warn(f"Simulation time exceeds the maximum allowed ({max_sim_time})")
        return result

    def _remedies(self) -> Iterator[Remedy]:
        """The changes tried on the solver, in the order they are tried."""
        yield self._reduce_min_step
        yield self._increase_accuracy
        if self.settings.add_parameters_small_network:
            yield self._add_parameters_small_networks
        if self.settings.enable_solver_flip:
            yield self._flip_solver

    def _why_it_failed(self, result: DynawoResult, max_sim_time: float | None) -> str:
        """What the attempt just made reported, to be quoted in the retry message."""
        if max_sim_time is not None and result.sim_time > max_sim_time:
            return f"took {result.sim_time:.1f}s, over the {max_sim_time}s limit"
        if result.timeline_error:
            return result.timeline_error
        reported = (result.log or "").strip().splitlines()
        return reported[-1] if reported else "Dynawo did not report success"

    def _warn(self, message: str) -> None:
        if not self.settings.disable_retry_logs:
            dycov_logging.get_logger("SolverRetryStrategy").warning(message)

    # --- attempt helper ---
    def _attempt(
        self,
        run: DynawoRunInputs,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        bm_name: str,
        oc_name: str,
        max_sim_time: float | None,
    ) -> DynawoResult:
        self.settings.attempt_count += 1
        return DynawoSimulator.run_base(
            run, output_dir, working_oc_dir, jobs_output_dir, bm_name, oc_name, max_sim_time
        )

    def _retries_exhausted(self) -> bool:
        return self.settings.attempt_count > self.settings.allowed_retries

    # --- mutations & file updates ---
    def _reduce_min_step(self, solver: SolverParams, working_oc_dir: Path) -> str:
        previous = solver.minimum_time_step
        solver.minimum_time_step /= self.settings.step_divisor
        solver.minimal_acceptable_step /= self.settings.step_divisor
        param_name_min_step = "minStep" if solver.solver_id == "IDA" else "hMin"
        replace_placeholders.modify_par_file(
            working_oc_dir, "solvers.par", param_name_min_step, solver.minimum_time_step
        )
        replace_placeholders.modify_par_file(
            working_oc_dir, "solvers.par", "minimalAcceptableStep", solver.minimal_acceptable_step
        )
        return (
            f"{param_name_min_step} {previous:.3g} -> {solver.minimum_time_step:.3g}, "
            f"minimalAcceptableStep {solver.minimal_acceptable_step:.3g}"
        )

    def _increase_accuracy(self, solver: SolverParams, working_oc_dir: Path) -> str:
        previous = solver.absAccuracy
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
            return (
                f"absAccuracy {previous:.3g} -> {solver.absAccuracy:.3g}, "
                f"relAccuracy {solver.relAccuracy:.3g}"
            )

        replace_placeholders.modify_par_file(
            working_oc_dir, "solvers.par", "fnormtol", solver.absAccuracy
        )
        return f"fnormtol {previous:.3g} -> {solver.absAccuracy:.3g}"

    def _add_parameters_small_networks(self, solver: SolverParams, working_oc_dir: Path) -> str:
        parameters = _SMALL_NETWORK_PARAMETERS[solver.solver_id]
        replace_placeholders.add_parameters(
            working_oc_dir, "solvers.par", solver.solver_id, parameters
        )
        solver.added_parameters.update({p["name"]: p["value"] for p in parameters})
        added = ", ".join(f"{name}={value}" for name, value in solver.added_parameters.items())
        return f"added the small network parameters ({added})"

    def _flip_solver(self, solver: SolverParams, working_oc_dir: Path) -> str:
        previous = solver.solver_id
        # The parameters added so far belong to the set of the solver being left behind.
        solver.added_parameters.clear()
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
        replace_placeholders.modify_jobs_file(
            working_oc_dir, "TSOModel.jobs", solver.solver_id, solver.solver_lib
        )
        return f"solver {previous} -> {solver.solver_id}, back to its configured settings"
