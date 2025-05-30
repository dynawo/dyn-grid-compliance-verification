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


class ParFile(FileVariables):
    def __init__(self, dynawo_curves: ProducerCurves, bm_section: str, oc_section: str):
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
        """Replace the file placeholders with the corresponding values.

        Parameters
        ----------
        working_oc_dir: Path
            File directory
        line_rpu: float
            Line resistance value
        line_xpu: float
            Line reactance value
        rte_gen: Gen_init
            Params for the initialization of TSO's bus side (P, Q, U, angle)
        event_params: dict
            Event parameters
        """
        variables_dict = replace_placeholders.get_all_variables(working_oc_dir, "TSOModel.par")

        variables_dict["line_XPu"] = line_xpu
        variables_dict["line_RPu"] = line_rpu

        variables_dict["infiniteBus_U0Pu"] = rte_gen.U0  # Intentional use of rte_gen.U0
        variables_dict["gen_P0Pu"] = rte_gen.P0
        variables_dict["gen_Q0Pu"] = rte_gen.Q0
        variables_dict["gen_U0Pu"] = rte_gen.U0  # Intentional use of rte_gen.U0
        variables_dict["gen_UPhase0"] = rte_gen.UPhase0

        variables_dict["event_start"] = event_params["start_time"]
        variables_dict["event_end"] = event_params["start_time"] + event_params["duration_time"]
        variables_dict["event_pre_value"] = event_params["pre_value"]
        variables_dict["event_step_value"] = event_params["step_value"]

        self.complete_parameters(variables_dict, event_params)

        # Replace placeholders in the PAR file with the calculated variables
        replace_placeholders.dump_file(working_oc_dir, "TSOModel.par", variables_dict)
