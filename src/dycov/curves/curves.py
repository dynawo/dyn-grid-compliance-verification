#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from abc import abstractmethod
from pathlib import Path
from typing import Union

import pandas as pd

from dycov.configuration.cfg import config
from dycov.core.global_variables import CASE_SEPARATOR
from dycov.electrical.generator_variables import generator_variables
from dycov.model.parameters import DisconnectionModel, SimulationResult
from dycov.model.producer import Producer


def get_cfg_oc_name(pcs_name: str, bm_name: str, oc_name: str) -> str:
    """Generate a combined configuration operating condition name from PCS benchmark
    name and operating condition name.

    Parameters
    ----------
    pcs_name : str
        The PCS name.
    bm_name : str
        The benchmark name.
    oc_name : str
        The operating condition name.

    Returns
    -------
    str
        The combined configuration operating condition name.
    """
    pcs_bm_name = pcs_name + CASE_SEPARATOR + bm_name
    if pcs_bm_name == oc_name:
        return oc_name
    return pcs_bm_name + CASE_SEPARATOR + oc_name


class ProducerCurves:
    """
    ProducerCurves is responsible for managing and calculating various characteristics
    and values related to a producer's electrical generation unit. It provides methods
    to obtain unit characteristics, setpoint variations, and other relevant data.

    Args
    ----
    producer: Producer
        The producer object containing configuration and producer information.

    """

    def __init__(
        self,
        producer: Producer,
    ):
        self._producer = producer
        self._line_Xpu = 0.0
        self._s_nref = config.get_float("Dynawo", "s_nref", 100.0)

    def obtain_value(self, value_definition: str) -> Union[str, float]:
        """Calculate the final value from a definition.

        Parameters
        ----------
        value_definition: str
            Description of the required value

        Returns
        -------
        Union[str, float]
            Final value.
        """
        # Ensure the PmaxConsumption and PmaxInjection are treated as Pmax for consistency
        value_definition = (
            value_definition
            .replace("PmaxConsumption", "Pmax")
            .replace("PmaxInjection", "Pmax")
        )
        unit_characteristics = self.get_unit_characteristics()
        if "*" in value_definition:
            parts = value_definition.split("*")
            multiplier = float(parts[0])
            value = parts[1]
            return multiplier * unit_characteristics.get(value, 0.0)
        return unit_characteristics.get(value_definition, value_definition)

    def complete_unit_characteristics(self, line_Xpu: float) -> None:
        """Complete the parameters used as unit characteristics.

        Parameters
        ----------
        line_Xpu: float
            Line reactance in per unit.
        """
        self._line_Xpu = line_Xpu

    def get_unit_characteristics(self) -> dict[str, float]:
        """Get a set of unit characteristics.

        Returns
        -------
        dict[str, float]
            set of unit characteristics.
        """
        producer = self.get_producer()
        return {
            "Pmax": producer.p_max_pu,
            "Qmax": producer.q_max_pu,
            "Udim": self.get_generator_u_dim() / producer.u_nom,
            "Unom": producer.u_nom / producer.u_nom,
            "line_XPu": self._line_Xpu,
        }

    def get_snref(self) -> float:
        """Get the reference power (S_nref).

        Returns
        -------
        float
            Reference power (S_nref).
        """
        return self._s_nref

    def get_producer(self) -> Producer:
        """Get the producer instance.

        Returns
        -------
        Producer
            Producer instance.
        """
        return self._producer

    def get_generator_u_dim(self) -> float:
        """Get the Udim.

        Returns
        -------
        float
            Udim.
        """
        producer = self.get_producer()
        return generator_variables.get_generator_u_dim(producer.u_nom)

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
        if not setpoint_variation:
            return 0.0

        producer = self.get_producer()
        return float(self.obtain_value(str(setpoint_variation))) * self._s_nref / producer.s_nom

    @abstractmethod
    def get_solver(self) -> dict:
        """Get the solver.

        Returns
        -------
        dict
            Solver parameters.
        """
        pass

    @abstractmethod
    def get_generators_imax(self) -> dict:
        """Get the maximum current (Imax) for each generator.

        This method should be implemented by subclasses to return a dictionary
        where the keys are generator identifiers and the values are the maximum
        current values for those generators.

        Returns
        -------
        dict:
            Maximum continuous current by generator.
        """
        pass

    @abstractmethod
    def obtain_reference_curve(
        self,
        working_oc_dir: Path,
        producer_name: str,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        curves: Path,
    ) -> tuple[float, pd.DataFrame]:
        """Obtain the reference curves.

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
        curves: Path
            Reference curves path

        Returns
        -------
        float
            Instant of time when the event is triggered
        DataFrame
           Curves imported from the file
        """
        pass

    @abstractmethod
    def obtain_simulated_curve(
        self,
        working_oc_dir: Path,
        producer_name: str,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        reference_event_start_time: float,
    ) -> tuple[str, dict, SimulationResult, pd.DataFrame]:
        """Obtain the simulated curves.

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

        Returns
        -------
        str
            Simulation output dir
        dict
            Event parameters
        SimulationResult
            Information about the simulation result.
        DataFrame
           Simulation calculated curves
        """
        pass

    @abstractmethod
    def get_time_cct(
        self,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        fault_duration: float,
        bm_name: str,
        oc_name: str,
    ) -> float:
        """Calculate the critical clearing time (CCT) for a fault.

        Parameters
        ----------
        working_oc_dir: Path
            Temporal working path
        jobs_output_dir: Path
            Simulation output dir
        fault_duration: float
            Fault duration in seconds
        bm_name: str
            Benchmark name
        oc_name: str
            Operating Condition name

        Returns
        -------
        float
            The critical clearing time (CCT) for the fault.
        """
        pass

    @abstractmethod
    def get_voltage_dip(self) -> float | None:
        """Get the voltage dip.

        Returns
        -------
        float | None
            The voltage dip value.
        """
        pass

    @abstractmethod
    def get_disconnection_model(self) -> DisconnectionModel:
        """Get all equipment in the model that can be disconnected in the simulation.

        This method should be implemented by subclasses to return an instance
        of the DisconnectionModel class, which contains the equipment that can be
        disconnected.

        Returns
        -------
        DisconnectionModel
            Equipment that can be disconnected.
        """
        pass
