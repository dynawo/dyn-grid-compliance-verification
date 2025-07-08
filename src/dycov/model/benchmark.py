#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from collections import namedtuple
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.core.global_variables import CASE_SEPARATOR, MODEL_VALIDATION
from dycov.core.parameters import Parameters
from dycov.core.validator import Validator
from dycov.curves.manager import CurvesManager
from dycov.files import manage_files
from dycov.logging.logging import dycov_logging
from dycov.model.compliance import Compliance
from dycov.model.operating_condition import OperatingCondition
from dycov.model.parameters import Simulation_result
from dycov.model.producer import Producer
from dycov.validation import compliance_list
from dycov.validation.model import ModelValidator
from dycov.validation.performance import PerformanceValidator

Summary = namedtuple(
    "Summary",
    [
        "producer_name",
        "id",
        "zone",
        "pcs",
        "benchmark",
        "operating_condition",
        "compliance",
        "report_name",
    ],
)


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

        stable_time = config.get_float("GridCode", "stable_time", 100.0)
        (
            oc_names,
            curves_manager,
            validator,
        ) = self.__prepare_benchmark_validation(parameters, producer, stable_time)
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
        # Create a specific folder by operating condition
        for oc_name in oc_names:
            working_oc_dir = (
                self._working_dir / self._producer_name / self._pcs_name / self._name / oc_name
            )
            manage_files.create_dir(working_oc_dir)

    def __get_log_title(self):
        return f"{self._pcs_name}.{self._name}:"

    def __info(self, message):
        """Debug function to print the PCS information."""
        dycov_logging.get_logger("Benchmark").info(f"{self.__get_log_title()} {message}")

    def __debug(self, message):
        """Debug function to print the PCS information."""
        dycov_logging.get_logger("Benchmark").debug(f"{self.__get_log_title()} {message}")

    def __warning(self, message):
        """Debug function to print the PCS information."""
        dycov_logging.get_logger("Benchmark").warning(f"{self.__get_log_title()} {message}")

    def __prepare_benchmark_validation(
        self, parameters: Parameters, producer: Producer, stable_time: float
    ) -> tuple[list, CurvesManager, Validator]:
        pcs_benchmark_name = self._pcs_name + CASE_SEPARATOR + self._name
        oc_names = config.get_list("PCS-OperatingConditions", pcs_benchmark_name)
        self.__create_operating_condition_working_paths(oc_names)
        if parameters.get_producer().is_gfm():
            return oc_names, None, None

        curves_manager = CurvesManager(
            parameters,
            producer,
            pcs_benchmark_name,
            stable_time,
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
                stable_time,
                validations,
                curves_manager.is_field_measurements(),
                self._pcs_name,
                self._name,
            )

        # If it is not a pcs with multiple operating conditions, returns itself
        return oc_names, curves_manager, validator

    def __initialize_validation_by_benchmark(self) -> list:
        # Prepare the validation list by pcs.benchmark
        pcs_benchmark_name = self._pcs_name + CASE_SEPARATOR + self._name

        # Read to all validations available the pcs list on which
        #  on will be applied
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
        self.__init_figures_ire(validations, pcs_benchmark_name)
        self.__init_figures_iim(validations, pcs_benchmark_name)
        self.__init_figures_w(validations, pcs_benchmark_name)
        self.__init_figures_wref(validations, pcs_benchmark_name)
        self.__init_figures_i(validations, pcs_benchmark_name)
        self.__init_figures_ustator(validations, pcs_benchmark_name)
        self.__init_figures_theta(validations, pcs_benchmark_name)
        self.__init_figures_tap(validations, pcs_benchmark_name)

    def __init_figures_v(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_V = config.get_list("ReportCurves", "fig_V")
        if pcs_benchmark_name in fig_V:
            tests = []
            if (
                "time_5P_85U" in validations
                or "time_10P_85U" in validations
                or "time_10Pfloor_85U" in validations
            ):
                tests.append("85U")

            self._figures_description.append(
                [
                    "fig_V",
                    [
                        {
                            "type": "bus",
                            "variable": "Voltage",
                        }
                    ],
                    tests,
                    "V(pu)",
                ]
            )

    def __init_figures_p(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_P = config.get_list("ReportCurves", "fig_P")
        if pcs_benchmark_name in fig_P:
            tests = []
            if "time_5P" in validations:
                tests.append("5P")
            if "time_10P" in validations:
                tests.append("10P")
            if "time_10P_85U" in validations:
                tests.append("10P")
            if "time_10Pfloor_85U" in validations or "time_10Pfloor_clear" in validations:
                tests.append("10Pfloor")

            self._figures_description.append(["fig_P", "BusPDR_BUS_ActivePower", tests, "P(pu)"])

    def __init_figures_q(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_Q = config.get_list("ReportCurves", "fig_Q")
        if pcs_benchmark_name in fig_Q:
            tests = []
            self._figures_description.append(["fig_Q", "BusPDR_BUS_ReactivePower", tests, "Q(pu)"])

    def __init_figures_ire(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_Ire = config.get_list("ReportCurves", "fig_Ire")
        if pcs_benchmark_name in fig_Ire:
            tests = []
            self._figures_description.append(
                ["fig_Ire", "BusPDR_BUS_ActiveCurrent", tests, "Ip(pu)"]
            )

    def __init_figures_iim(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_Iim = config.get_list("ReportCurves", "fig_Iim")
        if pcs_benchmark_name in fig_Iim:
            tests = []
            self._figures_description.append(
                ["fig_Iim", "BusPDR_BUS_ReactiveCurrent", tests, "Iq(pu)"]
            )

    def __init_figures_w(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_W = config.get_list("ReportCurves", "fig_W")
        if pcs_benchmark_name in fig_W:
            tests = []
            self._figures_description.append(
                [
                    "fig_W",
                    [
                        {
                            "type": "generator",
                            "variable": "RotorSpeedPu",
                        }
                    ],
                    tests,
                    r"$\omega$" + "(pu)",
                ]
            )

    def __init_figures_wref(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_WRef = config.get_list("ReportCurves", "fig_WRef")
        if pcs_benchmark_name in fig_WRef:
            tests = []
            if "freq_1" in validations:
                tests.append("freq_1")
            if "freq_200" in validations:
                tests.append("freq_200")
            if "freq_250" in validations:
                tests.append("freq_250")
            self._figures_description.append(
                [
                    "fig_WRef",
                    [
                        {
                            "type": "generator",
                            "variable": "NetworkFrequencyPu",
                        }
                    ],
                    tests,
                    r"$\omega$" + "(pu)",
                ]
            )

    def __init_figures_i(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_I = config.get_list("ReportCurves", "fig_I")
        if pcs_benchmark_name in fig_I:
            tests = []
            self._figures_description.append(
                [
                    "fig_I",
                    [
                        {
                            "type": "generator",
                            "variable": "InjectedActiveCurrent",
                        },
                        {
                            "type": "generator",
                            "variable": "InjectedReactiveCurrent",
                        },
                    ],
                    tests,
                    "I(pu)",
                ]
            )

    def __init_figures_ustator(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_Ustator = config.get_list("ReportCurves", "fig_Ustator")
        if pcs_benchmark_name in fig_Ustator:
            tests = []
            if "AVR_5" in validations:
                tests.append("AVR5")

            self._figures_description.append(
                [
                    "fig_Ustator",
                    [
                        {
                            "type": "generator",
                            "variable": "MagnitudeControlledByAVRPu",
                        },
                        {
                            "type": "generator",
                            "variable": "AVRSetpointPu",
                        },
                    ],
                    tests,
                    "V(pu)",
                ]
            )

    def __init_figures_theta(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_Theta = config.get_list("ReportCurves", "fig_Theta")
        if pcs_benchmark_name in fig_Theta:
            tests = []
            self._figures_description.append(
                [
                    "fig_Theta",
                    [
                        {
                            "type": "generator",
                            "variable": "InternalAngle",
                        }
                    ],
                    tests,
                    r"$\theta$" + "(rad)",
                ]
            )

    def __init_figures_tap(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_Tap = config.get_list("ReportCurves", "fig_Tap")
        if pcs_benchmark_name in fig_Tap:
            tests = []
            self._figures_description.append(
                [
                    "fig_Tap",
                    [
                        {
                            "type": "transformer",
                            "variable": "Tap",
                        }
                    ],
                    tests,
                    "Pos",
                ]
            )

    def __has_required_curves(
        self,
        measurement_names: list,
        bm_name: str,
        oc_name: str,
    ) -> tuple[Path, Path, dict, Simulation_result, int]:
        return self._curves_manager.has_required_curves(measurement_names, bm_name, oc_name)

    def __validate(
        self,
        op_cond: OperatingCondition,
        working_path: Path,
        jobs_output_dir: Path,
        event_params: dict,
        success: bool,
        has_simulated_curves: bool,
    ):
        op_cond_success, results = op_cond.validate(
            self._validator,
            working_path,
            jobs_output_dir,
            event_params,
            success,
            has_simulated_curves,
        )

        # Statuses for the Summary Report
        if results["compliance"] is None:
            compliance = Compliance.UndefinedValidations
            self.__warning("Undefined Validations")
        elif not op_cond_success:
            compliance = Compliance.FailedSimulation
        elif results["is_invalid_test"]:
            compliance = Compliance.InvalidTest
            self.__warning("Invalid Test")
        elif not results["compliance"]:
            compliance = Compliance.NonCompliant
        else:
            compliance = Compliance.Compliant

        return op_cond_success, results, compliance

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
            True if Benchmark can be validated, False otherwise
        """
        success = False

        # Check for operating conditions in the Pcs

        # Validate each operating condition
        for op_cond in self._oc_list:
            dycov_logging.get_logger("Benchmark").info(
                f"RUNNING PCS: {self._pcs_name}, BENCHMARK: {self._name}, "
                f"OPER. COND.: {op_cond.get_name()}"
            )
            (
                working_path,
                jobs_output_dir,
                event_params,
                simulation_result,
                has_curves,
            ) = self.__has_required_curves(
                self._validator.get_measurement_names(),
                self._name,
                op_cond.get_name(),
            )
            self.__debug(
                f"Succes: {simulation_result.success} "
                f"Has curves: {has_curves} "
                f"Time exceeds: {simulation_result.time_exceeds} "
                f"Error message: {simulation_result.error_message} "
            )
            if simulation_result.error_message is not None:
                self.__debug(f"Error message: {simulation_result.error_message}")
                compliance = Compliance.InvalidTest
                if simulation_result.error_message == "Fault simulation fails":
                    compliance = Compliance.FaultSimulationFails
                elif simulation_result.error_message == "Fault dip unachievable":
                    compliance = Compliance.FaultDipUnachievable
                results = {"compliance": False, "curves": None}
            elif simulation_result.time_exceeds:
                compliance = Compliance.SimulationTimeOut
                results = {"compliance": False, "curves": None}
            elif has_curves == 0:
                op_cond_success, results, compliance = self.__validate(
                    op_cond,
                    working_path,
                    jobs_output_dir,
                    event_params,
                    simulation_result.success,
                    simulation_result.has_simulated_curves,
                )
                results["solver"] = self._curves_manager.get_solver()
                # If there is a correct simulation, the report must be created
                success |= op_cond_success
            elif has_curves == 1:
                compliance = Compliance.WithoutProducerCurves
                results = {"compliance": False, "curves": None}
            elif has_curves == 2:
                compliance = Compliance.WithoutReferenceCurves
                results = {"compliance": False, "curves": None}
            else:
                compliance = Compliance.WithoutCurves
                results = {"compliance": False, "curves": None}

            results["summary"] = compliance
            summary_list.append(
                Summary(
                    self._producer_name,
                    int(self._pcs_id),
                    int(self._pcs_zone),
                    self._pcs_name,
                    self._name,
                    op_cond.get_name(),
                    compliance,
                    self._report_name,
                )
            )
            pcs_results[
                self._pcs_name + CASE_SEPARATOR + self._name + CASE_SEPARATOR + op_cond.get_name()
            ] = results

        return success

    def generate(self):
        for op_cond in self._oc_list:
            dycov_logging.get_logger("Benchmark").info(
                f"RUNNING PCS: {self._pcs_name}, BENCHMARK: {self._name}, "
                f"OPER. COND.: {op_cond.get_name()}"
            )
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

    def get_figures_description(self) -> dict:
        """Get the figure description.

        Returns
        -------
        dict
            Description of every figure to plot by benchmark
        """
        return self._figures_description
