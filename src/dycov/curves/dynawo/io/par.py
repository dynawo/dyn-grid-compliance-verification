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
from dycov.model.parameters import Gen_init


class ParFile(FileVariables):
    """
    Manages the completion of the PAR (parameters) file for Dynawo simulations.

    This class extends FileVariables to handle specific variables and
    placeholders related to the PAR file, including line parameters,
    generator initialization values, and event parameters.
    """

    def __init__(self, dynawo_curves: ProducerCurves, bm_section: str, oc_section: str):
        """
        Initializes the ParFile with necessary Dynawo curve information and sections.

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
            "line_XPu",
            "line_RPu",
            "infiniteBus_U0Pu",
            "gen_P0Pu",
            "gen_Q0Pu",
            "gen_U0Pu",
            "gen_UPhase0",
            "event_start",
            "event_end",
            "event_pre_value",
            "event_step_value",
        ]
        super().__init__(
            tool_variables,
            dynawo_curves,
            bm_section,
            oc_section,
        )

    def complete_file(
        self,
        working_oc_dir: Path,
        line_rpu: float,
        line_xpu: float,
        rte_gen: Gen_init,
        event_params: dict,
    ) -> None:
        """
        Replaces the file placeholders in the 'TSOModel.par' file with the corresponding values.

        Parameters
        ----------
        working_oc_dir: Path
            The working directory where the 'TSOModel.par' file is located.
        line_rpu: float
            The per unit resistance value for the line.
        line_xpu: float
            The per unit reactance value for the line.
        rte_gen: Gen_init
            Parameters for the initialization of the TSO's bus side (P, Q, U, angle).
        event_params: dict
            A dictionary containing event-specific parameters, including start time,
            duration, pre-event value, and step value.
        """
        # Retrieve all existing variables from the TSOModel.par file
        variables_dict = replace_placeholders.get_all_variables(working_oc_dir, "TSOModel.par")

        # Update line parameters
        variables_dict["line_XPu"] = line_xpu
        variables_dict["line_RPu"] = line_rpu

        # Update generator initialization parameters. Note: 'infiniteBus_U0Pu' and 'gen_U0Pu'
        # intentionally use 'rte_gen.U0' as per original script's logic.
        variables_dict["infiniteBus_U0Pu"] = rte_gen.U0
        variables_dict["gen_P0Pu"] = rte_gen.P0
        variables_dict["gen_Q0Pu"] = rte_gen.Q0
        variables_dict["gen_U0Pu"] = rte_gen.U0
        variables_dict["gen_UPhase0"] = rte_gen.UPhase0

        # Update event parameters
        variables_dict["event_start"] = event_params["start_time"]
        variables_dict["event_end"] = event_params["start_time"] + event_params["duration_time"]
        variables_dict["event_pre_value"] = event_params["pre_value"]
        variables_dict["event_step_value"] = event_params["step_value"]

        # Complete other parameters using the inherited method from FileVariables
        self.complete_parameters(variables_dict, event_params)

        # Dump the updated variables back into the PAR file, replacing placeholders
        replace_placeholders.dump_file(working_oc_dir, "TSOModel.par", variables_dict)
