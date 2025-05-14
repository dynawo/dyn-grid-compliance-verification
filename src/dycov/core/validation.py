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
import operator
import os
import shutil
import subprocess
import sys
import time
from multiprocessing import Pool
from operator import attrgetter
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.core.execution_parameters import Parameters
from dycov.core.global_variables import (
    CASE_SEPARATOR,
    ELECTRIC_PERFORMANCE_BESS,
    ELECTRIC_PERFORMANCE_PPM,
    ELECTRIC_PERFORMANCE_SM,
    MODEL_VALIDATION_BESS,
    MODEL_VALIDATION_PPM,
    REPORT_NAME,
)
from dycov.files import manage_files
from dycov.logging.logging import dycov_logging
from dycov.model.pcs import Pcs
from dycov.report import report
from dycov.report.LatexReportException import LatexReportException


def _aborted_execution(e: Exception) -> None:
    if dycov_logging.getEffectiveLevel() == logging.DEBUG:
        dycov_logging.get_logger("Validation").exception(f"Aborted execution. {e}")
    else:
        dycov_logging.get_logger("Validation").error(f"Aborted execution. {e}")


def _open_document(file: Path, is_testing: bool) -> None:
    if is_testing:
        return

    if os.name == "nt":
        dycov_logging.get_logger("Validation").info(f"Opening the report: {file}")
        subprocess.run(["start", file], shell=True)
    else:
        if shutil.which("open") and os.environ.get("DISPLAY"):
            dycov_logging.get_logger("Validation").info(f"Opening the report: {file}")
            subprocess.run(["open", file], check=True)
        else:
            dycov_logging.get_logger("Validation").info(f"Report saved in: {file}")


def _validate_pcs(pcs_tuple):
    """Helper function to validate a single PCS."""
    parameters, pcs_name, producer_name = pcs_tuple
    pcs = Pcs(
        producer_name, pcs_name, parameters
    )  # Assuming Pcs constructor can handle None for producer_name here
    summary_list = []
    try:
        if not pcs.is_valid():
            dycov_logging.get_logger("Validation").error(f"{pcs.get_name()} is not a valid PCS")
            return pcs.get_producer_name(), pcs.get_name(), False, {}

        report_name, success, pcs_results = pcs.validate(summary_list)
        pcs_results["pcs"] = pcs
        pcs_results["sim_type"] = parameters.get_sim_type()
        pcs_results["success"] = success
        pcs_results["report_name"] = report_name
        return pcs.get_producer_name(), pcs.get_name(), summary_list, pcs_results
    except (LatexReportException, FileNotFoundError, IOError, ValueError) as e:
        if dycov_logging.getEffectiveLevel() == logging.DEBUG:
            dycov_logging.get_logger("Validation").exception(
                f"Aborted execution for {pcs.get_name()}. {e}"
            )
        else:
            dycov_logging.get_logger("Validation").error(
                f"Aborted execution for {pcs.get_name()}. {e}"
            )
        return pcs.get_producer_name(), pcs.get_name(), summary_list, {}


class Validation:
    """Validation of producer inputs.
    There are two types of validations, electrical performance and model validation.
    Additionally, the electrical performance differs between the synchronous generator-type
    producer models and the Power Park Modules.

    Args
    ----
    parameters: Parameters
        Tool parameters
    """

    def __init__(
        self,
        parameters: Parameters,
    ):
        self._parameters = parameters
        self.__initialize_working_environment()

        # Environment Path
        self._modelica_path = Path(config.get_value("Global", "modelica_path"))
        self._templates_path = Path(config.get_value("Global", "templates_path"))
        self._path_latex_files = config.get_value("Global", "latex_templates_path")

        # Read the Pcs list to validate
        validation_pcs = set()
        if parameters.get_selected_pcs():
            validation_pcs.add(parameters.get_selected_pcs())

        if parameters.get_sim_type() == ELECTRIC_PERFORMANCE_SM:
            dycov_logging.get_logger("Validation").info(
                "DyCoV Electric Performance Verification for Synchronous Machines"
            )
            self.__populate_validation_pcs(
                validation_pcs, "electric_performance_verification_pcs", "performance/SM"
            )

        elif parameters.get_sim_type() == ELECTRIC_PERFORMANCE_PPM:
            dycov_logging.get_logger("Validation").info(
                "DyCoV Electric Performance Verification for Power Park Modules"
            )
            self.__populate_validation_pcs(
                validation_pcs, "electric_performance_ppm_verification_pcs", "performance/PPM"
            )

        elif parameters.get_sim_type() == ELECTRIC_PERFORMANCE_BESS:
            dycov_logging.get_logger("Validation").info(
                "DyCoV Electric Performance Verification for Storage"
            )
            self.__populate_validation_pcs(
                validation_pcs, "electric_performance_bess_verification_pcs", "performance/BESS"
            )

        elif parameters.get_sim_type() == MODEL_VALIDATION_PPM:
            dycov_logging.get_logger("Validation").info(
                "DyCoV Model Validation for Power Park Modules"
            )
            self.__populate_validation_pcs(validation_pcs, "model_ppm_validation_pcs", "model/PPM")

        elif parameters.get_sim_type() == MODEL_VALIDATION_BESS:
            dycov_logging.get_logger("Validation").info("DyCoV Model Validation for Storage")
            self.__populate_validation_pcs(
                validation_pcs, "model_bess_validation_pcs", "model/BESS"
            )

        self._validation_pcs = sorted(list(validation_pcs))

        # Prepare the environment to execute the tool
        pcs_list = []
        if parameters.get_sim_type() >= MODEL_VALIDATION_PPM:
            producers = parameters.get_producer().get_filenames(zone=1)
            dycov_logging.get_logger("Validation").debug(f"Zone1 files: {' '.join(producers)}")
            for producer_name in producers:
                pcs_list.extend(
                    (parameters, pcs_name, producer_name)
                    for pcs_name in self._validation_pcs
                    if pcs_name.endswith("z1")
                )
            producers = parameters.get_producer().get_filenames(zone=3)
            dycov_logging.get_logger("Validation").debug(f"Zone3 files: {' '.join(producers)}")
            for producer_name in parameters.get_producer().get_filenames(zone=3):
                pcs_list.extend(
                    (parameters, pcs_name, producer_name)
                    for pcs_name in self._validation_pcs
                    if pcs_name.endswith("z3")
                )
        else:
            producers = parameters.get_producer().get_filenames()
            dycov_logging.get_logger("Validation").debug(f"Producer files: {' '.join(producers)}")
            for producer_name in parameters.get_producer().get_filenames():
                pcs_list.extend(
                    (parameters, pcs_name, producer_name) for pcs_name in self._validation_pcs
                )
        self._pcs_list = sorted(pcs_list, key=lambda item: item[1])  # Sort by pcs_name

        # Flag to avoid opening the report in the tests
        self._is_testing = False

    def __populate_validation_pcs(
        self, validation_pcs: set, validation_key: str, validation_path: str
    ) -> None:
        tool_path = Path(__file__).resolve().parent.parent
        if not validation_pcs:
            validation_pcs.update(config.get_list("Global", validation_key))
        if not validation_pcs:
            if not self._parameters.get_only_dtr():
                validation_pcs.update(
                    manage_files.list_directories(
                        config.get_config_dir() / self._templates_path / validation_path
                    )
                )
            validation_pcs.update(
                manage_files.list_directories(tool_path / self._templates_path / validation_path)
            )

    def __initialize_working_environment(self) -> None:
        """Create the tool's working directory."""
        # prepare tool folders
        manage_files.create_dir(self._parameters.get_working_dir(), clean_first=False)
        manage_files.create_dir(self._parameters.get_working_dir() / "Reports", clean_first=False)
        manage_files.create_dir(self._parameters.get_working_dir() / "Latex", clean_first=False)

        # Check if results path exists to avoid overwriting if the user does not
        #  want to lose the files
        if manage_files.check_output_dir(self._parameters.get_output_dir()):
            logging.getLogger("Model Validation").warning(
                "Exiting. Please rename your current Results directory, otherwise it will be "
                "erased and a new one will be created."
            )
            sys.exit()
        manage_files.create_dir(self._parameters.get_output_dir())

    def __create_report(self, summary_list: list, report_results: dict) -> None:
        """Create the full report."""
        sorted_summary_list = sorted(summary_list, key=attrgetter("id", "zone", "producer_name"))
        dycov_logging.get_logger("Validation").debug(f"Sorted summary {sorted_summary_list}")

        if not self._is_testing:
            try:
                report.create_pdf(
                    sorted_summary_list,
                    report_results,
                    self._parameters,
                    Path(self._path_latex_files),
                )
            except LatexReportException as e:
                dycov_logging.get_logger("PDFLatex").error(
                    f"An error occurred while generating the report, "
                    f"look for the {REPORT_NAME.split(CASE_SEPARATOR)[0]}.log file "
                    f"under {self._parameters.get_output_dir()/'Reports'}"
                )
                _aborted_execution(e)
            except (FileNotFoundError, IOError, ValueError) as e:
                _aborted_execution(e)

        for pcs_results in report_results.values():
            pcs = pcs_results["pcs"]
            producer_name = pcs_results["producer"]
            manage_files.copy_output_files(
                self._parameters.get_working_dir(),
                self._parameters.get_output_dir(),
                pcs.get_name(),
                producer_name,
            )

        # Move output files to destination folder
        manage_files.copy_output_files(
            self._parameters.get_working_dir(),
            self._parameters.get_output_dir(),
            "Reports",
        )

    @staticmethod
    def get_project_path() -> Path:
        """Get the tool path
        Returns
        -------
        Path
            Tool path
        """
        return Path(__file__).parent.parent

    def validate(self, use_parallel: bool = False, num_processes: int = 4) -> list:
        """Validate the Producer inputs, parallel or sequential based on config.

        Parameters
        ----------
        use_parallel : bool
            Whether to use parallel validation or not. Default is False.
        num_processes : int
            Number of processes to use for parallel validation. Default is 4.

        Returns
        -------
        list
            Compliance results in a list
        """

        # Validate each configured Pcs
        summary_list = []
        report_results = {}
        t0 = time.monotonic()

        if use_parallel:
            dycov_logging.get_logger("Validation").info(
                f"Validating PCS in parallel using {num_processes} processes."
            )
            with Pool(processes=num_processes) as pool:
                results = pool.map(_validate_pcs, self._pcs_list)
            for producer_name, pcs_name, summary, pcs_results in results:
                summary_list.extend(summary)
                report_results[f"{producer_name}_{pcs_name}"] = pcs_results
        else:
            dycov_logging.get_logger("Validation").info("Validating PCS sequentially.")
            for pcs_tuple in self._pcs_list:
                producer_name, pcs_name, summary, pcs_results = _validate_pcs(pcs_tuple)
                summary_list.extend(summary)
                report_results[f"{producer_name}_{pcs_name}"] = pcs_results

        dycov_logging.get_logger("Validation").debug(f"Validation time {time.monotonic() - t0}s")
        # Create the pcs report
        self.__create_report(summary_list, report_results)

        report_file = (
            self._parameters.get_output_dir() / "Reports" / REPORT_NAME.replace("tex", "pdf")
        )
        if report_file.exists():
            _open_document(report_file, self._is_testing)
        else:
            dycov_logging.get_logger("Validation").warning(
                f"Report file does not exist: {report_file}"
            )

        compliance_list = list(map(operator.attrgetter("compliance"), summary_list))
        if dycov_logging.getEffectiveLevel() == logging.DEBUG:
            return compliance_list

        manage_files.remove_dir(self._parameters.get_working_dir())
        return compliance_list

    def set_testing(self, testing: bool):
        """Set the testing flag to avoid opening the report.

        Parameters
        ----------
        testing : bool
            If True, the report will not be opened.
        """
        self._is_testing = testing
