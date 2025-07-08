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

    def __init__(self, gfm_params: GFM_Params) -> None:
        """
        Initializes the GFMCalculator with system parameters.

        Parameters
        ----------
        gfm_params: GFM_Params
            An object containing all necessary parameters for GFM phase jump calculations.
        """
        self._gfm_params = gfm_params  # Stores GFM system parameters

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
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
        time_array : np.ndarray
            Array of time points for simulation.
        event_time : float
            The time (in seconds) at which the event occurs.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - magnitude: Name of the calculated magnitude.
            - p_pcc_final: The final calculated power at the point of common coupling.
            - p_up_final: The final upper power envelope.
            - p_down_final: The final lower power envelope.
        """
        pass  # This method is a placeholder and should be overridden by child classes.

    def _apply_delay(
        self, delay: float, delayed_value: float, time_array: np.ndarray, signal: np.ndarray
    ) -> np.ndarray:
        """
        Applies a time delay to a given signal. The delay is implemented by prepending
        a constant `delayed_value` for the duration of the `delay` time. The output
        signal is truncated to the original signal's length.

        Parameters
        ----------
        delay : float
            The desired delay time in seconds.
        delayed_value : float
            The constant value to fill the signal during the delay period.
        time_array : np.ndarray
            The time array corresponding to the `signal`. Assumed to have a constant
            time step.
        signal : np.ndarray
            The original signal (waveform) to be delayed.

        Returns
        -------
        np.ndarray
            The delayed signal, which has the same length as the original `signal`.
        """
        if len(time_array) < 2:
            # If there are fewer than 2 time points, a sampling frequency cannot be
            # determined, so return the original signal as no delay can be applied
            # meaningfully.
            return signal
        fs = time_array[1] - time_array[0]  # Calculate the sampling interval (time step).

        # Calculate the number of samples corresponding to the desired delay.
        # Rounding is used to get an integer number of samples.
        delay_samples = int(round(delay / fs))

        if delay_samples >= len(time_array):
            # If the calculated delay in samples is greater than or equal to the
            # length of the original signal, the entire signal will effectively
            # be replaced by the `delayed_value`.
            return np.full_like(signal, delayed_value)

        # Create an array filled with `delayed_value` for the duration of the delay.
        sample = np.full(delay_samples, delayed_value)
        # Concatenate this delay 'prefix' with the original signal.
        # Then, truncate the combined array to the original signal's length,
        # effectively shifting the signal values.
        return np.concatenate((sample, signal))[: len(time_array)]

    def _cut_signal(self, value_min: float, signal: np.ndarray, value_max: float) -> np.ndarray:
        """
        Clips the values of a given signal array to ensure they stay
        within a specified minimum (`value_min`) and maximum (`value_max`) range.
        Values below `value_min` are set to `value_min`, and values above `value_max`
        are set to `value_max`.

        Parameters
        ----------
        value_min : float
            The minimum allowed value for the signal.
        signal : np.ndarray
            The input signal array whose values need to be clipped.
        value_max : float
            The maximum allowed value for the signal.

        Returns
        -------
        np.ndarray
            The signal with its values clipped within the specified limits.
        """
        # Use np.where to efficiently apply the clipping.
        # First, ensure no value is below value_min.
        signal = np.where(signal < value_min, value_min, signal)
        # Second, ensure no value is above value_max.
        signal = np.where(signal > value_max, value_max, signal)
        return signal
