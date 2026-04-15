#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#
import logging
import math
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from dycov.configuration.cfg import config
from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.curves.dynawo.runtime.dynawo_simulator import DynawoSimulator
from dycov.curves.voltage_dip import VoltDipResult, classify_voltage_dip
from dycov.files import manage_files, replace_placeholders
from dycov.logging.logging import dycov_logging
from dycov.model.producer import Producer
from dycov.validation import common

# Number of decimal places to round for bisection method calculations
BISECTION_ROUND = 10
BOLTED_FAULT_XPU = 1e-5
CCT_REL_TOL = 0.0001

_TSO_PAR = "TSOModel.par"
_CURVES_CSV = "curves/curves.csv"


class BisectionEngine:
    """
    Implements iterative bisection algorithms for fault impedance search (HIZ),
    bolted fault setup, and Critical Clearing Time (CCT) calculation.

    This class is stateless with respect to the Dynawo model — it receives all
    required context (producer, launcher, curves_dict, etc.) at construction time
    and does not modify any simulation input files directly except for fault
    parameters during bisection iterations.
    """

    def __init__(
        self,
        pcs_name: str,
        launcher_dwo: str,
        producer: Producer,
        s_nref: float,
        f_nom: float,
        sim_time: float,
        stable_time: float,
        curves_dict: dict,
    ):
        """
        Parameters
        ----------
        pcs_name : str
            Name of the PCS (Power Control System), used for logging context.
        launcher_dwo : str
            Path to the Dynawo launcher executable.
        producer : Producer
            The producer associated with the simulation.
        s_nref : float
            Reference apparent power (MVA).
        f_nom : float
            Nominal frequency (Hz).
        sim_time : float
            Current simulation elapsed time; updated after successful runs.
        stable_time : float
            Time horizon used to evaluate generator angle stability in CCT checks.
        curves_dict : dict
            Mapping of curve variable names used by the simulator.
        """
        self._pcs_name = pcs_name
        self._launcher_dwo = launcher_dwo
        self._producer = producer
        self._s_nref = s_nref
        self._f_nom = f_nom
        self.sim_time = sim_time
        self._stable_time = stable_time
        self._curves_dict = curves_dict

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    @contextmanager
    def _isolated_copy(self, src_dir: Path):
        """
        Yields a temporary directory pre-populated with a copy of src_dir.
        The directory is cleaned up automatically on exit.
        """
        with TemporaryDirectory(prefix="dynawo_") as temp_dir:
            work = (
                Path(temp_dir)
                / f"fault_time_execution_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            )
            manage_files.copy_directory(src_dir, work)
            yield work

    @staticmethod
    def _fault_rpu_from_xpu(xpu: float, r_factor: float) -> float:
        """rpu = xpu / r_factor (with zero-division guard)."""
        return (xpu / r_factor) if r_factor != 0.0 else 0.0

    def _debug(self, message: str) -> None:
        dycov_logging.get_logger("ProducerCurves").debug(message)

    def _warning(self, message: str) -> None:
        dycov_logging.get_logger("ProducerCurves").warning(message)

    def _error(self, message: str) -> None:
        dycov_logging.get_logger("ProducerCurves").error(message)

    def _modify_fault(
        self,
        working_oc_dir: Path,
        fault_start: float,
        fault_duration: float,
        fault_xpu: float,
        fault_rpu: float,
    ) -> None:
        """
        Writes fault parameters into TSOModel.par.
        No-op for zones other than zone 1.

        Parameters
        ----------
        working_oc_dir : Path
            Working directory containing TSOModel.par.
        fault_start : float
            Fault start time.
        fault_duration : float
            Fault duration.
        fault_xpu : float
            Fault reactance in per unit.
        fault_rpu : float
            Fault resistance in per unit.
        """
        if self._producer.get_zone() != 1:
            return
        replace_placeholders.fault_par_file(
            working_oc_dir,
            _TSO_PAR,
            fault_start + fault_duration,
            fault_xpu,
            fault_rpu,
        )

    def _is_bisection_complete(
        self,
        max_val: float,
        min_val: float,
        rel_tol: float,
        bm_name: str,
        oc_name: str,
    ) -> bool:
        """
        Returns True when the bisection interval is narrower than rel_tol.

        Parameters
        ----------
        max_val : float
            Upper bound of the bisection interval.
        min_val : float
            Lower bound of the bisection interval.
        rel_tol : float
            Relative tolerance threshold.
        bm_name : str
            Benchmark name (for debug logging).
        oc_name : str
            Operating Condition name (for debug logging).
        """
        complete = math.isclose(max_val, min_val, rel_tol=rel_tol)
        self._debug(
            f"Bisection method is complete: "
            f"{max_val=}, {min_val=}, {rel_tol=}, is complete: {complete}"
        )
        return complete

    # ------------------------------------------------------------------
    # HIZ fault bisection
    # ------------------------------------------------------------------

    def find_hiz_fault(
        self,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        fault_start: float,
        fault_duration: float,
        dip: float,
        bm_name: str,
        oc_name: str,
        simulate_fn,
        reset_solver_fn,
    ) -> None:
        """
        Determines and applies the fault impedance that achieves the required voltage dip
        using bisection. Modifies working_oc_dir/TSOModel.par in-place with the result.

        Parameters
        ----------
        output_dir : Path
            Output directory for simulation results.
        working_oc_dir : Path
            Working directory for the simulation.
        jobs_output_dir : Path
            Output directory specified in the job file.
        fault_start : float
            Fault start time.
        fault_duration : float
            Fault duration.
        dip : float
            Desired voltage dip magnitude.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        simulate_fn : callable
            Callable (output_dir, working_oc_dir, jobs_output_dir, bm_name, oc_name)
            → SimulateOutcome, provided by DynawoCurves to avoid circular dependency.
        reset_solver_fn : callable
            Callable () → None, provided by DynawoCurves to restore solver defaults
            after each bisection step.

        Raises
        ------
        ValueError
            If no fault value yields a successful simulation, or if the required
            voltage dip cannot be achieved within the bisection tolerance.
        """
        fault_r_factor = config.get_float("GridCode", "fault_r_factor", 10.0)
        max_val = config.get_float("Global", "maximum_hiz_fault", 10.0)
        min_val = config.get_float("Global", "minimum_hiz_fault", 1e-10)
        last_fault_xpu = min_val
        bisection_success = False
        hiz_rel_tol = config.get_float("Global", "hiz_fault_rel_tol", 1e-5)
        voltage_dip_classification = None

        while True:
            fault_xpu = round(((max_val + min_val) / 2), BISECTION_ROUND)
            with self._isolated_copy(working_oc_dir) as working_oc_dir_fault:
                fault_rpu = self._fault_rpu_from_xpu(fault_xpu, fault_r_factor)
                self._debug(f"Bisection between {max_val} and {min_val}")
                self._debug(f"Fault XPU in {fault_xpu}")
                self._modify_fault(
                    working_oc_dir_fault,
                    fault_start,
                    fault_duration,
                    fault_xpu,
                    fault_rpu,
                )
                fault_outcome = simulate_fn(
                    output_dir,
                    working_oc_dir_fault,
                    jobs_output_dir,
                    bm_name,
                    oc_name,
                    disable_retry_logs=True,
                )
                reset_solver_fn()
                if fault_outcome.succeeded:
                    bisection_success = True
                    last_fault_xpu = fault_xpu
                    voltage_dip_classification = classify_voltage_dip(
                        self._pcs_name,
                        bm_name,
                        oc_name,
                        fault_outcome.curves,
                        fault_start,
                        fault_duration,
                        abs(dip),
                    )
                if dycov_logging.get_logger("ProducerCurves").getEffectiveLevel() == logging.DEBUG:
                    target_dir_name = (
                        "bisection_last_success"
                        if fault_outcome.succeeded
                        else "bisection_last_failure"
                    )
                    manage_files.rename_path(
                        working_oc_dir_fault, working_oc_dir / target_dir_name
                    )
                if fault_outcome.succeeded:
                    if voltage_dip_classification == VoltDipResult.DIP_TOO_LARGE:
                        min_val = fault_xpu
                    elif voltage_dip_classification == VoltDipResult.DIP_TOO_SMALL:
                        max_val = fault_xpu
                    else:
                        break
                else:
                    self._debug("Simulation fails")
                    if voltage_dip_classification is not None:
                        if voltage_dip_classification == VoltDipResult.DIP_TOO_LARGE:
                            max_val = fault_xpu
                        elif voltage_dip_classification == VoltDipResult.DIP_TOO_SMALL:
                            min_val = fault_xpu
                    else:
                        max_val = fault_xpu
                if self._is_bisection_complete(max_val, min_val, hiz_rel_tol, bm_name, oc_name):
                    break

        if not bisection_success:
            self._error("The simulation fails with any value for the fault")
            raise ValueError("Fault simulation fails")
        if voltage_dip_classification == VoltDipResult.COLUMN_MISSING:
            self._error("The expected voltage curve is missing in the simulation output")
            raise ValueError("Voltage curve missing")
        elif voltage_dip_classification != VoltDipResult.DIP_CORRECT:
            self._error("The required dip was not achieved")
            raise ValueError("Fault dip unachievable")

        last_fault_rpu = self._fault_rpu_from_xpu(last_fault_xpu, fault_r_factor)
        self._modify_fault(
            working_oc_dir,
            fault_start,
            fault_duration,
            last_fault_xpu,
            last_fault_rpu,
        )

    # ------------------------------------------------------------------
    # Bolted fault
    # ------------------------------------------------------------------

    def apply_bolted_fault(
        self,
        working_oc_dir: Path,
        fault_start: float,
        fault_duration: float,
    ) -> None:
        """
        Applies a bolted fault (near-zero impedance) to TSOModel.par.

        Parameters
        ----------
        working_oc_dir : Path
            Working directory.
        fault_start : float
            Fault start time.
        fault_duration : float
            Fault duration.
        """
        fault_r_factor = config.get_float("GridCode", "fault_r_factor", 10.0)
        fault_xpu = BOLTED_FAULT_XPU
        fault_rpu = self._fault_rpu_from_xpu(fault_xpu, fault_r_factor)
        self._modify_fault(working_oc_dir, fault_start, fault_duration, fault_xpu, fault_rpu)

    # ------------------------------------------------------------------
    # CCT bisection
    # ------------------------------------------------------------------

    def _run_time_cct(
        self,
        working_oc_dir_attempt: Path,
        jobs_output_dir: Path,
        fault_duration: float,
        bm_name: str,
        oc_name: str,
    ) -> bool:
        """
        Runs a single Dynawo simulation for the given fault duration and returns
        whether all generators remain stable.

        Parameters
        ----------
        working_oc_dir_attempt : Path
            Temporary working directory for this attempt.
        jobs_output_dir : Path
            Output directory specified in the job file.
        fault_duration : float
            Fault duration to test.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.

        Returns
        -------
        bool
            True if all generators are stable after the fault, False otherwise.
        """
        replace_placeholders.fault_time(
            working_oc_dir_attempt / _TSO_PAR,
            fault_duration,
        )
        cct_result = DynawoSimulator.run_simple(
            self._pcs_name,
            bm_name,
            oc_name,
            self._launcher_dwo,
            self._curves_dict,
            working_oc_dir_attempt,
            jobs_output_dir,
            self._producer.generators,
            self._producer.s_nom,
            self._s_nref,
            self._f_nom,
            save_file=False,
            simulation_limit=self.sim_time + 10,
        )
        if not cct_result.succeeded:
            return False
        curves_temp = pd.read_csv(
            working_oc_dir_attempt / jobs_output_dir / _CURVES_CSV,
            sep=";",
        )
        return all(
            common.is_stable(
                list(curves_temp["time"]),
                list(
                    curves_temp[
                        dynawo_translator.get_curve_variable(gen.id, gen.lib, "InternalAngle")
                    ]
                ),
                self._stable_time,
            )[0]
            for gen in self._producer.generators
        )

    def _find_max_duration(
        self,
        working_oc_dir_attempt: Path,
        jobs_output_dir: Path,
        fault_duration: float,
        bm_name: str,
        oc_name: str,
    ) -> tuple[float, float]:
        """
        Expands the bisection upper bound until an unstable simulation is found.

        Parameters
        ----------
        working_oc_dir_attempt : Path
            Temporary working directory for this attempt.
        jobs_output_dir : Path
            Output directory specified in the job file.
        fault_duration : float
            Initial fault duration to start from.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.

        Returns
        -------
        tuple[float, float]
            (min_val, max_val): last stable and first unstable fault duration.
        """
        min_val = fault_duration
        max_val = fault_duration * 2
        self._debug(f"Max time CCT in {max_val}")
        while self._run_time_cct(
            working_oc_dir_attempt,
            jobs_output_dir,
            max_val,
            bm_name,
            oc_name,
        ):
            min_val = max_val
            max_val *= 1.5
            self._debug(f"Max time CCT in {max_val}")
        return min_val, max_val

    def find_cct(
        self,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        fault_duration: float,
        bm_name: str,
        oc_name: str,
    ) -> float:
        """
        Finds the Critical Clearing Time (CCT) using bisection.

        Parameters
        ----------
        working_oc_dir : Path
            Temporal working path (must already contain completed model files).
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
            The critical clearing time (CCT) for the fault.
        """
        working_oc_dir_fault_max = manage_files.clone_as_subdirectory(
            working_oc_dir, "fault_time_execution_max"
        )
        min_val, max_val = self._find_max_duration(
            working_oc_dir_fault_max,
            jobs_output_dir,
            fault_duration,
            bm_name,
            oc_name,
        )
        manage_files.remove_dir(working_oc_dir_fault_max)
        self._debug("Upper time to find clear time: " + str(max_val))
        self._debug("Lower time to find clear time: " + str(min_val))

        time = round(((max_val + min_val) / 2), BISECTION_ROUND)
        counter = 0
        while True:
            self._debug(f"Attempt {counter} to find clear time. Used fault time: {time}")
            with self._isolated_copy(working_oc_dir) as working_oc_dir_fault:
                self._debug(f"Run time CCT in {time}")
                steady_state = self._run_time_cct(
                    working_oc_dir_fault,
                    jobs_output_dir,
                    time,
                    bm_name,
                    oc_name,
                )
                if steady_state:
                    min_val = time
                else:
                    max_val = time
                if dycov_logging.get_logger("ProducerCurves").getEffectiveLevel() == logging.DEBUG:
                    target_dir_name = (
                        "bisection_last_success" if steady_state else "bisection_last_failure"
                    )
                    manage_files.rename_path(
                        working_oc_dir_fault, working_oc_dir / target_dir_name
                    )
            time = round(((max_val + min_val) / 2), BISECTION_ROUND)
            if self._is_bisection_complete(max_val, min_val, CCT_REL_TOL, bm_name, oc_name):
                break
            counter += 1
        return time
