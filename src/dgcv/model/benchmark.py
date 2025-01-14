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

from dgcv.configuration.cfg import config
from dgcv.core.execution_parameters import Parameters
from dgcv.core.global_variables import CASE_SEPARATOR, MODEL_VALIDATION_PPM
from dgcv.core.validator import Validator
from dgcv.curves.manager import CurvesManager
from dgcv.files import manage_files
from dgcv.logging.logging import dgcv_logging
from dgcv.model.compliance import Compliance
from dgcv.model.operating_condition import OperatingCondition
from dgcv.validation import compliance_list
from dgcv.validation.model import ModelValidator
from dgcv.validation.performance import PerformanceValidator

Summary = namedtuple(
    "Summary",
    ["id", "zone", "pcs", "benchmark", "operating_condition", "compliance", "report_name"],
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
    benchmark_name: str
        Benchmark name
    parameters: Parameters
        Tool parameters
    """

    def __init__(
        self,
        pcs_name: str,
        pcs_id: int,
        pcs_zone: int,
        report_name: str,
        benchmark_name: str,
        parameters: Parameters,
    ):
        self._pcs_name = pcs_name
        self._pcs_id = pcs_id
        self._pcs_zone = pcs_zone
        self._report_name = report_name
        self._name = benchmark_name
        self._parameters = parameters
        self._working_dir = parameters.get_working_dir()
        self._output_dir = parameters.get_output_dir()
        self._templates_path = Path(config.get_value("Global", "templates_path"))
        self._lib_path = Path(config.get_value("Global", "lib_path"))
        self._figures_description = None

        stable_time = config.get_float("GridCode", "stable_time", 100.0)
        (
            op_names,
            curves_manager,
            validator,
        ) = self.__prepare_benchmark_validation(parameters, stable_time)
        self._curves_manager = curves_manager
        self._validator = validator
        self._op_names = op_names

    def __prepare_benchmark_validation(
        self, parameters: Parameters, stable_time: float
    ) -> tuple[list, CurvesManager, Validator]:
        # Read Benchmark configurations and prepare current Benchmark work path.
        # Creates a specific folder by pcs
        if not (self._working_dir / self._pcs_name).is_dir():
            manage_files.create_dir(self._working_dir / self._pcs_name)
        if not (self._working_dir / self._pcs_name / self._name).is_dir():
            manage_files.create_dir(self._working_dir / self._pcs_name / self._name)

        pcs_benchmark_name = self._pcs_name + CASE_SEPARATOR + self._name
        curves_manager = CurvesManager(
            parameters,
            pcs_benchmark_name,
            stable_time,
            self._lib_path,
            self._templates_path,
            self._pcs_name,
        )

        ops = config.get_list("PCS-OperatingConditions", pcs_benchmark_name)
        validations = self.__initialize_validation_by_benchmark()
        if parameters.get_producer().get_sim_type() >= MODEL_VALIDATION_PPM:
            validator = ModelValidator(
                curves_manager,
                pcs_benchmark_name,
                parameters,
                validations,
                curves_manager.is_field_measurements(),
            )
        else:
            validator = PerformanceValidator(
                curves_manager,
                parameters,
                stable_time,
                validations,
                curves_manager.is_field_measurements(),
            )

        # If it is not a pcs with multiple operating conditions, returns itself
        return ops, curves_manager, validator

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
                ["fig_Ire", "BusPDR_BUS_ActiveCurrent", tests, "Ire(pu)"]
            )

    def __init_figures_iim(self, validations: list, pcs_benchmark_name: str) -> None:
        fig_Iim = config.get_list("ReportCurves", "fig_Iim")
        if pcs_benchmark_name in fig_Iim:
            tests = []
            self._figures_description.append(
                ["fig_Iim", "BusPDR_BUS_ReactiveCurrent", tests, "Iim(pu)"]
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
        pcs_bm_name: str,
        bm_name: str,
        oc_name: str,
    ) -> tuple[Path, Path, dict, float, bool, bool, int]:
        return self._curves_manager.has_required_curves(
            measurement_names, pcs_bm_name, bm_name, oc_name
        )

    def __validate(
        self,
        op_name: str,
        pcs_benchmark_name: str,
        working_path: Path,
        jobs_output_dir: Path,
        event_params: dict,
        fs: float,
        success: bool,
        has_simulated_curves: bool,
    ):
        op_cond = OperatingCondition(
            self._parameters,
            self._pcs_name,
            op_name,
        )

        op_cond_success, results = op_cond.validate(
            self._validator,
            pcs_benchmark_name,
            working_path,
            jobs_output_dir,
            event_params,
            fs,
            success,
            has_simulated_curves,
        )

        # Statuses for the Summary Report
        if results["compliance"] is None:
            compliance = Compliance.UndefinedValidations
            dgcv_logging.get_logger("Benchmark").warning("Undefined Validations")
        elif not op_cond_success:
            compliance = Compliance.FailedSimulation
        elif results["is_invalid_test"]:
            compliance = Compliance.InvalidTest
            dgcv_logging.get_logger("Benchmark").warning("Invalid Test")
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

        # Validate each operational point
        pcs_benchmark_name = self._pcs_name + CASE_SEPARATOR + self._name
        for op_name in self._op_names:
            dgcv_logging.get_logger("Benchmark").info(
                "RUNNING BENCHMARK: " + pcs_benchmark_name + ", OPER. COND.: " + op_name
            )
            (
                working_path,
                jobs_output_dir,
                event_params,
                fs,
                success,
                has_simulated_curves,
                has_curves,
            ) = self.__has_required_curves(
                self._validator.get_measurement_names(),
                pcs_benchmark_name,
                self._name,
                op_name,
            )

            if has_curves == 0:
                op_cond_success, results, compliance = self.__validate(
                    op_name,
                    pcs_benchmark_name,
                    working_path,
                    jobs_output_dir,
                    event_params,
                    fs,
                    success,
                    has_simulated_curves,
                )
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
                    int(self._pcs_id),
                    int(self._pcs_zone),
                    self._pcs_name,
                    self._name,
                    op_name,
                    compliance,
                    self._report_name,
                )
            )
            pcs_results[pcs_benchmark_name + CASE_SEPARATOR + op_name] = results

        return success

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
