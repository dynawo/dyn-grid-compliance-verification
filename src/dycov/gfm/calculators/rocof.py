#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

import numpy as np

from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.parameters import GFMParameters
from dycov.logging import dycov_logging

LOGGER = dycov_logging.get_logger("RoCoF")


class RoCoF(GFMCalculator):
    """Handles the GFM response to a Rate of Change of Frequency (RoCoF) event."""

    def __init__(self, gfm_params: GFMParameters) -> None:
        """
        Initializes the RoCoF calculator with GFM parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            The shared configuration parameters.
        """
        super().__init__(gfm_params=gfm_params)
        self._rocof_value = gfm_params.get_change_frequency()
        self._rocof_duration = gfm_params.get_change_frequency_duration()
        self._t_pll = gfm_params.get_pll_time_constant()
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()

    def get_plot_parameter_names(self) -> list[str]:
        """
        Retrieves parameters relevant for rendering RoCoF plots.

        Returns
        -------
        list[str]
            A list of parameter names to be displayed.
        """
        return ["P0", "Q0", "Frequency0", "RoCoF", "RoCoFDuration", "SCR", "Xeff", "D", "H"]

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the active power deviation and bounding envelopes for RoCoF.

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
            The timestamp of the event.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            The magnitude name ("P"), the main signal, the upper envelope and the lower
            envelope.

        Raises
        ------
        TypeError
            If the time is not a one-dimensional array of floats or signed integers.
        ValueError
            If the time vector has fewer than two points, or is not finite, strictly
            increasing and evenly spaced.
        """
        self._check_time_array(time_array)
        LOGGER.debug(f"Input Params D={D} H={H} Xeff {Xeff}")

        delta_p_array, p_peak_array, t_response_array = self._get_delta_p(
            D=D, H=H, Xeff=Xeff, time_array=time_array, event_time=event_time
        )
        p_pcc, p_up, p_down = self._get_envelopes(
            delta_p_array=delta_p_array,
            p_peak_array=p_peak_array,
            t_response_array=t_response_array,
            time_array=time_array,
            event_time=event_time,
        )

        if self._is_emt_flag:
            p_up = self._delay_by_emt(p_up, time_array)
            p_down = self._delay_by_emt(p_down, time_array)
            p_pcc = self._delay_by_emt(p_pcc, time_array)

        return "P", p_pcc, p_up, p_down

    def _get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[list, list, list]:
        """
        Computes the response of the nominal D and H and of their two variations.

        The variations change D and H in opposite directions: D times RatioMin with H over
        RatioMin, and D times RatioMax with H over RatioMax.

        Parameters
        ----------
        D : float
            The base damping constant.
        H : float
            The base inertia constant.
        Xeff : float
            The effective reactance.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp of the event.

        Returns
        -------
        tuple[list, list, list]
            Lists of delta_p arrays, peak powers, and response times.
        """
        x_total = Xeff + 1 / self._scr
        d_array = np.array([D, D * self._min_ratio, D * self._max_ratio])
        h_array = np.array([H, H / self._min_ratio, H / self._max_ratio])

        delta_p_array, p_peak_array, t_response_array, epsilon_vals = [], [], [], []
        for d_value, h_value in zip(d_array, h_array):
            wn = self._natural_frequency(h_value, x_total)
            epsilon = d_value / (4 * h_value * wn)
            epsilon_vals.append(epsilon)
            delta_p, p_peak, t_response = self._calculate_delta_p_for_damping(
                d_value, h_value, wn, epsilon, time_array, event_time
            )
            delta_p_array.append(delta_p)
            p_peak_array.append(p_peak)
            t_response_array.append(t_response)

        self._d_vals = d_array
        self._h_vals = h_array
        self._epsilon_vals = np.array(epsilon_vals)

        return delta_p_array, p_peak_array, t_response_array

    def _calculate_delta_p_for_damping(
        self,
        D: float,
        H: float,
        wn: float,
        epsilon: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the response to the frequency ramp, which starts at the event and stops
        RoCoFDuration later, as the response to its start minus that to its stop.

        Parameters
        ----------
        D : float
            The damping constant.
        H : float
            The inertia constant.
        wn : float
            The natural frequency.
        epsilon : float
            The damping ratio.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp of the event.

        Returns
        -------
        tuple[np.ndarray, float, float]
            The calculated delta_p array, peak power, and response time.
        """
        calc_func = (
            self._get_overdamped_delta_p_base
            if epsilon >= self._EPSILON_THRESHOLD
            else self._get_underdamped_delta_p_base
        )
        rocof_stop_time = event_time + self._rocof_duration

        p1, p_peak, t_response = calc_func(D, H, wn, epsilon, time_array - event_time)
        p1 = np.where(time_array < event_time, 0, p1)

        p2, _, _ = calc_func(D, H, wn, epsilon, time_array - rocof_stop_time)
        p2 = np.where(time_array < rocof_stop_time, 0, p2)

        return p1 - p2, p_peak, t_response

    def _get_shared_coefficients(
        self, D: float, H: float, wn: float, epsilon: float
    ) -> tuple[float, float, float, float, float]:
        """
        Computes the coefficients the overdamped and the underdamped responses share.

        Parameters
        ----------
        D : float
            The damping constant.
        H : float
            The inertia constant.
        wn : float
            The natural frequency.
        epsilon : float
            The damping ratio.

        Returns
        -------
        tuple[float, float, float, float, float]
            alpha, beta, the denominator of the PLL and swing coefficients, the coefficient
            of the PLL mode and the coefficient of the swing mode.
        """
        alpha = 2 * H * self._t_pll * self._rocof_value
        beta = (2 * H + D * self._t_pll) / (2 * H * self._t_pll)
        common_denom = 1 - 2 * epsilon * wn * self._t_pll + wn**2 * self._t_pll**2
        pll_coeff = -(self._t_pll**2 * alpha * wn**2 * (self._t_pll * beta - 1)) / common_denom
        swing_coeff = (
            alpha
            * (
                4 * self._t_pll * beta * wn**2 * epsilon**2
                - self._t_pll * beta * wn**2
                - 2 * self._t_pll * wn**3 * epsilon
                - 2 * beta * wn * epsilon
                + wn**2
            )
        ) / common_denom
        return alpha, beta, common_denom, pll_coeff, swing_coeff

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, wn: float, epsilon: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Resolves the overdamped power response equation for RoCoF.

        Parameters
        ----------
        D : float
            The damping constant.
        H : float
            The inertia constant.
        wn : float
            The natural frequency.
        epsilon : float
            The damping ratio.
        time_array : np.ndarray
            The time since the start of the ramp; the response is zero before it.

        Returns
        -------
        tuple[np.ndarray, float, float]
            The power response array, peak power, and response time.
        """
        alpha, beta, common_denom, pll_coeff, swing_coeff = self._get_shared_coefficients(
            D, H, wn, epsilon
        )
        A_coeff = alpha * beta
        B_coeff = (
            alpha * (2 * self._t_pll * beta * wn * epsilon - self._t_pll * wn**2 - beta)
        ) / common_denom

        alpha1 = wn * (epsilon + np.sqrt(epsilon**2 - 1))
        alpha2 = wn * (epsilon - np.sqrt(epsilon**2 - 1))
        t_rel = time_array[time_array >= 0]

        term1 = (B_coeff * alpha1 - swing_coeff) * np.exp(-alpha1 * t_rel) / (alpha1 - alpha2)
        term2 = (B_coeff * alpha2 - swing_coeff) * np.exp(-alpha2 * t_rel) / (alpha1 - alpha2)
        term3 = (pll_coeff / self._t_pll) * np.exp(-t_rel / self._t_pll)

        delta_p = np.zeros_like(time_array)
        delta_p[time_array >= 0] = A_coeff + term1 - term2 + term3
        p_peak = abs(-self._rocof_value * (2 * H + D * self._t_pll))
        t_response = 4 * max(1 / alpha1, 1 / alpha2, self._t_pll)

        return -delta_p, p_peak, t_response

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, wn: float, epsilon: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Resolves the underdamped oscillating power response for RoCoF.

        Parameters
        ----------
        D : float
            The damping constant.
        H : float
            The inertia constant.
        wn : float
            The natural frequency.
        epsilon : float
            The damping ratio.
        time_array : np.ndarray
            The time since the start of the ramp; the response is zero before it.

        Returns
        -------
        tuple[np.ndarray, float, float]
            The power response array, peak power, and response time.
        """
        wd = wn * np.sqrt(1 - epsilon**2)
        alpha, beta, common_denom, pll_coeff, swing_coeff = self._get_shared_coefficients(
            D, H, wn, epsilon
        )
        A_coeff = alpha * beta
        C_coeff = (
            alpha * (2 * self._t_pll * beta * epsilon * wn - self._t_pll * wn**2 - beta)
        ) / common_denom

        t_rel = time_array[time_array >= 0]

        term_pll = (pll_coeff / self._t_pll) * np.exp(-t_rel / self._t_pll)
        term_cos = np.exp(-epsilon * wn * t_rel) * np.cos(wd * t_rel)
        term_sin = np.exp(-epsilon * wn * t_rel) * np.sin(wd * t_rel)

        delta_p = np.zeros_like(time_array)
        delta_p[time_array >= 0] = (
            A_coeff
            + term_pll
            + C_coeff * term_cos
            + ((swing_coeff - C_coeff * epsilon * wn) / wd) * term_sin
        )

        R_coeff = np.sqrt(C_coeff**2 + ((swing_coeff - C_coeff * epsilon * wn) / wd) ** 2)
        p_peak = abs(A_coeff + pll_coeff / self._t_pll + R_coeff)
        t_response = 4 / (epsilon * wn)

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
        Constructs power envelopes and enforces hardware constraints and clamp logic.

        Parameters
        ----------
        delta_p_array : list[np.ndarray]
            A list of calculated delta_p trajectories.
        p_peak_array : list[float]
            A list of calculated peak powers.
        t_response_array : list[float]
            A list of theoretical response times.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp of the event.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            Main PCC trace, upper, and lower envelopes.
        """
        p_pcc = self._initial_active_power + delta_p_array[self._ORIGINAL_PARAMS_IDX]
        tunnel_val = self._get_tunnel(p_peak_array)
        sign = np.sign(self._rocof_value)

        dp_min_trace = np.minimum.reduce(delta_p_array)
        dp_max_trace = np.maximum.reduce(delta_p_array)

        upper_margin = (1 - self._margin_high) if sign > 0 else (1 + self._margin_high)
        lower_margin = (1 + self._margin_low) if sign > 0 else (1 - self._margin_low)
        p_up_unlimited = self._initial_active_power + dp_max_trace * upper_margin + tunnel_val
        p_down_unlimited = self._initial_active_power + dp_min_trace * lower_margin - tunnel_val

        clamp_start_time = event_time + t_response_array[self._ORIGINAL_PARAMS_IDX]
        rocof_stop_time = event_time + self._rocof_duration

        if clamp_start_time < rocof_stop_time:
            mask = (time_array >= clamp_start_time) & (time_array < rocof_stop_time)
            pcc_steady_value = np.interp(clamp_start_time, time_array, p_pcc)
            p_up_unlimited = np.where(mask, pcc_steady_value + tunnel_val, p_up_unlimited)
            p_down_unlimited = np.where(mask, pcc_steady_value - tunnel_val, p_down_unlimited)

        p_up_unlimited, p_down_unlimited = self._hold_after_ramp(
            p_up_unlimited, p_down_unlimited, sign, time_array, rocof_stop_time
        )

        p_down_unlimited = np.clip(p_down_unlimited, -np.inf, self._pmax_mois_tunnel)
        p_up_unlimited = np.clip(p_up_unlimited, self._pmin_mois_tunnel, np.inf)

        p_up_limited = np.clip(p_up_unlimited, self._min_active_power, self._max_active_power)
        p_down_limited = np.clip(p_down_unlimited, self._min_active_power, self._max_active_power)

        return p_pcc, p_up_limited, p_down_limited

    def _hold_after_ramp(
        self,
        p_up: np.ndarray,
        p_down: np.ndarray,
        sign: float,
        time_array: np.ndarray,
        rocof_stop_time: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Stops the envelope on the side the ramp pushed the power towards from going beyond the
        value it had when the ramp stopped.

        For a rising frequency, the lower envelope does not drop after the ramp below the value
        it had just before it stopped; otherwise, the upper envelope does not rise above it.

        Parameters
        ----------
        p_up : np.ndarray
            The upper envelope.
        p_down : np.ndarray
            The lower envelope.
        sign : float
            The sign of the RoCoF.
        time_array : np.ndarray
            The simulation time vector.
        rocof_stop_time : float
            The time the ramp stops.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            The upper and lower envelopes.
        """
        indices_before_recovery = np.where(time_array < rocof_stop_time)[0]
        if len(indices_before_recovery) == 0:
            return p_up, p_down

        idx_before_recovery = indices_before_recovery[-1]
        mask_post_recovery = time_array >= rocof_stop_time
        if sign > 0:
            clamp_val = p_down[idx_before_recovery]
            p_down = np.where(mask_post_recovery, np.maximum(p_down, clamp_val), p_down)
        else:
            clamp_val = p_up[idx_before_recovery]
            p_up = np.where(mask_post_recovery, np.minimum(p_up, clamp_val), p_up)
        return p_up, p_down

    def _get_tunnel(self, p_peak_array: list[float]) -> float:
        """
        Calculates the dynamic margin based on nominal limits and peak responses.

        Parameters
        ----------
        p_peak_array : list[float]
            A list of peak power measurements.

        Returns
        -------
        float
            The calculated tunnel margin in pu.
        """
        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * p_peak_array[self._ORIGINAL_PARAMS_IDX],
        )
