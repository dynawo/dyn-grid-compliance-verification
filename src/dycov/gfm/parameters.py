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
    Configuration entity used to define and manage the validation parameters
    of a Grid Forming (GFM) model.

    This class inherits from the foundational Parameters class, extending it
    to retrieve, compute, and serve specific electrical, mechanical, and
    simulation parameters required for GFM calculations.
    """

    def __init__(
        self,
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
        producer_ini : Path
            The directory path containing the Producer Model INI configuration files.
        selected_pcs : str
            The string identifier of the specific Power Conversion System (PCS) designated for
            validation.
        output_dir : Path
            The user-specified target directory path where simulation results will be exported.
        only_dtr : bool
            A flag indicating whether to validate the model exclusively using the PCS defined in
            the DTR.
        emt : bool
            A flag defining whether the Electro-Magnetic Transients (EMT) simulation engine is
            enabled.
        """
        super().__init__(None, selected_pcs, output_dir, only_dtr)
        self._emt = emt
        self._producer = GFMProducer(producer_ini)

    def set_section(self, pcs_name: str, bm_name: str, oc_name: str) -> None:
        """
        Updates the internal hierarchical section identifiers utilized for parameter retrieval.

        Parameters
        ----------
        pcs_name : str
            The identifier name of the specific Power Conversion System.
        bm_name : str
            The identifier name of the specific Benchmark scenario.
        oc_name : str
            The identifier name of the specific Operating Condition.
        """
        self._pcs_section = pcs_name
        self._bm_section = f"{pcs_name}.{bm_name}"
        self._oc_section = f"{pcs_name}.{bm_name}.{oc_name}"

    def is_valid(self) -> bool:
        """
        Validates whether the initialized producer configuration supports GFM calculations.

        Returns
        -------
        bool
            True if the internal producer configuration is structurally valid for GFM analysis.
        """
        return self._producer.is_gfm()

    def is_emt(self) -> bool:
        """
        Checks if the configuration mandates an Electro-Magnetic Transients (EMT) simulation.

        Returns
        -------
        bool
            True if the EMT simulation engine is enabled, False otherwise.
        """
        return self._emt

    def get_calculator_name(self) -> str:
        """
        Retrieves the designated calculator strategy name for the current PCS and benchmark.

        Returns
        -------
        str
            The string identifier of the mathematical calculator (e.g., 'PhaseJump', 'RoCoF').
        """
        return self.__get_value("calculator")

    def get_effective_reactance(self) -> float:
        """
        Retrieves the effective reactance of the system.

        Returns
        -------
        float
            The effective reactance value, measured in per-unit (pu).
        """
        return float(self._producer._config.get("GFM Parameters", "Xeff"))

    def get_damping_constant(self) -> float:
        """
        Retrieves the system damping constant value derived from the producer configuration.

        Returns
        -------
        float
            The designated damping constant (D).
        """
        return float(self._producer._config.get("GFM Parameters", "D"))

    def get_inertia_constant(self) -> float:
        """
        Retrieves the system inertia constant value derived from the producer configuration.

        Returns
        -------
        float
            The designated inertia constant (H), measured in seconds (s).
        """
        return float(self._producer._config.get("GFM Parameters", "H"))

    def get_nominal_apparent_power(self) -> float:
        """
        Retrieves the nominal apparent power capacity of the system.

        Returns
        -------
        float
            The nominal apparent power value, measured in Megavolt-Amperes (MVA).
        """
        return float(self._producer._config.get("GFM Parameters", "Snom"))

    def get_nominal_voltage(self) -> float:
        """
        Retrieves the nominal operational voltage of the system.

        Returns
        -------
        float
            The nominal voltage value, measured in kilovolts (kV).
        """
        return float(self._producer._config.get("DEFAULT", "Unom"))

    def get_initial_active_power(self) -> float:
        """
        Retrieves the initial steady-state active power (P0).

        Returns
        -------
        float
            The computed initial active power, measured in per-unit (pu).
        """
        p0_definition = self.__get_value("P0")
        p_max = self.get_max_active_power()
        return model_parameters.extract_defined_value(p0_definition, "Pmax", p_max, 1)

    def get_min_active_power(self) -> float:
        """
        Retrieves the absolute minimum active power capability limit (PMin).

        Returns
        -------
        float
            The minimum active power constraint, measured in per-unit (pu).
        """
        return (
            float(self._producer._config.get("DEFAULT", "p_min_injection"))
            / self.get_nominal_apparent_power()
        )

    def get_max_active_power(self) -> float:
        """
        Retrieves the absolute maximum active power capability limit (PMax).

        Returns
        -------
        float
            The maximum active power constraint, measured in per-unit (pu).
        """
        return (
            float(self._producer._config.get("DEFAULT", "p_max_injection"))
            / self.get_nominal_apparent_power()
        )

    def get_initial_reactive_power(self) -> float:
        """
        Retrieves the initial steady-state reactive power (Q0).

        Returns
        -------
        float
            The computed initial reactive power, measured in per-unit (pu).
        """
        q0_definition = self.__get_value("Q0")
        if "Qmin" in q0_definition:
            q_min = self.get_min_reactive_power()
            return model_parameters.extract_defined_value(q0_definition, "Qmin", q_min, 1)
        q_max = self.get_max_reactive_power()
        return model_parameters.extract_defined_value(q0_definition, "Qmax", q_max, 1)

    def get_min_reactive_power(self) -> float:
        """
        Retrieves the absolute minimum reactive power capability limit (QMin).

        Returns
        -------
        float
            The minimum reactive power constraint, measured in per-unit (pu).
        """
        return (
            float(self._producer._config.get("DEFAULT", "q_min"))
            / self.get_nominal_apparent_power()
        )

    def get_max_reactive_power(self) -> float:
        """
        Retrieves the absolute maximum reactive power capability limit (QMax).

        Returns
        -------
        float
            The maximum reactive power constraint, measured in per-unit (pu).
        """
        return (
            float(self._producer._config.get("DEFAULT", "q_max"))
            / self.get_nominal_apparent_power()
        )

    def get_initial_voltage(self) -> float:
        """
        Retrieves the initial baseline voltage (U0).

        Returns
        -------
        float
            The initial voltage value.
        """
        return self.__get_float_value("U0", 1)

    def get_grid_voltage(self) -> float:
        """
        Retrieves the operational grid voltage (Ugr).

        Returns
        -------
        float
            The defined grid voltage value.
        """
        return self.__get_float_value("Ugr", 1)

    def get_time_to_90(self) -> float:
        """
        Retrieves the 'TimeTo90' transient response parameter.

        Returns
        -------
        float
            The designated time required to reach 90% of the steady-state response, in seconds.
        """
        return self.__get_float_value("TimeTo90", 0.0)

    def get_time_for_tunnel(self) -> float:
        """
        Retrieves the 'TimeForTunnel' parameter defining dynamic tolerance progression.

        Returns
        -------
        float
            The evaluated time parameter structuring the tunnel logic.
        """
        return self.__get_float_value("TimeforTunnel", 0.0)

    def get_final_allowed_tunnel_pn(self) -> float:
        """
        Retrieves the 'FinalAllowedTunnelPn' parameter.

        Returns
        -------
        float
            The static boundary allowed corresponding to the nominal power proportion.
        """
        return self.__get_float_value("FinalAllowedTunnelPn", 0.0)

    def get_final_allowed_tunnel_variation(self) -> float:
        """
        Retrieves the 'FinalAllowedTunnelVariation' parameter.

        Returns
        -------
        float
            The permitted tolerance variation margin evaluating dynamic bounds.
        """
        return self.__get_float_value("FinalAllowedTunnelVariation", 0.0)

    def get_margin_low(self) -> float:
        """
        Retrieves the scaling factor defining the lower margin for envelope generation.

        Returns
        -------
        float
            The specific multiplier structuring lower constraint boundaries.
        """
        return self.__get_float_value("MarginLow", 0.0)

    def get_margin_high(self) -> float:
        """
        Retrieves the scaling factor defining the upper margin for envelope generation.

        Returns
        -------
        float
            The specific multiplier structuring upper constraint boundaries.
        """
        return self.__get_float_value("MarginHigh", 0.0)

    def get_pmax_mois_tunnel(self) -> float:
        """
        Retrieves the 'PmaxMOISTunnel' parameter, anchoring absolute upper clipping limits.

        Returns
        -------
        float
            The defined ceiling limitation threshold. Defaults to 0.95 if omitted.
        """
        return self.__get_float_value("PmaxMOISTunnel", 0.95)

    def get_pmin_mois_tunnel(self) -> float:
        """
        Retrieves the 'PminMOISTunnel' parameter, anchoring absolute lower clipping limits.

        Returns
        -------
        float
            The defined floor limitation threshold. Defaults to 0.95 if omitted.
        """
        return self.__get_float_value("PminMOISTunnel", 0.95)

    def get_min_ratio(self) -> float:
        """
        Retrieves the designated minimum proportional multiplier mapping parameter variations.

        Returns
        -------
        float
            The established minimum variation ratio.
        """
        return self.__get_float_value("RatioMin", 1.0)

    def get_max_ratio(self) -> float:
        """
        Retrieves the designated maximum proportional multiplier mapping parameter variations.

        Returns
        -------
        float
            The established maximum variation ratio.
        """
        return self.__get_float_value("RatioMax", 1.0)

    def get_base_angular_frequency(self) -> float:
        """
        Retrieves the base angular frequency benchmark ('Wb') of the operational system.

        Returns
        -------
        float
            The base angular frequency value.
        """
        return self.__get_float_value("Wb", 0.0)

    def get_delta_phase(self) -> float:
        """
        Calculates and retrieves the phase angle jump magnitude explicitly.

        Supports dynamic evaluation if the configuration value is formulated
        as a mathematical expression mapping reactances.

        Returns
        -------
        float
            The final evaluated phase jump magnitude, converted and measured in degrees.
        """
        value_definition = self.__get_value("DeltaPhase")
        if "*" in value_definition:
            parts = value_definition.split("*")
            term1 = float(parts[0])
            # Process derived expression combining reactances
            delta_rad = term1 * (self.get_effective_reactance() + self.get_grid_reactance())
        else:
            delta_rad = float(value_definition)

        return delta_rad * 180 / np.pi

    def get_voltage_step_at_grid(self) -> float:
        """
        Calculates and retrieves the defined voltage step magnitude explicitly at the grid.

        Returns
        -------
        float
            The evaluated voltage step magnitude, measured in per-unit (pu).
        """
        value_definition = self.__get_value("VoltageStepAtGrid")
        if "*" in value_definition:
            parts = value_definition.split("*")
            term1 = float(parts[0])
            # Synthesize voltage step deriving through system impedance
            voltage_step = (
                term1 * (self.get_effective_reactance() + self.get_grid_reactance()) * 100
            )
        else:
            voltage_step = float(value_definition)

        return voltage_step

    def get_voltage_step_at_pdr(self) -> float:
        """
        Calculates the voltage step magnitude specifically projected at the
        Point of Delivery (PDR).

        Returns
        -------
        float
            The derived step magnitude at the PDR, measured in per-unit (pu).
        """
        return (
            self.get_voltage_step_at_grid()
            * self.get_effective_reactance()
            / (self.get_grid_reactance() + self.get_effective_reactance())
        )

    def get_delta_step(self) -> float:
        """
        Calculates the operational magnitude of the angle step mapping onto the
        Point of Common Coupling (PCC).

        Returns
        -------
        float
            The explicit derived angle step deviation, measured in degrees.
        """
        x_grid = self.get_grid_reactance()
        x_eff = self.get_effective_reactance()
        delta_theta_if = self.get_delta_phase()
        if (x_eff + x_grid) == 0:
            return 0.0
        delta_step = (x_eff / (x_eff + x_grid)) * delta_theta_if
        return delta_step

    def get_change_frequency(self) -> float:
        """
        Retrieves the Rate of Change of Frequency (RoCoF) parameter.

        Returns
        -------
        float
            The normalized frequency variation rate, measured in per-unit per second (pu/s).
        """
        return self.__get_float_value("RoCoF", 0.0) / self._producer._f_nom

    def get_change_frequency_duration(self) -> float:
        """
        Retrieves the defined operational duration of the RoCoF event.

        Returns
        -------
        float
            The designated temporal duration mapping the frequency shift, in seconds (s).
        """
        return self.__get_float_value("RoCoFDuration", 0.0)

    def get_initial_frequency(self) -> float:
        """
        Retrieves the normalized initial steady-state frequency benchmark.

        Returns
        -------
        float
            The initial system frequency baseline, measured in per-unit (pu).
        """
        return self.__get_float_value("Frequency0", 0.0) / self._producer._f_nom

    def get_t_expo_decrease(self) -> float:
        """
        Retrieves the designated exponential decay time constant governing transient profiles.

        Returns
        -------
        float
            The evaluated exponential decrease time parameter, measured in seconds (s).
        """
        return self.__get_float_value("TimeExponentialDecrease", 0.0)

    def get_pll_time_constant(self) -> float:
        """
        Retrieves the operational Phase-Locked Loop (PLL) time constant.

        Returns
        -------
        float
            The internal PLL time evaluation constant, measured in seconds (s).
        """
        return self.__get_float_value("Tpll", 0.0)

    def get_grid_reactance(self) -> float:
        """
        Derives the absolute grid reactance directly from the defined Short Circuit Ratio (SCR).

        Returns
        -------
        float
            The resultant grid reactance, measured in per-unit (pu).
        """
        return 1 / self.get_scr()

    def get_scr(self) -> float:
        """
        Retrieves the Short Circuit Ratio (SCR) parameter defined for the simulation.

        Returns
        -------
        float
            The evaluated static Short Circuit Ratio value.
        """
        scr = self.__get_value("SCR")
        if scr:
            try:
                return float(scr)
            except Exception:
                return config.get_float("GFM", scr, 0.0)
        return config.get_float("GFM", "SCRmax", 0.0)

    def get_initial_scr(self) -> float:
        """
        Retrieves the starting Short Circuit Ratio configured prior to an SCR jump event.

        Returns
        -------
        float
            The pre-event benchmark SCR value.
        """
        return self.__get_float_value("SCRinitial", 0.0)

    def get_final_scr(self) -> float:
        """
        Retrieves the terminal Short Circuit Ratio achieved following an SCR jump event.

        Returns
        -------
        float
            The post-event stabilized SCR value.
        """
        return self.__get_float_value("SCRfinal", 0.0)

    def __get_value(self, option: str) -> str:
        """Private helper traversing the hierarchical configuration framework to retrieve a string
        value.

        Parameters
        ----------
        option : str
            The specific key identifier indicating the target configuration parameter.

        Returns
        -------
        str
            The retrieved configuration string resolving through the highest precedence level.
        """
        if config.has_option(self._oc_section, option):
            return config.get_value(self._oc_section, option)
        elif config.has_option(self._bm_section, option):
            return config.get_value(self._bm_section, option)
        elif config.has_option(self._pcs_section, option):
            return config.get_value(self._pcs_section, option)
        return config.get_value("DEFAULT", option)

    def __get_float_value(self, option: str, default_value: float) -> float:
        """Private helper traversing the hierarchical configuration framework to retrieve a float
        value.

        Parameters
        ----------
        option : str
            The specific key identifier indicating the target configuration parameter.
        default_value : float
            The fallback baseline value deployed if the key is not explicitly defined.

        Returns
        -------
        float
            The parsed floating-point configuration value resolving through the highest precedence
            level.
        """
        if config.has_option(self._oc_section, option):
            return config.get_float(self._oc_section, option, default_value)
        elif config.has_option(self._bm_section, option):
            return config.get_float(self._bm_section, option, default_value)
        elif config.has_option(self._pcs_section, option):
            return config.get_float(self._pcs_section, option, default_value)
        return config.get_float("DEFAULT", option, default_value)

    def get_hybrid_parameters(self) -> Optional[Tuple[float, float, float, float]]:
        """
        Evaluates the configuration to retrieve a set of hybrid operational parameters
        mapping both Overdamped and Underdamped structural constants.

        Returns
        -------
        Optional[Tuple[float, float, float, float]]
            A comprehensive structural tuple mapping (D_Over, H_Over, D_Under, H_Under)
            if the specific configurations are completely defined, otherwise None.
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
        Evaluates the configuration to retrieve standard, non-hybrid parameters D and H.

        Returns
        -------
        Optional[Tuple[float, float]]
            A structural tuple mapping standard (D, H) variables if both are adequately
            defined, otherwise None.
        """
        d = self._get_optional_float("D")
        h = self._get_optional_float("H")

        if d is not None and h is not None:
            return d, h
        return None

    def _get_optional_float(self, option: str) -> Optional[float]:
        """
        Protected helper deploying dual-level hierarchy validation to extract float configurations.

        It interrogates the primary simulation parameter hierarchy first, before establishing
        fallback verification against the base physical producer definitions.

        Parameters
        ----------
        option : str
            The explicit string key referencing the target configuration flag.

        Returns
        -------
        Optional[float]
            The successfully parsed floating-point definition if located, otherwise None.
        """
        val_str = self.__get_value(option)

        # __get_value might return an empty string or default if not found in hierarchy
        if val_str:
            try:
                return float(val_str)
            except ValueError:
                pass  # Fallthrough to verify alternative source configuration

        if self._producer._config.has_option("GFM Parameters", option):
            try:
                return float(self._producer._config.get("GFM Parameters", option))
            except ValueError:
                return None

        return None

    def should_save_all_envelopes(self) -> bool:
        """
        Interrogates the base Producer INI framework to determine if extended
        data serialization for all intermediate operational envelopes is enabled.

        Returns
        -------
        bool
            True strictly if 'save_all_envelopes' evaluates to 'true' in the configuration.
        """
        if self._producer._config.has_option("GFM Parameters", "save_all_envelopes"):
            try:
                return self._producer._config.getboolean("GFM Parameters", "save_all_envelopes")
            except ValueError:
                return False
        return False

    def get_emt_initial_delay(self) -> float:
        """
        Retrieves the requisite initial delay specifically mapped for EMT simulation frameworks.

        In the absence of an explicit INI definition, it automatically reverts to utilizing
        the systemic baseline constant.

        Returns
        -------
        float
            The evaluated EMT initial delay parameter, measured in seconds (s).
        """
        if self._producer._config.has_option("GFM Parameters", "emt_initial_delay"):
            try:
                return float(self._producer._config.get("GFM Parameters", "emt_initial_delay"))
            except ValueError:
                pass

        from dycov.gfm import constants

        return constants.EMT_FINAL_DELAY_S
