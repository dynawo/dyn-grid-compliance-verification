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

from lxml import etree

from dycov.configuration.cfg import config
from dycov.core.execution_parameters import Parameters
from dycov.core.global_variables import (
    ELECTRIC_PERFORMANCE_PPM,
    ELECTRIC_PERFORMANCE_SM,
    MODEL_VALIDATION_PPM,
)
from dycov.core.validator import Validator
from dycov.curves.manager import CurvesManager
from dycov.logging.logging import dycov_logging
from dycov.model.parameters import Stability
from dycov.validation import common, compliance_list

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
            dycov_logging.get_logger("Validation").debug(
                f"Timeline disconnection. Model: {timeline_event.get('modelName')}"
            )

    return no_error, disconnection_list


class PerformanceValidator(Validator):
    def __init__(
        self,
        curves_manager: CurvesManager,
        parameters: Parameters,
        stable_time: float,
        validations: list,
        is_field_measurements: bool,
    ):
        super(PerformanceValidator, self).__init__(
            curves_manager, parameters, validations, is_field_measurements
        )
        self._stable_time = stable_time

    def __curve_list(self, curve_name: str) -> list:
        return list(self._get_calculated_curve_by_name(curve_name))

    def __run_common_tests(
        self,
        stable_time: float,
        is_ppm: bool,
    ) -> tuple[bool, int, bool, int, bool, int, bool, int, bool]:
        bus_pdr_voltage = "BusPDR" + "_BUS_" + "Voltage"
        # Run stabilization test
        steady_v, first_steady_pos_v = common.is_stable(
            self.__curve_list("time"),
            self.__curve_list(bus_pdr_voltage),
            stable_time,
        )

        steady_p, first_steady_pos_p = common.is_stable(
            self.__curve_list("time"),
            self.__curve_list("BusPDR_BUS_ActivePower"),
            stable_time,
        )

        steady_q, first_steady_pos_q = common.is_stable(
            self.__curve_list("time"),
            self.__curve_list("BusPDR_BUS_ReactivePower"),
            stable_time,
        )

        stable_theta = False
        first_stable_pos_theta = 0
        pass_pi = False
        if not is_ppm:
            stable_theta, first_stable_pos_theta, pass_pi = self._check_theta_stability(
                stable_time
            )

        if not steady_p:
            dycov_logging.get_logger("Validation").warning("P has not reached steady state")
        if not steady_q:
            dycov_logging.get_logger("Validation").warning("Q has not reached steady state")
        if not steady_v:
            dycov_logging.get_logger("Validation").warning("V has not reached steady state")

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

    def _check_theta_stability(self, stable_time: float) -> tuple[bool, int, bool]:
        stable_theta = True
        first_stable_pos_theta = len(self._get_calculated_curve_by_name("time"))
        pass_pi = True
        internal_angle_keys = [
            key for key in self._get_calculated_curves().keys() if key.endswith("_InternalAngle")
        ]
        for key in internal_angle_keys:

            gen_stable_theta, gen_first_stable_pos_theta = common.is_stable(
                self.__curve_list("time"),
                self.__curve_list(key),
                stable_time,
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
            dycov_logging.get_logger("Validation").warning("Theta has not reached stabilization")
        if not pass_pi:
            dycov_logging.get_logger("Validation").warning(
                "Theta has not met the success criterion"
            )

        return stable_theta, first_stable_pos_theta, pass_pi

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
                0.85,
                self.__curve_list("time"),
                self.__curve_list(bus_pdr_voltage),
                t_event_start,
            )

        if compliance_list.contains_key(["time_10Pfloor_85U"], self._validations):
            compliance_values["time_85u"] = common.get_txu(
                0.85,
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
            AVR_5_check = True
            AVR_5 = -1
            filter_col = self.__get_filtered_columns("_GEN_MagnitudeControlledByAVRPu")
            for curve_name in filter_col:
                generator_id = curve_name.replace("_GEN_MagnitudeControlledByAVRPu", "")
                magnitude_controlled_by_avr = generator_id + "_GEN_" + "MagnitudeControlledByAVRPu"
                avr_setpoint = generator_id + "_GEN_" + "AVRSetpointPu"
                gen_AVR_5_check, gen_AVR_5 = common.get_AVR_x(
                    self.__curve_list("time"),
                    self.__curve_list(magnitude_controlled_by_avr),
                    self.__curve_list(avr_setpoint),
                    t_event_start,
                )
                AVR_5_crv.append(self.__curve_list(avr_setpoint))
                AVR_5_check &= gen_AVR_5_check
                if gen_AVR_5 != -1:
                    AVR_5 = gen_AVR_5
            compliance_values["AVR_5_check"] = AVR_5_check
            compliance_values["AVR_5"] = AVR_5
            compliance_values["AVR_5_crvs"] = AVR_5_crv

    def __calculate_frequency(
        self,
        compliance_values: dict,
    ):
        if compliance_list.contains_key(["freq_1"], self._validations):
            check_freq1 = True
            time_freq1 = -1
            f_nom = config.get_float("Global", "f_nom", 50.0)
            filter_col = self.__get_filtered_columns("_GEN_NetworkFrequencyPu")
            for curve_name in filter_col:
                gen_check_freq1, gen_time_freq1 = common.check_frequency(
                    1 / f_nom,
                    self.__curve_list(curve_name),
                    self.__curve_list("time"),
                )
                check_freq1 &= gen_check_freq1
                if gen_time_freq1 != -1:
                    time_freq1 = gen_time_freq1
            compliance_values["check_freq1"] = check_freq1
            compliance_values["time_freq1"] = time_freq1

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
            max_static_diff = 0
            filter_col = [
                col
                for col in self._get_calculated_curves()
                if col.endswith("_GEN_MagnitudeControlledByAVRPu")
            ]
            for curve_name in filter_col:
                generator_id = curve_name.replace("_GEN_MagnitudeControlledByAVRPu", "")
                magnitude_controlled_by_avr = generator_id + "_GEN_" + "MagnitudeControlledByAVRPu"
                avr_setpoint = generator_id + "_GEN_" + "AVRSetpointPu"

                static_diff = common.get_static_diff(
                    self.__curve_list(magnitude_controlled_by_avr),
                    self.__curve_list(avr_setpoint),
                )
                if max_static_diff < static_diff:
                    max_static_diff = static_diff
            compliance_values["static_diff"] = max_static_diff

        if compliance_list.contains_key(["imax_reac"], self._validations):
            imax_reac = -1
            imax_reac_check = True
            filter_col = self.__get_filtered_columns("_GEN_InjectedCurrent")
            for curve_name in filter_col:
                generator_id = curve_name.replace("_GEN_InjectedCurrent", "")
                injected_current = generator_id + "_GEN_" + "InjectedCurrent"
                injected_active_current = generator_id + "_GEN_" + "InjectedActiveCurrent"

                imax_gen_reac, imax_gen_reac_check = common.check_generator_imax(
                    self._generators_imax[generator_id],
                    self.__curve_list("time"),
                    self.__curve_list(injected_current),
                    self.__curve_list(injected_active_current),
                )
                if not imax_gen_reac_check:
                    if imax_reac_check:
                        imax_reac = imax_gen_reac
                        imax_reac_check = imax_gen_reac_check
                    elif imax_gen_reac < imax_reac:
                        imax_reac = imax_gen_reac
            compliance_values["imax_reac"] = imax_reac
            compliance_values["imax_reac_check"] = imax_reac_check

    def __calculate(
        self,
        t_event_start: float,
    ) -> dict:
        compliance_values = {}

        self.__calculate_times(compliance_values, t_event_start)
        self.__calculate_avr(compliance_values, t_event_start)
        self.__calculate_frequency(compliance_values)
        self.__calculate_others(compliance_values, t_event_start)

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
                10.0,
            )

        if compliance_list.contains_key(["time_10U"], self._validations):
            _check_compliance(
                results,
                compliance_values["time_10u"],
                "time_10U",
                5.0,
            )

        if compliance_list.contains_key(["time_5P"], self._validations):
            _check_compliance(
                results,
                compliance_values["time_5p"],
                "time_5P",
                10.0,
            )

        if compliance_list.contains_key(["time_10P"], self._validations):
            _check_compliance(
                results,
                compliance_values["time_10p"],
                "time_10P",
                5.0,
            )

        if compliance_list.contains_key(["time_5P_clear"], self._validations):
            results["t_event_start"] = t_event_end
            _check_compliance(
                results,
                compliance_values["time_5p"] - (t_event_end - t_event_start),
                "time_5P_clear",
                10.0,
            )

        if compliance_list.contains_key(["time_10P_clear"], self._validations):
            results["t_event_start"] = t_event_end
            _check_compliance(
                results,
                compliance_values["time_10p"] - (t_event_end - t_event_start),
                "time_10P_clear",
                5.0,
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
                10.0,
            )

        if compliance_list.contains_key(["time_10P_85U"], self._validations):
            results["time_85U"] = compliance_values["time_85u"]
            results["time_10P"] = compliance_values["time_10p"]
            _check_compliance(
                results,
                compliance_values["time_10p"] - compliance_values["time_85u"],
                "time_10P_85U",
                5.0,
            )

        if compliance_list.contains_key(["time_10Pfloor_85U"], self._validations):
            results["time_85U"] = compliance_values["time_85u"]
            results["time_10Pfloor"] = compliance_values["time_10pfloor"]
            _check_compliance(
                results,
                compliance_values["time_10pfloor"] - compliance_values["time_85u"],
                "time_10Pfloor_85U",
                2.0,
            )

        if compliance_list.contains_key(["time_10Pfloor_clear"], self._validations):
            results["time_10Pfloor"] = compliance_values["time_10pfloor"]
            results["t_event_start"] = t_event_end
            _check_compliance(
                results,
                compliance_values["time_10pfloor"] - (t_event_end - t_event_start),
                "time_10Pfloor_clear",
                2.0,
            )

        if compliance_list.contains_key(["time_85U_10P"], self._validations):
            results["time_85U"] = compliance_values["time_85u"]
            results["time_10P"] = compliance_values["time_10p"]
            _check_compliance(
                results,
                compliance_values["time_10p"] - compliance_values["time_85u"],
                "time_85U_10P",
                5.0,
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
            if not results["no_disconnection_gen"]:
                if self._disconnection_model.gen_intline is None:
                    gen_intline_id = "Empty"
                else:
                    gen_intline_id = self._disconnection_model.gen_intline.id
                disconneted_xfmr = list(
                    set(self._disconnection_model.stepup_xfmrs) & set(disconnection_list)
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
        is_ppm: bool,
        compliance_values: dict,
    ):
        if compliance_list.contains_key(["static_diff"], self._validations):
            _check_compliance(
                results,
                compliance_values["static_diff"],
                "static_diff",
                0.2,
                100,
            )

        if compliance_list.contains_key(["stabilized"], self._validations):
            if not is_ppm:
                stabilized = (
                    is_stable.p
                    and is_stable.q
                    and is_stable.v
                    and is_stable.theta
                    and is_stable.pi
                )
            else:
                stabilized = is_stable.p and is_stable.q and is_stable.v

            results["stabilized"] = stabilized
            results["compliance"] &= stabilized

        if compliance_list.contains_key(["imax_reac"], self._validations):
            results["imax_reac"] = compliance_values["imax_reac"]
            results["imax_reac_check"] = compliance_values["imax_reac_check"]
            results["compliance"] &= results["imax_reac_check"]

        if compliance_list.contains_key(["AVR_5"], self._validations):
            results["AVR_5_check"] = compliance_values["AVR_5_check"]
            results["AVR_5"] = compliance_values["AVR_5"]
            results["AVR_5_crvs"] = compliance_values["AVR_5_crvs"]

        if compliance_list.contains_key(["freq_1"], self._validations):
            results["freq1"] = compliance_values["time_freq1"]
            results["freq1_check"] = compliance_values["check_freq1"]
            results["compliance"] &= results["freq1_check"]

    def __check(
        self,
        simulation_path: Path,
        has_dynamic_model: bool,
        is_stable: Stability,
        t_event_start: float,
        t_event_end: float,
        is_ppm: bool,
        compliance_values: dict,
    ):
        results = self.__create_results(t_event_start, compliance_values)

        self.__check_times(results, t_event_start, t_event_end, compliance_values)
        self.__check_disconnections(results, simulation_path, has_dynamic_model)
        self.__check_others(results, is_stable, is_ppm, compliance_values)

        return results

    def validate(
        self,
        oc_name: str,
        working_path: Path,
        sim_output_path: str,
        event_params: dict,
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
                'imax_reac': float,  # Maximum reactive current (if applicable)
                'imax_reac_check': bool,  # Maximum reactive current check status (if applicable)
                'AVR_5_check': bool,  # AVR 5% check status (if applicable)
                'AVR_5': float,  # AVR 5% value (if applicable)
                'AVR_5_crvs': list,  # AVR 5% curves (if applicable)
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
            self._stable_time,
            self.get_sim_type() == ELECTRIC_PERFORMANCE_PPM
            or self.get_sim_type() == MODEL_VALIDATION_PPM,
        )

        t_event = event_params["start_time"]
        # Calculation of the time limit for clearing faults
        time_clear = event_params["start_time"] + event_params["duration_time"]

        # Check operational point validations
        validation_values = self.__calculate(
            t_event,
        )

        results = self.__check(
            working_path / sim_output_path,
            self._producer.is_dynawo_model(),
            Stability(steady_p, steady_q, steady_v, stable_theta, pass_pi),
            t_event,
            time_clear,
            self.get_sim_type() == ELECTRIC_PERFORMANCE_PPM
            or self.get_sim_type() == MODEL_VALIDATION_PPM,
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
