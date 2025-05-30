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
    def __init__(self, dynawo_curves: ProducerCurves, bm_section: str, oc_section: str):
        super().__init__(
            [],
            dynawo_curves,
            bm_section,
            oc_section,
        )

    def complete_file(
        self,
        working_oc_dir: Path,
    ) -> None:
        """Replace the file placeholders with the corresponding values.

        Parameters
        ----------
        working_oc_dir: Path
            File directory
        """
        variables_dict = replace_placeholders.get_all_variables(working_oc_dir, "solvers.par")
        self.complete_parameters(variables_dict, dict())

        # Replace placeholders in the PAR file with the calculated variables
        replace_placeholders.dump_file(working_oc_dir, "solvers.par", variables_dict)
