#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import configparser
import re
from collections import namedtuple
from pathlib import Path
from typing import Optional

import numpy as np

from dycov.configuration.cfg import config
from dycov.core.parameters import Parameters
from dycov.files import model_parameters
from dycov.gfm.producer import CSVProducer

# Named tuple to store Grid Forming (GFM) parameters. This structure
# provides immutable and descriptive access to configuration values.
GFM_Params = namedtuple(
    "GFM_Params",
    [
        "EMT",  # Electro-Magnetic Transients simulation flag
        "RatioMin",  # Minimum ratio for parameter variations
        "RatioMax",  # Maximum ratio for parameter variations
        "P0",  # Initial active power (per unit - pu)
        "Q0",  # Initial reactive power (per unit - pu)
        "delta_theta",  # Phase angle jump magnitude (degrees)
        "voltage_step",  # Voltage step magnitude (per unit - pu)
        "SCR",  # Short Circuit Ratio, indicating grid strength
        "Wb",  # Base angular frequency (radians/second)
        "Ucv",  # Converter RMS voltage (pu)
        "Ugr",  # Grid RMS voltage (pu)
        "MarginHigh",  # Upper margin for power envelopes
        "MarginLow",  # Lower margin for power envelopes
        "FinalAllowedTunnelVariation",
        "FinalAllowedTunnelPn",
        "TimeTo90",  # Time to 90%
        "TimeForTunnel",  # Time for tunnel
        "PMax",  # Maximum allowed active power (pu)
        "PMin",  # Minimum allowed active power (pu)
        "QMax",  # Maximum allowed reactive power (pu)
        "QMin",  # Minimum allowed reactive power (pu)
    ],
)


class GFMParameters(Parameters):
    """
    Parameters to define the validation of a model.
    Inherits from the base Parameters class.
    """

    def __init__(
        self,
        launcher_dwo: Path,
        producer_csv: Path,
        selected_pcs: str,
        output_dir: Path,
        only_dtr: bool,
        emt: bool,
    ) -> None:
        """
        Initializes the GFMParameters class.

        Parameters
        ----------
        launcher_dwo : Path
            Path to the Dynawo launcher.
        producer_csv : Path
            Directory containing the Producer Model CSV files.
        selected_pcs : str
            Name of the individual PCS to validate.
        output_dir : Path
            User-specified output directory for results.
        only_dtr : bool
            Option to validate a model using only the PCS
            defined in the DTR.
        emt : bool
            Option to set the EMT (Electro-Magnetic Transients)
            simulation engine.
        """
        super().__init__(launcher_dwo, selected_pcs, output_dir, only_dtr)
        self._emt = emt

        self._producer = CSVProducer(producer_csv)

    def is_valid(self) -> bool:
        """
        Checks if the execution of the tool is valid.
        For GFM, the tool must have the CSV model of the user.

        Returns
        -------
        bool
            True if it is a valid execution (i.e., producer is GFM),
            False otherwise.
        """
        return self._producer.is_gfm()

    def get_calculator_name(self, pcs_name: str, bm_name: str) -> str:
        """
        Gets the calculator name for a given PCS and benchmark.

        Parameters
        ----------
        pcs_name : str
            The name of the PCS (Power Conversion System).
        bm_name : str
            The name of the benchmark.

        Returns
        -------
        str
            The name of the calculator to be used.
        """
        section = f"{pcs_name}.{bm_name}"
        return config.get_value(section, "calculator")

    def get_effective_reactance(self, pcs_name: str, bm_name: str, oc_name: str) -> float:
        """
        Gets the effective reactance.

        Parameters
        ----------
        pcs_name : str
            The name of the PCS.
        bm_name : str
            The name of the benchmark.
        oc_name : str
            The name of the operating condition.

        Returns
        -------
        float
            The effective reactance value.
        """
        section = f"{pcs_name}.{bm_name}"
        x_eff = self.__get_effective_reactance(section)
        if x_eff:
            return x_eff

        return self._producer.get_effective_reactance()

    def get_damping_constant(self) -> float:
        """
        Gets the damping constant from the producer.

        Returns
        -------
        float
            The damping constant value.
        """
        return self._producer.get_damping_constant()

    def get_inertia_constant(self) -> float:
        """
        Gets the inertia constant from the producer.

        Returns
        -------
        float
            The inertia constant value.
        """
        return self._producer.get_inertia_constant()

    def pcs_configuration(self, pcs_name: str, bm_name: str, oc_name: str) -> GFM_Params:
        """
        Retrieves the GFM parameters for a specific PCS, benchmark,
        and operating condition.

        Parameters
        ----------
        pcs_name : str
            The name of the PCS.
        bm_name : str
            The name of the benchmark.
        oc_name : str
            The name of the operating condition.

        Returns
        -------
        GFM_Params
            A named tuple containing the GFM parameters for the specified
            configuration.
        """
        default_section = "DEFAULT"
        producer_config = self.__read_producer_ini()

        pmax = (
            float(producer_config.get(default_section, "p_max_injection")) / self._producer._s_nref
        )
        qmax = float(producer_config.get(default_section, "q_max")) / self._producer._s_nref
        qmin = float(producer_config.get(default_section, "q_min")) / self._producer._s_nref

        pcs_section = pcs_name
        bm_section = f"{pcs_name}.{bm_name}"
        oc_section = f"{pcs_name}.{bm_name}.{oc_name}"

        return GFM_Params(
            EMT=self._emt,
            RatioMin=self.__get_min_ratio(pcs_section),
            RatioMax=self.__get_max_ratio(pcs_section),
            P0=self.__get_initial_active_power(oc_section, pmax),
            Q0=self.__get_initial_reactive_power(oc_section, qmax, qmin),
            delta_theta=self.__get_delta_phase(bm_section),
            voltage_step=self.__get_voltage_step(bm_section),
            SCR=self.__get_scr(bm_section),
            Wb=self.__get_base_angular_frequency(pcs_section),
            Ucv=self.__get_initial_voltage(oc_section),
            Ugr=self.__get_grid_voltage(pcs_section),
            MarginHigh=self.__get_margin_high(pcs_section),
            MarginLow=self.__get_margin_low(pcs_section),
            FinalAllowedTunnelVariation=self.__get_final_allowed_tunnel_variation(pcs_section),
            FinalAllowedTunnelPn=self.__get_final_allowed_tunnel_pn(pcs_section),
            TimeTo90=self.__get_time_to_90(pcs_section),
            TimeForTunnel=self.__get_time_for_tunnel(pcs_section),
            PMax=pmax,
            PMin=-float(producer_config.get(default_section, "p_max_injection"))
            / self._producer._s_nref,
            QMax=qmax,
            QMin=float(producer_config.get(default_section, "q_min")) / self._producer._s_nref,
        )

    def __read_producer_ini(self) -> configparser.ConfigParser:
        """
        Reads the producer INI file.

        Returns
        -------
        configparser.ConfigParser
            The parsed configuration object containing producer settings.
        """

        def __get_producer_ini(path: Path, pattern: re.Pattern) -> Path:
            """
            Helper function to get the producer INI file path.
            It iterates through the directory to find a file matching the pattern.

            Parameters
            ----------
            path : Path
                The directory path to search in.
            pattern : re.Pattern
                The regex pattern to match the filename.

            Returns
            -------
            Path
                The full path to the producer INI file.

            Raises
            ------
            FileNotFoundError
                If the producer INI file is not found in the specified path.
            """
            for file in path.resolve().iterdir():
                if pattern.match(str(file)):
                    return path.resolve() / file
            raise FileNotFoundError("Producer INI file not found.")

        pattern_ini = re.compile(r".*.Producer.[iI][nN][iI]")
        producer_ini = __get_producer_ini(self._producer.get_producer_path(), pattern_ini)

        default_section = "DEFAULT"
        # Read the content of the INI file, prepending a default section header
        # to ensure it's parsed correctly by ConfigParser.
        with open(producer_ini, "r") as f:
            producer_ini_txt = "[" + default_section + "]\n" + f.read()

        producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        producer_config.read_string(producer_ini_txt)
        return producer_config

    def __get_initial_active_power(self, section: str, p_max: float) -> float:
        """
        Gets the initial active power (P0) from the configuration.

        Parameters
        ----------
        section : str
            The configuration section (e.g., "PCS.Benchmark.OperatingCondition").
        p_max : float
            Maximum active power, used if P0 is defined relative to Pmax.

        Returns
        -------
        float
            Initial active power value.
        """
        p0_definition = config.get_value(section, "P0")
        return model_parameters.extract_defined_value(p0_definition, "Pmax", p_max, 1)

    def __get_initial_reactive_power(self, section: str, q_max: float, q_min: float) -> float:
        """
        Gets the initial reactive power (Q0) from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.
        q_max : float
            Maximum reactive power, used for relative definitions.
        q_min : float
            Minimum reactive power, used for relative definitions.

        Returns
        -------
        float
            Initial reactive power value.
        """
        q0_definition = config.get_value(section, "Q0")
        # If "Qmin" is in the definition, extract relative to Qmin.
        if "Qmin" in q0_definition:
            return model_parameters.extract_defined_value(q0_definition, "Qmin", q_min, 1)
        return model_parameters.extract_defined_value(q0_definition, "Qmax", q_max, 1)

    def __get_initial_voltage(self, section: str) -> float:
        """
        Gets the initial voltage (U0) from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            Initial voltage value.
        """
        return config.get_float(section, "U0", 1)

    def __get_grid_voltage(self, section: str) -> float:
        """
        Gets the grid voltage (Ugr) from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            Grid voltage value.
        """
        return config.get_float(section, "Ugr", 1)

    def __get_time_to_90(self, section: str) -> float:
        """
        Gets the 'TimeTo90' parameter from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            The 'TimeTo90' value, defaulting to 0.0 if not found.
        """
        return config.get_float(section, "TimeTo90", 0.0)

    def __get_time_for_tunnel(self, section: str) -> float:
        """
        Gets the 'TimeForTunnel' parameter from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            The 'TimeForTunnel' value, defaulting to 0.0 if not found.
        """
        return config.get_float(section, "TimeforTunnel", 0.0)

    def __get_final_allowed_tunnel_pn(self, section: str) -> float:
        """
        Gets the 'FinalAllowedTunnelPn' parameter from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            The 'FinalAllowedTunnelPn' value, defaulting to 0.0 if not found.
        """
        return config.get_float(section, "FinalAllowedTunnelPn", 0.0)

    def __get_final_allowed_tunnel_variation(self, section: str) -> float:
        """
        Gets the 'FinalAllowedTunnelVariation' parameter from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            The 'FinalAllowedTunnelVariation' value, defaulting to 0.0
            if not found.
        """
        return config.get_float(section, "FinalAllowedTunnelVariation", 0.0)

    def __get_margin_low(self, section: str) -> float:
        """
        Gets the lower margin for power envelopes ('MarginLow')
        from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            The 'MarginLow' value, defaulting to 0.0 if not found.
        """
        return config.get_float(section, "MarginLow", 0.0)

    def __get_margin_high(self, section: str) -> float:
        """
        Gets the upper margin for power envelopes ('MarginHigh')
        from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            The 'MarginHigh' value, defaulting to 0.0 if not found.
        """
        return config.get_float(section, "MarginHigh", 0.0)

    def __get_min_ratio(self, section: str) -> float:
        """
        Gets the minimum ratio for parameter variations ('RatioMin')
        from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            The 'RatioMin' value, defaulting to 1.0 if not found.
        """
        return config.get_float(section, "RatioMin", 1.0)

    def __get_max_ratio(self, section: str) -> float:
        """
        Gets the maximum ratio for parameter variations ('RatioMax')
        from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            The 'RatioMax' value, defaulting to 1.0 if not found.
        """
        return config.get_float(section, "RatioMax", 1.0)

    def __get_base_angular_frequency(self, section: str) -> float:
        """
        Gets the base angular frequency ('Wb') from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            The 'Wb' value, defaulting to 0.0 if not found.
        """
        return config.get_float(section, "Wb", 0.0)

    def __get_delta_phase(self, section: str) -> float:
        """
        Gets the phase angle jump magnitude (in degrees).

        Currently, this parameter supports definitions like "±0.3*(Xeff+Xgrid)".

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            Phase angle jump magnitude in degrees.
        """
        if not config.has_key(section, "DeltaPhase"):
            return 0.0
        value_definition = config.get_value(section, "DeltaPhase")
        if "*" in value_definition:
            parts = value_definition.split("*")
            term1 = float(parts[0])

        delta_rad = term1 * (
            self.__get_effective_reactance(section) + self.__get_grid_reactance(section)
        )

        return delta_rad * 180 / np.pi

    def __get_voltage_step(self, section: str) -> float:
        """
        Gets the voltage step magnitude (in per unit - pu).

        Currently, this parameter supports definitions like "±0.15∗(Xeff+Xgrid)".

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            Voltage step magnitude in pu.
        """
        if not config.has_key(section, "VoltageStep"):
            return 0.0
        value_definition = config.get_value(section, "VoltageStep")
        if "*" in value_definition:
            parts = value_definition.split("*")
            term1 = float(parts[0])

        voltage_step = term1 * (
            self.__get_effective_reactance(section) + self.__get_grid_reactance(section)
        )

        return voltage_step * 100

    def __get_effective_reactance(self, section: str) -> Optional[float]:
        """
        Gets the effective reactance ('Xeff') from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        Optional[float]
            The effective reactance value, or None if the key is not found.
        """
        if config.has_key(section, "Xeff"):
            return config.get_float(section, "Xeff", 0.0)
        return None

    def __get_grid_reactance(self, section: str) -> float:
        """
        Gets the grid reactance.
        It is calculated as the inverse of the Short Circuit Ratio (SCR).

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            The calculated grid reactance.
        """
        return 1 / self.__get_scr(section)

    def __get_scr(self, section: str) -> float:
        """
        Gets the Short Circuit Ratio (SCR) from the configuration.

        Parameters
        ----------
        section : str
            The configuration section.

        Returns
        -------
        float
            The Short Circuit Ratio value.
        """
        return config.get_float(section, "SCR", 0.0)
