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
import math
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from dycov.configuration.cfg import config
from dycov.core.global_variables import CASE_SEPARATOR
from dycov.core.parameters import Parameters
from dycov.curves.curves import ProducerCurves, get_cfg_oc_name
from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.curves.dynawo.io import crv
from dycov.curves.dynawo.io.dyd import DydFile
from dycov.curves.dynawo.io.jobs import JobsFile
from dycov.curves.dynawo.io.par import ParFile
from dycov.curves.dynawo.io.solvers import SolversFile
from dycov.curves.dynawo.io.table import TableFile
from dycov.curves.dynawo.runtime.dynawo_simulator import DynawoSimulator
from dycov.curves.dynawo.runtime.retry_strategy import RetrySettings, SolverRetryStrategy
from dycov.curves.dynawo.runtime.run_types import DynawoRunInputs, SolverParams
from dycov.electrical.generator_variables import generator_variables
from dycov.electrical.initialization_calcs import init_calcs
from dycov.electrical.pimodel_parameters import line_pimodel
from dycov.files import manage_files, model_parameters, omega_file, replace_placeholders, tso_file
from dycov.files.manage_files import ModelFiles, ProducerFiles
from dycov.logging.logging import dycov_logging
from dycov.logging.simulation_logger import SimulationLogger
from dycov.model.parameters import (
    Disconnection_Model,
    Gen_params,
    Load_init,
    Load_params,
    Pdr_params,
    Pimodel_params,
    Simulation_result,
)
from dycov.model.producer import Producer
from dycov.sanity_checks import parameter_checks
from dycov.validation import common

# Number of decimal places to round for bisection method calculations
BISECTION_ROUND = 10

# ----------------------------
# Private file/paths constants
# ----------------------------
_TSO_PAR = "TSOModel.par"
_TSO_DYD = "TSOModel.dyd"
_CURVES_CSV = "curves/curves.csv"


class DynawoCurves(ProducerCurves):
    """
    Manages the generation and processing of Dynawo simulation files and curves.
    This class handles the complete workflow for running Dynawo simulations,
    from preparing input files based on configuration to executing the simulation
    and processing its outputs. It supports various simulation types and fault
    scenarios, including high impedance and bolted faults, and calculates
    critical clearing times (CCT).
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
        Initializes the DynawoCurves object with simulation and producer parameters.
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
            Time used to check for stability in simulations (e.g., CCT).
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

        # Read default values from configuration
        self._f_nom = config.get_float("Dynawo", "f_nom", 50.0)
        self._s_nref = config.get_float("Dynawo", "s_nref", 100.0)
        self._simulation_start = config.get_float("Dynawo", "simulation_start", 0.0)
        self._simulation_stop = config.get_float("Dynawo", "simulation_stop", 100.0)
        self._simulation_precision = config.get_float("Dynawo", "simulation_precision", 1e-6)
        parameter_checks.check_simulation_duration(self.get_simulation_duration())

        # Simulation limit time, used in CCT calculations
        self._sim_time = config.get_float("Dynawo", "simulation_limit", 30.0)

        # Initialize the simulation logger
        logging.setLoggerClass(SimulationLogger)
        self._logger = logging.getLogger("ProducerCurves")

        # Internal variables for Dynawo files and simulation state
        self._dyd_file = None
        self._par_file = None
        self._crv_file = None
        self._jobs_file = None
        self._table_file = None
        self._solvers_file = None
        self._curves_dict = {}
        self._rte_loads = []  # To store RTE loads
        self._has_line = False  # Flag to indicate if a line is present

        # Solver parameters (initialized to defaults and reset as needed)
        self._solver_id = ""
        self._solver_lib = ""
        self._minimum_time_step = 0.0
        self._minimal_acceptable_step = 0.0
        self._absAccuracy = 0.0
        self._relAccuracy = 0.0  # Only for IDA solver
        self.__reset_solver()

    # ----------------------------
    # Small private helpers (DRY)
    # ----------------------------
    def __cfg_section(self, pcs_name: str, bm_name: str, oc_name: str, suffix: str = "") -> str:
        """
        Compose '<PCS>.<BM>.<OC>' optionally with a suffix like '.Model' or '.Event'.
        """
        base = get_cfg_oc_name(pcs_name, bm_name, oc_name)
        return base + suffix if suffix else base

    def __get_log_title(self, bm_name: str, oc_name: str) -> str:
        """
        Generates a standardized log title for debugging and warning messages.
        Parameters
        ----------
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        Returns
        -------
        str
            Formatted log title.
        """
        return f"{self._pcs_name}.{bm_name}.{oc_name}:"

    def __log_msg(self, level: str, bm_name: str, oc_name: str, message: str) -> None:
        """
        Centralized logger formatter (keeps one single format place).
        """
        getattr(dycov_logging.get_logger("ProducerCurves"), level)(
            f"{self.__get_log_title(bm_name, oc_name)} {message}"
        )

    def __debug(self, bm_name: str, oc_name: str, message: str) -> None:
        """
        Logs a debug message with PCS information.
        Parameters
        ----------
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        message : str
            The debug message.
        """
        self.__log_msg("debug", bm_name, oc_name, message)

    def __warning(self, bm_name: str, oc_name: str, message: str) -> None:
        """
        Logs a warning message with PCS information.
        Parameters
        ----------
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        message : str
            The warning message.
        """
        self.__log_msg("warning", bm_name, oc_name, message)

    def __error(self, bm_name: str, oc_name: str, message: str) -> None:
        """
        Logs an error message with PCS information.
        Parameters
        ----------
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        message : str
            The error message.
        """
        self.__log_msg("error", bm_name, oc_name, message)

    def __log(self, bm_name: str, oc_name: str, message: str) -> None:
        """
        Logs an informational message and also sends it to debug log.
        Parameters
        ----------
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        message : str
            The informational message.
        """
        self._logger.info(message)
        self.__debug(bm_name, oc_name, message)

    @staticmethod
    def __fault_rpu_from_xpu(xpu: float, r_factor: float) -> float:
        """rpu = xpu / r_factor (with 0 guard)."""
        return (xpu / r_factor) if r_factor != 0.0 else 0.0

    @contextmanager
    def __isolated_copy(self, src_dir: Path):
        """
        Create an isolated temp directory and copy src_dir contents there.
        Yields the temp working directory.
        """
        with TemporaryDirectory(prefix="dynawo_") as temp_dir:
            work = (
                Path(temp_dir)
                / f"fault_time_execution_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            )
            manage_files.copy_directory(src_dir, work)
            yield work

    def __reset_solver(self) -> None:
        """
        Resets the solver parameters to their default configured values.
        This is crucial for ensuring simulations start with a consistent solver state,
        especially after adjustments for failed simulations.
        """
        self._solver_lib = config.get_value("Dynawo", "solver_lib", "dynawo_SolverIDA")
        self._solver_id = self._solver_lib.replace("dynawo_Solver", "")
        if self._solver_id == "IDA":
            self._minimum_time_step = config.get_float("Dynawo", "ida_minStep", 1e-6)
            self._minimal_acceptable_step = config.get_float(
                "Dynawo", "ida_minimalAcceptableStep", 1e-6
            )
            self._absAccuracy = config.get_float("Dynawo", "ida_absAccuracy", 1e-6)
            self._relAccuracy = config.get_float("Dynawo", "ida_relAccuracy", 1e-4)
        else:  # Assuming "SIM" solver
            self._minimum_time_step = config.get_float("Dynawo", "sim_hMin", 1e-6)
            self._minimal_acceptable_step = config.get_float(
                "Dynawo", "sim_minimalAcceptableStep", 1e-6
            )
            self._absAccuracy = config.get_float("Dynawo", "sim_fnormtol", 1e-4)
            # Ensure _relAccuracy is not set for SIM solver, or set to None
            if hasattr(self, "_relAccuracy"):
                delattr(self, "_relAccuracy")
        parameter_checks.check_solver(self._solver_id, self._solver_lib)

    def __prepare_oc_validation(
        self,
        working_oc_dir: Path,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
    ) -> tuple[Path, Path]:
        """
        Prepares the working directory for an operating condition validation.
        This includes copying base case and producer files and setting up logging.
        Parameters
        ----------
        working_oc_dir : Path
            Temporal working path for the simulation.
        pcs_name : str
            PCS.Benchmark name.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        Returns
        -------
        tuple[Path, Path]
            A tuple containing:
            - output_dir: The final output directory for the simulation results.
            - jobs_output_dir: The output directory specified in the job file.
        """
        op_path = self._model_path / oc_name
        op_path_name = op_path.resolve().name

        # Create a specific folder by operational point
        output_dir = self._output_dir / self._pcs_name / bm_name / op_path_name

        # Copy base case and producers file
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

        # Get output dir read from job file
        jobs_output_dir = model_parameters.find_output_dir(working_oc_dir, "TSOModel")

        return output_dir, jobs_output_dir

    def _obtain_gen_value(self, gen: Gen_params, value_definition: str) -> float:
        """
        Obtains a specific generator value based on the definition.
        Parameters
        ----------
        gen : Gen_params
            Generator parameters object.
        value_definition : str
            The type of value to obtain (e.g., "P0", "Q0", "U0").
        Returns
        -------
        float
            The requested generator value.
        """
        # Optimized: Use a dictionary for direct lookup instead of if/elif chain
        value_map = {
            "P0": -gen.P0,
            "Q0": -gen.Q0,
            "U0": gen.U0,
        }
        return value_map.get(value_definition, 0.0)

    def __adjust_event_value(self, event_params: dict) -> None:
        """
        Adjusts the event 'pre_value' for AVRSetpointPu if voltage drop is enabled.
        Parameters
        ----------
        event_params : dict
            Dictionary containing event parameters.
        """
        if event_params["connect_to"] != "AVRSetpointPu":
            return
        # Optimized: Iterate through generators once to update pre_value
        for i, generator in enumerate(self.get_producer().generators):
            if generator.UseVoltageDroop:
                event_params["pre_value"][i] = (
                    generator.terminals[0].U0 + generator.VoltageDroop * generator.terminals[0].Q0
                )

    def __get_lines_for_initial_calcs(self, rte_lines: list) -> Pimodel_params:
        """
        Calculates equivalent line parameters for initial calculations.
        """
        if not rte_lines:
            return Pimodel_params(math.inf, 0, 0)  # No lines, infinite admittance

        Ytr_sum, Ysh1_sum, Ysh2_sum = 0, 0, 0
        for line in rte_lines:
            pimodel_line = line_pimodel(line)
            Ytr_sum += pimodel_line.Ytr
            Ysh1_sum += pimodel_line.Ysh1
            Ysh2_sum += pimodel_line.Ysh2
        return Pimodel_params(Ytr_sum, Ysh1_sum, Ysh2_sum)

    def __calculate_Xv(self, Udip, Zcc, Uinf):
        if Uinf == Udip:
            dycov_logging.get_logger("ProducerCurves").error(
                "Uinf cannot be equal to Udip to avoid division by zero."
            )
            raise ValueError("Uinf cannot be equal to Udip to avoid division by zero.")
        Zv = (Udip * Zcc) / (Uinf - Udip)
        ztanphi = config.get_float("GridCode", "Ztanphi", 1.0)
        Xv = (Zv * ztanphi) / math.sqrt(1 + ztanphi * ztanphi)
        return Xv

    def __calculate_Xv_values(
        self,
        event_params,
        line_xpu,
        line_rpu,
        rte_gen_U0,
        pcs_name,
        bm_name,
        oc_name,
        generator_variables,
    ):
        Zcc = math.sqrt(line_xpu * line_xpu + line_rpu * line_rpu)
        Uinf = rte_gen_U0
        model_section = self.__cfg_section(pcs_name, bm_name, oc_name, ".Model")
        generator_type = generator_variables.get_generator_type(self.get_producer().u_nom)
        u_list_options = [
            s
            for s in config.get_options(model_section)
            if s.startswith("u_") and s.endswith(generator_type)
        ]
        for option in u_list_options:
            name_Xv = f"Xv_{option[2:]}".replace(f"_{generator_type}", "")
            u_value_from_config = config.get_float(model_section, option, -999.0)
            event_params[name_Xv] = self.__calculate_Xv(u_value_from_config, Zcc, Uinf)

    def __complete_model(
        self,
        working_oc_dir: Path,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        reference_event_start_time: float,
    ) -> dict:
        """
        Completes the Dynawo model by calculating initial conditions, event parameters,
        and modifying input files accordingly.
        Parameters
        ----------
        working_oc_dir : Path
            Temporal working path for the simulation.
        pcs_name : str
            PCS name.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        reference_event_start_time : float
            Instant of time when the event is triggered in reference curves.
        Returns
        -------
        dict
            Event parameters after completion.
        """
        self.__log(
            bm_name,
            oc_name,
            f"Unom: {self.get_producer().u_nom}, "
            f"Generator type: {generator_variables.get_generator_type(self.get_producer().u_nom)}",
        )
        self.__log(
            bm_name,
            oc_name,
            f"Model definition for '{get_cfg_oc_name(pcs_name, bm_name, oc_name)}':",
        )

        # Read the load parameters in the TSO network, if exists
        self._rte_loads = model_parameters.get_pcs_load_params(
            working_oc_dir / _TSO_DYD,
            working_oc_dir / _TSO_PAR,
        )

        u_dim = self.get_generator_u_dim()
        pdr = self.__get_pdr(pcs_name, bm_name, oc_name, u_dim)

        # Calculates the initialization parameters and replace the placeholders by
        # its values in the input files of Dynawo.
        line_rpu, line_xpu = self.__get_line(pcs_name, bm_name, oc_name)

        rte_lines = []
        if self._has_line:
            # Read lines configuration from TSO network
            rte_lines = model_parameters.get_pcs_lines_params(
                working_oc_dir / _TSO_DYD,
                working_oc_dir / _TSO_PAR,
                line_rpu,
                line_xpu,
            )

        # Optimized: Refactored line parameter calculation into a helper method
        conn_line = self.__get_lines_for_initial_calcs(rte_lines)

        # Sort step-up transformers to match generator order if needed
        # Optimized: Using a dictionary for faster lookup, then building sorted list
        xfmr_map = {xfmr.id: xfmr for xfmr in self.get_producer().stepup_xfmrs}
        sorted_stepup_xfmrs = [
            xfmr_map[gen.terminals[0].connectedEquipment]
            for gen in self.get_producer().generators
            if gen.terminals[0].connectedEquipment in xfmr_map
        ]

        # Perform initial calculations for the system
        rte_gen = init_calcs(
            tuple(self.get_producer().generators),
            tuple(sorted_stepup_xfmrs),
            self.get_producer().aux_load,
            self.get_producer().auxload_xfmr,
            self.get_producer().ppm_xfmr,
            self.get_producer().intline,
            pdr,
            conn_line,
            self.__get_grid_load(pcs_name, bm_name, oc_name, u_dim),
        )

        self.__log(
            bm_name,
            oc_name,
            f"Event definition for '{get_cfg_oc_name(pcs_name, bm_name, oc_name)}':",
        )
        event_params = self.__get_event_parameters(
            pcs_name,
            bm_name,
            oc_name,
        )
        if (
            reference_event_start_time is not None
            and event_params["start_time"] != reference_event_start_time
        ):
            self.__warning(
                bm_name,
                oc_name,
                f"The simulation will use the 'sim_t_event_start' value present in the Reference "
                f"Curves ({reference_event_start_time}), instead of the value configured "
                f"({event_params['start_time']}).",
            )
            event_params["start_time"] = reference_event_start_time

        # Modify producer par to add generator init values
        section = get_cfg_oc_name(pcs_name, bm_name, oc_name)
        control_mode = config.get_value(section, "setpoint_change_test_type")
        force_voltage_droop = config.get_boolean(self._pcs_name, "force_voltage_droop", False)
        model_parameters.adjust_producer_init(
            working_oc_dir,
            self.get_producer().get_producer_par(),
            self.get_producer().generators,
            sorted_stepup_xfmrs,
            self.get_producer().aux_load,
            control_mode,
            force_voltage_droop,
        )
        self.__adjust_event_value(event_params)
        self.__calculate_Xv_values(
            event_params,
            line_xpu,
            line_rpu,
            rte_gen.U0,
            pcs_name,
            bm_name,
            oc_name,
            generator_variables,
        )

        # Initialize Dynawo file handlers
        pcs_bm_name = f"{pcs_name}{CASE_SEPARATOR}{bm_name}"
        self._jobs_file = JobsFile(self, pcs_bm_name, oc_name)
        self._par_file = ParFile(self, pcs_bm_name, oc_name)
        self._dyd_file = DydFile(self, pcs_bm_name, oc_name)
        self._table_file = TableFile(self, pcs_bm_name, oc_name)
        self._solvers_file = SolversFile(self, pcs_bm_name, oc_name)

        # Complete Dynawo input files
        self._jobs_file.complete_file(
            working_oc_dir, self._solver_id, self._solver_lib, event_params
        )
        self._par_file.complete_file(working_oc_dir, line_rpu, line_xpu, rte_gen, event_params)
        self._dyd_file.complete_file(working_oc_dir, event_params)
        self._table_file.complete_file(working_oc_dir, rte_gen, event_params)
        self._solvers_file.complete_file(working_oc_dir)

        # Read the generators parameters in the TSO network, if exists
        rte_generators = model_parameters.get_pcs_generators_params(
            working_oc_dir / _TSO_DYD,
            working_oc_dir / _TSO_PAR,
        )

        # Complete Omega and TSO files
        dycov_logging.get_logger("ProducerCurves").debug("Complete omega file")
        omega_file.complete_omega(
            working_oc_dir,
            "Omega.dyd",
            "Omega.par",
            self.get_producer().generators + rte_generators,
        )
        tso_file.complete_setpoint(
            working_oc_dir,
            _TSO_DYD,
            _TSO_PAR,
            self.get_producer().generators,
            config.get_value(pcs_bm_name, "TSO_model"),
            event_params,
        )

        # Collect all transformers for CRV file creation
        xmfrs = self.get_producer().stepup_xfmrs[:]
        if self.get_producer().auxload_xfmr:
            xmfrs.append(self.get_producer().auxload_xfmr)
        if self.get_producer().ppm_xfmr:
            xmfrs.append(self.get_producer().ppm_xfmr)

        # Create CRV (curves) file
        self._curves_dict = crv.create_curves_file(
            working_oc_dir,
            "TSOModel.crv",
            self.get_producer().get_connected_to_pdr(),
            xmfrs,
            self.get_producer().generators,
            self._rte_loads,
            self.get_producer().get_sim_type(),
            self.get_producer().get_zone(),
            control_mode,
        )
        return event_params

    def __get_event_parameters(
        self,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
    ) -> dict:
        """
        Retrieves event parameters from the configuration.
        Parameters
        ----------
        pcs_name : str
            PCS.Benchmark name.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        Returns
        -------
        dict
            A dictionary containing event parameters.
        """
        config_section = self.__cfg_section(pcs_name, bm_name, oc_name, ".Event")
        connect_event_to = config.get_value(config_section, "connect_event_to")
        self.__log(bm_name, oc_name, f"\t{connect_event_to=}")
        pre_value = 1.0  # Default pre_value
        # Active/Reactive power in PDR are in pu (base UNom, SnRef)
        # but Active/Reactive power setpoint are in pu (base SNom)
        setpoint_factor = self._s_nref / self.get_producer().s_nom
        if connect_event_to:
            if "ActivePowerSetpointPu" == connect_event_to:
                pre_value = [
                    -gen.terminals[0].P0 * setpoint_factor
                    for gen in self.get_producer().generators
                ]
            elif "ReactivePowerSetpointPu" == connect_event_to:
                pre_value = [
                    -gen.terminals[0].Q0 * setpoint_factor
                    for gen in self.get_producer().generators
                ]
            elif "AVRSetpointPu" == connect_event_to:
                pre_value = [gen.terminals[0].U0 for gen in self.get_producer().generators]
        start_time = config.get_float(config_section, "sim_t_event_start", 0.0)
        self.__log(bm_name, oc_name, f"\tsim_t_event_start={start_time}")
        # Optimized: Determine fault_duration more concisely
        fault_duration = 0.0
        if config.has_option(config_section, "fault_duration"):
            fault_duration = config.get_float(config_section, "fault_duration", 0.0)
        else:
            generator_type = generator_variables.get_generator_type(self.get_producer().u_nom)
            fault_duration = config.get_float(
                config_section, f"fault_duration_{generator_type}", 0.0
            )
        self.__log(bm_name, oc_name, f"\tfault_duration={fault_duration}")
        # Optimized: Determine step_value more concisely
        step_value = 0.0
        if config.has_option(config_section, "setpoint_step_value"):
            step_value = self.obtain_value(
                str(config.get_value(config_section, "setpoint_step_value"))
            )
        self.__log(bm_name, oc_name, f"\tsetpoint_step_value={step_value}")
        return {
            "start_time": start_time,
            "duration_time": fault_duration,
            "pre_value": pre_value,
            "step_value": step_value,
            "connect_to": connect_event_to,
        }

    def __get_line(
        self,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
    ) -> tuple[float, float]:
        """
        Calculates line resistance (rpu) and reactance (xpu) based on configuration.
        Parameters
        ----------
        pcs_name : str
            PCS.Benchmark name.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        Returns
        -------
        tuple[float, float]
            A tuple containing line_rpu and line_xpu.
        """
        config_section = self.__cfg_section(pcs_name, bm_name, oc_name, ".Model")
        line_rpu = 0.0
        line_xpu = 0.0
        self._has_line = False  # Reset flag
        # Optimized: Consolidated logic for line parameter calculation
        if config.has_option(config_section, "line_XPu"):
            self._has_line = True
            line_xpu_definition = config.get_value(config_section, "line_XPu")
            self.__log(bm_name, oc_name, f"\tline_XPu={line_xpu_definition}")
            xpu_multiplier = 1.0
            line_xtype = line_xpu_definition
            if "*" in line_xpu_definition:
                parts = line_xpu_definition.split("*")
                xpu_multiplier = float(parts[0])
                line_xtype = parts[1]
            try:
                line_xpu = float(line_xtype)
            except ValueError:
                line_xpu = xpu_multiplier * generator_variables.calculate_line_xpu(
                    line_xtype,
                    self.get_producer().p_max_pu * -1,
                    self.get_producer().s_nom,
                    self.get_producer().u_nom,
                    self._s_nref,
                )
            if self.get_producer().get_zone() == 3:  # Specific for Zone 3 (TSO)
                xpu_r_factor = config.get_float("GridCode", "XPu_r_factor", 0.0)
                line_rpu = line_xpu / xpu_r_factor if xpu_r_factor != 0.0 else 0.0
            else:
                line_rpu = 0.0
        elif config.has_option(config_section, "SCR"):
            self._has_line = True
            scr = config.get_float(config_section, "SCR", 0.0)
            self.__log(bm_name, oc_name, f"\tSCR={scr}")
            scr_r_factor = config.get_float("GridCode", "SCR_r_factor", 0.0)
            if scr != 0:
                line_xpu = 1.0 / (scr * self.get_producer().p_max_pu)
                line_rpu = line_xpu / scr_r_factor if scr_r_factor != 0.0 else 0.0
            # else: line_xpu and line_rpu remain 0, _has_line remains False
            # (as initialized or explicitly set)
        elif config.has_option(config_section, "Zcc"):
            self._has_line = True
            scc = generator_variables.get_scc(self.get_producer().u_nom)
            udim = generator_variables.get_generator_u_dim(self.get_producer().u_nom)
            uc_pu = udim / self.get_producer().u_nom
            scc_pu = scc / self._s_nref
            ztanphi = config.get_float("GridCode", "Ztanphi", 1.0)
            if ztanphi < 1.0:
                ztanphi = 1.0
            if scc != 0:
                zcc = uc_pu**2 / scc_pu
                self.__log(bm_name, oc_name, f"\tZcc={zcc}")
                line_xpu = ztanphi * zcc / math.sqrt(1 + ztanphi * ztanphi)
                line_rpu = line_xpu / ztanphi
            # else: line_xpu and line_rpu remain 0, _has_line remains False

        self.complete_unit_characteristics(line_xpu)
        return (
            line_rpu,
            line_xpu,
        )

    def __get_pdr(self, pcs_name: str, bm_name: str, oc_name: str, u_dim: float) -> Pdr_params:
        """
        Retrieves and calculates PDR (Point of Designate Response) parameters.
        Parameters
        ----------
        pcs_name : str
            PCS.Benchmark name.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        u_dim : float
            Dimensionless voltage.
        Returns
        -------
        Pdr_params
            PDR parameters (U, complex power, active power, reactive power).
        """
        config_section = self.__cfg_section(pcs_name, bm_name, oc_name, ".Model")
        # Read PDR params from configuration
        pdr_p_cfg = config.get_value(config_section, "pdr_P")
        self.__log(bm_name, oc_name, f"\tpdr_P={pdr_p_cfg}")
        pdr_q_cfg = config.get_value(config_section, "pdr_Q")
        self.__log(bm_name, oc_name, f"\tpdr_Q={pdr_q_cfg}")
        pdr_u_cfg = config.get_value(config_section, "pdr_U")
        self.__log(bm_name, oc_name, f"\tpdr_U={pdr_u_cfg}")

        # Modify the PMax value depending on the PCS initialization:
        # PmaxInjection (default) or PmaxConsumption
        self.get_producer().set_consumption("PmaxConsumption" in pdr_p_cfg)

        # For BESS producers, p_max_parameter is defined as PmaxInjection or PmaxConsumption
        # for other types of producers, p_max_parameter is always defined as Pmax
        p_max_parameter = (
            "PmaxConsumption"
            if "PmaxConsumption" in pdr_p_cfg
            else "PmaxInjection" if "PmaxInjection" in pdr_p_cfg else "Pmax"
        )

        # Sign convention: the initializations expects Pdr to be negative;
        # therefore we need to flip its sign.
        ini_pdr_p = model_parameters.extract_defined_value(
            pdr_p_cfg, p_max_parameter, self.get_producer().p_max_pu, -1
        )

        # Optimized: Simplified conditional logic for ini_pdr_q
        ini_pdr_q = 0.0
        if "Qmin" in pdr_q_cfg:
            ini_pdr_q = model_parameters.extract_defined_value(
                pdr_q_cfg, "Qmin", self.get_producer().q_min_pu, -1
            )
        elif "Qmax" in pdr_q_cfg:
            ini_pdr_q = model_parameters.extract_defined_value(
                pdr_q_cfg, "Qmax", self.get_producer().q_max_pu, -1
            )
        else:
            ini_pdr_q = model_parameters.extract_defined_value(
                pdr_q_cfg, p_max_parameter, self.get_producer().p_max_pu, -1
            )

        ini_pdr_u = (
            model_parameters.extract_defined_value(pdr_u_cfg, "Udim", u_dim)
            / self.get_producer().u_nom
        )
        return Pdr_params(ini_pdr_u, complex(ini_pdr_p, ini_pdr_q), ini_pdr_p, ini_pdr_q)

    def __get_grid_load(
        self,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        u_dim: float,
    ) -> Load_params:
        """
        Retrieves grid load parameters.
        Parameters
        ----------
        pcs_name : str
            PCS.Benchmark name.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        u_dim : float
            Dimensionless voltage.
        Returns
        -------
        Load_params
            Grid load parameters.
        """
        config_section = self.__cfg_section(pcs_name, bm_name, oc_name, ".Model")
        self._init_loads = self.__complete_loads(config_section, bm_name, oc_name, u_dim)
        return model_parameters.get_grid_load(self._init_loads)

    def __complete_loads(
        self, config_section: str, bm_name: str, oc_name: str, u_dim: float
    ) -> list:
        """
        Completes load parameters by reading from configuration or using defaults.
        Parameters
        ----------
        config_section : str
            Configuration section for the model.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        u_dim : float
            Dimensionless voltage.
        Returns
        -------
        list
            List of Load_init objects with completed load parameters.
        """

        # Optimized: Nested helper function for clarity and reduced repetition
        def _get_load_value(param_name: str, default_key: str, default_value: float) -> float:
            """Helper function to get a single load parameter value."""
            try:
                # Try to convert directly to float if it's a numeric string
                return float(param_name)
            except ValueError:
                # Otherwise, it's a config key, retrieve from config and extract value
                cfg_value = config.get_value(config_section, param_name)
                self.__log(bm_name, oc_name, f"\t{param_name}={cfg_value}")
                return model_parameters.extract_defined_value(
                    cfg_value, default_key, default_value
                )

        loads = []
        for load in self._rte_loads:
            p = _get_load_value(load.P, "pmax", self.get_producer().p_max_pu)
            q = _get_load_value(load.Q, "pmax", self.get_producer().p_max_pu)
            u = _get_load_value(load.U, "udim", u_dim) / self.get_producer().u_nom
            uphase = _get_load_value(
                load.UPhase, "NA", 1.0
            )  # 'NA' for no specific default extraction logic
            loads.append(Load_init(load.id, "", p, q, u, uphase))
        return loads

    def __modify_fault(
        self,
        working_oc_dir: Path,
        fault_start: float,
        fault_duration: float,
        fault_xpu: float,
        fault_rpu: float,
    ) -> None:
        """
        Modifies the TSOModel.par file to include fault parameters.
        Parameters
        ----------
        working_oc_dir : Path
            Working directory.
        fault_start : float
            Fault start time.
        fault_duration : float
            Fault duration.
        fault_xpu : float
            Fault reactance in per unit.
        fault_rpu : float
            Fault resistance in per unit.
        """
        if self.get_producer().get_zone() != 1:
            return
        replace_placeholders.fault_par_file(
            working_oc_dir,
            _TSO_PAR,
            fault_start + fault_duration,  # Fault end time
            fault_xpu,
            fault_rpu,
        )

    def __simulate(
        self,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        bm_name: str,
        oc_name: str,
    ) -> tuple[bool, bool, bool, pd.DataFrame]:
        """
        Runs the Dynawo simulation and checks for success, time exceedance, and
        curves availability.
        Parameters
        ----------
        output_dir : Path
            The final output directory for the simulation results.
        working_oc_dir : Path
            Working directory for the simulation.
        jobs_output_dir : Path
            Output directory specified in the job file.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        Returns
        -------
        tuple[bool, bool, bool, pd.DataFrame]
            A tuple containing:
            - success: True if simulation succeeded, False otherwise.
            - time_exceeds: True if simulation time exceeded limit.
            - has_dynawo_curves: True if Dynawo curves file was generated.
            - curves_calculated: DataFrame of calculated curves.
        """
        # Run Base Mode
        success, time_exceeds, log, curves_calculated = self.__execute_simulation(
            output_dir,
            working_oc_dir,
            jobs_output_dir,
            bm_name,
            oc_name,
        )
        if not success:
            self.__warning(bm_name, oc_name, log)
        else:
            self.__debug(bm_name, oc_name, "Simulation successful")
        # Check if there is a curves file
        has_dynawo_curves = (working_oc_dir / jobs_output_dir / _CURVES_CSV).exists() and success
        return success, time_exceeds, has_dynawo_curves, curves_calculated

    def __execute_simulation(
        self,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        bm_name: str,
        oc_name: str,
        max_sim_time: float = None,
    ) -> tuple[bool, bool, str, pd.DataFrame]:
        """
        Executes Dynawo simulation using a dedicated retry strategy.
        Returns (success, time_exceeds, log, curves_calculated).
        Parameters
        ----------
        output_dir : Path
            The final output directory for the simulation results.
        working_oc_dir : Path
            Working directory for the simulation.
        jobs_output_dir : Path
            Output directory specified in the job file.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        max_sim_time : float, optional
            Maximum allowed simulation time, by default None (uses config value).
        Returns
        -------
        tuple[bool, bool, str, pd.DataFrame]
            A tuple containing:
            - success: True if simulation succeeded, False otherwise.
            - time_exceeds: True if simulation time exceeded limit.
            - log: Log message.
            - curves_calculated: DataFrame of calculated curves.
        """
        if max_sim_time is None:
            max_sim_time = config.get_float("Dynawo", "simulation_limit", 30.0)
        strategy = SolverRetryStrategy(RetrySettings.from_config())
        run_inputs = DynawoRunInputs(
            pcs_name=self._pcs_name,
            launcher_dwo=self._launcher_dwo,
            curves_dict=self._curves_dict,
            generators=self.get_producer().generators,
            s_nom=self.get_producer().s_nom,
            s_nref=self._s_nref,
        )
        solver = SolverParams(
            solver_id=self._solver_id,
            solver_lib=self._solver_lib,
            minimum_time_step=self._minimum_time_step,
            minimal_acceptable_step=self._minimal_acceptable_step,
            absAccuracy=self._absAccuracy,
            relAccuracy=self._relAccuracy if hasattr(self, "_relAccuracy") else None,
        )
        success, time_exceeds, log, curves_df, sim_time = strategy.run(
            run=run_inputs,
            solver=solver,
            output_dir=output_dir,
            working_oc_dir=working_oc_dir,
            jobs_output_dir=jobs_output_dir,
            bm_name=bm_name,
            oc_name=oc_name,
            max_sim_time=max_sim_time,
        )
        if success:
            self._sim_time = sim_time  # persist for later routines (e.g., CCT)
        return success, time_exceeds, log, curves_df

    def __get_hiz_fault(
        self,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        fault_start: float,
        fault_duration: float,
        dip: float,
        bm_name: str,
        oc_name: str,
    ) -> None:
        """
        Determines the fault impedance for a high impedance fault using bisection.
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
            Desired voltage dip.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        Raises
        ------
        ValueError
            If the simulation fails for any fault value or if the required dip is unachievable.
        """
        fault_r_factor = config.get_float("GridCode", "fault_r_factor", 10.0)
        max_val = config.get_float("Global", "maximum_hiz_fault", 10.0)
        min_val = config.get_float("Global", "minimum_hiz_fault", 1e-10)
        last_fault_xpu = min_val
        bisection_success = False
        hiz_rel_tol = config.get_float("Global", "hiz_fault_rel_tol", 1e-5)
        voltage_dip_check_result = None  # Initialize to None
        # Optimized: Removed `incomplete_bisection` flag, using `while True` with `break`
        while True:
            fault_xpu = round(((max_val + min_val) / 2), BISECTION_ROUND)
            with self.__isolated_copy(working_oc_dir) as working_oc_dir_fault:
                fault_rpu = self.__fault_rpu_from_xpu(fault_xpu, fault_r_factor)
                self.__debug(bm_name, oc_name, f"Bisection between {max_val} and {min_val}")
                self.__debug(bm_name, oc_name, f"Fault XPU in {fault_xpu}")
                self.__modify_fault(
                    working_oc_dir_fault,
                    fault_start,
                    fault_duration,
                    fault_xpu,
                    fault_rpu=fault_rpu,
                )
                success, _, _, curves_calculated = self.__simulate(
                    output_dir, working_oc_dir_fault, jobs_output_dir, bm_name, oc_name
                )
                self.__reset_solver()  # Restore the solver to the default values
                if success:
                    bisection_success = True
                    last_fault_xpu = fault_xpu
                    voltage_dip_check_result = DynawoSimulator.check_voltage_dip(
                        self._pcs_name,
                        bm_name,
                        oc_name,
                        curves_calculated,
                        fault_start,
                        fault_duration,
                        abs(dip),
                    )
                if dycov_logging.get_logger("ProducerCurves").getEffectiveLevel() == logging.DEBUG:
                    target_dir_name = (
                        "bisection_last_success" if success else "bisection_last_failure"
                    )
                    manage_files.rename_path(
                        working_oc_dir_fault, working_oc_dir / target_dir_name
                    )
                if success:
                    if voltage_dip_check_result == 1:  # Required dip is greater than obtained
                        min_val = fault_xpu
                    elif voltage_dip_check_result == -1:  # Required dip is less than obtained
                        max_val = fault_xpu
                    else:  # voltage_dip_check_result == 0: Dip achieved
                        break  # Exit loop if dip is achieved
                else:
                    self.__debug(bm_name, oc_name, "Simulation fails")
                    # If the simulation fails, adjust search range based on previous outcome
                    # if available
                    if voltage_dip_check_result is not None:
                        if voltage_dip_check_result == 1:
                            max_val = fault_xpu
                        elif voltage_dip_check_result == -1:
                            min_val = fault_xpu
                    else:  # Fallback if voltage_dip_check_result is not yet set
                        max_val = fault_xpu  # Default to reducing fault if first simulation fails
                if self.__is_bisection_complete(max_val, min_val, hiz_rel_tol, bm_name, oc_name):
                    break  # Exit loop if bisection is complete
        if not bisection_success:
            self.__error(bm_name, oc_name, "The simulation fails with any value for the fault")
            raise ValueError("Fault simulation fails")
        # Check if the exact dip was achieved, if not, raise error
        if voltage_dip_check_result != 0:
            self.__error(bm_name, oc_name, "The required dip was not achieved")
            raise ValueError("Fault dip unachievable")
        # Recover the last successful fault values and apply to original working directory
        last_fault_rpu = self.__fault_rpu_from_xpu(last_fault_xpu, fault_r_factor)
        self.__modify_fault(
            working_oc_dir,
            fault_start,
            fault_duration,
            last_fault_xpu,
            last_fault_rpu,
        )

    def __get_bolted_fault(
        self,
        working_oc_dir: Path,
        fault_start: float,
        fault_duration: float,
    ) -> None:
        """
        Applies a bolted fault (very low impedance fault) to the model.
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
        fault_xpu = 1e-5  # Very low reactance for a bolted fault
        fault_rpu = self.__fault_rpu_from_xpu(fault_xpu, fault_r_factor)
        self.__modify_fault(
            working_oc_dir,
            fault_start,
            fault_duration,
            fault_xpu,
            fault_rpu,
        )

    def __get_max_duration(
        self,
        working_oc_dir_attempt: Path,
        jobs_output_dir: Path,
        fault_duration: float,
        bm_name: str,
        oc_name: str,
    ) -> tuple[float, float]:
        """
        Finds the maximum fault duration for stability before bisection for CCT.
        Parameters
        ----------
        working_oc_dir_attempt : Path
            Temporary working directory for this attempt.
        jobs_output_dir : Path
            Output directory specified in the job file.
        fault_duration : float
            Initial fault duration to start checking from.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        Returns
        -------
        tuple[float, float]
            A tuple containing:
            - min_val: The maximum stable duration found.
            - max_val: The minimum unstable duration found.
        """
        # For a given fault duration time, it is checked if the
        # simulation is stable, if it is, the time is doubled
        # until an unstable simulation is achieved.
        min_val = fault_duration
        max_val = fault_duration * 2
        self.__debug(bm_name, oc_name, f"Max time CCT in {max_val}")
        while self.__run_time_cct(
            working_oc_dir_attempt,
            jobs_output_dir,
            max_val,
            bm_name,
            oc_name,
        ):
            min_val = max_val
            max_val *= 1.5
            self.__debug(bm_name, oc_name, f"Max time CCT in {max_val}")
        return min_val, max_val

    def __run_time_cct(
        self,
        working_oc_dir_attempt: Path,
        jobs_output_dir: Path,
        fault_duration: float,
        bm_name: str,
        oc_name: str,
    ) -> bool:
        """
        Runs a Dynawo simulation for a given fault duration and checks for stability.
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
            True if the simulation is stable, False otherwise.
        """
        # Modify the fault time in the TSOModel.par file
        replace_placeholders.fault_time(
            working_oc_dir_attempt / _TSO_PAR,
            fault_duration,
        )
        # Run Dynawo simulation
        ret_val, _, _, _, _ = DynawoSimulator.run_simple(
            self._pcs_name,
            bm_name,
            oc_name,
            self._launcher_dwo,
            self._curves_dict,
            working_oc_dir_attempt,
            jobs_output_dir,
            self.get_producer().generators,
            self.get_producer().s_nom,
            self._s_nref,
            save_file=False,  # No need to save output file for CCT check
            simulation_limit=self._sim_time + 10,
        )
        # If the simulation fails, it's unstable
        if not ret_val:
            return False
        # Create the expected curves from the output
        curves_temp = pd.read_csv(
            working_oc_dir_attempt / jobs_output_dir / _CURVES_CSV,
            sep=";",
        )
        # Check the stability of each generator's internal angle
        # Optimized: Use all() with a generator expression for efficiency
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
            for gen in self.get_producer().generators
        )

    def __is_bisection_complete(
        self, max_val: float, min_val: float, rel_tol: float, bm_name: str, oc_name: str
    ) -> bool:
        """
        Check if the bisection method is complete based on a relative tolerance.
        Parameters
        ----------
        max_val : float
            Maximum value in the bisection method.
        min_val : float
            Minimum value in the bisection method.
        rel_tol : float
            Relative tolerance to consider the bisection method complete.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        Returns
        -------
        bool
            True if the bisection method is complete, False otherwise.
        """
        self.__debug(
            bm_name,
            oc_name,
            "Bisection method is complete: "
            f"{max_val=}, {min_val=}, {rel_tol=}, "
            f"is complete: {math.isclose(max_val, min_val, rel_tol=rel_tol)}",
        )
        return math.isclose(max_val, min_val, rel_tol=rel_tol)

    def get_solver(self) -> dict:
        """
        Gets the current and default solver parameters.
        Returns
        -------
        dict
            A dictionary containing current and default solver parameters.
        """
        solver_parameters = {
            "lib": (self._solver_lib, config.get_value("Dynawo", "solver_lib")),
            "parId": (
                self._solver_id,
                config.get_value("Dynawo", "solver_lib").replace("dynawo_Solver", ""),
            ),
        }
        # Optimized: Use a helper dictionary to define common keys and their default values
        common_solver_params = {
            "minimalAcceptableStep": (
                "_minimal_acceptable_step",
                "ida_minimalAcceptableStep",
                1e-6,
            ),
        }
        if self._solver_id == "IDA":
            ida_params = {
                "order": (
                    config.get_int("Dynawo", "ida_order", 2),
                    config.get_int("Dynawo", "ida_order", 2),
                ),
                "initStep": (
                    config.get_float("Dynawo", "ida_initStep", 1e-9),
                    config.get_float("Dynawo", "ida_initStep", 1e-6),
                ),
                "minStep": (
                    self._minimum_time_step,
                    config.get_float("Dynawo", "ida_minStep", 1e-6),
                ),
                "maxStep": (
                    config.get_float("Dynawo", "ida_maxStep", 1.0),
                    config.get_float("Dynawo", "ida_maxStep", 1.0),
                ),
                "absAccuracy": (
                    self._absAccuracy,
                    config.get_float("Dynawo", "ida_absAccuracy", 1e-6),
                ),
                "relAccuracy": (
                    self._relAccuracy,
                    config.get_float("Dynawo", "ida_relAccuracy", 1e-4),
                ),
            }
            solver_parameters.update(ida_params)
            # Add common param specifically for IDA
            solver_parameters["minimalAcceptableStep"] = (
                getattr(self, common_solver_params["minimalAcceptableStep"][0]),
                config.get_float(
                    "Dynawo",
                    common_solver_params["minimalAcceptableStep"][1],
                    common_solver_params["minimalAcceptableStep"][2],
                ),
            )
        else:  # SIM solver
            sim_params = {
                "hMin": (self._minimum_time_step, config.get_float("Dynawo", "sim_hMin", 0.01)),
                "hMax": (
                    config.get_float("Dynawo", "sim_hMax", 0.01),
                    config.get_float("Dynawo", "sim_hMax", 0.01),
                ),
                "kReduceStep": (
                    config.get_float("Dynawo", "sim_kReduceStep", 0.5),
                    config.get_float("Dynawo", "sim_kReduceStep", 0.5),
                ),
                "maxNewtonTry": (
                    config.get_int("Dynawo", "sim_maxNewtonTry", 10),
                    config.get_int("Dynawo", "sim_maxNewtonTry", 10),
                ),
                "linearSolverName": (
                    config.get_value("Dynawo", "sim_linearSolverName"),
                    config.get_value("Dynawo", "sim_linearSolverName"),
                ),
                "fnormtol": (self._absAccuracy, config.get_float("Dynawo", "sim_fnormtol", 0.01)),
            }
            solver_parameters.update(sim_params)
            # Add common param specifically for SIM
            solver_parameters["minimalAcceptableStep"] = (
                getattr(self, common_solver_params["minimalAcceptableStep"][0]),
                config.get_float(
                    "Dynawo",
                    common_solver_params["minimalAcceptableStep"][1],
                    common_solver_params["minimalAcceptableStep"][2],
                ),
            )
        return solver_parameters

    def get_time_cct(
        self,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        fault_duration: float,
        bm_name: str,
        oc_name: str,
    ) -> float:
        """
        Finds by bisection the critical clearing time (CCT) for a fault.
        Parameters
        ----------
        working_oc_dir : Path
            Temporal working path.
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
        # Define the initial range for bisection from the configured time
        # to a value where the simulation is not stable.
        working_oc_dir_fault_max = manage_files.clone_as_subdirectory(
            working_oc_dir, "fault_time_execution_max"
        )
        min_val, max_val = self.__get_max_duration(
            working_oc_dir_fault_max,
            jobs_output_dir,
            fault_duration,
            bm_name,
            oc_name,
        )
        manage_files.remove_dir(working_oc_dir_fault_max)  # Clean up temporary dir
        self.__debug(bm_name, oc_name, "Upper time to find clear time: " + str(max_val))
        self.__debug(bm_name, oc_name, "Lower time to find clear time: " + str(min_val))
        # Perform bisection to find the maximum duration the fault admits without losing stability
        time = round(((max_val + min_val) / 2), BISECTION_ROUND)
        counter = 0
        cct_rel_tol = 0.0001  # Defined directly for CCT bisection
        while True:
            self.__debug(
                bm_name,
                oc_name,
                f"Attempt {counter} to find clear time. Used fault time: {time}",
            )
            with self.__isolated_copy(working_oc_dir) as working_oc_dir_fault:
                self.__debug(bm_name, oc_name, f"Run time CCT in {time}")
                steady_state = self.__run_time_cct(
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
            if self.__is_bisection_complete(max_val, min_val, cct_rel_tol, bm_name, oc_name):
                break  # Exit loop if bisection is complete
            counter += 1
        return time

    def obtain_simulated_curve(
        self,
        working_oc_dir: Path,
        producer_name: str,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        reference_event_start_time: float,
    ) -> tuple[str, dict, Simulation_result, pd.DataFrame]:
        """
        Runs Dynawo to get the simulated curves for a given operating condition.
        Parameters
        ----------
        working_oc_dir : Path
            Temporal working path.
        producer_name : str
            Producer name (not directly used, but kept for interface consistency).
        pcs_name : str
            PCS.Benchmark name.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        reference_event_start_time : float
            Instant of time when the event is triggered in reference curves.
        Returns
        -------
        tuple[str, dict, Simulation_result, pd.DataFrame]
            A tuple containing:
            - str: Simulation output directory (jobs_output_dir).
            - dict: Event parameters.
            - Simulation_result: Information about the simulation result (success, errors).
            - pd.DataFrame: Simulation calculated curves.
        """
        error_message = None
        self.__reset_solver()
        # Prepare environment by copying base case and producer files
        output_dir, jobs_output_dir = self.__prepare_oc_validation(
            working_oc_dir,
            pcs_name,
            bm_name,
            oc_name,
        )
        success = False
        time_exceeds = False
        has_dynawo_curves = False
        event_params = dict()
        curves_calculated = pd.DataFrame()
        try:
            # Calculate initialization values and replace in input files
            event_params = self.__complete_model(
                working_oc_dir,
                pcs_name,
                bm_name,
                oc_name,
                reference_event_start_time,
            )
            pcs_bm_oc_name = self.__cfg_section(pcs_name, bm_name, oc_name)
            # Handle different fault types
            if config.get_boolean(pcs_bm_oc_name, "hiz_fault"):
                self.__get_hiz_fault(
                    output_dir,
                    working_oc_dir,
                    jobs_output_dir,
                    event_params["start_time"],
                    event_params["duration_time"],
                    event_params["step_value"],
                    bm_name,
                    oc_name,
                )
            elif config.get_boolean(pcs_bm_oc_name, "bolted_fault"):
                self.__get_bolted_fault(
                    working_oc_dir,
                    event_params["start_time"],
                    event_params["duration_time"],
                )
            # Run the simulation
            success, time_exceeds, has_dynawo_curves, curves_calculated = self.__simulate(
                output_dir,
                working_oc_dir,
                jobs_output_dir,
                bm_name,
                oc_name,
            )
            self.__debug(
                bm_name,
                oc_name,
                f"Simulation finished in {self._sim_time}s: "
                f"{success=} {time_exceeds=} {has_dynawo_curves=}",
            )
        except ValueError as e:
            error_message = str(e)
        simulation_result = Simulation_result(
            success, time_exceeds, has_dynawo_curves, error_message
        )
        return (
            jobs_output_dir,
            event_params,
            simulation_result,
            curves_calculated,
        )

    def get_disconnection_model(self) -> Disconnection_Model:
        """
        Get all equipment in the model that can be disconnected in the simulation.
        Returns
        -------
        Disconnection_Model
            Equipment that can be disconnected, including auxiliary load,
            auxiliary load transformer, step-up transformers, and internal line.
        """
        return Disconnection_Model(
            self.get_producer().aux_load,
            self.get_producer().auxload_xfmr,
            [stepup_xfmr.id for stepup_xfmr in self.get_producer().stepup_xfmrs],
            self.get_producer().intline,
        )

    def get_generators_imax(self) -> dict:
        """
        Get the maximum current (Imax) for each generator.
        Returns
        -------
        dict
            Maximum continuous current by generator, keyed by generator ID.
        """
        generators_imax = {}
        for generator in self.get_producer().generators:
            generators_imax[generator.id] = generator.IMax
        return generators_imax

    def get_simulation_start(self) -> float:
        """
        Get the simulation start time.
        Returns
        -------
        float
            Simulation start time.
        """
        return self._simulation_start

    def get_simulation_duration(self) -> float:
        """
        Get the simulation duration time.
        Returns
        -------
        float
            Simulation duration time.
        """
        return self._simulation_stop - self._simulation_start

    def get_simulation_precision(self) -> float:
        """
        Get the simulation precision.
        Returns
        -------
        float
            Simulation precision.
        """
        return self._simulation_precision
