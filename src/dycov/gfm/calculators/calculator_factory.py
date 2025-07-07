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
from dycov.gfm.parameters import GFMParameters


def get_calculator(name: str, gfm_params: GFMParameters) -> Optional[GFMCalculator]:

    if name == "PhaseJump":
        return PhaseJump(gfm_params=gfm_params)
    if name == "AmplitudeStep":
        return AmplitudeStep(gfm_params=gfm_params)

    return None
