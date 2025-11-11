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
from dycov.logging.logging import dycov_logging
from dycov.model.parameters import Disconnection_Model
from dycov.model.producer import Producer
from dycov.validation import compliance_list


class Validator(ABC):  # Inherit from ABC to define an abstract base class
    """
    An abstract base class defining the interface for validating simulation results.
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
        """
        Initializes the Validator with necessary components and parameters.

        Parameters
        ----------
        curves_manager: CurvesManager
            Manages the retrieval and processing of curves.
        producer: Producer
            Represents the producer model used in the simulation.
        validations: list
            A list of validations to be performed.
        is_field_measurements: bool
            Indicates if the measurements are from the field.
        pcs_name: str
            Name of the PCS (Power Conversion System).
        bm_name: str
            Name of the Benchmark.
        """
        self._curves_manager = curves_manager
        self._producer = producer
        self._validations = validations
        self._is_field_measurements = is_field_measurements
        self._pcs_name = pcs_name
        self._bm_name = bm_name
        self._time_cct: float = None
        self._generators_imax: dict = {}
        self._disconnection_model: Disconnection_Model = None
        self._setpoint_variation: float = 0.0
        self._oc_name: str = None  # Operating Condition name

    def _get_log_title(self) -> str:
        """
        Generates a standardized title for log messages.

        Returns
        -------
        str
            The formatted log title including PCS, Benchmark, and Operating Condition names.
        """
        return f"{self._pcs_name}.{self._bm_name}.{self._oc_name}:"

    def _log_message(self, level: str, message: str) -> None:
        """
        Logs a message with the specified level and includes the standardized log title.

        Parameters
        ----------
        level: str
            The logging level (e.g., "info", "debug", "warning").
        message: str
            The message to be logged.
        """
        full_message = f"{self._get_log_title()} {message}"
        if level == "info":
            dycov_logging.get_logger("Validator").info(full_message)
        elif level == "debug":
            dycov_logging.get_logger("Validator").debug(full_message)
        elif level == "warning":
            dycov_logging.get_logger("Validator").warning(full_message)

    def _get_calculated_curves(self) -> dict:
        """
        Retrieves the calculated curves from the curves manager.

        Returns
        -------
        dict
            A dictionary of calculated curves.
        """
        return self._curves_manager.get_curves("calculated")

    def _get_reference_curves(self) -> dict:
        """
        Retrieves the reference curves from the curves manager.

        Returns
        -------
        dict
            A dictionary of reference curves.
        """
        return self._curves_manager.get_curves("reference")

    def _get_calculated_curve_by_name(self, name: str) -> pd.DataFrame:
        """
        Retrieves a specific calculated curve by its name.

        Parameters
        ----------
        name: str
            The name of the calculated curve to retrieve.

        Returns
        -------
        pd.DataFrame
            The DataFrame of the requested calculated curve, or an empty DataFrame if not found.
        """
        curves = self._get_calculated_curves()
        return curves.get(name, pd.DataFrame())

    def _get_reference_curve_by_name(self, name: str) -> pd.DataFrame:
        """
        Retrieves a specific reference curve by its name.

        Parameters
        ----------
        name: str
            The name of the reference curve to retrieve.

        Returns
        -------
        pd.DataFrame
            The DataFrame of the requested reference curve, or None if not found.
        """
        curves = self._get_reference_curves()
        return curves.get(name, None)

    def _get_exclusion_times(self) -> tuple[float, float, float, float]:
        """
        Retrieves exclusion times from the curves manager.

        Returns
        -------
        tuple[float, float, float, float]
            A tuple containing four float values representing exclusion times.
        """
        return self._curves_manager.get_exclusion_times()

    def _get_curves_by_windows(self, windows: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Retrieves calculated and reference curves filtered by specified windows.

        Parameters
        ----------
        windows: str
            The window type to apply for filtering curves.

        Returns
        -------
        tuple[pd.DataFrame, pd.DataFrame]
            A tuple containing two DataFrames:
            (calculated_curves_in_window, reference_curves_in_window).
        """
        return self._curves_manager.get_curves_by_windows(windows)

    def set_oc_name(self, oc_name: str) -> None:
        """
        Sets the operating condition name for the validator.

        Parameters
        ----------
        oc_name: str
            The name of the operating condition.
        """
        self._oc_name = oc_name

    def has_validations(self) -> bool:
        """
        Checks if the validator has any defined validations.

        Returns
        -------
        bool
            True if validations are defined, False otherwise.
        """
        return False if not self._validations else True

    def get_sim_type(self) -> int:
        """
        Gets the type of simulation being validated.

        Returns
        -------
        int
            1 if it is an electrical performance for Synchronous Machine Model.
            2 if it is an electrical performance for Power Park Module Model.
            3 if it is a model validation.
        """
        return self._producer.get_sim_type()

    def is_defined_cct(self) -> bool:
        """
        Checks if 'time_cct' validation is defined in the list of validations.

        Returns
        -------
        bool
            True if 'time_cct' validation is defined, False otherwise.
        """
        return compliance_list.contains_key(["time_cct"], self._validations)

    def set_time_cct(self, time_cct: float) -> None:
        """
        Sets the maximum critical clearing time (CCT).

        Parameters
        ----------
        time_cct: float
            The maximum critical clearing time.
        """
        self._time_cct = time_cct

    def set_generators_imax(self, generators_imax: dict) -> None:
        """
        Sets the maximum continuous current for generators.

        Parameters
        ----------
        generators_imax: dict
            A dictionary where keys are generator names and values are their maximum
            continuous currents.
        """
        self._generators_imax = generators_imax

    def set_disconnection_model(self, disconnection_model: Disconnection_Model) -> None:
        """
        Sets the disconnection model, detailing equipment that can be disconnected during
        simulation.

        Parameters
        ----------
        disconnection_model: Disconnection_Model
            An object representing the disconnection model.
        """
        self._disconnection_model = disconnection_model

    def set_setpoint_variation(self, setpoint_variation: float) -> None:
        """
        Sets the setpoint variation value.

        Parameters
        ----------
        setpoint_variation: float
            The value of the setpoint variation.
        """
        self._setpoint_variation = setpoint_variation

    def get_generator_u_dim(self) -> float:
        """
        Gets the generator Udim (rated voltage).

        Returns
        -------
        float
            The generator's rated voltage (Udim).
        """
        return self._curves_manager.get_generator_u_dim()

    def complete_parameters(
        self,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        event_params: dict,
        cfg_oc_name: str,
        oc_name: str,
    ) -> None:
        """
        Completes the validation parameters by retrieving necessary values from the curves manager.

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
    ) -> dict:
        """
        Abstract method to validate the simulation results.
        This method must be implemented by concrete subclasses.

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

        Returns
        -------
        dict
            Dictionary containing the compliance results.
        """
        pass

    @abstractmethod
    def get_measurement_names(self) -> list:
        """
        Abstract method to get the list of required curve names for the validation.
        This method must be implemented by concrete subclasses.

        Returns
        -------
        list
            A list of strings, where each string is the name of a required curve.
        """
        pass
