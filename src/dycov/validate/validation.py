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
from multiprocessing import Pool
from operator import attrgetter
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.core.global_variables import (
    CASE_SEPARATOR,
    ELECTRIC_PERFORMANCE_BESS,
    ELECTRIC_PERFORMANCE_PPM,
    ELECTRIC_PERFORMANCE_SM,
    MODEL_VALIDATION,
    MODEL_VALIDATION_BESS,
    MODEL_VALIDATION_PPM,
    REPORT_NAME,
)
from dycov.files import manage_files
from dycov.logging.logging import dycov_logging
from dycov.model.pcs import Pcs
from dycov.report import report
from dycov.report.LatexReportException import LatexReportException
from dycov.validate.parameters import ValidationParameters

LOGGER = dycov_logging.get_logger("Validation")


def _aborted_execution(e: Exception) -> None:
    """Logs an aborted execution message with exception details.

    Parameters
    ----------
    e : Exception
        The exception that caused the abortion.
    """

    if dycov_logging.getEffectiveLevel() == logging.DEBUG:
        LOGGER.exception(f"Aborted execution. {e}")
    else:
        LOGGER.error(f"Aborted execution. {e}")


def _open_document(file: Path, is_testing: bool) -> None:
    """Opens a document using the appropriate system command.

    Parameters
    ----------
    file : Path
        The path to the document to open.
    is_testing : bool
        If True, the document will not be opened.
    """
    if is_testing:
        return

    if os.name == "nt":
        LOGGER.info(f"Opening the report: {file}")
        subprocess.run(["start", file], shell=True)
    else:
        if shutil.which("open") and os.environ.get("DISPLAY"):
            LOGGER.info(f"Opening the report: {file}")
            subprocess.run(["open", file], check=True)
        else:
            LOGGER.info(f"Report saved in: {file}")


def _validate_pcs(pcs_args) -> tuple:
    """Helper function to validate a single PCS.

    Parameters
    ----------
    pcs_args : tuple
        A tuple containing parameters, PCS name, producer name, and path to LaTeX files.

    Returns
    -------
    tuple
        A tuple containing producer name, PCS name, summary list, and PCS results.
    """
    parameters, pcs_name, producer_name, path_latex_files = pcs_args
    pcs = Pcs(producer_name, pcs_name, parameters)
    summary_list = []
    pcs_results = {}
    try:
        if not pcs.is_valid():
            LOGGER.error(f"{pcs.get_name()} is not a valid PCS")
            return pcs.get_producer_name(), pcs.get_name(), False, {}

        report_name, success, pcs_results = pcs.validate(summary_list)
        pcs_results["pcs"] = pcs
        pcs_results["sim_type"] = parameters.get_sim_type()
        pcs_results["success"] = success
        pcs_results["report_name"] = report_name
        _prepare_report_pcs(pcs_results, parameters, path_latex_files)
        return pcs.get_producer_name(), pcs.get_name(), summary_list, pcs_results
    except (FileNotFoundError, IOError, ValueError) as e:

        if dycov_logging.getEffectiveLevel() == logging.DEBUG:
            LOGGER.exception(f"Aborted execution for {pcs.get_name()}. {e}")
        else:
            LOGGER.error(f"Aborted execution for {pcs.get_name()}. {e}")
        return pcs.get_producer_name(), pcs.get_name(), summary_list, {}


def _prepare_report_pcs(
    pcs_results: dict, parameters: ValidationParameters, path_latex_files: Path
) -> None:
    """Prepare the report for the PCS validation.

    Parameters
    ----------
    pcs_results : dict
        Dictionary containing PCS validation results.
    parameters : Parameters
        Tool parameters.
    path_latex_files : Path
        Path to the LaTeX template files.
    """
    try:
        report.prepare_pcs_report(pcs_results, parameters, Path(path_latex_files))
    except LatexReportException as e:
        LOGGER.error(
            f"An error occurred while preparing the report "
            f"for {pcs_results['pcs'].get_name()}."
        )
        _aborted_execution(e)
    except (FileNotFoundError, IOError, ValueError) as e:
        _aborted_execution(e)


class Validation:
    """Validation of producer inputs.
    There are two types of validations: electrical performance and model validation.
    Additionally, the electrical performance differs between the synchronous generator-type
    producer models and the Power Park Modules.

    Parameters
    ----------
    parameters: Parameters
        Tool parameters
    """

    def __init__(
        self,
        parameters: ValidationParameters,
    ):
        self._parameters = parameters
        self._is_testing = False  # Flag to avoid opening the report in the tests

        # Environment Path
        self._modelica_path = Path(config.get_value("Global", "modelica_path"))
        self._templates_path = Path(config.get_value("Global", "templates_path"))
        self._path_latex_files = config.get_value("Global", "latex_templates_path")

        self.__initialize_working_environment()
        self._validation_pcs = self.__get_validation_pcs()
        self._pcs_list = self.__prepare_pcs_list()

    def __initialize_working_environment(self) -> None:
        """Creates the tool's working directory and output directory.
        Checks if the output directory already exists and prompts the user if it
          will be overwritten.
        """
        # Prepare tool folders
        manage_files.create_dir(self._parameters.get_working_dir(), clean_first=False)
        manage_files.create_dir(self._parameters.get_working_dir() / "Reports", clean_first=False)
        manage_files.create_dir(self._parameters.get_working_dir() / "Latex", clean_first=False)

        # Check if results path exists to avoid overwriting if the user does not
        # want to lose the files
        if manage_files.check_output_dir(self._parameters.get_output_dir()):
            LOGGER.warning(
                "Exiting. Please rename your current Results directory, otherwise it will be "
                "erased and a new one will be created."
            )
            sys.exit()
        manage_files.create_dir(self._parameters.get_output_dir())

    def __get_validation_pcs(self) -> list:
        """Determines the list of PCS to be validated based on simulation type and configuration.

        Returns
        -------
        list
            A sorted list of PCS names to validate.
        """
        validation_pcs = set()
        if self._parameters.get_selected_pcs():
            validation_pcs.add(self._parameters.get_selected_pcs())

        sim_type_mapping = {
            ELECTRIC_PERFORMANCE_SM: (
                "DyCoV Electric Performance Verification for Synchronous Machines",
                "electric_performance_verification_pcs",
                "performance/SM",
            ),
            ELECTRIC_PERFORMANCE_PPM: (
                "DyCoV Electric Performance Verification for Power Park Modules",
                "electric_performance_ppm_verification_pcs",
                "performance/PPM",
            ),
            ELECTRIC_PERFORMANCE_BESS: (
                "DyCoV Electric Performance Verification for Storage",
                "electric_performance_bess_verification_pcs",
                "performance/BESS",
            ),
            MODEL_VALIDATION_PPM: (
                "DyCoV Model Validation for Power Park Modules",
                "model_ppm_validation_pcs",
                "model/PPM",
            ),
            MODEL_VALIDATION_BESS: (
                "DyCoV Model Validation for Storage",
                "model_bess_validation_pcs",
                "model/BESS",
            ),
        }

        sim_type = self._parameters.get_sim_type()
        if sim_type in sim_type_mapping:
            log_message, config_key, template_path = sim_type_mapping[sim_type]
            LOGGER.info(log_message)
            self.__populate_validation_pcs(validation_pcs, config_key, template_path)
        else:
            LOGGER.info(f"Unknown simulation type: {sim_type}")

        return sorted(list(validation_pcs))

    def __populate_validation_pcs(
        self, validation_pcs: set, validation_key: str, validation_path: str
    ) -> None:
        """Populates the set of PCS to validate from configuration and template directories.

        Parameters
        ----------
        validation_pcs : set
            The set to populate with PCS names.
        validation_key : str
            The configuration key for validation PCS.
        validation_path : str
            The relative path to the validation templates.
        """
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

    def __prepare_pcs_list(self) -> list:
        """Prepares the list of PCS and their associated producers for validation.

        Returns
        -------
        list
            A list of tuples, each containing
            (parameters, pcs_name, producer_name, path_latex_files).
        """
        pcs_list = []
        # Get all producer files regardless of zone initially
        all_producer_files = self._parameters.get_producer().get_filenames()
        LOGGER.debug(f"Producer files: {' '.join(all_producer_files)}")

        if self._parameters.get_sim_type() > MODEL_VALIDATION:
            # For MODEL_VALIDATION types, iterate through zones
            for zone in [1, 3]:
                # Get producers specific to the current zone
                producers_in_zone = self._parameters.get_producer().get_filenames(zone=zone)
                LOGGER.debug(f"Zone{zone} files: {' '.join(producers_in_zone)}")
                for producer_name in producers_in_zone:
                    # Extend pcs_list with PCSs ending with the zone suffix
                    pcs_list.extend(
                        (self._parameters, pcs_name, producer_name, self._path_latex_files)
                        for pcs_name in self._validation_pcs
                        if pcs_name.endswith(f"z{zone}")
                    )
        else:
            # For other simulation types, use all producer files
            for producer_name in all_producer_files:
                pcs_list.extend(
                    (self._parameters, pcs_name, producer_name, self._path_latex_files)
                    for pcs_name in self._validation_pcs
                )
        return pcs_list

    def __create_report(self, summary_list: list, report_results: dict) -> None:
        """Creates the full validation report.

        Parameters
        ----------
        summary_list : list
            A list of summary objects containing validation results.
        report_results : dict
            A dictionary containing detailed PCS report results.
        """
        LOGGER.debug(f"Sorted summary {summary_list}")

        try:
            report.create_pdf(
                summary_list,
                report_results,
                self._parameters,
                Path(self._path_latex_files),
            )
        except LatexReportException as e:
            LOGGER.error(
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
                self._parameters.get_working_dir() / producer_name,
                self._parameters.get_output_dir() / producer_name,
                pcs.get_name(),
            )

        # Move output files to destination folder
        manage_files.copy_output_files(
            self._parameters.get_working_dir(),
            self._parameters.get_output_dir(),
            "Reports",
        )

    @staticmethod
    def get_project_path() -> Path:
        """Gets the tool path.

        Returns
        -------
        Path
            Tool path.
        """
        return Path(__file__).parent.parent

    def validate(self, use_parallel: bool = False, num_processes: int = 4) -> list:
        """Validates the Producer inputs, parallel or sequential based on config.

        Parameters
        ----------
        use_parallel : bool, optional
            Whether to use parallel validation or not. Default is False.
        num_processes : int, optional
            Number of processes to use for parallel validation. Default is 4.

        Returns
        -------
        list
            Compliance results in a list.
        """
        summary_list = []
        report_results = {}

        if use_parallel:
            LOGGER.info(f"Validating PCS in parallel using {num_processes} processes.")
            with Pool(processes=num_processes) as pool:
                results = pool.map(_validate_pcs, self._pcs_list)
            for producer_name, pcs_name, summary, pcs_results in results:
                summary_list.extend(summary)
                report_results[f"{producer_name}_{pcs_name}"] = pcs_results
        else:
            LOGGER.info("Validating PCS sequentially.")
            for pcs_tuple in self._pcs_list:
                producer_name, pcs_name, summary, pcs_results = _validate_pcs(pcs_tuple)
                summary_list.extend(summary)
                report_results[f"{producer_name}_{pcs_name}"] = pcs_results

        # Create the pcs report
        sorted_summary_list = sorted(summary_list, key=attrgetter("id", "zone", "producer_name"))
        self.__create_report(sorted_summary_list, report_results)

        report_file = (
            self._parameters.get_output_dir() / "Reports" / REPORT_NAME.replace("tex", "pdf")
        )
        if report_file.exists():
            _open_document(report_file, self._is_testing)
        else:
            LOGGER.warning(f"Report file does not exist: {report_file}")

        compliance_list = list(map(operator.attrgetter("compliance"), sorted_summary_list))
        if dycov_logging.getEffectiveLevel() == logging.DEBUG:
            return compliance_list

        manage_files.remove_dir(self._parameters.get_working_dir())
        return compliance_list

    def set_testing(self, testing: bool):
        """Sets the testing flag to avoid opening the report.

        Parameters
        ----------
        testing : bool
            If True, the report will not be opened.
        """
        self._is_testing = testing
