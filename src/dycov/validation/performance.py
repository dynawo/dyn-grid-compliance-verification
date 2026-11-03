#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from pathlib import Path

import numpy as np
from lxml import etree

from dycov.configuration.cfg import config
from dycov.core.global_variables import (
    ELECTRIC_PERFORMANCE_SM,
)
from dycov.core.validator import Validator
from dycov.curves import naming
from dycov.curves.manager import CurvesManager
from dycov.logging import dycov_logging
from dycov.model.parameters import Stability
from dycov.model.producer import Producer
from dycov.validation import checks, common, compliance_list

GENERATOR_DISCONNECT_MSG = "GENERATOR : disconnecting"
LOAD_DISCONNECT_MSG = "LOAD : disconnecting"
IEC_DISCONNECT_PROTECTION_MSG = "IEC WT disconnected due to"


def _check_compliance(
    results: dict,
    compliance_value: float,
    results_name: str,
    threshold: float,
    scale: float = 1.0,
):
    results[results_name] = compliance_value * scale
    if threshold is not None:
        results[results_name + "_check"] = results[results_name] < threshold
        results["compliance"] &= results[results_name + "_check"]


def _combined_check(parts: list) -> bool | str:
    """A check made of several: failed if one of them fails, otherwise not computable if one of
    them cannot be computed or if there are none."""
    if not parts:
        return checks.NOT_COMPUTABLE
    if not all(parts):
        return False
    return checks.NOT_COMPUTABLE if checks.NOT_COMPUTABLE in parts else True


def _warn_not_computable(check: str, missing: str) -> None:
    dycov_logging.get_logger("Performance").warning(
        f"{check} cannot be checked without {missing}: reported as {checks.NOT_COMPUTABLE}"
    )


def _is_generator_disconnection_event(event: etree.Element):
    return event.get("message") == GENERATOR_DISCONNECT_MSG or event.get("message").startswith(
        IEC_DISCONNECT_PROTECTION_MSG
    )


def _is_load_disconnection_event(event: etree.Element):
    return event.get("message") == LOAD_DISCONNECT_MSG


def _is_disconnection_event(event: etree.Element, element_type: str):
    return (element_type == "gen" and _is_generator_disconnection_event(event)) or (
        element_type == "load" and _is_load_disconnection_event(event)
    )


def _check_timeline(timeline_file: Path, element_type: str) -> tuple[bool, list]:
    no_error = True
    # Load timeline file
    timeline = etree.parse(timeline_file, etree.XMLParser(remove_blank_text=True))

    # Look for generator disconnection event
    root = timeline.getroot()
    ns = etree.QName(root).namespace
    disconnection_list = []
    for timeline_event in root.iter("{%s}event" % ns):
        if _is_disconnection_event(timeline_event, element_type):
            no_error = False
            disconnection_list.append(timeline_event.get("modelName"))

    return no_error, disconnection_list


class PerformanceValidator(Validator):
    def __init__(
        self,
        curves_manager: CurvesManager,
        producer: Producer,
        thr_ss_tol: float,
        validations: list,
        is_field_measurements: bool,
        pcs_name: str,
        bm_name: str,
    ):
        super().__init__(
            curves_manager, producer, validations, is_field_measurements, pcs_name, bm_name
        )
        self._thr_ss_tol = thr_ss_tol

    def __curve_list(self, curve_name: str) -> list:
        return list(self._get_calculated_curve_by_name(curve_name))

    def __run_common_tests(
        self,
        thr_ss_tol: float,
        is_non_synchronous: bool,
    ) -> tuple[bool, int, bool, int, bool, int, bool, int, bool]:
        bus_pdr_voltage = "BusPDR" + "_BUS_" + "Voltage"
        # Run stabilization test
        steady_v, first_steady_pos_v = common.is_stable(
            self.__curve_list("time"),
            self.__curve_list(bus_pdr_voltage),
            thr_ss_tol,
        )

        steady_p, first_steady_pos_p = common.is_stable(
            self.__curve_list("time"),
            self.__curve_list("BusPDR_BUS_ActivePower"),
            thr_ss_tol,
        )

        steady_q, first_steady_pos_q = common.is_stable(
            self.__curve_list("time"),
            self.__curve_list("BusPDR_BUS_ReactivePower"),
            thr_ss_tol,
        )

        stable_theta = False
        first_stable_pos_theta = 0
        pass_pi = False
        if not is_non_synchronous:
            stable_theta, first_stable_pos_theta, pass_pi = self._check_theta_stability(thr_ss_tol)

        if not steady_p:
            dycov_logging.get_logger("Performance").warning("P has not reached steady state")
        if not steady_q:
            dycov_logging.get_logger("Performance").warning("Q has not reached steady state")
        if not steady_v:
            dycov_logging.get_logger("Performance").warning("V has not reached steady state")

        return (
            steady_p,
            first_steady_pos_p,
            steady_q,
            first_steady_pos_q,
            steady_v,
            first_steady_pos_v,
            stable_theta,
            first_stable_pos_theta,
            pass_pi,
        )

    def _check_theta_stability(self, thr_ss_tol: float) -> tuple[bool, int, bool]:
        stable_theta = True
        first_stable_pos_theta = len(self._get_calculated_curve_by_name("time"))
        pass_pi = True
        internal_angle_keys = [
            key for key in self._get_calculated_curves().keys() if key.endswith("_InternalAngle")
        ]
        missing = sorted(
            f"{unit}_GEN_InternalAngle"
            for unit in self.__units()
            if f"{unit}_GEN_InternalAngle" not in internal_angle_keys
        )
        if not internal_angle_keys:
            _warn_not_computable("The rotor stability", "the internal angle of the units")
            return checks.NOT_COMPUTABLE, 0, checks.NOT_COMPUTABLE
        if missing:
            _warn_not_computable("The rotor stability", " and ".join(missing))

        for key in internal_angle_keys:
            gen_stable_theta, gen_first_stable_pos_theta = common.is_stable(
                self.__curve_list("time"),
                self.__curve_list(key),
                thr_ss_tol,
            )

            # Check +- Pi
            gen_pass_pi = common.theta_pi(
                self.__curve_list("time"),
                self.__curve_list(key),
            )
            stable_theta &= gen_stable_theta
            if gen_first_stable_pos_theta < first_stable_pos_theta:
                first_stable_pos_theta = gen_first_stable_pos_theta
            pass_pi &= gen_pass_pi

        if not stable_theta:
            dycov_logging.get_logger("Performance").warning("Theta has not reached stabilization")
        if not pass_pi:
            dycov_logging.get_logger("Performance").warning(
                "Theta has not met the success criterion"
            )

        if missing:
            stable_theta = _combined_check([stable_theta, checks.NOT_COMPUTABLE])
            pass_pi = _combined_check([pass_pi, checks.NOT_COMPUTABLE])
        return stable_theta, first_stable_pos_theta, pass_pi

    def __units(self) -> set:
        """The generating units of the producer: those of its model, or those its curves name,
        the machines of the network aside."""
        if self._producer.is_dynawo_model():
            return {generator.id for generator in self._producer.generators}
        columns = self._get_calculated_curves().columns
        network = {name.split("_GEN_TSO_")[0] for name in columns if "_GEN_TSO_" in name}
        return {name.split("_GEN_")[0] for name in columns if "_GEN_" in name} - network

    def __calculate_simple_times(
        self,
        compliance_values: dict,
        t_event_start: float,
    ):
        bus_pdr_voltage = "BusPDR" + "_BUS_" + "Voltage"
        if compliance_list.contains_key(["time_5U"], self._validations):
            compliance_values["time_5u"] = common.get_txu_relative(
                0.05,
                self.__curve_list("time"),
                self.__curve_list(bus_pdr_voltage),
                t_event_start,
            )

        if compliance_list.contains_key(["time_10U"], self._validations):
            compliance_values["time_10u"] = common.get_txu_relative(
                0.10,
                self.__curve_list("time"),
                self.__curve_list(bus_pdr_voltage),
                t_event_start,
            )

        if compliance_list.contains_key(["time_10Pfloor_clear"], self._validations):
            compliance_values["time_10pfloor"] = common.get_txpfloor(
                0.1,
                self.__curve_list("time"),
                self.__curve_list("BusPDR_BUS_ActivePower"),
                t_event_start,
            )

    def __calculate_composed_times(
        self,
        compliance_values: dict,
        t_event_start: float,
    ) -> dict:
        bus_pdr_voltage = "BusPDR" + "_BUS_" + "Voltage"
        if compliance_list.contains_key(
            ["time_5P", "time_5P_85U", "time_5P_clear"], self._validations
        ):
            compliance_values["time_5p"] = common.get_txp(
                0.05,
                self.__curve_list("time"),
                self.__curve_list("BusPDR_BUS_ActivePower"),
                t_event_start,
            )

        if compliance_list.contains_key(
            ["time_10P", "time_10P_85U", "time_10P_clear"], self._validations
        ):
            compliance_values["time_10p"] = common.get_txp(
                0.1,
                self.__curve_list("time"),
                self.__curve_list("BusPDR_BUS_ActivePower"),
                t_event_start,
            )

        if compliance_list.contains_key(["time_5P_85U", "time_10P_85U"], self._validations):
            compliance_values["time_85u"] = common.get_txu(
                config.get_float("GridCode", "recovery_voltage", 0.85),
                self.__curve_list("time"),
                self.__curve_list(bus_pdr_voltage),
                t_event_start,
            )

        if compliance_list.contains_key(["time_10Pfloor_85U"], self._validations):
            compliance_values["time_85u"] = common.get_txu(
                config.get_float("GridCode", "recovery_voltage", 0.85),
                self.__curve_list("time"),
                self.__curve_list(bus_pdr_voltage),
                t_event_start,
            )
            compliance_values["time_10pfloor"] = common.get_txpfloor(
                0.1,
                self.__curve_list("time"),
                self.__curve_list("BusPDR_BUS_ActivePower"),
                t_event_start,
            )

    def __calculate_times(
        self,
        compliance_values: dict,
        t_event_start: float,
    ):
        self.__calculate_simple_times(compliance_values, t_event_start)
        self.__calculate_composed_times(compliance_values, t_event_start)

    def __get_filtered_columns(self, suffix: str) -> list:
        return [col for col in self._get_calculated_curves() if col.endswith(suffix)]

    def __calculate_avr(
        self,
        compliance_values: dict,
        t_event_start: float,
    ):
        if compliance_list.contains_key(["AVR_5"], self._validations):
            AVR_5_crv = list()
            AVR_5_checks = []
            AVR_5 = -1
            for magnitude_controlled_by_avr, avr_setpoint in self.__avr_curves():
                if avr_setpoint is None:
                    AVR_5_checks.append(checks.NOT_COMPUTABLE)
                    continue
                gen_AVR_5_check, gen_AVR_5 = common.get_AVR_x(
                    self.__curve_list("time"),
                    self.__curve_list(magnitude_controlled_by_avr),
                    self.__curve_list(avr_setpoint),
                    t_event_start,
                )
                AVR_5_crv.append(self.__curve_list(avr_setpoint))
                AVR_5_checks.append(gen_AVR_5_check)
                if gen_AVR_5 != -1:
                    AVR_5 = gen_AVR_5
            compliance_values["AVR_5_check"] = _combined_check(AVR_5_checks)
            compliance_values["AVR_5"] = AVR_5
            compliance_values["AVR_5_crvs"] = AVR_5_crv

    def __avr_curves(self) -> list[tuple[str, str | None]]:
        """The magnitude the AVR of each unit controls and its setpoint, None when the curves do
        not carry it; warns about what is missing, as the regulation cannot be checked without."""
        suffix = "_GEN_MagnitudeControlledByAVRPu"
        curves = self._get_calculated_curves()
        units = self.__units() | {
            magnitude[: -len(suffix)] for magnitude in self.__get_filtered_columns(suffix)
        }
        pairs = []
        for unit in sorted(units):
            magnitude, setpoint = f"{unit}{suffix}", f"{unit}_GEN_VoltageSetpointPu"
            missing = [name for name in (magnitude, setpoint) if name not in curves]
            if missing:
                _warn_not_computable("The voltage regulation", " and ".join(missing))
            pairs.append((magnitude, None if missing else setpoint))
        if not pairs:
            _warn_not_computable(
                "The voltage regulation",
                "the magnitude the AVR of a unit controls (MagnitudeControlledByAVRPu)",
            )
        return pairs

    def __calculate_frequency(
        self,
        compliance_values: dict,
    ):
        if compliance_list.contains_key(["freq_1"], self._validations):
            freq1_checks = []
            time_freq1 = -1
            f_nom = config.get_float("Dynawo", "f_nom", 50.0)
            frequencies = self.__separated_network_frequencies(f_nom)
            if not frequencies:
                _warn_not_computable("The frequency of the separated network", "a frequency")
            for frequency in frequencies:
                gen_check_freq1, gen_time_freq1 = common.check_frequency(
                    1 / f_nom,
                    frequency,
                    self.__curve_list("time"),
                )
                freq1_checks.append(gen_check_freq1)
                if gen_time_freq1 != -1:
                    time_freq1 = gen_time_freq1
            compliance_values["check_freq1"] = _combined_check(freq1_checks)
            compliance_values["time_freq1"] = time_freq1

    def __separated_network_frequencies(self, f_nom: float) -> list:
        """The frequency of the separated network, in pu of f_nom, which is what Fiche I10 bounds:
        that of the synchronous condenser when the test models one, as the frequency the units
        measure jumps for a few milliseconds at the load step; the units' own otherwise, or the
        network frequency the curves carry when they give neither."""
        sources = (("_GEN_TSO_FrequencyHz", 1.0 / f_nom), ("_GEN_NetworkFrequencyPu", 1.0))
        for suffix, to_pu in sources:
            columns = self.__get_filtered_columns(suffix)
            if columns:
                return [[value * to_pu for value in self.__curve_list(c)] for c in columns]
        if naming.NETWORK_FREQUENCY in self._get_calculated_curves():
            return [self.__curve_list(naming.NETWORK_FREQUENCY)]
        return []

    def __calculate_others(
        self,
        compliance_values: dict,
        t_event_start: float,
    ):
        bus_pdr_voltage = "BusPDR" + "_BUS_" + "Voltage"
        compliance_values["is_invalid_test"] = common.is_invalid_test(
            self.__curve_list("time"),
            self.__curve_list(bus_pdr_voltage),
            self.__curve_list("BusPDR_BUS_ActivePower"),
            self.__curve_list("BusPDR_BUS_ReactivePower"),
            t_event_start,
        )

        if compliance_list.contains_key(["static_diff"], self._validations):
            compliance_values["static_diffs"] = [
                common.get_static_diff(
                    self.__curve_list(magnitude_controlled_by_avr),
                    self.__curve_list(avr_setpoint),
                )
                if avr_setpoint is not None
                else None
                for magnitude_controlled_by_avr, avr_setpoint in self.__avr_curves()
            ]

        if compliance_list.contains_key(["imax_reac"], self._validations):
            imax_reac = -1
            imax_reac_check = True

            time_curve = self.__curve_list("time")

            active_current = {
                c.replace("_GEN_ActiveCurrentNode2", ""): c
                for c in self.__get_filtered_columns("_GEN_ActiveCurrentNode2")
            }
            reactive_current = {
                c.replace("_GEN_ReactiveCurrentNode2", ""): c
                for c in self.__get_filtered_columns("_GEN_ReactiveCurrentNode2")
            }
            units = (
                self.__units()
                | set(self._generators_imax)
                | active_current.keys()
                | reactive_current.keys()
            )
            incomplete = sorted(
                unit
                for unit in units
                if unit not in active_current or unit not in reactive_current
            )
            if not units or incomplete:
                _warn_not_computable(
                    "The reactive current priority",
                    f"both currents of {', '.join(incomplete) or 'a unit'} "
                    "(ActiveCurrentNode2, ReactiveCurrentNode2)",
                )
                imax_reac_check = checks.NOT_COMPUTABLE

            # Columns names are expected to be in the format:
            #   - <generator_id>_GEN_ActiveCurrentNode2
            #   - <generator_id>_GEN_ReactiveCurrentNode2
            # so we can match them based on the generator_id extracted from the column name
            generator_ids = sorted(set(active_current.keys()) & set(reactive_current.keys()))
            for generator_id in generator_ids:
                ip = self.__curve_list(active_current[generator_id])
                iq = self.__curve_list(reactive_current[generator_id])

                if ip is None or iq is None:
                    continue

                n = min(len(time_curve), len(ip), len(iq))
                if n == 0:
                    continue

                t = time_curve[:n]
                ip = np.array(ip[:n], dtype=float)  # None → NaN
                iq = np.array(iq[:n], dtype=float)  # None → NaN

                # I = sqrt(Ip² + Iq²), NaN where either component was None
                current_magnitude = np.hypot(ip, iq)
                # Replace NaN (originated from None values) with 0.0
                current_magnitude = np.where(np.isnan(current_magnitude), 0.0, current_magnitude)

                imax_gen_reac, imax_gen_reac_check = common.check_generator_imax(
                    self._generators_imax.get(generator_id),
                    t,
                    current_magnitude,
                    ip,
                )

                # Track worst (minimum) violating value across all generators
                if not imax_gen_reac_check:
                    imax_reac_check = False
                    if imax_reac == -1 or imax_gen_reac < imax_reac:
                        imax_reac = imax_gen_reac

            compliance_values["imax_reac"] = imax_reac
            compliance_values["imax_reac_check"] = imax_reac_check

    def __calculate_response_characteristics(
        self,
        compliance_values: dict,
        event_params: dict,
        t_event_start: float,
        time_clear: float,
    ) -> None:
        measurement_name = common.get_measurement_name(event_params["connect_to"])
        time_curve = self.__curve_list("time")
        measurement_curve = self.__curve_list(measurement_name)
        if not time_curve or not measurement_curve:
            return

        event_duration = time_clear - t_event_start

        res_reaction_time, res_reaction_target = common.get_reached_time(
            0.1,
            time_curve,
            measurement_curve,
            time_clear,
        )
        compliance_values["calc_reaction_time"] = res_reaction_time + event_duration
        compliance_values["calc_reaction_target"] = {measurement_name: res_reaction_target}

        res_rise_time, res_rise_target = common.get_rise_time(
            time_curve,
            measurement_curve,
            time_clear,
        )
        compliance_values["calc_rise_time"] = res_rise_time
        compliance_values["calc_rise_target"] = {measurement_name: res_rise_target}

        res_settling_time, _, res_settling_min, res_settling_max, calc_ss_value = (
            common.get_settling_time(
                0.05,
                time_curve,
                measurement_curve,
                time_clear,
            )
        )
        compliance_values["calc_settling_time"] = res_settling_time + event_duration
        compliance_values["calc_ss_value"] = calc_ss_value
        compliance_values["calc_settling_tube"] = {
            measurement_name: [res_settling_min, res_settling_max]
        }

    def __calculate(
        self,
        event_params: dict,
        t_event_start: float,
        time_clear: float,
    ) -> dict:
        compliance_values = {}

        self.__calculate_times(compliance_values, t_event_start)
        self.__calculate_avr(compliance_values, t_event_start)
        self.__calculate_frequency(compliance_values)
        self.__calculate_others(compliance_values, t_event_start)
        self.__calculate_response_characteristics(
            compliance_values, event_params, t_event_start, time_clear
        )

        return compliance_values

    def __create_results(
        self,
        t_event_start: float,
        compliance_values: dict,
    ) -> dict:
        # Dictionary to store the results of the validation
        results = {
            # Start time of the event
            "sim_t_event_start": t_event_start,
            # Overall compliance status
            "compliance": True,
            # Indicates if the test is invalid
            "is_invalid_test": compliance_values["is_invalid_test"],
        }
        # Add critical clearing time if available
        if self._time_cct is not None:
            results["time_cct"] = self._time_cct

        return results

    def __check_simple_times(
        self,
        results: dict,
        t_event_start: float,
        t_event_end: float,
        compliance_values: dict,
    ):
        if compliance_list.contains_key(["time_5U"], self._validations):
            _check_compliance(
                results,
                compliance_values["time_5u"],
                "time_5U",
                config.get_threshold("GridCode", "thr_time_5U", 10.0),
            )

        if compliance_list.contains_key(["time_10U"], self._validations):
            _check_compliance(
                results,
                compliance_values["time_10u"],
                "time_10U",
                config.get_threshold("GridCode", "thr_time_10U", 5.0),
            )

        if compliance_list.contains_key(["time_5P"], self._validations):
            _check_compliance(
                results,
                compliance_values["time_5p"],
                "time_5P",
                config.get_threshold("GridCode", "thr_time_5P", 10.0),
            )

        if compliance_list.contains_key(["time_10P"], self._validations):
            _check_compliance(
                results,
                compliance_values["time_10p"],
                "time_10P",
                config.get_threshold("GridCode", "thr_time_10P", 5.0),
            )

        if compliance_list.contains_key(["time_5P_clear"], self._validations):
            results["t_event_start"] = t_event_end
            _check_compliance(
                results,
                compliance_values["time_5p"] - (t_event_end - t_event_start),
                "time_5P_clear",
                config.get_threshold("GridCode", "thr_time_5P_clear", 10.0),
            )

        if compliance_list.contains_key(["time_10P_clear"], self._validations):
            results["t_event_start"] = t_event_end
            _check_compliance(
                results,
                compliance_values["time_10p"] - (t_event_end - t_event_start),
                "time_10P_clear",
                config.get_threshold("GridCode", "thr_time_10P_clear", 5.0),
            )

    def __check_composed_times(
        self,
        results: dict,
        t_event_start: float,
        t_event_end: float,
        compliance_values: dict,
    ):
        if compliance_list.contains_key(["time_5P_85U"], self._validations):
            results["time_85U"] = compliance_values["time_85u"]
            _check_compliance(
                results,
                compliance_values["time_5p"] - compliance_values["time_85u"],
                "time_5P_85U",
                config.get_threshold("GridCode", "thr_time_5P_85U", 10.0),
            )

        if compliance_list.contains_key(["time_10P_85U"], self._validations):
            results["time_85U"] = compliance_values["time_85u"]
            results["time_10P"] = compliance_values["time_10p"]
            _check_compliance(
                results,
                compliance_values["time_10p"] - compliance_values["time_85u"],
                "time_10P_85U",
                config.get_threshold("GridCode", "thr_time_10P_85U", 5.0),
            )

        if compliance_list.contains_key(["time_10Pfloor_85U"], self._validations):
            results["time_85U"] = compliance_values["time_85u"]
            results["time_10Pfloor"] = compliance_values["time_10pfloor"]
            _check_compliance(
                results,
                compliance_values["time_10pfloor"] - compliance_values["time_85u"],
                "time_10Pfloor_85U",
                config.get_threshold("GridCode", "thr_time_10Pfloor_85U", 2.0),
            )

        if compliance_list.contains_key(["time_10Pfloor_clear"], self._validations):
            results["time_10Pfloor"] = compliance_values["time_10pfloor"]
            results["t_event_start"] = t_event_end
            _check_compliance(
                results,
                compliance_values["time_10pfloor"] - (t_event_end - t_event_start),
                "time_10Pfloor_clear",
                config.get_threshold("GridCode", "thr_time_10Pfloor_clear", 2.0),
            )

        if compliance_list.contains_key(["time_85U_10P"], self._validations):
            results["time_85U"] = compliance_values["time_85u"]
            results["time_10P"] = compliance_values["time_10p"]
            _check_compliance(
                results,
                compliance_values["time_10p"] - compliance_values["time_85u"],
                "time_85U_10P",
                config.get_threshold("GridCode", "thr_time_85U_10P", 5.0),
            )

    def __check_times(
        self,
        results: dict,
        t_event_start: float,
        t_event_end: float,
        compliance_values: dict,
    ):
        self.__check_simple_times(results, t_event_start, t_event_end, compliance_values)
        self.__check_composed_times(results, t_event_start, t_event_end, compliance_values)

    def __check_disconnections(
        self,
        results: dict,
        simulation_path: Path,
        has_dynamic_model: bool,
    ):
        if (
            compliance_list.contains_key(["no_disconnection_gen"], self._validations)
            and has_dynamic_model
        ):
            results["no_disconnection_gen"], disconnection_list = _check_timeline(
                simulation_path / "timeLine/timeline.xml", "gen"
            )
            for disconnection in disconnection_list:
                dycov_logging.get_logger("Performance").debug(
                    f"Timeline disconnection. Model: {disconnection}"
                )

            if not results["no_disconnection_gen"]:
                if self._disconnection_model.gen_intline is None:
                    gen_intline_id = "Empty"
                else:
                    gen_intline_id = self._disconnection_model.gen_intline.id
                disconneted_xfmr = list(
                    set(self._disconnection_model.connection_xfmrs) & set(disconnection_list)
                )
                if len(disconneted_xfmr) == 0 and gen_intline_id not in disconnection_list:
                    results["no_disconnection_gen"] = True

            results["compliance"] &= results["no_disconnection_gen"]

        if (
            compliance_list.contains_key(["no_disconnection_load"], self._validations)
            and has_dynamic_model
        ):
            results["no_disconnection_load"], disconnection_list = _check_timeline(
                simulation_path / "timeLine/timeline.xml", "load"
            )
            for disconnection in disconnection_list:
                dycov_logging.get_logger("Performance").debug(
                    f"Timeline disconnection. Model: {disconnection}"
                )

            if not results["no_disconnection_load"]:
                if self._disconnection_model.auxload_xfmr is None:
                    auxload_xfmr_id = "Empty"
                else:
                    auxload_xfmr_id = self._disconnection_model.auxload_xfmr.id
                if (
                    self._disconnection_model.auxload.id not in disconnection_list
                    and auxload_xfmr_id not in disconnection_list
                ):
                    results["no_disconnection_load"] = True
            results["compliance"] &= results["no_disconnection_load"]

    def __check_others(
        self,
        results: dict,
        is_stable: Stability,
        is_non_synchronous: bool,
        compliance_values: dict,
    ):
        if compliance_list.contains_key(["static_diff"], self._validations):
            percentages = [
                None if static_diff is None else static_diff * 100
                for static_diff in compliance_values["static_diffs"]
            ]
            computed = [percentage for percentage in percentages if percentage is not None]
            results["static_diff"] = max(computed) if computed else -1
            results["static_diff_check"] = _combined_check(
                [
                    checks.NOT_COMPUTABLE if percentage is None else percentage < 0.2
                    for percentage in percentages
                ]
            )
            results["compliance"] &= results["static_diff_check"] is True

        if compliance_list.contains_key(["stabilized"], self._validations):
            measured = [is_stable.p, is_stable.q, is_stable.v]
            if not is_non_synchronous:
                measured += [is_stable.theta, is_stable.pi]
            stabilized = _combined_check(measured)

            results["stabilized"] = stabilized
            results["stabilized_rotor_angle"] = not is_non_synchronous
            results["compliance"] &= stabilized is True

        if compliance_list.contains_key(["imax_reac"], self._validations):
            results["imax_reac"] = compliance_values["imax_reac"]
            results["imax_reac_check"] = compliance_values["imax_reac_check"]
            results["compliance"] &= results["imax_reac_check"] is True

        if compliance_list.contains_key(["AVR_5"], self._validations):
            results["AVR_5_check"] = compliance_values["AVR_5_check"]
            results["AVR_5"] = compliance_values["AVR_5"]
            results["AVR_5_crvs"] = compliance_values["AVR_5_crvs"]
            results["compliance"] &= results["AVR_5_check"] is True

        if compliance_list.contains_key(["freq_1"], self._validations):
            results["freq1"] = compliance_values["time_freq1"]
            results["freq1_check"] = compliance_values["check_freq1"]
            results["compliance"] &= results["freq1_check"] is True

    def __check(
        self,
        simulation_path: Path,
        has_dynamic_model: bool,
        is_stable: Stability,
        t_event_start: float,
        t_event_end: float,
        is_non_synchronous: bool,
        compliance_values: dict,
    ):
        results = self.__create_results(t_event_start, compliance_values)

        self.__check_times(results, t_event_start, t_event_end, compliance_values)
        self.__check_disconnections(results, simulation_path, has_dynamic_model)
        self.__check_others(results, is_stable, is_non_synchronous, compliance_values)

        for key in [
            "calc_reaction_time",
            "calc_reaction_target",
            "calc_rise_time",
            "calc_rise_target",
            "calc_settling_time",
            "calc_ss_value",
            "calc_settling_tube",
        ]:
            if key in compliance_values:
                results[key] = compliance_values[key]

        return results

    def validate(
        self,
        oc_name: str,
        working_path: Path,
        sim_output_path: str,
        event_params: dict,
        has_reference: bool = True,
    ) -> dict:
        """Electric Performance Verification.

        Parameters
        ----------
        oc_name: str
            Operating condition name (Not used in this validator).
        working_path: Path
            Working path.
        sim_output_path: str
            Simulator output path.
        event_params: dict
            Event parameters
        has_reference: bool, optional
            Indicates whether reference curves are available for the validation.

        Returns
        -------
        dict
            Dictionary containing the compliance results, including:
            {
                'sim_t_event_start': float,  # Start time of the event
                'compliance': bool,  # Overall compliance status
                'is_invalid_test': bool,  # Indicates if the test is invalid
                'time_cct': float,  # Critical clearing time (if available)
                'first_steady_pos': int,  # Position of the first steady state
                'curves': dict,  # Calculated curves from the simulation
                'reference_curves': DataFrame,  # Reference curves (if available)
                'time_5U': float,  # Time for 5% voltage deviation (if applicable)
                'time_10U': float,  # Time for 10% voltage deviation (if applicable)
                'time_5P': float,  # Time for 5% active power deviation (if applicable)
                'time_10P': float,  # Time for 10% active power deviation (if applicable)
                'time_5P_clear': float,  # Time for 5% active power deviation after clearing
                    (if applicable)
                'time_10P_clear': float,  # Time for 10% active power deviation after clearing
                    (if applicable)
                'time_5P_85U': float,  # Time for 5% active power deviation at 85% voltage
                    (if applicable)
                'time_10P_85U': float,  # Time for 10% active power deviation at 85% voltage
                    (if applicable)
                'time_10Pfloor_85U': float,  # Time for 10% active power floor deviation at 85%
                    voltage (if applicable)
                'time_10Pfloor_clear': float,  # Time for 10% active power floor deviation after
                    clearing (if applicable)
                'time_85U_10P': float,  # Time for 85% voltage deviation at 10% active power
                    (if applicable)
                'no_disconnection_gen': bool,  # No generator disconnection (if applicable)
                'no_disconnection_load': bool,  # No load disconnection (if applicable)
                'static_diff': float,  # Static difference (if applicable)
                'stabilized': bool,  # Stabilization status (if applicable)
                'stabilized_rotor_angle': bool,  # The rotor angle took part in the
                    stabilization status (if applicable)
                'imax_reac': float,  # Maximum reactive current (if applicable)
                'imax_reac_check': bool,  # Maximum reactive current check status (if applicable)
                'AVR_5_check': bool,  # Plant-level voltage regulation 5% check status
                    (if applicable)
                'AVR_5': float,  # Plant-level voltage regulation 5% value (if applicable)
                'AVR_5_crvs': list,  # Plant-level voltage regulation 5% curves (if applicable)
                'freq1': float,  # Frequency deviation (if applicable)
                'freq1_check': bool,  # Frequency deviation check status (if applicable)
            }
        """
        # Validations common to all Pcs
        (
            steady_p,
            first_steady_pos_p,
            steady_q,
            first_steady_pos_q,
            steady_v,
            first_steady_pos_v,
            stable_theta,
            first_stable_pos_theta,
            pass_pi,
        ) = self.__run_common_tests(
            self._thr_ss_tol,
            self.get_sim_type() != ELECTRIC_PERFORMANCE_SM,
        )

        t_event = event_params["start_time"]
        # Calculation of the time limit for clearing faults
        time_clear = event_params["start_time"] + event_params["duration_time"]

        # Check operational point validations
        validation_values = self.__calculate(
            event_params,
            t_event,
            time_clear,
        )

        results = self.__check(
            working_path / sim_output_path,
            self._producer.is_dynawo_model(),
            Stability(steady_p, steady_q, steady_v, stable_theta, pass_pi),
            t_event,
            time_clear,
            self.get_sim_type() != ELECTRIC_PERFORMANCE_SM,
            validation_values,
        )

        if self.get_sim_type() == ELECTRIC_PERFORMANCE_SM:
            results["first_steady_pos"] = max(
                [
                    first_stable_pos_theta,
                    first_steady_pos_p,
                    first_steady_pos_q,
                    first_steady_pos_v,
                ]
            )
        else:
            results["first_steady_pos"] = max(
                [first_steady_pos_p, first_steady_pos_q, first_steady_pos_v]
            )

        results["curves"] = self._get_calculated_curves()
        if not self._get_reference_curves().empty:
            results["reference_curves"] = self._get_reference_curves()

        return results

    def get_measurement_names(self) -> list:
        """Get the list of required curves for the validation

        Returns
        -------
        list of str
            A list containing the names of the required curves for the validation.
            These curves are:
            - "BusPDR_BUS_ActivePower": The active power of the bus.
            - "BusPDR_BUS_ReactivePower": The reactive power of the bus.
            - "BusPDR_BUS_Voltage": The voltage of the bus.
        """
        return [
            "BusPDR_BUS_ActivePower",
            "BusPDR_BUS_ReactivePower",
            "BusPDR_BUS_Voltage",
        ]
