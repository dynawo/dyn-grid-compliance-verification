#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

"""
Factory module for creating GFM calculator instances.

This module provides a function to dynamically instantiate the correct GFM calculator
(e.g., PhaseJump or AmplitudeStep) based on a given name, ensuring the proper
GFM parameters are passed during initialization.
"""

from typing import Optional

from dycov.gfm.calculators.amplitude_step import AmplitudeStep
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.calculators.phase_jump import PhaseJump
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
        An instance of the specified GFMCalculator subclass if the name is recognized,
        otherwise None.
    """
    if name == "PhaseJump":
        return PhaseJump(gfm_params=gfm_params)
    if name == "AmplitudeStep":
        return AmplitudeStep(gfm_params=gfm_params)

    return None
