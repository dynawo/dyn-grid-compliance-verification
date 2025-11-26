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

from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.parameters import GFMParameters
from dycov.logging.logging import dycov_logging
from dycov.gfm import constants


class RoCoF(GFMCalculator):
    """
    Class to calculate the GFM response to a RoCoF (Rate of Change of
    Frequency) event.

    This class handles all core calculations for active power envelopes,
    differentiating between overdamped and underdamped system responses
    to match legacy analytical validation scripts.
    """

    def __init__(
        self,
        gfm_params: GFMParameters,
    ) -> None:
        """
        Initializes the RoCoF calculator with GFM parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            An object containing all necessary parameters for GFM calculations.
        """
        super().__init__(gfm_params=gfm_params)
        self._rocof_value = gfm_params.get_change_frequency()
        self._rocof_duration = gfm_params.get_change_frequency_duration()
        self._t_pll = gfm_params.get_pll_time_constant()
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()

        # FIX: Calculate MoisTunnel limits based on Pmin/Pmax to match original script behavior.
        # The default getter might return +0.95 which is incorrect for Pmin thresholds.
        self._pmax_mois_tunnel = self._max_active_power * 0.95
        self._pmin_mois_tunnel = self._min_active_power * 0.95

        # Internal state to track if the nominal case is underdamped
        self._is_underdamped = False
        # Variable to store the current epsilon during iteration
        self._current_epsilon = 0.0

    def get_plot_parameter_names(self) -> list[str]:
        """Returns the list of parameter names relevant for RoCoF plots."""
        return [
            "P0",
            "Q0",
            "Frequency0",
            "RoCoF",
            "RoCoFDuration",
            "SCR",
            "Xeff",
            "D",
            "H",
            "Epsilon",
        ]

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the change in power (delta_p) and its envelopes (PCC,
        upper, and lower) based on damping characteristics for a RoCoF event.
        """
        dycov_logging.get_logger("RoCoF").debug(f"Input Params D={D} H={H} Xeff {Xeff}")

        # 1. Calculate Delta P for Nominal, Min, and Max variations
        (delta_p_array, p_peak_array, t_response_array) = self._get_delta_p(
            D=D, H=H, Xeff=Xeff, time_array=time_array, event_time=event_time
        )

        # 2. Calculate Envelopes applying all logic rules (saturation, latches, etc.)
        p_pcc, p_up, p_down = self._get_envelopes(
            delta_p_array=delta_p_array,
            p_peak_array=p_peak_array,
            t_response_array=t_response_array,
            time_array=time_array,
            event_time=event_time,
        )

        # 3. Apply a final delay for EMT-type simulations if required
        if self._is_emt_flag:
            upper_envelope = self._apply_delay(
                constants.EMT_FINAL_DELAY_S, p_up[0], time_array, p_up
            )
            lower_envelope = self._apply_delay(
                constants.EMT_FINAL_DELAY_S, p_down[0], time_array, p_down
            )
            pcc_signal = self._apply_delay(
                constants.EMT_FINAL_DELAY_S, p_pcc[0], time_array, p_pcc
            )
        else:
            upper_envelope = p_up
            lower_envelope = p_down
            pcc_signal = p_pcc

        magnitude_name = "Ip"
        return magnitude_name, pcc_signal, upper_envelope, lower_envelope

    def _get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[list, list, list]:
        """
        Calculates delta_p for nominal, min, and max parameter variations.
        Also determines if the nominal case is underdamped.
        """
        x_total = Xeff + 1 / self._scr
        d_array = np.array([D, D * self._min_ratio, D * self._max_ratio])
        h_array = np.array([H, H / self._min_ratio, H / self._max_ratio])

        delta_p_array = []
        p_peak_array = []
        t_response_array = []

        for i in range(len(d_array)):
            delta_p, p_peak, t_response = self._calculate_delta_p_for_damping(
                d_array[i], h_array[i], x_total, time_array, event_time
            )

            # Capture damping status for the NOMINAL case (index 0)
            if i == self._ORIGINAL_PARAMS_IDX:
                self._epsilon = self._current_epsilon
                self._is_underdamped = self._epsilon < self._EPSILON_THRESHOLD

            delta_p_array.append(delta_p)
            p_peak_array.append(p_peak)
            t_response_array.append(t_response)

        return delta_p_array, p_peak_array, t_response_array

    def _calculate_delta_p_for_damping(
        self, D: float, H: float, x_total: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Selects the calculation method (over/underdamped) and applies the
        superposition principle for the finite duration event.
        """
        u_prod = self._initial_voltage * self._grid_voltage
        wn = np.sqrt(self._base_angular_frequency * u_prod / (2 * H * x_total))
        epsilon = D / (4 * H * wn)

        # Store epsilon for the current iteration
        self._current_epsilon = epsilon

        calc_func = (
            self._get_overdamped_delta_p_base
            if epsilon >= self._EPSILON_THRESHOLD
            else self._get_underdamped_delta_p_base
        )

        # A finite duration RoCoF is modeled by superimposing two step responses.
        rocof_stop_time = event_time + self._rocof_duration

        # 1. Calculate the step-on response starting at event_time.
        time_event_start = time_array - event_time
        p1, p_peak, t_response = calc_func(D, H, x_total, time_event_start)
        p1 = np.where(time_array < event_time, 0, p1)

        # 2. Calculate the step-off response (negated) starting at rocof_stop_time.
        time_event_stop = time_array - rocof_stop_time
        p2, _, _ = calc_func(D, H, x_total, time_event_stop)
        p2 = np.where(time_array < rocof_stop_time, 0, p2)

        # 3. The final response is the difference between the two.
        delta_p = p1 - p2

        return delta_p, p_peak, t_response

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, x_total: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """Solves the system's differential equation for an overdamped step response."""
        u_prod = self._initial_voltage * self._grid_voltage
        wn = np.sqrt(self._base_angular_frequency * u_prod / (2 * H * x_total))
        epsilon = D / (4 * H * wn)

        alpha = 2 * H * self._t_pll * self._rocof_value
        beta = (2 * H + D * self._t_pll) / (2 * H * self._t_pll)

        common_denom = 1 - 2 * epsilon * wn * self._t_pll + wn**2 * self._t_pll**2

        D_coeff = -(self._t_pll**2 * alpha * wn**2 * (self._t_pll * beta - 1)) / common_denom
        A_coeff = alpha * beta
        B_coeff = (
            alpha
            * (2 * self._t_pll * beta * wn * epsilon - self._t_pll * wn**2 - beta)
            / common_denom
        )
        C_coeff = (
            alpha
            * (
                4 * self._t_pll * beta * wn**2 * epsilon**2
                - self._t_pll * beta * wn**2
                - 2 * self._t_pll * wn**3 * epsilon
                - 2 * beta * wn * epsilon
                + wn**2
            )
            / common_denom
        )

        alpha1 = wn * (epsilon + np.sqrt(epsilon**2 - 1))
        alpha2 = wn * (epsilon - np.sqrt(epsilon**2 - 1))

        t_rel = time_array[time_array >= 0]

        term1 = (B_coeff * alpha1 - C_coeff) * np.exp(-alpha1 * t_rel) / (alpha1 - alpha2)
        term2 = (B_coeff * alpha2 - C_coeff) * np.exp(-alpha2 * t_rel) / (alpha1 - alpha2)
        term3 = (D_coeff / self._t_pll) * np.exp(-t_rel / self._t_pll)

        delta_p_rel = A_coeff + term1 - term2 + term3

        delta_p = np.zeros_like(time_array)
        delta_p[time_array >= 0] = delta_p_rel

        p_peak = abs(-self._rocof_value * (2 * H + D * self._t_pll))
        t_response = 4 * max(1 / alpha1, 1 / alpha2, self._t_pll)

        # The original code calculates the negative DeltaP response
        return -delta_p, p_peak, t_response

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, x_total: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """Solves the system's differential equation for an underdamped step response."""
        u_prod = self._initial_voltage * self._grid_voltage
        wn = np.sqrt(self._base_angular_frequency * u_prod / (2 * H * x_total))
        epsilon = D / (4 * H * wn)
        wd = wn * np.sqrt(1 - epsilon**2)

        alpha = 2 * H * self._t_pll * self._rocof_value
        beta = (2 * H + D * self._t_pll) / (2 * H * self._t_pll)

        A_coeff = alpha * beta
        common_denom = 1 - 2 * epsilon * wn * self._t_pll + wn**2 * self._t_pll**2
        B_coeff = -(self._t_pll**2 * alpha * wn**2 * (self._t_pll * beta - 1)) / common_denom
        C_coeff = (
            alpha * (2 * self._t_pll * beta * epsilon * wn - self._t_pll * wn**2 - beta)
        ) / common_denom
        D_coeff = (
            alpha
            * (
                4 * self._t_pll * beta * wn**2 * epsilon**2
                - self._t_pll * beta * wn**2
                - 2 * self._t_pll * wn**3 * epsilon
                - 2 * beta * wn * epsilon
                + wn**2
            )
        ) / common_denom

        t_rel = time_array[time_array >= 0]

        term_pll = (B_coeff / self._t_pll) * np.exp(-t_rel / self._t_pll)
        term_cos = np.exp(-epsilon * wn * t_rel) * np.cos(wd * t_rel)
        term_sin = np.exp(-epsilon * wn * t_rel) * np.sin(wd * t_rel)

        delta_p_rel = (
            A_coeff
            + term_pll
            + C_coeff * term_cos
            + ((D_coeff - C_coeff * epsilon * wn) / wd) * term_sin
        )

        delta_p = np.zeros_like(time_array)
        delta_p[time_array >= 0] = delta_p_rel

        R_coeff = np.sqrt(C_coeff**2 + ((D_coeff - C_coeff * epsilon * wn) / wd) ** 2)
        p_peak = abs(A_coeff + B_coeff / self._t_pll + R_coeff)
        t_response = 4 / (epsilon * wn)

        # The original code calculates the negative DeltaP response
        return -delta_p, p_peak, t_response

    def _get_envelopes(
        self,
        delta_p_array: list[np.ndarray],
        p_peak_array: list[float],
        t_response_array: list[float],
        time_array: np.ndarray,
        event_time: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates and limits the final active power envelopes, applying all
        special logic rules for RoCoF events (Overdamped vs Underdamped).
        """
        # Nominal values
        delta_p_nominal = delta_p_array[self._ORIGINAL_PARAMS_IDX]
        p_pcc_nominal = self._initial_active_power + delta_p_nominal

        tunnel_val = self._get_tunnel(p_peak_array)
        sign = np.sign(self._rocof_value)
        rocof_stop_time = event_time + self._rocof_duration

        # --- Rule 1: Calculate initial unlimited envelopes ---
        dp_min_trace = np.minimum.reduce(delta_p_array)
        dp_max_trace = np.maximum.reduce(delta_p_array)

        if sign > 0:  # Positive RoCoF (Frequency Increases -> Power Decreases)
            p_up_unlimited = (
                self._initial_active_power + dp_max_trace * (1 - self._margin_high) + tunnel_val
            )
            p_down_unlimited = (
                self._initial_active_power + dp_min_trace * (1 + self._margin_low) - tunnel_val
            )
        else:  # Negative RoCoF (Frequency Decreases -> Power Increases)
            p_up_unlimited = (
                self._initial_active_power + dp_max_trace * (1 + self._margin_high) + tunnel_val
            )
            p_down_unlimited = (
                self._initial_active_power + dp_min_trace * (1 - self._margin_low) - tunnel_val
            )

        # --- Rule 2: Underdamped Specific "50% Hold" Rule ---
        if self._is_underdamped:
            hold_duration = constants.UNDERDAMPED_MAX_DELAY_S
            mask_hold = (time_array >= event_time) & (time_array <= event_time + hold_duration)
            p_50_percent = self._initial_active_power + (delta_p_nominal * 0.5)

            if sign < 0:  # DeltaP > 0 -> Envelope Up needs mod
                p_up_unlimited = np.where(mask_hold, p_50_percent, p_up_unlimited)
            else:  # DeltaP < 0 -> Envelope Down needs mod
                p_down_unlimited = np.where(mask_hold, p_50_percent, p_down_unlimited)

        # --- Rule 3: Saturation Limits ("MoisTunnel") ---
        # Before final clipping, we apply the "Pmax/min - Tunnel" rule.
        # This prevents envelopes from crossing the physical capability "tunnel".
        p_up_unlimited, p_down_unlimited = self._apply_saturation_limits(
            p_up_unlimited, p_down_unlimited, time_array, event_time
        )

        # --- Rule 4: Clamp to Steady State after Response Time ---
        # Note: P_PCC here follows the ramp (delta_p_nominal is time-varying)
        t_response = t_response_array[self._ORIGINAL_PARAMS_IDX]
        clamp_start_time = event_time + t_response

        if clamp_start_time < rocof_stop_time:
            mask_steady = (time_array >= clamp_start_time) & (time_array < rocof_stop_time)

            p_up_unlimited = np.where(mask_steady, p_pcc_nominal + tunnel_val, p_up_unlimited)
            p_down_unlimited = np.where(mask_steady, p_pcc_nominal - tunnel_val, p_down_unlimited)

        # --- Rule 5: Post-RoCoF Latching ---
        # Envelopes shouldn't bounce back after the event stops.
        indices_at_stop = np.where(time_array <= rocof_stop_time)[0]
        if len(indices_at_stop) > 0:
            idx_stop = indices_at_stop[-1]
            mask_post_recovery = time_array > rocof_stop_time

            if sign > 0:  # Power Dropped. Latch lower envelope.
                val_at_stop = p_down_unlimited[idx_stop]
                p_down_unlimited = np.where(
                    mask_post_recovery, np.maximum(p_down_unlimited, val_at_stop), p_down_unlimited
                )
            else:  # Power Rose. Latch upper envelope.
                val_at_stop = p_up_unlimited[idx_stop]
                p_up_unlimited = np.where(
                    mask_post_recovery, np.minimum(p_up_unlimited, val_at_stop), p_up_unlimited
                )

        # --- Rule 6: Final Absolute Clipping ---
        p_up_limited = self._cut_signal(
            self._min_active_power, p_up_unlimited, self._max_active_power
        )
        p_down_limited = self._cut_signal(
            self._min_active_power, p_down_unlimited, self._max_active_power
        )

        return p_pcc_nominal, p_up_limited, p_down_limited

    def _apply_saturation_limits(
        self, p_up: np.ndarray, p_down: np.ndarray, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Applies the 'MoisTunnel' saturation logic.
        Ensures upper envelope doesn't fall below Pmin_MoisTunnel and
        lower envelope doesn't rise above Pmax_MoisTunnel.
        """
        mask_active = time_array >= event_time

        # Lower envelope should not exceed the Maximum saturation threshold
        condition_down = mask_active & (p_down > self._pmax_mois_tunnel)
        p_down = np.where(condition_down, self._pmax_mois_tunnel, p_down)

        # Upper envelope should not fall below the Minimum saturation threshold
        condition_up = mask_active & (p_up < self._pmin_mois_tunnel)
        p_up = np.where(condition_up, self._pmin_mois_tunnel, p_up)

        return p_up, p_down

    def _get_tunnel(self, p_peak_array: list[float]) -> float:
        """
        Calculates the tolerance "tunnel" value.
        Tunnel = max(0.02, 0.05 * P_peak_deviation)
        """
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]
        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * p_peak,
        )
