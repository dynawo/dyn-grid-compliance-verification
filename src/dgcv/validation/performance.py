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

import pandas as pd
from lxml import etree

from dgcv.core.execution_parameters import Parameters
from dgcv.core.global_variables import (
    ELECTRIC_PERFORMANCE_PPM,
    ELECTRIC_PERFORMANCE_SM,
    MODEL_VALIDATION_PPM,
)
from dgcv.core.validator import Stability, Validator
from dgcv.files import manage_files
from dgcv.logging.logging import dgcv_logging
from dgcv.validation import common, compliance_list


GENERATOR_DISCONNECT_MSG = "GENERATOR : disconnecting"
LOAD_DISCONNECT_MSG = "LOAD : disconnecting"


def _check_compliance(
    results: dict,
    compliance_value: float,
    results_name: str,
    threshold: float,
    scale: float = 1.0,
):
    if results_name not in results:
        results[results_name] = compliance_value * scale
    else:
        dgcv_logging.get_logger("Validation").warning(
            f"Key '{results_name}' already exists in results"
        )
    if threshold is not None:
        results[results_name + "_check"] = results[results_name] < threshold
        results["compliance"] &= results[results_name + "_check"]


def _get_disconnection_list(timeline_file: Path, message: str) -> list:
    # Load timeline file
    try:
        timeline = etree.parse(timeline_file, etree.XMLParser(remove_blank_text=True))
    except (etree.XMLSyntaxError, OSError) as e:
        dgcv_logging.get_logger("Validation").error(
            f"Error parsing timeline file '{timeline_file}' in '_get_disconnection_list': {e}"
        )
        return []

    disconnection_list = []

    # Get the root element and namespace
    root = timeline.getroot()
    ns = etree.QName(root).namespace or ""

    # Look for element disconnection event
    for timeline_event in root.iter(f"{{{ns}}}event"):
        if timeline_event.get("message") == message:
            model_name = timeline_event.get("modelName")
            disconnection_list.append(model_name)
            dgcv_logging.get_logger("Validation").debug(
                f"Timeline disconnection. Model: {model_name}"
            )

    # Return the list of disconnected models
    return disconnection_list


def _check_timeline(timeline_file: Path, element_type: str) -> tuple[bool, list]:
    disconnection_list = (
        _get_disconnection_list(timeline_file, GENERATOR_DISCONNECT_MSG)
        if element_type == "gen"
        else _get_disconnection_list(timeline_file, LOAD_DISCONNECT_MSG)
    )

    return len(disconnection_list) > 0, disconnection_list


def _check_stabilization(
    variable: str, time_list: list, value_list: list, stable_time: float
) -> tuple[bool, int]:
    try:
        steady, first_steady_pos = common.is_stable(time_list, value_list, stable_time)
        if not steady:
            dgcv_logging.get_logger("Validation").warning(
                f"{variable} has not reached steady state"
            )
    except Exception as e:
        dgcv_logging.get_logger("Validation").error(
            f"Error checking stabilization for {variable}: {e}"
        )
        steady, first_steady_pos = False, -1
    return steady, first_steady_pos


def _update_theta_stabilization(
    stable_theta: bool,
    time_list: list,
    curve: list,
    stable_time: float,
    first_stable_pos_theta: int,
) -> tuple[bool, int]:
    stable_theta, gen_first_stable_pos_theta = _check_stabilization(
        "Theta", time_list, curve, stable_time
    )
    if gen_first_stable_pos_theta < first_stable_pos_theta:
        first_stable_pos_theta = gen_first_stable_pos_theta
    return stable_theta, first_stable_pos_theta


def _check_all_theta_stabilization(
    time_list: list, theta_curves: list, stable_time: float
) -> tuple[bool, int]:
    first_stable_pos_theta = len(time_list)
    stable_theta = True
    for theta_curve in theta_curves:
        stable_theta, first_stable_pos_theta = _update_theta_stabilization(
            stable_theta, time_list, theta_curve, stable_time, first_stable_pos_theta
        )
        if not stable_theta:
            dgcv_logging.get_logger("Validation").warning("Theta has not reached stabilization")
            break

    return stable_theta, first_stable_pos_theta


def _check_all_theta_pi(time_list: list, theta_curves: list) -> bool:
    pass_pi = True
    for theta_curve in theta_curves:
        pass_pi = common.theta_pi(time_list, theta_curve)
        if not pass_pi:
            dgcv_logging.get_logger("Validation").warning(
                "Theta has not met the success criterion"
            )
            break
    return pass_pi


def _check_theta_stability(curves: pd.DataFrame, stable_time: float) -> tuple[bool, int, bool]:
    time_list = list(curves["time"])
    theta_curves = [
        curves[curve_name].tolist()
        for curve_name in curves.keys()
        if curve_name.endswith("_InternalAngle")
    ]
    stable_theta, first_stable_pos_theta = _check_all_theta_stabilization(
        time_list, theta_curves, stable_time
    )
    pass_pi = _check_all_theta_pi(time_list, theta_curves)
    return stable_theta, first_stable_pos_theta, pass_pi


def _run_common_tests(
    curves: pd.DataFrame,
    stable_time: float,
    is_ppm: bool,
) -> tuple[bool, int, bool, int, bool, int, bool, int, bool]:
    bus_pdr_voltage = "BusPDR_BUS_Voltage"
    time_list = list(curves["time"])
    voltage_list = list(curves[bus_pdr_voltage])
    active_power_list = list(curves["BusPDR_BUS_ActivePower"])
    reactive_power_list = list(curves["BusPDR_BUS_ReactivePower"])

    steady_v, first_steady_pos_v = _check_stabilization("V", time_list, voltage_list, stable_time)
    steady_p, first_steady_pos_p = _check_stabilization(
        "P", time_list, active_power_list, stable_time
    )
    steady_q, first_steady_pos_q = _check_stabilization(
        "Q", time_list, reactive_power_list, stable_time
    )

    stable_theta, first_stable_pos_theta, pass_pi = (False, 0, False)
    if not is_ppm:
        stable_theta, first_stable_pos_theta, pass_pi = _check_theta_stability(curves, stable_time)

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


def _get_generator_static_diff(generator_id, curves):
    magnitude_controlled_by_avr = f"{generator_id}_GEN_MagnitudeControlledByAVRPu"
    avr_setpoint = f"{generator_id}_GEN_AVRSetpointPu"
    return common.get_static_diff(
        list(curves[magnitude_controlled_by_avr]),
        list(curves[avr_setpoint]),
    )


def _add_static_diff(compliance_values, curves):
    max_static_diff = 0
    filtered_curves = curves.filter(regex="_GEN_MagnitudeControlledByAVRPu$").columns
    for curve_name in filtered_curves:
        generator_id = curve_name.replace("_GEN_MagnitudeControlledByAVRPu", "")
        static_diff = _get_generator_static_diff(generator_id, curves)
        if max_static_diff < static_diff:
            max_static_diff = static_diff
    compliance_values["static_diff"] = max_static_diff


def _add_time_5u(compliance_values, curves, t_event_start, bus_pdr_voltage):
    compliance_values["time_5u"] = common.get_txu_relative(
        0.05,
        list(curves["time"]),
        list(curves[bus_pdr_voltage]),
        t_event_start,
    )


def _add_time_10u(compliance_values, curves, t_event_start, bus_pdr_voltage):
    compliance_values["time_10u"] = common.get_txu_relative(
        0.10,
        list(curves["time"]),
        list(curves[bus_pdr_voltage]),
        t_event_start,
    )


def _add_time_5p(compliance_values, curves, t_event_start):
    compliance_values["time_5p"] = common.get_txp(
        0.05,
        list(curves["time"]),
        list(curves["BusPDR_BUS_ActivePower"]),
        t_event_start,
    )


def _add_time_10p(compliance_values, curves, t_event_start):
    compliance_values["time_10p"] = common.get_txp(
        0.1,
        list(curves["time"]),
        list(curves["BusPDR_BUS_ActivePower"]),
        t_event_start,
    )


def _add_time_85u(compliance_values, curves, t_event_start, bus_pdr_voltage):
    compliance_values["time_85u"] = common.get_txu(
        0.85,
        list(curves["time"]),
        list(curves[bus_pdr_voltage]),
        t_event_start,
    )


def _add_time_10pfloor(compliance_values, curves, t_event_start):
    compliance_values["time_10pfloor"] = common.get_txpfloor(
        0.1,
        list(curves["time"]),
        list(curves["BusPDR_BUS_ActivePower"]),
        t_event_start,
    )


def _add_time_10pfloor_clear(compliance_values, curves, t_event_start):
    compliance_values["time_10pfloor"] = common.get_txpfloor(
        0.1,
        list(curves["time"]),
        list(curves["BusPDR_BUS_ActivePower"]),
        t_event_start,
    )


def _get_avr_setpoint_curves(curves):
    filtered_curves = curves.filter(regex="_GEN_AVRSetpointPu$").columns
    return [curves[avr_setpoint].tolist() for avr_setpoint in filtered_curves]


def _check_avr_5(curves, t_event_start):
    time_curve = list(curves["time"])
    filtered_curves = curves.filter(regex="_GEN_MagnitudeControlledByAVRPu$").columns
    for magnitude_controlled_by_avr in filtered_curves:
        magnitude_controlled_by_avr_curve = list(curves[magnitude_controlled_by_avr])
        avr_setpoint = magnitude_controlled_by_avr.replace(
            "_GEN_MagnitudeControlledByAVRPu", "_GEN_AVRSetpointPu"
        )
        avr_setpoint_curve = list(curves[avr_setpoint])
        AVR_5_check, AVR_5_error_time = common.get_AVR_x(
            time_curve,
            magnitude_controlled_by_avr_curve,
            avr_setpoint_curve,
            t_event_start,
        )
        if not AVR_5_check:
            return AVR_5_check, AVR_5_error_time

    return True, -1


def _add_avr_5(compliance_values, curves, t_event_start):
    AVR_5_check, AVR_5_error_time = _check_avr_5(curves, t_event_start)
    compliance_values["AVR_5_check"] = AVR_5_check
    compliance_values["AVR_5"] = AVR_5_error_time
    compliance_values["AVR_5_crvs"] = _get_avr_setpoint_curves(curves)


def _check_freq_1(curves):
    filtered_curves = curves.filter(regex="_GEN_NetworkFrequencyPu$").columns
    for curve_name in filtered_curves:
        check_freq1, error_time_freq1 = common.check_frequency(
            1 / 50,
            list(curves[curve_name]),
            list(curves["time"]),
        )
        if not check_freq1:
            return check_freq1, error_time_freq1

    return True, -1


def _add_freq_1(compliance_values, curves):
    check_freq1, error_time_freq1 = _check_freq_1(curves)
    compliance_values["check_freq1"] = check_freq1
    compliance_values["time_freq1"] = error_time_freq1


class PerformanceValidator(Validator):
    """
    PerformanceValidator is responsible for validating the performance of electric models
    based on various compliance criteria. It checks for stabilization, disconnections,
    and other performance metrics using the provided simulation data.

    Attributes:
        parameters (Parameters): Execution parameters for the validation.
        stable_time (float): Time duration to check for stability.
        validations (list): List of validations to be performed.
        is_field_measurements (bool): Flag indicating if field measurements are used.

    Methods:
        validate(oc_name, working_path, sim_output_path, event_params, fs):
            Validates the performance based on the provided parameters and simulation data.
        get_measurement_names():
            Returns the list of required curves for the validation.
    """

    def __init__(
        self,
        parameters: Parameters,
        stable_time: float,
        validations: list,
        is_field_measurements: bool,
    ):
        super().__init__(validations, is_field_measurements)
        self._producer = parameters.get_producer()
        self._stable_time = stable_time

    def _get_generator_imax_reac(self, curves, curve_name):
        generator_id = curve_name.replace("_GEN_InjectedCurrent", "")
        injected_current = generator_id + "_GEN_" + "InjectedCurrent"
        injected_active_current = generator_id + "_GEN_" + "InjectedActiveCurrent"

        return common.check_generator_imax(
            self._generators_imax[generator_id],
            list(curves["time"]),
            list(curves[injected_current]),
            list(curves[injected_active_current]),
        )

    def __add_imax_reac(self, compliance_values, curves):
        imax_reac = -1
        imax_reac_check = True
        filtered_curves = curves.filter(regex="_GEN_InjectedCurrent$").columns
        for curve_name in filtered_curves:
            imax_gen_reac, imax_gen_reac_check = self._get_generator_imax_reac(curves, curve_name)
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
        curves: pd.DataFrame,
        t_event_start: float,
    ) -> dict:
        compliance_values = {}

        static_diff_check = compliance_list.contains_key(["static_diff"], self._validations)
        time_5u_check = compliance_list.contains_key(["time_5U"], self._validations)
        time_10u_check = compliance_list.contains_key(["time_10U"], self._validations)
        time_5p_check = compliance_list.contains_key(
            ["time_5P", "time_5P_85U", "time_5P_clear"], self._validations
        )
        time_10p_check = compliance_list.contains_key(
            ["time_10P", "time_10P_85U", "time_10P_clear"], self._validations
        )
        time_5p_85u_check = compliance_list.contains_key(
            ["time_5P_85U", "time_10P_85U"], self._validations
        )
        time_10pfloor_85u_check = compliance_list.contains_key(
            ["time_10Pfloor_85U"], self._validations
        )
        time_10pfloor_clear_check = compliance_list.contains_key(
            ["time_10Pfloor_clear"], self._validations
        )
        imax_reac_check = compliance_list.contains_key(["imax_reac"], self._validations)
        avr_5_check = compliance_list.contains_key(["AVR_5"], self._validations)
        freq_1_check = compliance_list.contains_key(["freq_1"], self._validations)

        if static_diff_check:
            _add_static_diff(compliance_values, curves)

        bus_pdr_voltage = "BusPDR_BUS_Voltage"
        compliance_values["is_invalid_test"] = common.is_invalid_test(
            list(curves["time"]),
            list(curves[bus_pdr_voltage]),
            list(curves["BusPDR_BUS_ActivePower"]),
            list(curves["BusPDR_BUS_ReactivePower"]),
            t_event_start,
        )

        if time_5u_check:
            _add_time_5u(compliance_values, curves, t_event_start, bus_pdr_voltage)

        if time_10u_check:
            _add_time_10u(compliance_values, curves, t_event_start, bus_pdr_voltage)

        if time_5p_check:
            _add_time_5p(compliance_values, curves, t_event_start)

        if time_10p_check:
            _add_time_10p(compliance_values, curves, t_event_start)

        if time_5p_85u_check:
            _add_time_85u(compliance_values, curves, t_event_start, bus_pdr_voltage)

        if time_10pfloor_85u_check:
            _add_time_85u(compliance_values, curves, t_event_start, bus_pdr_voltage)
            _add_time_10pfloor(compliance_values, curves, t_event_start)

        if time_10pfloor_clear_check:
            _add_time_10pfloor_clear(compliance_values, curves, t_event_start)

        if imax_reac_check:
            self.__add_imax_reac(compliance_values, curves)

        if avr_5_check:
            _add_avr_5(compliance_values, curves, t_event_start)

        if freq_1_check:
            _add_freq_1(compliance_values, curves)

        return compliance_values

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
        results = self._initialize_results(t_event_start, compliance_values)
        self._check_static_diff(results, compliance_values)
        self._check_time_compliance(results, compliance_values, t_event_start, t_event_end)
        self._check_stabilization(results, is_stable, is_ppm)
        self._check_disconnections(results, simulation_path, has_dynamic_model)
        self._check_imax_reac(results, compliance_values)
        self._check_avr_5(results, compliance_values)
        self._check_freq_1(results, compliance_values)
        return results

    def _initialize_results(self, t_event_start: float, compliance_values: dict) -> dict:
        results = {
            "sim_t_event_start": t_event_start,
            "compliance": True,
            "is_invalid_test": compliance_values["is_invalid_test"],
        }
        if self._time_cct is not None:
            results["time_cct"] = self._time_cct
        return results

    def _check_static_diff(self, results: dict, compliance_values: dict):
        if compliance_list.contains_key(["static_diff"], self._validations):
            _check_compliance(
                results,
                compliance_values["static_diff"],
                "static_diff",
                0.2,
                100,
            )

    def _check_imax_reac(self, results: dict, compliance_values: dict):
        if compliance_list.contains_key(["imax_reac"], self._validations):
            results["imax_reac"] = compliance_values["imax_reac"]
            results["imax_reac_check"] = compliance_values["imax_reac_check"]
            results["compliance"] &= results["imax_reac_check"]

    def _check_time_compliance(
        self, results: dict, compliance_values: dict, t_event_start: float, t_event_end: float
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

    def _check_stabilization(self, results: dict, is_stable: Stability, is_ppm: bool):
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

    def _check_disconnections(self, results: dict, simulation_path: Path, has_dynamic_model: bool):
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

    def _check_avr_5(self, results: dict, compliance_values: dict):
        if compliance_list.contains_key(["AVR_5"], self._validations):
            results["AVR_5_check"] = compliance_values["AVR_5_check"]
            results["AVR_5"] = compliance_values["AVR_5"]
            results["AVR_5_crvs"] = compliance_values["AVR_5_crvs"]

    def _check_freq_1(self, results: dict, compliance_values: dict):
        if compliance_list.contains_key(["freq_1"], self._validations):
            results["freq1"] = compliance_values["time_freq1"]
            results["freq1_check"] = compliance_values["check_freq1"]
            results["compliance"] &= results["freq1_check"]

    def validate(
        self,
        oc_name: str,
        working_path: Path,
        sim_output_path: str,
        event_params: dict,
        fs: float,
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
        fs: float
            Frequency sampling (Not used in this validator).

        Returns
        -------
        dict
            Compliance results
        """
        calculated_curves = manage_files.read_curves(working_path / "curves_calculated.csv")
        if (working_path / "curves_reference.csv").is_file():
            reference_curves = manage_files.read_curves(working_path / "curves_reference.csv")
        else:
            reference_curves = None

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
        ) = _run_common_tests(
            calculated_curves,
            self._stable_time,
            self.get_sim_type() == ELECTRIC_PERFORMANCE_PPM
            or self.get_sim_type() == MODEL_VALIDATION_PPM,
        )

        t_event = event_params["start_time"]
        # Calculation of the time limit for clearing faults
        time_clear = event_params["start_time"] + event_params["duration_time"]

        # Check operational point validations
        validation_values = self.__calculate(
            calculated_curves,
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

        results["curves"] = calculated_curves
        if reference_curves is not None:
            results["reference_curves"] = reference_curves

        return results

    def get_measurement_names(self) -> list:
        """Get the list of required curves for the validation

        Returns
        -------
        list
            Required curves for the validation
        """
        return [
            "BusPDR_BUS_ActivePower",
            "BusPDR_BUS_ReactivePower",
            "BusPDR_BUS_Voltage",
        ]
