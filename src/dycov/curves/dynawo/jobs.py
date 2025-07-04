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

from dycov.configuration.cfg import config
from dycov.curves.curves import ProducerCurves
from dycov.curves.dynawo.file_variables import FileVariables
from dycov.files import replace_placeholders


class JobsFile(FileVariables):
    """
    Manages the completion of the JOBS file for Dynawo simulations.

    This class extends FileVariables to handle specific variables and
    placeholders related to the JOBS file, ensuring proper configuration
    for the solver and producer dynamics.
    """

    def __init__(self, dynawo_curves: ProducerCurves, bm_section: str, oc_section: str):
        """
        Initializes the JobsFile with necessary Dynawo curve information and sections.

        Parameters
        ----------
        dynawo_curves: ProducerCurves
            An object containing Dynawo producer curve data.
        bm_section: str
            The section identifier for Balance Management.
        oc_section: str
            The section identifier for Operational Contingency.
        """
        tool_variables = [
            "solver_lib",
            "solver_id",
            "dycov_ddb_path",
            "producer_dyd",
        ]
        super().__init__(
            tool_variables,
            dynawo_curves,
            bm_section,
            oc_section,
        )

    def complete_file(
        self, working_oc_dir: Path, solver_id: str, solver_lib: str, event_params: dict
    ) -> None:
        """
        Replaces the file placeholders in the 'TSOModel.jobs' file with the corresponding values.

        Parameters
        ----------
        working_oc_dir: Path
            The working directory where the 'TSOModel.jobs' file is located.
        solver_id: str
            The identifier for the solver.
        solver_lib: str
            The library path for the solver.
        event_params: dict
            A dictionary containing event-specific parameters to be included.
        """
        # Retrieve all existing variables from the TSOModel.jobs file
        variables_dict = replace_placeholders.get_all_variables(working_oc_dir, "TSOModel.jobs")

        # Update solver-related variables in the dictionary
        variables_dict["solver_lib"] = solver_lib
        variables_dict["solver_id"] = solver_id

        # Set the path to the DyCoV DDB directory using the global configuration
        variables_dict["dycov_ddb_path"] = config.get_config_dir() / "ddb"
        # Get the name of the producer's DYD file from the Dynawo curves
        variables_dict["producer_dyd"] = self._dynawo_curves.get_producer().get_producer_dyd().name

        # Complete other parameters using the inherited method from FileVariables
        self.complete_parameters(variables_dict, event_params)

        # Dump the updated variables back into the JOBS file, replacing placeholders
        replace_placeholders.dump_file(working_oc_dir, "TSOModel.jobs", variables_dict)
