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

from dycov.curves.curves import ProducerCurves
from dycov.curves.dynawo.file_variables import FileVariables
from dycov.curves.dynawo.translator import dynawo_translator
from dycov.files import replace_placeholders


class DydFile(FileVariables):
    def __init__(self, dynawo_curves: ProducerCurves, bm_section: str, oc_section: str):
        tool_variables = [
            "generator_id",
            "connection_event",
        ]
        super().__init__(
            tool_variables,
            dynawo_curves,
            bm_section,
            oc_section,
        )

    def complete_file(self, working_oc_dir: Path, event_params: dict) -> None:
        """Complete the DYD file by replacing the placeholders with the corresponding values.

        Parameters
        ----------
        working_oc_dir: Path
            File directory
        event_params: dict
            Event parameters
        """
        variables_dict = replace_placeholders.get_all_variables(working_oc_dir, "TSOModel.dyd")

        if event_params.get("connect_to"):
            _, connect_event_to = dynawo_translator.get_dynawo_variable(
                self._dynawo_curves.get_producer().generators[0].lib, event_params["connect_to"]
            )
            variables_dict["generator_id"] = self._dynawo_curves.get_producer().generators[0].id
            variables_dict["connection_event"] = connect_event_to

        self.complete_parameters(variables_dict, event_params)

        # Modify dyd to add calculated variables
        # This includes replacing placeholders in the DYD file with the actual values
        # from the variables_dict, such as generator_id and connection_event.
        replace_placeholders.dump_file(working_oc_dir, "TSOModel.dyd", variables_dict)
