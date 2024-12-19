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

from dgcv.dynawo.curves import ProducerCurves
from dgcv.dynawo.file_variables import FileVariables
from dgcv.files import replace_placeholders
from dgcv.model.parameters import Gen_init


class TableFile(FileVariables):
    def __init__(self, producer_curves: ProducerCurves, bm_section: str, oc_section: str):
        tool_variables = [
            "start_event",
            "end_event",
            "bus_u0pu",
            "bus_upu",
            "end_freq",
        ]
        super().__init__(
            tool_variables,
            producer_curves,
            bm_section,
            oc_section,
        )

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
        variables_dict = replace_placeholders.get_all_variables(
            working_oc_dir, "TableInfiniteBus.txt"
        )

        variables_dict["start_event"] = event_params["start_time"]
        variables_dict["end_event"] = event_params["start_time"] + event_params["duration_time"]
        variables_dict["bus_u0pu"] = rte_gen.U0
        if event_params["connect_to"] == "AVRSetpointPu":
            variables_dict["bus_upu"] = rte_gen.U0 + float(event_params["step_value"])
        elif event_params["connect_to"] == "NetworkFrequencyPu":
            variables_dict["end_freq"] = 1.0 + float(event_params["step_value"])

        self.complete_parameters(variables_dict, event_params)

        # Modify dyd to add calculated variables
        replace_placeholders.table_file(
            working_oc_dir,
            variables_dict,
        )
