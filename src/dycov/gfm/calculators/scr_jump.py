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
import math

from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.parameters import GFMParameters
from dycov.logging.logging import dycov_logging


class SCRJump(GFMCalculator):
    """
    Class to calculate the GFM response to an SCR (Short-Circuit Ratio) Jump.
    This class handles all core calculations for delta_p and active power
    envelopes, differentiating between overdamped and underdamped system
    responses.
    """

    def __init__(
        self,
        gfm_params: GFMParameters,
    ) -> None:
        super().__init__(gfm_params=gfm_params)

        self._initial_scr = gfm_params.get_initial_scr()
        self._final_scr = gfm_params.get_final_scr()
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the change in power (delta_p) and active power envelopes (PCC,
        upper, and lower) based on damping characteristics for an SCR jump event.

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
            The time (in seconds) at which the SCR jump event occurs.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - magnitude: Name of the calculated magnitude ("P").
            - p_pcc_final: The final calculated active power at the PCC.
            - p_up_final: The final upper active power envelope.
            - p_down_final: The final lower active power envelope.
        """
        dycov_logging.get_logger("SCRJump").debug(f"Input Params D={D} H={H} Xeff {Xeff}")

        (
            delta_p_array,
            p_peak_array,
            epsilon_array,
            delta_p_up_env_array,
            delta_p_down_env_array,
        ) = self._get_delta_p(
            D=D,
            H=H,
            Xeff=Xeff,
            time_array=time_array,
            event_time=event_time,
        )

        p_pcc, p_up, p_down = self._get_envelopes(
            delta_p_array=delta_p_array,
            p_peak_array=p_peak_array,
            time_array=time_array,
            event_time=event_time,
            delta_p_up_env_array=delta_p_up_env_array,
            delta_p_down_env_array=delta_p_down_env_array,
        )
        return "P", p_pcc, p_up, p_down

    def _get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[list[np.ndarray], list[float], list[float], list[np.ndarray], list[np.ndarray]]:
        """
        Calculates the change in active power (delta_p) and related parameters
        based on damping characteristics.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Time array for the simulation.
        event_time : float
            Time at which the event occurs.

        Returns
        -------
        tuple[list[np.ndarray], list[float], list[float], list[np.ndarray], list[np.ndarray]]
            A tuple containing:
            - delta_p_array: List of delta_p arrays for parameter variations.
            - p_peak_array: List of p_peak values.
            - epsilon_array: List of epsilon values.
            - delta_p_up_env_array: List of analytical upper envelopes of delta_p.
            - delta_p_down_env_array: List of analytical lower envelopes of delta_p.
        """
        d_array = np.array([D, D * self._min_ratio, D * self._max_ratio])
        h_array = np.array([H, H / self._min_ratio, H / self._max_ratio])

        _, epsilon_check, _, _ = self._calculate_common_params(D, H, Xeff)
        dycov_logging.get_logger("SCRJump").debug(f"Epsilon={epsilon_check}")

        delta_p_array: list[np.ndarray] = []
        p_peak_array: list[float] = []
        epsilon_array: list[float] = []
        delta_p_up_env_array: list[np.ndarray] = []
        delta_p_down_env_array: list[np.ndarray] = []

        for i in range(len(d_array)):
            delta_p, p_peak, epsilon, delta_p_up, delta_p_down = (
                self._calculate_delta_p_for_damping(
                    d_array[i],
                    h_array[i],
                    Xeff,
                    time_array,
                    event_time,
                    epsilon_check,
                )
            )
            delta_p_array.append(delta_p)
            p_peak_array.append(p_peak)
            epsilon_array.append(epsilon)
            delta_p_up_env_array.append(delta_p_up)
            delta_p_down_env_array.append(delta_p_down)

        return (
            delta_p_array,
            p_peak_array,
            epsilon_array,
            delta_p_up_env_array,
            delta_p_down_env_array,
        )

    def _get_envelopes(
        self,
        delta_p_array: list[np.ndarray],
        p_peak_array: list[float],
        time_array: np.ndarray,
        event_time: float,
        delta_p_up_env_array: list[np.ndarray],
        delta_p_down_env_array: list[np.ndarray],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates and limits the final active power envelopes.

        Parameters
        ----------
        delta_p_array : list[np.ndarray]
            List of delta_p arrays.
        p_peak_array : list[float]
            List of p_peak values.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            Time at which the event occurs.
        delta_p_up_env_array : list[np.ndarray]
            Analytical upper envelopes of delta_p.
        delta_p_down_env_array : list[np.ndarray]
            Analytical lower envelopes of delta_p.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            p_pcc_final, p_up_final, p_down_final
        """
        delta_p = delta_p_array[self._ORIGINAL_PARAMS_IDX]
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]

        # Check the direction of power change right after the event
        delta_p_at_event = delta_p[np.where(time_array >= event_time)[0][1]]

        p_pcc = self._initial_active_power + delta_p
        tunnel = self._get_tunnel(p_peak)

        all_traces_up = []
        all_traces_down = []

        for i in range(len(delta_p_array)):
            current_delta_p = delta_p_array[i]
            current_delta_up_env = delta_p_up_env_array[i]
            current_delta_down_env = delta_p_down_env_array[i]

            # Underdamped case uses analytical envelopes
            if current_delta_up_env is not None and current_delta_down_env is not None:
                p_up_trace = (
                    self._initial_active_power
                    + current_delta_up_env * (1 + self._margin_high)
                    + tunnel
                )
                p_down_trace = (
                    self._initial_active_power
                    + current_delta_down_env * (1 - self._margin_low)
                    - tunnel
                )
            # Overdamped case uses the signal itself with margins
            else:
                if delta_p_at_event > 0:
                    # Power increases, so upper envelope is above and lower is below
                    p_up_trace = (
                        self._initial_active_power
                        + current_delta_p * (1 + self._margin_high)
                        + tunnel
                    )
                    p_down_trace = (
                        self._initial_active_power
                        + current_delta_p * (1 - self._margin_low)
                        - tunnel
                    )
                else:
                    # Power decreases, so margins are inverted relative to delta_p
                    p_up_trace = (
                        self._initial_active_power
                        + current_delta_p * (1 - self._margin_high)
                        + tunnel
                    )
                    p_down_trace = (
                        self._initial_active_power
                        + current_delta_p * (1 + self._margin_low)
                        - tunnel
                    )

        all_traces_up.append(p_up_trace)
        all_traces_down.append(p_down_trace)

        p_50_prc = self._initial_active_power + delta_p * 0.5
        all_traces_up.append(p_50_prc)
        all_traces_down.append(p_50_prc)

        p_up_unlimited = np.maximum.reduce(all_traces_up)
        p_down_unlimited = np.minimum.reduce(all_traces_down)

        pup_limited = np.clip(p_up_unlimited, self._min_active_power, self._max_active_power)
        pdown_limited = np.clip(p_down_unlimited, self._min_active_power, self._max_active_power)

        if self._is_emt_flag:
            p_up_final = self._apply_delay(0.02, pup_limited[0], time_array, pup_limited)
            p_down_final = self._apply_delay(0.02, pdown_limited[0], time_array, pdown_limited)
            p_pcc_final = self._apply_delay(0.02, p_pcc[0], time_array, p_pcc)
        else:
            p_up_final = pup_limited
            p_down_final = pdown_limited
            p_pcc_final = p_pcc

        return p_pcc_final, p_up_final, p_down_final

    def _calculate_common_params(
        self, D: float, H: float, Xeff: float
    ) -> tuple[float, float, float, float]:
        """
        Calculates common parameters required for delta_p calculations.
        """
        z_init = 1 / self._initial_scr
        z_final = 1 / self._final_scr
        delta_z_grid = z_final - z_init
        x_total_initial = Xeff + z_final
        u_prod = self._initial_voltage * self._grid_voltage

        wn = np.sqrt(self._base_angular_frequency * u_prod / (2 * H * x_total_initial))
        epsilon = D / (
            2 * np.sqrt(2 * H * self._base_angular_frequency * u_prod * x_total_initial)
        )

        p_peak_calc = delta_z_grid * self._initial_active_power / x_total_initial

        return x_total_initial, epsilon, wn, p_peak_calc

    def _calculate_delta_p_for_damping(
        self,
        D: float,
        H: float,
        Xeff: float,
        time_array: np.ndarray,
        event_time: float,
        epsilon_initial_check: float,
    ) -> tuple[np.ndarray, float, float, np.ndarray, np.ndarray]:
        """
        Selects the delta_p calculation method based on damping.
        """
        if epsilon_initial_check >= 1:
            delta_p, p_peak, epsilon = self._get_overdamped_delta_p(
                D, H, Xeff, time_array, event_time
            )
            return delta_p, p_peak, epsilon, None, None
        else:
            return self._get_underdamped_delta_p(D, H, Xeff, time_array, event_time)

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the base delta_p waveform for an overdamped system.
        """
        x_total, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)

        alpha = D / (2 * H)
        betha = self._base_angular_frequency / (2 * H * x_total)

        sqrt_term = alpha**2 - 4 * betha
        # Safeguard against sqrt of a tiny negative number due to float precision
        if sqrt_term < 0:
            sqrt_term = 0

        p1 = (alpha - np.sqrt(sqrt_term)) / 2
        p2 = (alpha + np.sqrt(sqrt_term)) / 2

        # Safeguard against division by zero in the critically damped case (p1 = p2)
        denominator = p2 - p1
        if math.isclose(denominator, 0):
            # If critically damped, the standard formula is invalid.
            # We return a zero-array to prevent a crash. A full implementation
            # would require the specific formula for critical damping.
            return np.zeros_like(time_array), p_peak, epsilon

        A = (2 * H * (-p1) + D) / denominator / (2 * H)
        B = (2 * H * (-p2) + D) / denominator / (2 * H)

        term1 = A * np.exp(-p1 * time_array)
        term2 = B * np.exp(-p2 * time_array)

        delta_p_base = p_peak * (term1 + term2) * -1

        return delta_p_base, p_peak, epsilon

    def _get_overdamped_delta_p(
        self,
        D: float,
        H: float,
        Xeff: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates delta_p for an overdamped system.
        """
        delta_p_base, p_peak, epsilon = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p = np.where(time_array < event_time, 0, delta_p_base)
        return delta_p, p_peak, epsilon

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float, np.ndarray, np.ndarray]:
        """
        Calculates the base delta_p waveform for an underdamped system.
        """
        _, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)

        # Safeguard against numerical errors if epsilon is >= 1
        if epsilon >= 1:
            # This case should be handled by the overdamped path, but as a safeguard
            # to prevent sqrt of a negative number, we return zeros.
            zeros = np.zeros_like(time_array)
            return zeros, p_peak, epsilon, zeros, zeros

        wd = wn * np.sqrt(1 - epsilon**2)

        exp_term = np.exp(-epsilon * wn * time_array)
        cos_term = np.cos(wd * time_array)
        sin_term = np.sin(wd * time_array)

        # Safeguard against division by zero if wd is close to zero (critically damped)
        if math.isclose(wd, 0):
            term2 = np.zeros_like(time_array)  # The sine term becomes zero
        else:
            term2 = ((D / (2 * H) - epsilon * wn) / wd) * sin_term

        delta_p_base = p_peak * (exp_term * (cos_term + term2)) * -1

        amplitude_factor = (
            np.sqrt(1 + ((D - 2 * H * epsilon * wn) / (2 * H * wd)) ** 2)
            if not math.isclose(wd, 0)
            else 1
        )
        envelope = np.abs(amplitude_factor * p_peak * exp_term)

        delta_p_up_envelope = envelope
        delta_p_down_envelope = -envelope

        return delta_p_base, p_peak, epsilon, delta_p_up_envelope, delta_p_down_envelope

    def _get_underdamped_delta_p(
        self,
        D: float,
        H: float,
        Xeff: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> tuple[np.ndarray, float, float, np.ndarray, np.ndarray]:
        """
        Calculates delta_p and its envelopes for an underdamped system.
        """
        delta_p_base, p_peak, epsilon, delta_p_up, delta_p_down = (
            self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        )

        delta_p = np.where(time_array < event_time, 0, delta_p_base)
        delta_p_up_final = np.where(time_array < event_time, 0, delta_p_up)
        delta_p_down_final = np.where(time_array < event_time, 0, delta_p_down)

        return delta_p, p_peak, epsilon, delta_p_up_final, delta_p_down_final

    def _get_tunnel(self, p_peak: float) -> float:
        """
        Calculates the tolerance "tunnel" value.
        """
        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * np.abs(p_peak),
        )
