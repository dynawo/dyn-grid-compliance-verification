#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import cmath
import logging
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from dycov.configuration.cfg import config
from dycov.core.execution_parameters import Parameters
from dycov.curves.curves import ProducerCurves, get_cfg_oc_name
from dycov.dynawo import crv, dynawo
from dycov.dynawo.dyd import DydFile
from dycov.dynawo.jobs import JobsFile
from dycov.dynawo.par import ParFile
from dycov.dynawo.solvers import SolversFile
from dycov.dynawo.table import TableFile
from dycov.dynawo.translator import dynawo_translator, get_generator_family_level
from dycov.electrical.generator_variables import generator_variables
from dycov.electrical.initialization_calcs import init_calcs
from dycov.electrical.pimodel_parameters import line_pimodel
from dycov.files import (
    manage_files,
    model_parameters,
    omega_file,
    replace_placeholders,
)
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
)
from dycov.validation import common, sanity_checks

MINIMAL_HIZ_FAULT = 1e-10
BISECTION_THRESHOLD = 1e-10
BISECTION_ROUND = 10


class DynawoCurves(ProducerCurves):
    def __init__(
        self,
        parameters: Parameters,
        pcs_name: str,
        model_path: Path,
        omega_path: Path,
        pcs_path: Path,
        job_name: str,
        stable_time: float,
    ):
        super().__init__(parameters)
        self._output_dir = parameters.get_output_dir()
        self._launcher_dwo = parameters.get_launcher_dwo()
        self._pcs_name = pcs_name
        self._model_path = model_path
        self._omega_path = omega_path
        self._pcs_path = pcs_path
        self._job_name = job_name
        self._stable_time = stable_time

        # Read default values
        self._f_nom = config.get_float("Dynawo", "f_nom", 50.0)
        self._s_nref = config.get_float("Dynawo", "s_nref", 100.0)
        self._simulation_start = config.get_float("Dynawo", "simulation_start", 0.0)
        self._simulation_stop = config.get_float("Dynawo", "simulation_stop", 100.0)
        self._simulation_precision = config.get_float("Dynawo", "simulation_precision", 1e-6)
        sanity_checks.check_simulation_duration(self.get_simulation_duration())

        self._sim_time = config.get_float("Dynawo", "simulation_limit", 90.0)

        logging.setLoggerClass(SimulationLogger)
        self._logger = logging.getLogger("ProducerCurves")

    def __reset_solver(self):
        self._solver_lib = config.get_value("Dynawo", "solver_lib")
        if self._solver_lib is None:
            self._solver_lib = "dynawo_SolverIDA"
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
        sanity_checks.check_solver(self._solver_id, self._solver_lib)

    def __log(self, message: str):
        self._logger.info(message)
        dycov_logging.get_logger("ProducerCurves").debug(message)

    def __prepare_oc_validation(
        self,
        working_oc_dir: Path,
        pcs_bm_name: str,
        bm_name: str,
        oc_name: str,
    ):
        op_path = self._model_path / oc_name

        op_path_name = op_path.resolve().name

        # Create a specific folder by operational point
        if pcs_bm_name == op_path_name:
            output_dir = self._output_dir / self._pcs_name / bm_name
        else:
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

        # Create trees to modify files
        # Get output dir read from job file
        jobs_output_dir = model_parameters.find_output_dir(working_oc_dir, "TSOModel")

        file_log_level = config.get_value("Global", "file_log_level")
        file_formatter = config.get_value("Global", "file_formatter")
        file_max_bytes = config.get_int("Global", "file_log_max_bytes", 50 * 1024 * 1024)
        if dycov_logging.getEffectiveLevel() == logging.DEBUG:
            file_log_level = logging.DEBUG
        self._logger.init_handlers(
            file_log_level,
            file_formatter,
            file_max_bytes,
            working_oc_dir,
        )

        return (
            output_dir,
            jobs_output_dir,
        )

    def _obtain_gen_value(self, gen: Gen_params, value_definition: str) -> float:
        if value_definition == "P0":
            return -gen.P0
        elif value_definition == "Q0":
            return -gen.Q0
        elif value_definition == "U0":
            return gen.U0

        return 0.0

    def __complete_model(
        self,
        working_oc_dir: Path,
        pcs_bm_name: str,
        oc_name: str,
        reference_event_start_time: float,
    ) -> dict:

        self.__log(f"Model definition for '{get_cfg_oc_name(pcs_bm_name, oc_name)}':")

        # Read the load parameters in the TSO network, if exists
        self._rte_loads = model_parameters.get_pcs_load_params(
            working_oc_dir / "TSOModel.dyd",
            working_oc_dir / "TSOModel.par",
        )

        line_rpu, line_xpu = self.__get_line(pcs_bm_name, oc_name)

        u_dim = self.get_generator_u_dim()
        pdr = self.__get_pdr(pcs_bm_name, oc_name, u_dim)

        # Calculates the initialization parameters and replace the placeholders by
        #  its values in the input files of Dynawo.
        if self._has_line:
            # Read lines configuration from TSO network
            rte_lines = model_parameters.get_pcs_lines_params(
                working_oc_dir / "TSOModel.dyd",
                working_oc_dir / "TSOModel.par",
                line_rpu,
                line_xpu,
            )

            # In order to implement the fault in a line, the line with
            #  the fault is divided into two lines in series, but for calculation
            #  purposes it must be taken into account as a single line.
            if self.__is_specific_fault(pcs_bm_name):
                line = rte_lines[0]
                lines = [line, line, line, line]
            else:
                lines = rte_lines

            # for initialization calculations, lines in parallel are replaced by a
            #  single equivalent line.
            Ytr = 0
            Ysh1 = 0
            Ysh2 = 0
            for line in lines:
                pimodel_line = line_pimodel(line)
                Ytr += pimodel_line.Ytr
                Ysh1 += pimodel_line.Ysh1
                Ysh2 += pimodel_line.Ysh2
        else:
            rte_lines = list()
            Ytr = math.inf
            Ysh1 = 0
            Ysh2 = 0

        conn_line = Pimodel_params(Ytr, Ysh1, Ysh2)

        sorted_stepup_xfmrs = list()
        for generator in self.get_producer().generators:
            sorted_stepup_xfmrs += list(
                filter(
                    lambda xfmr: (xfmr.id == generator.connectedXmfr),
                    self.get_producer().stepup_xfmrs,
                )
            )

        # Initialization calcs
        rte_gen, gens, aux_load = init_calcs(
            tuple(self.get_producer().generators),
            tuple(sorted_stepup_xfmrs),
            self.get_producer().aux_load,
            self.get_producer().auxload_xfmr,
            self.get_producer().ppm_xfmr,
            self.get_producer().intline,
            pdr,
            conn_line,
            self.__get_grid_load(pcs_bm_name, oc_name, u_dim),
        )
        self._gens = gens

        self.__log(f"Event definition for '{get_cfg_oc_name(pcs_bm_name, oc_name)}':")
        event_params = self.__get_event_parameters(
            pcs_bm_name,
            oc_name,
        )
        if (
            reference_event_start_time is not None
            and event_params["start_time"] != reference_event_start_time
        ):
            dycov_logging.get_logger("ProducerCurves").warning(
                f"The simulation will use the 'sim_t_event_start' value present in the Reference "
                f"Curves ({reference_event_start_time}), instead of the value configured "
                f"({event_params['start_time']})."
            )
            event_params["start_time"] = reference_event_start_time

        # Modify producer par to add generator init values
        section = get_cfg_oc_name(pcs_bm_name, oc_name)
        control_mode = config.get_value(section, "setpoint_change_test_type")
        model_parameters.adjust_producer_init(
            working_oc_dir,
            self.get_producer().get_producer_par(),
            self.get_producer().generators,
            sorted_stepup_xfmrs,
            gens,
            aux_load,
            pdr,
            control_mode,
        )
        self.__adjust_event_value(event_params)

        jobs_file = JobsFile(self, pcs_bm_name, oc_name)
        jobs_file.complete_file(working_oc_dir, self._solver_id, self._solver_lib, event_params)

        par_file = ParFile(self, pcs_bm_name, oc_name)
        par_file.complete_file(working_oc_dir, line_rpu, line_xpu, rte_gen, event_params)

        dyd_file = DydFile(self, pcs_bm_name, oc_name)
        dyd_file.complete_file(working_oc_dir, event_params)

        table_file = TableFile(self, pcs_bm_name, oc_name)
        table_file.complete_file(working_oc_dir, rte_gen, event_params)

        solvers_file = SolversFile(self, pcs_bm_name, oc_name)
        solvers_file.complete_file(working_oc_dir)

        omega_file.complete_omega(
            working_oc_dir,
            "Omega.dyd",
            "Omega.par",
            self.get_producer().generators,
        )

        xmfrs = self.get_producer().stepup_xfmrs.copy()
        if self.get_producer().auxload_xfmr:
            xmfrs.append(self.get_producer().auxload_xfmr)
        if self.get_producer().ppm_xfmr:
            xmfrs.append(self.get_producer().ppm_xfmr)

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

    def __is_specific_fault(self, pcs_bm_name: str) -> bool:
        specific_faults = [
            "PCS_RTE-I4.ThreePhaseFault",
            "PCS_RTE-I5.ThreePhaseFault",
            "PCS_RTE-I16z3.ThreePhaseFault",
        ]
        return any(fault in pcs_bm_name for fault in specific_faults)

    def __adjust_event_value(self, event_params: dict) -> None:
        generator = self.get_producer().generators[0]
        if generator.UseVoltageDrop and event_params["connect_to"] == "AVRSetpointPu":
            event_params["pre_value"] = (
                self._gens[0].U0
                + generator.VoltageDrop * self._gens[0].Q0 * self._s_nref / generator.SNom
            )

    def __obtain_generator_values(
        self, generator_params, generator_values
    ) -> tuple[float, float, float, float]:
        family, level = get_generator_family_level(generator_params)
        if family == "WECC" and level == "Turbine" and "VoltageSource" not in generator_params.lib:
            equiv_int_line = generator_params.equiv_int_line
            u0Pu = cmath.rect(generator_values.U0, generator_values.UPhase0)
            s0Pu = complex(generator_values.P0, generator_values.Q0)
            i0Pu = np.conj(s0Pu / u0Pu)
            uInj0Pu = u0Pu - i0Pu * complex(equiv_int_line.R, equiv_int_line.X)
            iInj0Pu = -i0Pu * self._s_nref / generator_params.SNom
            sInj0Pu = uInj0Pu * np.conj(iInj0Pu)
            PInj0Pu = sInj0Pu.real
            QInj0Pu = sInj0Pu.imag
            UInj0Pu = abs(uInj0Pu)
            UInjPhase0 = np.angle(uInj0Pu)
            if "CurrentSource" not in generator_params.lib:
                PInj0Pu = -PInj0Pu
                QInj0Pu = -QInj0Pu
        else:
            PInj0Pu = generator_values.P0 * self._s_nref / generator_params.SNom
            QInj0Pu = generator_values.Q0 * self._s_nref / generator_params.SNom
            UInj0Pu = generator_values.U0
            UInjPhase0 = generator_values.UPhase0
        dycov_logging.get_logger("ProducerCurves").debug(
            f"Generator terminal values: {generator_values.P0=}, {generator_values.Q0=}, "
            f"{generator_values.U0=}"
        )
        dycov_logging.get_logger("ProducerCurves").debug(
            f"Initial values: {PInj0Pu=}, {QInj0Pu=}, {UInj0Pu=}, {UInjPhase0=}"
        )
        return PInj0Pu, QInj0Pu, UInj0Pu, UInjPhase0

    def __obtain_setpoint_value(self, connect_event_to: str) -> float:
        generator_params = self.get_producer().generators[0]
        generator_values = self._gens[0]
        PInj0Pu, QInj0Pu, UInj0Pu, _ = self.__obtain_generator_values(
            generator_params, generator_values
        )
        pre_value = 1.0
        if connect_event_to:
            if "ActivePowerSetpointPu" == connect_event_to:
                pre_value = -PInj0Pu
            elif "ReactivePowerSetpointPu" == connect_event_to:
                pre_value = -QInj0Pu
            elif "AVRSetpointPu" == connect_event_to:
                family, level = get_generator_family_level(generator_params)
                if family == "WECC" and level == "Turbine":
                    pre_value = -QInj0Pu
                else:
                    pre_value = UInj0Pu

        return pre_value

    def __get_event_parameters(
        self,
        pcs_bm_name: str,
        oc_name: str,
    ) -> dict:
        config_section = get_cfg_oc_name(pcs_bm_name, oc_name) + ".Event"

        connect_event_to = config.get_value(config_section, "connect_event_to")
        self.__log(f"\t{connect_event_to=}")
        pre_value = self.__obtain_setpoint_value(connect_event_to)
        start_time = config.get_float(config_section, "sim_t_event_start", 0.0)
        self.__log(f"\tsim_t_event_start={start_time}")
        # Read Fault duration if exists
        if config.has_key(config_section, "fault_duration"):
            fault_duration = config.get_float(config_section, "fault_duration", 0.0)
            self.__log(f"\t{fault_duration=}")
        else:
            generator_type = generator_variables.get_generator_type(self.get_producer().u_nom)
            fault_duration = config.get_float(
                config_section, f"fault_duration_{generator_type}", 0.0
            )
            self.__log(f"\tfault_duration_{generator_type}={fault_duration}")

        if config.has_key(config_section, "setpoint_step_value"):
            step_value = self.obtain_value(
                str(config.get_value(config_section, "setpoint_step_value"))
            )
            self.__log(f"\tsetpoint_step_value={step_value}")
        else:
            step_value = 0

        return {
            "start_time": start_time,
            "duration_time": fault_duration,
            "pre_value": pre_value,
            "step_value": step_value,
            "connect_to": connect_event_to,
        }

    def __get_line(
        self,
        pcs_bm_name: str,
        oc_name: str,
    ) -> tuple[float, float]:
        config_section = get_cfg_oc_name(pcs_bm_name, oc_name) + ".Model"

        # Read reactance definition
        # Calculate line X from DTR and Producer info
        xpu_multiplier = 1.0
        if config.has_key(config_section, "line_XPu"):
            self._has_line = True
            line_xpu_definition = config.get_value(config_section, "line_XPu")
            self.__log(f"\tline_XPu={line_xpu_definition}")
            if "*" in line_xpu_definition:
                xpu_multiplier = float(line_xpu_definition.split("*")[0])
                line_xtype = line_xpu_definition.split("*")[1]
            else:
                line_xtype = line_xpu_definition
            line_xpu = xpu_multiplier * generator_variables.calculate_line_xpu(
                line_xtype,
                self.get_producer().p_max_pu * -1,
                self.get_producer().s_nom,
                self.get_producer().u_nom,
                self._s_nref,
            )
            if self.get_producer().get_zone() == 3:
                xpu_r_factor = config.get_float("GridCode", "XPu_r_factor", 0.0)
                if xpu_r_factor == 0.0:
                    line_rpu = 0
                else:
                    line_rpu = line_xpu / xpu_r_factor
            else:
                line_rpu = 0
        elif config.has_key(config_section, "SCR"):
            self._has_line = True
            scr = config.get_float(config_section, "SCR", 0.0)
            self.__log(f"\tSCR={scr}")
            scr_r_factor = config.get_float("GridCode", "SCR_r_factor", 0.0)
            if scr != 0:
                line_xpu = 1.0 / (scr * self.get_producer().p_max_pu)
                if scr_r_factor == 0.0:
                    line_rpu = 0
                else:
                    line_rpu = line_xpu / scr_r_factor
            else:
                self._has_line = False
                line_xpu = 0
                line_rpu = 0
        else:
            self._has_line = False
            line_xpu = 0
            line_rpu = 0

        self.complete_unit_characteristics(line_xpu)

        return (
            line_rpu,
            line_xpu,
        )

    def __get_pdr(self, pcs_bm_name: str, oc_name: str, u_dim: float) -> Pdr_params:
        config_section = get_cfg_oc_name(pcs_bm_name, oc_name) + ".Model"

        # Read PDR params
        pdr_p = config.get_value(config_section, "pdr_P")
        self.__log(f"\tpdr_P={pdr_p}")
        pdr_q = config.get_value(config_section, "pdr_Q")
        self.__log(f"\tpdr_Q={pdr_q}")
        pdr_u = config.get_value(config_section, "pdr_U")
        self.__log(f"\tpdr_U={pdr_u}")

        # Sign convention:
        # the initializations expects Pdr to be negative;
        # therefore we need to flip its sign.
        ini_pdr_p = model_parameters.extract_defined_value(
            pdr_p, "Pmax", self.get_producer().p_max_pu, -1
        )

        if "Qmin" in pdr_q:
            ini_pdr_q = model_parameters.extract_defined_value(
                pdr_q, "Qmin", self.get_producer().q_min_pu, -1
            )
        elif "Qmax" in pdr_q:
            ini_pdr_q = model_parameters.extract_defined_value(
                pdr_q, "Qmax", self.get_producer().q_max_pu, -1
            )
        else:
            ini_pdr_q = model_parameters.extract_defined_value(
                pdr_q, "Pmax", self.get_producer().p_max_pu, -1
            )

        ini_pdr_u = (
            model_parameters.extract_defined_value(pdr_u, "Udim", u_dim)
            / self.get_producer().u_nom
        )
        return Pdr_params(ini_pdr_u, complex(ini_pdr_p, ini_pdr_q), ini_pdr_p, ini_pdr_q)

    def __get_grid_load(
        self,
        pcs_bm_name: str,
        oc_name: str,
        u_dim: float,
    ) -> Load_params:
        config_section = get_cfg_oc_name(pcs_bm_name, oc_name) + ".Model"
        self._init_loads = self.__complete_loads(config_section, u_dim)
        return model_parameters.get_grid_load(self._init_loads)

    def __complete_loads(self, config_section: str, u_dim: float) -> list:
        def __get_value(param, default_key, default_value):
            try:
                return float(param)
            except ValueError:
                cfg_value = config.get_value(config_section, param)
                self.__log(f"\t{param}={cfg_value}")
                return model_parameters.extract_defined_value(
                    cfg_value, default_key, default_value
                )

        loads = []
        for load in self._rte_loads:
            p = __get_value(load.P, "pmax", self.get_producer().p_max_pu)
            q = __get_value(load.Q, "pmax", self.get_producer().p_max_pu)
            u = __get_value(load.U, "udim", u_dim) / self.get_producer().u_nom
            uphase = __get_value(load.UPhase, "NA", 1.0)

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
        if self.get_producer().get_zone() != 1:
            return

        replace_placeholders.fault_par_file(
            working_oc_dir,
            "TSOModel.par",
            fault_start + fault_duration,
            fault_xpu,
            fault_rpu,
        )

    def __simulate(
        self,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
    ) -> tuple[bool, bool, pd.DataFrame]:

        # Run Base Mode
        (
            success,
            log,
            curves_calculated,
        ) = self.__execute_dynawo(
            output_dir,
            working_oc_dir,
            jobs_output_dir,
        )

        if not success:
            dycov_logging.get_logger("ProducerCurves").warning(log)
        else:
            dycov_logging.get_logger("ProducerCurves").debug("Simulation successful")

        # Check if there is a curves file
        has_dynawo_curves = False
        if (working_oc_dir / jobs_output_dir / "curves/curves.csv").exists() and success:
            has_dynawo_curves = True

        return success, has_dynawo_curves, curves_calculated

    def __execute_dynawo_core(
        self,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
    ) -> tuple[bool, str, pd.DataFrame]:
        # Run Dynawo
        success, log, has_error, curves_calculated, sim_time = dynawo.run_base_dynawo(
            self._launcher_dwo,
            "TSOModel",
            self._curves_dict,
            working_oc_dir,
            jobs_output_dir,
            self.get_producer().generators,
            self.get_producer().s_nom,
            self._s_nref,
        )
        if has_error:
            log_file = output_dir / jobs_output_dir / "logs/dynawo.log"
            log = f"Simulation Fails, logs in {str(log_file)}"
        if success:
            self._sim_time = sim_time

        return success, log, curves_calculated

    def __execute_dynawo(
        self,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
    ) -> tuple[bool, str, pd.DataFrame]:

        (
            success,
            log,
            curves_calculated,
        ) = self.__execute_dynawo_core(
            output_dir,
            working_oc_dir,
            jobs_output_dir,
        )

        if not success:
            dycov_logging.get_logger("ProducerCurves").warning(
                "Retry by modifying the minimum time step"
            )

            # Modifying the minimum time step
            self._minimum_time_step /= 10.0
            self._minimal_acceptable_step /= 10.0
            dycov_logging.get_logger("ProducerCurves").debug(
                f"New minimum time step: {self._minimum_time_step}"
            )
            if self._solver_id == "IDA":
                replace_placeholders.modify_par_file(
                    working_oc_dir,
                    "solvers.par",
                    "minStep",
                    self._minimum_time_step,
                )
            else:
                replace_placeholders.modify_par_file(
                    working_oc_dir,
                    "solvers.par",
                    "hMin",
                    self._minimum_time_step,
                )
            replace_placeholders.modify_par_file(
                working_oc_dir,
                "solvers.par",
                "minimalAcceptableStep",
                self._minimal_acceptable_step,
            )
            (
                success,
                log,
                curves_calculated,
            ) = self.__execute_dynawo_core(
                output_dir,
                working_oc_dir,
                jobs_output_dir,
            )
        else:
            dycov_logging.get_logger("ProducerCurves").debug("Simulation successful")

        if not success:
            dycov_logging.get_logger("ProducerCurves").warning(
                "Retry by modifying the required accuracy"
            )

            # Modifying the required accuracy
            self._relAccuracy *= 10.0
            self._absAccuracy *= 10.0
            dycov_logging.get_logger("ProducerCurves").debug(
                f"New required accuracy: {self._absAccuracy}"
            )
            if self._solver_id == "IDA":
                replace_placeholders.modify_par_file(
                    working_oc_dir,
                    "solvers.par",
                    "relAccuracy",
                    self._relAccuracy,
                )
                replace_placeholders.modify_par_file(
                    working_oc_dir,
                    "solvers.par",
                    "absAccuracy",
                    self._absAccuracy,
                )
            else:
                replace_placeholders.modify_par_file(
                    working_oc_dir,
                    "solvers.par",
                    "fnormtol",
                    self._absAccuracy,
                )

            (
                success,
                log,
                curves_calculated,
            ) = self.__execute_dynawo_core(
                output_dir,
                working_oc_dir,
                jobs_output_dir,
            )
        else:
            dycov_logging.get_logger("ProducerCurves").debug("Simulation successful")

        if not success:
            dycov_logging.get_logger("ProducerCurves").warning("Retry by changing the solver type")

            # Changing the solver type
            if self._solver_id == "SIM":
                self._solver_id = "IDA"
                self._solver_lib = "dynawo_SolverIDA"
                # Restore default values
                self._minimum_time_step = config.get_float("Dynawo", "ida_minStep", 1e-6)
                self._minimal_acceptable_step = config.get_float(
                    "Dynawo", "ida_minimalAcceptableStep", 1e-6
                )
                self._absAccuracy = config.get_float("Dynawo", "ida_absAccuracy", 1e-6)
                self._relAccuracy = config.get_float("Dynawo", "ida_relAccuracy", 1e-4)
            else:
                self._solver_id = "SIM"
                self._solver_lib = "dynawo_SolverSIM"
                # Restore default values
                self._minimum_time_step = config.get_float("Dynawo", "sim_hMin", 1e-6)
                self._minimal_acceptable_step = config.get_float(
                    "Dynawo", "sim_minimalAcceptableStep", 1e-6
                )
                self._absAccuracy = config.get_float("Dynawo", "sim_fnormtol", 1e-4)
            dycov_logging.get_logger("ProducerCurves").debug(f"Selected solver: {self._solver_id}")
            replace_placeholders.modify_jobs_file(
                working_oc_dir,
                "TSOModel.jobs",
                self._solver_id,
                self._solver_lib,
            )
            (
                success,
                log,
                curves_calculated,
            ) = self.__execute_dynawo_core(
                output_dir,
                working_oc_dir,
                jobs_output_dir,
            )
        else:
            dycov_logging.get_logger("ProducerCurves").debug("Simulation successful")

        return success, log, curves_calculated

    def __get_hiz_fault(
        self,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        fault_start: float,
        fault_duration: float,
        dip: float,
    ):
        fault_r_factor = config.get_float("GridCode", "fault_r_factor", 10.0)

        max_val = 10.0
        min_val = MINIMAL_HIZ_FAULT
        incomplete_bisection = True
        last_fault_xpu = MINIMAL_HIZ_FAULT
        working_oc_dirs_to_remove = []
        bisection_success = False
        while incomplete_bisection:
            fault_xpu = round(((max_val + min_val) / 2), BISECTION_ROUND)

            now = datetime.now()
            working_oc_dir_fault = manage_files.clone_as_subdirectory(
                working_oc_dir, "fault_time_execution_" + now.strftime("%Y%m%d%H%M%S%f")
            )

            if fault_r_factor == 0.0:
                fault_rpu = 0
            else:
                fault_rpu = fault_xpu / fault_r_factor
            dycov_logging.get_logger("ProducerCurves").debug(
                f"Bisection between {max_val} and {min_val}"
            )
            dycov_logging.get_logger("ProducerCurves").debug(f"Fault XPU in {fault_xpu}")
            self.__modify_fault(
                working_oc_dir_fault,
                fault_start,
                fault_duration,
                fault_xpu,
                fault_rpu=fault_rpu,
            )

            (
                success,
                _,
                curves_calculated,
            ) = self.__execute_dynawo(output_dir, working_oc_dir_fault, jobs_output_dir)

            # Restore the solver to the default values
            # It is necessary to restore the parameters because only
            # the current iteration has the possible changes made, the
            # original file still has the starting parameters.Additionally,
            # to copy the parameters back to the original file, you need
            # to modify the backup mode so that it can take into account
            # changes already applied in previous iterations.
            self.__reset_solver()

            # returned values:
            #  *  1 if the required dip is greater than that obtained
            #  * -1 if the required dip is less than that obtained
            #  *  0 otherwise
            if success:
                bisection_success = True
                last_fault_xpu = fault_xpu
                voltage_dip = dynawo.check_voltage_dip(
                    curves_calculated,
                    fault_start,
                    fault_duration,
                    abs(dip),
                )

                if dycov_logging.getEffectiveLevel() != logging.DEBUG:
                    working_oc_dirs_to_remove.append(working_oc_dir_fault)
                else:
                    if success:
                        manage_files.rename_dir(
                            working_oc_dir_fault, working_oc_dir / "bisection_last_success"
                        )
                    else:
                        manage_files.rename_dir(
                            working_oc_dir_fault, working_oc_dir / "bisection_last_failure"
                        )

                if voltage_dip == 1:
                    min_val = fault_xpu
                elif voltage_dip == -1:
                    max_val = fault_xpu
                else:
                    incomplete_bisection = False
            else:
                dycov_logging.get_logger("ProducerCurves").debug("Simulation fails")
                # If the simulation fails after decreasing the fault value,
                # it is necessary to increase it.
                # If the simulation fails after increasing the fault value,
                # it is necessary to decrease it
                dycov_logging.get_logger("ProducerCurves").debug(
                    f"Last fault XPU in {last_fault_xpu} actual {fault_xpu}"
                )
                try:
                    if voltage_dip == 1:
                        max_val = fault_xpu
                    elif voltage_dip == -1:
                        min_val = fault_xpu
                except UnboundLocalError:
                    max_val = fault_xpu

            if self.__is_bisection_complete(max_val, min_val, BISECTION_THRESHOLD):
                incomplete_bisection = False

        # Remove all bisection directories
        for dir_to_remove in working_oc_dirs_to_remove:
            manage_files.remove_dir(dir_to_remove)

        if not bisection_success:
            dycov_logging.get_logger("ProducerCurves").error(
                "The simulation fails with any value for the fault"
            )
            raise ValueError("Fault simulation fails")

        try:
            achive_dip = voltage_dip == 0
        except UnboundLocalError:
            achive_dip = False

        if not achive_dip:
            dycov_logging.get_logger("ProducerCurves").error("The required dip was not achieved")
            raise ValueError("Fault dip unachievable")

        # Recover the last successful fault values
        if fault_r_factor == 0.0:
            last_fault_rpu = 0
        else:
            last_fault_rpu = last_fault_xpu / fault_r_factor

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
    ):
        fault_rpu = 0.0173
        fault_xpu = 0.0

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
    ) -> tuple[float, float]:
        # For a given fault duration time, it is checked if the
        #  simulation is stable, if it is, the time is doubled
        #  until an unstable simulation is achieved.
        min_val = fault_duration
        max_val = fault_duration * 2

        dycov_logging.get_logger("ProducerCurves").debug(f"Max time CCT in {max_val}")
        while self.__run_time_cct(
            working_oc_dir_attempt,
            jobs_output_dir,
            max_val,
        ):
            min_val = max_val
            max_val *= 1.5
            dycov_logging.get_logger("ProducerCurves").debug(f"Max time CCT in {max_val}")

        return min_val, max_val

    def __run_time_cct(
        self,
        working_oc_dir_attempt: Path,
        jobs_output_dir: Path,
        fault_duration: float,
    ) -> bool:
        replace_placeholders.fault_time(
            working_oc_dir_attempt / ("TSOModel.par"),
            fault_duration,
        )

        # Run Dynawo
        ret_val, _, _, _, _ = dynawo.run_base_dynawo(
            self._launcher_dwo,
            "TSOModel",
            self._curves_dict,
            working_oc_dir_attempt,
            jobs_output_dir,
            self.get_producer().generators,
            self.get_producer().s_nom,
            self._s_nref,
            save_file=False,
            simulation_limit=self._sim_time + 10,
        )

        # If the simulation fails returns
        if not ret_val:
            return False

        # Create the expected curves
        curves_temp = pd.read_csv(
            working_oc_dir_attempt / jobs_output_dir / "curves/curves.csv",
            sep=";",
        )

        # Check the stability
        steady_state = True
        for generator in self.get_producer().generators:
            steady_key = dynawo_translator.get_curve_variable(
                generator.id, generator.lib, "InternalAngle"
            )

            gen_steady_state, _ = common.is_stable(
                list(curves_temp["time"]),
                list(curves_temp[steady_key]),
                self._stable_time,
            )
            steady_state &= gen_steady_state

        return steady_state

    def __is_bisection_complete(self, max_val: float, min_val: float, threshold: float) -> bool:
        """Check if the bisection method is complete.

        Parameters
        ----------
        max_val: float
            Maximum value in the bisection method.
        min_val: float
            Minimum value in the bisection method.
        threshold: float
            Threshold to consider the bisection method as complete.

        Returns
        -------
        bool
            True if the bisection method is complete, False otherwise.
        """
        dycov_logging.get_logger("ProducerCurves").debug(
            "Bisection method is complete: "
            f"{round(max_val - min_val, BISECTION_ROUND)} <= {threshold}"
        )
        return round(max_val - min_val, BISECTION_ROUND) <= threshold

    def get_solver(self) -> dict:
        solver_parameters = {
            "lib": (self._solver_lib, config.get_value("Dynawo", "solver_lib")),
            "parId": (
                self._solver_id,
                config.get_value("Dynawo", "solver_lib").replace("dynawo_Solver", ""),
            ),
        }
        if self._solver_id == "IDA":
            solver_parameters["order"] = (
                config.get_int("Dynawo", "ida_order", 2),
                config.get_int("Dynawo", "ida_order", 2),
            )
            solver_parameters["initStep"] = (
                config.get_float("Dynawo", "ida_initStep", 1e-9),
                config.get_float("Dynawo", "ida_initStep", 1e-6),
            )
            solver_parameters["minStep"] = (
                self._minimum_time_step,
                config.get_float("Dynawo", "ida_minStep", 1e-6),
            )
            solver_parameters["maxStep"] = (
                config.get_float("Dynawo", "ida_maxStep", 1.0),
                config.get_float("Dynawo", "ida_maxStep", 1.0),
            )
            solver_parameters["absAccuracy"] = (
                self._absAccuracy,
                config.get_float("Dynawo", "ida_absAccuracy", 1e-6),
            )
            solver_parameters["relAccuracy"] = (
                self._relAccuracy,
                config.get_float("Dynawo", "ida_relAccuracy", 1e-4),
            )
            solver_parameters["minimalAcceptableStep"] = (
                self._minimal_acceptable_step,
                config.get_float("Dynawo", "ida_minimalAcceptableStep", 1e-6),
            )
        else:
            solver_parameters["hMin"] = (
                self._minimum_time_step,
                config.get_float("Dynawo", "sim_hMin", 0.01),
            )
            solver_parameters["hMax"] = (
                config.get_float("Dynawo", "sim_hMax", 0.01),
                config.get_float("Dynawo", "sim_hMax", 0.01),
            )
            solver_parameters["kReduceStep"] = (
                config.get_float("Dynawo", "sim_kReduceStep", 0.5),
                config.get_float("Dynawo", "sim_kReduceStep", 0.5),
            )
            solver_parameters["maxNewtonTry"] = (
                config.get_int("Dynawo", "sim_maxNewtonTry", 10),
                config.get_int("Dynawo", "sim_maxNewtonTry", 10),
            )
            solver_parameters["linearSolverName"] = (
                config.get_value("Dynawo", "sim_linearSolverName"),
                config.get_value("Dynawo", "sim_linearSolverName"),
            )
            solver_parameters["fnormtol"] = (
                self._absAccuracy,
                config.get_float("Dynawo", "sim_fnormtol", 0.01),
            )
            solver_parameters["minimalAcceptableStep"] = (
                self._minimal_acceptable_step,
                config.get_float("Dynawo", "sim_minimalAcceptableStep", 1e-6),
            )

        return solver_parameters

    def get_time_cct(
        self,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        fault_duration: float,
    ) -> float:
        """Find by bisection the critical clearing time (CCT) for a fault.

        Parameters
        ----------
        working_oc_dir: Path
            Temporal working path
        jobs_output_dir: Path
            Simulation output dir
        fault_duration: float
            Fault duration in seconds

        Returns
        -------
        float
            The critical clearing time (CCT) for the fault.
        """

        # The range to work is defined from the configured time to the
        #  fault duration to a value where the simulation is not stable.
        working_oc_dir_fault = manage_files.clone_as_subdirectory(
            working_oc_dir, "fault_time_execution_max"
        )
        min_val, max_val = self.__get_max_duration(
            working_oc_dir_fault,
            jobs_output_dir,
            fault_duration,
        )
        manage_files.remove_dir(working_oc_dir_fault)

        dycov_logging.get_logger("Operating Condition").debug(
            "Upper time to find clear time: " + str(max_val)
        )
        dycov_logging.get_logger("Operating Condition").debug(
            "Lower time to find clear time: " + str(min_val)
        )

        # The maximum duration that the fault admits without losing
        #  stability is sought by bisection
        time = round(((max_val + min_val) / 2), BISECTION_ROUND)
        counter = 0
        find = False
        working_oc_dirs_to_remove = []
        while not find:
            dycov_logging.get_logger("Operating Condition").debug(
                "Attempt " + str(counter) + " to find clear time. Used fault time: " + str(time)
            )

            now = datetime.now()
            working_oc_dir_fault = manage_files.clone_as_subdirectory(
                working_oc_dir, "fault_time_execution_" + now.strftime("%Y%m%d%H%M%S%f")
            )
            dycov_logging.get_logger("ProducerCurves").debug(f"Run time CCT in {time}")
            steady_state = self.__run_time_cct(
                working_oc_dir_fault,
                jobs_output_dir,
                time,
            )

            if steady_state:
                min_val = time
            else:
                max_val = time

            if dycov_logging.getEffectiveLevel() != logging.DEBUG:
                working_oc_dirs_to_remove.append(working_oc_dir_fault)
            else:
                if steady_state:
                    manage_files.rename_dir(
                        working_oc_dir_fault, working_oc_dir / "bisection_last_success"
                    )
                else:
                    manage_files.rename_dir(
                        working_oc_dir_fault, working_oc_dir / "bisection_last_failure"
                    )

            time = round(((max_val + min_val) / 2), BISECTION_ROUND)

            if self.__is_bisection_complete(max_val, min_val, 0.0001):
                find = True

            counter += 1

        # Remove all bisection directories
        for dir_to_remove in working_oc_dirs_to_remove:
            manage_files.remove_dir(dir_to_remove)

        return time

    def obtain_simulated_curve(
        self,
        working_oc_dir: Path,
        pcs_bm_name: str,
        bm_name: str,
        oc_name: str,
        reference_event_start_time: float,
    ) -> tuple[str, dict, int, bool, bool, pd.DataFrame, str]:
        """Runs Dynawo to get the simulated curves.

        Parameters
        ----------
        working_oc_dir: Path
            Temporal working path
        pcs_bm_name: str
            PCS.Benchmark name
        bm_name: str
            Benchmark name
        oc_name: str
            Operating Condition name
        reference_event_start_time: float
            Instant of time when the event is triggered in reference curves

        Returns
        -------
        str
            Simulation output dir
        dict
            Event parameters
        float
            Frequency sampling
        bool
            True if simulation is success
        bool
            True if simulation calculated curves
        DataFrame
           Simulation calculated curves
        Str
            Error message if simulation fails
        """

        error_message = None
        self.__reset_solver()

        # Prepare environment to validate it,
        #  prepare in a specific folder all dynawo inputs
        (
            output_dir,
            jobs_output_dir,
        ) = self.__prepare_oc_validation(
            working_oc_dir,
            pcs_bm_name,
            bm_name,
            oc_name,
        )

        # Calculate initialization values and replace it in inputs files
        try:
            event_params = self.__complete_model(
                working_oc_dir,
                pcs_bm_name,
                oc_name,
                reference_event_start_time,
            )
            pcs_bm_oc_name = get_cfg_oc_name(pcs_bm_name, oc_name)
            # Pcs with desired voltage dip are High impedance faults
            if config.get_boolean(pcs_bm_oc_name, "hiz_fault"):
                self.__get_hiz_fault(
                    output_dir,
                    working_oc_dir,
                    jobs_output_dir,
                    event_params["start_time"],
                    event_params["duration_time"],
                    event_params["step_value"],
                )
            # Pcs without desired voltage dip are bolted faults
            elif config.get_boolean(pcs_bm_oc_name, "bolted_fault"):
                self.__get_bolted_fault(
                    working_oc_dir,
                    event_params["start_time"],
                    event_params["duration_time"],
                )

            (
                success,
                has_dynawo_curves,
                curves_calculated,
            ) = self.__simulate(
                output_dir,
                working_oc_dir,
                jobs_output_dir,
            )

        except ValueError as e:
            success = False
            has_dynawo_curves = False
            event_params = dict()
            curves_calculated = pd.DataFrame()
            error_message = str(e)

        self._logger.close_handlers()

        return (
            jobs_output_dir,
            event_params,
            0,
            success,
            has_dynawo_curves,
            curves_calculated,
            error_message,
        )

    def get_disconnection_model(self) -> Disconnection_Model:
        """Get all equipment in the model that can be disconnected in the simulation.

        Returns
        -------
        Disconnection_Model
            Equipment that can be disconnected.
        """
        return Disconnection_Model(
            self.get_producer().aux_load,
            self.get_producer().auxload_xfmr,
            [stepup_xfmr.id for stepup_xfmr in self.get_producer().stepup_xfmrs],
            self.get_producer().intline,
        )

    def get_generators_imax(self) -> dict:
        """Get the maximum current (Imax) for each generator.

        Returns
        -------
        dict
            Maximum continuous current by generator.
        """
        generators_imax = {}
        for generator in self.get_producer().generators:
            generators_imax[generator.id] = generator.IMax
        return generators_imax

    def get_simulation_start(self) -> float:
        """Get simulation start time.

        Returns
        -------
        float
            Simulation start time.
        """
        return self._simulation_start

    def get_simulation_duration(self) -> float:
        """Get simulation duration time.

        Returns
        -------
        float
            Simulation duration time.
        """
        return self._simulation_stop - self._simulation_start

    def get_simulation_precision(self) -> float:
        """Get simulation precision.

        Returns
        -------
        float
            Simulation precision.
        """
        return self._simulation_precision
