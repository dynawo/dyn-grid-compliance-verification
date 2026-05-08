#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#
import logging
from collections import namedtuple
from pathlib import Path

import pandas as pd

from dycov.configuration.cfg import config
from dycov.core.parameters import Parameters
from dycov.curves.curves import ProducerCurves, get_cfg_oc_name
from dycov.curves.dynawo.orchestrator.bisection import BisectionEngine
from dycov.curves.dynawo.orchestrator.model_setup import ModelSetup
from dycov.curves.dynawo.runtime.retry_strategy import RetrySettings, SolverRetryStrategy
from dycov.curves.dynawo.runtime.run_types import DynawoRunInputs, SolverParams
from dycov.curves.voltage_dip import measure_voltage_dip
from dycov.files import manage_files, model_parameters
from dycov.files.manage_files import ModelFiles, ProducerFiles
from dycov.logging.logging import dycov_logging
from dycov.logging.simulation_logger import SimulationLogger
from dycov.model.parameters import DisconnectionModel, SimulationError, SimulationResult
from dycov.model.producer import Producer
from dycov.sanity_checks import parameter_checks

_CURVES_CSV = "curves/curves.csv"

_ERROR_MAP = {
    "Fault simulation fails": SimulationError.FAULT_SIMULATION_FAILS,
    "Fault dip unachievable": SimulationError.FAULT_DIP_UNACHIEVABLE,
}

SimulateOutcome = namedtuple("SimulateOutcome", "succeeded time_exceeds has_curves curves")
SolverParam = namedtuple("SolverParam", "actual default")


def _to_simulation_error(message: str) -> SimulationError | None:
    return _ERROR_MAP.get(message)


class DynawoCurves(ProducerCurves):
    """
    Orchestrates the full Dynawo simulation workflow for one producer.

    Responsibilities:
    - Solver lifecycle: reset, build params, retry strategy.
    - Environment preparation: copy base-case and producer files.
    - Delegation to ModelSetup (model file completion) and
      BisectionEngine (HIZ / bolted / CCT search algorithms).
    - Post-simulation bookkeeping: voltage-dip measurement, result assembly.

    Model setup details live in ModelSetup; bisection algorithms live in
    BisectionEngine.  This class owns the public ProducerCurves interface.
    """

    def __init__(
        self,
        parameters: Parameters,
        producer: Producer,
        pcs_name: str,
        model_path: Path,
        omega_path: Path,
        pcs_path: Path,
        job_name: str,
        stable_time: float,
    ):
        """
        Parameters
        ----------
        parameters : Parameters
            Execution parameters for the simulation.
        producer : Producer
            The producer associated with these curves.
        pcs_name : str
            Name of the PCS (Power Control System).
        model_path : Path
            Path to the model directory.
        omega_path : Path
            Path to the Omega files directory.
        pcs_path : Path
            Path to the PCS directory.
        job_name : str
            Name of the job file.
        stable_time : float
            Time horizon used to evaluate stability in CCT calculations.
        """
        super().__init__(producer)
        self._output_dir = parameters.get_output_dir()
        self._launcher_dwo = parameters.get_launcher_dwo()
        self._pcs_name = pcs_name
        self._model_path = model_path
        self._omega_path = omega_path
        self._pcs_path = pcs_path
        self._job_name = job_name
        self._stable_time = stable_time

        self._f_nom = config.get_float("Dynawo", "f_nom", 50.0)
        self._s_nref = config.get_float("Dynawo", "s_nref", 100.0)
        self._simulation_start = config.get_float("Dynawo", "simulation_start", 0.0)
        self._simulation_stop = config.get_float("Dynawo", "simulation_stop", 100.0)
        self._simulation_precision = config.get_float("Dynawo", "simulation_precision", 1e-6)
        parameter_checks.check_simulation_duration(self.get_simulation_duration())

        self._sim_time = config.get_float("Dynawo", "simulation_limit", 30.0)

        # Solver parameters — initialised by __reset_solver
        self._solver_id = ""
        self._solver_lib = ""
        self._minimum_time_step = 0.0
        self._minimal_acceptable_step = 0.0
        self._absAccuracy = 0.0
        self._relAccuracy = 0.0
        self.__reset_solver()

        self._voltage_dip = None

        # Collaborators (created once; ModelSetup state is refreshed per OC)
        self._setup = ModelSetup(self, pcs_name, self._s_nref, self._f_nom)
        self._bisection = self._build_bisection_engine()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def __reset_solver(self) -> None:
        """Resets all solver parameters to their configured defaults."""
        self._solver_lib = config.get_value("Dynawo", "solver_lib", "dynawo_SolverIDA")
        self._solver_id = self._solver_lib.replace("dynawo_Solver", "")
        if self._solver_id == "IDA":
            self._minimum_time_step = config.get_float("Dynawo", "ida_minStep", 1e-6)
            self._minimal_acceptable_step = config.get_float(
                "Dynawo", "ida_minimalAcceptableStep", 1e-6
            )
            self._absAccuracy = config.get_float("Dynawo", "ida_absAccuracy", 1e-6)
            self._relAccuracy = config.get_float("Dynawo", "ida_relAccuracy", 1e-4)
        else:
            self._minimum_time_step = config.get_float("Dynawo", "sim_hMin", 1e-6)
            self._minimal_acceptable_step = config.get_float(
                "Dynawo", "sim_minimalAcceptableStep", 1e-6
            )
            self._absAccuracy = config.get_float("Dynawo", "sim_fnormtol", 1e-4)
            if hasattr(self, "_relAccuracy"):
                delattr(self, "_relAccuracy")
        parameter_checks.check_solver(self._solver_id, self._solver_lib)

    def _build_bisection_engine(self) -> BisectionEngine:
        return BisectionEngine(
            pcs_name=self._pcs_name,
            launcher_dwo=self._launcher_dwo,
            producer=self.get_producer(),
            s_nref=self._s_nref,
            f_nom=self._f_nom,
            sim_time=self._sim_time,
            stable_time=self._stable_time,
            curves_dict=self._setup.curves_dict,
        )

    def __prepare_oc_validation(
        self,
        working_oc_dir: Path,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
    ) -> tuple[Path, Path]:
        """
        Copies base-case and producer files into working_oc_dir.

        Returns
        -------
        tuple[Path, Path]
            (output_dir, jobs_output_dir)
        """
        op_path = self._model_path / oc_name
        op_path_name = op_path.resolve().name
        output_dir = self._output_dir / self._pcs_name / bm_name / op_path_name

        manage_files.copy_base_case_files(
            ModelFiles(
                self._model_path,
                self._omega_path,
                self._pcs_path,
                bm_name,
            ),
            ProducerFiles(
                self.get_producer().get_producer_dyd(),
                self.get_producer().get_producer_par(),
            ),
            working_oc_dir,
        )
        jobs_output_dir = model_parameters.find_output_dir(working_oc_dir, "TSOModel")
        return output_dir, jobs_output_dir

    def __build_run_inputs(self) -> DynawoRunInputs:
        return DynawoRunInputs(
            pcs_name=self._pcs_name,
            launcher_dwo=self._launcher_dwo,
            curves_dict=self._setup.curves_dict,
            generators=self.get_producer().generators,
            s_nom=self.get_producer().s_nom,
            s_nref=self._s_nref,
            f_nom=self._f_nom,
        )

    def __build_solver_params(self) -> SolverParams:
        return SolverParams(
            solver_id=self._solver_id,
            solver_lib=self._solver_lib,
            minimum_time_step=self._minimum_time_step,
            minimal_acceptable_step=self._minimal_acceptable_step,
            absAccuracy=self._absAccuracy,
            relAccuracy=self._relAccuracy if hasattr(self, "_relAccuracy") else None,
        )

    def __execute_simulation(
        self,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        bm_name: str,
        oc_name: str,
        max_sim_time: float | None = None,
    ):
        """
        Runs Dynawo via SolverRetryStrategy and returns a DynawoResult.

        Parameters
        ----------
        output_dir : Path
            Final output directory for saved results.
        working_oc_dir : Path
            Working directory for the current run.
        jobs_output_dir : Path
            Output sub-directory declared in the job file.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        max_sim_time : float | None
            Simulation time limit override; defaults to config value.
        """
        if max_sim_time is None:
            max_sim_time = config.get_float("Dynawo", "simulation_limit", 30.0)
        strategy = SolverRetryStrategy(RetrySettings.from_config())
        result = strategy.run(
            run=self.__build_run_inputs(),
            solver=self.__build_solver_params(),
            output_dir=output_dir,
            working_oc_dir=working_oc_dir,
            jobs_output_dir=jobs_output_dir,
            bm_name=bm_name,
            oc_name=oc_name,
            max_sim_time=max_sim_time,
        )
        if result.succeeded:
            self._sim_time = result.sim_time
        return result

    def __simulate(
        self,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        bm_name: str,
        oc_name: str,
    ) -> SimulateOutcome:
        """
        Runs the simulation and packages the result as a SimulateOutcome.

        Parameters
        ----------
        output_dir : Path
            Final output directory for saved results.
        working_oc_dir : Path
            Working directory for the current run.
        jobs_output_dir : Path
            Output sub-directory declared in the job file.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        """
        result = self.__execute_simulation(
            output_dir, working_oc_dir, jobs_output_dir, bm_name, oc_name
        )
        if not result.succeeded:
            dycov_logging.get_logger("ProducerCurves").warning(result.log)
        else:
            dycov_logging.get_logger("ProducerCurves").debug("Simulation successful")
        has_curves = (working_oc_dir / jobs_output_dir / _CURVES_CSV).exists() and result.succeeded
        return SimulateOutcome(
            succeeded=result.succeeded,
            time_exceeds=result.sim_time > self._sim_time,
            has_curves=has_curves,
            curves=result.curves,
        )

    # ------------------------------------------------------------------
    # Public interface (ProducerCurves)
    # ------------------------------------------------------------------

    def obtain_simulated_curve(
        self,
        working_oc_dir: Path,
        producer_name: str,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        reference_event_start_time: float,
    ) -> tuple[str, dict, SimulationResult, pd.DataFrame]:
        """
        Runs Dynawo to get the simulated curves for a given operating condition.

        Parameters
        ----------
        working_oc_dir : Path
            Temporal working path.
        producer_name : str
            Producer name (kept for interface consistency, not used directly).
        pcs_name : str
            PCS.Benchmark name.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        reference_event_start_time : float
            Instant of time when the event is triggered in the reference curves.

        Returns
        -------
        tuple[str, dict, SimulationResult, pd.DataFrame]
            (jobs_output_dir, event_params, simulation_result, curves)
        """
        self.__reset_solver()
        output_dir, jobs_output_dir = self.__prepare_oc_validation(
            working_oc_dir, pcs_name, bm_name, oc_name
        )
        event_params: dict = {}
        outcome = SimulateOutcome(
            succeeded=False, time_exceeds=False, has_curves=False, curves=pd.DataFrame()
        )
        error_message = None
        try:
            event_params = self._setup.complete_model(
                working_oc_dir, pcs_name, bm_name, oc_name, reference_event_start_time
            )
            # Sync curves_dict into bisection engine after model setup
            self._bisection.curves_dict = self._setup.curves_dict
            self._bisection.sim_time = self._sim_time

            pcs_bm_oc_name = get_cfg_oc_name(pcs_name, bm_name, oc_name)
            if config.get_boolean(pcs_bm_oc_name, "hiz_fault"):
                self._bisection.find_hiz_fault(
                    output_dir,
                    working_oc_dir,
                    jobs_output_dir,
                    event_params["start_time"],
                    event_params["duration_time"],
                    event_params["step_value"],
                    bm_name,
                    oc_name,
                    simulate_fn=self.__simulate,
                    reset_solver_fn=self.__reset_solver,
                )
            elif config.get_boolean(pcs_bm_oc_name, "bolted_fault"):
                self._bisection.apply_bolted_fault(
                    working_oc_dir,
                    event_params["start_time"],
                    event_params["duration_time"],
                )
            outcome = self.__simulate(
                output_dir, working_oc_dir, jobs_output_dir, bm_name, oc_name
            )
            self._voltage_dip = measure_voltage_dip(
                self._pcs_name,
                bm_name,
                oc_name,
                outcome.curves,
                event_params["start_time"],
                event_params["duration_time"],
            )
            dycov_logging.get_logger("ProducerCurves").debug(
                f"Simulation finished in {self._sim_time}s: "
                f"succeeded={outcome.succeeded} time_exceeds={outcome.time_exceeds} "
                f"has_curves={outcome.has_curves}",
            )
        except ValueError as e:
            error_message = _to_simulation_error(str(e))

        simulation_result = SimulationResult(
            outcome.succeeded, outcome.time_exceeds, outcome.has_curves, error_message
        )
        return jobs_output_dir, event_params, simulation_result, outcome.curves

    def get_time_cct(
        self,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        fault_duration: float,
        bm_name: str,
        oc_name: str,
    ) -> float:
        """
        Finds by bisection the Critical Clearing Time (CCT) for a fault.

        Parameters
        ----------
        working_oc_dir : Path
            Temporal working path (must contain completed model files).
        jobs_output_dir : Path
            Simulation output directory.
        fault_duration : float
            Initial fault duration in seconds.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.

        Returns
        -------
        float
            The critical clearing time (CCT).
        """
        self._bisection.sim_time = self._sim_time
        return self._bisection.find_cct(
            working_oc_dir, jobs_output_dir, fault_duration, bm_name, oc_name
        )

    def get_disconnection_model(self) -> DisconnectionModel:
        """
        Returns all equipment in the model that can be disconnected.
        """
        producer = self.get_producer()
        return DisconnectionModel(
            producer.aux_load,
            producer.auxload_xfmr,
            [xfmr.id for xfmr in producer.stepup_xfmrs],
            producer.intline,
        )

    def get_generators_imax(self) -> dict:
        """
        Returns the maximum current (Imax) for each generator, keyed by generator ID.
        """
        return {gen.id: gen.i_max for gen in self.get_producer().generators}

    def get_voltage_dip(self) -> float | None:
        """Returns the measured voltage dip, or None if not yet computed."""
        return self._voltage_dip

    def get_simulation_start(self) -> float:
        """Returns the simulation start time."""
        return self._simulation_start

    def get_simulation_duration(self) -> float:
        """Returns the simulation duration (stop - start)."""
        return self._simulation_stop - self._simulation_start

    def get_simulation_precision(self) -> float:
        """Returns the simulation precision."""
        return self._simulation_precision

    def get_solver(self) -> dict[str, SolverParam]:
        """
        Returns the current and default solver parameters, used for reporting.

        Returns
        -------
        dict[str, SolverParam]
            Parameter name mapped to SolverParam(actual, default).
        """
        P = SolverParam
        solver_parameters = {
            "lib": P(self._solver_lib, config.get_value("Dynawo", "solver_lib")),
            "parId": P(
                self._solver_id,
                config.get_value("Dynawo", "solver_lib").replace("dynawo_Solver", ""),
            ),
        }
        if self._solver_id == "IDA":
            solver_parameters.update(
                {
                    "order": P(
                        config.get_int("Dynawo", "ida_order", 2),
                        config.get_int("Dynawo", "ida_order", 2),
                    ),
                    "initStep": P(
                        config.get_float("Dynawo", "ida_initStep", 1e-9),
                        config.get_float("Dynawo", "ida_initStep", 1e-6),
                    ),
                    "minStep": P(
                        self._minimum_time_step,
                        config.get_float("Dynawo", "ida_minStep", 1e-6),
                    ),
                    "maxStep": P(
                        config.get_float("Dynawo", "ida_maxStep", 1.0),
                        config.get_float("Dynawo", "ida_maxStep", 1.0),
                    ),
                    "absAccuracy": P(
                        self._absAccuracy,
                        config.get_float("Dynawo", "ida_absAccuracy", 1e-6),
                    ),
                    "relAccuracy": P(
                        self._relAccuracy,
                        config.get_float("Dynawo", "ida_relAccuracy", 1e-4),
                    ),
                    "minimalAcceptableStep": P(
                        self._minimal_acceptable_step,
                        config.get_float("Dynawo", "ida_minimalAcceptableStep", 1e-6),
                    ),
                }
            )
        else:
            solver_parameters.update(
                {
                    "hMin": P(
                        self._minimum_time_step, config.get_float("Dynawo", "sim_hMin", 0.01)
                    ),
                    "hMax": P(
                        config.get_float("Dynawo", "sim_hMax", 0.01),
                        config.get_float("Dynawo", "sim_hMax", 0.01),
                    ),
                    "kReduceStep": P(
                        config.get_float("Dynawo", "sim_kReduceStep", 0.5),
                        config.get_float("Dynawo", "sim_kReduceStep", 0.5),
                    ),
                    "maxNewtonTry": P(
                        config.get_int("Dynawo", "sim_maxNewtonTry", 10),
                        config.get_int("Dynawo", "sim_maxNewtonTry", 10),
                    ),
                    "linearSolverName": P(
                        config.get_value("Dynawo", "sim_linearSolverName"),
                        config.get_value("Dynawo", "sim_linearSolverName"),
                    ),
                    "fnormtol": P(
                        self._absAccuracy, config.get_float("Dynawo", "sim_fnormtol", 0.01)
                    ),
                    "minimalAcceptableStep": P(
                        self._minimal_acceptable_step,
                        config.get_float("Dynawo", "sim_minimalAcceptableStep", 1e-6),
                    ),
                }
            )
        return solver_parameters

    # ------------------------------------------------------------------
    # ProducerCurves abstract method delegated to setup
    # ------------------------------------------------------------------

    def _obtain_gen_value(self, gen, value_definition: str) -> float:
        """
        Obtains a specific generator value based on the definition.

        Parameters
        ----------
        gen : GenParams
            Generator parameters object.
        value_definition : str
            The type of value to obtain (e.g., "P0", "Q0", "U0").

        Returns
        -------
        float
            The requested generator value.
        """
        value_map = {
            "P0": -gen.p0,
            "Q0": -gen.q0,
            "U0": gen.u0,
        }
        return value_map.get(value_definition, 0.0)
