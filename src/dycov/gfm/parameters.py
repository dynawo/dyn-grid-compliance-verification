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
from typing import Optional, Tuple

import numpy as np

from dycov.configuration.cfg import config
from dycov.core.parameters import Parameters
from dycov.files import model_parameters
from dycov.gfm.producer import GFMProducer


class GFMParameters(Parameters):
    """
    Parameters to define the validation of a GFM model.
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
        """
        self._pcs_section = pcs_name
        self._bm_section = f"{pcs_name}.{bm_name}"
        self._oc_section = f"{pcs_name}.{bm_name}.{oc_name}"

    def is_valid(self) -> bool:
        """Checks if the execution of the tool is valid."""
        return self._producer.is_gfm()

    def is_emt(self) -> bool:
        """Checks if it is an EMT system."""
        return self._emt

    def get_calculator_name(self) -> str:
        """Gets the calculator name for a given PCS and benchmark."""
        return self.__get_value("calculator")

    def get_effective_reactance(self) -> float:
        """Gets the effective reactance (in pu)."""
        return float(self._producer._config.get("GFM Parameters", "Xeff"))

    def get_damping_constant(self) -> float:
        """Gets the damping constant from the producer."""
        return float(self._producer._config.get("GFM Parameters", "D"))

    def get_inertia_constant(self) -> float:
        """Gets the inertia constant from the producer (in s)."""
        return float(self._producer._config.get("GFM Parameters", "H"))

    def get_nominal_apparent_power(self) -> float:
        """Gets the nominal apparent power from the producer (in MVA)."""
        return float(self._producer._config.get("GFM Parameters", "Snom"))

    def get_nominal_voltage(self) -> float:
        """Gets the nominal voltage from the producer (in kV)."""
        return float(self._producer._config.get("DEFAULT", "Unom"))

    def get_initial_active_power(self) -> float:
        """Gets the initial active power (P0) from the configuration (in pu)."""
        p0_definition = self.__get_value("P0")
        p_max = self.get_max_active_power()
        return model_parameters.extract_defined_value(p0_definition, "Pmax", p_max, 1)

    def get_min_active_power(self) -> float:
        """Gets the minimum active power (PMin) from the configuration (in pu)."""
        return (
            float(self._producer._config.get("DEFAULT", "p_min_injection"))
            / self.get_nominal_apparent_power()
        )

    def get_max_active_power(self) -> float:
        """Gets the maximum active power (PMax) from the configuration (in pu)."""
        return (
            float(self._producer._config.get("DEFAULT", "p_max_injection"))
            / self.get_nominal_apparent_power()
        )

    def get_initial_reactive_power(self) -> float:
        """Gets the initial reactive power (Q0) from the configuration (in pu)."""
        q0_definition = self.__get_value("Q0")
        if "Qmin" in q0_definition:
            q_min = self.get_min_reactive_power()
            return model_parameters.extract_defined_value(q0_definition, "Qmin", q_min, 1)
        q_max = self.get_max_reactive_power()
        return model_parameters.extract_defined_value(q0_definition, "Qmax", q_max, 1)

    def get_min_reactive_power(self) -> float:
        """Gets the minimum reactive power (QMin) from the configuration (in pu)."""
        return (
            float(self._producer._config.get("DEFAULT", "q_min"))
            / self.get_nominal_apparent_power()
        )

    def get_max_reactive_power(self) -> float:
        """Gets the maximum reactive power (QMax) from the configuration (in pu)."""
        return (
            float(self._producer._config.get("DEFAULT", "q_max"))
            / self.get_nominal_apparent_power()
        )

    def get_initial_voltage(self) -> float:
        """Gets the initial voltage (U0)."""
        return self.__get_float_value("U0", 1)

    def get_grid_voltage(self) -> float:
        """Gets the grid voltage (Ugr)."""
        return self.__get_float_value("Ugr", 1)

    def get_time_to_90(self) -> float:
        """Gets the 'TimeTo90' parameter."""
        return self.__get_float_value("TimeTo90", 0.0)

    def get_time_for_tunnel(self) -> float:
        """Gets the 'TimeForTunnel' parameter."""
        return self.__get_float_value("TimeforTunnel", 0.0)

    def get_final_allowed_tunnel_pn(self) -> float:
        """Gets the 'FinalAllowedTunnelPn' parameter."""
        return self.__get_float_value("FinalAllowedTunnelPn", 0.0)

    def get_final_allowed_tunnel_variation(self) -> float:
        """Gets the 'FinalAllowedTunnelVariation' parameter."""
        return self.__get_float_value("FinalAllowedTunnelVariation", 0.0)

    def get_margin_low(self) -> float:
        """Gets the lower margin for envelopes."""
        return self.__get_float_value("MarginLow", 0.0)

    def get_margin_high(self) -> float:
        """Gets the upper margin for envelopes."""
        return self.__get_float_value("MarginHigh", 0.0)

    def get_pmax_mois_tunnel(self) -> float:
        """Gets the 'PmaxMOISTunnel' parameter."""
        return self.__get_float_value("PmaxMOISTunnel", 0.95)

    def get_pmin_mois_tunnel(self) -> float:
        """Gets the 'PminMOISTunnel' parameter."""
        return self.__get_float_value("PminMOISTunnel", 0.95)

    def get_min_ratio(self) -> float:
        """Gets the minimum ratio for parameter variations."""
        return self.__get_float_value("RatioMin", 1.0)

    def get_max_ratio(self) -> float:
        """Gets the maximum ratio for parameter variations."""
        return self.__get_float_value("RatioMax", 1.0)

    def get_base_angular_frequency(self) -> float:
        """Gets the base angular frequency ('Wb')."""
        return self.__get_float_value("Wb", 0.0)

    def get_delta_phase(self) -> float:
        """Gets the phase angle jump magnitude (in degrees)."""
        value_definition = self.__get_value("DeltaPhase")
        if "*" in value_definition:
            parts = value_definition.split("*")
            term1 = float(parts[0])
            delta_rad = term1 * (self.get_effective_reactance() + self.get_grid_reactance())
        else:
            delta_rad = float(value_definition)

        return delta_rad * 180 / np.pi

    def get_voltage_step_at_grid(self) -> float:
        """Gets the voltage step magnitude at the grid (in pu)."""
        value_definition = self.__get_value("VoltageStepAtGrid")
        if "*" in value_definition:
            parts = value_definition.split("*")
            term1 = float(parts[0])
            voltage_step = (
                term1 * (self.get_effective_reactance() + self.get_grid_reactance()) * 100
            )
        else:
            voltage_step = float(value_definition)

        return voltage_step

    def get_voltage_step_at_pdr(self) -> float:
        """Gets the voltage step at PDR (Point of Delivery) (in pu)."""
        return (
            self.get_voltage_step_at_grid()
            * self.get_effective_reactance()
            / (self.get_grid_reactance() + self.get_effective_reactance())
        )

    def get_delta_step(self) -> float:
        """Calculates the magnitude of the angle step at the PCC (in degrees)."""
        x_grid = self.get_grid_reactance()
        x_eff = self.get_effective_reactance()
        delta_theta_if = self.get_delta_phase()
        if (x_eff + x_grid) == 0:
            return 0.0
        delta_step = (x_eff / (x_eff + x_grid)) * delta_theta_if
        return delta_step

    def get_change_frequency(self) -> float:
        """Gets the rate of change of frequency (in pu/s)."""
        return self.__get_float_value("RoCoF", 0.0) / self._producer._f_nom

    def get_change_frequency_duration(self) -> float:
        """Gets the duration of the rate of change of frequency (in s)."""
        return self.__get_float_value("RoCoFDuration", 0.0)

    def get_initial_frequency(self) -> float:
        """Gets the initial frequency (in pu)."""
        return self.__get_float_value("Frequency0", 0.0) / self._producer._f_nom

    def get_t_expo_decrease(self) -> float:
        """Gets the exponential decrease time constant (in s)."""
        return self.__get_float_value("TimeExponentialDecrease", 0.0)

    def get_pll_time_constant(self) -> float:
        """Gets the PLL time constant (in s)."""
        return self.__get_float_value("Tpll", 0.0)

    def get_grid_reactance(self) -> float:
        """Gets the grid reactance (in pu)."""
        return 1 / self.get_scr()

    def get_scr(self) -> float:
        """Gets the Short Circuit Ratio (SCR)."""
        scr = self.__get_value("SCR")
        if scr:
            try:
                return float(scr)
            except Exception:
                return config.get_float("GFM", scr, 0.0)
        return config.get_float("GFM", "SCRmax", 0.0)

    def get_initial_scr(self) -> float:
        """Gets the initial SCR for an SCR jump event."""
        return self.__get_float_value("SCRinitial", 0.0)

    def get_final_scr(self) -> float:
        """Gets the final SCR for an SCR jump event."""
        return self.__get_float_value("SCRfinal", 0.0)

    def __get_value(self, option: str) -> str:
        """Helper to retrieve a string value from hierarchical config sections."""
        if config.has_option(self._oc_section, option):
            return config.get_value(self._oc_section, option)
        elif config.has_option(self._bm_section, option):
            return config.get_value(self._bm_section, option)
        elif config.has_option(self._pcs_section, option):
            return config.get_value(self._pcs_section, option)
        return config.get_value("DEFAULT", option)

    def __get_float_value(self, option: str, default_value: float) -> float:
        """Helper to retrieve a float value from hierarchical config sections."""
        if config.has_option(self._oc_section, option):
            return config.get_float(self._oc_section, option, default_value)
        elif config.has_option(self._bm_section, option):
            return config.get_float(self._bm_section, option, default_value)
        elif config.has_option(self._pcs_section, option):
            return config.get_float(self._pcs_section, option, default_value)
        return config.get_float("DEFAULT", option, default_value)

    # -------------------------------------------------------------------------
    # NEW METHODS FOR HYBRID PARAMETER DETECTION
    # -------------------------------------------------------------------------

    def get_hybrid_parameters(self) -> Optional[Tuple[float, float, float, float]]:
        """
        Attempts to retrieve the hybrid parameters (Overdamped/Underdamped).

        Returns
        -------
        tuple[float, float, float, float] | None
            A tuple (D_Over, H_Over, D_Under, H_Under) if all exist,
            otherwise None.
        """
        d_over = self._get_optional_float("D_Overdamped")
        h_over = self._get_optional_float("H_Overdamped")
        d_under = self._get_optional_float("D_Underdamped")
        h_under = self._get_optional_float("H_Underdamped")

        if all(v is not None for v in [d_over, h_over, d_under, h_under]):
            return d_over, h_over, d_under, h_under
        return None

    def get_standard_parameters(self) -> Optional[Tuple[float, float]]:
        """
        Attempts to retrieve the standard parameters D and H.

        Returns
        -------
        tuple[float, float] | None
            A tuple (D, H) if both exist, otherwise None.
        """
        d = self._get_optional_float("D")
        h = self._get_optional_float("H")

        if d is not None and h is not None:
            return d, h
        return None

    def _get_optional_float(self, option: str) -> Optional[float]:
        """
        Helper to retrieve a float value without a default fallback.
        It checks the hierarchical config first, then the producer specific config.

        Parameters
        ----------
        option : str
            The configuration key to look for.

        Returns
        -------
        float | None
            The float value if found, None otherwise.
        """
        # 1. Try getting from the standard hierarchical config (Sim parameters)
        val_str = self.__get_value(option)

        # __get_value might return an empty string or default if not found in hierarchy
        if val_str:
            try:
                return float(val_str)
            except ValueError:
                pass  # Proceed to check producer config

        # 2. Try getting directly from the Producer.ini (Physical parameters)
        if self._producer._config.has_option("GFM Parameters", option):
            try:
                return float(self._producer._config.get("GFM Parameters", option))
            except ValueError:
                return None

        return None

    def should_save_all_envelopes(self) -> bool:
        """
        Checks if 'save_all_envelopes' is set to True in the Producer.ini.

        Returns
        -------
        bool
            True if the option exists and is 'true' (case insensitive), False otherwise.
        """
        if self._producer._config.has_option("GFM Parameters", "save_all_envelopes"):
            try:
                return self._producer._config.getboolean("GFM Parameters", "save_all_envelopes")
            except ValueError:
                return False
        return False
