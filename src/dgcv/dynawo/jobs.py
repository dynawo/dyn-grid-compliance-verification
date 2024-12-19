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

from dgcv.configuration.cfg import config
from dgcv.curves.producer import ProducerCurves
from dgcv.dynawo.file_variables import FileVariables
from dgcv.files import replace_placeholders


class JobsFile(FileVariables):
    def __init__(self, dynawo_curves: ProducerCurves, bm_section: str, oc_section: str):
        tool_variables = [
            "solver_lib",
            "solver_id",
            "dgcv_ddb_path",
            "producer_dyd",
        ]
        super().__init__(
            tool_variables,
            dynawo_curves,
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
        variables_dict = replace_placeholders.get_all_variables(working_oc_dir, "TSOModel.jobs")

        variables_dict["solver_lib"] = "dynawo_SolverIDA"
        variables_dict["solver_id"] = "IDA"

        variables_dict["dgcv_ddb_path"] = config.get_config_dir() / "ddb"
        variables_dict["producer_dyd"] = self._dynawo_curves.get_producer().get_producer_dyd().name

        self.complete_parameters(variables_dict, event_params)

        # Replace placeholders in job file
        replace_placeholders.jobs_file(working_oc_dir, "TSOModel.jobs", variables_dict)
