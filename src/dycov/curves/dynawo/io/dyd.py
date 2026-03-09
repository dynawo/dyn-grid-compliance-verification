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
from dycov.curves.dynawo.io.file_variables import FileVariables
from dycov.files import replace_placeholders


class DydFile(FileVariables):
    """
    Manages operations related to the DYD file, inheriting from FileVariables.

    This class is responsible for handling specific variables within the DYD file
    and completing it by replacing placeholders with dynamic values relevant
    to simulation events.
    """

    def __init__(self, dynawo_curves: ProducerCurves, bm_section: str, oc_section: str):
        """
        Initializes the DydFile instance.

        Parameters
        ----------
        dynawo_curves : ProducerCurves
            An object containing producer curve data, used to extract generator information.
        bm_section : str
            The section identifier for the benchmark within the configuration.
        oc_section : str
            The section identifier for the operational condition within the configuration.
        """
        tool_variables = []
        super().__init__(
            tool_variables,
            dynawo_curves,
            bm_section,
            oc_section,
        )

    def complete_file(self, working_oc_dir: Path, event_params: dict) -> None:
        """
        Completes the DYD file by replacing placeholders with corresponding values.

        Parameters
        ----------
        working_oc_dir : Path
            The directory where the TSOModel.dyd file is located.
        event_params : dict
            A dictionary containing event-specific parameters, such as 'connect_to'.
        """
        variables_dict = replace_placeholders.get_all_variables(working_oc_dir, "TSOModel.dyd")

        # Complete parameters using the inherited method
        self.complete_parameters(variables_dict, event_params)

        # Dump the modified variables back into the DYD file, replacing placeholders.
        replace_placeholders.dump_file(working_oc_dir, "TSOModel.dyd", variables_dict)
