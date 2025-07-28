#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path

import numpy as np

from dycov.configuration.cfg import config
from dycov.core.parameters import Parameters
from dycov.files import model_parameters
from dycov.gfm.producer import GFMProducer


class GFMParameters(Parameters):
    """
    Parameters to define the validation of a model.
    Inherits from the base Parameters class.
    """

    def __init__(
        self,
        launcher_dwo: Path,
        producer_ini: Path,
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
        producer_ini : Path
            Directory containing the Producer Model ini files.
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

        self._producer = GFMProducer(producer_ini)

    def set_section(self, pcs_name: str, bm_name: str, oc_name: str) -> None:
        """
        Sets the GFM parameters for a specific PCS, benchmark,
        and operating condition.

        Parameters
        ----------
        pcs_name : str
            The name of the PCS.
        bm_name : str
            The name of the benchmark.
        oc_name : str
            The name of the operating condition.

        """
        self._pcs_section = pcs_name
        self._bm_section = f"{pcs_name}.{bm_name}"
        self._oc_section = f"{pcs_name}.{bm_name}.{oc_name}"

    def is_valid(self) -> bool:
        """
        Checks if the execution of the tool is valid.

        Returns
        -------
        bool
            True if it is a valid execution (i.e., producer is GFM),
            False otherwise.
        """
        return self._producer.is_gfm()

    def is_emt(self) -> bool:
        """
        Checks it is an EMT system.

        Returns
        -------
        bool
            True if it is an EMT system,
            False otherwise.
        """
        return self._emt

    def get_calculator_name(self) -> str:
        """
        Gets the calculator name for a given PCS and benchmark.

        Returns
        -------
        str
            The name of the calculator to be used.
        """
        return self.__get_value("calculator")

    def get_effective_reactance(self) -> float:
        """
        Gets the effective reactance.

        Returns
        -------
        float
            The effective reactance value.
        """
        x_eff = self.__get_float_value("Xeff", 0.0)
        if x_eff:
            return x_eff

        return float(self._producer._config.get("GFM Parameters", "Xeff"))

    def get_damping_constant(self) -> float:
        """
        Gets the damping constant from the producer.

        Returns
        -------
        float
            The damping constant value.
        """
        return float(self._producer._config.get("GFM Parameters", "D"))

    def get_inertia_constant(self) -> float:
        """
        Gets the inertia constant from the producer.

        Returns
        -------
        float
            The inertia constant value.
        """
        return float(self._producer._config.get("GFM Parameters", "H"))

    def get_nominal_apparent_power(self) -> float:
        """
        Gets the nominal apparent power from the producer.

        Returns
        -------
        float
            The nominal apparent power value.
        """
        return float(self._producer._config.get("GFM Parameters", "Snom"))

    def get_nominal_voltage(self) -> float:
        """
        Gets the nominal voltage from the producer.

        Returns
        -------
        float
            The nominal voltage value.
        """
        return float(self._producer._config.get("DEFAULT", "Unom"))

    def get_initial_active_power(self) -> float:
        """
        Gets the initial active power (P0) from the configuration.

        Returns
        -------
        float
            Initial active power value.
        """
        p0_definition = self.__get_value("P0")
        p_max = self.get_max_active_power()
        return model_parameters.extract_defined_value(p0_definition, "Pmax", p_max, 1)

    def get_min_active_power(self) -> float:
        """
        Gets the minimum active power (PMin) from the configuration.

        Returns
        -------
        float
            Minimum active power value.
        """
        return (
            float(self._producer._config.get("DEFAULT", "p_min_injection"))
            / self._producer._s_nref
        )

    def get_max_active_power(self) -> float:
        """
        Gets the maximum active power (PMax) from the configuration.

        Returns
        -------
        float
            Maximum active power value.
        """
        return (
            float(self._producer._config.get("DEFAULT", "p_max_injection"))
            / self._producer._s_nref
        )

    def get_initial_reactive_power(self) -> float:
        """
        Gets the initial reactive power (Q0) from the configuration.

        Returns
        -------
        float
            Initial reactive power value.
        """
        q0_definition = self.__get_value("Q0")
        # If "Qmin" is in the definition, extract relative to Qmin.
        if "Qmin" in q0_definition:
            q_min = self.get_min_reactive_power()
            return model_parameters.extract_defined_value(q0_definition, "Qmin", q_min, 1)
        q_max = self.get_max_reactive_power()
        return model_parameters.extract_defined_value(q0_definition, "Qmax", q_max, 1)

    def get_min_reactive_power(self) -> float:
        """
        Gets the minimum reactive power (QMin) from the configuration.

        Returns
        -------
        float
            Minimum reactive power value.
        """
        return float(self._producer._config.get("DEFAULT", "q_min")) / self._producer._s_nref

    def get_max_reactive_power(self) -> float:
        """
        Gets the maximum reactive power (QMax) from the configuration.

        Returns
        -------
        float
            Maximum reactive power value.
        """
        return float(self._producer._config.get("DEFAULT", "q_max")) / self._producer._s_nref

    def get_initial_voltage(self) -> float:
        """
        Gets the initial voltage (U0) from the configuration.

        Returns
        -------
        float
            Initial voltage value.
        """
        return self.__get_float_value("U0", 1)

    def get_grid_voltage(self) -> float:
        """
        Gets the grid voltage (Ugr) from the configuration.

        Returns
        -------
        float
            Grid voltage value.
        """
        return self.__get_float_value("Ugr", 1)

    def get_time_to_90(self) -> float:
        """
        Gets the 'TimeTo90' parameter from the configuration.

        Returns
        -------
        float
            The 'TimeTo90' value, defaulting to 0.0 if not found.
        """
        return self.__get_float_value("TimeTo90", 0.0)

    def get_time_for_tunnel(self) -> float:
        """
        Gets the 'TimeForTunnel' parameter from the configuration.

        Returns
        -------
        float
            The 'TimeForTunnel' value, defaulting to 0.0 if not found.
        """
        return self.__get_float_value("TimeforTunnel", 0.0)

    def get_final_allowed_tunnel_pn(self) -> float:
        """
        Gets the 'FinalAllowedTunnelPn' parameter from the configuration.

        Returns
        -------
        float
            The 'FinalAllowedTunnelPn' value, defaulting to 0.0 if not found.
        """
        return self.__get_float_value("FinalAllowedTunnelPn", 0.0)

    def get_final_allowed_tunnel_variation(self) -> float:
        """
        Gets the 'FinalAllowedTunnelVariation' parameter from the configuration.

        Returns
        -------
        float
            The 'FinalAllowedTunnelVariation' value, defaulting to 0.0
            if not found.
        """
        return self.__get_float_value("FinalAllowedTunnelVariation", 0.0)

    def get_margin_low(self) -> float:
        """
        Gets the lower margin for power envelopes ('MarginLow')
        from the configuration.

        Returns
        -------
        float
            The 'MarginLow' value, defaulting to 0.0 if not found.
        """
        return self.__get_float_value("MarginLow", 0.0)

    def get_margin_high(self) -> float:
        """
        Gets the upper margin for power envelopes ('MarginHigh')
        from the configuration.

        Returns
        -------
        float
            The 'MarginHigh' value, defaulting to 0.0 if not found.
        """
        return self.__get_float_value("MarginHigh", 0.0)

    def get_min_ratio(self) -> float:
        """
        Gets the minimum ratio for parameter variations ('RatioMin')
        from the configuration.

        Returns
        -------
        float
            The 'RatioMin' value, defaulting to 1.0 if not found.
        """
        return self.__get_float_value("RatioMin", 1.0)

    def get_max_ratio(self) -> float:
        """
        Gets the maximum ratio for parameter variations ('RatioMax')
        from the configuration.

        Returns
        -------
        float
            The 'RatioMax' value, defaulting to 1.0 if not found.
        """
        return self.__get_float_value("RatioMax", 1.0)

    def get_base_angular_frequency(self) -> float:
        """
        Gets the base angular frequency ('Wb') from the configuration.

        Returns
        -------
        float
            The 'Wb' value, defaulting to 0.0 if not found.
        """
        return self.__get_float_value("Wb", 0.0)

    def get_delta_phase(self) -> float:
        """
        Gets the phase angle jump magnitude (in degrees).

        Currently, this parameter supports definitions like "±0.3*(Xeff+Xgrid)".

        Returns
        -------
        float
            Phase angle jump magnitude in degrees.
        """
        value_definition = self.__get_value("DeltaPhase")
        if "*" in value_definition:
            parts = value_definition.split("*")
            term1 = float(parts[0])
            delta_rad = term1 * (self.get_effective_reactance() + self.get_grid_reactance())
        else:
            delta_rad = float(value_definition)

        return delta_rad * 180 / np.pi

    def get_voltage_step(self) -> float:
        """
        Gets the voltage step magnitude (in per unit - pu).

        Currently, this parameter supports definitions like "±0.15∗(Xeff+Xgrid)".

        Returns
        -------
        float
            Voltage step magnitude in pu.
        """
        value_definition = self.__get_value("VoltageStep")
        if "*" in value_definition:
            parts = value_definition.split("*")
            term1 = float(parts[0])
            voltage_step = (
                term1 * (self.get_effective_reactance() + self.get_grid_reactance()) * 100
            )
        else:
            voltage_step = float(value_definition)

        return voltage_step

    def get_change_frequency(self) -> float:
        """
        Gets the rate of change of frequency (in per unit - pu).

        Returns
        -------
        float
            rate of change of frequency in pu.
        """
        return self.__get_float_value("RoCoF", 0.0) / self._producer._f_nom

    def get_change_frequency_duration(self) -> float:
        """
        Gets the duration of the rate of change of frequency (s).

        Returns
        -------
        float
            duration of the rate of change of frequency in s.
        """
        return self.__get_float_value("RoCoFDuration", 0.0)

    def get_initial_frequency(self) -> float:
        """
        Gets the rate of change of frequency (in per unit - pu).

        Returns
        -------
        float
            rate of change of frequency in pu.
        """
        return self.__get_float_value("Phase0", 0.0) / self._producer._f_nom

    def get_t_expo_decrease(self) -> float:
        """
        Gets the exponential decrease time constant.

        Returns
        -------
        float
            The exponential decrease time constant.
        """
        return self.__get_float_value("TimeExponentialDecrease", 0.0)

    def get_pll_time_constant(self) -> float:
        """
        Gets the PLL time constant.

        Returns
        -------
        float
            The PLL time constant.
        """
        return self.__get_float_value("Tpll", 0.0)

    def get_grid_reactance(self) -> float:
        """
        Gets the grid reactance.
        It is calculated as the inverse of the Short Circuit Ratio (SCR).

        Returns
        -------
        float
            The calculated grid reactance.
        """
        return 1 / self.get_scr()

    def get_scr(self) -> float:
        """
        Gets the Short Circuit Ratio (SCR) from the configuration.

        Returns
        -------
        float
            The Short Circuit Ratio value.
        """
        return self.__get_float_value("SCR", 0.0)

    def get_initial_scr(self) -> float:
        """
        Gets the rate of change of frequency (in per unit - pu).

        Returns
        -------
        float
            rate of change of frequency in pu.
        """
        return self.__get_float_value("SCRinitial", 0.0)

    def get_final_scr(self) -> float:
        """
        Gets the rate of change of frequency (in per unit - pu).

        Returns
        -------
        float
            rate of change of frequency in pu.
        """
        return self.__get_float_value("SCRfinal", 0.0)

    def __get_value(self, option: str) -> float:
        if config.has_key(self._oc_section, option):
            return config.get_value(self._oc_section, option)
        elif config.has_key(self._bm_section, option):
            return config.get_value(self._bm_section, option)
        elif config.has_key(self._pcs_section, option):
            return config.get_value(self._pcs_section, option)
        return config.get_float("DEFAULT", option)

    def __get_float_value(self, option: str, default_value: float) -> float:
        if config.has_key(self._oc_section, option):
            return config.get_float(self._oc_section, option, default_value)
        elif config.has_key(self._bm_section, option):
            return config.get_float(self._bm_section, option, default_value)
        elif config.has_key(self._pcs_section, option):
            return config.get_float(self._pcs_section, option, default_value)
        return config.get_float("DEFAULT", option, default_value)
