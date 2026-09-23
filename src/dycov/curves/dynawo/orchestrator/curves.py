#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#
import configparser
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
from dycov.curves.naming import to_output_name
from dycov.curves.voltage_dip import measure_voltage_dip
from dycov.files import manage_files, simulation_files
from dycov.files.manage_files import ModelFiles, ProducerFiles
from dycov.files.simulation_files import SIMULATION_INPUTS_FILE
from dycov.logging import dycov_logging
from dycov.model.parameters import DisconnectionModel, SimulationOutcomeError, SimulationResult
from dycov.model.producer import Producer
from dycov.sanity_checks import parameter_checks

_CURVES_CSV = "curves/curves.csv"
_SIMULATION_SECTION = "Simulation"
_NOT_CONFIGURED = "not set"

SimulateOutcome = namedtuple("SimulateOutcome", "succeeded time_exceeds has_curves curves")
SolverParam = namedtuple("SolverParam", "actual default")


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
        thr_ss_tol: float,
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
        thr_ss_tol : float
            Tolerance defining the steady-state band around the final value.
        """
        super().__init__(producer)
        self._output_dir = parameters.get_output_dir()
        self._launcher_dwo = parameters.get_launcher_dwo()
        self._pcs_name = pcs_name
        self._model_path = model_path
        self._omega_path = omega_path
        self._pcs_path = pcs_path
        self._job_name = job_name
        self._thr_ss_tol = thr_ss_tol

        self._f_nom = config.get_float("Dynawo", "f_nom", 50.0)
        self._simulation_start = config.get_float("Dynawo", "simulation_start", 0.0)
        self._simulation_stop = config.get_float("Dynawo", "simulation_stop", 100.0)
        self._simulation_precision = config.get_float("Dynawo", "simulation_precision", 1e-6)
        parameter_checks.check_simulation_duration(self.get_simulation_duration())

        self._sim_time = config.get_float("Dynawo", "simulation_limit", 30.0)

        self.__reset_solver()

        self._voltage_dip = None

        # Collaborators (created once; ModelSetup state is refreshed per OC)
        self._setup = ModelSetup(self, pcs_name, self.get_snref(), self._f_nom)
        self._bisection = self._build_bisection_engine()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def __configured_solver(self) -> SolverParams:
        """Builds the solver parameters as the configuration declares them."""
        solver_lib = config.get_value("Dynawo", "solver_lib", "dynawo_SolverIDA")
        solver_id = solver_lib.replace("dynawo_Solver", "")
        if solver_id == "IDA":
            return SolverParams(
                solver_id=solver_id,
                solver_lib=solver_lib,
                minimum_time_step=config.get_float("Dynawo", "ida_minStep", 1e-6),
                minimal_acceptable_step=config.get_float(
                    "Dynawo", "ida_minimalAcceptableStep", 1e-6
                ),
                absAccuracy=config.get_float("Dynawo", "ida_absAccuracy", 1e-6),
                relAccuracy=config.get_float("Dynawo", "ida_relAccuracy", 1e-4),
            )
        return SolverParams(
            solver_id=solver_id,
            solver_lib=solver_lib,
            minimum_time_step=config.get_float("Dynawo", "sim_hMin", 1e-6),
            minimal_acceptable_step=config.get_float("Dynawo", "sim_minimalAcceptableStep", 1e-6),
            absAccuracy=config.get_float("Dynawo", "sim_fnormtol", 1e-4),
            relAccuracy=None,
        )

    def __reset_solver(self) -> None:
        """Resets all solver parameters to their configured defaults."""
        self._solver = self.__configured_solver()
        parameter_checks.check_solver(self._solver.solver_id, self._solver.solver_lib)

    def _build_bisection_engine(self) -> BisectionEngine:
        return BisectionEngine(
            pcs_name=self._pcs_name,
            launcher_dwo=self._launcher_dwo,
            producer=self.get_producer(),
            s_nref=self.get_snref(),
            f_nom=self._f_nom,
            sim_time=self._sim_time,
            thr_ss_tol=self._thr_ss_tol,
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
        jobs_output_dir = simulation_files.find_output_dir(working_oc_dir, "TSOModel")
        return output_dir, jobs_output_dir

    def __build_run_inputs(self) -> DynawoRunInputs:
        return DynawoRunInputs(
            pcs_name=self._pcs_name,
            launcher_dwo=self._launcher_dwo,
            curves_dict=self._setup.curves_dict,
            generators=self.get_producer().generators,
            s_nom=self.get_producer().s_nom,
            s_nref=self.get_snref(),
            f_nom=self._f_nom,
        )

    def __execute_simulation(
        self,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        bm_name: str,
        oc_name: str,
        max_sim_time: float | None = None,
        disable_retry_logs: bool = False,
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
        strategy = SolverRetryStrategy(
            RetrySettings.from_config(disable_retry_logs=disable_retry_logs)
        )
        result = strategy.run(
            run=self.__build_run_inputs(),
            solver=self._solver,
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
        disable_retry_logs: bool = False,
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
            output_dir,
            working_oc_dir,
            jobs_output_dir,
            bm_name,
            oc_name,
            disable_retry_logs=disable_retry_logs,
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

    def __initial_state(self) -> dict:
        """The operating point the simulation starts from, named as the curves of its zone."""
        pdr = self._setup.pdr
        if pdr is None:
            return {}

        zone = self._producer.get_zone()
        return {
            f"init_{to_output_name(f'BusPDR_BUS_{magnitude}', zone)}": value
            for magnitude, value in (
                ("Voltage", pdr.u),
                ("VoltagePhase", pdr.u_phase),
                ("ActivePower", pdr.p),
                ("ReactivePower", pdr.q),
            )
        }

    def __record_simulation_inputs(self, working_oc_dir: Path, event_params: dict) -> None:
        """Record next to the curves of a test what its simulation ran with.

        `dycov anonymize` rebuilds the [Curves-Metadata] section of the dictionaries it
        generates by reading this file: without it every generated curve set declares its
        event at t = 0 and no warning is raised.
        """
        curves_metadata = {
            "is_field_measurements": False,
            "sim_t_event_start": event_params.get("start_time"),
            "fault_duration": event_params.get("duration_time"),
            "frequency_sampling": config.get_float("GridCode", "cutoff", 15.0),
        }
        simulation_inputs = {
            "simulation_start": self._simulation_start,
            "simulation_stop": self._simulation_stop,
            "event_connected_to": event_params.get("connect_to"),
            "event_step_value": event_params.get("step_value"),
        } | {f"solver_{name}": value.actual for name, value in self.get_solver().items()}

        record = configparser.ConfigParser()
        record.optionxform = str
        record[_SIMULATION_SECTION] = {
            name: str(value)
            for name, value in (
                curves_metadata | self.__initial_state() | simulation_inputs
            ).items()
        }
        with open(working_oc_dir / SIMULATION_INPUTS_FILE, "w") as record_file:
            record.write(record_file)

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

        Raises
        ------
        ValueError
            If the model cannot be set up at all, a rejected configuration value
            being the usual cause. Only the outcomes reported as
            ``SimulationOutcomeError`` are turned into a failed
            ``SimulationResult``; anything else aborts the run.
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
        is_test_applicable = False
        try:
            is_test_applicable, event_params = self._setup.complete_model(
                working_oc_dir, pcs_name, bm_name, oc_name, reference_event_start_time
            )
            if not is_test_applicable:
                dycov_logging.get_logger("ProducerCurves").warning("Test not applicable.")
                return (
                    jobs_output_dir,
                    event_params,
                    SimulationResult(
                        appicable=is_test_applicable,
                        success=outcome.succeeded,
                        time_exceeds=outcome.time_exceeds,
                        has_simulated_curves=outcome.has_curves,
                        error=error_message,
                    ),
                    pd.DataFrame(),
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
                self._bisection.find_bolted_fault(
                    output_dir,
                    working_oc_dir,
                    jobs_output_dir,
                    event_params["start_time"],
                    event_params["duration_time"],
                    bm_name,
                    oc_name,
                    simulate_fn=self.__simulate,
                    reset_solver_fn=self.__reset_solver,
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
        except SimulationOutcomeError as e:
            error_message = e.error

        if event_params:
            self.__record_simulation_inputs(working_oc_dir, event_params)

        simulation_result = SimulationResult(
            is_test_applicable,
            outcome.succeeded,
            outcome.time_exceeds,
            outcome.has_curves,
            error_message,
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
        connection_xfmrs = list(producer.group_xfmrs)
        if producer.main_xfmr:
            connection_xfmrs.append(producer.main_xfmr)

        return DisconnectionModel(
            producer.aux_load,
            producer.auxload_xfmr,
            [xfmr.id for xfmr in connection_xfmrs],
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

    def get_solver_params(self) -> SolverParams:
        """
        Returns the solver parameters the next simulation runs with, as the retry strategy
        leaves them.

        Returns
        -------
        SolverParams
            Live solver parameters.
        """
        return self._solver

    def get_solver(self) -> dict[str, SolverParam]:
        """
        Returns the current and default solver parameters, used for reporting.

        Returns
        -------
        dict[str, SolverParam]
            Parameter name mapped to SolverParam(actual, default).
        """
        P = SolverParam
        solver = self._solver
        configured_lib = config.get_value("Dynawo", "solver_lib")
        solver_parameters = {
            "lib": P(solver.solver_lib, configured_lib),
            "parId": P(solver.solver_id, configured_lib.replace("dynawo_Solver", "")),
        }
        if solver.solver_id == "IDA":
            solver_parameters.update(
                {
                    "order": P(
                        config.get_int("Dynawo", "ida_order", 2),
                        config.get_int("Dynawo", "ida_order", 2),
                    ),
                    "initStep": P(
                        config.get_float("Dynawo", "ida_initStep", 1e-6),
                        config.get_float("Dynawo", "ida_initStep", 1e-6),
                    ),
                    "minStep": P(
                        solver.minimum_time_step,
                        config.get_float("Dynawo", "ida_minStep", 1e-6),
                    ),
                    "maxStep": P(
                        config.get_float("Dynawo", "ida_maxStep", 1.0),
                        config.get_float("Dynawo", "ida_maxStep", 1.0),
                    ),
                    "absAccuracy": P(
                        solver.absAccuracy,
                        config.get_float("Dynawo", "ida_absAccuracy", 1e-6),
                    ),
                    "relAccuracy": P(
                        solver.relAccuracy,
                        config.get_float("Dynawo", "ida_relAccuracy", 1e-4),
                    ),
                    "minimalAcceptableStep": P(
                        solver.minimal_acceptable_step,
                        config.get_float("Dynawo", "ida_minimalAcceptableStep", 1e-6),
                    ),
                }
            )
        else:
            solver_parameters.update(
                {
                    "hMin": P(
                        solver.minimum_time_step, config.get_float("Dynawo", "sim_hMin", 1e-6)
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
                        solver.absAccuracy, config.get_float("Dynawo", "sim_fnormtol", 1e-4)
                    ),
                    "minimalAcceptableStep": P(
                        solver.minimal_acceptable_step,
                        config.get_float("Dynawo", "sim_minimalAcceptableStep", 1e-6),
                    ),
                }
            )
        solver_parameters.update(
            {name: P(value, _NOT_CONFIGURED) for name, value in solver.added_parameters.items()}
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
