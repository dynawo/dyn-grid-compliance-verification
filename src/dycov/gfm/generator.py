#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

import logging
import multiprocessing
import sys
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.files import manage_files
from dycov.gfm import report
from dycov.gfm.parameters import GFMParameters
from dycov.gfm.report import PcsReport
from dycov.logging import dycov_logging, worker_initializer
from dycov.model.compliance import Compliance
from dycov.model.pcs import Pcs

LOGGER = dycov_logging.get_logger("GFMGeneration")


def _generate_pcs(pcs_args: tuple[GFMParameters, str, str]) -> PcsReport:
    """
    Worker function that generates envelopes for a specific PCS.

    A PCS that fails on a missing file or a malformed value is reported and skipped, so the
    others still run.

    Parameters
    ----------
    pcs_args : tuple[GFMParameters, str, str]
        A tuple containing the
        simulation parameters, the PCS name, and the producer name.

    Returns
    -------
    PcsReport
        What the report shows of every test of the PCS, none when the PCS cannot be generated.
    """
    parameters, pcs_name, producer_name = pcs_args
    pcs = Pcs(producer_name, pcs_name, parameters)
    pcs_report = PcsReport(producer_name, pcs_name, pcs.get_report_name(), [])

    try:
        if not pcs.is_valid():
            LOGGER.error(f"{pcs.get_name()} is not a valid PCS")
            return pcs_report
        return pcs_report._replace(tests=pcs.generate())
    except (OSError, ValueError) as e:
        log = LOGGER.exception if LOGGER.getEffectiveLevel() == logging.DEBUG else LOGGER.error
        log(f"Aborted execution for {pcs.get_name()}. {e}")
        return pcs_report


class GFMGeneration:
    """Orchestrator class to manage Grid Forming (GFM) envelopes generation."""

    def __init__(self, parameters: GFMParameters) -> None:
        """
        Initializes the generation orchestrator.

        Parameters
        ----------
        parameters : GFMParameters
            The configuration parameters for the GFM run.
        """
        self._parameters = parameters
        self._templates_path = Path(config.get_value("Global", "templates_path"))
        self.__initialize_working_environment()
        self._validation_pcs = self.__get_validation_pcs()
        if not self._validation_pcs:
            LOGGER.error(
                f"The DTR revision {config.get_value('DTR', 'current')} gives the units of "
                f"{self._parameters.get_producer().get_sim_type_str()} no Grid Forming PCS"
            )
        self._pcs_list = self.__prepare_pcs_list()

    def __initialize_working_environment(self) -> None:
        """
        Sets up the working and output directories for the simulation.

        Raises
        ------
        SystemExit
            If the output directory already exists and risks being overwritten.
        """
        manage_files.create_dir(self._parameters.get_working_dir(), clean_first=False)
        if manage_files.check_output_dir(self._parameters.get_output_dir()):
            LOGGER.warning(
                "Exiting. Please rename your current Results directory, otherwise it will"
                " be erased."
            )
            sys.exit(1)
        manage_files.create_dir(self._parameters.get_output_dir())

    def __get_validation_pcs(self) -> list[str]:
        """
        Gathers the PCS to generate.

        The PCS selected on the command line, else those ``gridforming_pcs`` of the
        configuration lists, else every GFM PCS of the kind of unit (PPM or BESS) that the tool
        ships, that the delta of its revision of the DTR adds and, unless only the DTR ones are
        asked for, that the user's configuration directory holds. Aliases are left out.

        Returns
        -------
        list[str]
            The sorted names of the PCS.
        """
        LOGGER.info("DyCoV Envelopes Generation")
        validation_pcs: set[str] = set()

        if self._parameters.get_selected_pcs():
            validation_pcs.add(self._parameters.get_selected_pcs())

        self.__populate_validation_pcs(
            validation_pcs, "gridforming_pcs", self._parameters.get_producer().get_sim_type_str()
        )

        return sorted(validation_pcs)

    def __populate_validation_pcs(
        self, validation_pcs: set[str], validation_key: str, validation_path: str
    ) -> None:
        """
        Fills the set, if empty, from the configuration or else from the templates, and
        drops the aliases.

        Parameters
        ----------
        validation_pcs : set[str]
            The set of PCS names to populate.
        validation_key : str
            The configuration key to look up.
        validation_path : str
            The directory of the templates that holds the PCS.
        """
        tool_path = Path(__file__).resolve().parent.parent

        if not validation_pcs:
            validation_pcs.update(config.get_list("Global", validation_key))
        if not validation_pcs:
            shipped = tool_path / self._templates_path
            sources = [shipped, manage_files.dtr_delta_path(shipped)]
            if not self._parameters.get_only_dtr():
                sources.append(config.get_config_dir() / self._templates_path)
            for source in sources:
                if source is not None and (source / validation_path).is_dir():
                    validation_pcs.update(manage_files.list_directories(source / validation_path))

        validation_pcs.difference_update({pcs for pcs in validation_pcs if "aliases" in pcs})

    def __prepare_pcs_list(self) -> list[tuple[GFMParameters, str, str]]:
        """
        Prepares a list of configuration tuples for execution.

        Returns
        -------
        list[tuple[GFMParameters, str, str]]
            A list of tuples containing
            (parameters, pcs_name, producer_name).
        """
        return [
            (self._parameters, pcs_name, producer_name)
            for producer_name in self._parameters.get_producer().get_filenames()
            for pcs_name in self._validation_pcs
        ]

    def generate(self, use_parallel: bool = False, num_processes: int = 4) -> bool:
        """
        Generates the envelopes of every PCS and their report, then moves them to the output
        directory and removes the working one.

        Parameters
        ----------
        use_parallel : bool, optional
            Whether to run using multiprocessing. Defaults to False.
        num_processes : int, optional
            Number of CPU cores to utilize. Defaults to 4.

        Returns
        -------
        bool
            True if the envelopes of at least one test were generated.
        """
        if use_parallel:
            LOGGER.info(f"Generating envelopes in parallel using {num_processes} processes.")
            with multiprocessing.Pool(
                processes=num_processes,
                initializer=worker_initializer,
                initargs=(dycov_logging.get_handler_settings(), config.run_layers()),
            ) as pool:
                pcs_reports = pool.map(_generate_pcs, self._pcs_list)
                pool.close()
                pool.join()
        else:
            LOGGER.info("Generating envelopes sequentially.")
            pcs_reports = [_generate_pcs(pcs_tuple) for pcs_tuple in self._pcs_list]

        try:
            # The report reads the figures from the working directory, before it is moved
            report.create_pdf(pcs_reports, self._parameters)
        finally:
            for _, pcs_name, producer_name in self._pcs_list:
                manage_files.copy_directory(
                    self._parameters.get_working_dir() / producer_name,
                    self._parameters.get_output_dir(),
                    pcs_name,
                )
            manage_files.remove_dir(self._parameters.get_working_dir())

        return any(
            test.compliance not in (Compliance.WithoutEnvelopes, Compliance.InvalidTest)
            for pcs_report in pcs_reports
            for test in pcs_report.tests
        )
