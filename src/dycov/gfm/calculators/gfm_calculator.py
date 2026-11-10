#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

import numpy as np

from dycov.gfm import constants
from dycov.gfm.parameters import GFMParameters


class GFMCalculator:
    """Abstract base class for all Grid Forming (GFM) calculators."""

    _ORIGINAL_PARAMS_IDX = 0
    _MINIMUM_PARAMS_IDX = 1
    _MAXIMUM_PARAMS_IDX = 2
    _EPSILON_THRESHOLD = 1.0

    def __init__(self, gfm_params: GFMParameters) -> None:
        """
        Initializes the base properties for all GFM calculators.

        Parameters
        ----------
        gfm_params : GFMParameters
            The shared configuration parameters.
        """
        self._scr = gfm_params.get_scr()
        self._min_ratio = gfm_params.get_min_ratio()
        self._max_ratio = gfm_params.get_max_ratio()
        self._is_emt_flag = gfm_params.is_emt()
        self._emt_delay = gfm_params.get_emt_delay()
        self._initial_voltage = gfm_params.get_initial_voltage()
        self._grid_voltage = gfm_params.get_grid_voltage()
        self._base_angular_frequency = gfm_params.get_base_angular_frequency()
        self._margin_low = gfm_params.get_margin_low()
        self._margin_high = gfm_params.get_margin_high()
        self._final_allowed_tunnel_pn = gfm_params.get_final_allowed_tunnel_pn()
        self._final_allowed_tunnel_variation = gfm_params.get_final_allowed_tunnel_variation()

        self._d_vals = None
        self._h_vals = None
        self._epsilon_vals = None

    def get_plot_parameter_names(self) -> list[str]:
        """
        Retrieves parameters relevant for rendering plots.

        Returns
        -------
        list[str]
            A list of parameter names to be displayed.
        """
        raise NotImplementedError

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the signal deviation and bounding envelopes.

        Parameters
        ----------
        D : float
            The damping constant.
        H : float
            The inertia constant.
        Xeff : float
            The effective reactance.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp when the grid event occurs.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing the
            magnitude name, the main signal, the upper envelope, and the lower envelope.
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
        Applies a temporal right-shift delay to a signal.

        Parameters
        ----------
        delay_time : float
            The duration of the delay in seconds.
        delayed_value : float
            The constant value applied during the delay period.
        time_array : np.ndarray
            The simulation time vector.
        signal : np.ndarray
            The original signal to be delayed.
        start_time : float, optional
            The time at which delay logic initiates. Defaults to 0.0.

        Returns
        -------
        np.ndarray
            The resulting time-shifted array.
        """
        # Calculate the discrete number of samples to shift based on time resolution
        dt = time_array[1] - time_array[0]
        delay_samples = int(delay_time / dt) + 1

        if start_time > time_array[-1]:
            return signal

        start_idx = np.argmax(time_array >= start_time)
        pre_delay_signal = signal[:start_idx]

        # Inject the delayed constant value block
        delay_block = np.full(delay_samples, delayed_value)
        post_delay_signal = signal[start_idx:]

        combined_signal = np.concatenate((pre_delay_signal, delay_block, post_delay_signal))
        return combined_signal[: len(time_array)]

    def _cut_signal(self, value_min: float, signal: np.ndarray, value_max: float) -> np.ndarray:
        """
        Clips signal values that exceed specified operational limits.

        Parameters
        ----------
        value_min : float
            The lower boundary limit.
        signal : np.ndarray
            The array to be clipped.
        value_max : float
            The upper boundary limit.

        Returns
        -------
        np.ndarray
            The clipped signal array.
        """
        return np.clip(signal, value_min, value_max)

    def _get_time_tunnel(
        self, p_peak: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Generates a dynamic, time-dependent tolerance band ('tunnel').

        Parameters
        ----------
        p_peak : float
            The absolute peak power deviation.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The time the event occurs.

        Returns
        -------
        np.ndarray
            An array representing the dynamic tunnel values over time.
        """
        t_val = max(self._final_allowed_tunnel_pn, self._final_allowed_tunnel_variation * p_peak)

        # Calculate dynamic margin decaying exponentially over time
        tunnel_exp = 1 - np.exp(
            (-time_array + constants.TIME_TUNNEL_START_OFFSET) / constants.TIME_TUNNEL_EXP_TAU
        )
        tunnel = t_val * tunnel_exp
        return np.where(time_array < event_time, 0, tunnel)
