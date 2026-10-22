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
import multiprocessing
import operator
import os
import shutil
import subprocess
import sys
from operator import attrgetter
from pathlib import Path
from typing import Optional

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
from dycov.core.graceful_shutdown import terminate_all_children
from dycov.files import manage_files
from dycov.gfm import report as gfm_report
from dycov.gfm.parameters import GFMParameters
from dycov.gfm.producer import GFMProducer
from dycov.logging import dycov_logging, worker_initializer
from dycov.model.benchmark import Summary
from dycov.model.pcs import Pcs
from dycov.report import report
from dycov.report.LatexReportException import LatexReportException
from dycov.validate.parameters import ValidationParameters

# The kind of unit whose Grid Forming PCS a performance verification runs: the DTR Fiche I18
# covers storage units, and neither power park modules nor synchronous machines
_GRID_FORMING_UNITS = {ELECTRIC_PERFORMANCE_BESS: "BESS"}


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

    if not (shutil.which("xdg-open") and os.environ.get("DISPLAY")):
        dycov_logging.get_logger("Validation").info(f"Report saved in: {file}")
        return

    dycov_logging.get_logger("Validation").info(f"Opening the report: {file}")
    try:
        subprocess.run(["xdg-open", file], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        dycov_logging.get_logger("Validation").warning(
            f"The report could not be opened ({exc}). Report saved in: {file}"
        )


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
            dycov_logging.get_logger("Validation").error(f"{pcs.get_name()} is not a valid PCS")
            return pcs.get_producer_name(), pcs.get_name(), False, {}
        if not pcs.declares_tests():
            dycov_logging.get_logger("Validation").info(
                f"{pcs.get_name()}: no test declared, nothing to validate"
            )
            return pcs.get_producer_name(), pcs.get_name(), summary_list, {}
        if parameters.get_producer().is_gfm():
            return _check_grid_forming_pcs(pcs, parameters)

        report_name, success, pcs_results = pcs.validate(summary_list)
        pcs_results["pcs"] = pcs
        pcs_results["sim_type"] = parameters.get_sim_type()
        pcs_results["success"] = success
        pcs_results["report_name"] = report_name
        _prepare_report_pcs(pcs_results, parameters, path_latex_files)
        return pcs.get_producer_name(), pcs.get_name(), summary_list, pcs_results
    except (FileNotFoundError, IOError, ValueError) as e:
        if dycov_logging.get_logger("Validation").getEffectiveLevel() == logging.DEBUG:
            dycov_logging.get_logger("Validation").exception(
                f"Aborted execution for {pcs.get_name()}. {e}"
            )
        else:
            dycov_logging.get_logger("Validation").error(
                f"Aborted execution for {pcs.get_name()}. {e}"
            )
        return pcs.get_producer_name(), pcs.get_name(), summary_list, {}


def _check_grid_forming_pcs(pcs: Pcs, parameters: GFMParameters) -> tuple:
    """Checks the producer curves of every Grid Forming test of the PCS against its envelopes,
    instead of simulating the test, and writes the section of the PCS in the report.

    Parameters
    ----------
    pcs : Pcs
        The Grid Forming PCS of a producer.
    parameters : GFMParameters
        The parameters the tests of the producer are checked with.

    Returns
    -------
    tuple
        A tuple containing producer name, PCS name, summary list, and PCS results.
    """
    tests = pcs.generate()
    summary_list = [
        Summary(
            producer_name=test.producer_name,
            id=pcs.get_id(),
            zone=pcs.get_zone(),
            pcs=test.pcs,
            benchmark=test.benchmark,
            operating_condition=test.operating_condition,
            compliance=test.compliance,
            report_name=pcs.get_report_name(),
        )
        for test in tests
    ]
    gfm_report.prepare_pcs_report(
        gfm_report.PcsReport(
            pcs.get_producer_name(),
            pcs.get_name(),
            pcs.get_report_name(),
            [test for test in tests if test.compliance.show_report()],
        ),
        parameters.get_working_dir() / "Latex",
        parameters.get_producer().get_sim_type_str(),
        outputs_by_producer=True,
    )
    pcs_results = {"producer": pcs.get_producer_name(), "report_name": pcs.get_report_name()}
    return pcs.get_producer_name(), pcs.get_name(), summary_list, pcs_results


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
    except LatexReportException:
        dycov_logging.get_logger("Validation").error(
            f"An error occurred while preparing the report for {pcs_results['pcs'].get_name()}."
        )
        raise


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
        dry_run: bool = False,
    ):
        self._parameters = parameters
        self._is_testing = False  # Flag to avoid opening the report in the tests
        self._dry_run = dry_run
        self._summary: list = []

        # Environment Path
        self._templates_path = Path(config.get_value("Global", "templates_path"))
        self._path_latex_files = config.get_value("Global", "latex_templates_path")

        self.__initialize_working_environment()
        self._checks_grid_forming_curves = self.__checks_grid_forming_curves()
        self._validation_pcs = self.__get_validation_pcs()
        self._grid_forming_pcs = self.__get_grid_forming_pcs()
        self._grid_forming_parameters: dict[str, GFMParameters] = {}
        self._pcs_list = self.__prepare_pcs_list()

    def __initialize_working_environment(self) -> None:
        """Creates the tool's working directory and output directory.
        Checks if the output directory already exists and prompts the user if it
          will be overwritten.
        """
        # Prepare tool folders
        manage_files.create_dir(self._parameters.get_working_dir() / "Reports", clean_first=False)
        manage_files.create_dir(self._parameters.get_working_dir() / "Latex", clean_first=False)

        # Check if results path exists to avoid overwriting if the user does not
        # want to lose the files
        if manage_files.check_output_dir(self._parameters.get_output_dir()):
            dycov_logging.get_logger("Validation").warning(
                "Exiting. Please rename your current Results directory, otherwise it will be "
                "erased and a new one will be created."
            )
            sys.exit(1)

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
            dycov_logging.get_logger("Validation").info(log_message)
            template_paths = [template_path]
            if self._checks_grid_forming_curves:
                template_paths.append(f"gfm/{_GRID_FORMING_UNITS[sim_type]}")
            self.__populate_validation_pcs(validation_pcs, config_key, template_paths)
        else:
            dycov_logging.get_logger("Validation").info(f"Unknown simulation type: {sim_type}")

        return sorted(list(validation_pcs))

    def __populate_validation_pcs(
        self, validation_pcs: set, validation_key: str, validation_paths: list[str]
    ) -> None:
        """Populates the set of PCS to validate from configuration and template directories.

        Parameters
        ----------
        validation_pcs : set
            The set to populate with PCS names.
        validation_key : str
            The configuration key for validation PCS.
        validation_paths : list[str]
            The relative paths to the validation templates.
        """
        tool_path = Path(__file__).resolve().parent.parent
        if not validation_pcs:
            validation_pcs.update(config.get_list("Global", validation_key))
        if not validation_pcs:
            for validation_path in validation_paths:
                if not self._parameters.get_only_dtr():
                    validation_pcs.update(
                        manage_files.list_directories(
                            config.get_config_dir() / self._templates_path / validation_path
                        )
                    )
                validation_pcs.update(
                    manage_files.list_directories(
                        tool_path / self._templates_path / validation_path
                    )
                )

    def __checks_grid_forming_curves(self) -> bool:
        """Whether the run checks the curves of the Grid Forming tests of the DTR Fiche I18: a
        performance verification of a storage given its curves. DyCoV does not simulate those
        tests, so a run on a model leaves them out.

        Returns
        -------
        bool
            True if the Grid Forming PCS are run.
        """
        logger = dycov_logging.get_logger("Validation")
        if self._parameters.get_sim_type() not in _GRID_FORMING_UNITS:
            if self._parameters.get_gfm_envelopes_path() is not None:
                logger.warning(
                    "The Grid Forming envelopes given are not used: the DTR Fiche I18 covers "
                    "the performance of storage units only"
                )
            return False
        if self._parameters.is_dynawo_model_valid():
            logger.info(
                "The Grid Forming tests of the DTR Fiche I18 are checked on the curves of the "
                "producer (-c), DyCoV does not simulate them"
            )
            return False
        return True

    def __get_grid_forming_pcs(self) -> set:
        """Determines which of the PCS to validate are Grid Forming PCS, whose tests are checked
        against envelopes instead of being simulated.

        Returns
        -------
        set
            The names of the Grid Forming PCS to validate.
        """
        if not self._checks_grid_forming_curves:
            return set()

        gfm_unit = _GRID_FORMING_UNITS[self._parameters.get_sim_type()]
        gfm_templates = self._templates_path / "gfm" / gfm_unit
        templates_paths = (Path(__file__).resolve().parent.parent, config.get_config_dir())
        return {
            pcs_name
            for pcs_name in self._validation_pcs
            if any((path / gfm_templates / pcs_name).is_dir() for path in templates_paths)
        }

    def __get_pcs_parameters(self, pcs_name: str, producer_name: str):
        """The parameters a PCS of a unit is validated with: those of the Grid Forming tests of
        the unit for a Grid Forming PCS, those of the validation otherwise."""
        if pcs_name not in self._grid_forming_pcs:
            return self._parameters
        if producer_name not in self._grid_forming_parameters:
            self._grid_forming_parameters[producer_name] = self.__get_grid_forming_parameters(
                producer_name
            )
        return self._grid_forming_parameters[producer_name]

    def __get_grid_forming_parameters(self, producer_name: str) -> GFMParameters:
        """The parameters the Grid Forming tests of a producer are checked with: its INI file
        describes the unit, its curves are those given, and its envelopes are read from the
        directory given, when there is one, instead of being generated.

        Parameters
        ----------
        producer_name : str
            Name of the producer, that of its INI file and of the directory of its curves.

        Returns
        -------
        GFMParameters
            The parameters of the Grid Forming tests of the producer.
        """
        producer = self._parameters.get_producer()
        producer_ini = producer.get_producer_ini(0, producer_name)
        if producer_ini is None:
            raise FileNotFoundError(f"The producer {producer_name} has no INI file")

        envelopes = self.__get_envelopes_path(producer_name)
        parameters = GFMParameters(
            self._parameters,
            GFMProducer(producer_ini),
            producer_curves=producer.get_producer_curves_path(),
            envelopes=envelopes,
        )
        logger = dycov_logging.get_logger("Validation")
        if envelopes is not None:
            logger.info(f"The Grid Forming envelopes of {producer_name} are read from {envelopes}")
        elif not parameters.declares_unit_parameters():
            logger.warning(
                f"{producer_ini} declares no [GFM Parameters] and no Grid Forming envelopes are "
                f"given, so the Grid Forming tests of {producer_name} cannot be checked"
            )
        return parameters

    def __get_envelopes_path(self, producer_name: str) -> Optional[Path]:
        """The directory of the envelopes of a producer: the subdirectory named after it, or
        else the whole directory given, which then serves every producer."""
        envelopes = self._parameters.get_gfm_envelopes_path()
        if envelopes is None:
            return None
        unit_envelopes = envelopes / producer_name
        return unit_envelopes if unit_envelopes.is_dir() else envelopes

    def __prepare_pcs_list(self) -> list:
        """Prepares the list of PCS and their associated producers for validation.

        Returns
        -------
        list
            A list of tuples, each containing
            (parameters, pcs_name, producer_name, path_latex_files).
        """
        pcs_list = []
        all_producer_files = self._parameters.get_producer().get_filenames()
        dycov_logging.get_logger("Validation").debug(
            f"Producer files: {' '.join(all_producer_files)}"
        )

        if self._parameters.get_sim_type() > MODEL_VALIDATION:
            for zone in [1, 3]:
                producers_in_zone = self._parameters.get_producer().get_filenames(zone=zone)
                dycov_logging.get_logger("Validation").debug(
                    f"Zone{zone} files: {' '.join(producers_in_zone)}"
                )
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
                    (
                        self.__get_pcs_parameters(pcs_name, producer_name),
                        pcs_name,
                        producer_name,
                        self._path_latex_files,
                    )
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
        dycov_logging.get_logger("Validation").debug(f"Sorted summary {summary_list}")

        try:
            if not summary_list:
                dycov_logging.get_logger("Validation").warning(
                    "No test was run, so there is no report to generate"
                )
                return
            report.create_pdf(
                summary_list,
                report_results,
                self._parameters,
                Path(self._path_latex_files),
                self._dry_run,
            )
        except LatexReportException:
            dycov_logging.get_logger("Validation").error(
                f"An error occurred while generating the report, "
                f"look for the {REPORT_NAME.split(CASE_SEPARATOR)[0]}.log file "
                f"under {self._parameters.get_output_dir() / 'Reports'}"
            )
            raise
        finally:
            # Clean Latex folder
            if dycov_logging.get_logger("Report").getEffectiveLevel() != logging.DEBUG:
                manage_files.remove_dir(self._parameters.get_working_dir() / "Latex")

            # Move output files to destination folder
            dycov_logging.close_run_handler()
            manage_files.rename_path(
                self._parameters.get_working_dir(),
                self._parameters.get_output_dir(),
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

    def _validate(self, use_parallel: bool = False, num_processes: int = 4) -> tuple[list, dict]:
        summary_list = []
        report_results = {}

        if use_parallel:
            dycov_logging.get_logger("Validation").info(
                f"Validating PCS in parallel using {num_processes} processes."
            )
            with multiprocessing.Pool(
                processes=num_processes,
                initializer=worker_initializer,
                initargs=(dycov_logging.get_handler_settings(),),
            ) as pool:
                try:
                    results = pool.map(_validate_pcs, self._pcs_list)
                    pool.close()
                    pool.join()
                except KeyboardInterrupt:
                    # 1) Terminate external children before tearing down the pool
                    terminate_all_children(timeout=5.0)
                    # 2) Stop workers cleanly, avoiding multiple worker tracebacks
                    pool.terminate()
                    pool.join()
                    logger = dycov_logging.get_logger("Validation")
                    logger.error(
                        "Execution interrupted by user (SIGINT). "
                        "Shutting down workers and children..."
                    )
                    # Propagate conventional exit code for SIGINT
                    raise SystemExit(130)

            # Collect results only if we reached here (no interrupt)
            for producer_name, pcs_name, summary, pcs_results in results:
                summary_list.extend(summary)
                report_results[f"{producer_name}_{pcs_name}"] = pcs_results
        else:
            dycov_logging.get_logger("Validation").info("Validating PCS sequentially.")
            try:
                for pcs_tuple in self._pcs_list:
                    producer_name, pcs_name, summary, pcs_results = _validate_pcs(pcs_tuple)
                    summary_list.extend(summary)
                    report_results[f"{producer_name}_{pcs_name}"] = pcs_results
            except KeyboardInterrupt:
                # Ensure external children are stopped also in sequential mode
                terminate_all_children(timeout=5.0)
                logger = dycov_logging.get_logger("Validation")
                logger.error("Execution interrupted by user (SIGINT). Aborting current task...")
                raise SystemExit(130)

        return summary_list, report_results

    def validate(self, use_parallel: bool = False, num_processes: int = 4) -> list:
        """Validates the Producer inputs, using parallel or sequential execution.

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
        summary_list, report_results = self._validate(use_parallel, num_processes)
        # Create the pcs report
        sorted_summary_list = sorted(summary_list, key=attrgetter("id", "zone", "producer_name"))
        self._summary = sorted_summary_list
        self.__create_report(sorted_summary_list, report_results)

        if self._parameters.get_output_dir().exists():
            report_file = (
                self._parameters.get_output_dir() / "Reports" / REPORT_NAME.replace("tex", "pdf")
            )
            if report_file.exists():
                _open_document(report_file, self._is_testing)
            else:
                dycov_logging.get_logger("Validation").warning(
                    f"Report file does not exist: {report_file}"
                )

        compliance_list = list(map(operator.attrgetter("compliance"), sorted_summary_list))
        return compliance_list

    def get_summary(self) -> list:
        """Returns what the last validation produced, one Summary per test, in the order the
        report presents them. The compliance list that validate() returns is its verdict column.

        Returns
        -------
        list
            Summary of each test of the last validation, empty before the first one.
        """
        return self._summary

    def set_testing(self, testing: bool) -> None:
        """Sets the testing flag to avoid opening the report.

        Parameters
        ----------
        testing : bool
            If True, the report will not be opened.
        """
        self._is_testing = testing
