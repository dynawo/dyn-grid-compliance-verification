#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from operator import attrgetter
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.files import manage_files
from dycov.gfm.parameters import GFMParameters
from dycov.logging.logging import dycov_logging
from dycov.model.pcs import Pcs


class GFMGeneration:
    def __init__(
        self,
        parameters: GFMParameters,
    ):
        self._parameters = parameters
        self.__initialize_working_environment()

        # Environment Path
        self._templates_path = Path(config.get_value("Global", "templates_path"))

        # Read the GFM Pcs list to validate
        validation_pcs = set()
        if parameters.get_selected_pcs():
            validation_pcs.add(parameters.get_selected_pcs())

        dycov_logging.get_logger("Envelopes").info("DyCoV Envelopes Generation")
        self.__populate_validation_pcs(validation_pcs, "gridforming_pcs", "gfm")

        self._validation_pcs = validation_pcs

        # Prepare the environment to execute the tool
        pcs_list = [Pcs(pcs_name, parameters) for pcs_name in self._validation_pcs]
        self._pcs_list = sorted(pcs_list, key=attrgetter("_id", "_zone"))

    def __initialize_working_environment(self) -> None:
        """Create the tool's working directory."""
        # prepare tool folders
        manage_files.create_dir(self._parameters.get_working_dir(), clean_first=False)

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

    def generate(self):

        for pcs in self._pcs_list:
            if not pcs.is_valid():
                dycov_logging.get_logger("Validation").error(
                    f"{pcs.get_name()} is not a valid PCS"
                )
                continue

            pcs.generate()

        for pcs in self._pcs_list:
            manage_files.copy_output_files(
                pcs.get_name(),
                self._parameters.get_working_dir(),
                self._parameters.get_output_dir(),
            )

        manage_files.remove_dir(self._parameters.get_working_dir())
