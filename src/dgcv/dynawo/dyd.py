#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from pathlib import Path

from dgcv.dynawo.file_variables import FileVariables
from dgcv.dynawo.simulator import Simulator
from dgcv.dynawo.translator import dynawo_translator
from dgcv.files import replace_placeholders


class DydFile(FileVariables):
    def __init__(self, simulator: Simulator, bm_section: str, oc_section: str):
        tool_variables = [
            "generator_id",
            "connection_event",
        ]
        super().__init__(
            tool_variables,
            simulator,
            bm_section,
            oc_section,
        )

    def complete_file(self, working_oc_dir: Path, event_params: dict) -> None:
        """Replace the file placeholders with the corresponding values.

        Parameters
        ----------
        working_oc_dir: Path
            File directory
        event_params: dict
            Event parameters
        """
        variables_dict = replace_placeholders.get_all_variables(working_oc_dir, "TSOModel.dyd")

        if event_params["connect_to"]:
            connect_event_to = dynawo_translator.get_dynawo_variable(
                self._simulator.get_producer().generators[0].lib, event_params["connect_to"]
            )
            variables_dict["generator_id"] = self._simulator.get_producer().generators[0].id
            variables_dict["connection_event"] = connect_event_to

        self.complete_parameters(variables_dict, event_params)

        # Modify dyd to add calculated variables
        replace_placeholders.dyd_file(working_oc_dir, "TSOModel.dyd", variables_dict)
