#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA

import numpy as np

from dycov.gfm import constants
from dycov.gfm.parameters import GFMParameters


class GFMCalculator:
    """Abstract base class for all Grid Forming (GFM) calculators."""

    _ORIGINAL_PARAMS_IDX = 0
    _MINIMUM_PARAMS_IDX = 1
    _MAXIMUM_PARAMS_IDX = 2

    # Threshold defining the boundary between underdamped (< 1.0) and overdamped (>= 1.0) systems.
    # Note: Critically damped systems (exactly 1.0) are mathematically grouped with the overdamped logic[cite: 2].
    _EPSILON_THRESHOLD = 1.0

    def __init__(self, gfm_params: GFMParameters) -> None:
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

    def get_plot_parameter_names(self) -> list[str]:
        raise NotImplementedError

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        raise NotImplementedError

    def _apply_delay(
        self,
        delay_time: float,
        delayed_value: float,
        time_array: np.ndarray,
        signal: np.ndarray,
        start_time: float = 0.0,
    ) -> np.ndarray:
        """Applies a temporal right-shift delay to a signal."""
        dt = time_array[1] - time_array[0]
        delay_samples = int(delay_time / dt) + 1

        # Safety Check: If the requested start time exceeds the simulation horizon, abort modification[cite: 2]
        if start_time > time_array[-1]:
            return signal

        # Isolate the precise index corresponding to the delay initiation threshold[cite: 2]
        start_idx = np.argmax(time_array >= start_time)
        pre_delay_signal = signal[:start_idx]
        delay_block = np.full(delay_samples, delayed_value)
        post_delay_signal = signal[start_idx:]

        combined_signal = np.concatenate((pre_delay_signal, delay_block, post_delay_signal))
        return combined_signal[: len(time_array)]

    def _cut_signal(self, value_min: float, signal: np.ndarray, value_max: float) -> np.ndarray:
        """Clips signal values that exceed specified operational limits."""
        return np.clip(signal, value_min, value_max)

    def _calculate_epsilon_initial_check(
        self, D: np.ndarray, H: np.ndarray, x_total_initial: float
    ) -> np.ndarray:
        """Computes the damping ratio (epsilon) to classify the dynamic response."""
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
        """Generates a dynamic, time-dependent tolerance band ('tunnel')."""
        t_val = max(self._final_allowed_tunnel_pn, self._final_allowed_tunnel_variation * p_peak)
        tunnel_exp = 1 - np.exp(
            (-time_array + constants.TIME_TUNNEL_START_OFFSET) / constants.TIME_TUNNEL_EXP_TAU
        )
        tunnel = t_val * tunnel_exp
        return np.where(time_array < event_time, 0, tunnel)

    def _calculate_unlimited_power_envelopes(
        self, list_of_arrays: list[np.ndarray], tunnel: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Synthesizes theoretical bounding envelopes before hardware constraints."""
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
        """Executes hardware and software saturation boundary logic using optimized clipping."""
        limit_max = self._pmax_mois_tunnel
        limit_min = self._pmin_mois_tunnel

        if use_opposite_signs:
            # Execution branch applying divergent clipping dependent on trajectory vs steady-state opposition[cite: 2]
            if np.sign(initial_power) * sign == -1:
                lower_envelope_limited = np.clip(
                    initial_power - sign * lower_envelope_unlimited, limit_min, limit_max
                )
                upper_envelope_limited = np.clip(
                    initial_power - sign * upper_envelope_unlimited, min_power, max_power
                )
            else:
                lower_envelope_limited = np.clip(
                    initial_power - sign * lower_envelope_unlimited, min_power, max_power
                )
                upper_envelope_limited = np.clip(
                    initial_power - sign * upper_envelope_unlimited, limit_min, limit_max
                )
        else:
            # Standard unified execution branch handling symmetrical capability bounding[cite: 2]
            lower_envelope_limited = np.clip(
                initial_power - sign * lower_envelope_unlimited, limit_min, limit_max
            )
            upper_envelope_limited = np.clip(
                initial_power - sign * upper_envelope_unlimited, min_power, max_power
            )

        return lower_envelope_limited, upper_envelope_limited
