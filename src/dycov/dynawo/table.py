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
from dycov.dynawo.file_variables import FileVariables
from dycov.files import replace_placeholders
from dycov.model.parameters import Gen_init


class TableFile(FileVariables):
    def __init__(self, dynawo_curves: ProducerCurves, bm_section: str, oc_section: str):
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

    def __complete_file(
        self, working_oc_dir: Path, rte_gen: Gen_init, event_params: dict, filename: str
    ) -> None:
        variables_dict = replace_placeholders.get_all_variables(working_oc_dir, filename)

        variables_dict["start_event"] = event_params["start_time"]
        variables_dict["end_event"] = event_params["start_time"] + event_params["duration_time"]
        variables_dict["bus_u0pu"] = rte_gen.U0
        if event_params["connect_to"] == "AVRSetpointPu":
            variables_dict["bus_upu"] = rte_gen.U0 + float(event_params["step_value"])
        elif event_params["connect_to"] == "NetworkFrequencyPu":
            variables_dict["end_freq"] = 1.0 + float(event_params["step_value"])

        self.complete_parameters(variables_dict, event_params)

        # Replace placeholders in the TableInfiniteBus file with the calculated variables
        replace_placeholders.dump_file(working_oc_dir, filename, variables_dict)

    def complete_file(self, working_oc_dir: Path, rte_gen: Gen_init, event_params: dict) -> None:
        """Replace the file placeholders with the corresponding values.

        Parameters
        ----------
        working_oc_dir: Path
            File directory
        rte_gen: Gen_init
            Params for the initialization of TSO's bus side (P, Q, U, angle)
        event_params: dict
            Event parameters
        """
        if (working_oc_dir / "TableInfiniteBus.txt").exists():
            self.__complete_file(working_oc_dir, rte_gen, event_params, "TableInfiniteBus.txt")
        if (working_oc_dir / "TableVariableImpedance.txt").exists():
            self.__complete_file(
                working_oc_dir, rte_gen, event_params, "TableVariableImpedance.txt"
            )
