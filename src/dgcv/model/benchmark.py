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
from dgcv.core.simulator import Simulator
from dgcv.curves.manager import CurvesManager
from dgcv.dynawo.simulator import DynawoSimulator
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
        self._working_dir = parameters.get_working_dir()
        self._output_dir = parameters.get_output_dir()
        self._templates_path = Path(config.get_value("Global", "templates_path"))
        self._lib_path = Path(config.get_value("Global", "lib_path"))
        self._figures_description = None

        stable_time = config.get_float("GridCode", "stable_time", 100.0)
        (
            op_names,
            simulator,
            reference_manager,
            validator,
        ) = self.__prepare_benchmark_validation(parameters, stable_time)
        self._op_cond_list = [
            OperatingCondition(
                simulator,
                reference_manager,
                validator,
                parameters,
                pcs_name,
                op_name,
            )
            for op_name in op_names
        ]

    def __prepare_benchmark_validation(
        self, parameters: Parameters, stable_time: float
    ) -> tuple[list, Simulator, CurvesManager]:
        # Read Benchmark configurations and prepare current Benchmark work path.
        # Creates a specific folder by pcs
        if not (self._working_dir / self._pcs_name).is_dir():
            manage_files.create_dir(self._working_dir / self._pcs_name)
        if not (self._working_dir / self._pcs_name / self._name).is_dir():
            manage_files.create_dir(self._working_dir / self._pcs_name / self._name)

        pcs_benchmark_name = self._pcs_name + CASE_SEPARATOR + self._name
        producer = parameters.get_producer()
        if producer.is_dynawo_model():
            job_name = config.get_value(pcs_benchmark_name, "job_name")
            rte_model = config.get_value(pcs_benchmark_name, "TSO_model")
            omega_model = config.get_value(pcs_benchmark_name, "Omega_model")

            file_path = Path(__file__).resolve().parent.parent
            sim_type_path = producer.get_sim_type_str()
            model_path = file_path / self._lib_path / "TSO_model" / rte_model
            omega_path = file_path / self._lib_path / "Omega" / omega_model
            pcs_path = file_path / self._templates_path / sim_type_path / self._pcs_name
            if not pcs_path.exists():
                pcs_path = (
                    config.get_config_dir() / self._templates_path / sim_type_path / self._pcs_name
                )

            simulator = DynawoSimulator(
                parameters,
                self._pcs_name,
                model_path,
                omega_path,
                pcs_path,
                job_name,
                stable_time,
            )
        elif producer.is_user_curves():
            simulator = CurvesManager(parameters)

        reference_manager = CurvesManager(parameters)
        ops = config.get_list("PCS-OperatingConditions", pcs_benchmark_name)
        validations = self.__initialize_validation_by_benchmark()
        if producer.get_sim_type() >= MODEL_VALIDATION_PPM:
            validator = ModelValidator(
                pcs_benchmark_name,
                parameters,
                validations,
                reference_manager.is_field_measurements(),
            )
        else:
            validator = PerformanceValidator(
                parameters, stable_time, validations, reference_manager.is_field_measurements()
            )

        # If it is not a pcs with multiple operating conditions, returns itself
        return ops, simulator, reference_manager, validator

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
        fig_P = config.get_list("ReportCurves", "fig_P")
        fig_Q = config.get_list("ReportCurves", "fig_Q")
        fig_Ire = config.get_list("ReportCurves", "fig_Ire")
        fig_Iim = config.get_list("ReportCurves", "fig_Iim")
        fig_Ustator = config.get_list("ReportCurves", "fig_Ustator")
        fig_V = config.get_list("ReportCurves", "fig_V")
        fig_W = config.get_list("ReportCurves", "fig_W")
        fig_Theta = config.get_list("ReportCurves", "fig_Theta")
        fig_WRef = config.get_list("ReportCurves", "fig_WRef")
        fig_I = config.get_list("ReportCurves", "fig_I")
        fig_Tap = config.get_list("ReportCurves", "fig_Tap")

        pcs_benchmark_name = self._pcs_name + CASE_SEPARATOR + self._name
        self._figures_description = []
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

        if pcs_benchmark_name in fig_Q:
            tests = []
            self._figures_description.append(["fig_Q", "BusPDR_BUS_ReactivePower", tests, "Q(pu)"])

        if pcs_benchmark_name in fig_Ire:
            tests = []
            self._figures_description.append(
                ["fig_Ire", "BusPDR_BUS_ActiveCurrent", tests, "Ire(pu)"]
            )

        if pcs_benchmark_name in fig_Iim:
            tests = []
            self._figures_description.append(
                ["fig_Iim", "BusPDR_BUS_ReactiveCurrent", tests, "Iim(pu)"]
            )

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

    def __validate(
        self,
        op_cond: OperatingCondition,
        pcs_benchmark_name: str,
        working_path: Path,
        jobs_output_dir: Path,
        event_params: dict,
        fs: float,
        success: bool,
        has_simulated_curves: bool,
    ):
        op_cond_success, results = op_cond.validate(
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
        for op_cond in self._op_cond_list:
            (
                working_path,
                jobs_output_dir,
                event_params,
                fs,
                success,
                has_simulated_curves,
                has_curves,
            ) = op_cond.has_required_curves(pcs_benchmark_name, self._name)
            if has_curves == 0:
                op_cond_success, results, compliance = self.__validate(
                    op_cond,
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
                    op_cond.get_name(),
                    compliance,
                    self._report_name,
                )
            )
            pcs_results[pcs_benchmark_name + CASE_SEPARATOR + op_cond.get_name()] = results

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
