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
from dycov.core.execution_parameters import Parameters
from dycov.curves.curves import ProducerCurves, get_cfg_oc_name
from dycov.curves.importer.importer import CurvesImporter
from dycov.files import manage_files
from dycov.model.parameters import Disconnection_Model, Gen_init, Gen_params


def _get_generators_ini(generators: list, curves: pd.DataFrame) -> list:
    gens = list()
    for generator in generators:
        voltage = curves[generator.id + "_AVRSetpointPu"]
        U0 = voltage.iloc[0]
        gens.append(Gen_init(generator.id, 0, 0, U0, 0))

    return gens


def _get_config_value(config, section, option, default=0.0):
    if config.has_option(section, option):
        return float(config.get(section, option))
    return default


class ImportedCurves(ProducerCurves):
    def __init__(
        self,
        parameters: Parameters,
    ):
        super().__init__(parameters)
        self._is_field_measurements = False

    def __get_generators(self, curves: pd.DataFrame) -> list:
        generators = list()
        for key in curves.keys():
            if key.endswith("_AVRSetpointPu"):
                gen_id = key.replace("_AVRSetpointPu", "")
                generators.append(
                    Gen_params(
                        id=gen_id,
                        lib="",
                        connectedXmfr="",
                        SNom="",
                        IMax="",
                        par_id="",
                        P="",
                        Q="",
                        VoltageDrop="",
                        UseVoltageDrop=False,
                        equiv_int_line=None,
                    )
                )

        self.get_producer().set_generators(generators)
        return generators

    def __get_curves_dataframe(
        self,
        working_oc_dir: Path,
        pcs_bm_name: str,
        oc_name: str,
        success: bool,
        is_reference: bool = False,
    ) -> tuple[bool, float, float, float, pd.DataFrame]:
        has_imported_curves = True
        if success:
            importer = CurvesImporter(working_oc_dir, get_cfg_oc_name(pcs_bm_name, oc_name))
            (
                df_imported_curves,
                _,
                _,
                fs,
            ) = importer.get_curves_dataframe(self._producer.get_zone())
            if df_imported_curves.empty:
                success = False
                has_imported_curves = False

            if not is_reference:
                self._generators = self.__get_generators(df_imported_curves)
                self._gens = _get_generators_ini(self._generators, df_imported_curves)

            sim_t_event_start = _get_config_value(
                importer.config, "Curves-Metadata", "sim_t_event_start"
            )
            fault_duration = _get_config_value(
                importer.config, "Curves-Metadata", "fault_duration"
            )
            if fs == 0:
                fs = _get_config_value(importer.config, "Curves-Metadata", "frequency_sampling")

            if importer.config.has_option("Curves-Metadata", "is_field_measurements"):
                self._is_field_measurements = bool(
                    importer.config.get("Curves-Metadata", "is_field_measurements")
                )

            generators_imax = {}
            for key in importer.config["Curves-Metadata"].keys():
                if key.endswith("_GEN_MaxInjectedCurrentPu"):
                    generator_id = key.replace("_GEN_MaxInjectedCurrentPu", "")
                    generators_imax[generator_id] = float(
                        importer.config.get("Curves-Metadata", key)
                    )
            self._generators_imax = generators_imax

        else:
            has_imported_curves = False
            sim_t_event_start = 0
            fault_duration = 0
            fs = 0
            self._generators_imax = {}
            df_imported_curves = pd.DataFrame()

        return has_imported_curves, sim_t_event_start, fault_duration, fs, df_imported_curves

    def __obtain_files_curve(
        self,
        working_oc_dir: Path,
        pcs_bm_name: str,
        oc_name: str,
        curves: Path,
        is_reference: bool = False,
    ):
        # Copy base case and producers file
        success = manage_files.copy_base_curves_files(
            curves, working_oc_dir, get_cfg_oc_name(pcs_bm_name, oc_name)
        )
        has_imported_curves, sim_t_event_start, fault_duration, fs, df_imported_curves = (
            self.__get_curves_dataframe(
                working_oc_dir, pcs_bm_name, oc_name, success, is_reference
            )
        )

        config_section = get_cfg_oc_name(pcs_bm_name, oc_name) + ".Event"
        connect_event_to = config.get_value(config_section, "connect_event_to")
        if config.has_key(config_section, "setpoint_step_value"):
            step_value = self.obtain_value(
                str(config.get_value(config_section, "setpoint_step_value"))
            )
        else:
            step_value = 0

        event_params = {
            "start_time": sim_t_event_start,
            "duration_time": fault_duration,
            "pre_value": 0.0,
            "step_value": step_value,
            "connect_to": connect_event_to,
        }

        return (
            event_params,
            fs,
            success,
            has_imported_curves,
            df_imported_curves,
        )

    def get_solver(self) -> dict:
        """There is no solver in this curve format.

        Returns
        -------
        dict
            Solver parameters.
        """
        return dict()

    def obtain_reference_curve(
        self,
        working_oc_dir: Path,
        pcs_bm_name: str,
        oc_name: str,
        curves: Path,
    ) -> tuple[float, pd.DataFrame]:
        """Obtain the reference curves.

        Parameters
        ----------
        working_oc_dir: Path
            Temporal working path
        pcs_bm_name: str
            PCS.Benchmark name
        oc_name: str
            Operating Condition name
        curves: Path
            Reference curves path

        Returns
        -------
        float
            Instant of time when the event is triggered
        DataFrame
           Curves imported from the file
        """
        (
            event_params,
            fs,
            success,
            has_imported_curves,
            curves,
        ) = self.__obtain_files_curve(
            working_oc_dir, pcs_bm_name, oc_name, curves, is_reference=True
        )
        return event_params["start_time"], curves

    def obtain_simulated_curve(
        self,
        working_oc_dir: Path,
        pcs_bm_name: str,
        bm_name: str,
        oc_name: str,
        reference_event_start_time: float,
    ) -> tuple[str, dict, float, bool, bool, pd.DataFrame, str]:
        """Read the input curves to get the simulated curves.

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
        float
            Instant of time when the event is triggered
        float
            Fault duration in seconds
        float
            Frequency sampling
        bool
            True if simulation is success
        bool
            True if simulation calculated curves
        DataFrame
           Simulation calculated curves
        """
        (
            event_params,
            fs,
            success,
            has_imported_curves,
            curves,
        ) = self.__obtain_files_curve(
            working_oc_dir, pcs_bm_name, oc_name, self.get_producer().get_producer_curves_path()
        )

        return (".", event_params, fs, success, has_imported_curves, curves, None)

    def get_disconnection_model(self) -> Disconnection_Model:
        """Get all equipment in the model that can be disconnected in the simulation.
        When there is no model to simulate, it is not possible to detect the equipment
        that has been disconnected.

        Returns
        -------
        Disconnection_Model
            Equipment that can be disconnected.
        """
        return Disconnection_Model(
            None,
            None,
            [],
            None,
        )

    def get_generators_imax(self) -> dict:
        """Get the maximum current (Imax) for each generator.

        Returns
        -------
        dict
            Maximum continuous current by generator.
        """
        return self._generators_imax

    def is_field_measurements(self) -> bool:
        """Check if the reference curves are field measurements.

        Returns
        -------
        bool
            True if the reference signals are field measurements.
        """
        return self._is_field_measurements
