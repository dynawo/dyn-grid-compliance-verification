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
from dycov.files import value_registry
from dycov.gfm.producer import GFMProducer
from dycov.logging import dycov_logging


class GFMParameters:
    """What the Grid Forming tests of a unit are generated or checked with: the unit, the PCS
    description of the test at hand and the run the tests belong to."""

    def __init__(
        self,
        run: Parameters,
        producer: GFMProducer,
        emt: bool = False,
        producer_curves: Optional[Path] = None,
        envelopes: Optional[Path] = None,
    ) -> None:
        """
        Initializes the parameters of the tests of a unit.

        Parameters
        ----------
        run : Parameters
            The parameters of the run the tests belong to, which owns their working and output
            directories and the selection of PCS: an envelope generation, or the performance
            verification of the producer.
        producer : GFMProducer
            The unit the tests are for.
        emt : bool, optional
            Whether the envelopes are for EMT simulations, whatever the INI file of the unit
            declares. Defaults to False.
        producer_curves : Optional[Path], optional
            Directory of the producer curves to check against the envelopes, one subdirectory
            per unit. Defaults to None, in which case only the envelopes are generated.
        envelopes : Optional[Path], optional
            Directory the envelopes of the unit are read from, as 'dycov generate_gfm_envelopes'
            writes them, instead of being generated. Defaults to None.
        """
        self._run = run
        self._producer = producer
        self._emt = emt
        self._producer_curves = producer_curves
        self._envelopes = envelopes
        # What the producer declares holds for every test, and is reported once
        self._reported_declarations = set()

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

    def get_working_dir(self) -> Path:
        """
        Retrieves the working directory of the run.

        Returns
        -------
        Path
            The working directory.
        """
        return self._run.get_working_dir()

    def get_output_dir(self) -> Path:
        """
        Retrieves the output directory of the run.

        Returns
        -------
        Path
            The output directory.
        """
        return self._run.get_output_dir()

    def get_selected_pcs(self) -> str:
        """
        Retrieves the PCS the run is limited to.

        Returns
        -------
        str
            The PCS name, None when the run is not limited to one.
        """
        return self._run.get_selected_pcs()

    def get_only_dtr(self) -> bool:
        """
        Returns whether the run uses only the PCS of the DTR.

        Returns
        -------
        bool
            True if the PCS of the user are left out.
        """
        return self._run.get_only_dtr()

    def get_producer(self) -> GFMProducer:
        """
        Retrieves the unit the tests are for.

        Returns
        -------
        GFMProducer
            The unit.
        """
        return self._producer

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
        Returns whether the envelopes are for EMT simulations: when the run asks for it, or when
        the INI file of the unit declares that its curves come from them.

        Returns
        -------
        bool
            True if EMT mode is enabled.
        """
        return self._emt or self._producer.get_config().getboolean(
            "GFM Parameters", "emt", fallback=False
        )

    def declares_unit_parameters(self) -> bool:
        """
        Checks whether the INI file of the unit declares the parameters its envelopes are
        generated from.

        Returns
        -------
        bool
            True if the INI file has a [GFM Parameters] section.
        """
        return self._producer.get_config().has_section("GFM Parameters")

    def get_envelopes_path(self) -> Optional[Path]:
        """
        Retrieves the directory the envelopes of the unit are read from.

        Returns
        -------
        Optional[Path]
            The directory of the envelopes, or None when they are generated.
        """
        return self._envelopes

    def get_producer_curves_path(self) -> Optional[Path]:
        """
        Retrieves the directory of the producer curves to check against the envelopes.

        Returns
        -------
        Optional[Path]
            The directory of the producer curves, or None when only envelopes are generated.
        """
        return self._producer_curves

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
        Retrieves the effective reactance (Xeff). A fiche may fix it in its PCS: the Fiche I18
        sets 0.27 pu, which RTE may raise in the convention d'exploitation, so the value of the
        producer is used only when it is higher.

        Returns
        -------
        float
            The effective reactance value in pu.
        """
        declared = self._producer.get_config().getfloat("GFM Parameters", "Xeff", fallback=None)
        fixed = self.__get_value("Xeff")
        if not fixed:
            if declared is None:
                raise ValueError(
                    f"{self._producer.get_producer_path()} declares no Xeff in its "
                    "[GFM Parameters] section"
                )
            return declared
        fixed = float(fixed)
        if declared is not None and declared < fixed:
            self.__report_once(
                "Xeff",
                f"The Xeff of {declared} pu the producer declares is below the {fixed} pu the "
                f"PCS fixes: {fixed} pu is used",
            )
        return fixed if declared is None else max(fixed, declared)

    def get_damping_constant(self) -> float:
        """
        Retrieves the damping constant (D), which the PCS may fix in place of the producer.

        Returns
        -------
        float
            The damping constant.
        """
        return self._get_optional_float("D")

    def get_inertia_constant(self) -> float:
        """
        Retrieves the inertia constant (H), which the PCS may fix in place of the producer: the
        Fiche I18 sets TR = 10 s, an H of 5 s.

        Returns
        -------
        float
            The inertia constant in seconds.
        """
        return self._get_optional_float("H")

    def get_nominal_apparent_power(self) -> float:
        """
        Retrieves the nominal apparent power (Snom).

        Returns
        -------
        float
            The nominal apparent power.
        """
        return float(self._producer._config.get("GFM Parameters", "Snom"))

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
        Retrieves the minimum active power, the opposite of the maximum consumption for a storage
        unit whose INI file declares it.

        Returns
        -------
        float
            The minimum active power in pu.
        """
        # The INI file of a verification declares the consumption of a storage unit as
        # p_max_consumption, that of an envelope generation as a negative p_min_injection
        option, p_min = self.__unit_power("p_max_consumption", "p_min_injection")
        return -p_min if option == "p_max_consumption" else p_min

    def get_max_active_power(self) -> float:
        """
        Retrieves the maximum active power injection.

        Returns
        -------
        float
            The maximum active power in pu.
        """
        return self.__unit_power("p_max_injection")[1]

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
        return self.__unit_power("q_min")[1]

    def get_max_reactive_power(self) -> float:
        """
        Retrieves the maximum reactive power.

        Returns
        -------
        float
            The maximum reactive power in pu.
        """
        return self.__unit_power("q_max")[1]

    def __unit_power(self, *options: str) -> tuple[str, float]:
        """A power of the unit under test, in pu of its Snom, and the name it is declared under.
        In a performance verification [DEFAULT] describes the whole installation, and a power
        above the rating of the converter is one of its limits that [GFM Parameters] does not
        restate for the PGU."""
        option, value = self.__unit_option(*options)
        snom = self.get_nominal_apparent_power()
        if self._producer_curves is not None and abs(float(value)) > snom:
            self.__report_once(
                option,
                f"The {option} of {value} the producer declares for the PGU exceeds its Snom of "
                f"{snom} MVA: the [GFM Parameters] section is to declare the limits of the PGU "
                "when they differ from those of the installation",
            )
        return option, float(value) / snom

    def __report_once(self, declaration: str, message: str) -> None:
        if declaration not in self._reported_declarations:
            self._reported_declarations.add(declaration)
            dycov_logging.get_logger("GFMParameters").warning(message)

    def __unit_option(self, *options: str) -> tuple[str, str]:
        """A power of the unit under test. The [GFM Parameters] section describes the PGU and
        overrides [DEFAULT], which describes the whole installation when the INI file also
        serves the tests of the PDR, such as those of a performance verification.

        Parameters
        ----------
        *options : str
            The names the power may be declared under, as [DEFAULT] writes them, the preferred
            one first.

        Returns
        -------
        tuple[str, str]
            The name the power is declared under and its value, in MW or MVAr.

        Raises
        ------
        ValueError
            If neither section declares the power.
        """
        producer_config = self._producer.get_config()
        defaults = producer_config.defaults()
        if producer_config.has_section("GFM Parameters"):
            pgu = producer_config["GFM Parameters"]
            for option in options:
                # Every option of [DEFAULT] shows in the section too
                if option in pgu and pgu.get(option, raw=True) != defaults.get(option):
                    return option, pgu[option]
        for option in options:
            if option in defaults:
                return option, producer_config.get("DEFAULT", option)
        raise ValueError(f"The INI file of the producer declares no {' nor '.join(options)}")

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
        Retrieves the base angular frequency (Wb).

        Returns
        -------
        float
            The base angular frequency in rad/s.
        """
        return self.__get_float_value("Wb", 0.0)

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
        value_definition = self.__get_value("VoltageStepAtGrid")
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
        return self.__get_float_value("RoCoF", 0.0) / self._producer._f_nom

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
            The normalized initial frequency.
        """
        return self.__get_float_value("Frequency0", 0.0) / self._producer._f_nom

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

        Returns
        -------
        float
            The Short-Circuit Ratio.
        """
        scr = self.__get_value("SCR")
        if scr:
            try:
                return float(scr)
            except Exception:
                self.__warn_of_the_new_scr_max(scr)
                return config.get_float("GFM", scr, 0.0)
        return config.get_float("GFM", "SCRmax", 0.0)

    def __warn_of_the_new_scr_max(self, scr: str) -> None:
        """A description of the user written for the SCRmax of 10 the tool had before the DTR
        Fiche I18 now gets the 20 of the fiche."""
        if scr != "SCRmax":
            return
        section = next(
            (section for section in self._eval_sections if config.has_option(section, "SCR")),
            None,
        )
        if section is not None and config.is_set_by_user(section, "SCR"):
            dycov_logging.warn_once(
                "GFMParameters",
                f"The SCR of [{section}] of the user's configuration names SCRmax, which is now "
                "20, the maximum short-circuit ratio of the DTR Fiche I18; the 10 it was before "
                "is SCRmed",
            )

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

    def get_envelope_magnitude(self, default: str) -> str:
        """
        Retrieves the magnitude the envelopes of the test bound, when the PCS names one in place
        of the one its calculator bounds by default.

        Parameters
        ----------
        default : str
            The magnitude the calculator bounds when the PCS names none.

        Returns
        -------
        str
            The name of the magnitude, such as "P" or "Ip".
        """
        return self.__get_value("envelope_magnitude") or default

    def get_max_current(self) -> Optional[float]:
        """
        Retrieves the short-duration maximum current of the unit (Imax), when declared.

        Returns
        -------
        Optional[float]
            The maximum current in pu of Snom, or None when the producer declares none.
        """
        return self._producer.get_config().getfloat("GFM Parameters", "Imax", fallback=None)

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
