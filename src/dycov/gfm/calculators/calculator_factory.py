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

from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.calculators.phase_jump import PhaseJump
from dycov.gfm.parameters import GFMParameters


def get_calculator(
    gfm_params: GFMParameters, pcs_name: str, bm_name: str
) -> Optional[GFMCalculator]:
    name = gfm_params.get_calculator_name(pcs_name, bm_name)
    if name == "PhaseJump":
        return PhaseJump(gfm_params=gfm_params)

    return None
