#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

from abc import ABC, abstractmethod

import numpy as np

from dycov.gfm import constants
from dycov.gfm.parameters import GFMParameters


class GFMCalculator(ABC):
    """Base class of the Grid Forming (GFM) calculators, one per kind of grid event."""

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
        self._pmax_mois_tunnel = gfm_params.get_pmax_mois_tunnel()
        self._pmin_mois_tunnel = gfm_params.get_pmin_mois_tunnel()

        # The D, H and damping ratio of each variation the last calculation ran, which the
        # simulation dump reports and the first of which is the producer's own.
        self._d_vals = None
        self._h_vals = None
        self._epsilon_vals = None

    @abstractmethod
    def get_plot_parameter_names(self) -> list[str]:
        """
        Retrieves parameters relevant for rendering plots.

        Returns
        -------
        list[str]
            A list of parameter names to be displayed.
        """

    @abstractmethod
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

    def get_damping_ratio(self) -> float:
        """
        Retrieves the damping ratio of the producer's D and H in the last calculation.

        Returns
        -------
        float
            The damping ratio of the producer's D and H, not of one of their variations.
        """
        return self._epsilon_vals[self._ORIGINAL_PARAMS_IDX]

    def _natural_frequency(self, H: float, x_total: float) -> float:
        """
        Computes the natural frequency of the swing equation of the unit on the grid.

        Parameters
        ----------
        H : float
            The inertia constant.
        x_total : float
            The total reactance between the unit and the grid.

        Returns
        -------
        float
            The natural frequency in rad/s.
        """
        u_prod = self._initial_voltage * self._grid_voltage
        return np.sqrt(self._base_angular_frequency * u_prod / (2 * H * x_total))

    @staticmethod
    def _check_time_array(time_array: np.ndarray) -> None:
        """
        Rejects a time vector the envelopes cannot be calculated on.

        Parameters
        ----------
        time_array : np.ndarray
            The simulation time vector.

        Raises
        ------
        TypeError
            If the time is not a one-dimensional array of floats or signed integers.
        ValueError
            If the time vector has fewer than two points, or is not finite, strictly
            increasing and evenly spaced.
        """
        if not isinstance(time_array, np.ndarray):
            raise TypeError(
                "The time must be a one-dimensional array of floats or signed integers, not of "
                f"type {type(time_array).__name__}."
            )
        if time_array.ndim != 1 or time_array.dtype.kind not in "if":
            raise TypeError(
                "The time must be a one-dimensional array of floats or signed integers, not an "
                f"array of shape {time_array.shape} and type {time_array.dtype}."
            )
        if time_array.size < 2:
            raise ValueError("The time vector must have at least two points.")
        steps = np.diff(time_array)
        if not np.all(np.isfinite(time_array)) or not np.all(steps > 0):
            raise ValueError("The time vector must be finite and strictly increasing.")
        rounding_tolerance = 4 * np.spacing(np.abs(time_array).max())
        if not np.allclose(steps, steps[0], rtol=1e-6, atol=rounding_tolerance):
            raise ValueError("The time vector must be evenly spaced.")

    def _delay_by_emt(self, signal: np.ndarray, time_array: np.ndarray) -> np.ndarray:
        """
        Delays a signal by the EMT delay, holding its initial value meanwhile.

        Parameters
        ----------
        signal : np.ndarray
            The signal to delay.
        time_array : np.ndarray
            The simulation time vector.

        Returns
        -------
        np.ndarray
            The delayed signal.
        """
        return self._apply_delay(self._emt_delay, signal[0], time_array, signal)

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
            The resulting time-shifted array, as long as the time vector.
        """
        dt = time_array[1] - time_array[0]
        delay_samples = int(delay_time / dt) + 1

        if start_time > time_array[-1]:
            return signal

        start_idx = np.argmax(time_array >= start_time)
        delay_block = np.full(delay_samples, delayed_value)
        combined_signal = np.concatenate((signal[:start_idx], delay_block, signal[start_idx:]))
        return combined_signal[: len(time_array)]

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
            The tunnel, zero before the event and rising exponentially towards its final
            value after it.
        """
        t_val = max(self._final_allowed_tunnel_pn, self._final_allowed_tunnel_variation * p_peak)
        tunnel_exp = 1 - np.exp(
            (-time_array + constants.TIME_TUNNEL_START_OFFSET) / constants.TIME_TUNNEL_EXP_TAU
        )
        tunnel = t_val * tunnel_exp
        return np.where(time_array < event_time, 0, tunnel)
