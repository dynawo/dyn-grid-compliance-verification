#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
from dycov.gfm import constants
from dycov.gfm.parameters import GFMParameters


class GFMCalculator:
    _ORIGINAL_PARAMS_IDX = 0
    _MINIMUM_PARAMS_IDX = 1
    _MAXIMUM_PARAMS_IDX = 2
    _EPSILON_THRESHOLD = 1.0

    def __init__(self, gfm_params: GFMParameters) -> None:
        """
        Parameters
        ----------
        gfm_params: GFMParameters
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
        self._d_vals = None
        self._h_vals = None
        self._epsilon_vals = None

    @property
    def d_vals(self) -> np.ndarray:
        return self._d_vals

    @property
    def h_vals(self) -> np.ndarray:
        return self._h_vals

    @property
    def epsilon_vals(self) -> np.ndarray:
        return self._epsilon_vals

    @property
    def epsilon(self) -> float:
        return getattr(self, "_epsilon", 0.0)

    @property
    def is_inconsistent(self) -> bool:
        return getattr(self, "_is_inconsistent", False)

    @property
    def disclaimer_message(self) -> str:
        return getattr(self, "_disclaimer_message", None)

    def get_plot_parameter_names(self) -> list[str]:
        """
        Returns
        -------
        list[str]
        """
        raise NotImplementedError

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Parameters
        ----------
        D : float
        H : float
        Xeff : float
        time_array : np.ndarray
        event_time : float

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
        """
        raise NotImplementedError

    def apply_emt_delay_to_envelopes(
        self,
        time_array: np.ndarray,
        pcc_signal: np.ndarray,
        upper_envelope: np.ndarray,
        lower_envelope: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Parameters
        ----------
        time_array : np.ndarray
        pcc_signal : np.ndarray
        upper_envelope : np.ndarray
        lower_envelope : np.ndarray

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
        """
        if not self._is_emt_flag:
            return pcc_signal, upper_envelope, lower_envelope
        up_val = upper_envelope[0] if not np.isscalar(upper_envelope) else upper_envelope
        down_val = lower_envelope[0] if not np.isscalar(lower_envelope) else lower_envelope
        pcc_val = pcc_signal[0] if not np.isscalar(pcc_signal) else pcc_signal
        up_final = self._apply_delay(
            delay_time=self._emt_delay,
            delayed_value=up_val,
            time_array=time_array,
            signal=upper_envelope,
        )
        down_final = self._apply_delay(
            delay_time=self._emt_delay,
            delayed_value=down_val,
            time_array=time_array,
            signal=lower_envelope,
        )
        pcc_final = self._apply_delay(
            delay_time=self._emt_delay,
            delayed_value=pcc_val,
            time_array=time_array,
            signal=pcc_signal,
        )
        return pcc_final, up_final, down_final

    def _apply_delay(
        self,
        delay_time: float,
        delayed_value: float,
        time_array: np.ndarray,
        signal: np.ndarray,
        start_time: float = 0.0,
    ) -> np.ndarray:
        """
        Parameters
        ----------
        delay_time : float
        delayed_value : float
        time_array : np.ndarray
        signal : np.ndarray
        start_time : float, optional

        Returns
        -------
        np.ndarray
        """
        dt = time_array[1] - time_array[0]
        delay_samples = int(delay_time / dt) + 1
        if start_time > time_array[-1]:
            return signal
        start_idx = np.argmax(time_array >= start_time)
        pre_delay_signal = signal[:start_idx]
        delay_block = np.full(shape=delay_samples, fill_value=delayed_value)
        post_delay_signal = signal[start_idx:]
        combined_signal = np.concatenate((pre_delay_signal, delay_block, post_delay_signal))
        return combined_signal[: len(time_array)]

    def _cut_signal(self, value_min: float, signal: np.ndarray, value_max: float) -> np.ndarray:
        """
        Parameters
        ----------
        value_min : float
        signal : np.ndarray
        value_max : float

        Returns
        -------
        np.ndarray
        """
        signal = np.where(signal < value_min, value_min, signal)
        signal = np.where(signal > value_max, value_max, signal)
        return signal

    def _calculate_epsilon_initial_check(
        self, D: np.ndarray, H: np.ndarray, x_total_initial: float
    ) -> np.ndarray:
        """
        Parameters
        ----------
        D : np.ndarray
        H : np.ndarray
        x_total_initial : float

        Returns
        -------
        np.ndarray
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
        Parameters
        ----------
        p_peak : float
        time_array : np.ndarray
        event_time : float

        Returns
        -------
        np.ndarray
        """
        t_val = max(self._final_allowed_tunnel_pn, self._final_allowed_tunnel_variation * p_peak)
        tunnel_exp = 1 - np.exp(
            (-time_array + constants.TIME_TUNNEL_START_OFFSET) / constants.TIME_TUNNEL_EXP_TAU
        )
        tunnel = t_val * tunnel_exp
        return np.where(time_array < event_time, 0, tunnel)

    def _calculate_unlimited_power_envelopes(
        self, list_of_arrays: list[np.ndarray], tunnel: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Parameters
        ----------
        list_of_arrays : list[np.ndarray]
        tunnel : np.ndarray

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
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
        Parameters
        ----------
        lower_envelope_unlimited : np.ndarray
        upper_envelope_unlimited : np.ndarray
        tunnel_value : float
        initial_power : float
        max_power : float
        min_power : float
        sign : int
        use_opposite_signs : bool

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
        """
        limit_max = self._pmax_mois_tunnel
        limit_min = self._pmin_mois_tunnel
        if use_opposite_signs:
            # Apply divergent clipping when initial power and disturbance direction oppose each other
            if np.sign(initial_power) * sign == -1:
                lower_envelope_limited = np.minimum(
                    np.maximum(initial_power - sign * lower_envelope_unlimited, limit_min),
                    limit_max,
                )
                upper_envelope_limited = np.minimum(
                    np.maximum(initial_power - sign * upper_envelope_unlimited, min_power),
                    max_power,
                )
            else:
                lower_envelope_limited = np.minimum(
                    np.maximum(initial_power - sign * lower_envelope_unlimited, min_power),
                    max_power,
                )
                upper_envelope_limited = np.minimum(
                    np.maximum(initial_power - sign * upper_envelope_unlimited, limit_min),
                    limit_max,
                )
        else:
            lower_envelope_limited = np.minimum(
                np.maximum(initial_power - sign * lower_envelope_unlimited, limit_min), limit_max
            )
            upper_envelope_limited = np.minimum(
                np.maximum(initial_power - sign * upper_envelope_unlimited, min_power), max_power
            )
        return lower_envelope_limited, upper_envelope_limited
