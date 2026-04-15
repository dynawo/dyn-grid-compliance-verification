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
    """Worker function that generates envelopes for a specific Power Conversion System (PCS).

    Designed to be executed concurrently within a multiprocessing Pool. It initializes
    a Pcs object and triggers the internal envelope generation routine.

    Parameters
    ----------
    pcs_args : tuple[GFMParameters, str, str]
        A tuple structured as (parameters, pcs_name, producer_name) containing the
        GFM simulation configuration and identifiers for the target PCS and producer.
    """
    parameters, pcs_name, producer_name = pcs_args
    pcs = Pcs(producer_name, pcs_name, parameters)

    try:
        # Validate the PCS definition before proceeding with the generation pipeline
        if not pcs.is_valid():
            dycov_logging.get_logger("GFMGeneration").error(f"{pcs.get_name()} is not a valid PCS")
            return

        # Execute the core envelope generation
        pcs.generate()
    except (FileNotFoundError, IOError, ValueError) as e:
        # Catch explicit exceptions related to input/output or faulty values and log them
        # appropriately
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
    """Core orchestrator class designed to manage the generation of Grid Forming (GFM) envelopes
    across multiple PCS units and producers.

    This class handles the initialization of the secure working environment, identifies the
    specific PCS models requiring validation, and manages the execution flow of the generation
    process, supporting both sequential and parallel multiprocessing workflows.
    """

    def __init__(self, parameters: GFMParameters) -> None:
        """Initializes the GFMGeneration orchestrator with the required simulation parameters.

        Parameters
        ----------
        parameters : GFMParameters
            An object containing all parsed GFM simulation configurations and settings.
        """
        self._parameters = parameters
        self._templates_path = Path(config.get_value("Global", "templates_path"))

        self.__initialize_working_environment()
        self._validation_pcs = self.__get_validation_pcs()
        self._pcs_list = self.__prepare_pcs_list()

    def __initialize_working_environment(self) -> None:
        """Initializes the operational environment by creating required directory structures.

        It ensures the working directory is available and implements safety checks on the target
        output directory to prevent the accidental overwriting of pre-existing results.
        """
        manage_files.create_dir(self._parameters.get_working_dir(), clean_first=False)

        # Verify if the designated results output path already exists to safeguard previous data
        if manage_files.check_output_dir(self._parameters.get_output_dir()):
            dycov_logging.get_logger("GFMGeneration").warning(
                "Exiting. Please rename your current Results directory, "
                "otherwise it will be erased and a new one will be created."
            )
            sys.exit()

        # Create a fresh output directory once safety is confirmed
        manage_files.create_dir(self._parameters.get_output_dir())

    def __get_validation_pcs(self) -> list[str]:
        """Determines and compiles the definitive list of PCS units targeted for envelope
        generation.

        This method aggregates the required PCS models by evaluating command-line arguments,
        global configuration settings, and the availability of underlying templates.

        Returns
        -------
        list[str]
            A sorted list containing the string identifiers of the PCS models designated for
            generation.
        """
        dycov_logging.get_logger("GFMGeneration").info("DyCoV Envelopes Generation")
        validation_pcs: set[str] = set()

        # Register a specifically selected PCS if provided via parameters
        if self._parameters.get_selected_pcs():
            validation_pcs.add(self._parameters.get_selected_pcs())

        self.__populate_validation_pcs(validation_pcs, "gridforming_pcs", "gfm")

        return sorted(list(validation_pcs))

    def __populate_validation_pcs(
        self, validation_pcs: set[str], validation_key: str, validation_path: str
    ) -> None:
        """Dynamically populates the target set of PCS models by scanning global configurations and
        local template directories.

        Parameters
        ----------
        validation_pcs : set[str]
            The referenced set of PCS names to be populated. This collection is modified in-place.
        validation_key : str
            The specific configuration key used to extract target PCS names from the global config
            file.
        validation_path : str
            The relative subdirectory path within the templates folder where PCS definitions
            reside.
        """
        tool_path = Path(__file__).resolve().parent.parent

        # Fetch configurations from the global settings if the set is currently empty
        if not validation_pcs:
            validation_pcs.update(config.get_list("Global", validation_key))

        if not validation_pcs:
            # If not restricted to "only DTR" mode, scan the custom configuration's template
            # directory
            if not self._parameters.get_only_dtr():
                validation_pcs.update(
                    manage_files.list_directories(
                        config.get_config_dir() / self._templates_path / validation_path
                    )
                )
            # Guarantee the tool's native template directory is always scanned as a fallback
            validation_pcs.update(
                manage_files.list_directories(tool_path / self._templates_path / validation_path)
            )

        # Sanitize the final set by purging any abstract 'aliases' entries that are not actual PCS
        #  names
        for item in list(validation_pcs):
            if "aliases" in item:
                validation_pcs.remove(item)

    def __prepare_pcs_list(self) -> list[tuple[GFMParameters, str, str]]:
        """Constructs the comprehensive list of execution arguments required by the worker
        functions.

        It maps every designated validation PCS against every available producer file to
        create a flat list of discrete generation tasks.

        Returns
        -------
        list[tuple[GFMParameters, str, str]]
            A fully structured list of tuples, each formatted as (parameters, pcs_name,
            producer_name), ready for sequential or parallel iteration.
        """
        pcs_list: list[tuple[GFMParameters, str, str]] = []
        all_producer_files = self._parameters.get_producer().get_filenames()

        # Iterate through all discovered producers and map them to the targeted PCS units
        for producer_name in all_producer_files:
            pcs_list.extend(
                (self._parameters, pcs_name, producer_name) for pcs_name in self._validation_pcs
            )
        return pcs_list

    def generate(self, use_parallel: bool = False, num_processes: int = 4) -> None:
        """Executes the generation of GFM envelopes, supporting both sequential execution and
        multiprocessing parallelism.

        Following the successful generation of all required envelopes, this method automatically
        handles the transfer of output artifacts to the final directory and wipes the temporary
        working environment.

        Parameters
        ----------
        use_parallel : bool, optional
            If True, activates the multiprocessing pool for concurrent generation.
            Defaults to False.
        num_processes : int, optional
            The maximum number of concurrent worker processes to utilize when `use_parallel`
            is True. Defaults to 4.
        """
        if use_parallel:
            dycov_logging.get_logger("GFMGeneration").info(
                f"Generating envelopes in parallel using {num_processes} processes."
            )
            # Dispatch generation tasks concurrently using a managed process pool
            with Pool(processes=num_processes) as pool:
                pool.map(_generate_pcs, self._pcs_list)
        else:
            dycov_logging.get_logger("GFMGeneration").info("Generating envelopes sequentially.")
            # Execute tasks synchronously on the main thread
            for pcs_tuple in self._pcs_list:
                _generate_pcs(pcs_tuple)

        # Migrate all finalized generation artifacts from the temporary workspace to the user
        # output directory
        for _, pcs_name, producer_name in self._pcs_list:
            manage_files.copy_directory(
                self._parameters.get_working_dir() / producer_name,
                self._parameters.get_output_dir(),
                pcs_name,
            )

        # Perform routine cleanup by securely deleting the temporary working directory
        manage_files.remove_dir(self._parameters.get_working_dir())
