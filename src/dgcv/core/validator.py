#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from collections import namedtuple
from pathlib import Path

from dgcv.validation import compliance_list

Stability = namedtuple("Stability", ["p", "q", "v", "theta", "pi"])
Disconnection_Model = namedtuple(
    "Disconnection_Model", ["auxload", "auxload_xfmr", "stepup_xfmrs", "gen_intline"]
)


class Validator:
    def __init__(self, validations: list, is_field_measurements: bool):
        self._time_cct = None
        self._generators_imax = {}
        self._disconnection_model = None
        self._setpoint_variation = 0.0
        self._validations = validations
        self._is_field_measurements = is_field_measurements

    def has_validations(self) -> bool:
        """Check if validator has defined validations.

        Returns
        -------
        bool
            True if the validator has validations.
        """
        return self._validations

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

    def validate(
        self,
        oc_name: str,
        results_path: Path,
        sim_output_path: str,
        event_params: dict,
        fs: float,
        curves: dict,
    ) -> dict:
        """Virtual method"""
        pass

    def get_measurement_names(self) -> list:
        """Virtual method"""
        pass
