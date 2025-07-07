#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import numpy as np

from dycov.gfm.parameters import GFM_Params


class GFMCalculator:
    """
    Base class for Grid Forming (GFM) calculations.

    This class provides common attributes and an abstract method for calculating
    power envelopes in GFM systems. It defines constants for parameter indexing
    and a threshold for damping classification.
    """

    # Constants for indexing parameter arrays: original, minimum, and maximum values.
    _ORIGINAL_PARAMS_IDX = 0
    _MINIMUM_PARAMS_IDX = 1
    _MAXIMUM_PARAMS_IDX = 2
    # Threshold to differentiate between overdamped and underdamped systems.
    # Critically damped systems are grouped with overdamped.
    _EPSILON_THRESHOLD = 1.0

    def __init__(self, gfm_params: GFM_Params):
        """
        Initializes the GFMCalculator with system parameters.

        Parameters
        ----------
        gfm_params: GFM_Params
            An object containing all necessary parameters for GFM phase jump calculations.
        """
        self._gfm_params = gfm_params  # Stores GFM system parameters

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> tuple[bool, np.ndarray, np.ndarray, np.ndarray]:
        """
        Abstract method to be implemented by subclasses for calculating power envelopes.

        This method is intended to calculate the power at the point of common coupling (PCC)
        and its upper and lower envelopes based on specific event characteristics.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        time_array : np.array
            Array of time points for simulation.
        event_time : float
            The time (in seconds) at which the event occurs.

        Returns
        -------
        tuple[bool, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - is_overdamped: True if the initial system is overdamped, False otherwise.
            - p_pcc_final: The final calculated power at the point of common coupling.
            - p_up_final: The final upper power envelope.
            - p_down_final: The final lower power envelope.
        """
        pass  # This method is a placeholder and should be overridden by child classes.
