#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
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
    """Configuration entity to define and manage GFM model validation parameters."""

    def __init__(
        self,
        producer_ini: Path,
        selected_pcs: str,
        output_dir: Path,
        only_dtr: bool,
        emt: bool,
    ) -> None:
        """Initializes the GFMParameters configuration instance.

        Parameters
        ----------
        producer_ini : Path
            Directory path containing the Producer Model INI files.
        selected_pcs : str
            Identifier of the specific Power Conversion System (PCS) for validation.
        output_dir : Path
            Target directory path where simulation results will be exported.
        only_dtr : bool
            Flag to validate the model exclusively using the PCS defined in the DTR.
        emt : bool
            Flag defining whether the Electro-Magnetic Transients (EMT) engine is enabled.
        """
        super().__init__(None, selected_pcs, output_dir, only_dtr)
        self._emt = emt
        self._producer = GFMProducer(producer_ini)

    def set_section(self, pcs_name: str, bm_name: str, oc_name: str) -> None:
        """Updates internal hierarchical section identifiers for parameter retrieval."""
        self._pcs_section = pcs_name
        self._bm_section = f"{pcs_name}.{bm_name}"
        self._oc_section = f"{pcs_name}.{bm_name}.{oc_name}"

    def is_valid(self) -> bool:
        """Validates if the producer configuration supports GFM calculations."""
        return self._producer.is_gfm()

    def is_emt(self) -> bool:
        """Checks if the configuration mandates an EMT simulation."""
        return self._emt

    def get_calculator_name(self) -> str:
        """Retrieves the designated calculator strategy name."""
        return self.__get_value("calculator")

    def get_effective_reactance(self) -> float:
        """Retrieves the effective reactance (Xeff) in per-unit (pu)."""
        return float(self._producer._config.get("GFM Parameters", "Xeff"))

    def get_damping_constant(self) -> float:
        """Retrieves the system damping constant (D)."""
        return float(self._producer._config.get("GFM Parameters", "D"))

    def get_inertia_constant(self) -> float:
        """Retrieves the system inertia constant (H) in seconds."""
        return float(self._producer._config.get("GFM Parameters", "H"))

    def get_nominal_apparent_power(self) -> float:
        """Retrieves the nominal apparent power capacity in MVA."""
        return float(self._producer._config.get("GFM Parameters", "Snom"))

    def get_nominal_voltage(self) -> float:
        """Retrieves the nominal operational voltage in kV."""
        return float(self._producer._config.get("DEFAULT", "Unom"))

    def get_initial_active_power(self) -> float:
        """Retrieves the initial steady-state active power (P0) in pu."""
        p0_definition = self.__get_value("P0")
        p_max = self.get_max_active_power()
        return model_parameters.extract_defined_value(p0_definition, "Pmax", p_max, 1)

    def get_min_active_power(self) -> float:
        """Retrieves the absolute minimum active power capability limit (PMin) in pu."""
        return (
            float(self._producer._config.get("DEFAULT", "p_min_injection"))
            / self.get_nominal_apparent_power()
        )

    def get_max_active_power(self) -> float:
        """Retrieves the absolute maximum active power capability limit (PMax) in pu."""
        return (
            float(self._producer._config.get("DEFAULT", "p_max_injection"))
            / self.get_nominal_apparent_power()
        )

    def get_initial_reactive_power(self) -> float:
        """Retrieves the initial steady-state reactive power (Q0) in pu."""
        q0_definition = self.__get_value("Q0")
        if "Qmin" in q0_definition:
            q_min = self.get_min_reactive_power()
            return model_parameters.extract_defined_value(q0_definition, "Qmin", q_min, 1)
        q_max = self.get_max_reactive_power()
        return model_parameters.extract_defined_value(q0_definition, "Qmax", q_max, 1)

    def get_min_reactive_power(self) -> float:
        """Retrieves the absolute minimum reactive power capability limit (QMin) in pu."""
        return (
            float(self._producer._config.get("DEFAULT", "q_min"))
            / self.get_nominal_apparent_power()
        )

    def get_max_reactive_power(self) -> float:
        """Retrieves the absolute maximum reactive power capability limit (QMax) in pu."""
        return (
            float(self._producer._config.get("DEFAULT", "q_max"))
            / self.get_nominal_apparent_power()
        )

    def get_initial_voltage(self) -> float:
        """Retrieves the initial baseline voltage (U0)."""
        return self.__get_float_value("U0", 1)

    def get_grid_voltage(self) -> float:
        """Retrieves the operational grid voltage (Ugr)."""
        return self.__get_float_value("Ugr", 1)

    def get_time_to_90(self) -> float:
        """Retrieves the time required to reach 90% of the steady-state response in seconds."""
        return self.__get_float_value("TimeTo90", 0.0)

    def get_time_for_tunnel(self) -> float:
        """Retrieves the 'TimeForTunnel' parameter structuring the tunnel logic."""
        return self.__get_float_value("TimeforTunnel", 0.0)

    def get_final_allowed_tunnel_pn(self) -> float:
        """Retrieves the static boundary allowed corresponding to the nominal power proportion."""
        return self.__get_float_value("FinalAllowedTunnelPn", 0.0)

    def get_final_allowed_tunnel_variation(self) -> float:
        """Retrieves the permitted tolerance variation margin evaluating dynamic bounds."""
        return self.__get_float_value("FinalAllowedTunnelVariation", 0.0)

    def get_margin_low(self) -> float:
        """Retrieves the scaling factor defining the lower margin for envelope generation."""
        return self.__get_float_value("MarginLow", 0.0)

    def get_margin_high(self) -> float:
        """Retrieves the scaling factor defining the upper margin for envelope generation."""
        return self.__get_float_value("MarginHigh", 0.0)

    def get_pmax_mois_tunnel(self) -> float:
        """Retrieves the upper clipping limit threshold (defaults to 0.95)."""
        return self.__get_float_value("PmaxMOISTunnel", 0.95)

    def get_pmin_mois_tunnel(self) -> float:
        """Retrieves the lower clipping limit threshold (defaults to 0.95)."""
        return self.__get_float_value("PminMOISTunnel", 0.95)

    def get_min_ratio(self) -> float:
        """Retrieves the minimum proportional multiplier mapping parameter variations."""
        return self.__get_float_value("RatioMin", 1.0)

    def get_max_ratio(self) -> float:
        """Retrieves the maximum proportional multiplier mapping parameter variations."""
        return self.__get_float_value("RatioMax", 1.0)

    def get_base_angular_frequency(self) -> float:
        """Retrieves the base angular frequency benchmark ('Wb')."""
        return self.__get_float_value("Wb", 0.0)

    def get_delta_phase(self) -> float:
        """Calculates and retrieves the phase angle jump magnitude in degrees."""
        value_definition = self.__get_value("DeltaPhase")
        if "*" in value_definition:
            parts = value_definition.split("*")
            term1 = float(parts[0])
            delta_rad = term1 * (self.get_effective_reactance() + self.get_grid_reactance())
        else:
            delta_rad = float(value_definition)
        return delta_rad * 180 / np.pi

    def get_voltage_step_at_grid(self) -> float:
        """Calculates and retrieves the defined voltage step magnitude at the grid in pu."""
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
        """Calculates the voltage step magnitude at the Point of Delivery (PDR) in pu."""
        return (
            self.get_voltage_step_at_grid()
            * self.get_effective_reactance()
            / (self.get_grid_reactance() + self.get_effective_reactance())
        )

    def get_delta_step(self) -> float:
        """Calculates the angle step deviation mapped onto the Point of Common Coupling in degrees."""
        x_grid = self.get_grid_reactance()
        x_eff = self.get_effective_reactance()
        delta_theta_if = self.get_delta_phase()
        if (x_eff + x_grid) == 0:
            return 0.0
        return (x_eff / (x_eff + x_grid)) * delta_theta_if

    def get_change_frequency(self) -> float:
        """Retrieves the Rate of Change of Frequency (RoCoF) in pu/s."""
        return self.__get_float_value("RoCoF", 0.0) / self._producer._f_nom

    def get_change_frequency_duration(self) -> float:
        """Retrieves the duration of the RoCoF event in seconds."""
        return self.__get_float_value("RoCoFDuration", 0.0)

    def get_initial_frequency(self) -> float:
        """Retrieves the normalized initial steady-state frequency in pu."""
        return self.__get_float_value("Frequency0", 0.0) / self._producer._f_nom

    def get_t_expo_decrease(self) -> float:
        """Retrieves the exponential decay time constant governing transient profiles in seconds."""
        return self.__get_float_value("TimeExponentialDecrease", 0.0)

    def get_pll_time_constant(self) -> float:
        """Retrieves the Phase-Locked Loop (PLL) time evaluation constant in seconds."""
        return self.__get_float_value("Tpll", 0.0)

    def get_grid_reactance(self) -> float:
        """Derives the absolute grid reactance directly from the Short Circuit Ratio (SCR) in pu."""
        return 1 / self.get_scr()

    def get_scr(self) -> float:
        """Retrieves the Short Circuit Ratio (SCR) parameter."""
        scr = self.__get_value("SCR")
        if scr:
            try:
                return float(scr)
            except Exception:
                return config.get_float("GFM", scr, 0.0)
        return config.get_float("GFM", "SCRmax", 0.0)

    def get_initial_scr(self) -> float:
        """Retrieves the pre-event benchmark SCR value."""
        return self.__get_float_value("SCRinitial", 0.0)

    def get_final_scr(self) -> float:
        """Retrieves the post-event stabilized SCR value."""
        return self.__get_float_value("SCRfinal", 0.0)

    def __get_value(self, option: str) -> str:
        """Traverses the hierarchical configuration framework to retrieve a string value."""
        if config.has_option(self._oc_section, option):
            return config.get_value(self._oc_section, option)
        elif config.has_option(self._bm_section, option):
            return config.get_value(self._bm_section, option)
        elif config.has_option(self._pcs_section, option):
            return config.get_value(self._pcs_section, option)
        return config.get_value("DEFAULT", option)

    def __get_float_value(self, option: str, default_value: float) -> float:
        """Traverses the hierarchical configuration framework to retrieve a float value."""
        if config.has_option(self._oc_section, option):
            return config.get_float(self._oc_section, option, default_value)
        elif config.has_option(self._bm_section, option):
            return config.get_float(self._bm_section, option, default_value)
        elif config.has_option(self._pcs_section, option):
            return config.get_float(self._pcs_section, option, default_value)
        return config.get_float("DEFAULT", option, default_value)

    def get_hybrid_parameters(self) -> Optional[Tuple[float, float, float, float]]:
        """Retrieves hybrid parameters (D_Over, H_Over, D_Under, H_Under) if defined."""
        d_over = self._get_optional_float("D_Overdamped")
        h_over = self._get_optional_float("H_Overdamped")
        d_under = self._get_optional_float("D_Underdamped")
        h_under = self._get_optional_float("H_Underdamped")

        if all(v is not None for v in [d_over, h_over, d_under, h_under]):
            return d_over, h_over, d_under, h_under
        return None

    def get_standard_parameters(self) -> Optional[Tuple[float, float]]:
        """Retrieves standard, non-hybrid parameters D and H."""
        d = self._get_optional_float("D")
        h = self._get_optional_float("H")

        if d is not None and h is not None:
            return d, h
        return None

    def _get_optional_float(self, option: str) -> Optional[float]:
        """Extracts float configurations using dual-level hierarchy validation."""
        val_str = self.__get_value(option)
        if val_str:
            try:
                return float(val_str)
            except ValueError:
                pass

        if self._producer._config.has_option("GFM Parameters", option):
            try:
                return float(self._producer._config.get("GFM Parameters", option))
            except ValueError:
                return None
        return None

    def should_save_all_envelopes(self) -> bool:
        """Determines if extended serialization for intermediate envelopes is enabled."""
        if self._producer._config.has_option("GFM Parameters", "save_all_envelopes"):
            try:
                return self._producer._config.getboolean("GFM Parameters", "save_all_envelopes")
            except ValueError:
                return False
        return False

    def get_emt_delay(self) -> float:
        """Retrieves the initial delay mapped for EMT simulation frameworks."""
        if self._producer._config.has_option("GFM Parameters", "emt_delay"):
            try:
                return float(self._producer._config.get("GFM Parameters", "emt_delay"))
            except ValueError:
                pass

        from dycov.gfm import constants

        return constants.EMT_DELAY_S
