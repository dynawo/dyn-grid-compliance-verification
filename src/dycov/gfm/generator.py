#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import logging
import sys
from multiprocessing import Pool
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.files import manage_files
from dycov.gfm.parameters import GFMParameters
from dycov.logging.logging import dycov_logging
from dycov.model.pcs import Pcs

LOGGER = dycov_logging.get_logger("GFMGeneration")


def _generate_pcs(pcs_args: tuple[GFMParameters, str, str]) -> None:
    """
    Generates envelopes for a given PCS (Power Conversion System).

    This function initializes a Pcs object with the provided parameters,
    PCS name, and producer name. It then checks if the PCS is valid
    before attempting to generate its envelopes. Error handling is
    included to log exceptions during the generation process.

    Parameters
    ----------
    pcs_args : tuple[GFMParameters, str, str]
        A tuple containing the GFM simulation parameters, the PCS name,
        and the producer name associated with the PCS.
    """
    parameters, pcs_name, producer_name = pcs_args
    pcs = Pcs(producer_name, pcs_name, parameters)
    try:
        if not pcs.is_valid():
            LOGGER.error(f"{pcs.get_name()} is not a valid PCS")
            return

        pcs.generate()
    except (FileNotFoundError, IOError, ValueError) as e:
        # Catch specific exceptions that might occur during file operations
        # or value errors.
        # Log the exception details based on the current logging level.
        if dycov_logging.getEffectiveLevel() == logging.DEBUG:
            LOGGER.exception(f"Aborted execution for {pcs.get_name()}. {e}")
        else:
            LOGGER.error(f"Aborted execution for {pcs.get_name()}. {e}")
        return


class GFMGeneration:
    """
    A class to manage the generation of Grid Forming (GFM) envelopes
    for PCS validation.

    This class handles the initialization of the working environment,
    identification of PCS to validate, and the execution of the
    envelope generation process, either sequentially or in parallel.
    """

    def __init__(self, parameters: GFMParameters) -> None:
        """
        Initializes the GFMGeneration class with simulation parameters.

        This constructor sets up the GFM simulation parameters, defines
        the path to templates, initializes the working environment,
        identifies the PCS to be validated, and prepares the list of PCS
        for processing.

        Parameters
        ----------
        parameters : GFMParameters
            An object containing the GFM simulation parameters.
        """
        self._parameters = parameters
        self._templates_path = Path(config.get_value("Global", "templates_path"))

        self.__initialize_working_environment()
        self._validation_pcs = self.__get_validation_pcs()
        self._pcs_list = self.__prepare_pcs_list()

    def __initialize_working_environment(self) -> None:
        """
        Creates the tool's working directory and checks the output directory.

        This method ensures that the necessary directories for the tool's
        operation exist. It creates the working directory and checks if the
        output directory already exists, prompting the user with a warning
        and exiting if overwriting might occur without explicit consent.
        """
        manage_files.create_dir(self._parameters.get_working_dir(), clean_first=False)

        # Check if the results output path exists to prevent accidental
        # overwriting if the user does not want to lose existing files.
        if manage_files.check_output_dir(self._parameters.get_output_dir()):
            LOGGER.warning(
                "Exiting. Please rename your current Results directory, "
                "otherwise it will be erased and a new one will be created."
            )
            sys.exit()
        manage_files.create_dir(self._parameters.get_output_dir())

    def __get_validation_pcs(self) -> list[str]:
        """
        Determines the list of PCS to generate envelopes.

        This method populates the list of PCS based on selected PCS from
        command-line arguments, configuration settings, and available
        templates in predefined directories. It prioritizes selected PCS,
        then configuration, and finally discovers from template directories.

        Returns
        -------
        list[str]
            A sorted list of PCS names for which to generate envelopes.
        """
        LOGGER.info("DyCoV Envelopes Generation")
        validation_pcs: set[str] = set()
        if self._parameters.get_selected_pcs():
            validation_pcs.add(self._parameters.get_selected_pcs())

        self.__populate_validation_pcs(validation_pcs, "gridforming_pcs", "gfm")

        return sorted(list(validation_pcs))

    def __populate_validation_pcs(
        self, validation_pcs: set[str], validation_key: str, validation_path: str
    ) -> None:
        """
        Populates the set of PCS to generate envelopes from configuration
        and template directories.

        This helper method adds PCS names to the `validation_pcs` set.
        It first checks the global configuration for PCS names under
        `validation_key`. If no PCS are specified there, it then
        scans the template directories (both in config and tool paths)
        for subdirectories representing PCS templates.

        Parameters
        ----------
        validation_pcs : set[str]
            The set to populate with PCS names. This set is modified in-place.
        validation_key : str
            The configuration key (e.g., "gridforming_pcs") used to retrieve
            PCS names from the global configuration.
        validation_path : str
            The relative path within the templates directory where PCS
            templates are located (e.g., "gfm").
        """
        tool_path = Path(__file__).resolve().parent.parent
        if not validation_pcs:
            validation_pcs.update(config.get_list("Global", validation_key))
        if not validation_pcs:
            # If not in "only DTR" mode, check the configuration's template dir.
            if not self._parameters.get_only_dtr():
                validation_pcs.update(
                    manage_files.list_directories(
                        config.get_config_dir() / self._templates_path / validation_path
                    )
                )
            # Always check the tool's own template directory for PCS.
            validation_pcs.update(
                manage_files.list_directories(tool_path / self._templates_path / validation_path)
            )

        for item in list(validation_pcs):
            if "aliases" in item:
                validation_pcs.remove(item)

    def __prepare_pcs_list(self) -> list[tuple[GFMParameters, str, str]]:
        """
        Prepares the list of PCS and their associated producers for validation.

        This method iterates through all identified producer files and
        for each producer, it associates all validation PCS. This creates
        a comprehensive list of (parameters, pcs_name, producer_name) tuples
        to be processed for envelope generation.

        Returns
        -------
        list[tuple[GFMParameters, str, str]]
            A list of tuples, each containing:
            - GFMParameters: The simulation parameters object.
            - str: The name of the PCS.
            - str: The name of the producer associated with the PCS.
        """
        pcs_list: list[tuple[GFMParameters, str, str]] = []

        all_producer_files = self._parameters.get_producer().get_filenames()
        for producer_name in all_producer_files:
            # For each producer, extend the pcs_list with all validation PCS.
            # Each entry in the list will be a tuple:
            # (parameters, pcs_name, producer_name).
            pcs_list.extend(
                (self._parameters, pcs_name, producer_name) for pcs_name in self._validation_pcs
            )
        return pcs_list

    def generate(self, use_parallel: bool = False, num_processes: int = 4) -> None:
        """
        Generates the GFM envelopes, either sequentially or in parallel.

        This method orchestrates the envelope generation process. It can
        run the generation for each PCS sequentially or distribute the
        tasks across multiple processes for parallel execution, depending
        on the `use_parallel` flag. After generation, it copies the
        output files and cleans up the working directory.

        Parameters
        ----------
        use_parallel : bool
            If True, use multiprocessing for parallel generation.
            Defaults to False.
        num_processes : int
            The number of processes to use if `use_parallel` is True.
            Defaults to 4.
        """
        if use_parallel:
            LOGGER.info(f"Generating envelopes in parallel using {num_processes} processes.")
            with Pool(processes=num_processes) as pool:
                pool.map(_generate_pcs, self._pcs_list)
        else:
            LOGGER.info("Generating envelopes sequentially.")
            for pcs_tuple in self._pcs_list:
                _generate_pcs(pcs_tuple)

        for _, pcs_name, producer_name in self._pcs_list:
            manage_files.copy_output_files(
                self._parameters.get_working_dir() / producer_name,
                self._parameters.get_output_dir(),
                pcs_name,
            )

        manage_files.remove_dir(self._parameters.get_working_dir())
