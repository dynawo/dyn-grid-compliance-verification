#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import logging
import math
from datetime import datetime
from pathlib import Path

import pandas as pd

from dgcv.configuration.cfg import config
from dgcv.core.execution_parameters import Parameters
from dgcv.core.producer_curves import ProducerCurves, get_cfg_oc_name
from dgcv.core.validator import Disconnection_Model
from dgcv.dynawo import dynawo
from dgcv.dynawo.dyd import DydFile
from dgcv.dynawo.jobs import JobsFile
from dgcv.dynawo.par import ParFile
from dgcv.dynawo.table import TableFile
from dgcv.dynawo.translator import dynawo_translator
from dgcv.electrical.generator_variables import generator_variables
from dgcv.electrical.initialization_calcs import init_calcs
from dgcv.electrical.pimodel_parameters import line_pimodel
from dgcv.files import (
    dynawo_curves_file,
    manage_files,
    model_parameters,
    omega_file,
    replace_placeholders,
)
from dgcv.files.manage_files import ModelFiles, ProducerFiles
from dgcv.logging.logging import dgcv_logging
from dgcv.logging.simulation_logger import SimulationLogger
from dgcv.model.parameters import Gen_params, Load_init, Load_params, Pdr_params, Pimodel_params
from dgcv.validation import common, sanity_checks


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
        self._simulation_precision = config.get_float("Dynawo", "simulation_precision", 1e-4)
        sanity_checks.check_simulation_duration(self.get_simulation_duration())

        logging.setLoggerClass(SimulationLogger)
        self._logger = logging.getLogger("ProducerCurves")

    def __log(self, message: str):
        self._logger.info(message)
        dgcv_logging.get_logger("ProducerCurves").debug(message)

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
        if dgcv_logging.getEffectiveLevel() == logging.DEBUG:
            file_log_level = "DEBUG"
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

        self.__log("Model definition:")

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

            # In order to implement the fault of the PCS_RTE-I4, the line with
            #  the fault is divided into two lines in series, but for calculation
            #  purposes it must be taken into account as a single line.

            # TODO: Fix this in a more elegant way
            if (
                "PCS_RTE-I4.ThreePhaseFault" in pcs_bm_name
                or "PCS_RTE-I5.ThreePhaseFault" in pcs_bm_name
                or "PCS_RTE-I16z3.ThreePhaseFault" in pcs_bm_name
            ):
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

        self.__log("Event definition:")
        event_params = self.__get_event_parameters(
            pcs_bm_name,
            oc_name,
        )
        if reference_event_start_time and event_params["start_time"] != reference_event_start_time:
            dgcv_logging.get_logger("Dynawo ProducerCurves").warning(
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

        jobs_file = JobsFile(self, pcs_bm_name, oc_name)
        jobs_file.complete_file(working_oc_dir, event_params)

        par_file = ParFile(self, pcs_bm_name, oc_name)
        par_file.complete_file(working_oc_dir, line_rpu, line_xpu, rte_gen, event_params)

        dyd_file = DydFile(self, pcs_bm_name, oc_name)
        dyd_file.complete_file(working_oc_dir, event_params)

        table_file = TableFile(self, pcs_bm_name, oc_name)
        table_file.complete_file(working_oc_dir, rte_gen, event_params)

        omega_file.complete_omega(
            working_oc_dir,
            "Omega.dyd",
            "Omega.par",
            self.get_producer().generators,
            self.get_producer().get_zone(),
        )

        xmfrs = self.get_producer().stepup_xfmrs.copy()
        if self.get_producer().auxload_xfmr:
            xmfrs.append(self.get_producer().auxload_xfmr)
        if self.get_producer().ppm_xfmr:
            xmfrs.append(self.get_producer().ppm_xfmr)

        self._curves_dict = dynawo_curves_file.create_curves_file(
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
        pcs_bm_name: str,
        oc_name: str,
    ) -> dict:
        config_section = get_cfg_oc_name(pcs_bm_name, oc_name) + ".Event"

        connect_event_to = config.get_value(config_section, "connect_event_to")
        self.__log(f"\t{connect_event_to=}")
        pre_value = 1.0
        if connect_event_to:
            if "ActivePowerSetpointPu" == connect_event_to:
                pre_value = -self._gens[0].P0
            elif "ReactivePowerSetpointPu" == connect_event_to:
                pre_value = -self._gens[0].Q0
            elif "AVRSetpointPu" == connect_event_to:
                pre_value = self._gens[0].U0

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

        self._line_Xpu = line_xpu
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

        ini_pdr_p = model_parameters.extract_defined_value(
            pdr_p, "pmax", self.get_producer().p_max_pu * -1
        )

        if "Qmin" in pdr_q:
            ini_pdr_q = model_parameters.extract_defined_value(
                pdr_q, "qmin", self.get_producer().q_min_pu
            )
        elif "Qmax" in pdr_q:
            ini_pdr_q = model_parameters.extract_defined_value(
                pdr_q, "qmax", self.get_producer().q_max_pu
            )
        else:
            ini_pdr_q = model_parameters.extract_defined_value(
                pdr_q, "pmax", self.get_producer().p_max_pu * -1
            )

        ini_pdr_u = (
            model_parameters.extract_defined_value(pdr_u, "udim", u_dim)
            / self.get_producer().u_nom
        )
        return Pdr_params(ini_pdr_u, complex(ini_pdr_p, ini_pdr_q))

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
        loads = []
        for load in self._rte_loads:
            try:
                p = float(load.P)
            except ValueError:
                p_cfg = config.get_value(config_section, load.P)
                self.__log(f"\t{load.P}={p_cfg}")
                p = model_parameters.extract_defined_value(
                    p_cfg, "pmax", self.get_producer().p_max_pu
                )

            try:
                q = float(load.Q)
            except ValueError:
                q_cfg = config.get_value(config_section, load.Q)
                self.__log(f"\t{load.Q}={q_cfg}")
                q = model_parameters.extract_defined_value(
                    q_cfg, "pmax", self.get_producer().p_max_pu
                )

            try:
                u = float(load.U)
            except ValueError:
                u_cfg = config.get_value(config_section, load.U)
                self.__log(f"\t{load.U}={u_cfg}")
                u = (
                    model_parameters.extract_defined_value(u_cfg, "udim", u_dim)
                    / self.get_producer().u_nom
                )

            try:
                uphase = float(load.UPhase)
            except ValueError:
                uphase_cfg = config.get_value(config_section, load.UPhase)
                self.__log(f"\t{load.UPhase}={uphase_cfg}")
                uphase = model_parameters.extract_defined_value(uphase_cfg, "NA", 1.0)

            loads.append(Load_init(load.id, "", p, q, u, uphase))

        return loads

    def __modify_fault(
        self,
        working_oc_dir: Path,
        fault_start: float,
        fault_duration: float,
        fault_xpu: float,
        fault_rpu: float,
    ) -> bool:
        if self.get_producer().get_zone() != 1:
            return

        replace_placeholders.fault_par_file(
            working_oc_dir,
            "TSOModel.par",
            fault_start + fault_duration,
            fault_xpu,
            fault_rpu,
        )

    def __execute_dynawo(
        self,
        output_dir: Path,
        working_oc_dir: Path,
        jobs_output_dir: Path,
    ):
        # Run Dynawo
        success, log, has_error, curves_calculated = dynawo.run_base_dynawo(
            self._launcher_dwo,
            "TSOModel",
            self._curves_dict,
            working_oc_dir,
            jobs_output_dir,
        )
        if has_error:
            log_file = output_dir / jobs_output_dir / "logs/dynawo.log"
            log = f"Simulation Fails, logs in {str(log_file)}"

        # Check if there is a curves file
        has_dynawo_curves = False
        if (working_oc_dir / jobs_output_dir / "curves/curves.csv").exists() and success:
            has_dynawo_curves = True

        return success, log, has_dynawo_curves, curves_calculated

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

        max_val = 1
        min_val = 0.000001
        fault_xpu = round(((max_val + min_val) / 2), 4)
        run_dynawo = True
        last_fault_xpu = fault_xpu
        while run_dynawo:
            now = datetime.now()
            working_oc_dir_fault = manage_files.clone_as_subdirectory(
                working_oc_dir, "fault_time_execution_" + now.strftime("%Y%m%d%H%M%S%f")
            )

            if fault_r_factor == 0.0:
                fault_rpu = 0
            else:
                fault_rpu = fault_xpu / fault_r_factor
            self.__modify_fault(
                working_oc_dir_fault,
                fault_start,
                fault_duration,
                fault_xpu,
                fault_rpu=fault_rpu,
            )

            (
                success,
                log,
                has_dynawo_curves,
                curves_calculated,
            ) = self.__execute_dynawo(
                output_dir,
                working_oc_dir_fault,
                jobs_output_dir,
            )

            # returned values:
            #  *  1 if the required dip is greater than that obtained
            #  * -1 if the required dip is less than that obtained
            #  *  0 otherwise
            voltage_dip = dynawo.check_voltage_dip(
                success,
                curves_calculated,
                fault_start,
                fault_duration,
                abs(dip),
            )

            if success:
                last_fault_xpu = fault_xpu

            if dgcv_logging.getEffectiveLevel() != logging.DEBUG:
                manage_files.remove_dir(working_oc_dir_fault)
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
                run_dynawo = False

            fault_xpu = round(((max_val + min_val) / 2), 4)
            if round(max_val - min_val, 4) <= 0.0001:
                run_dynawo = False

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
    ) -> float:
        # For a given fault duration time, it is checked if the
        #  simulation is stable, if it is, the time is doubled
        #  until an unstable simulation is achieved.
        max_val = fault_duration * 2

        while self.__run_time_cct(
            working_oc_dir_attempt,
            jobs_output_dir,
            max_val,
        ):
            max_val *= 2

        return max_val

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
        ret_val, _, _, _ = dynawo.run_base_dynawo(
            self._launcher_dwo,
            "TSOModel",
            self._curves_dict,
            working_oc_dir_attempt,
            jobs_output_dir,
            save_file=False,
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

    def get_time_cct(
        self,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        fault_duration: float,
    ) -> float:
        """Find by bisection the maximum time fault.

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
            Maximum time fault
        """

        # The range to work is defined from the configured time to the
        #  fault duration to a value where the simulation is not stable.
        min_val = fault_duration
        working_oc_dir_fault = manage_files.clone_as_subdirectory(
            working_oc_dir, "fault_time_execution_max"
        )
        max_val = self.__get_max_duration(
            working_oc_dir_fault,
            jobs_output_dir,
            fault_duration,
        )
        manage_files.remove_dir(working_oc_dir_fault)

        dgcv_logging.get_logger("Operating Condition").debug(
            "Upper time to find clear time: " + str(max_val)
        )
        dgcv_logging.get_logger("Operating Condition").debug(
            "Lower time to find clear time: " + str(min_val)
        )

        # The maximum duration that the fault admits without losing
        #  stability is sought by bisection
        time = round(((max_val + min_val) / 2), 4)
        counter = 0
        find = False
        while not find:
            dgcv_logging.get_logger("Operating Condition").debug(
                "Attempt " + str(counter) + " to find clear time. Used fault time: " + str(time)
            )

            now = datetime.now()
            working_oc_dir_fault = manage_files.clone_as_subdirectory(
                working_oc_dir, "fault_time_execution_" + now.strftime("%Y%m%d%H%M%S%f")
            )
            steady_state = self.__run_time_cct(
                working_oc_dir_fault,
                jobs_output_dir,
                time,
            )

            if steady_state:
                min_val = time
            else:
                max_val = time

            if dgcv_logging.getEffectiveLevel() != logging.DEBUG:
                manage_files.remove_dir(working_oc_dir_fault)
            else:
                if steady_state:
                    manage_files.rename_dir(
                        working_oc_dir_fault, working_oc_dir / "bisection_last_success"
                    )
                else:
                    manage_files.rename_dir(
                        working_oc_dir_fault, working_oc_dir / "bisection_last_failure"
                    )

            time = round(((max_val + min_val) / 2), 4)

            if round(max_val - min_val, 4) <= 0.0001:
                find = True

            counter += 1

        return time

    def obtain_simulated_curve(
        self,
        working_oc_dir: Path,
        pcs_bm_name: str,
        bm_name: str,
        oc_name: str,
        reference_event_start_time: float,
    ) -> tuple[str, dict, int, bool, bool, pd.DataFrame]:
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
        """

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
                log,
                has_dynawo_curves,
                curves_calculated,
            ) = self.__execute_dynawo(
                output_dir,
                working_oc_dir,
                jobs_output_dir,
            )

            if not success:
                dgcv_logging.get_logger("Dynawo").warning(log)

        except ValueError:
            success = False
            has_dynawo_curves = False
            event_params = dict()
            curves_calculated = pd.DataFrame()

        self._logger.close_handlers()

        return (
            jobs_output_dir,
            event_params,
            0,
            success,
            has_dynawo_curves,
            curves_calculated,
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
        """Get maximum continuous current.

        Returns
        -------
        dict
            Get maximum continuous current by generator.
        """
        generators_imax = {}
        for generator in self.get_producer().generators:
            generators_imax[generator.id] = generator.IMax
        return generators_imax

    def get_simulation_start(self) -> float:
        return self._simulation_start

    def get_simulation_duration(self) -> float:
        return self._simulation_stop - self._simulation_start

    def get_simulation_precision(self) -> float:
        return self._simulation_precision