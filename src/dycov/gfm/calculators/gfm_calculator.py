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

from dycov.gfm import constants
from dycov.gfm.parameters import GFMParameters


class GFMCalculator:
    """
    Base class for Grid Forming (GFM) calculations.

    This class provides common attributes and an abstract method for calculating
    response envelopes in GFM systems. It defines constants for parameter
    indexing and a threshold for damping classification.
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

        # Attributes for INI dump validation
        self._d_vals = None
        self._h_vals = None
        self._epsilon_vals = None

    def get_plot_parameter_names(self) -> list[str]:
        """
        Abstract method to get the list of parameter names relevant for plotting.
        This method must be implemented by each concrete calculator subclass.

        Returns
        -------
        list[str]
            A list of parameter names (as strings) to be displayed on the plot.
        """
        raise NotImplementedError

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Abstract method to be implemented by subclasses for calculating
        response envelopes.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Array of time points for the simulation.
        event_time : float
            The time (in seconds) at which the event occurs.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - str: Name of the calculated magnitude (e.g., "P", "Iq").
            - np.ndarray: The calculated signal at the PCC (Point of Common Coupling).
            - np.ndarray: The upper envelope of the signal.
            - np.ndarray: The lower envelope of the signal.
        """
        raise NotImplementedError

    def _apply_delay(
        self,
        delay_time: float,
        delayed_value: float,
        time_array: np.ndarray,
        signal: np.ndarray,
        start_time: float = 0.0,
    ) -> np.ndarray:
        """
        Applies a time delay to a given signal starting at a specific time (default t=0).

        This method keeps the signal unchanged for t < start_time. At t=start_time,
        it inserts the `delayed_value` for the duration of the delay, shifting the
        subsequent original signal values to the right.

        Parameters
        ----------
        delay_time : float
            The amount of time (in seconds) by which to delay the signal.
        delayed_value : float
            The value to use for the signal during the delay period.
        time_array : np.ndarray
            The original time array of the signal (can contain negative values).
        signal : np.ndarray
            The input signal array to be delayed.
        start_time : float, optional
            The time at which the delay should start applied. Defaults to 0.0.

        Returns
        -------
        np.ndarray
            The delayed signal array, truncated to the original length.
        """
        # 1. Calculate sample time (dt) assuming uniform spacing
        dt = time_array[1] - time_array[0]

        # 2. Calculate how many samples correspond to the delay_time
        delay_samples = int(delay_time / dt) + 1

        # Safety check: If start_time is beyond the simulation range, return original signal
        if start_time > time_array[-1]:
            return signal

        # 3. Find the index where time becomes >= start_time
        start_idx = np.argmax(time_array >= start_time)

        # 4. Construct the new signal
        pre_delay_signal = signal[:start_idx]
        delay_block = np.full(delay_samples, delayed_value)
        post_delay_signal = signal[start_idx:]

        # 5. Concatenate parts
        combined_signal = np.concatenate((pre_delay_signal, delay_block, post_delay_signal))

        # 6. Truncate to match the original length of time_array
        return combined_signal[: len(time_array)]

    def _cut_signal(self, value_min: float, signal: np.ndarray, value_max: float) -> np.ndarray:
        """
        Clips the values of a signal array to ensure they stay within a
        specified minimum (`value_min`) and maximum (`value_max`) range.

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
    ) -> np.ndarray:
        """
        Calculates the initial damping ratio (epsilon) to determine
        whether the system's response is overdamped or underdamped.

        Parameters
        ----------
        D : np.ndarray
            Array of damping factors.
        H : np.ndarray
            Array of inertia constants.
        x_total_initial : float
            Total initial reactance of the system.

        Returns
        -------
        np.ndarray
            The array of calculated damping ratios (epsilon).
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
        Calculates a time-dependent "tunnel" array.

        This array represents a dynamic band around the power response that
        expands over time after an event. It starts at zero before the event
        and increases exponentially towards a final magnitude.

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
        tunnel_exp = 1 - np.exp(
            (-time_array + constants.TIME_TUNNEL_START_OFFSET) / constants.TIME_TUNNEL_EXP_TAU
        )
        tunnel = t_val * tunnel_exp
        return np.where(time_array < event_time, 0, tunnel)

    def _calculate_unlimited_power_envelopes(
        self, list_of_arrays: list[np.ndarray], tunnel: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculates the initial (unlimited) power down and power up envelopes.

        This is done by finding the minimum and maximum across various delta_p arrays
        and adjusting them by the time-dependent tunnel.

        Parameters
        ----------
        list_of_arrays : list[np.ndarray]
            A list of delta_p arrays (e.g., nominal, min/max variations) to be
            used for determining the overall minimum and maximum response.
        tunnel : np.ndarray
            The time-dependent tunnel response array.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing:
            - lower_env: The calculated lower envelope.
            - upper_env: The calculated upper envelope.
        """
        lower_env = np.minimum.reduce(list_of_arrays) - tunnel
        upper_env = np.maximum.reduce(list_of_arrays) + tunnel
        return np.minimum(lower_env, upper_env), np.maximum(lower_env, upper_env)

    def _limit_power_envelopes(
        self,
        lower_envelope_unlimited: np.ndarray,
        upper_envelope_unlimited: np.ndarray,
        tunnel_value: float,
        initial_power: float,
        max_power: float,
        min_power: float,
        sign: int,
        use_opposite_signs: bool,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Applies final operational limits to the calculated power envelopes.

        This involves incorporating the initial power (P0) and clipping
        the signals based on system-defined minimum/maximum power.

        Parameters
        ----------
        lower_envelope_unlimited : np.ndarray
            The unlimited lower envelope signal, not yet adjusted by initial power P0.
        upper_envelope_unlimited : np.ndarray
            The unlimited upper envelope signal, not yet adjusted by initial power P0.
        tunnel_value : float
            The constant tunnel value used for final limiting.
        initial_power : float
            The initial active or reactive power.
        max_power : float
            The maximum power limit.
        min_power : float
            The minimum power limit.
        sign : int
            The sign of the disturbance (e.g., of the phase jump).
        use_opposite_signs : bool
            A flag for a specific clipping logic.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing:
            - lower_envelope_limited: The final, limited lower envelope.
            - upper_envelope_limited: The final, limited upper envelope.
        """

        limit_max = max_power - tunnel_value
        limit_min = min_power + tunnel_value

        if use_opposite_signs:
            # This checks if the initial power and the angle change have opposite signs.
            if np.sign(initial_power) * sign == -1:
                lower_envelope_limited = np.minimum(
                    np.maximum(
                        initial_power - sign * lower_envelope_unlimited,
                        limit_min,
                    ),
                    limit_max,
                )
                upper_envelope_limited = np.minimum(
                    np.maximum(
                        initial_power - sign * upper_envelope_unlimited,
                        -max_power,
                    ),
                    max_power,
                )
            else:
                lower_envelope_limited = np.minimum(
                    np.maximum(
                        initial_power - sign * lower_envelope_unlimited,
                        -max_power,
                    ),
                    max_power,
                )
                upper_envelope_limited = np.minimum(
                    np.maximum(
                        initial_power - sign * upper_envelope_unlimited,
                        limit_min,
                    ),
                    limit_max,
                )

        else:
            # Standard logic (used in most calculators)
            lower_envelope_limited = np.minimum(
                np.maximum(
                    initial_power - sign * lower_envelope_unlimited,
                    limit_min,
                ),
                limit_max,
            )
            upper_envelope_limited = np.minimum(
                np.maximum(
                    initial_power - 1 * sign * upper_envelope_unlimited,
                    min_power,
                ),
                max_power,
            )

        return lower_envelope_limited, upper_envelope_limited
