#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

from typing import Optional

from dycov.gfm.calculators.amplitude_step import AmplitudeStep
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.calculators.phase_jump import PhaseJump
from dycov.gfm.calculators.rocof import RoCoF
from dycov.gfm.calculators.scr_jump import SCRJump
from dycov.gfm.parameters import GFMParameters

_CALCULATOR_REGISTRY = {
    "PhaseJump": PhaseJump,
    "AmplitudeStep": AmplitudeStep,
    "RoCoF": RoCoF,
    "SCRJump": SCRJump,
}


def get_calculator(name: str, gfm_params: GFMParameters) -> Optional[GFMCalculator]:
    """
    Factory method to instantiate a specific GFMCalculator subclass.

    Parameters
    ----------
    name : str
        The string identifier of the target calculator.
    gfm_params : GFMParameters
        The shared configuration parameters to pass.

    Returns
    -------
    Optional[GFMCalculator]
        An instance of the requested calculator, or None if not found.
    """

    # Retrieve the class definition and instantiate if it exists in the registry
    calc_class = _CALCULATOR_REGISTRY.get(name)
    return calc_class(gfm_params=gfm_params) if calc_class else None
