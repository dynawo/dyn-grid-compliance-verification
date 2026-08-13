#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional
from dycov.gfm.calculators.amplitude_step import AmplitudeStep
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.calculators.phase_jump import PhaseJump
from dycov.gfm.calculators.rocof import RoCoF
from dycov.gfm.calculators.scr_jump import SCRJump
from dycov.gfm.parameters import GFMParameters


def get_calculator(name: str, gfm_params: GFMParameters) -> Optional[GFMCalculator]:
    """
    Parameters
    ----------
    name : str
    gfm_params : GFMParameters

    Returns
    -------
    Optional[GFMCalculator]
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
