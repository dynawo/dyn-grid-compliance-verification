#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA

from typing import Optional

from dycov.gfm.calculators.amplitude_step import AmplitudeStep
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.calculators.phase_jump import PhaseJump
from dycov.gfm.calculators.rocof import RoCoF
from dycov.gfm.calculators.scr_jump import SCRJump
from dycov.gfm.parameters import GFMParameters

# Using a mapping dictionary for O(1) factory lookups
_CALCULATOR_REGISTRY = {
    "PhaseJump": PhaseJump,
    "AmplitudeStep": AmplitudeStep,
    "RoCoF": RoCoF,
    "SCRJump": SCRJump,
}


def get_calculator(name: str, gfm_params: GFMParameters) -> Optional[GFMCalculator]:
    """Factory method to instantiate a specific GFMCalculator subclass."""
    calc_class = _CALCULATOR_REGISTRY.get(name)
    return calc_class(gfm_params=gfm_params) if calc_class else None
