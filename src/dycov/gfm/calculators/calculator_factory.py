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
    Returns an instance of a GFMCalculator subclass based on the provided name.

    This factory function maps string names to corresponding GFM calculator classes
    and instantiates them with the given GFM parameters.

    Parameters
    ----------
    name : str
        The name of the calculator to retrieve (e.g., "PhaseJump", "AmplitudeStep").
    gfm_params : GFMParameters
        An object containing all necessary parameters for the GFM calculation.

    Returns
    -------
    Optional[GFMCalculator]
        An instance of the specified GFMCalculator subclass if the name is
        recognized, otherwise None.
    """
    if name == "PhaseJump":
        return PhaseJump(gfm_params=gfm_params)
    if name == "AmplitudeStep":
        return AmplitudeStep(gfm_params=gfm_params)
    if name == "RoCoF":
        return RoCoF(gfm_params=gfm_params)
    if name == "SCRJump":
        return SCRJump(gfm_params=gfm_params)

    return None
