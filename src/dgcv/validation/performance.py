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
from dgcv.logging.logging import dgcv_logging
from dgcv.validation import common, compliance_list


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


def _check_timeline(timeline_file: Path, element_type: str) -> tuple[bool, list]:
    no_error = True
    # Load timeline file
    timeline = etree.parse(timeline_file, etree.XMLParser(remove_blank_text=True))

    # Look for generator disconnection event
    root = timeline.getroot()
    ns = etree.QName(root).namespace
    disconnection_list = []
    for timeline_event in root.iter("{%s}event" % ns):
        if timeline_event.get("message") == "GENERATOR : disconnecting" and element_type == "gen":
            no_error = False
            disconnection_list.append(timeline_event.get("modelName"))
            dgcv_logging.get_logger("Validation").debug(
                "Timeline disconnection. Model: " + timeline_event.get("modelName")
            )
        if timeline_event.get("message") == "LOAD : disconnecting" and element_type == "load":
            no_error = False
            disconnection_list.append(timeline_event.get("modelName"))
            dgcv_logging.get_logger("Validation").debug(
                "Timeline disconnection. Model: " + timeline_event.get("modelName")
            )

    return no_error, disconnection_list


def _run_common_tests(
    curves: pd.DataFrame,
    stable_time: float,
    is_ppm: bool,
) -> tuple[bool, int, bool, int, bool, int, bool, int, bool]:
    bus_pdr_voltage = "BusPDR" + "_BUS_" + "Voltage"
    # Run stabilization test
    steady_v, first_steady_pos_v = common.is_stable(
        list(curves["time"]),
        list(curves[bus_pdr_voltage]),
        stable_time,
    )

    steady_p, first_steady_pos_p = common.is_stable(
        list(curves["time"]),
        list(curves["BusPDR_BUS_ActivePower"]),
        stable_time,
    )

    steady_q, first_steady_pos_q = common.is_stable(
        list(curves["time"]),
        list(curves["BusPDR_BUS_ReactivePower"]),
        stable_time,
    )

    if not is_ppm:
        stable_theta = True
        first_stable_pos_theta = len(curves["time"])
        pass_pi = True
        for key in curves.keys():
            if not key.endswith("_InternalAngle"):
                continue

            gen_stable_theta, gen_first_stable_pos_theta = common.is_stable(
                list(curves["time"]),
                list(curves[key]),
                stable_time,
            )

            # Check +- Pi
            gen_pass_pi = common.theta_pi(
                list(curves["time"]),
                list(curves[key]),
            )
            stable_theta &= gen_stable_theta
            if gen_first_stable_pos_theta < first_stable_pos_theta:
                first_stable_pos_theta = gen_first_stable_pos_theta
            pass_pi &= gen_pass_pi

        if not stable_theta:
            dgcv_logging.get_logger("Validation").warning("Theta has not reached stabilization")
        if not pass_pi:
            dgcv_logging.get_logger("Validation").warning(
                "Theta has not met the success criterion"
            )
    else:
        stable_theta = False
        first_stable_pos_theta = 0
        pass_pi = False

    if not steady_p:
        dgcv_logging.get_logger("Validation").warning("P has not reached steady state")
    if not steady_q:
        dgcv_logging.get_logger("Validation").warning("Q has not reached steady state")
    if not steady_v:
        dgcv_logging.get_logger("Validation").warning("V has not reached steady state")

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


class PerformanceValidator(Validator):
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

    def __calculate_simple_times(
        self,
        compliance_values: dict,
        curves: pd.DataFrame,
        t_event_start: float,
    ):
        bus_pdr_voltage = "BusPDR" + "_BUS_" + "Voltage"
        if compliance_list.contains_key(["time_5U"], self._validations):
            compliance_values["time_5u"] = common.get_txu_relative(
                0.05,
                list(curves["time"]),
                list(curves[bus_pdr_voltage]),
                t_event_start,
            )

        if compliance_list.contains_key(["time_10U"], self._validations):
            compliance_values["time_10u"] = common.get_txu_relative(
                0.10,
                list(curves["time"]),
                list(curves[bus_pdr_voltage]),
                t_event_start,
            )

        if compliance_list.contains_key(["time_10Pfloor_clear"], self._validations):
            compliance_values["time_10pfloor"] = common.get_txpfloor(
                0.1,
                list(curves["time"]),
                list(curves["BusPDR_BUS_ActivePower"]),
                t_event_start,
            )

    def __calculate_composed_times(
        self,
        compliance_values: dict,
        curves: pd.DataFrame,
        t_event_start: float,
    ) -> dict:
        bus_pdr_voltage = "BusPDR" + "_BUS_" + "Voltage"
        if compliance_list.contains_key(
            ["time_5P", "time_5P_85U", "time_5P_clear"], self._validations
        ):
            compliance_values["time_5p"] = common.get_txp(
                0.05,
                list(curves["time"]),
                list(curves["BusPDR_BUS_ActivePower"]),
                t_event_start,
            )

        if compliance_list.contains_key(
            ["time_10P", "time_10P_85U", "time_10P_clear"], self._validations
        ):
            compliance_values["time_10p"] = common.get_txp(
                0.1,
                list(curves["time"]),
                list(curves["BusPDR_BUS_ActivePower"]),
                t_event_start,
            )

        if compliance_list.contains_key(["time_5P_85U", "time_10P_85U"], self._validations):
            compliance_values["time_85u"] = common.get_txu(
                0.85,
                list(curves["time"]),
                list(curves[bus_pdr_voltage]),
                t_event_start,
            )

        if compliance_list.contains_key(["time_10Pfloor_85U"], self._validations):
            compliance_values["time_85u"] = common.get_txu(
                0.85,
                list(curves["time"]),
                list(curves[bus_pdr_voltage]),
                t_event_start,
            )
            compliance_values["time_10pfloor"] = common.get_txpfloor(
                0.1,
                list(curves["time"]),
                list(curves["BusPDR_BUS_ActivePower"]),
                t_event_start,
            )

    def __calculate_times(
        self,
        compliance_values: dict,
        curves: pd.DataFrame,
        t_event_start: float,
    ):
        self.__calculate_simple_times(compliance_values, curves, t_event_start)
        self.__calculate_composed_times(compliance_values, curves, t_event_start)

    def __calculate_avr(
        self,
        compliance_values: dict,
        curves: pd.DataFrame,
        t_event_start: float,
    ):
        if compliance_list.contains_key(["AVR_5"], self._validations):
            AVR_5_crv = list()
            AVR_5_check = True
            AVR_5 = -1
            filter_col = [col for col in curves if col.endswith("_GEN_MagnitudeControlledByAVRPu")]
            for curve_name in filter_col:
                generator_id = curve_name.replace("_GEN_MagnitudeControlledByAVRPu", "")
                magnitude_controlled_by_avr = generator_id + "_GEN_" + "MagnitudeControlledByAVRPu"
                avr_setpoint = generator_id + "_GEN_" + "AVRSetpointPu"
                gen_AVR_5_check, gen_AVR_5 = common.get_AVR_x(
                    list(curves["time"]),
                    list(curves[magnitude_controlled_by_avr]),
                    list(curves[avr_setpoint]),
                    t_event_start,
                )
                AVR_5_crv.append(list(curves[avr_setpoint]))
                AVR_5_check &= gen_AVR_5_check
                if gen_AVR_5 != -1:
                    AVR_5 = gen_AVR_5
            compliance_values["AVR_5_check"] = AVR_5_check
            compliance_values["AVR_5"] = AVR_5
            compliance_values["AVR_5_crvs"] = AVR_5_crv

    def __calculate_frequency(
        self,
        compliance_values: dict,
        curves: pd.DataFrame,
    ):
        if compliance_list.contains_key(["freq_1"], self._validations):
            check_freq1 = True
            time_freq1 = -1
            filter_col = [col for col in curves if col.endswith("_GEN_NetworkFrequencyPu")]
            for curve_name in filter_col:
                gen_check_freq1, gen_time_freq1 = common.check_frequency(
                    1 / 50,
                    list(curves[curve_name]),
                    list(curves["time"]),
                )
                check_freq1 &= gen_check_freq1
                if gen_time_freq1 != -1:
                    time_freq1 = gen_time_freq1
            compliance_values["check_freq1"] = check_freq1
            compliance_values["time_freq1"] = time_freq1

    def __calculate_others(
        self,
        compliance_values: dict,
        curves: pd.DataFrame,
        t_event_start: float,
    ):
        bus_pdr_voltage = "BusPDR" + "_BUS_" + "Voltage"
        compliance_values["is_invalid_test"] = common.is_invalid_test(
            list(curves["time"]),
            list(curves[bus_pdr_voltage]),
            list(curves["BusPDR_BUS_ActivePower"]),
            list(curves["BusPDR_BUS_ReactivePower"]),
            t_event_start,
        )

        if compliance_list.contains_key(["static_diff"], self._validations):
            max_static_diff = 0
            filter_col = [col for col in curves if col.endswith("_GEN_MagnitudeControlledByAVRPu")]
            for curve_name in filter_col:
                generator_id = curve_name.replace("_GEN_MagnitudeControlledByAVRPu", "")
                magnitude_controlled_by_avr = generator_id + "_GEN_" + "MagnitudeControlledByAVRPu"
                avr_setpoint = generator_id + "_GEN_" + "AVRSetpointPu"

                static_diff = common.get_static_diff(
                    list(curves[magnitude_controlled_by_avr]),
                    list(curves[avr_setpoint]),
                )
                if max_static_diff < static_diff:
                    max_static_diff = static_diff
            compliance_values["static_diff"] = max_static_diff

        if compliance_list.contains_key(["imax_reac"], self._validations):
            imax_reac = -1
            imax_reac_check = True
            filter_col = [col for col in curves if col.endswith("_GEN_InjectedCurrent")]
            for curve_name in filter_col:
                generator_id = curve_name.replace("_GEN_InjectedCurrent", "")
                injected_current = generator_id + "_GEN_" + "InjectedCurrent"
                injected_active_current = generator_id + "_GEN_" + "InjectedActiveCurrent"

                imax_gen_reac, imax_gen_reac_check = common.check_generator_imax(
                    self._generators_imax[generator_id],
                    list(curves["time"]),
                    list(curves[injected_current]),
                    list(curves[injected_active_current]),
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
        curves: pd.DataFrame,
        t_event_start: float,
    ) -> dict:
        compliance_values = {}

        self.__calculate_times(compliance_values, curves, t_event_start)
        self.__calculate_avr(compliance_values, curves, t_event_start)
        self.__calculate_frequency(compliance_values, curves)
        self.__calculate_others(compliance_values, curves, t_event_start)

        return compliance_values

    def __create_results(
        self,
        t_event_start: float,
        compliance_values: dict,
    ) -> dict:
        results = {
            "sim_t_event_start": t_event_start,
            "compliance": True,
            "is_invalid_test": compliance_values["is_invalid_test"],
        }
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

    def __check_diconnections(
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
                if self._disconnection_model.auxload_xfmr is None:
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
        self.__check_diconnections(results, simulation_path, has_dynamic_model)
        self.__check_others(results, is_stable, is_ppm, compliance_values)

        return results

    def validate(
        self,
        oc_name: str,
        working_path: Path,
        sim_output_path: str,
        event_params: dict,
        fs: float,
        curves: dict,
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
        calculated_curves = curves["calculated"]
        calculated_curves.to_csv(working_path / "curves_calculated.csv", sep=";")
        if "reference" in curves and not curves["reference"].empty:
            reference_curves = curves["reference"]
            reference_curves.to_csv(working_path / "curves_reference.csv", sep=";")
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
