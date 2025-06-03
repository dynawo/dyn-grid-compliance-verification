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
from dycov.model.parameters import Gen_init


class TableFile(FileVariables):
    """
    Manages the completion of the 'TableInfiniteBus.txt' file for Dynawo simulations.

    This class extends FileVariables to handle specific variables and
    placeholders related to the infinite bus parameters and event timing,
    which are crucial for defining simulation conditions.
    """

    def __init__(self, dynawo_curves: ProducerCurves, bm_section: str, oc_section: str):
        """
        Initializes the TableFile with necessary Dynawo curve information and sections.

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
            "start_event",
            "end_event",
            "bus_u0pu",
            "bus_upu",
            "end_freq",
        ]
        super().__init__(
            tool_variables,
            dynawo_curves,
            bm_section,
            oc_section,
        )

    def complete_file(self, working_oc_dir: Path, rte_gen: Gen_init, event_params: dict) -> None:
        """
        Replaces the file placeholders in the 'TableInfiniteBus.txt' file with the corresponding
        values.

        Parameters
        ----------
        working_oc_dir: Path
            The working directory where the 'TableInfiniteBus.txt' file is located.
        rte_gen: Gen_init
            Parameters for the initialization of the TSO's bus side (P, Q, U, angle).
        event_params: dict
            A dictionary containing event-specific parameters, including start time,
            duration, step value, and connection type.
        """
        # Retrieve all existing variables from the TableInfiniteBus.txt file
        variables_dict = replace_placeholders.get_all_variables(
            working_oc_dir, "TableInfiniteBus.txt"
        )

        # Update event timing variables
        variables_dict["start_event"] = event_params["start_time"]
        variables_dict["end_event"] = event_params["start_time"] + event_params["duration_time"]

        # Set the initial per-unit voltage for the bus
        variables_dict["bus_u0pu"] = rte_gen.U0

        # Adjust bus voltage or frequency based on the event's connection type
        if event_params["connect_to"] == "AVRSetpointPu":
            variables_dict["bus_upu"] = rte_gen.U0 + float(event_params["step_value"])
        elif event_params["connect_to"] == "NetworkFrequencyPu":
            variables_dict["end_freq"] = 1.0 + float(event_params["step_value"])

        # Complete any additional parameters using the inherited method
        self.complete_parameters(variables_dict, event_params)

        # Check if the file exists before attempting to dump variables
        if not (working_oc_dir / "TableInfiniteBus.txt").exists():
            return

        # Replace placeholders in the TableInfiniteBus file with the calculated variables
        replace_placeholders.dump_file(working_oc_dir, "TableInfiniteBus.txt", variables_dict)
