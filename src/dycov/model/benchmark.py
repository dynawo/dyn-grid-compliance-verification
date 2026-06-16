#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import logging
from dataclasses import dataclass
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.configuration.dump import dump_effective_pcs_description
from dycov.core.global_variables import CASE_SEPARATOR, MODEL_VALIDATION
from dycov.core.parameters import Parameters
from dycov.core.validator import Validator
from dycov.curves.manager import CurvesManager
from dycov.files import manage_files
from dycov.logging.logging import dycov_logging
from dycov.model.compliance import Compliance
from dycov.model.operating_condition import OperatingCondition
from dycov.model.parameters import CurvesAvailability, CurvesCheckResult, SimulationError
from dycov.model.producer import Producer
from dycov.report.types import (
    DynamicBand,
    EventMarker,
    FigureDescription,
    FinalValueBand,
    FrequencyBand,
)
from dycov.validation import compliance_list
from dycov.validation.model import ModelValidator
from dycov.validation.performance import PerformanceValidator


@dataclass(frozen=True)
class Summary:
    producer_name: str
    id: int
    zone: int
    pcs: str
    benchmark: str
    operating_condition: str
    compliance: Compliance
    report_name: str


_FAILED_RESULTS: dict = {"compliance": False, "curves": None}


def _compliance_for_missing_curves(availability: CurvesAvailability) -> Compliance:
    match availability:
        case CurvesAvailability.NO_PRODUCER:
            return Compliance.WithoutProducerCurves
        case CurvesAvailability.NO_REFERENCE:
            return Compliance.WithoutReferenceCurves
        case _:
            return Compliance.WithoutCurves


class Benchmark:
    """Second-level representation of the pcs described in the DTR.
    A pcs can contain several Benchmarks, in each Benchmark a topological model
    is defined.

    Args
    ----
    pcs_name: str
        PCS name
    pcs_id: str
        PCS id
    pcs_zone: str
        PCS zone id
    producer_name: str
        Producer name
    report_name: str
        Report name
    benchmark_name: str
        Benchmark name
    parameters: Parameters
        Tool parameters
    producer: Producer
        Producer object
    """

    def __init__(
        self,
        pcs_name: str,
        pcs_id: int,
        pcs_zone: int,
        producer_name: str,
        report_name: str,
        benchmark_name: str,
        parameters: Parameters,
        producer: Producer,
    ):
        self._pcs_name = pcs_name
        self._pcs_id = pcs_id
        self._pcs_zone = pcs_zone
        self._report_name = report_name
        self._producer_name = producer_name
        self._name = benchmark_name
        self._parameters = parameters
        self._producer = producer
        self._working_dir = parameters.get_working_dir()
        self._output_dir = parameters.get_output_dir()
        self._templates_path = Path(config.get_value("Global", "templates_path"))
        self._lib_path = Path(config.get_value("Global", "lib_path"))
        self._figures_description = None

        thr_ss_tol = config.get_float("GridCode", "thr_ss_tol", 0.002)
        (
            oc_names,
            curves_manager,
            validator,
        ) = self.__prepare_benchmark_validation(parameters, producer, thr_ss_tol)
        self._curves_manager = curves_manager
        self._validator = validator
        self._oc_list = [
            OperatingCondition(
                self._parameters,
                self._pcs_name,
                self._name,
                oc_name,
            )
            for oc_name in oc_names
        ]

    def __create_operating_condition_working_paths(self, oc_names: list):
        for oc_name in oc_names:
            working_oc_dir = (
                self._working_dir / self._producer_name / self._pcs_name / self._name / oc_name
            )
            manage_files.create_dir(working_oc_dir)

    def __prepare_benchmark_validation(
        self, parameters: Parameters, producer: Producer, thr_ss_tol: float
    ) -> tuple[list, CurvesManager | None, Validator | None]:
        pcs_benchmark_name = self._pcs_name + CASE_SEPARATOR + self._name
        oc_names = config.get_list("PCS-OperatingConditions", pcs_benchmark_name)
        self.__create_operating_condition_working_paths(oc_names)
        if parameters.get_producer().is_gfm():
            return oc_names, None, None

        curves_manager = CurvesManager(
            parameters,
            producer,
            pcs_benchmark_name,
            thr_ss_tol,
            self._lib_path,
            self._templates_path,
            self._pcs_name,
            self._producer_name,
        )
        validations = self.__initialize_validation_by_benchmark()
        if self._producer.get_sim_type() > MODEL_VALIDATION:
            validator = ModelValidator(
                curves_manager,
                pcs_benchmark_name,
                producer,
                validations,
                curves_manager.is_field_measurements(),
                self._pcs_name,
                self._name,
            )
        else:
            validator = PerformanceValidator(
                curves_manager,
                producer,
                thr_ss_tol,
                validations,
                curves_manager.is_field_measurements(),
                self._pcs_name,
                self._name,
            )

        # If it is not a pcs with multiple operating conditions, returns itself
        return oc_names, curves_manager, validator

    def __initialize_validation_by_benchmark(self) -> list:
        pcs_benchmark_name = self._pcs_name + CASE_SEPARATOR + self._name
        validations = []

        # Performance-Validations
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "static_diff"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "time_5U"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "time_5P"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "time_10U"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "time_10P"
        )
        compliance_list.append(
            validations,
            pcs_benchmark_name,
            "Performance-Validations",
            "time_85U",
            ["time_5P_85U", "time_10P_85U"],
        )
        compliance_list.append(
            validations,
            pcs_benchmark_name,
            "Performance-Validations",
            "time_clear",
            ["time_5P_clear", "time_10P_clear"],
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "time_cct"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "stabilized"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "no_disconnection_gen"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "no_disconnection_load"
        )
        compliance_list.append(validations, pcs_benchmark_name, "Performance-Validations", "AVR_5")
        if "time_10P_85U" not in validations:
            compliance_list.append(
                validations, pcs_benchmark_name, "Performance-Validations", "time_10P_85U"
            )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "freq_1"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "freq_200"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "freq_250"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "time_10Pfloor_85U"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "time_10Pfloor_clear"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Performance-Validations", "imax_reac"
        )

        # Model-Validations
        compliance_list.append(
            validations, pcs_benchmark_name, "Model-Validations", "mean_absolute_error_power_1P"
        )
        compliance_list.append(
            validations,
            pcs_benchmark_name,
            "Model-Validations",
            "mean_absolute_error_injection_1P",
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Model-Validations", "mean_absolute_error_voltage"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Model-Validations", "voltage_dips_active_power"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Model-Validations", "voltage_dips_reactive_power"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Model-Validations", "voltage_dips_active_current"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Model-Validations", "voltage_dips_reactive_current"
        )
        compliance_list.append(
            validations,
            pcs_benchmark_name,
            "Model-Validations",
            "setpoint_tracking_controlled_magnitude",
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Model-Validations", "setpoint_tracking_active_power"
        )
        compliance_list.append(
            validations,
            pcs_benchmark_name,
            "Model-Validations",
            "setpoint_tracking_reactive_power",
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Model-Validations", "active_power_recovery"
        )

        compliance_list.append(
            validations, pcs_benchmark_name, "Model-Validations", "reaction_time"
        )
        compliance_list.append(validations, pcs_benchmark_name, "Model-Validations", "rise_time")
        compliance_list.append(
            validations, pcs_benchmark_name, "Model-Validations", "response_time"
        )
        compliance_list.append(
            validations, pcs_benchmark_name, "Model-Validations", "settling_time"
        )
        compliance_list.append(validations, pcs_benchmark_name, "Model-Validations", "overshoot")
        compliance_list.append(
            validations, pcs_benchmark_name, "Model-Validations", "ramp_time_lag"
        )
        compliance_list.append(validations, pcs_benchmark_name, "Model-Validations", "ramp_error")

        self.__init_figures_description(validations)

        return validations

    def __init_figures_description(self, validations: list) -> None:
        pcs_benchmark_name = self._pcs_name + CASE_SEPARATOR + self._name
        self._figures_description = []
        self.__init_figures_v(validations, pcs_benchmark_name)
        self.__init_figures_p(validations, pcs_benchmark_name)
        self.__init_figures_q(validations, pcs_benchmark_name)
        self.__init_figures_ip(validations, pcs_benchmark_name)
        self.__init_figures_iq(validations, pcs_benchmark_name)
        self.__init_figures_w(validations, pcs_benchmark_name)
        self.__init_figures_wref(validations, pcs_benchmark_name)
        self.__init_figures_i(validations, pcs_benchmark_name)
        self.__init_figures_uit(validations, pcs_benchmark_name)
        self.__init_figures_ustator(validations, pcs_benchmark_name)
        self.__init_figures_theta(validations, pcs_benchmark_name)
        self.__init_figures_tap(validations, pcs_benchmark_name)
        self.__init_figures_sync_cond_p(validations, pcs_benchmark_name)
        self.__init_figures_sync_cond_q(validations, pcs_benchmark_name)
        self.__init_figures_sync_cond_freq(validations, pcs_benchmark_name)
        self.__init_figures_load_p(validations, pcs_benchmark_name)
        self.__init_figures_load_q(validations, pcs_benchmark_name)

    def __init_figures_v(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_V = config.get_list("ReportCurves", "fig_V")
        if pcs_benchmark_name not in fig_V:
            return

        has_85u = (
            "time_5P_85U" in validations
            or "time_10P_85U" in validations
            or "time_10Pfloor_85U" in validations
        )
        event_markers = [EventMarker(source_key="time_85U")] if has_85u else []

        self._figures_description.append(
            FigureDescription(
                name="fig_V",
                variables=[{"type": "bus", "variable": "Voltage"}],
                ylabel="V (pu base Unom)",
                event_markers=event_markers,
            )
        )

    def __init_figures_p(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_P = config.get_list("ReportCurves", "fig_P")
        if pcs_benchmark_name not in fig_P:
            return

        tolerance_band = None
        if "time_10Pfloor_85U" in validations or "time_10Pfloor_clear" in validations:
            tolerance_band = FinalValueBand(upper=None, lower=10.0, color="#55a868")
        elif "time_5P" in validations:
            tolerance_band = FinalValueBand(upper=5.0, lower=5.0, color="#c44e52")
        elif "time_10P" in validations or "time_10P_85U" in validations:
            tolerance_band = FinalValueBand(upper=10.0, lower=10.0, color="#55a868")

        if self._producer.is_dynawo_model():
            p_label = f"P (pu base Snom = {self._producer.s_nom}MVA)"
        else:
            p_label = "P (pu base Snom)"

        self._figures_description.append(
            FigureDescription(
                name="fig_P",
                variables="BusPDR_BUS_ActivePower",
                ylabel=p_label,
                tolerance_band=tolerance_band,
            )
        )

    def __init_figures_q(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_Q = config.get_list("ReportCurves", "fig_Q")
        if pcs_benchmark_name not in fig_Q:
            return

        if self._producer.is_dynawo_model():
            q_label = f"Q (pu base Snom = {self._producer.s_nom}MVA)"
        else:
            q_label = "Q (pu base Snom)"

        self._figures_description.append(
            FigureDescription(
                name="fig_Q",
                variables="BusPDR_BUS_ReactivePower",
                ylabel=q_label,
            )
        )

    def __init_figures_ip(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_Ip = config.get_list("ReportCurves", "fig_Ip")
        if pcs_benchmark_name not in fig_Ip:
            return

        if self._producer.is_dynawo_model():
            ip_label = f"Ip (pu base Unom, Snom = {self._producer.s_nom}MVA)"
        else:
            ip_label = "Ip (pu base Unom, Snom)"

        self._figures_description.append(
            FigureDescription(
                name="fig_Ip",
                variables="BusPDR_BUS_ActiveCurrent",
                ylabel=ip_label,
            )
        )

    def __init_figures_iq(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_Iq = config.get_list("ReportCurves", "fig_Iq")
        if pcs_benchmark_name not in fig_Iq:
            return

        if self._producer.is_dynawo_model():
            iq_label = f"Iq (pu base Unom, Snom = {self._producer.s_nom}MVA)"
        else:
            iq_label = "Iq (pu base Unom, Snom)"

        self._figures_description.append(
            FigureDescription(
                name="fig_Iq",
                variables="BusPDR_BUS_ReactiveCurrent",
                ylabel=iq_label,
            )
        )

    def __init_figures_w(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_W = config.get_list("ReportCurves", "fig_W")
        if pcs_benchmark_name not in fig_W:
            return

        self._figures_description.append(
            FigureDescription(
                name="fig_W",
                variables=[{"type": "generator", "variable": "RotorSpeedPu"}],
                ylabel=r"$\omega$ (Hz)",
            )
        )

    def __init_figures_wref(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_WRef = config.get_list("ReportCurves", "fig_WRef")
        if pcs_benchmark_name not in fig_WRef:
            return

        frequency_band = None
        if "freq_1" in validations:
            frequency_band = FrequencyBand(upper=1.0, lower=1.0)
        elif "freq_250" in validations:
            frequency_band = FrequencyBand(upper=0.250, lower=0.250)
        elif "freq_200" in validations:
            frequency_band = FrequencyBand(upper=0.2, lower=0.2)

        self._figures_description.append(
            FigureDescription(
                name="fig_WRef",
                variables=[{"type": "generator", "variable": "NetworkFrequencyPu"}],
                ylabel=r"$\omega$ (Hz)",
                frequency_band=frequency_band,
            )
        )

    def __init_figures_i(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_I = config.get_list("ReportCurves", "fig_I")
        if pcs_benchmark_name not in fig_I:
            return

        tolerance_band = (
            FinalValueBand(upper=20.0, lower=10.0, color="#c44e52")
            if "imax_reac" in validations
            else None
        )

        if self._producer.is_dynawo_model():
            i_label = f"I (pu base Unom, Snom = {self._producer.s_nom}MVA)"
        else:
            i_label = "I (pu base Unom, Snom)"

        self._figures_description.append(
            FigureDescription(
                name="fig_I",
                variables=[
                    {"type": "generator", "variable": "IpInjTerminal"},
                    {"type": "generator", "variable": "IqInjTerminal"},
                ],
                ylabel=i_label,
                tolerance_band=tolerance_band,
            )
        )

    def __init_figures_uit(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_UIt = config.get_list("ReportCurves", "fig_UIt")
        if pcs_benchmark_name not in fig_UIt:
            return

        self._figures_description.append(
            FigureDescription(
                name="fig_UIt",
                variables=[{"type": "generator", "variable": "UPuInjTerminal"}],
                ylabel="V (pu base Unom)",
            )
        )

    def __init_figures_ustator(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_Ustator = config.get_list("ReportCurves", "fig_Ustator")
        if pcs_benchmark_name not in fig_Ustator:
            return

        dynamic_band = (
            DynamicBand(upper=5.0, lower=5.0, source_key="AVR_5_crvs")
            if "AVR_5" in validations
            else None
        )

        self._figures_description.append(
            FigureDescription(
                name="fig_Ustator",
                variables=[
                    {"type": "generator", "variable": "MagnitudeControlledByAVRPu"},
                    {"type": "generator", "variable": "VoltageSetpointPu"},
                ],
                ylabel="V (pu base Unom)",
                dynamic_band=dynamic_band,
            )
        )

    def __init_figures_theta(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_Theta = config.get_list("ReportCurves", "fig_Theta")
        if pcs_benchmark_name not in fig_Theta:
            return

        self._figures_description.append(
            FigureDescription(
                name="fig_Theta",
                variables=[{"type": "generator", "variable": "InternalAngle"}],
                ylabel=r"$\theta$ (rad)",
            )
        )

    def __init_figures_tap(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_Tap = config.get_list("ReportCurves", "fig_Tap")
        if pcs_benchmark_name not in fig_Tap:
            return

        self._figures_description.append(
            FigureDescription(
                name="fig_Tap",
                variables=[{"type": "transformer", "variable": "Tap"}],
                ylabel="Pos",
            )
        )

    def __init_figures_sync_cond_p(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_SyncCondP = config.get_list("ReportCurves", "fig_SyncCondP")
        if pcs_benchmark_name not in fig_SyncCondP:
            return

        if self._producer.is_dynawo_model():
            p_label = f"P (pu base Snom = {self._producer.s_nom}MVA)"
        else:
            p_label = "P (pu base Snom)"

        self._figures_description.append(
            FigureDescription(
                name="fig_SyncCondP",
                variables=[{"type": "sync_condenser", "variable": "ActivePower"}],
                ylabel=p_label,
            )
        )

    def __init_figures_sync_cond_q(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_SyncCondQ = config.get_list("ReportCurves", "fig_SyncCondQ")
        if pcs_benchmark_name not in fig_SyncCondQ:
            return

        if self._producer.is_dynawo_model():
            q_label = f"Q (pu base Snom = {self._producer.s_nom}MVA)"
        else:
            q_label = "Q (pu base Snom)"

        self._figures_description.append(
            FigureDescription(
                name="fig_SyncCondQ",
                variables=[{"type": "sync_condenser", "variable": "ReactivePower"}],
                ylabel=q_label,
            )
        )

    def __init_figures_sync_cond_freq(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_SyncCondFreq = config.get_list("ReportCurves", "fig_SyncCondFreq")
        if pcs_benchmark_name not in fig_SyncCondFreq:
            return

        freq_label = "Frequency (Hz)"
        self._figures_description.append(
            FigureDescription(
                name="fig_SyncCondFreq",
                variables=[{"type": "sync_condenser", "variable": "FrequencyHz"}],
                ylabel=freq_label,
            )
        )

    def __init_figures_load_p(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_LoadP = config.get_list("ReportCurves", "fig_LoadP")
        if pcs_benchmark_name not in fig_LoadP:
            return

        if self._producer.is_dynawo_model():
            p_label = f"P (pu base Snom = {self._producer.s_nom}MVA)"
        else:
            p_label = "P (pu base Snom)"

        self._figures_description.append(
            FigureDescription(
                name="fig_LoadP",
                variables=[{"type": "load", "variable": "ActivePower"}],
                ylabel=p_label,
            )
        )

    def __init_figures_load_q(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_LoadQ = config.get_list("ReportCurves", "fig_LoadQ")
        if pcs_benchmark_name not in fig_LoadQ:
            return

        if self._producer.is_dynawo_model():
            q_label = f"Q (pu base Snom = {self._producer.s_nom}MVA)"
        else:
            q_label = "Q (pu base Snom)"

        self._figures_description.append(
            FigureDescription(
                name="fig_LoadQ",
                variables=[{"type": "load", "variable": "ReactivePower"}],
                ylabel=q_label,
            )
        )

    def __get_curves_check_result(
        self,
        measurement_names: list,
        bm_name: str,
        oc_name: str,
    ) -> CurvesCheckResult:
        return self._curves_manager.has_required_curves(measurement_names, bm_name, oc_name)

    def __validate(
        self,
        op_cond: OperatingCondition,
        working_path: Path,
        jobs_output_dir: Path,
        event_params: dict,
        success: bool,
        has_simulated_curves: bool,
        has_reference: bool = True,
    ):
        results = op_cond.validate(
            self._validator,
            working_path,
            jobs_output_dir,
            event_params,
            has_simulated_curves,
            has_reference=has_reference,
        )

        # Statuses for the Summary Report
        if results["compliance"] is None:
            compliance = Compliance.UndefinedValidations
            dycov_logging.get_logger("Benchmark").warning("Undefined Validations")
        elif not success:
            compliance = Compliance.FailedSimulation
        elif results["is_invalid_test"]:
            compliance = Compliance.InvalidTest
            dycov_logging.get_logger("Benchmark").warning("Invalid Test")
        elif not results["compliance"]:
            compliance = Compliance.NonCompliant
        else:
            compliance = Compliance.Compliant

        return success, results, compliance

    def validate(
        self,
        summary_list: list,
        pcs_results: dict,
    ) -> bool:
        """Validate the Benchmark.

        Parameters
        ----------
        summary_list: list
            Compliance summary by pcs
        pcs_results: dict
            Results of the validations applied in the pcs

        Returns
        -------
        bool
            True if at least one operating condition succeeds, False otherwise
        """
        success = False

        for op_cond in self._oc_list:
            dycov_logging.set_test_context(
                pcs=self._pcs_name,
                benchmark=self._name,
                oc=op_cond.get_name(),
            )
            dycov_logging.get_logger("Benchmark").info("Validate")
            if dycov_logging.get_logger("PCS").isEnabledFor(logging.DEBUG):
                dump_effective_pcs_description(
                    config,
                    pcs=self._pcs_name,
                    benchmark=self._name,
                    oc=op_cond.get_name(),
                )
            curves_result = self.__get_curves_check_result(
                self._validator.get_measurement_names(),
                self._name,
                op_cond.get_name(),
            )
            sim = curves_result.simulation_result
            dycov_logging.get_logger("Benchmark").debug(
                f"Success: {sim.success} "
                f"Has curves: {curves_result.availability} "
                f"Time exceeds: {sim.time_exceeds} "
                f"Error: {sim.error} "
            )

            if sim.error is not None:
                compliance = Compliance.InvalidTest
                match sim.error:
                    case SimulationError.FAULT_SIMULATION_FAILS:
                        compliance = Compliance.FaultSimulationFails
                    case SimulationError.FAULT_DIP_UNACHIEVABLE:
                        compliance = Compliance.FaultDipUnachievable
                    case _:
                        pass
                results = {**_FAILED_RESULTS}
            elif not sim.appicable:
                compliance = Compliance.NotApplicableTest
                results = {**_FAILED_RESULTS}
            elif sim.time_exceeds:
                compliance = Compliance.SimulationTimeOut
                results = {**_FAILED_RESULTS}
            elif curves_result.availability == CurvesAvailability.ALL:
                op_cond_success, results, compliance = self.__validate(
                    op_cond,
                    curves_result.working_oc_dir,
                    curves_result.jobs_output_dir,
                    curves_result.event_params,
                    sim.success,
                    sim.has_simulated_curves,
                )
                results["solver"] = self._curves_manager.get_solver()
                success |= op_cond_success
            elif curves_result.availability == CurvesAvailability.NO_REFERENCE:
                op_cond_success, results, compliance = self.__validate(
                    op_cond,
                    curves_result.working_oc_dir,
                    curves_result.jobs_output_dir,
                    curves_result.event_params,
                    sim.success,
                    sim.has_simulated_curves,
                    has_reference=False,
                )
                if compliance.show_report():
                    compliance = _compliance_for_missing_curves(curves_result.availability)
                results["solver"] = self._curves_manager.get_solver()
                success |= op_cond_success
            else:
                compliance = _compliance_for_missing_curves(curves_result.availability)
                results = {**_FAILED_RESULTS}

            results["summary"] = compliance
            results["missed_columns"] = self._curves_manager.get_missed_curves("reference")

            if self._validator.is_defined_imax_reac():
                gen_imax = self._curves_manager.get_generators_imax()
                voltage_dip = self._curves_manager.get_voltage_dip()
                results["reactive_current_target"] = {
                    key: min(2 * voltage_dip, gen_imax[key]) for key in gen_imax
                }

            summary_list.append(
                Summary(
                    producer_name=self._producer_name,
                    id=int(self._pcs_id),
                    zone=int(self._pcs_zone),
                    pcs=self._pcs_name,
                    benchmark=self._name,
                    operating_condition=op_cond.get_name(),
                    compliance=compliance,
                    report_name=self._report_name,
                )
            )
            pcs_results[
                self._pcs_name + CASE_SEPARATOR + self._name + CASE_SEPARATOR + op_cond.get_name()
            ] = results

        return success

    def generate(self) -> None:
        """Execute the generation step for all operating conditions of the benchmark."""

        for op_cond in self._oc_list:
            dycov_logging.set_test_context(
                pcs=self._pcs_name,
                benchmark=self._name,
                oc=op_cond.get_name(),
            )
            dycov_logging.get_logger("Benchmark").info("Generate")
            working_oc_dir = (
                self._working_dir
                / self._producer_name
                / self._pcs_name
                / self._name
                / op_cond.get_name()
            )
            op_cond.generate(working_oc_dir)

    def get_name(self) -> str:
        """Get the benchmark name.

        Returns
        -------
        str
            Benchmark name
        """
        return self._name

    def get_figures_description(self) -> list:
        """Get the figure description.

        Returns
        -------
        list
            List of figure descriptions for the benchmark
        """
        return self._figures_description
