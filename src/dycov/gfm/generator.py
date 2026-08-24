#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA

import logging
import sys
from multiprocessing import Pool
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.files import manage_files
from dycov.gfm.parameters import GFMParameters
from dycov.logging import dycov_logging
from dycov.model.pcs import Pcs


def _generate_pcs(pcs_args: tuple[GFMParameters, str, str]) -> None:
    """Worker function that generates envelopes for a specific PCS."""
    parameters, pcs_name, producer_name = pcs_args
    pcs = Pcs(producer_name, pcs_name, parameters)

    try:
        if not pcs.is_valid():
            dycov_logging.get_logger("GFMGeneration").error(f"{pcs.get_name()} is not a valid PCS")
            return
        pcs.generate()

    except (FileNotFoundError, IOError, ValueError) as e:
        if dycov_logging.get_logger("GFMGeneration").getEffectiveLevel() == logging.DEBUG:
            dycov_logging.get_logger("GFMGeneration").exception(
                f"Aborted execution for {pcs.get_name()}. {e}"
            )
        else:
            dycov_logging.get_logger("GFMGeneration").error(
                f"Aborted execution for {pcs.get_name()}. {e}"
            )


class GFMGeneration:
    """Orchestrator class to manage Grid Forming (GFM) envelopes generation."""

    def __init__(self, parameters: GFMParameters) -> None:
        self._parameters = parameters
        self._templates_path = Path(config.get_value("Global", "templates_path"))
        self.__initialize_working_environment()
        self._validation_pcs = self.__get_validation_pcs()
        self._pcs_list = self.__prepare_pcs_list()

    def __initialize_working_environment(self) -> None:
        manage_files.create_dir(self._parameters.get_working_dir(), clean_first=False)
        if manage_files.check_output_dir(self._parameters.get_output_dir()):
            dycov_logging.get_logger("GFMGeneration").warning(
                "Exiting. Please rename your current Results directory, otherwise it will be erased."
            )
            sys.exit(1)

        manage_files.create_dir(self._parameters.get_output_dir())

    def __get_validation_pcs(self) -> list[str]:
        dycov_logging.get_logger("GFMGeneration").info("DyCoV Envelopes Generation")
        validation_pcs: set[str] = set()

        if self._parameters.get_selected_pcs():
            validation_pcs.add(self._parameters.get_selected_pcs())

        self.__populate_validation_pcs(validation_pcs, "gridforming_pcs", "gfm")
        return sorted(list(validation_pcs))

    def __populate_validation_pcs(
        self, validation_pcs: set[str], validation_key: str, validation_path: str
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

        for item in list(validation_pcs):
            if "aliases" in item:
                validation_pcs.remove(item)

    def __prepare_pcs_list(self) -> list[tuple[GFMParameters, str, str]]:
        return [
            (self._parameters, pcs_name, producer_name)
            for producer_name in self._parameters.get_producer().get_filenames()
            for pcs_name in self._validation_pcs
        ]

    def generate(self, use_parallel: bool = False, num_processes: int = 4) -> None:
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
