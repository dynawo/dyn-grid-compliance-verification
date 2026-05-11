#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from dycov.curves.manager import CurvesManager
from dycov.model.parameters import DisconnectionModel, ExclusionWindows
from dycov.model.producer import Producer
from dycov.validation import compliance_list


class Validator(ABC):
    """Abstract base class defining the interface for validating simulation results.

    Concrete validator classes must inherit from this class and implement its abstract methods.
    """

    def __init__(
        self,
        curves_manager: CurvesManager,
        producer: Producer,
        validations: list,
        is_field_measurements: bool,
        pcs_name: str,
        bm_name: str,
    ):
        self._curves_manager = curves_manager
        self._producer = producer
        self._validations = validations
        self._is_field_measurements = is_field_measurements
        self._pcs_name = pcs_name
        self._bm_name = bm_name
        self._time_cct: float | None = None
        self._generators_imax: dict = {}
        self._disconnection_model: DisconnectionModel | None = None
        self._setpoint_variation: float = 0.0
        self._oc_name: str | None = None

    def _get_calculated_curves(self) -> pd.DataFrame:
        return self._curves_manager.get_curves("calculated")

    def _get_reference_curves(self) -> pd.DataFrame:
        return self._curves_manager.get_curves("reference")

    def _get_calculated_curve_by_name(self, name: str) -> pd.DataFrame:
        curves = self._get_calculated_curves()
        return curves.get(name, pd.DataFrame())

    def _get_reference_curve_by_name(self, name: str) -> pd.DataFrame | None:
        curves = self._get_reference_curves()
        return curves.get(name, None)

    def _get_exclusion_windows(self) -> ExclusionWindows:
        return self._curves_manager.get_exclusion_windows()

    def _get_curves_by_windows(self, windows: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        return self._curves_manager.get_curves_by_windows(windows)

    def set_oc_name(self, oc_name: str) -> None:
        """Set the operating condition name.

        Parameters
        ----------
        oc_name: str
            The name of the operating condition.
        """
        self._oc_name = oc_name

    def has_validations(self) -> bool:
        """Check if any validations are defined.

        Returns
        -------
        bool
            True if validations are defined, False otherwise.
        """
        return bool(self._validations)

    def get_sim_type(self) -> int:
        """Get the type of simulation being validated.

        Returns
        -------
        int
            1 if it is an electrical performance for Synchronous Machine Model.
            2 if it is an electrical performance for Power Park Module Model.
            3 if it is a model validation.
        """
        return self._producer.get_sim_type()

    def is_defined_cct(self) -> bool:
        """Check if 'time_cct' validation is defined.

        Returns
        -------
        bool
            True if 'time_cct' validation is defined, False otherwise.
        """
        return compliance_list.contains_key(["time_cct"], self._validations)

    def is_defined_imax_reac(self) -> bool:
        """Check if 'imax_reac' validation is defined.

        Returns
        -------
        bool
            True if 'imax_reac' validation is defined, False otherwise.
        """
        return compliance_list.contains_key(["imax_reac"], self._validations)

    def set_time_cct(self, time_cct: float) -> None:
        """Set the maximum critical clearing time (CCT).

        Parameters
        ----------
        time_cct: float
            The maximum critical clearing time.
        """
        self._time_cct = time_cct

    def set_generators_imax(self, generators_imax: dict) -> None:
        """Set the maximum continuous current for generators.

        Parameters
        ----------
        generators_imax: dict
            A dictionary where keys are generator names and values are their maximum
            continuous currents.
        """
        self._generators_imax = generators_imax

    def set_disconnection_model(self, disconnection_model: DisconnectionModel) -> None:
        """Set the disconnection model.

        Parameters
        ----------
        disconnection_model: DisconnectionModel
            An object representing the disconnection model.
        """
        self._disconnection_model = disconnection_model

    def set_setpoint_variation(self, setpoint_variation: float) -> None:
        """Set the setpoint variation value.

        Parameters
        ----------
        setpoint_variation: float
            The value of the setpoint variation.
        """
        self._setpoint_variation = setpoint_variation

    def get_generator_u_dim(self) -> float:
        """Get the generator Udim (rated voltage).

        Returns
        -------
        float
            The generator's rated voltage (Udim).
        """
        return self._curves_manager.get_generator_u_dim()

    def initialize_validation_params(
        self,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        event_params: dict,
        cfg_oc_name: str,
        oc_name: str,
    ) -> None:
        """Initialize the validation parameters from the curves manager.

        Parameters
        ----------
        working_oc_dir: Path
            The working directory for the operating condition.
        jobs_output_dir: Path
            The output directory for jobs.
        event_params: dict
            Parameters related to the event (e.g., 'duration_time').
        cfg_oc_name: str
            Composite name including PCS, Benchmark, and Operating Condition name.
        oc_name: str
            The specific operating condition name.
        """
        if self.is_defined_cct():
            time_cct_value = self._curves_manager.get_time_cct(
                working_oc_dir,
                jobs_output_dir,
                event_params["duration_time"],
                self._bm_name,
                oc_name,
            )
            self.set_time_cct(time_cct_value)
        self.set_generators_imax(self._curves_manager.get_generators_imax())
        self.set_disconnection_model(self._curves_manager.get_disconnection_model())
        self.set_setpoint_variation(self._curves_manager.get_setpoint_variation(cfg_oc_name))

    @abstractmethod
    def validate(
        self,
        oc_name: str,
        results_path: Path,
        sim_output_path: str,
        event_params: dict,
        has_reference: bool = True,
    ) -> dict:
        """Validate the simulation results.

        Parameters
        ----------
        oc_name: str
            Operating condition name.
        results_path: Path
            Path where validation results will be stored.
        sim_output_path: str
            Path to the simulator's output.
        event_params: dict
            Event parameters relevant to the validation.
        has_reference: bool
            Whether reference curves are available. When False, only validations
            that do not require reference curves are executed.

        Returns
        -------
        dict
            Dictionary containing the compliance results.
        """

    @abstractmethod
    def get_measurement_names(self) -> list:
        """Get the list of required curve names for the validation.

        Returns
        -------
        list
            A list of strings, where each string is the name of a required curve.
        """
