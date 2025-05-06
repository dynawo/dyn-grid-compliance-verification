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

from dycov.core.execution_parameters import Parameters
from dycov.curves.manager import CurvesManager
from dycov.model.parameters import Disconnection_Model
from dycov.validation import compliance_list


class Validator:
    def __init__(
        self,
        curves_manager: CurvesManager,
        parameters: Parameters,
        validations: list,
        is_field_measurements: bool,
    ):
        self._curves_manager = curves_manager
        self._time_cct = None
        self._generators_imax = {}
        self._disconnection_model = None
        self._setpoint_variation = 0.0
        self._validations = validations
        self._is_field_measurements = is_field_measurements
        self._producer = parameters.get_producer()

    def _get_calculated_curves(self) -> dict:
        return self._curves_manager.get_curves("calculated")

    def _get_reference_curves(self) -> dict:
        return self._curves_manager.get_curves("reference")

    def _get_calculated_curve_by_name(self, name: str) -> pd.DataFrame:
        curves = self._get_calculated_curves()
        if name not in curves.keys():
            return pd.DataFrame()

        return curves[name]

    def _get_reference_curve_by_name(self, name: str) -> pd.DataFrame:
        curves = self._get_reference_curves()
        if name not in curves.keys():
            return None

        return curves[name]

    def _get_exclusion_times(self) -> tuple[float, float, float, float]:
        return self._curves_manager.get_exclusion_times()

    def _get_curves_by_windows(self, windows: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        return self._curves_manager.get_curves_by_windows(windows)

    def has_validations(self) -> bool:
        """Check if validator has defined validations.

        Returns
        -------
        bool
            True if the validator has validations.
        """
        return bool(self._validations)

    def get_sim_type(self) -> int:
        """Gets the type of validation executed.

        Returns
        -------
        int
            0 if it is an electrical performance for Synchronous Machine Model
            1 if it is an electrical performance for Power Park Module Model
            2 if it is a model validation
        """
        return self._producer.get_sim_type()

    def is_defined_cct(self) -> bool:
        """Check if it is defined the validation Time_cct.

        Returns
        -------
        bool
            True if the validation is defined.
        """
        return compliance_list.contains_key(["time_cct"], self._validations)

    def set_time_cct(self, time_cct: float) -> None:
        """Set the maximum time fault.

        Parameters
        ----------
        time_cct: float
            Maximum time fault
        """
        self._time_cct = time_cct

    def set_generators_imax(self, generators_imax: dict) -> None:
        """Set maximum continuous current.

        Parameters
        ----------
        generators_imax: dict
            Maximum continuous current by generator.
        """
        self._generators_imax = generators_imax

    def set_disconnection_model(self, disconnection_model: Disconnection_Model) -> None:
        """Set all equipment in the model that can be disconnected in the simulation.

        Parameters
        ----------
        disconnection_model: Disconnection_Model
            Equipment that can be disconnected.
        """
        self._disconnection_model = disconnection_model

    def set_setpoint_variation(self, setpoint_variation: float) -> None:
        """Set the setpoint variation.

        Parameters
        ----------
        setpoint_variation: float
            Setpoint variation.
        """
        self._setpoint_variation = setpoint_variation

    def get_generator_u_dim(self) -> float:
        """Get the generator Udim.

        Returns
        -------
        float
            Generator Udim.
        """
        return self._curves_manager.get_generator_u_dim()

    def complete_parameters(
        self,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        event_params: dict,
        cfg_oc_name: str,
    ) -> None:
        """Complete the parameters of the validation.

        Parameters
        ----------
        working_oc_dir: Path
            Working directory.
        jobs_output_dir: Path
            Jobs output directory.
        event_params: dict
            Event parameters.
        cfg_oc_name: str
            Composite name, pcs + Benchmark name + Operating Condition name.
        """
        if self.is_defined_cct():
            self.set_time_cct(
                self._curves_manager.get_time_cct(
                    working_oc_dir,
                    jobs_output_dir,
                    event_params["duration_time"],
                )
            )
        self.set_generators_imax(self._curves_manager.get_generators_imax())
        self.set_disconnection_model(self._curves_manager.get_disconnection_model())
        self.set_setpoint_variation(self._curves_manager.get_setpoint_variation(cfg_oc_name))

    def validate(
        self,
        oc_name: str,
        results_path: Path,
        sim_output_path: str,
        event_params: dict,
    ) -> dict:
        """Validate the simulation results.

        Parameters
        ----------
        oc_name: str
            Operating condition name.
        working_path: Path
            Working path.
        sim_output_path: str
            Simulator output path.
        event_params: dict
            Event parameters

        Returns
        -------
        dict
            Dictionary containing the compliance results.
        """
        pass

    def get_measurement_names(self) -> list:
        """Get the list of required curves for the validation

        Returns
        -------
        list
            Required curves for the validation
        """
        pass
