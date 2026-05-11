#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#
import math
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.core.global_variables import CASE_SEPARATOR
from dycov.curves.curves import ProducerCurves, get_cfg_oc_name
from dycov.curves.dynawo.io import crv
from dycov.curves.dynawo.io.dyd import DydFile
from dycov.curves.dynawo.io.jobs import JobsFile
from dycov.curves.dynawo.io.par import ParFile
from dycov.curves.dynawo.io.solvers import SolversFile
from dycov.curves.dynawo.io.table import TableFile
from dycov.electrical.generator_variables import generator_variables
from dycov.electrical.initialization_calcs import init_calcs
from dycov.electrical.pimodel_parameters import line_pimodel
from dycov.files import model_parameters, omega_file, tso_file
from dycov.logging.logging import dycov_logging
from dycov.model.parameters import GenParams, LoadInit, LoadParams, PdrParams, PimodelParams

_TSO_PAR = "TSOModel.par"
_TSO_DYD = "TSOModel.dyd"


def compute_rx_from_scr(scr, x_over_r=10.0):
    """
    Compute R and X from SCR assuming:
      R^2 + X^2 = 1 / SCR^2
      X / R = x_over_r
    Returns (R, X)
    """
    factor = math.sqrt(1 + x_over_r**2)
    R = 1.0 / (factor * scr)
    X = x_over_r * R
    return R, X


class ModelSetup:
    """
    Calculates initial conditions and completes all Dynawo input files
    (.jobs, .par, .dyd, .crv, .solvers) for one operating condition.

    This class is purely concerned with model preparation: it reads
    configuration, performs electrical initialization calculations, and
    writes the resulting values into the working directory. It does not
    run any simulations.
    """

    def __init__(self, producer: ProducerCurves, pcs_name: str, s_nref: float, f_nom: float):
        """
        Parameters
        ----------
        producer : ProducerCurves
            The ProducerCurves instance that owns this setup object, used to
            access producer data (generators, transformers, etc.) and the
            complete_unit_characteristics / obtain_value helpers.
        pcs_name : str
            Name of the PCS (Power Control System).
        s_nref : float
            Reference apparent power (MVA).
        f_nom : float
            Nominal frequency (Hz).  (Unused directly here but kept for completeness.)
        """
        self._owner = producer
        self._pcs_name = pcs_name
        self._s_nref = s_nref
        self._f_nom = f_nom

        # State populated during complete_model; exposed as attributes so that
        # DynawoCurves can read them after the call.
        self.rte_loads: list = []
        self.has_line: bool = False
        self.curves_dict: dict = {}

        # Dynawo file handlers (re-created per operating condition)
        self._jobs_file = None
        self._par_file = None
        self._dyd_file = None
        self._table_file = None
        self._solvers_file = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cfg_section(self, pcs_name: str, bm_name: str, oc_name: str, suffix: str = "") -> str:
        base = get_cfg_oc_name(pcs_name, bm_name, oc_name)
        return base + suffix if suffix else base

    # ------------------------------------------------------------------
    # Grid impedance
    # ------------------------------------------------------------------

    def _get_lines_for_initial_calcs(self, rte_lines: list) -> PimodelParams:
        """Aggregates pi-model parameters from all TSO lines."""
        if not rte_lines:
            return PimodelParams(math.inf, 0, 0)

        y_tr_sum, y_sh1_sum, y_sh2_sum = 0, 0, 0
        for line in rte_lines:
            pimodel_line = line_pimodel(line)
            y_tr_sum += pimodel_line.y_tr
            y_sh1_sum += pimodel_line.y_sh1
            y_sh2_sum += pimodel_line.y_sh2
        return PimodelParams(y_tr_sum, y_sh1_sum, y_sh2_sum)

    def _get_line(
        self,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
    ) -> tuple[float, float]:
        """
        Calculates line resistance (rpu) and reactance (xpu) from configuration.

        Returns
        -------
        tuple[float, float]
            (line_rpu, line_xpu)
        """
        config_section = self._cfg_section(pcs_name, bm_name, oc_name, ".Model")
        line_rpu = 0.0
        line_xpu = 0.0
        self.has_line = False
        producer = self._owner.get_producer()

        if config.has_option(config_section, "line_XPu"):
            self.has_line = True
            line_xpu_definition = config.get_value(config_section, "line_XPu")
            dycov_logging.get_logger("ModelSetup").debug(f"\tline_XPu={line_xpu_definition}")
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
                    abs(producer.p_max_pu) * -1,
                    producer.s_nom,
                    producer.u_nom,
                    self._s_nref,
                )
            if producer.get_zone() == 3:
                xpu_r_factor = config.get_float("GridCode", "XPu_r_factor", 0.0)
                line_rpu = line_xpu / xpu_r_factor if xpu_r_factor != 0.0 else 0.0
            else:
                line_rpu = 0.0

        elif config.has_option(config_section, "SCR"):
            self.has_line = True
            scr = config.get_float(config_section, "SCR", 0.0)
            dycov_logging.get_logger("ModelSetup").debug(f"\tSCR={scr}")
            scr_r_factor = config.get_float("GridCode", "SCR_r_factor", 0.0)
            if scr != 0:
                line_rpu, line_xpu = compute_rx_from_scr(scr, x_over_r=scr_r_factor)
                line_rpu *= self._s_nref / producer.s_nom
                line_xpu *= self._s_nref / producer.s_nom

        elif config.has_option(config_section, "Zcc"):
            self.has_line = True
            scc = generator_variables.get_scc(producer.u_nom)
            udim = generator_variables.get_generator_u_dim(producer.u_nom)
            uc_pu = udim / producer.u_nom
            scc_pu = scc / self._s_nref
            ztanphi = config.get_float("GridCode", "Ztanphi", 1.0)
            if ztanphi < 1.0:
                ztanphi = 1.0
            if scc != 0:
                zcc = uc_pu**2 / scc_pu
                dycov_logging.get_logger("ModelSetup").debug(f"\tZcc={zcc}")
                line_xpu = ztanphi * zcc / math.sqrt(1 + ztanphi * ztanphi)
                line_rpu = line_xpu / ztanphi

        self._owner.complete_unit_characteristics(line_xpu)
        return line_rpu, line_xpu

    # ------------------------------------------------------------------
    # PDR and load parameters
    # ------------------------------------------------------------------

    def _get_pdr(
        self,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        u_dim: float,
    ) -> PdrParams:
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
        PdrParams
            PDR parameters (U, complex power, active power, reactive power).
        """
        config_section = self._cfg_section(pcs_name, bm_name, oc_name, ".Model")
        producer = self._owner.get_producer()

        pdr_p_cfg = config.get_value(config_section, "pdr_P")
        dycov_logging.get_logger("ModelSetup").debug(f"\tpdr_P={pdr_p_cfg}")
        pdr_q_cfg = config.get_value(config_section, "pdr_Q")
        dycov_logging.get_logger("ModelSetup").debug(f"\tpdr_Q={pdr_q_cfg}")
        pdr_u_cfg = config.get_value(config_section, "pdr_U")
        dycov_logging.get_logger("ModelSetup").debug(f"\tpdr_U={pdr_u_cfg}")

        producer.set_consumption("PmaxConsumption" in pdr_p_cfg)
        ini_pdr_p = model_parameters.extract_defined_value(
            pdr_p_cfg, "Pmax", producer.p_max_pu, -1
        )

        if "Qmin" in pdr_q_cfg:
            ini_pdr_q = model_parameters.extract_defined_value(
                pdr_q_cfg, "Qmin", producer.q_min_pu, -1
            )
        elif "Qmax" in pdr_q_cfg:
            ini_pdr_q = model_parameters.extract_defined_value(
                pdr_q_cfg, "Qmax", producer.q_max_pu, -1
            )
        else:
            ini_pdr_q = model_parameters.extract_defined_value(
                pdr_q_cfg, "Pmax", producer.p_max_pu, -1
            )

        if "Udim" in pdr_u_cfg:
            base_value = u_dim
            parameter_name = "Udim"
        else:
            base_value = producer.u_nom
            parameter_name = "Unom"
        ini_pdr_u = (
            model_parameters.extract_defined_value(pdr_u_cfg, parameter_name, base_value)
            / producer.u_nom
        )
        return PdrParams(ini_pdr_u, 0.0, complex(ini_pdr_p, ini_pdr_q), ini_pdr_p, ini_pdr_q)

    def _get_grid_load(
        self,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        u_dim: float,
    ) -> LoadParams:
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
        LoadParams
            Grid load parameters.
        """
        config_section = self._cfg_section(pcs_name, bm_name, oc_name, ".Model")
        init_loads = self._complete_loads(config_section, bm_name, oc_name, u_dim)
        return model_parameters.get_grid_load(init_loads)

    def _complete_loads(
        self,
        config_section: str,
        bm_name: str,
        oc_name: str,
        u_dim: float,
    ) -> list:
        """
        Resolves per-load P/Q/U values from configuration or defaults.

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
        list[LoadInit]
        """
        producer = self._owner.get_producer()

        def _get_load_value(param_name: str, default_key: str, default_value: float) -> float:
            try:
                return float(param_name)
            except ValueError:
                cfg_value = config.get_value(config_section, param_name)
                dycov_logging.get_logger("ModelSetup").debug(f"\t{param_name}={cfg_value}")
                return model_parameters.extract_defined_value(
                    cfg_value, default_key, default_value
                )

        loads = []
        for load in self.rte_loads:
            p = _get_load_value(load.p, "pmax", producer.p_max_pu)
            q = _get_load_value(load.q, "pmax", producer.p_max_pu)
            u = _get_load_value(load.u, "udim", u_dim) / producer.u_nom
            uphase = _get_load_value(load.u_phase, "NA", 1.0)
            loads.append(LoadInit(load.id, "", p, q, u, uphase))
        return loads

    # ------------------------------------------------------------------
    # Voltage dip Xv parameters
    # ------------------------------------------------------------------

    def _calculate_xv(self, udip: float, zcc: float, uinf: float) -> float:
        """
        Calculates the series reactance Xv that produces a given voltage dip.

        Raises
        ------
        ValueError
            If uinf equals udip (division by zero).
        """
        if uinf == udip:
            dycov_logging.get_logger("ModelSetup").error(
                "Uinf cannot be equal to Udip to avoid division by zero."
            )
            raise ValueError("Uinf cannot be equal to Udip to avoid division by zero.")
        zv = (udip * zcc) / (uinf - udip)
        ztanphi = config.get_float("GridCode", "Ztanphi", 1.0)
        xv = (zv * ztanphi) / math.sqrt(1 + ztanphi * ztanphi)
        if xv == 0.0:
            dycov_logging.get_logger("ModelSetup").warning(
                "Xv is zero, which may indicate an issue with the calculation."
            )
            xv = 1e-3
        return xv

    def _calculate_xv_values(
        self,
        event_params: dict,
        line_xpu: float,
        line_rpu: float,
        rte_gen_u0: float,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
    ) -> None:
        """
        Populates event_params with Xv entries derived from u_* config options.

        Parameters
        ----------
        event_params : dict
            Event parameters dict to update in-place.
        line_xpu : float
            Line reactance (pu).
        line_rpu : float
            Line resistance (pu).
        rte_gen_u0 : float
            RTE generator terminal voltage (pu), used as Uinf.
        pcs_name : str
            PCS.Benchmark name.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        """
        zcc = math.sqrt(line_xpu * line_xpu + line_rpu * line_rpu)
        uinf = rte_gen_u0
        model_section = self._cfg_section(pcs_name, bm_name, oc_name, ".Model")
        generator_type = generator_variables.get_generator_type(self._owner.get_producer().u_nom)
        u_list_options = [
            s
            for s in config.get_options(model_section)
            if s.startswith("u_") and s.endswith(generator_type)
        ]
        for option in u_list_options:
            name_xv = f"Xv_{option[2:]}".replace(f"_{generator_type}", "")
            u_value_from_config = config.get_float(model_section, option, -999.0)
            event_params[name_xv] = self._calculate_xv(u_value_from_config, zcc, uinf)

    # ------------------------------------------------------------------
    # Event parameters
    # ------------------------------------------------------------------

    def _get_event_parameters(
        self,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        pdr: PdrParams,
    ) -> dict:
        """
        Retrieves event parameters (start time, duration, setpoint step, etc.)
        from the configuration.

        Parameters
        ----------
        pcs_name : str
            PCS.Benchmark name.
        bm_name : str
            Benchmark name.
        oc_name : str
            Operating Condition name.
        pdr : PdrParams
            PDR parameters.

        Returns
        -------
        dict
            Event parameters dictionary.
        """
        config_section = self._cfg_section(pcs_name, bm_name, oc_name, ".Event")
        producer = self._owner.get_producer()
        connect_event_to = config.get_value(config_section, "connect_event_to")
        dycov_logging.get_logger("ModelSetup").debug(f"\t{connect_event_to=}")

        pre_value = 1.0
        setpoint_factor = self._s_nref / producer.s_nom
        if connect_event_to:
            if connect_event_to == "ActivePowerSetpointPu":
                pre_value = [
                    (
                        -pdr.p * setpoint_factor
                        if not gen.ppc_local
                        else -gen.terminals[0].p0 * setpoint_factor
                    )
                    for gen in producer.generators
                ]
            elif connect_event_to == "ReactivePowerSetpointPu":
                pre_value = [
                    (
                        -pdr.q * setpoint_factor
                        if not gen.ppc_local
                        else -gen.terminals[0].q0 * setpoint_factor
                    )
                    for gen in producer.generators
                ]
            elif connect_event_to == "VoltageSetpointPu":
                pre_value = [
                    (pdr.u if not gen.ppc_local else gen.terminals[0].u0)
                    for gen in producer.generators
                ]

        start_time = config.get_float(config_section, "sim_t_event_start", 0.0)
        dycov_logging.get_logger("ModelSetup").debug(f"\tsim_t_event_start={start_time}")

        if config.has_option(config_section, "fault_duration"):
            fault_duration = config.get_float(config_section, "fault_duration", 0.0)
        else:
            generator_type = generator_variables.get_generator_type(producer.u_nom)
            fault_duration = config.get_float(
                config_section, f"fault_duration_{generator_type}", 0.0
            )
        dycov_logging.get_logger("ModelSetup").debug(f"\tfault_duration={fault_duration}")

        step_value = 0.0
        if config.has_option(config_section, "setpoint_step_value"):
            step_value = self._owner.obtain_value(
                str(config.get_value(config_section, "setpoint_step_value"))
            )
            if connect_event_to in ["ActivePowerSetpointPu", "ReactivePowerSetpointPu"]:
                step_value *= setpoint_factor
        dycov_logging.get_logger("ModelSetup").debug(f"\tsetpoint_step_value={step_value}")

        return {
            "start_time": start_time,
            "duration_time": fault_duration,
            "pre_value": pre_value,
            "step_value": step_value,
            "connect_to": connect_event_to,
        }

    def _resolve_pre_value(self, gen: GenParams, pdr: PdrParams) -> float:
        base_u = gen.terminals[0].u0 if gen.ppc_local else pdr.u
        base_q = gen.terminals[0].q0 if gen.ppc_local else pdr.q

        if not gen.use_voltage_droop:
            return base_u

        return base_u + gen.voltage_droop * base_q

    def _adjust_event_value(self, event_params: dict, pdr: PdrParams) -> None:
        """
        Adjusts event pre_value for VoltageSetpointPu when voltage droop is active.

        Parameters
        ----------
        event_params : dict
            Event parameters dict to update in-place.
        pdr : PdrParams
            PDR parameters.
        """
        if event_params["connect_to"] != "VoltageSetpointPu":
            return

        producer = self._owner.get_producer()
        pre_value = [self._resolve_pre_value(gen, pdr) for gen in producer.generators]
        dycov_logging.get_logger("ModelSetup").debug(
            f"Adjusted pre_value for VoltageSetpointPu: {pre_value}"
        )
        event_params["pre_value"] = pre_value

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def complete_model(
        self,
        working_oc_dir: Path,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        reference_event_start_time: float,
    ) -> tuple[bool, dict]:
        """
        Performs the full model setup pipeline for one operating condition:
        reads loads, computes PDR/line/grid-load initial conditions, resolves
        event parameters, writes all Dynawo input files, and populates
        self.curves_dict.

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
            Instant of time when the event is triggered in the reference curves.
            When not None and different from the configured value, it overrides the
            configured start time and a warning is emitted.

        Returns
        -------
        bool
            True if the model setup is completed successfully, False if the test is not applicable.
        dict
            Completed event parameters.
        """
        producer = self._owner.get_producer()

        dycov_logging.get_logger("ModelSetup").debug(
            f"Unom: {producer.u_nom}, "
            f"Generator type: {generator_variables.get_generator_type(producer.u_nom)}",
        )
        dycov_logging.get_logger("ModelSetup").debug(
            f"Model definition for '{get_cfg_oc_name(pcs_name, bm_name, oc_name)}':",
        )

        # Read TSO network loads
        self.rte_loads = model_parameters.get_pcs_load_params(
            working_oc_dir / _TSO_DYD,
            working_oc_dir / _TSO_PAR,
        )

        u_dim = self._owner.get_generator_u_dim()
        pdr = self._get_pdr(pcs_name, bm_name, oc_name, u_dim)
        line_rpu, line_xpu = self._get_line(pcs_name, bm_name, oc_name)

        rte_lines = []
        if self.has_line:
            rte_lines = model_parameters.get_pcs_lines_params(
                working_oc_dir / _TSO_DYD,
                working_oc_dir / _TSO_PAR,
                line_rpu,
                line_xpu,
            )

        conn_line = self._get_lines_for_initial_calcs(rte_lines)

        # Sort step-up transformers to match generator order
        xfmr_map = {xfmr.id: xfmr for xfmr in producer.stepup_xfmrs}
        sorted_stepup_xfmrs = [
            xfmr_map[gen.terminals[0].connected_equipment]
            for gen in producer.generators
            if gen.terminals[0].connected_equipment in xfmr_map
        ]

        rte_gen = init_calcs(
            tuple(producer.generators),
            tuple(sorted_stepup_xfmrs),
            producer.aux_load,
            producer.auxload_xfmr,
            producer.ppm_xfmr,
            producer.intline,
            pdr,
            conn_line,
            self._get_grid_load(pcs_name, bm_name, oc_name, u_dim),
        )

        dycov_logging.get_logger("ModelSetup").debug(
            f"Event definition for '{get_cfg_oc_name(pcs_name, bm_name, oc_name)}':",
        )
        event_params = self._get_event_parameters(pcs_name, bm_name, oc_name, pdr)

        if (
            reference_event_start_time is not None
            and event_params["start_time"] != reference_event_start_time
        ):
            dycov_logging.get_logger("ModelSetup").warning(
                f"The simulation will use the 'sim_t_event_start' value present in the Reference "
                f"Curves ({reference_event_start_time}), instead of the value configured "
                f"({event_params['start_time']}).",
            )
            event_params["start_time"] = reference_event_start_time

        section = get_cfg_oc_name(pcs_name, bm_name, oc_name)
        control_mode = config.get_value(section, "setpoint_change_test_type")
        force_voltage_droop = config.get_boolean(self._pcs_name, "force_voltage_droop", False)
        is_test_applicable = model_parameters.adjust_producer_init(
            working_oc_dir,
            producer.get_producer_par(),
            producer.generators,
            sorted_stepup_xfmrs,
            producer.aux_load,
            pdr,
            control_mode,
            force_voltage_droop,
            producer.get_zone(),
        )
        if not is_test_applicable:
            self._debug(
                f"The selected control mode '{control_mode}' is not valid for all generators. "
                f"Please check the configuration for '{section}' and ensure that the control mode "
                f"is compatible with the generator types."
            )
            return False, event_params

        self._adjust_event_value(event_params, pdr)
        self._calculate_xv_values(
            event_params,
            line_xpu,
            line_rpu,
            rte_gen.u0,
            pcs_name,
            bm_name,
            oc_name,
        )

        # Initialize and write Dynawo file handlers
        pcs_bm_name = f"{pcs_name}{CASE_SEPARATOR}{bm_name}"
        self._jobs_file = JobsFile(self._owner, pcs_bm_name, oc_name)
        self._par_file = ParFile(self._owner, pcs_bm_name, oc_name)
        self._dyd_file = DydFile(self._owner, pcs_bm_name, oc_name)
        self._table_file = TableFile(self._owner, pcs_bm_name, oc_name)
        self._solvers_file = SolversFile(self._owner, pcs_bm_name, oc_name)

        solver_id = self._owner._solver_id
        solver_lib = self._owner._solver_lib
        self._jobs_file.complete_file(working_oc_dir, solver_id, solver_lib, event_params)
        self._par_file.complete_file(
            working_oc_dir, line_rpu, line_xpu, rte_gen, event_params, producer.u_nom
        )
        self._dyd_file.complete_file(working_oc_dir, event_params)
        self._table_file.complete_file(working_oc_dir, rte_gen, event_params)
        self._solvers_file.complete_file(working_oc_dir)

        rte_generators = model_parameters.get_pcs_generators_params(
            working_oc_dir / _TSO_DYD,
            working_oc_dir / _TSO_PAR,
        )

        dycov_logging.get_logger("ModelSetup").debug("Complete omega file")
        omega_file.complete_omega(
            working_oc_dir,
            "Omega.dyd",
            "Omega.par",
            producer.generators + rte_generators,
        )
        tso_file.complete_setpoint(
            working_oc_dir,
            _TSO_DYD,
            _TSO_PAR,
            producer.generators,
            config.get_value(pcs_bm_name, "TSO_model"),
            event_params,
        )
        model_parameters.write_pdr_comment(
            working_oc_dir,
            producer.get_producer_par().name,
            pdr,
        )
        model_parameters.write_pdr_comment(
            working_oc_dir,
            _TSO_PAR,
            pdr,
        )

        xmfrs = producer.stepup_xfmrs[:]
        if producer.auxload_xfmr:
            xmfrs.append(producer.auxload_xfmr)
        if producer.ppm_xfmr:
            xmfrs.append(producer.ppm_xfmr)

        self.curves_dict = crv.create_curves_file(
            working_oc_dir,
            "TSOModel.crv",
            xmfrs,
            producer.generators,
            self.rte_loads,
            producer.get_sim_type(),
            producer.get_zone(),
            control_mode,
        )
        return True, event_params
