#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
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
        self, producer_ini: Path, selected_pcs: str, output_dir: Path, only_dtr: bool, emt: bool
    ) -> None:
        """
        Initializes the parameters object with producer configuration and runtime options.

        Parameters
        ----------
        producer_ini : Path
            Path to the producer's INI configuration file.
        selected_pcs : str
            The specific PCS to evaluate.
        output_dir : Path
            The directory path for saving outputs.
        only_dtr : bool
            Flag indicating if only DTR evaluation is required.
        emt : bool
            Flag to enable EMT simulation mode.
        """
        super().__init__(None, selected_pcs, output_dir, only_dtr)
        self._emt = emt
        self._producer = GFMProducer(producer_ini=producer_ini)

    def set_section(self, pcs_name: str, bm_name: str, oc_name: str) -> None:
        """
        Updates internal hierarchical section identifiers for parameter retrieval.

        Parameters
        ----------
        pcs_name : str
            Name of the PCS section.
        bm_name : str
            Name of the Base Model section.
        oc_name : str
            Name of the Operating Condition section.
        """
        # Establishes resolution order: Operating Condition -> Base Model -> PCS
        self._pcs_section = pcs_name
        self._bm_section = f"{pcs_name}.{bm_name}"
        self._oc_section = f"{pcs_name}.{bm_name}.{oc_name}"
        self._eval_sections = (self._oc_section, self._bm_section, self._pcs_section)

    def is_valid(self) -> bool:
        """
        Checks if the associated producer is a valid GFM model.

        Returns
        -------
        bool
            True if valid, False otherwise.
        """
        return self._producer.is_gfm()

    def is_emt(self) -> bool:
        """
        Returns whether EMT simulation mode is active.

        Returns
        -------
        bool
            True if EMT mode is enabled.
        """
        return self._emt

    def get_calculator_name(self) -> str:
        """
        Retrieves the name of the calculator to be used.

        Returns
        -------
        str
            The calculator identifier string.
        """
        return self.__get_value(option="calculator")

    def get_effective_reactance(self) -> float:
        """
        Retrieves the effective reactance (Xeff).

        Returns
        -------
        float
            The effective reactance value in pu.
        """
        return float(self._producer.get_config().get("GFM Parameters", "Xeff"))

    def get_damping_constant(self) -> float:
        """
        Retrieves the damping constant (D).

        Returns
        -------
        float
            The damping constant.
        """
        return float(self._producer.get_config().get("GFM Parameters", "D"))

    def get_inertia_constant(self) -> float:
        """
        Retrieves the inertia constant (H).

        Returns
        -------
        float
            The inertia constant in seconds.
        """
        return float(self._producer.get_config().get("GFM Parameters", "H"))

    def get_nominal_apparent_power(self) -> float:
        """
        Retrieves the nominal apparent power (Snom).

        Returns
        -------
        float
            The nominal apparent power.
        """
        return float(self._producer.get_config().get("GFM Parameters", "Snom"))

    def get_nominal_voltage(self) -> float:
        """
        Retrieves the nominal voltage (Unom).

        Returns
        -------
        float
            The nominal voltage.
        """
        return float(self._producer._config.get("DEFAULT", "Unom"))

    def get_initial_active_power(self) -> float:
        """
        Calculates and retrieves the initial active power (P0).

        Returns
        -------
        float
            The initial active power in pu.
        """
        p0_definition = self.__get_value("P0")
        return model_parameters.extract_defined_value(
            p0_definition, "Pmax", self.get_max_active_power(), 1
        )

    def get_min_active_power(self) -> float:
        """
        Retrieves the minimum active power injection.

        Returns
        -------
        float
            The minimum active power in pu.
        """
        return (
            float(self._producer.get_config().get("DEFAULT", "p_min_injection"))
            / self.get_nominal_apparent_power()
        )

    def get_max_active_power(self) -> float:
        """
        Retrieves the maximum active power injection.

        Returns
        -------
        float
            The maximum active power in pu.
        """
        return (
            float(self._producer.get_config().get("DEFAULT", "p_max_injection"))
            / self.get_nominal_apparent_power()
        )

    def get_initial_reactive_power(self) -> float:
        """
        Calculates and retrieves the initial reactive power (Q0).

        Returns
        -------
        float
            The initial reactive power in pu.
        """
        q0_definition = self.__get_value("Q0")
        if "Qmin" in q0_definition:
            return model_parameters.extract_defined_value(
                q0_definition, "Qmin", self.get_min_reactive_power(), 1
            )
        return model_parameters.extract_defined_value(
            q0_definition, "Qmax", self.get_max_reactive_power(), 1
        )

    def get_min_reactive_power(self) -> float:
        """
        Retrieves the minimum reactive power.

        Returns
        -------
        float
            The minimum reactive power in pu.
        """
        return (
            float(self._producer.get_config().get("DEFAULT", "q_min"))
            / self.get_nominal_apparent_power()
        )

    def get_max_reactive_power(self) -> float:
        """
        Retrieves the maximum reactive power.

        Returns
        -------
        float
            The maximum reactive power in pu.
        """
        return (
            float(self._producer.get_config().get("DEFAULT", "q_max"))
            / self.get_nominal_apparent_power()
        )

    def get_initial_active_power(self) -> float:
        """
        Retrieves the initial voltage (U0).

        Returns
        -------
        float
            The initial voltage in pu.
        """
        p0_definition = self.__get_value(option="P0")
        p_max = self.get_max_active_power()
        # Corregido a argumentos posicionales
        return model_parameters.extract_defined_value(p0_definition, "Pmax", p_max, 1)

    def get_initial_reactive_power(self) -> float:
        """
        Returns
        -------
        float
        """
        q0_definition = self.__get_value(option="Q0")
        if "Qmin" in q0_definition:
            q_min = self.get_min_reactive_power()
            # Corregido a argumentos posicionales
            return model_parameters.extract_defined_value(q0_definition, "Qmin", q_min, 1)
        q_max = self.get_max_reactive_power()
        # Corregido a argumentos posicionales
        return model_parameters.extract_defined_value(q0_definition, "Qmax", q_max, 1)

    def get_initial_voltage(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="U0", default_value=1.0)

    def get_grid_voltage(self) -> float:
        """
        Retrieves the grid voltage (Ugr).

        Returns
        -------
        float
            The grid voltage in pu.
        """
        return self.__get_float_value(option="Ugr", default_value=1.0)

    def get_time_to_90(self) -> float:
        """
        Retrieves the time to reach 90% of the steady-state response.

        Returns
        -------
        float
            The time in seconds.
        """
        return self.__get_float_value(option="TimeTo90", default_value=0.0)

    def get_time_for_tunnel(self) -> float:
        """
        Retrieves the time constant for the margin tunnel decay.

        Returns
        -------
        float
            The time constant in seconds.
        """
        return self.__get_float_value(option="TimeforTunnel", default_value=0.0)

    def get_final_allowed_tunnel_pn(self) -> float:
        """
        Retrieves the final allowed margin tunnel in absolute nominal power.

        Returns
        -------
        float
            The allowed tunnel margin in pu.
        """
        return self.__get_float_value(option="FinalAllowedTunnelPn", default_value=0.0)

    def get_final_allowed_tunnel_variation(self) -> float:
        """
        Retrieves the final allowed margin tunnel relative to the signal variation.

        Returns
        -------
        float
            The allowed variation ratio.
        """
        return self.__get_float_value(option="FinalAllowedTunnelVariation", default_value=0.0)

    def get_margin_low(self) -> float:
        """
        Retrieves the lower envelope margin multiplier.

        Returns
        -------
        float
            The lower margin ratio.
        """
        return self.__get_float_value(option="MarginLow", default_value=0.0)

    def get_margin_high(self) -> float:
        """
        Retrieves the upper envelope margin multiplier.

        Returns
        -------
        float
            The upper margin ratio.
        """
        return self.__get_float_value(option="MarginHigh", default_value=0.0)

    def get_pmax_mois_tunnel(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="PmaxMOISTunnel", default_value=0.95)

    def get_pmin_mois_tunnel(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="PminMOISTunnel", default_value=0.95)

    def get_pmax_mois_tunnel(self) -> float:
        """
        Retrieves the maximum power limit for the MOIS tunnel.

        Returns
        -------
        float
            The maximum power limit in pu.
        """
        return self.__get_float_value("PmaxMOISTunnel", 0.95)

    def get_pmin_mois_tunnel(self) -> float:
        """
        Retrieves the minimum power limit for the MOIS tunnel.

        Returns
        -------
        float
            The minimum power limit in pu.
        """
        return self.__get_float_value("PminMOISTunnel", 0.95)

    def get_min_ratio(self) -> float:
        """
        Retrieves the minimum parameter variation ratio.

        Returns
        -------
        float
            The minimum ratio.
        """
        return self.__get_float_value(option="RatioMin", default_value=1.0)

    def get_max_ratio(self) -> float:
        """
        Retrieves the maximum parameter variation ratio.

        Returns
        -------
        float
            The maximum ratio.
        """
        return self.__get_float_value(option="RatioMax", default_value=1.0)

    def get_base_angular_frequency(self) -> float:
        """
        Retrieves the base angular frequency (Wb).

        Returns
        -------
        float
            The base angular frequency in rad/s.
        """
        return self.__get_float_value(option="Wb", default_value=0.0)

    def get_delta_phase(self) -> float:
        """
        Calculates and retrieves the phase jump delta.

        Returns
        -------
        float
            The phase jump delta in degrees.
        """
        value_definition = self.__get_value("DeltaPhase")

        # Support dynamic calculation if delta phase relies on total reactance multiplication
        if "*" in value_definition:
            term1 = float(value_definition.split("*")[0])
            delta_rad = term1 * (self.get_effective_reactance() + self.get_grid_reactance())
        else:
            delta_rad = float(value_definition)
        return delta_rad * 180 / np.pi

    def get_voltage_step_at_grid(self) -> float:
        """
        Calculates and retrieves the voltage step at the grid side.

        Returns
        -------
        float
            The voltage step at the grid in percentage.
        """
        value_definition = self.__get_value(option="VoltageStepAtGrid")
        if "*" in value_definition:
            term1 = float(value_definition.split("*")[0])
            return term1 * (self.get_effective_reactance() + self.get_grid_reactance()) * 100
        return float(value_definition)

    def get_voltage_step_at_pdr(self) -> float:
        """
        Calculates and retrieves the voltage step at the point of delivery.

        Returns
        -------
        float
            The voltage step at PDR in percentage.
        """
        x_eff = self.get_effective_reactance()
        x_grid = self.get_grid_reactance()
        return self.get_voltage_step_at_grid() * x_eff / (x_grid + x_eff)

    def get_delta_step(self) -> float:
        """
        Calculates the angle step based on system reactances.

        Returns
        -------
        float
            The calculated angle step in degrees.
        """
        x_grid = self.get_grid_reactance()
        x_eff = self.get_effective_reactance()
        if (x_eff + x_grid) == 0:
            return 0.0
        return (x_eff / (x_eff + x_grid)) * self.get_delta_phase()

    def get_change_frequency(self) -> float:
        """
        Retrieves the Rate of Change of Frequency (RoCoF).

        Returns
        -------
        float
            The normalized RoCoF value.
        """
        return self.__get_float_value(option="RoCoF", default_value=0.0) / getattr(
            self._producer, "_f_nom", 50.0
        )

    def get_change_frequency_duration(self) -> float:
        """
        Retrieves the duration of the RoCoF event.

        Returns
        -------
        float
            The RoCoF duration in seconds.
        """
        return self.__get_float_value(option="RoCoFDuration", default_value=0.0)

    def get_initial_frequency(self) -> float:
        """
        Retrieves the initial system frequency.

        Returns
        -------
        float
            The normalized initial frequency.
        """
        return self.__get_float_value(option="Frequency0", default_value=0.0) / getattr(
            self._producer, "_f_nom", 50.0
        )

    def get_t_expo_decrease(self) -> float:
        """
        Retrieves the time constant for exponential decrease.

        Returns
        -------
        float
            The exponential decrease time constant in seconds.
        """
        return self.__get_float_value(option="TimeExponentialDecrease", default_value=0.0)

    def get_pll_time_constant(self) -> float:
        """
        Retrieves the PLL time constant (Tpll).

        Returns
        -------
        float
            The PLL time constant in seconds.
        """
        return self.__get_float_value(option="Tpll", default_value=0.0)

    def get_grid_reactance(self) -> float:
        """
        Calculates and retrieves the grid reactance based on SCR.

        Returns
        -------
        float
            The grid reactance in pu.
        """
        return 1 / self.get_scr()

    def get_scr(self) -> float:
        """
        Retrieves the Short-Circuit Ratio (SCR).

        Returns
        -------
        float
            The Short-Circuit Ratio.
        """
        scr = self.__get_value(option="SCR")
        if scr:
            try:
                return float(scr)
            except Exception:
                return config.get_float("GFM", scr, 0.0)
        return config.get_float("GFM", "SCRmax", 0.0)

    def get_initial_scr(self) -> float:
        """
        Retrieves the initial Short-Circuit Ratio.

        Returns
        -------
        float
            The initial Short-Circuit Ratio.
        """
        return self.__get_float_value(option="SCRinitial", default_value=0.0)

    def get_final_scr(self) -> float:
        """
        Retrieves the final Short-Circuit Ratio.

        Returns
        -------
        float
            The final Short-Circuit Ratio.
        """
        return self.__get_float_value(option="SCRfinal", default_value=0.0)

    def _has_config_option(self, section: str, option: str) -> bool:
        """
        Helper to gracefully check if an option exists in the Config object
        regardless of the exact underlying method implemented.
        """
        if hasattr(config, "has_option"):
            return config.has_option(section, option)
        elif hasattr(config, "get_options"):
            try:
                opts = config.get_options(section)
                return opts is not None and any(opt.lower() == option.lower() for opt in opts)
            except Exception:
                return False
        return False

    def __get_value(self, option: str) -> str:
        """
        Traverses the hierarchical configuration framework to retrieve a string value.

        Parameters
        ----------
        option : str
            The configuration key to find.

        Returns
        -------
        str
            The configuration value as a string.
        """
        # Fallback sequence: Specific Operating Condition -> Base Model -> General PCS -> Default
        for section in self._eval_sections:
            if config.has_option(section, option):
                return config.get_value(section, option)
        return config.get_value("DEFAULT", option)

    def __get_float_value(self, option: str, default_value: float) -> float:
        """
        Traverses the hierarchical configuration framework to retrieve a float value.

        Parameters
        ----------
        option : str
            The configuration key to find.
        default_value : float
            The default value if not found.

        Returns
        -------
        float
            The configuration value as a float.
        """
        # Identical fallback sequence for numeric evaluations
        for section in self._eval_sections:
            if config.has_option(section, option):
                return config.get_float(section, option, default_value)
        return config.get_float("DEFAULT", option, default_value)

    def get_hybrid_parameters(self) -> Optional[Tuple[float, float, float, float]]:
        """
        Retrieves the D and H parameters for hybrid (over/underdamped) conditions.

        Returns
        -------
        Optional[Tuple[float, float, float, float]]
            A tuple containing
            (D_Overdamped, H_Overdamped, D_Underdamped, H_Underdamped) or None if incomplete.
        """
        params = (
            self._get_optional_float("D_Overdamped"),
            self._get_optional_float("H_Overdamped"),
            self._get_optional_float("D_Underdamped"),
            self._get_optional_float("H_Underdamped"),
        )
        # Ensure strict validation: return None if any of the 4 variables is missing
        return params if None not in params else None

    def get_standard_parameters(self) -> Optional[Tuple[float, float]]:
        """
        Retrieves standard D and H parameters.

        Returns
        -------
        Optional[Tuple[float, float]]
            A tuple containing (D, H) or None if incomplete.
        """
        params = (self._get_optional_float("D"), self._get_optional_float("H"))
        return params if None not in params else None

    def _get_optional_float(self, option: str) -> Optional[float]:
        """
        Safely parses and retrieves an optional float value from config.

        Parameters
        ----------
        option : str
            The configuration key to evaluate.

        Returns
        -------
        Optional[float]
            The parsed float value or None if invalid/missing.
        """
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
        """
        Returns whether to save detailed envelope outputs for debugging.

        Returns
        -------
        bool
            True if all envelopes should be saved, False otherwise.
        """
        if self._producer._config.has_option("GFM Parameters", "save_all_envelopes"):
            try:
                return self._producer._config.getboolean("GFM Parameters", "save_all_envelopes")
            except ValueError:
                return False
        return False

    def get_emt_delay(self) -> float:
        """
        Retrieves the EMT delay value for timing compensation.

        Returns
        -------
        float
            The EMT delay in seconds.
        """
        if self._producer._config.has_option("GFM Parameters", "emt_delay"):
            try:
                return float(self._producer._config.get("GFM Parameters", "emt_delay"))
            except ValueError:
                pass

        from dycov.gfm import constants

        return constants.EMT_DELAY_S
