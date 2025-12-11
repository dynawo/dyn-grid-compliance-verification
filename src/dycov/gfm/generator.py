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


def _generate_pcs(pcs_args: tuple[GFMParameters, str, str]) -> None:
    """
    Generates envelopes for a given PCS (Power Conversion System).

    This function is designed to be called by a multiprocessing Pool. It
    initializes a Pcs object and runs the envelope generation process.

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
            dycov_logging.get_logger("GFMGeneration").error(f"{pcs.get_name()} is not a valid PCS")
            return

        pcs.generate()
    except (FileNotFoundError, IOError, ValueError) as e:
        # Catch specific exceptions that might occur during file operations or value errors.
        if dycov_logging.get_logger("GFMGeneration").getEffectiveLevel() == logging.DEBUG:
            dycov_logging.get_logger("GFMGeneration").exception(
                f"Aborted execution for {pcs.get_name()}. {e}"
            )
        else:
            dycov_logging.get_logger("GFMGeneration").error(
                f"Aborted execution for {pcs.get_name()}. {e}"
            )
        return


class GFMGeneration:
    """
    A class to manage the generation of Grid Forming (GFM) envelopes
    for multiple PCSs and producers.

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
        """
        manage_files.create_dir(self._parameters.get_working_dir(), clean_first=False)

        # Check if the results output path exists to prevent accidental overwriting.
        if manage_files.check_output_dir(self._parameters.get_output_dir()):
            dycov_logging.get_logger("GFMGeneration").warning(
                "Exiting. Please rename your current Results directory, "
                "otherwise it will be erased and a new one will be created."
            )
            sys.exit()
        manage_files.create_dir(self._parameters.get_output_dir())

    def __get_validation_pcs(self) -> list[str]:
        """
        Determines the list of PCS to generate envelopes for.

        It populates the list of PCS based on command-line arguments,
        configuration settings, and available templates.

        Returns
        -------
        list[str]
            A sorted list of PCS names for which to generate envelopes.
        """
        dycov_logging.get_logger("GFMGeneration").info("DyCoV Envelopes Generation")
        validation_pcs: set[str] = set()
        if self._parameters.get_selected_pcs():
            validation_pcs.add(self._parameters.get_selected_pcs())

        self.__populate_validation_pcs(validation_pcs, "gridforming_pcs", "gfm")

        return sorted(list(validation_pcs))

    def __populate_validation_pcs(
        self, validation_pcs: set[str], validation_key: str, validation_path: str
    ) -> None:
        """
        Populates the set of PCS from configuration and template directories.

        Parameters
        ----------
        validation_pcs : set[str]
            The set to populate with PCS names. This set is modified in-place.
        validation_key : str
            The configuration key used to retrieve PCS names from global config.
        validation_path : str
            The relative path within the templates directory for PCS templates.
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

        # Remove any "aliases" items from the set, as they are not valid PCS names.
        for item in list(validation_pcs):
            if "aliases" in item:
                validation_pcs.remove(item)

    def __prepare_pcs_list(self) -> list[tuple[GFMParameters, str, str]]:
        """
        Prepares the list of all (parameters, pcs_name, producer_name) tuples
        to be processed for envelope generation.

        Returns
        -------
        list[tuple[GFMParameters, str, str]]
            A comprehensive list of all simulation tasks to be run.
        """
        pcs_list: list[tuple[GFMParameters, str, str]] = []
        all_producer_files = self._parameters.get_producer().get_filenames()

        for producer_name in all_producer_files:
            # For each producer, create a task for each validation PCS.
            pcs_list.extend(
                (self._parameters, pcs_name, producer_name) for pcs_name in self._validation_pcs
            )
        return pcs_list

    def generate(self, use_parallel: bool = False, num_processes: int = 4) -> None:
        """
        Generates the GFM envelopes, either sequentially or in parallel.

        After generation, it copies the output files and cleans up the
        working directory.

        Parameters
        ----------
        use_parallel : bool
            If True, use multiprocessing for parallel generation. Defaults to False.
        num_processes : int
            The number of processes to use if `use_parallel` is True. Defaults to 4.
        """
        if use_parallel:
            dycov_logging.get_logger("GFMGeneration").info(
                f"Generating envelopes in parallel using {num_processes} processes."
            )
            with Pool(processes=num_processes) as pool:
                pool.map(_generate_pcs, self._pcs_list)
        else:
            dycov_logging.get_logger("GFMGeneration").info("Generating envelopes sequentially.")
            for pcs_tuple in self._pcs_list:
                _generate_pcs(pcs_tuple)

        for _, pcs_name, producer_name in self._pcs_list:
            manage_files.copy_directory(
                self._parameters.get_working_dir() / producer_name,
                self._parameters.get_output_dir(),
                pcs_name,
            )

        manage_files.remove_dir(self._parameters.get_working_dir())
