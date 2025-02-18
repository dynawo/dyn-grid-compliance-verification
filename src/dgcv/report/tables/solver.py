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
        solver_parameters.append([key.replace("_", "\_"), str(value).replace("_", "\_")])

    return solver_parameters
