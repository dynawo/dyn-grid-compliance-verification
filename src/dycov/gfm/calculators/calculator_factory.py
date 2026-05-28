#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from typing import Optional

from dycov.gfm.calculators.amplitude_step import AmplitudeStep
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.calculators.phase_jump import PhaseJump
from dycov.gfm.calculators.rocof import RoCoF
from dycov.gfm.calculators.scr_jump import SCRJump
from dycov.gfm.parameters import GFMParameters


def get_calculator(name: str, gfm_params: GFMParameters) -> Optional[GFMCalculator]:
    """
    Factory method to instantiate and return a specific GFMCalculator subclass.

    This function maps string identifiers to their corresponding Grid Forming (GFM)
    calculator classes, ensuring they are initialized with the provided parameters.

    Parameters
    ----------
    name : str
        The identifier name of the calculator to retrieve
        (e.g., "PhaseJump", "AmplitudeStep", "RoCoF", "SCRJump").
    gfm_params : GFMParameters
        An object containing all necessary grid forming parameters required
        for the calculation instance.

    Returns
    -------
    Optional[GFMCalculator]
        An instantiated object of the requested GFMCalculator subclass if the
        name is recognized. Returns None if the calculator name is unknown.
    """
    if name == "PhaseJump":
        return PhaseJump(gfm_params=gfm_params)
    if name == "AmplitudeStep":
        return AmplitudeStep(gfm_params=gfm_params)
    if name == "RoCoF":
        return RoCoF(gfm_params=gfm_params)
    if name == "SCRJump":
        return SCRJump(gfm_params=gfm_params)

    # Return None if no matching calculator is found
    return None
