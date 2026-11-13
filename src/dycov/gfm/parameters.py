#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

from pathlib import Path
from typing import Callable, Optional, TypeVar

import numpy as np

from dycov.configuration.cfg import config
from dycov.core.parameters import Parameters
from dycov.files import value_registry
from dycov.gfm import constants
from dycov.gfm.producer import GFMProducer

_GFM_SECTION = "GFM Parameters"
_DEFAULT_SECTION = "DEFAULT"

_T = TypeVar("_T")


class GFMParameters(Parameters):
    """The parameters of a GFM envelope generation.

    Two sources feed it: the producer's INI file, which describes the unit, and the PCS
    configuration, which describes the test and is read from the most specific section that sets
    each option (the operating condition, then the benchmark, then the PCS).
    """

    def __init__(
        self,
        producer_ini: Path,
        selected_pcs: Optional[str],
        output_dir: Path,
        only_dtr: bool,
        emt: bool,
    ) -> None:
        """
        Initializes the parameters object with producer configuration and runtime options.

        Parameters
        ----------
        producer_ini : Path
            Path to the producer's INI configuration file.
        selected_pcs : str, optional
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
        self._producer = GFMProducer(producer_ini)

    def set_section(self, pcs_name: str, bm_name: str, oc_name: str) -> None:
        """
        Sets the operating condition whose PCS configuration the getters read.

        Parameters
        ----------
        pcs_name : str
            Name of the PCS.
        bm_name : str
            Name of the benchmark.
        oc_name : str
            Name of the operating condition.
        """
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
        return self.__get_value("calculator")

    def get_effective_reactance(self) -> float:
        """
        Retrieves the effective reactance (Xeff).

        Returns
        -------
        float
            The effective reactance value in pu.
        """
        return self.__get_producer_float("Xeff")

    def get_damping_constant(self) -> float:
        """
        Retrieves the damping constant (D).

        Returns
        -------
        float
            The damping constant.
        """
        return self.__get_producer_float("D")

    def get_inertia_constant(self) -> float:
        """
        Retrieves the inertia constant (H).

        Returns
        -------
        float
            The inertia constant in seconds.
        """
        return self.__get_producer_float("H")

    def get_nominal_apparent_power(self) -> float:
        """
        Retrieves the nominal apparent power (Snom).

        Returns
        -------
        float
            The nominal apparent power.
        """
        return self.__get_producer_float("Snom")

    def get_initial_active_power(self) -> float:
        """
        Calculates and retrieves the initial active power (P0).

        Returns
        -------
        float
            The initial active power in pu.
        """
        p0_definition = self.__get_value("P0")
        return value_registry.extract_defined_value(
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
        return self.__get_per_unit_power("p_min_injection")

    def get_max_active_power(self) -> float:
        """
        Retrieves the maximum active power injection.

        Returns
        -------
        float
            The maximum active power in pu.
        """
        return self.__get_per_unit_power("p_max_injection")

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
            return value_registry.extract_defined_value(
                q0_definition, "Qmin", self.get_min_reactive_power(), 1
            )
        return value_registry.extract_defined_value(
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
        return self.__get_per_unit_power("q_min")

    def get_max_reactive_power(self) -> float:
        """
        Retrieves the maximum reactive power.

        Returns
        -------
        float
            The maximum reactive power in pu.
        """
        return self.__get_per_unit_power("q_max")

    def get_initial_voltage(self) -> float:
        """
        Retrieves the initial voltage (U0).

        Returns
        -------
        float
            The initial voltage in pu.
        """
        return self.__get_float_value("U0", 1)

    def get_grid_voltage(self) -> float:
        """
        Retrieves the grid voltage (Ugr).

        Returns
        -------
        float
            The grid voltage in pu.
        """
        return self.__get_float_value("Ugr", 1)

    def get_time_to_90(self) -> float:
        """
        Retrieves the time to reach 90% of the steady-state response.

        Returns
        -------
        float
            The time in seconds.
        """
        return self.__get_float_value("TimeTo90", 0.0)

    def get_time_for_tunnel(self) -> float:
        """
        Retrieves the time constant for the margin tunnel decay.

        Returns
        -------
        float
            The time constant in seconds.
        """
        return self.__get_float_value("TimeforTunnel", 0.0)

    def get_final_allowed_tunnel_pn(self) -> float:
        """
        Retrieves the final allowed margin tunnel in absolute nominal power.

        Returns
        -------
        float
            The allowed tunnel margin in pu.
        """
        return self.__get_float_value("FinalAllowedTunnelPn", 0.0)

    def get_final_allowed_tunnel_variation(self) -> float:
        """
        Retrieves the final allowed margin tunnel relative to the signal variation.

        Returns
        -------
        float
            The allowed variation ratio.
        """
        return self.__get_float_value("FinalAllowedTunnelVariation", 0.0)

    def get_margin_low(self) -> float:
        """
        Retrieves the lower envelope margin multiplier.

        Returns
        -------
        float
            The lower margin ratio.
        """
        return self.__get_float_value("MarginLow", 0.0)

    def get_margin_high(self) -> float:
        """
        Retrieves the upper envelope margin multiplier.

        Returns
        -------
        float
            The upper margin ratio.
        """
        return self.__get_float_value("MarginHigh", 0.0)

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
        return self.__get_float_value("RatioMin", 1.0)

    def get_max_ratio(self) -> float:
        """
        Retrieves the maximum parameter variation ratio.

        Returns
        -------
        float
            The maximum ratio.
        """
        return self.__get_float_value("RatioMax", 1.0)

    def get_base_angular_frequency(self) -> float:
        """
        Retrieves the base angular frequency (Wb) at the nominal frequency.

        The PCS give Wb for 50 Hz; it is scaled to the nominal frequency of the configuration,
        the one the frequencies of the PCS are turned into pu with.

        Returns
        -------
        float
            The base angular frequency in rad/s.
        """
        return self.__get_float_value("Wb", 0.0) * (
            self.get_nominal_frequency() / constants.PCS_WB_FREQUENCY_HZ
        )

    def get_delta_phase(self) -> float:
        """
        Calculates and retrieves the phase jump delta.

        Returns
        -------
        float
            The phase jump delta in degrees.
        """
        value_definition = self.__get_value("DeltaPhase")
        delta_rad = self.__times_total_reactance(value_definition)
        if delta_rad is None:
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
        value_definition = self.__get_value("VoltageStepAtGrid")
        voltage_step = self.__times_total_reactance(value_definition)
        if voltage_step is None:
            return float(value_definition)
        return voltage_step * 100

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

    def get_nominal_frequency(self) -> float:
        """
        Retrieves the nominal frequency of the producer, the base of the frequencies in pu.

        Returns
        -------
        float
            The nominal frequency in Hz.
        """
        return self._producer.get_nominal_frequency()

    def get_change_frequency(self) -> float:
        """
        Retrieves the Rate of Change of Frequency (RoCoF).

        Returns
        -------
        float
            The RoCoF value, in pu of the nominal frequency per second.
        """
        return self.__get_float_value("RoCoF", 0.0) / self.get_nominal_frequency()

    def get_change_frequency_duration(self) -> float:
        """
        Retrieves the duration of the RoCoF event.

        Returns
        -------
        float
            The RoCoF duration in seconds.
        """
        return self.__get_float_value("RoCoFDuration", 0.0)

    def get_initial_frequency(self) -> float:
        """
        Retrieves the initial system frequency.

        Returns
        -------
        float
            The initial frequency, in pu of the nominal frequency.
        """
        return self.__get_float_value("Frequency0", 0.0) / self.get_nominal_frequency()

    def get_t_expo_decrease(self) -> float:
        """
        Retrieves the time constant for exponential decrease.

        Returns
        -------
        float
            The exponential decrease time constant in seconds.
        """
        return self.__get_float_value("TimeExponentialDecrease", 0.0)

    def get_pll_time_constant(self) -> float:
        """
        Retrieves the PLL time constant (Tpll).

        Returns
        -------
        float
            The PLL time constant in seconds.
        """
        return self.__get_float_value("Tpll", 0.0)

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

        The PCS configuration gives it as a number or as the name of an option of the ``[GFM]``
        section of the tool's configuration (``SCRmin``, ``SCRmax``); without it, ``SCRmax``.

        Returns
        -------
        float
            The Short-Circuit Ratio.
        """
        scr = self.__get_value("SCR")
        if not scr:
            return config.get_float("GFM", "SCRmax", 0.0)
        try:
            return float(scr)
        except ValueError:
            return config.get_float("GFM", scr, 0.0)

    def get_initial_scr(self) -> float:
        """
        Retrieves the initial Short-Circuit Ratio.

        Returns
        -------
        float
            The initial Short-Circuit Ratio.
        """
        return self.__get_float_value("SCRinitial", 0.0)

    def get_final_scr(self) -> float:
        """
        Retrieves the final Short-Circuit Ratio.

        Returns
        -------
        float
            The final Short-Circuit Ratio.
        """
        return self.__get_float_value("SCRfinal", 0.0)

    def get_hybrid_parameters(self) -> Optional[tuple[float, ...]]:
        """
        Retrieves the D and H parameters for hybrid (over/underdamped) conditions.

        Returns
        -------
        Optional[tuple[float, ...]]
            A tuple containing
            (D_Overdamped, H_Overdamped, D_Underdamped, H_Underdamped), or None unless all four
            are given.
        """
        return self.__all_or_none(
            ("D_Overdamped", "H_Overdamped", "D_Underdamped", "H_Underdamped")
        )

    def get_standard_parameters(self) -> Optional[tuple[float, ...]]:
        """
        Retrieves standard D and H parameters.

        Returns
        -------
        Optional[tuple[float, ...]]
            A tuple containing (D, H), or None unless both are given.
        """
        return self.__all_or_none(("D", "H"))

    def _get_optional_float(self, option: str) -> Optional[float]:
        """
        Retrieves a number the PCS configuration or the producer may give.

        Parameters
        ----------
        option : str
            The configuration key to evaluate.

        Returns
        -------
        Optional[float]
            The number the PCS configuration gives, else the one the producer gives, or None
            when neither gives a number.
        """
        val_str = self.__get_value(option)
        if val_str:
            try:
                return float(val_str)
            except ValueError:
                pass
        return self.__get_producer_option(option, self._producer.get_config().getfloat, None)

    def should_save_all_envelopes(self) -> bool:
        """
        Returns whether to save detailed envelope outputs for debugging.

        Returns
        -------
        bool
            True if all envelopes should be saved, False otherwise.
        """
        return self.__get_producer_option(
            "save_all_envelopes", self._producer.get_config().getboolean, False
        )

    def get_emt_delay(self) -> float:
        """
        Retrieves the EMT delay value for timing compensation.

        Returns
        -------
        float
            The EMT delay in seconds.
        """
        return self.__get_producer_option(
            "emt_delay", self._producer.get_config().getfloat, constants.EMT_DELAY_S
        )

    def __all_or_none(self, options: tuple[str, ...]) -> Optional[tuple[float, ...]]:
        values = tuple(self._get_optional_float(option) for option in options)
        return values if None not in values else None

    def __times_total_reactance(self, value_definition: str) -> Optional[float]:
        """The value of a definition ``k*(Xeff+Xgrid)``, or None if it is a plain number."""
        if "*" not in value_definition:
            return None
        multiplier = float(value_definition.split("*")[0])
        return multiplier * (self.get_effective_reactance() + self.get_grid_reactance())

    def __get_per_unit_power(self, option: str) -> float:
        return (
            float(self._producer.get_config().get(_DEFAULT_SECTION, option))
            / self.get_nominal_apparent_power()
        )

    def __get_producer_float(self, option: str) -> float:
        return float(self._producer.get_config().get(_GFM_SECTION, option))

    def __get_producer_option(
        self, option: str, read: Callable[[str, str], _T], fallback: _T
    ) -> _T:
        """An option of the producer's GFM section, or fallback when it is missing or malformed."""
        if not self._producer.get_config().has_option(_GFM_SECTION, option):
            return fallback
        try:
            return read(_GFM_SECTION, option)
        except ValueError:
            return fallback

    def __section_setting(self, option: str) -> str:
        """The most specific section of the PCS configuration that sets option."""
        return next(
            (section for section in self._eval_sections if config.has_option(section, option)),
            _DEFAULT_SECTION,
        )

    def __get_value(self, option: str) -> str:
        return config.get_value(self.__section_setting(option), option)

    def __get_float_value(self, option: str, default_value: float) -> float:
        return config.get_float(self.__section_setting(option), option, default_value)
