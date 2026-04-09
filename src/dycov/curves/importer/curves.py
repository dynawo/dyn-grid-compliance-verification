#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from pathlib import Path

import pandas as pd

from dycov.configuration.cfg import config
from dycov.curves.curves import ProducerCurves, get_cfg_oc_name
from dycov.curves.importer.importer import CurvesImporter
from dycov.curves.voltage_dip import measure_voltage_dip
from dycov.files import manage_files
from dycov.model.parameters import (
    DisconnectionModel,
    GenInit,
    GenParams,
    SimulationResult,
    Terminal,
)
from dycov.model.producer import Producer


def _get_generators_ini(generators: list, curves: pd.DataFrame) -> list:
    """Initializes generator parameters based on provided curves.

    Parameters
    ----------
    generators : list
        List of GenParams objects representing generators.
    curves : pd.DataFrame
        DataFrame containing curve data, including VoltageSetpointPu for each generator.

    Returns
    -------
    list
        List of GenInit objects with initialized voltage (u0).
    """
    return [
        GenInit(
            id=generator.id,
            p0=0,
            q0=0,
            u0=curves[generator.id + "_VoltageSetpointPu"].iloc[0],
            u_phase0=0,
        )
        for generator in generators
    ]


def _get_config_value(config, section, option, default=0.0):
    if config.has_option(section, option):
        return float(config.get(section, option))
    return default


class ImportedCurves(ProducerCurves):
    """
    Manages the import and processing of producer curves from external files.
    This class handles reading curve data, extracting generator parameters,
    and preparing data for simulation based on imported curves.
    """

    def __init__(
        self,
        producer: Producer,
    ):
        super().__init__(producer)
        self._is_field_measurements = False
        self._generators = []
        self._gens = []
        self._generators_imax = {}
        self._voltage_dip = None

    def _get_common_curve_data(
        self,
        working_oc_dir: Path,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        success: bool,
        is_reference: bool = False,
    ) -> tuple[bool, float, float, pd.DataFrame]:
        has_imported_curves = False
        sim_t_event_start = 0.0
        fault_duration = 0.0
        df_imported_curves = pd.DataFrame()

        if not success:
            return has_imported_curves, sim_t_event_start, fault_duration, df_imported_curves

        importer = CurvesImporter(working_oc_dir, get_cfg_oc_name(pcs_name, bm_name, oc_name))
        df_imported_curves = importer.get_curves_dataframe(self._producer.get_zone())

        if df_imported_curves.empty:
            return has_imported_curves, sim_t_event_start, fault_duration, df_imported_curves

        has_imported_curves = True
        if not is_reference:
            self._generators = self.__get_generators(df_imported_curves)
            self._gens = _get_generators_ini(self._generators, df_imported_curves)

        sim_t_event_start = _get_config_value(
            importer.config, "Curves-Metadata", "sim_t_event_start"
        )
        fault_duration = _get_config_value(importer.config, "Curves-Metadata", "fault_duration")

        if importer.config.has_option("Curves-Metadata", "is_field_measurements"):
            self._is_field_measurements = (
                importer.config.get("Curves-Metadata", "is_field_measurements").lower() == "true"
            )
        self.get_producer().set_is_field_measurements(self._is_field_measurements)

        generators_imax = {}
        for key in importer.config["Curves-Metadata"].keys():
            if key.endswith("_GEN_MaxInjectedCurrentPu"):
                generator_id = key.replace("_GEN_MaxInjectedCurrentPu", "")
                generators_imax[generator_id] = float(importer.config.get("Curves-Metadata", key))
        self._generators_imax = generators_imax

        return has_imported_curves, sim_t_event_start, fault_duration, df_imported_curves

    def __get_generators(self, curves: pd.DataFrame) -> list:
        """Identifies generators from the curve data based on a naming convention.

        Parameters
        ----------
        curves : pd.DataFrame
            The DataFrame containing curve data.

        Returns
        -------
        list
            A list of GenParams objects representing the identified generators.
        """
        generators = []
        for key in curves.keys():
            if key.endswith("_VoltageSetpointPu"):
                gen_id = key.replace("_VoltageSetpointPu", "")
                generators.append(
                    GenParams(
                        id=gen_id,
                        lib="",
                        terminals=(Terminal(connected_equipment=""),),
                        s_nom=0.0,
                        i_max=0.0,
                        par_id="",
                        p=0.0,
                        q=0.0,
                        voltage_droop=0.0,
                        use_voltage_droop=False,
                    )
                )
        self.get_producer().set_generators(generators)
        return generators

    def __process_event_parameters(
        self,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        sim_t_event_start: float,
        fault_duration: float,
    ) -> dict:
        config_section = get_cfg_oc_name(pcs_name, bm_name, oc_name) + ".Model"
        pdr_p = config.get_value(config_section, "pdr_P")
        self.get_producer().set_consumption("PmaxConsumption" in pdr_p)

        config_section = get_cfg_oc_name(pcs_name, bm_name, oc_name) + ".Event"
        connect_event_to = config.get_value(config_section, "connect_event_to")
        step_value = 0.0
        if config.has_option(config_section, "setpoint_step_value"):
            step_value = self.obtain_value(
                str(config.get_value(config_section, "setpoint_step_value"))
            )

        return {
            "start_time": sim_t_event_start,
            "duration_time": fault_duration,
            "pre_value": 0.0,
            "step_value": step_value,
            "connect_to": connect_event_to,
        }

    def _obtain_curves(
        self,
        working_oc_dir: Path,
        producer_name: str,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        curves_path: Path,
        is_reference: bool = False,
    ) -> tuple[dict, bool, bool, pd.DataFrame]:
        success = manage_files.copy_base_curves_files(
            curves_path / producer_name,
            working_oc_dir,
            get_cfg_oc_name(pcs_name, bm_name, oc_name),
        )

        has_imported_curves, sim_t_event_start, fault_duration, df_imported_curves = (
            self._get_common_curve_data(
                working_oc_dir, pcs_name, bm_name, oc_name, success, is_reference
            )
        )

        event_params = self.__process_event_parameters(
            pcs_name, bm_name, oc_name, sim_t_event_start, fault_duration
        )

        return event_params, success, has_imported_curves, df_imported_curves

    def get_solver(self) -> dict:
        return {}

    def obtain_reference_curve(
        self,
        working_oc_dir: Path,
        producer_name: str,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        curves: Path,
    ) -> tuple[float, pd.DataFrame]:
        event_params, _, _, curves_df = self._obtain_curves(
            working_oc_dir, producer_name, pcs_name, bm_name, oc_name, curves, is_reference=True
        )
        return event_params["start_time"], curves_df

    def obtain_simulated_curve(
        self,
        working_oc_dir: Path,
        producer_name: str,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        reference_event_start_time: float,
    ) -> tuple[str, dict, SimulationResult, pd.DataFrame]:
        """Read the input curves to get the simulated curves.

        Parameters
        ----------
        working_oc_dir: Path
            Temporal working path
        producer_name: str
            Producer name
        pcs_name: str
            PCS name
        bm_name: str
            Benchmark name
        oc_name: str
            Operating Condition name
        reference_event_start_time: float
            Instant of time when the event is triggered in reference curves
            (not directly used but can be for future validation).

        Returns
        -------
        str
            Simulation output directory (represented as '.').
        dict
            Event parameters.
        SimulationResult
            Information about the simulation result.
        DataFrame
           Simulation calculated curves.
        """
        event_params, success, has_imported_curves, curves_df = self._obtain_curves(
            working_oc_dir,
            producer_name,
            pcs_name,
            bm_name,
            oc_name,
            self.get_producer().get_producer_curves_path(),
        )

        self._voltage_dip = measure_voltage_dip(
            pcs_name,
            bm_name,
            oc_name,
            curves_df,
            event_params["start_time"],
            event_params["duration_time"],
        )

        simulation_result = SimulationResult(
            success=success,
            time_exceeds=False,
            has_simulated_curves=has_imported_curves,
            error=None,
        )
        return ".", event_params, simulation_result, curves_df

    def get_disconnection_model(self) -> DisconnectionModel:
        """Get all equipment in the model that can be disconnected in the simulation.
        When there is no model to simulate, it is not possible to detect the equipment
        that has been disconnected.

        Returns
        -------
        DisconnectionModel
            Equipment that can be disconnected.
        """
        return DisconnectionModel(
            None,
            None,
            [],
            None,
        )

    def get_generators_imax(self) -> dict:
        return self._generators_imax

    def get_voltage_dip(self) -> float | None:
        return self._voltage_dip

    def is_field_measurements(self) -> bool:
        return self._is_field_measurements
