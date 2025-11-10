#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#


def create_map(results: dict) -> list:
    """Creates a list to populate the solver parameters table in the LaTex reports

    Parameters
    ----------
    results: dict
        Results of the validations applied in the pcs

    Returns
    -------
    list
        Solver parameters list
    """

    solver_parameters = []
    if "solver" not in results:
        return solver_parameters

    solver = results["solver"]
    for key, value in solver.items():
        if type(value[0]) is float:
            conf_value = f"{value[0]:.3g}".strip()
        else:
            conf_value = str(value[0]).replace("_", r"\_")
        if type(value[1]) is float:
            default_value = f"{value[1]:.3g}".strip()
        else:
            default_value = str(value[1]).replace("_", r"\_")
        solver_parameters.append([key.replace("_", r"\_"), f"{conf_value} ({default_value})"])

    return solver_parameters
