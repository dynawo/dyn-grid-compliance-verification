#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
from dycov.configuration.cfg import config
from dycov.core.parameters import Parameters
from dycov.files import model_parameters
from dycov.gfm.producer import GFMProducer


class GFMParameters(Parameters):
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
        Parameters
        ----------
        launcher_dwo : Path
        producer_ini : Path
        selected_pcs : str
        output_dir : Path
        only_dtr : bool
        emt : bool
        """
        super().__init__(launcher_dwo, selected_pcs, output_dir, only_dtr)
        self._emt = emt
        self._producer = GFMProducer(producer_ini=producer_ini)

    def set_section(self, pcs_name: str, bm_name: str, oc_name: str) -> None:
        """
        Parameters
        ----------
        pcs_name : str
        bm_name : str
        oc_name : str
        """
        self._pcs_section = pcs_name
        self._bm_section = f"{pcs_name}.{bm_name}"
        self._oc_section = f"{pcs_name}.{bm_name}.{oc_name}"

    def is_valid(self) -> bool:
        """
        Returns
        -------
        bool
        """
        return self._producer.is_gfm()

    def is_emt(self) -> bool:
        """
        Returns
        -------
        bool
        """
        return self._emt

    def get_calculator_name(self) -> str:
        """
        Returns
        -------
        str
        """
        return self.__get_value(option="calculator")

    def get_effective_reactance(self) -> float:
        """
        Returns
        -------
        float
        """
        return float(self._producer.get_config().get("GFM Parameters", "Xeff"))

    def get_damping_constant(self) -> float:
        """
        Returns
        -------
        float
        """
        return float(self._producer.get_config().get("GFM Parameters", "D"))

    def get_inertia_constant(self) -> float:
        """
        Returns
        -------
        float
        """
        return float(self._producer.get_config().get("GFM Parameters", "H"))

    def get_nominal_apparent_power(self) -> float:
        """
        Returns
        -------
        float
        """
        return float(self._producer.get_config().get("GFM Parameters", "Snom"))

    def get_nominal_voltage(self) -> float:
        """
        Returns
        -------
        float
        """
        return float(self._producer.get_config().get("DEFAULT", "Unom"))

    def get_min_active_power(self) -> float:
        """
        Returns
        -------
        float
        """
        return (
            float(self._producer.get_config().get("DEFAULT", "p_min_injection"))
            / self.get_nominal_apparent_power()
        )

    def get_max_active_power(self) -> float:
        """
        Returns
        -------
        float
        """
        return (
            float(self._producer.get_config().get("DEFAULT", "p_max_injection"))
            / self.get_nominal_apparent_power()
        )

    def get_min_reactive_power(self) -> float:
        """
        Returns
        -------
        float
        """
        return (
            float(self._producer.get_config().get("DEFAULT", "q_min"))
            / self.get_nominal_apparent_power()
        )

    def get_max_reactive_power(self) -> float:
        """
        Returns
        -------
        float
        """
        return (
            float(self._producer.get_config().get("DEFAULT", "q_max"))
            / self.get_nominal_apparent_power()
        )

    def get_initial_active_power(self) -> float:
        """
        Returns
        -------
        float
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
        Returns
        -------
        float
        """
        return self.__get_float_value(option="Ugr", default_value=1.0)

    def get_time_to_90(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="TimeTo90", default_value=0.0)

    def get_time_for_tunnel(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="TimeforTunnel", default_value=0.0)

    def get_final_allowed_tunnel_pn(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="FinalAllowedTunnelPn", default_value=0.0)

    def get_final_allowed_tunnel_variation(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="FinalAllowedTunnelVariation", default_value=0.0)

    def get_margin_low(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="MarginLow", default_value=0.0)

    def get_margin_high(self) -> float:
        """
        Returns
        -------
        float
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

    def get_min_ratio(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="RatioMin", default_value=1.0)

    def get_max_ratio(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="RatioMax", default_value=1.0)

    def get_base_angular_frequency(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="Wb", default_value=0.0)

    def get_delta_phase(self) -> float:
        """
        Returns
        -------
        float
        """
        value_definition = self.__get_value(option="DeltaPhase")
        if "*" in value_definition:
            parts = value_definition.split("*")
            term1 = float(parts[0])
            delta_rad = term1 * (self.get_effective_reactance() + self.get_grid_reactance())
        else:
            delta_rad = float(value_definition)
        return delta_rad * 180 / np.pi

    def get_voltage_step_at_grid(self) -> float:
        """
        Returns
        -------
        float
        """
        value_definition = self.__get_value(option="VoltageStepAtGrid")
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
        """
        Returns
        -------
        float
        """
        return (
            self.get_voltage_step_at_grid()
            * self.get_effective_reactance()
            / (self.get_grid_reactance() + self.get_effective_reactance())
        )

    def get_delta_step(self) -> float:
        """
        Returns
        -------
        float
        """
        x_grid = self.get_grid_reactance()
        x_eff = self.get_effective_reactance()
        delta_theta_if = self.get_delta_phase()
        if (x_eff + x_grid) == 0:
            return 0.0
        return (x_eff / (x_eff + x_grid)) * delta_theta_if

    def get_change_frequency(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="RoCoF", default_value=0.0) / getattr(
            self._producer, "_f_nom", 50.0
        )

    def get_change_frequency_duration(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="RoCoFDuration", default_value=0.0)

    def get_initial_frequency(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="Frequency0", default_value=0.0) / getattr(
            self._producer, "_f_nom", 50.0
        )

    def get_t_expo_decrease(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="TimeExponentialDecrease", default_value=0.0)

    def get_pll_time_constant(self) -> float:
        """
        Returns
        -------
        float
        """
        return self.__get_float_value(option="Tpll", default_value=0.0)

    def get_grid_reactance(self) -> float:
        """
        Returns
        -------
        float
        """
        return 1 / self.get_scr()

    def get_scr(self) -> float:
        """
        Returns
        -------
        float
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
        Returns
        -------
        float
        """
        return self.__get_float_value(option="SCRinitial", default_value=0.0)

    def get_final_scr(self) -> float:
        """
        Returns
        -------
        float
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
        Parameters
        ----------
        option : str

        Returns
        -------
        str
        """
        if self._has_config_option(self._oc_section, option):
            return config.get_value(self._oc_section, option)
        elif self._has_config_option(self._bm_section, option):
            return config.get_value(self._bm_section, option)
        elif self._has_config_option(self._pcs_section, option):
            return config.get_value(self._pcs_section, option)
        return config.get_value("DEFAULT", option)

    def __get_float_value(self, option: str, default_value: float) -> float:
        """
        Parameters
        ----------
        option : str
        default_value : float

        Returns
        -------
        float
        """
        if self._has_config_option(self._oc_section, option):
            return config.get_float(self._oc_section, option, default_value)
        elif self._has_config_option(self._bm_section, option):
            return config.get_float(self._bm_section, option, default_value)
        elif self._has_config_option(self._pcs_section, option):
            return config.get_float(self._pcs_section, option, default_value)
        return config.get_float("DEFAULT", option, default_value)

    def get_hybrid_parameters(self) -> Optional[Tuple[float, float, float, float]]:
        """
        Returns
        -------
        Optional[Tuple[float, float, float, float]]
        """
        d_over = self._get_optional_float(option="D_Overdamped")
        h_over = self._get_optional_float(option="H_Overdamped")
        d_under = self._get_optional_float(option="D_Underdamped")
        h_under = self._get_optional_float(option="H_Underdamped")
        if all(v is not None for v in [d_over, h_over, d_under, h_under]):
            return d_over, h_over, d_under, h_under
        return None

    def get_standard_parameters(self) -> Optional[Tuple[float, float]]:
        """
        Returns
        -------
        Optional[Tuple[float, float]]
        """
        d = self._get_optional_float(option="D")
        h = self._get_optional_float(option="H")
        if d is not None and h is not None:
            return d, h
        return None

    def _get_optional_float(self, option: str) -> Optional[float]:
        """
        Parameters
        ----------
        option : str

        Returns
        -------
        Optional[float]
        """
        val_str = self.__get_value(option=option)
        if val_str:
            try:
                return float(val_str)
            except ValueError:
                pass
        if self._producer.get_config().has_option("GFM Parameters", option):
            try:
                return float(self._producer.get_config().get("GFM Parameters", option))
            except ValueError:
                return None
        return None

    def should_save_all_envelopes(self) -> bool:
        """
        Returns
        -------
        bool
        """
        if self._producer.get_config().has_option("GFM Parameters", "save_all_envelopes"):
            try:
                return self._producer.get_config().getboolean(
                    "GFM Parameters", "save_all_envelopes"
                )
            except ValueError:
                return False
        return False

    def get_emt_delay(self) -> float:
        """
        Returns
        -------
        float
        """
        if self._producer.get_config().has_option("GFM Parameters", "emt_delay"):
            try:
                return float(self._producer.get_config().get("GFM Parameters", "emt_delay"))
            except ValueError:
                pass
        from dycov.gfm import constants

        return constants.EMT_FINAL_DELAY_S
