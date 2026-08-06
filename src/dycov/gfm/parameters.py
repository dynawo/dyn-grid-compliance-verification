#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

from pathlib import Path
from typing import Optional, Tuple
import numpy as np
from dycov.configuration.cfg import config
from dycov.core.parameters import Parameters
from dycov.files import model_parameters
from dycov.gfm.producer import GFMProducer


class GFMParameters(Parameters):
    """
    Configuration entity used to define and manage the validation parameters
    of a Grid Forming (GFM) model.
    This class inherits from the foundational Parameters class, extending it
    to retrieve, compute, and serve specific electrical, mechanical, and
    simulation parameters required for GFM calculations.
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
        Initializes the GFMParameters configuration instance.

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
            Option to validate a model using only the PCS defined in the DTR.
        emt : bool
            Option to set the EMT (Electro-Magnetic Transients) simulation engine.
        """
        super().__init__(launcher_dwo, selected_pcs, output_dir, only_dtr)
        self._emt = emt
        self._producer = GFMProducer(producer_ini)

    def set_section(self, pcs_name: str, bm_name: str, oc_name: str) -> None:
        """Updates the internal hierarchical section identifiers utilized for parameter retrieval."""
        self._pcs_section = pcs_name
        self._bm_section = f"{pcs_name}.{bm_name}"
        self._oc_section = f"{pcs_name}.{bm_name}.{oc_name}"

    def is_valid(self) -> bool:
        """Validates whether the initialized producer configuration supports GFM calculations."""
        return self._producer.is_gfm()

    def is_emt(self) -> bool:
        """Checks if the configuration mandates an Electro-Magnetic Transients (EMT) simulation."""
        return self._emt

    def get_calculator_name(self) -> str:
        """Retrieves the designated calculator strategy name for the current PCS and benchmark."""
        return self.__get_value("calculator")

    # Safe retrieval of parameters using the public getter get_config()
    def get_effective_reactance(self) -> float:
        """Retrieves the effective reactance of the system."""
        return float(self._producer.get_config().get("GFM Parameters", "Xeff"))

    def get_damping_constant(self) -> float:
        """Retrieves the system damping constant value derived from the producer configuration."""
        return float(self._producer.get_config().get("GFM Parameters", "D"))

    def get_inertia_constant(self) -> float:
        """Retrieves the system inertia constant value derived from the producer configuration."""
        return float(self._producer.get_config().get("GFM Parameters", "H"))

    def get_nominal_apparent_power(self) -> float:
        """Retrieves the nominal apparent power capacity of the system."""
        return float(self._producer.get_config().get("GFM Parameters", "Snom"))

    def get_nominal_voltage(self) -> float:
        """Retrieves the nominal operational voltage of the system."""
        return float(self._producer.get_config().get("DEFAULT", "Unom"))

    def get_min_active_power(self) -> float:
        """Retrieves the absolute minimum active power capability limit (PMin)."""
        return (
            float(self._producer.get_config().get("DEFAULT", "p_min_injection"))
            / self.get_nominal_apparent_power()
        )

    def get_max_active_power(self) -> float:
        """Retrieves the absolute maximum active power capability limit (PMax)."""
        return (
            float(self._producer.get_config().get("DEFAULT", "p_max_injection"))
            / self.get_nominal_apparent_power()
        )

    def get_min_reactive_power(self) -> float:
        """Retrieves the absolute minimum reactive power capability limit (QMin)."""
        return (
            float(self._producer.get_config().get("DEFAULT", "q_min"))
            / self.get_nominal_apparent_power()
        )

    def get_max_reactive_power(self) -> float:
        """Retrieves the absolute maximum reactive power capability limit (QMax)."""
        return (
            float(self._producer.get_config().get("DEFAULT", "q_max"))
            / self.get_nominal_apparent_power()
        )

    def get_initial_active_power(self) -> float:
        """Retrieves the initial steady-state active power (P0)."""
        p0_definition = self.__get_value("P0")
        p_max = self.get_max_active_power()
        return model_parameters.extract_defined_value(p0_definition, "Pmax", p_max, 1)

    def get_initial_reactive_power(self) -> float:
        """Retrieves the initial steady-state reactive power (Q0)."""
        q0_definition = self.__get_value("Q0")
        if "Qmin" in q0_definition:
            q_min = self.get_min_reactive_power()
            return model_parameters.extract_defined_value(q0_definition, "Qmin", q_min, 1)
        q_max = self.get_max_reactive_power()
        return model_parameters.extract_defined_value(q0_definition, "Qmax", q_max, 1)

    def get_initial_voltage(self) -> float:
        """Retrieves the initial baseline voltage (U0)."""
        return self.__get_float_value("U0", 1)

    def get_grid_voltage(self) -> float:
        """Retrieves the operational grid voltage (Ugr)."""
        return self.__get_float_value("Ugr", 1)

    def get_time_to_90(self) -> float:
        """Retrieves the 'TimeTo90' transient response parameter."""
        return self.__get_float_value("TimeTo90", 0.0)

    def get_time_for_tunnel(self) -> float:
        """Retrieves the 'TimeForTunnel' parameter defining dynamic tolerance progression."""
        return self.__get_float_value("TimeforTunnel", 0.0)

    def get_final_allowed_tunnel_pn(self) -> float:
        """Retrieves the 'FinalAllowedTunnelPn' parameter."""
        return self.__get_float_value("FinalAllowedTunnelPn", 0.0)

    def get_final_allowed_tunnel_variation(self) -> float:
        """Retrieves the 'FinalAllowedTunnelVariation' parameter."""
        return self.__get_float_value("FinalAllowedTunnelVariation", 0.0)

    def get_margin_low(self) -> float:
        """Retrieves the scaling factor defining the lower margin for envelope generation."""
        return self.__get_float_value("MarginLow", 0.0)

    def get_margin_high(self) -> float:
        """Retrieves the scaling factor defining the upper margin for envelope generation."""
        return self.__get_float_value("MarginHigh", 0.0)

    def get_pmax_mois_tunnel(self) -> float:
        """Retrieves the 'PmaxMOISTunnel' parameter, anchoring absolute upper clipping limits."""
        return self.__get_float_value("PmaxMOISTunnel", 0.95)

    def get_pmin_mois_tunnel(self) -> float:
        """Retrieves the 'PminMOISTunnel' parameter, anchoring absolute lower clipping limits."""
        return self.__get_float_value("PminMOISTunnel", 0.95)

    def get_min_ratio(self) -> float:
        """Retrieves the designated minimum proportional multiplier mapping parameter variations."""
        return self.__get_float_value("RatioMin", 1.0)

    def get_max_ratio(self) -> float:
        """Retrieves the designated maximum proportional multiplier mapping parameter variations."""
        return self.__get_float_value("RatioMax", 1.0)

    def get_base_angular_frequency(self) -> float:
        """Retrieves the base angular frequency benchmark ('Wb') of the operational system."""
        return self.__get_float_value("Wb", 0.0)

    def get_delta_phase(self) -> float:
        """Calculates and retrieves the phase angle jump magnitude explicitly."""
        value_definition = self.__get_value("DeltaPhase")
        # Evaluate formula if delta phase is defined as an expression mapping reactances
        if "*" in value_definition:
            parts = value_definition.split("*")
            term1 = float(parts[0])
            delta_rad = term1 * (self.get_effective_reactance() + self.get_grid_reactance())
        else:
            delta_rad = float(value_definition)
        # Convert derived radians into degrees
        return delta_rad * 180 / np.pi

    def get_voltage_step_at_grid(self) -> float:
        """Calculates and retrieves the defined voltage step magnitude explicitly at the grid."""
        value_definition = self.__get_value("VoltageStepAtGrid")
        # Synthesize voltage step deriving through system impedance if formula is provided
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
        """Calculates the voltage step magnitude specifically projected at the Point of Delivery."""
        # Project step magnitude to the Point of Delivery
        return (
            self.get_voltage_step_at_grid()
            * self.get_effective_reactance()
            / (self.get_grid_reactance() + self.get_effective_reactance())
        )

    def get_delta_step(self) -> float:
        """Calculates the operational magnitude of the angle step mapping onto the PCC."""
        x_grid = self.get_grid_reactance()
        x_eff = self.get_effective_reactance()
        delta_theta_if = self.get_delta_phase()
        if (x_eff + x_grid) == 0:
            return 0.0
        return (x_eff / (x_eff + x_grid)) * delta_theta_if

    def get_change_frequency(self) -> float:
        """Retrieves the Rate of Change of Frequency (RoCoF) parameter."""
        return self.__get_float_value("RoCoF", 0.0) / getattr(self._producer, "_f_nom", 50.0)

    def get_change_frequency_duration(self) -> float:
        """Retrieves the defined operational duration of the RoCoF event."""
        return self.__get_float_value("RoCoFDuration", 0.0)

    def get_initial_frequency(self) -> float:
        """Retrieves the normalized initial steady-state frequency benchmark."""
        return self.__get_float_value("Frequency0", 0.0) / getattr(self._producer, "_f_nom", 50.0)

    def get_t_expo_decrease(self) -> float:
        """Retrieves the designated exponential decay time constant governing transient profiles."""
        return self.__get_float_value("TimeExponentialDecrease", 0.0)

    def get_pll_time_constant(self) -> float:
        """Retrieves the operational Phase-Locked Loop (PLL) time constant."""
        return self.__get_float_value("Tpll", 0.0)

    def get_grid_reactance(self) -> float:
        """Derives the absolute grid reactance directly from the defined Short Circuit Ratio (SCR)."""
        return 1 / self.get_scr()

    def get_scr(self) -> float:
        """Retrieves the Short Circuit Ratio (SCR) parameter defined for the simulation."""
        scr = self.__get_value("SCR")
        if scr:
            try:
                return float(scr)
            except Exception:
                return config.get_float("GFM", scr, 0.0)
        return config.get_float("GFM", "SCRmax", 0.0)

    def get_initial_scr(self) -> float:
        """Retrieves the starting Short Circuit Ratio configured prior to an SCR jump event."""
        return self.__get_float_value("SCRinitial", 0.0)

    def get_final_scr(self) -> float:
        """Retrieves the terminal Short Circuit Ratio achieved following an SCR jump event."""
        return self.__get_float_value("SCRfinal", 0.0)

    def __get_value(self, option: str) -> str:
        """Helper to retrieve a string value traversing the hierarchical config sections."""
        if config.has_option(self._oc_section, option):
            return config.get_value(self._oc_section, option)
        elif config.has_option(self._bm_section, option):
            return config.get_value(self._bm_section, option)
        elif config.has_option(self._pcs_section, option):
            return config.get_value(self._pcs_section, option)
        return config.get_value("DEFAULT", option)

    def __get_float_value(self, option: str, default_value: float) -> float:
        """Helper to retrieve a float value traversing the hierarchical config sections."""
        if config.has_option(self._oc_section, option):
            return config.get_float(self._oc_section, option, default_value)
        elif config.has_option(self._bm_section, option):
            return config.get_float(self._bm_section, option, default_value)
        elif config.has_option(self._pcs_section, option):
            return config.get_float(self._pcs_section, option, default_value)
        return config.get_float("DEFAULT", option, default_value)

    def get_hybrid_parameters(self) -> Optional[Tuple[float, float, float, float]]:
        """
        Attempts to retrieve the hybrid parameters (Overdamped/Underdamped).

        Returns
        -------
        Optional[Tuple[float, float, float, float]]
            A tuple (D_Over, H_Over, D_Under, H_Under) if all exist, otherwise None.
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
        Optional[Tuple[float, float]]
            A tuple (D, H) if both exist, otherwise None.
        """
        d = self._get_optional_float("D")
        h = self._get_optional_float("H")
        if d is not None and h is not None:
            return d, h
        return None

    def _get_optional_float(self, option: str) -> Optional[float]:
        """Helper to retrieve a float value without a default fallback."""
        val_str = self.__get_value(option)
        if val_str:
            try:
                return float(val_str)
            except ValueError:
                pass

        # Fallback to physical producer INI declarations
        if self._producer.get_config().has_option("GFM Parameters", option):
            try:
                return float(self._producer.get_config().get("GFM Parameters", option))
            except ValueError:
                return None
        return None

    def should_save_all_envelopes(self) -> bool:
        """Checks if 'save_all_envelopes' is set to True in the Producer.ini."""
        if self._producer.get_config().has_option("GFM Parameters", "save_all_envelopes"):
            try:
                return self._producer.get_config().getboolean(
                    "GFM Parameters", "save_all_envelopes"
                )
            except ValueError:
                return False
        return False

    def get_emt_initial_delay(self) -> float:
        """Gets the initial delay for EMT simulations from the producer configuration."""
        if self._producer.get_config().has_option("GFM Parameters", "emt_initial_delay"):
            try:
                return float(
                    self._producer.get_config().get("GFM Parameters", "emt_initial_delay")
                )
            except ValueError:
                pass

        from dycov.gfm import constants

        return constants.EMT_FINAL_DELAY_S
