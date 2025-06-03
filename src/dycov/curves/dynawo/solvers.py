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
from dycov.files import replace_placeholders


class SolversFile(FileVariables):
    """
    Manages the completion of the 'solvers.par' file for Dynawo simulations.

    This class extends FileVariables to specifically handle variables and
    placeholders within the 'solvers.par' file, ensuring it's correctly
    configured for Dynawo's solver settings.
    """

    def __init__(self, dynawo_curves: ProducerCurves, bm_section: str, oc_section: str):
        """
        Initializes the SolversFile with necessary Dynawo curve information and sections.

        Parameters
        ----------
        dynawo_curves: ProducerCurves
            An object containing Dynawo producer curve data.
        bm_section: str
            The section identifier for Balance Management.
        oc_section: str
            The section identifier for Operational Contingency.
        """
        # SolversFile does not require specific tool_variables for its direct placeholders,
        # as it primarily relies on the inherited complete_parameters method.
        super().__init__(
            [],  # No specific tool_variables defined for this file's placeholders
            dynawo_curves,
            bm_section,
            oc_section,
        )

    def complete_file(
        self,
        working_oc_dir: Path,
    ) -> None:
        """
        Replaces the file placeholders in the 'solvers.par' file with the corresponding values.

        Parameters
        ----------
        working_oc_dir: Path
            The working directory where the 'solvers.par' file is located.
        """
        # Retrieve all existing variables from the 'solvers.par' file
        variables_dict = replace_placeholders.get_all_variables(working_oc_dir, "solvers.par")

        # Complete the parameters. For 'solvers.par', additional event_params are not
        # directly supplied here, so an empty dictionary is passed.
        self.complete_parameters(variables_dict, dict())

        # Dump the updated variables back into the 'solvers.par' file, replacing placeholders
        replace_placeholders.dump_file(working_oc_dir, "solvers.par", variables_dict)
