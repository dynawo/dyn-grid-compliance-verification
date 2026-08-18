#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA

import numpy as np

from dycov.gfm import constants
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.parameters import GFMParameters
from dycov.logging import dycov_logging


class PhaseJump(GFMCalculator):
    """Handles the GFM response to a phase jump event."""

    def __init__(self, gfm_params: GFMParameters) -> None:
        super().__init__(gfm_params=gfm_params)
        self._delta_phase = gfm_params.get_delta_phase()
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()

    def get_plot_parameter_names(self) -> list[str]:
        return ["P0", "Q0", "DeltaPhase", "AngleStepAtPDR", "SCR", "Xeff", "D", "H", "Epsilon"]

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        logger = dycov_logging.get_logger("PhaseJump")
        logger.debug(f"Input Params D={D} H={H} Xeff {Xeff}")
        logger.debug(
            f"Input Params Phase={self._delta_phase} SCR={self._scr} "
            f"P0={self._initial_active_power} PMin={self._min_active_power} PMax={self._max_active_power}"
        )

        self._d_val = D
        self._h_val = H
        _, self._epsilon, _, _ = self._calculate_common_params(D, H, Xeff)

        delta_p_array, delta_p_min, delta_p_max, p_peak_array, _ = self._get_delta_p(
            D=D, H=H, Xeff=Xeff, time_array=time_array, event_time=event_time
        )

        p_pcc, p_up, p_down = self._get_envelopes(
            delta_p_array=delta_p_array,
            delta_p_min=delta_p_min,
            delta_p_max=delta_p_max,
            p_peak_array=p_peak_array,
            time_array=time_array,
            event_time=event_time,
        )

        if self._is_emt_flag:
            upper_envelope = self._apply_delay(self._emt_delay, p_up[0], time_array, p_up)
            lower_envelope = self._apply_delay(self._emt_delay, p_down[0], time_array, p_down)
            pcc_signal = self._apply_delay(self._emt_delay, p_pcc[0], time_array, p_pcc)
        else:
            upper_envelope, lower_envelope, pcc_signal = p_up, p_down, p_pcc

        return "Ip", pcc_signal, upper_envelope, lower_envelope

    def _get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[list[np.ndarray], np.ndarray, np.ndarray, list[float], list[float]]:
        x_gr = 1 / self._scr
        x_total_initial = Xeff + x_gr

        d_array = np.array([D, D * self._min_ratio, D * self._max_ratio])
        h_array = np.array([H, H * self._min_ratio, H * self._max_ratio])

        epsilon_initial_check = self._calculate_epsilon_initial_check(
            d_array, h_array, x_total_initial
        )
        dycov_logging.get_logger("PhaseJump").debug(f"Epsilon={epsilon_initial_check}")

        delta_p_array, p_peak_array, epsilon_array = [], [], []

        for i in range(len(d_array)):
            delta_p, p_peak, epsilon = self._calculate_delta_p_for_damping(
                d_array[i], h_array[i], Xeff, time_array, event_time, epsilon_initial_check[i]
            )
            delta_p_array.append(delta_p)
            p_peak_array.append(p_peak)
            epsilon_array.append(epsilon)

        if epsilon_initial_check[self._ORIGINAL_PARAMS_IDX] > self._EPSILON_THRESHOLD:
            delta_p_min = self._get_overdamped_delta_p_min(D, H, Xeff, time_array, event_time)
            delta_p_max = self._get_overdamped_delta_p_max(D, H, Xeff, time_array, event_time)
        else:
            delta_p_min = self._get_underdamped_delta_p_min(D, H, Xeff, time_array, event_time)
            delta_p_max = self._get_underdamped_delta_p_max(D, H, Xeff, time_array, event_time)

        self._d_vals, self._h_vals, self._epsilon_vals = d_array, h_array, np.array(epsilon_array)
        return delta_p_array, delta_p_min, delta_p_max, p_peak_array, epsilon_array

    def _get_envelopes(
        self,
        delta_p_array: list[np.ndarray],
        delta_p_min: np.ndarray,
        delta_p_max: np.ndarray,
        p_peak_array: list[float],
        time_array: np.ndarray,
        event_time: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        delta_p = delta_p_array[self._ORIGINAL_PARAMS_IDX]
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]
        sign = np.sign(self._delta_phase)

        tunnel_time_dep = self._get_time_tunnel(
            p_peak=p_peak, time_array=time_array, event_time=event_time
        )
        p_pcc = self._initial_active_power + delta_p * -(sign)

        list_of_arrays: list[np.ndarray] = delta_p_array + [delta_p_min, delta_p_max]
        lower_env_unlimited, upper_env_unlimited = self._calculate_unlimited_power_envelopes(
            list_of_arrays, tunnel_time_dep
        )

        lower_envelope, upper_envelope = self._limit_power_envelopes(
            lower_env_unlimited,
            upper_env_unlimited,
            self._get_tunnel(p_peak_array),
            self._initial_active_power,
            self._max_active_power,
            self._min_active_power,
            sign,
            True,
        )

        return p_pcc, upper_envelope, lower_envelope

    def _calculate_common_params(
        self, D: float, H: float, Xeff: float
    ) -> tuple[float, float, float, float]:
        x_gr = 1 / self._scr
        x_total_initial = Xeff + x_gr
        u_prod = self._initial_voltage * self._grid_voltage

        epsilon = (D / 2) * np.sqrt(
            x_total_initial / (2 * H * self._base_angular_frequency * u_prod)
        )
        wn = np.sqrt(self._base_angular_frequency * u_prod / (2 * H * x_total_initial))
        delta_theta_rad = np.abs(self._delta_phase * np.pi / 180)
        p_peak_calc = delta_theta_rad * u_prod / x_total_initial

        self._epsilon = epsilon
        return x_total_initial, epsilon, wn, p_peak_calc

    def _calculate_delta_p_for_damping(
        self,
        D: float,
        H: float,
        Xeff: float,
        time_array: np.ndarray,
        event_time: float,
        epsilon_initial_check: float,
    ) -> tuple[np.ndarray, float, float]:
        if epsilon_initial_check > self._EPSILON_THRESHOLD:
            return self._get_overdamped_delta_p(D, H, Xeff, time_array, event_time)
        else:
            return self._get_underdamped_delta_p(D, H, Xeff, time_array, event_time)

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """Resolves the fundamental delta_p waveform for an overdamped system."""
        _, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)
        wd = wn * np.sqrt(epsilon**2 - 1)

        # Alpha and Beta mathematically represent the real roots defining the overdamped characteristic equation[cite: 2]
        alpha = epsilon * wn + wd
        beta = epsilon * wn - wd

        # A and B formulate the initial integration constants for the second-order response[cite: 2]
        A = 1 / (beta - alpha)
        B = -A

        # Deconstruct the solution into its elemental exponential decay responses[cite: 2]
        term1 = 2 * H * A * (1 - alpha * np.exp(-alpha * time_array))
        term2 = 2 * H * B * (1 - beta * np.exp(-beta * time_array))
        term3 = D * A * np.exp(-alpha * time_array)
        term4 = D * B * np.exp(-beta * time_array)

        # Synthesize the final aggregated power deviation solution[cite: 2]
        delta_p1 = (p_peak / (2 * H)) * (term1 + term2 + term3 + term4)
        return delta_p1, p_peak, epsilon

    def _get_overdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        delta_p1, p_peak, epsilon = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p = np.where(time_array < event_time, 0, delta_p1)
        return delta_p, p_peak, epsilon

    def _get_overdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        delta_p1, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p1_margined = (1 + self._margin_low) * delta_p1
        return np.where(time_array < event_time, 0, delta_p1_margined)

    def _get_overdamped_delta_p_max(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        delta_p, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p_margined = self._margin_high * delta_p
        delta_p_delayed = self._apply_delay(
            constants.OVERDAMPED_MAX_DELAY_S, 0, time_array, delta_p_margined
        )
        return np.where(time_array < event_time, 0, delta_p_delayed)

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """Resolves the fundamental delta_p waveform capturing oscillatory traits[cite: 2]"""
        _, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)
        wd = wn * np.sqrt(1 - epsilon**2)

        # Synthesize components: An exponential decay boundary bounding sinusoidal oscillation[cite: 2]
        term1 = np.exp(-epsilon * wn * time_array)
        term2 = np.cos(wd * time_array)
        term3 = np.sin(wd * time_array)

        delta_p1 = term1 * (term2 - (epsilon * wn - 1) / wd * term3) * p_peak
        return delta_p1, p_peak, epsilon

    def _get_underdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        delta_p1, p_peak, epsilon = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p = np.where(time_array < event_time, 0, delta_p1)
        return delta_p, p_peak, epsilon

    def _get_underdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        _, p_peak, _ = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        sigma = D / (4 * H)
        delta_p_margined = p_peak * (1 - self._margin_low) * np.exp(-sigma * time_array)
        delta_p_delayed = self._apply_delay(
            constants.UNDERDAMPED_MIN_DELAY_S, 0, time_array, delta_p_margined
        )
        return np.where(time_array < event_time, 0, delta_p_delayed)

    def _get_underdamped_delta_p_max(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        _, p_peak, _ = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        sigma = D / (4 * H)
        delta_p_margined = p_peak * (1 + self._margin_high) * np.exp(-sigma * time_array)
        delta_p_delayed = self._apply_delay(
            constants.UNDERDAMPED_MAX_DELAY_S, delta_p_margined[0], time_array, delta_p_margined
        )
        return np.where(time_array < event_time, 0, delta_p_delayed)

    def _get_tunnel(self, p_peak_array: list[float]) -> float:
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]
        return max(self._final_allowed_tunnel_pn, self._final_allowed_tunnel_variation * p_peak)
