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

    Parameters
    ----------
    pcs_args : tuple[GFMParameters, str, str]
        A tuple containing parameters, PCS name, and producer name.
    """
    parameters, pcs_name, producer_name = pcs_args
    pcs = Pcs(producer_name, pcs_name, parameters)
    try:
        if not pcs.is_valid():
            LOGGER.error(f"{pcs.get_name()} is not a valid PCS")
            return

        pcs.generate()
    except (FileNotFoundError, IOError, ValueError) as e:

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
        operation exist and prompts the user if the output directory
        might be overwritten.
        """
        # prepare tool folders
        manage_files.create_dir(self._parameters.get_working_dir(), clean_first=False)

        # Check if results path exists to avoid overwriting if the user does not
        # want to lose the files
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

        This method populates the list of PCS based on selected PCS,
        configuration settings, and available templates.

        Returns
        -------
        list[str]
            A sorted list of PCS names for which to generate envelopes.
        """
        LOGGER.info("DyCoV Envelopes Generation")
        # Read the GFM Pcs list to validate
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

        Parameters
        ----------
        validation_pcs : set[str]
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

    def __prepare_pcs_list(self) -> list[tuple[GFMParameters, str, str]]:
        """
        Prepares the list of PCS and their associated producers for validation.

        Returns
        -------
        list[tuple[GFMParameters, str, str]]
            A list of tuples, each containing (parameters, pcs_name, producer_name).
        """
        pcs_list: list[tuple[GFMParameters, str, str]] = []

        all_producer_files = self._parameters.get_producer().get_filenames()
        # For other simulation types, use all producer files
        for producer_name in all_producer_files:
            pcs_list.extend(
                (self._parameters, pcs_name, producer_name) for pcs_name in self._validation_pcs
            )
        return pcs_list

    def generate(self, use_parallel: bool = False, num_processes: int = 4) -> None:
        """
        Generates the GFM envelopes, either sequentially or in parallel.

        Parameters
        ----------
        use_parallel : bool
            If True, use multiprocessing for parallel generation. Defaults to False.
        num_processes : int
            The number of processes to use if `use_parallel` is True. Defaults to 4.
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
