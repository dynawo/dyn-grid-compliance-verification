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

from dycov.gfm.parameters import GFMParameters


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

    def __init__(self, gfm_params: GFMParameters) -> None:
        """
        Initializes the GFMCalculator with system parameters.

        Parameters
        ----------
        gfm_params: GFMParameters
            An object containing all necessary parameters for GFM calculations.
        """
        self._scr = gfm_params.get_scr()
        self._min_ratio = gfm_params.get_min_ratio()
        self._max_ratio = gfm_params.get_max_ratio()
        self._is_emt_flag = gfm_params.is_emt()
        self._initial_voltage = gfm_params.get_initial_voltage()
        self._grid_voltage = gfm_params.get_grid_voltage()
        self._base_angular_frequency = gfm_params.get_base_angular_frequency()
        self._margin_low = gfm_params.get_margin_low()
        self._margin_high = gfm_params.get_margin_high()
        self._final_allowed_tunnel_pn = gfm_params.get_final_allowed_tunnel_pn()
        self._final_allowed_tunnel_variation = gfm_params.get_final_allowed_tunnel_variation()

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Abstract method to be implemented by subclasses for calculating power envelopes.

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
            - str: Name of the calculated magnitude (e.g., "P", "Q").
            - np.ndarray: The PCC (Point of Common Coupling) power data.
            - np.ndarray: The upper envelope data.
            - np.ndarray: The lower envelope data.
        """
        raise NotImplementedError

    def _apply_delay(
        self, delay_time: float, delayed_value: float, time_array: np.ndarray, signal: np.ndarray
    ) -> np.ndarray:
        """
        Applies a time delay to a given signal.

        This method shifts the signal in time, filling the initial part of
        the array with a specified `delayed_value` for the duration of the delay.

        Parameters
        ----------
        delay_time : float
            The amount of time (in seconds) by which to delay the signal.
        delayed_value : float
            The value to use for the signal during the delay period.
        time_array : np.ndarray
            The original time array of the signal.
        signal : np.ndarray
            The input signal array to be delayed.

        Returns
        -------
        np.ndarray
            The delayed signal array, truncated to the original length.
        """
        # Calculate the number of samples corresponding to the delay time.
        # Ensure at least one sample for the delay.
        delay_samples = max(1, int(delay_time / (time_array[1] - time_array[0])))
        # Create a 'prefix' array filled with `delayed_value` for the duration
        # of the delay.
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
        signal = np.where(signal < value_min, value_min, signal)
        signal = np.where(signal > value_max, value_max, signal)
        return signal

    def _calculate_epsilon_initial_check(
        self, D: np.ndarray, H: np.ndarray, x_total_initial: float
    ) -> float:
        """
        Calculates the initial damping ratio (epsilon) to determine
        whether the system's response is overdamped or underdamped.
        This calculation uses base values to determine the overall system behavior.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        x_total_initial : float
            Total initial reactance of the system.

        Returns
        -------
        float
            The calculated initial damping ratio (epsilon).
        """
        return (
            D
            / 2
            * np.sqrt(
                x_total_initial
                / (
                    2
                    * H
                    * self._base_angular_frequency
                    * self._initial_voltage
                    * self._grid_voltage
                )
            )
        )

    def _get_time_tunnel(
        self, p_peak: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Calculates a time-dependent "tunnel" array. This array represents
        a dynamic band around the power response that expands over time after an
        event. It starts at zero before the event and increases exponentially
        towards a final magnitude.

        Parameters
        ----------
        p_peak : float
            The peak power value, used to determine the final magnitude of the tunnel.
        time_array : np.ndarray
            The array of time points for the simulation.
        event_time : float
            The time at which the event occurs, before which the tunnel is zero.

        Returns
        -------
        np.ndarray
            The time-dependent tunnel array.
        """
        t_val = max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * p_peak,
        )
        tunnel_exp = 1 - np.exp((-time_array + 0.02) / 0.3)
        tunnel = t_val * tunnel_exp
        return np.where(time_array < event_time, 0, tunnel)

    def _calculate_unlimited_power_envelopes(
        self, list_of_arrays: list[np.ndarray], tunnel: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculates the initial (unlimited) power down and power up envelopes.
        This is done by finding the minimum and maximum across various delta_p arrays
        and adjusting them by the time-dependent tunnel, effectively creating a band.

        Parameters
        ----------
        list_of_arrays : list[np.ndarray]
            A list of delta_p arrays (e.g., nominal, min/max D/H variations, specific
            min/max delta_p) to be used for determining the overall minimum and maximum
            response.
        tunnel : np.ndarray
            The time-dependent tunnel response array, which defines the dynamic width of
            the band.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing:
            - pdown_no_p0: The calculated lower power envelope, without considering the
              initial power (P0).
            - pup_no_p0: The calculated upper power envelope, without considering the
              initial power (P0).
        """
        pdown_no_p0 = np.minimum.reduce(list_of_arrays) - tunnel
        pup_no_p0 = np.maximum.reduce(list_of_arrays) + tunnel
        return np.minimum(pdown_no_p0, pup_no_p0), np.maximum(pdown_no_p0, pup_no_p0)

    def _limit_power_envelopes(
        self,
        pdown_no_p0: np.ndarray,
        pup_no_p0: np.ndarray,
        tunnel_value: float,
        initial_power: float,
        max_power: float,
        min_power: float,
        sign: int,
        use_opposite_signs: bool,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Applies final operational limits to the calculated power down and power up
        envelopes. This involves incorporating the initial power (P0) and clipping
        the signals based on system-defined minimum/maximum power and a constant
        tunnel value.

        Parameters
        ----------
        pdown_no_p0 : np.ndarray
            The unlimited power down signal, not yet adjusted by initial power P0.
        pup_no_p0 : np.ndarray
            The unlimited power up signal, not yet adjusted by initial power P0.
        tunnel_value : float
            The constant tunnel value used for final limiting, defining the static
            band width.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing:
            - pdown_limited: The final, limited power down envelope.
            - pup_limited: The final, limited power up envelope.
        """

        if use_opposite_signs:
            # This checks if the initial power and the angle change have opposite signs.
            if np.sign(initial_power) * sign == -1:
                pdown_limited = np.minimum(
                    np.maximum(
                        initial_power - sign * pdown_no_p0,
                        -1 + tunnel_value,
                    ),
                    1 - tunnel_value,
                )
                pup_limited = np.minimum(
                    np.maximum(
                        initial_power - sign * pup_no_p0,
                        -max_power,
                    ),
                    max_power,
                )

            else:
                pdown_limited = np.minimum(
                    np.maximum(
                        initial_power - sign * pdown_no_p0,
                        -max_power,
                    ),
                    max_power,
                )
                pup_limited = np.minimum(
                    np.maximum(
                        initial_power - sign * pup_no_p0,
                        -1 + tunnel_value,
                    ),
                    1 - tunnel_value,
                )

        else:
            pdown_limited = np.minimum(
                np.maximum(
                    initial_power - sign * pdown_no_p0,
                    -1 + tunnel_value,
                ),
                1 - tunnel_value,
            )
            pup_limited = np.minimum(
                np.maximum(
                    initial_power - 1 * sign * pup_no_p0,
                    min_power,
                ),
                max_power,
            )

        return pdown_limited, pup_limited
