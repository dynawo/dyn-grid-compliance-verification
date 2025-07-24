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


class RoCoF(GFMCalculator):
    """
    Class to calculate the GFM rate of change of frequency response.
    This class handles all core calculations for delta_p and active power
    envelopes, differentiating between overdamped and underdamped system
    responses.
    """

    def __init__(
        self,
        gfm_params: GFMParameters,
    ) -> None:
        super().__init__(gfm_params=gfm_params)
        self._change_frequency = gfm_params.get_change_frequency()
        self._change_frequency_duration = gfm_params.get_change_frequency_duration()
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()
        self._pll_time_constant = gfm_params.get_pll_time_constant()
        self._t_expo_decrease = gfm_params.get_t_expo_decrease()

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the change in power (delta_p) and active power envelopes (PCC,
        upper, and lower) based on damping characteristics for a phase jump event.

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
            The time (in seconds) at which the phase jump event occurs.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - magnitude: Name of the calculated magnitude.
            - p_pcc_final: The final calculated active power at the point of common
              coupling.
            - p_up_final: The final upper active power envelope.
            - p_down_final: The final lower active power envelope.
        """
        # Log the input parameters for debugging.
        dycov_logging.get_logger("RoCoF").debug(f"Input Params D={D} H={H} Xeff {Xeff}")
        dycov_logging.get_logger("RoCoF").debug(
            f"Input Params Δfrequency={self._change_frequency} "
            f"SCR={self._scr} "
            f"P0={self._initial_active_power} "
            f"PMin={self._min_active_power} "
            f"PMax={self._max_active_power}"
        )

        (
            delta_p_array,
            delta_p_min,
            delta_p_max,
            p_peak_array,
            epsilon_array,
        ) = self._get_delta_p(
            D=D,
            H=H,
            Xeff=Xeff,
            time_array=time_array,
            event_time=event_time,
        )

        p_pcc, p_up, p_down = self._get_envelopes(
            delta_p_array=delta_p_array,
            delta_p_min=delta_p_min,
            delta_p_max=delta_p_max,
            p_peak_array=p_peak_array,
            epsilon_array=epsilon_array,
            time_array=time_array,
            event_time=event_time,
            D=D,
            H=H,
        )
        return "P", p_pcc, p_up, p_down

    def _get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[list[np.ndarray], np.ndarray, np.ndarray, list[float], list[float]]:
        """
        Calculates the change in active power (delta_p) and related parameters based
        on damping characteristics, considering variations for nominal, minimum, and
        maximum parameters.

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
            The time (in seconds) at which the phase jump event occurs.

        Returns
        -------
        tuple[list[np.ndarray], np.ndarray, np.ndarray, list[float], list[float]]
            A tuple containing:
            - delta_p_array: List of delta_p arrays for original, min, and max parameter
              variations.
            - delta_p_min: delta_p array specifically calculated for the minimum
              parameter case.
            - delta_p_max: delta_p array specifically calculated for the maximum
              parameter case.
            - p_peak_array: List of p_peak values for original, min, and max parameter
              variations.
            - epsilon_array: List of epsilon values for original, min, and max parameter
              variations.
        """
        x_gr = 1 / self._scr
        x_total_initial = Xeff + x_gr
        t_pll = self._pll_time_constant

        d_array = np.array([D, D * self._min_ratio, D * self._max_ratio])
        h_array = np.array([H, H / self._min_ratio, H / self._max_ratio])
        t_pll_array = np.array(
            [
                t_pll,
                t_pll / self._min_ratio,
                t_pll / self._max_ratio,
            ]
        )

        epsilon_initial_check = self._calculate_epsilon_initial_check(
            d_array, h_array, x_total_initial
        )
        dycov_logging.get_logger("RoCoF").debug(f"Epsilon={epsilon_initial_check}")

        delta_p_array: list[np.ndarray] = []
        p_peak_array: list[float] = []
        epsilon_array: list[float] = []

        for i in range(len(d_array)):
            delta_p, p_peak, epsilon = self._calculate_delta_p_for_damping(
                d_array[i],
                h_array[i],
                Xeff,
                t_pll_array[i],
                time_array,
                event_time,
                epsilon_initial_check[i],
            )
            delta_p_array.append(delta_p)
            p_peak_array.append(p_peak)
            epsilon_array.append(epsilon)

        if epsilon_initial_check[self._ORIGINAL_PARAMS_IDX] > self._EPSILON_THRESHOLD:
            delta_p_min_array: list[np.ndarray] = []
            delta_p_max_array: list[np.ndarray] = []
            for i in range(len(d_array)):
                delta_p_min_array.append(
                    self._calculate_overdamped_envelope(
                        delta_p_array[i], p_peak_array[i], time_array, event_time, "min"
                    )
                )
                delta_p_max_array.append(
                    self._calculate_overdamped_envelope(
                        delta_p_array[i], p_peak_array[i], time_array, event_time, "max"
                    )
                )

            stacked = np.vstack((delta_p_min_array))
            delta_p_min = np.nanmin(stacked, axis=0)
            stacked = np.vstack((delta_p_max_array))
            delta_p_max = np.nanmax(stacked, axis=0)
        else:
            copouding_value = np.exp(-time_array / self._t_expo_decrease)
            delta_p_array[self._MINIMUM_PARAMS_IDX] = delta_p_array[
                self._MINIMUM_PARAMS_IDX
            ] * copouding_value + delta_p_array[self._ORIGINAL_PARAMS_IDX] * (1 - copouding_value)
            delta_p_array[self._MAXIMUM_PARAMS_IDX] = delta_p_array[
                self._MAXIMUM_PARAMS_IDX
            ] * copouding_value + delta_p_array[self._ORIGINAL_PARAMS_IDX] * (1 - copouding_value)

            # Optimization: Calculate the base waveform once to avoid redundant computations
            base_delta_p, _, _ = self._get_underdamped_delta_p_base(D, H, Xeff, t_pll, time_array)

            delta_p_min = self._get_underdamped_delta_p_min(
                base_delta_p, D, H, t_pll, time_array, event_time
            )
            delta_p_max = self._get_underdamped_delta_p_max(
                base_delta_p, D, H, t_pll, time_array, event_time
            )

        return (
            delta_p_array,
            delta_p_min,
            delta_p_max,
            p_peak_array,
            epsilon_array,
        )

    def _get_envelopes(
        self,
        delta_p_array: list[np.ndarray],
        delta_p_min: np.ndarray,
        delta_p_max: np.ndarray,
        p_peak_array: list[float],
        epsilon_array: list[float],
        time_array: np.ndarray,
        event_time: float,
        D: float,
        H: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates and limits the final active power envelopes (PCC power, upper
        envelope, lower envelope).

        Parameters
        ----------
        delta_p_array : list[np.ndarray]
            List of delta_p arrays for original, min, and max parameters.
        delta_p_min : np.ndarray
            delta_p array calculated with minimum parameters.
        delta_p_max : np.ndarray
            delta_p array calculated with maximum parameters.
        p_peak_array : list[float]
            List of p_peak values for original, min, and max parameters.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.
        D : float
            Damping factor.
        H : float
            Inertia constant.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - p_pcc_final: The final calculated active power at the point of common
              coupling.
            - p_up_final: The final upper active power envelope.
            - p_down_final: The final lower active power envelope.
        """
        delta_p = delta_p_array[self._ORIGINAL_PARAMS_IDX]
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]
        sign = self._change_frequency / np.abs(self._change_frequency)

        tunnel_time_dep = self._get_time_tunnel(
            p_peak=p_peak, time_array=time_array, event_time=event_time
        )

        p_pcc = self._initial_active_power + delta_p * -(sign)

        if epsilon_array[0] < self._EPSILON_THRESHOLD:
            list_of_arrays: list[np.ndarray] = [
                delta_p_array[self._MINIMUM_PARAMS_IDX],
                delta_p_array[self._MAXIMUM_PARAMS_IDX],
                delta_p_min,
                delta_p_max,
            ]

            pdown_no_p0, pup_no_p0 = self._calculate_unlimited_power_envelopes(
                list_of_arrays, tunnel_time_dep
            )

            expected_delta_p = np.abs(
                -(2 * H + D * self._pll_time_constant) * self._change_frequency
            )
            pdown_limited, pup_limited = self._limit_power_envelopes(
                pdown_no_p0,
                pup_no_p0,
                self._get_tunnel(expected_delta_p),
                self._initial_active_power,
                self._max_active_power,
                self._min_active_power,
                sign,
            )
        else:
            pdown_limited = delta_p_min
            pup_limited = delta_p_max

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
        Calculates common parameters required for delta_p calculations,
        such as total initial reactance (x_total_initial), damping ratio (epsilon),
        natural frequency (wn), and peak power (p_peak_calc).

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.

        Returns
        -------
        tuple[float, float, float, float]
            A tuple containing:
            - x_total_initial: Total initial reactance.
            - epsilon: Damping ratio.
            - wn: Natural frequency.
            - p_peak_calc: Calculated peak power.
        """
        x_gr = 1 / self._scr
        x_total_initial = Xeff + x_gr
        u_prod = self._initial_voltage * self._grid_voltage

        epsilon = (
            D / 2 * np.sqrt(x_total_initial / (2 * H * self._base_angular_frequency * u_prod))
        )
        wn = np.sqrt(self._base_angular_frequency * u_prod / (2 * H * x_total_initial))

        delta_theta_rad = np.abs(self._change_frequency * np.pi / 180)
        p_peak_calc = delta_theta_rad * u_prod / x_total_initial

        return x_total_initial, epsilon, wn, p_peak_calc

    def _calculate_delta_p_for_damping(
        self,
        D: float,
        H: float,
        Xeff: float,
        t_pll: float,
        time_array: np.ndarray,
        event_time: float,
        epsilon_initial_check: float,
    ) -> tuple[np.ndarray, float, float]:
        """
        Dispatches the calculation of delta_p, p_peak, and epsilon to the
        appropriate method based on whether the system is initially determined to be
        overdamped or underdamped.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        t_pll : float
            PLL time constant.
        time_array : np.ndarray
            Array of time points for simulation.
        event_time : float
            The time (in seconds) at which the phase jump event occurs.
        epsilon_initial_check : float
            Initial check value for epsilon to determine damping type.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing:
            - delta_p: The delta_p array for the system.
            - p_peak: The peak power.
            - epsilon: The damping ratio.
        """
        if epsilon_initial_check > self._EPSILON_THRESHOLD:
            return self._get_overdamped_delta_p(D, H, Xeff, t_pll, time_array, event_time)
        else:
            return self._get_underdamped_delta_p(D, H, Xeff, t_pll, time_array, event_time)

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, t_pll: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the fundamental delta_p waveform and related parameters for
        an overdamped system response, without applying event time conditions or
        margins. This represents the raw dynamic behavior.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        t_pll : float
            PLL time constant.
        time_array : np.ndarray
            Array of time points for simulation.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing:
            - delta_p1: The base delta_p waveform.
            - p_peak: The peak power.
            - xi: The damping ratio.
        """
        x_total_initial, _, wn, p_peak = self._calculate_common_params(D, H, Xeff)
        u_prod = self._initial_voltage * self._grid_voltage
        xi = wn * D * x_total_initial / (2 * self._base_angular_frequency * u_prod)

        alpha = 2 * H * t_pll * self._change_frequency
        beta = (2 * H + D * t_pll) / (2 * H * t_pll)

        # Coefficients for the analytical solution
        A_coeff = alpha * beta
        common_denom = 1 - 2 * xi * wn * t_pll + wn**2 * t_pll**2
        B_coeff = (alpha * (2 * t_pll * beta * wn * xi - t_pll * wn**2 - beta)) / common_denom
        C_coeff = (
            alpha
            * (
                4 * t_pll * beta * wn**2 * xi**2
                - t_pll * beta * wn**2
                - 2 * t_pll * wn**3 * xi
                - 2 * beta * wn * xi
                + wn**2
            )
        ) / common_denom
        D_coeff = (-1 * (t_pll**2 * alpha * wn**2 * (t_pll * beta - 1))) / common_denom

        alpha1 = wn * (xi + np.sqrt(xi**2 - 1))
        alpha2 = wn * (xi - np.sqrt(xi**2 - 1))

        term1 = np.exp(-alpha1 * time_array)
        term2 = np.exp(-alpha2 * time_array)
        term3 = np.exp(-time_array / t_pll)

        delta_p1 = (
            A_coeff
            + (B_coeff * alpha1 - C_coeff) * term1 / (alpha1 - alpha2)
            - (B_coeff * alpha2 - C_coeff) * term2 / (alpha1 - alpha2)
            + D_coeff * term3 / t_pll
        )
        return delta_p1, p_peak, xi

    def _get_overdamped_delta_p(
        self,
        D: float,
        H: float,
        Xeff: float,
        t_pll: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates delta_p, p_peak, and epsilon for an overdamped system response.
        This optimized version avoids redundant calculations by computing the base
        waveform once and applying it at the start and end of the event.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        t_pll : float
            PLL time constant.
        time_array : np.ndarray
            Array of time points for simulation.
        event_time : float
            The time (in seconds) at which the phase jump event occurs.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing:
            - delta_p: The delta_p array for the overdamped system.
            - p_peak: The peak power.
            - epsilon: The damping ratio.
        """
        # Calculate the base waveform shifted to the event start time
        time_shifted_start = time_array - event_time
        response_start, _, epsilon = self._get_overdamped_delta_p_base(
            D, H, Xeff, t_pll, time_shifted_start
        )

        # Calculate the base waveform shifted to the event end time
        event_end_time = event_time + self._change_frequency_duration
        time_shifted_end = time_array - event_end_time
        response_end, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, t_pll, time_shifted_end)

        # Apply waveforms only after their respective event times
        delta_p_start = np.where(time_array >= event_time, response_start, 0)
        delta_p_end = np.where(time_array >= event_end_time, response_end, 0)

        # The final delta_p is the superposition of the two responses
        delta_p = (delta_p_start - delta_p_end) * -1

        p_peak = delta_p[-1]
        return delta_p, p_peak, epsilon

    def _add_margin(
        self, initial_margin: float, init_time: float, final_time: float, time_array: np.ndarray
    ) -> np.ndarray:
        """
        Adds a decaying margin to a signal over a specified time interval.

        Parameters
        ----------
        initial_margin : float
            The initial value of the margin.
        init_time : float
            The start time for applying the margin.
        final_time : float
            The end time for applying the margin.
        time_array : np.ndarray
            Array of time points.

        Returns
        -------
        np.ndarray
            The calculated margin array.
        """
        decay_rate = 0.36
        mask = (final_time >= time_array) & (time_array >= init_time)
        margin = (
            np.where(time_array < init_time, 0, np.exp(-(time_array - init_time) * 1 / decay_rate))
            * mask
            * initial_margin
        )
        return margin

    def _get_value_at_time(
        self, selected_time: float, signal: np.ndarray, time_array: np.ndarray
    ) -> float:
        """
        Retrieves the value of a signal at a specific time.

        Parameters
        ----------
        selected_time : float
            The time at which to retrieve the signal value.
        signal : np.ndarray
            The signal array.
        time_array : np.ndarray
            Array of time points corresponding to the signal.

        Returns
        -------
        float
            The signal value at the selected time.
        """
        index = np.argmin(np.abs(time_array - (selected_time - 0.01)))
        return signal[index]

    def _calculate_overdamped_envelope(
        self,
        signal: np.ndarray,
        p_peak: float,
        time_array: np.ndarray,
        event_time: float,
        envelope_type: str,
    ) -> np.ndarray:
        """
        Calculates the minimum or maximum delta_p envelope for an overdamped system.
        This unified function replaces the duplicated logic from the original
        _get_overdamped_delta_p_min and _get_overdamped_delta_p_max methods by
        using an 'envelope_type' parameter to control the logic.

        Parameters
        ----------
        signal : np.ndarray
            The base signal array.
        p_peak : float
            Peak power value.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.
        envelope_type : str
            Type of envelope to calculate ("min" or "max").

        Returns
        -------
        np.ndarray
            The calculated envelope array.
        """
        if envelope_type not in ["min", "max"]:
            raise ValueError("envelope_type must be 'min' or 'max'")

        sign_multiplier = 1.0 if envelope_type == "max" else -1.0
        tunnel = max(0.02, 0.05 * p_peak)
        event_end_time = event_time + self._change_frequency_duration

        apply_margin_during_event = (self._change_frequency > 0 and envelope_type == "min") or (
            self._change_frequency <= 0 and envelope_type == "max"
        )

        if apply_margin_during_event:
            margin_start, margin_end = event_time, event_end_time
            signal_start, signal_end = event_end_time, time_array[-1]
        else:
            margin_start, margin_end = event_end_time, time_array[-1]
            signal_start, signal_end = event_time, event_end_time

        margin = self._add_margin(self._margin_high, margin_start, margin_end, time_array)

        ref_value_time = margin_end if margin_end <= time_array[-1] else margin_start
        value_at_ref_time = self._get_value_at_time(
            ref_value_time, signal + self._initial_active_power, time_array
        )

        envelope = np.full_like(time_array, self._initial_active_power)

        mask_signal = (time_array >= signal_start) & (time_array < signal_end)
        envelope = np.where(
            mask_signal, signal + self._initial_active_power + (sign_multiplier * tunnel), envelope
        )

        mask_margin = (time_array >= margin_start) & (time_array < margin_end)
        envelope = np.where(
            mask_margin,
            value_at_ref_time + (sign_multiplier * margin) + (sign_multiplier * tunnel),
            envelope,
        )

        if margin_end >= time_array[-1]:
            envelope[-1] = (
                value_at_ref_time + (sign_multiplier * margin[-1]) + (sign_multiplier * tunnel)
            )

        delay_mask = (
            (time_array >= signal_start)
            if apply_margin_during_event
            else (time_array < event_end_time)
        )
        envelope = np.where(
            delay_mask, self._apply_delay(0.01, envelope[0], time_array, envelope), envelope
        )

        limit_value = (
            (self._max_active_power * 0.95)
            if envelope_type == "min"
            else (self._min_active_power * 0.95)
        )
        limit_cond = (
            (envelope > limit_value) if envelope_type == "min" else (envelope < limit_value)
        )
        condition = (time_array >= event_time) & limit_cond
        envelope = np.where(condition, limit_value, envelope)

        return self._cut_signal(self._min_active_power, envelope, self._max_active_power)

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, t_pll: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the fundamental delta_p waveform and related parameters for
        an underdamped system response, without applying event time conditions or
        margins. This represents the raw dynamic behavior including oscillations.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        t_pll : float
            PLL time constant.
        time_array : np.ndarray
            Array of time points for simulation.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing:
            - delta_p1: The base delta_p waveform.
            - p_peak: The peak power.
            - epsilon: The damping ratio.
        """
        _, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)
        wd = wn * np.sqrt(1 - epsilon**2)

        alpha = 2 * H * t_pll * np.abs(self._change_frequency)
        beta = (2 * H + D * t_pll) / (2 * H * t_pll)

        A_coeff = alpha * beta
        common_denom = 1 - 2 * epsilon * wn * t_pll + wn**2 * t_pll**2
        B_coeff = -(t_pll**2 * alpha * wn**2 * (t_pll * beta - 1)) / common_denom
        C_coeff = (alpha * (2 * t_pll * beta * epsilon * wn - t_pll * wn**2 - beta)) / common_denom
        D_coeff = (
            alpha
            * (
                4 * t_pll * beta * wn**2 * epsilon**2
                - t_pll * beta * wn**2
                - 2 * t_pll * wn**3 * epsilon
                - 2 * beta * wn * epsilon
                + wn**2
            )
        ) / common_denom

        term2 = np.exp(-time_array / t_pll)
        term3 = np.exp(-epsilon * wn * time_array) * np.cos(wd * time_array)
        term4 = np.exp(-epsilon * wn * time_array) * np.sin(wd * time_array)

        delta_p1 = (
            A_coeff
            + B_coeff / t_pll * term2
            + C_coeff * term3
            + C_coeff * (D_coeff / C_coeff - epsilon * wn) / wd * term4
        )
        return delta_p1, p_peak, epsilon

    def _get_underdamped_delta_p(
        self,
        D: float,
        H: float,
        Xeff: float,
        t_pll: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates delta_p, p_peak, and epsilon for an underdamped system response,
        ensuring that the delta_p values are zero before the specified event time.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        t_pll : float
            PLL time constant.
        time_array : np.ndarray
            Array of time points for simulation.
        event_time : float
            The time (in seconds) at which the phase jump event occurs.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing:
            - delta_p: The delta_p array for the underdamped system, with pre-event
              values zeroed.
            - p_peak: The peak power.
            - epsilon: The damping ratio.
        """
        delta_p1, p_peak, epsilon = self._get_underdamped_delta_p_base(
            D, H, Xeff, t_pll, time_array
        )
        delta_p = np.where(time_array < event_time, 0, delta_p1)
        return delta_p, p_peak, epsilon

    def _get_underdamped_delta_p_min(
        self,
        base_delta_p: np.ndarray,
        D: float,
        H: float,
        t_pll: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> np.ndarray:
        """
        Calculates the minimum delta_p for an underdamped system, by applying
        a lower margin and an exponential decay, then setting pre-event values to
        zero. This represents the lower bound of the oscillating response.

        Parameters
        ----------
        base_delta_p : np.ndarray
            The base delta_p waveform.
        D : float
            Damping factor.
        H : float
            Inertia constant.
        t_pll : float
            PLL time constant.
        time_array : np.ndarray
            Array of time points for simulation.
        event_time : float
            The time (in seconds) at which the phase jump event occurs.

        Returns
        -------
        np.ndarray
            The minimum delta_p array.
        """
        expected_delta_p = np.abs(-(2 * H + D * t_pll) * self._change_frequency)
        delta_p1 = base_delta_p
        delta_p1_margined = (1 + self._margin_low) * delta_p1

        delta_p1_diff = np.diff(delta_p1_margined)
        index_decrease = np.where(delta_p1_diff < 0)[0][0]

        min_time = np.min(time_array[index_decrease + 1 :])
        max_value = np.max(delta_p1[index_decrease + 1 :])

        tunnel = self._get_tunnel(expected_delta_p)
        delta_p2 = (
            expected_delta_p
            - tunnel
            + (max_value - expected_delta_p + tunnel)
            * np.exp(-(time_array - min_time) / self._t_expo_decrease)
        )

        delta_p = delta_p1_margined
        delta_p[index_decrease + 1 :] = delta_p2[index_decrease + 1 :]

        delta_p = np.where(time_array < event_time, 0, delta_p)
        return delta_p

    def _get_underdamped_delta_p_max(
        self,
        base_delta_p: np.ndarray,
        D: float,
        H: float,
        t_pll: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> np.ndarray:
        """
        Calculates the maximum delta_p for an underdamped system, by applying
        an upper margin and an exponential decay, then setting pre-event values to
        zero. This represents the upper bound of the oscillating response.

        Parameters
        ----------
        base_delta_p : np.ndarray
            The base delta_p waveform.
        D : float
            Damping factor.
        H : float
            Inertia constant.
        t_pll : float
            PLL time constant.
        time_array : np.ndarray
            Array of time points for simulation.
        event_time : float
            The time (in seconds) at which the phase jump event occurs.

        Returns
        -------
        np.ndarray
            The maximum delta_p array.
        """
        expected_delta_p = np.abs(-(2 * H + D * t_pll) * self._change_frequency)
        delta_p1 = base_delta_p
        delta_p1_margined = (1 + self._margin_high) * delta_p1

        delta_p1_diff = np.diff(delta_p1_margined)
        index_decrease = np.where(delta_p1_diff < 0)[0][0]
        delta_p1_diff[:index_decrease] = 0
        index_increase = np.where(delta_p1_diff > 0)[0][0]

        min_time = np.min(time_array[index_increase + 1 :])
        min_value = np.min(delta_p1[index_increase + 1 :])

        delta_p2 = expected_delta_p + (min_value - expected_delta_p) * np.exp(
            -(time_array - min_time) / self._t_expo_decrease
        )

        delta_p = delta_p1_margined
        delta_p[index_increase + 1 :] = delta_p2[index_increase + 1 :]

        delta_p = np.where(time_array < event_time, 0, delta_p)
        return delta_p

    def _get_tunnel(self, expected_delta_p: float) -> float:
        """
        Calculates a constant "tunnel" value.

        Parameters
        ----------
        expected_delta_p : float
            The expected change in active power.

        Returns
        -------
        float
            The calculated tunnel value.
        """
        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * expected_delta_p,
        )
