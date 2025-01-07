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

from dgcv.configuration.cfg import config
from dgcv.core.execution_parameters import Parameters
from dgcv.core.global_variables import CASE_SEPARATOR
from dgcv.core.validator import Disconnection_Model
from dgcv.electrical.generator_variables import generator_variables
from dgcv.model.producer import Producer


def get_cfg_oc_name(pcs_bm_name: str, oc_name: str) -> str:
    if pcs_bm_name == oc_name:
        return oc_name
    return pcs_bm_name + CASE_SEPARATOR + oc_name


class ProducerCurves:
    def __init__(
        self,
        parameters: Parameters,
    ):
        self._producer = parameters.get_producer()
        self._line_Xpu = 0.0

    def obtain_value(self, value_definition: str) -> str:
        """Calculate the final value from a definition.

        Parameters
        ----------
        value_definition: str
            Description of the required value

        Returns
        -------
        str
            Final value.
        """
        if "*" in value_definition:
            multiplier = float(value_definition.split("*")[0])
            value = value_definition.split("*")[1]
            if value in self.get_unit_characteristics():
                return multiplier * self.get_unit_characteristics()[value]
            else:
                return 0.0
        elif value_definition in self.get_unit_characteristics():
            return self.get_unit_characteristics()[value_definition]
        return value_definition

    def get_unit_characteristics(self):
        """Get a set of unit characteristics.

        Returns
        -------
        dict
            set of unit characteristics.
        """
        return {
            "Pmax": self.get_producer().p_max_pu,
            "Qmax": self.get_producer().q_max_pu,
            "Udim": self.get_generator_u_dim() / self.get_producer().u_nom,
            "line_XPu": self._line_Xpu,
        }

    def get_producer(self) -> Producer:
        """Get the producer parameters.

        Returns
        -------
        Producer
            Producer parameters.
        """
        return self._producer

    def get_generator_u_dim(self) -> float:
        """Get the Udim.

        Returns
        -------
        float
            Udim.
        """
        return generator_variables.get_generator_u_dim(self.get_producer().u_nom)

    def get_setpoint_variation(self, pcs_bm_oc_name: str) -> float:
        """Get the setpoint variation.

        Parameters
        ----------
        pcs_bm_oc_name: str
            PCS.Benchmark.Operating Condition name

        Returns
        -------
        float
            Setpoint variation.
        """
        if config.get_boolean(pcs_bm_oc_name, "hiz_fault") or config.get_boolean(
            pcs_bm_oc_name, "bolted_fault"
        ):
            return 0.0

        config_key = pcs_bm_oc_name + ".Event"
        setpoint_variation = config.get_value(config_key, "setpoint_step_value")
        if setpoint_variation:
            return float(self.obtain_value(str(setpoint_variation)))

        return 0.0

    def get_generators_imax(self) -> dict:
        """Virtual method"""
        pass

    def obtain_reference_curve(
        self,
        working_oc_dir: Path,
        pcs_bm_name: str,
        curves: Path,
    ) -> tuple[float, pd.DataFrame]:
        """Virtual method"""
        pass

    def obtain_simulated_curve(
        self,
        working_oc_dir: Path,
        pcs_bm_name: str,
        bm_name: str,
        oc_name: str,
        reference_event_start_time: float,
    ) -> tuple[str, dict, int, bool, bool, pd.DataFrame]:
        """Virtual method"""
        pass

    def get_time_cct(
        self,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        fault_duration: float,
    ) -> float:
        """Virtual method"""
        pass

    def get_disconnection_model(self) -> Disconnection_Model:
        """Virtual method"""
        pass
