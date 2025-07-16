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
from dycov.logging.logging import dycov_logging


class RoCoF(GFMCalculator):
    """
    Class to calculate the GFM rate of change of frequency response.
    This class handles all core calculations for delta_p and active power
    envelopes, differentiating between overdamped and underdamped system
    responses.
    """

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
            f"Input Params Δfrequency={self._gfm_params.get_change_frequency()} "
            f"SCR={self._gfm_params.get_scr()} "
            f"P0={self._gfm_params.get_initial_active_power()} "
            f"PMin={self._gfm_params.get_min_active_power()} "
            f"PMax={self._gfm_params.get_max_active_power()}"
        )

        (
            delta_p_array,
            delta_p_min,
            delta_p_max,
            p_peak_array,
            _,
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
        x_gr = 1 / self._gfm_params.get_scr()
        x_total_initial = Xeff + x_gr
        t_pll = self._gfm_params.get_pll_time_constant()

        d_array = np.array(
            [D, D * self._gfm_params.get_min_ratio(), D * self._gfm_params.get_max_ratio()]
        )
        h_array = np.array(
            [H, H / self._gfm_params.get_min_ratio(), H / self._gfm_params.get_max_ratio()]
        )
        t_pll_array = np.array(
            [
                t_pll,
                t_pll / self._gfm_params.get_min_ratio(),
                t_pll / self._gfm_params.get_max_ratio(),
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

        copouding_value = np.exp(-time_array / self._gfm_params.get_t_expo_decrease())
        delta_p_array[self._MINIMUM_PARAMS_IDX] = delta_p_array[
            self._MINIMUM_PARAMS_IDX
        ] * copouding_value + delta_p_array[self._ORIGINAL_PARAMS_IDX] * (1 - copouding_value)
        delta_p_array[self._MAXIMUM_PARAMS_IDX] = delta_p_array[
            self._MAXIMUM_PARAMS_IDX
        ] * copouding_value + delta_p_array[self._ORIGINAL_PARAMS_IDX] * (1 - copouding_value)

        if epsilon_initial_check[self._ORIGINAL_PARAMS_IDX] > self._EPSILON_THRESHOLD:
            delta_p_min = self._get_overdamped_delta_p_min(
                D, H, Xeff, t_pll, time_array, event_time
            )
            delta_p_max = self._get_overdamped_delta_p_max(
                D, H, Xeff, t_pll, time_array, event_time
            )
        else:
            delta_p_min = self._get_underdamped_delta_p_min(
                D, H, Xeff, t_pll, time_array, event_time
            )
            delta_p_max = self._get_underdamped_delta_p_max(
                D, H, Xeff, t_pll, time_array, event_time
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
        time_array: np.ndarray,
        event_time: float,
        D: float,
        H: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates and limits the final active power envelopes (PCC power, upper
        envelope, lower envelope). This involves combining various delta_p
        calculations, applying a time-dependent tunnel effect, and enforcing
        operational limits.

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

        tunnel_time_dep = self._get_time_tunnel(
            p_peak=p_peak, time_array=time_array, event_time=event_time
        )

        p_pcc = self._gfm_params.get_initial_active_power() + delta_p * -(
            self._gfm_params.get_change_frequency()
            / np.abs(self._gfm_params.get_change_frequency())
        )

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
            -(2 * H + D * self._gfm_params.get_pll_time_constant())
            * self._gfm_params.get_change_frequency()
        )
        pdown_limited, pup_limited = self._limit_power_envelopes(
            pdown_no_p0, pup_no_p0, self._get_tunnel(expected_delta_p)
        )

        if self._gfm_params.is_emt():
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
        x_gr = 1 / self._gfm_params.get_scr()
        x_total_initial = Xeff + x_gr
        u_prod = self._gfm_params.get_initial_voltage() * self._gfm_params.get_grid_voltage()

        epsilon = (
            D
            / 2
            * np.sqrt(
                x_total_initial / (2 * H * self._gfm_params.get_base_angular_frequency() * u_prod)
            )
        )
        wn = np.sqrt(
            self._gfm_params.get_base_angular_frequency() * u_prod / (2 * H * x_total_initial)
        )

        delta_theta_rad = np.abs(self._gfm_params.get_change_frequency() * np.pi / 180)
        p_peak_calc = delta_theta_rad * u_prod / x_total_initial

        return x_total_initial, epsilon, wn, p_peak_calc

    def _calculate_epsilon_initial_check(
        self, D: np.ndarray, H: np.ndarray, x_total_initial: float
    ) -> float:
        """
        Calculates the initial damping ratio (epsilon) to determine
        whether the system's response is overdamped or underdamped.
        This calculation uses base values to determine the overall system behavior.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        x_total_initial : float
            Total initial reactance of the system.

        Returns
        -------
        float
            The calculated initial damping ratio (epsilon).
        """
        return (
            D
            / 2
            * np.sqrt(
                x_total_initial
                / (
                    2
                    * H
                    * self._gfm_params.get_base_angular_frequency()
                    * self._gfm_params.get_initial_voltage()
                    * self._gfm_params.get_grid_voltage()
                )
            )
        )

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
        t_pll: float
            PLL time constant
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.
        epsilon_initial_check : float
            The pre-calculated initial damping ratio used to determine the damping type.

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
        D_damping : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        t_pll: float
            PLL time constant
        time_array : np.ndarray
            Array of time points.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing:
            - delta_p1: The base delta_p waveform.
            - p_peak: The peak power.
            - epsilon: The damping ratio.
        """
        x_total_initial, _, wn, p_peak = self._calculate_common_params(D, H, Xeff)
        u_prod = self._gfm_params.get_initial_voltage() * self._gfm_params.get_grid_voltage()
        xi = (
            wn * D * x_total_initial / (1 * self._gfm_params.get_base_angular_frequency() * u_prod)
        )

        # Common terms
        alpha = 2 * H * t_pll * np.abs(self._gfm_params.get_change_frequency())
        beta = (2 * H + D * t_pll) / (2 * H * t_pll)

        A_coeff = alpha * beta
        B_coeff = (
            alpha
            * (2 * t_pll * beta * wn * xi - t_pll * wn**2 - beta)
            / (1 - 2 * xi * wn * t_pll + wn**2 * t_pll**2)
        )
        C_coeff = (
            alpha
            * (
                4 * t_pll * beta * wn**2 * xi**2
                - t_pll * beta * wn**2
                - 2 * t_pll * wn**3 * xi
                - 2 * beta * wn * xi
                + wn**2
            )
            / (1 - 2 * xi * wn * t_pll + wn**2 * t_pll**2)
        )
        D_coeff = (
            (t_pll**2 * alpha * wn**2 * (t_pll * beta - 1))
            / (1 - 2 * xi * wn * t_pll + wn**2 * t_pll**2)
            * -1
        )

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
        Calculates delta_p, p_peak, and epsilon for an overdamped system response,
        ensuring that the delta_p values are zero before the specified event time.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        t_pll: float
            PLL time constant
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing:
            - delta_p: The delta_p array for the overdamped system, with pre-event
              values zeroed.
            - p_peak: The peak power.
            - epsilon: The damping ratio.
        """
        delta_p1, p_peak, epsilon = self._get_overdamped_delta_p_base(
            D, H, Xeff, t_pll, time_array
        )
        delta_p = np.where(time_array < event_time, 0, delta_p1)
        return delta_p, p_peak, epsilon

    def _get_overdamped_delta_p_min(
        self,
        D: float,
        H: float,
        Xeff: float,
        t_pll: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> np.ndarray:
        """
        Calculates the minimum delta_p for an overdamped system, by applying
        a lower margin to the base delta_p waveform and setting pre-event values to
        zero.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        t_pll: float
            PLL time constant
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The minimum delta_p array for the overdamped system.
        """
        delta_p1, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, t_pll, time_array)
        delta_p1_margined = (1 + self._gfm_params.get_margin_low()) * delta_p1
        delta_p = np.where(time_array < event_time, 0, delta_p1_margined)
        return delta_p

    def _get_overdamped_delta_p_max(
        self,
        D: float,
        H: float,
        Xeff: float,
        t_pll: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> np.ndarray:
        """
        Calculates the maximum delta_p for an overdamped system, by applying
        an upper margin, an additional delay, and setting pre-event values to zero.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        t_pll: float
            PLL time constant
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The maximum delta_p array for the overdamped system.
        """
        delta_p1, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, t_pll, time_array)
        delta_p1_margined = self._gfm_params.get_margin_high() * delta_p1
        delta_p1_delayed = self._apply_delay(0.01, 0, time_array, delta_p1_margined)
        delta_p = np.where(time_array < event_time, 0, delta_p1_delayed)
        return delta_p

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
        t_pll: float
            PLL time constant
        time_array : np.ndarray
            Array of time points.

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

        # Common terms
        alpha = 2 * H * t_pll * np.abs(self._gfm_params.get_change_frequency())
        beta = (2 * H + D * t_pll) / (2 * H * t_pll)

        A_coeff = alpha * beta
        B_coeff = -(t_pll**2 * alpha * wn**2 * (t_pll * beta - 1)) / (
            1 - 2 * epsilon * wn * t_pll + wn**2 * t_pll**2
        )
        C_coeff = (
            alpha
            * (2 * t_pll * beta * epsilon * wn - t_pll * wn**2 - beta)
            / (1 - 2 * epsilon * wn * t_pll + wn**2 * t_pll**2)
        )
        D_coeff = (
            alpha
            * (
                4 * t_pll * beta * wn**2 * epsilon**2
                - t_pll * beta * wn**2
                - 2 * t_pll * wn**3 * epsilon
                - 2 * beta * wn * epsilon
                + wn**2
            )
            / (1 - 2 * epsilon * wn * t_pll + wn**2 * t_pll**2)
        )

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
        t_pll: float
            PLL time constant
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

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
        D: float,
        H: float,
        Xeff: float,
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
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        t_pll: float
            PLL time constant
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The minimum delta_p array for the underdamped system.
        """
        expected_delta_p = np.abs(-(2 * H + D * t_pll) * self._gfm_params.get_change_frequency())
        delta_p1, _, _ = self._get_underdamped_delta_p_base(D, H, Xeff, t_pll, time_array)
        delta_p1_margined = (1 + self._gfm_params.get_margin_low()) * delta_p1

        delta_p1_diff = np.diff(delta_p1_margined)
        index_decrease = np.where(delta_p1_diff < 0)[0][0]

        min_time = np.min(time_array[index_decrease + 1 :])
        max_value = np.max(delta_p1[index_decrease + 1 :])

        tunnel = self._get_tunnel(expected_delta_p)
        delta_p2 = (
            expected_delta_p
            - tunnel
            + (max_value - expected_delta_p + tunnel)
            * np.exp(-(time_array - min_time) / self._gfm_params.get_t_expo_decrease())
        )

        delta_p = delta_p1_margined
        delta_p[index_decrease + 1 :] = delta_p2[index_decrease + 1 :]

        delta_p = np.where(time_array < event_time, 0, delta_p)
        return delta_p

    def _get_underdamped_delta_p_max(
        self,
        D: float,
        H: float,
        Xeff: float,
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
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        t_pll: float
            PLL time constant
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The maximum delta_p array for the underdamped system.
        """
        expected_delta_p = np.abs(-(2 * H + D * t_pll) * self._gfm_params.get_change_frequency())
        delta_p1, _, _ = self._get_underdamped_delta_p_base(D, H, Xeff, t_pll, time_array)
        delta_p1_margined = (1 + self._gfm_params.get_margin_high()) * delta_p1

        delta_p1_diff = np.diff(delta_p1_margined)
        index_decrease = np.where(delta_p1_diff < 0)[0][0]
        delta_p1_diff[:index_decrease] = 0
        index_increase = np.where(delta_p1_diff > 0)[0][0]

        min_time = np.min(time_array[index_increase + 1 :])
        min_value = np.min(delta_p1[index_increase + 1 :])

        delta_p2 = expected_delta_p + (min_value - expected_delta_p) * np.exp(
            -(time_array - min_time) / self._gfm_params.get_t_expo_decrease()
        )

        delta_p = delta_p1_margined
        delta_p[index_increase + 1 :] = delta_p2[index_increase + 1 :]

        delta_p = np.where(time_array < event_time, 0, delta_p)
        return delta_p

    def _calculate_unlimited_power_envelopes(
        self, list_of_arrays: list[np.ndarray], tunnel: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculates the initial (unlimited) power down and power up envelopes.
        This is done by finding the minimum and maximum across various delta_p arrays
        and adjusting them by the time-dependent tunnel, effectively creating a band.

        Parameters
        ----------
        list_of_arrays : list[np.ndarray]
            A list of delta_p arrays (e.g., nominal, min/max D/H variations, specific
            min/max delta_p) to be used for determining the overall minimum and maximum
            response.
        tunnel : np.ndarray
            The time-dependent tunnel response array, which defines the dynamic width of
            the band.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing:
            - pdown_no_p0: The calculated lower power envelope, without considering the
              initial power (P0).
            - pup_no_p0: The calculated upper power envelope, without considering the
              initial power (P0).
        """
        pdown_no_p0 = np.minimum.reduce(list_of_arrays) - tunnel
        pup_no_p0 = np.maximum.reduce(list_of_arrays) + tunnel
        return np.minimum(pdown_no_p0, pup_no_p0), np.maximum(pdown_no_p0, pup_no_p0)

    def _limit_power_envelopes(
        self,
        pdown_no_p0: np.ndarray,
        pup_no_p0: np.ndarray,
        tunnel_value: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Applies final operational limits to the calculated power down and power up
        envelopes. This involves incorporating the initial power (P0) and clipping
        the signals based on system-defined minimum/maximum power and a constant
        tunnel value.

        Parameters
        ----------
        pdown_no_p0 : np.ndarray
            The unlimited power down signal, not yet adjusted by initial power P0.
        pup_no_p0 : np.ndarray
            The unlimited power up signal, not yet adjusted by initial power P0.
        tunnel_value : float
            The constant tunnel value used for final limiting, defining the static
            band width.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing:
            - pdown_limited: The final, limited power down envelope.
            - pup_limited: The final, limited power up envelope.
        """
        rocof_sign = 1 if self._gfm_params.get_change_frequency() > 0 else -1

        pdown_limited = np.minimum(
            np.maximum(
                self._gfm_params.get_initial_active_power() - rocof_sign * pdown_no_p0,
                -1 + tunnel_value,
            ),
            1 - tunnel_value,
        )
        pup_limited = np.minimum(
            np.maximum(
                self._gfm_params.get_initial_active_power() - 1 * rocof_sign * pup_no_p0,
                self._gfm_params.get_min_active_power(),
            ),
            self._gfm_params.get_max_active_power(),
        )
        return pdown_limited, pup_limited

    def _get_tunnel(self, expected_delta_p: float) -> float:
        """
        Calculates a constant "tunnel" value. This value defines a static band
        around the power response. It is determined as the maximum of a fixed
        power component and a component proportional to the peak power (p_peak).

        Parameters
        ----------
        expected_delta_p : float
            Expected delta P.

        Returns
        -------
        float
            The calculated constant tunnel value.
        """
        return max(
            self._gfm_params.get_final_allowed_tunnel_pn(),
            self._gfm_params.get_final_allowed_tunnel_variation() * expected_delta_p,
        )

    def _get_time_tunnel(
        self, p_peak: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Calculates a time-dependent "tunnel" array. This array represents
        a dynamic band around the power response that expands over time after an
        event. It starts at zero before the event and increases exponentially
        towards a final magnitude.

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
            self._gfm_params.get_final_allowed_tunnel_pn(),
            self._gfm_params.get_final_allowed_tunnel_variation() * p_peak,
        )
        tunnel_exp = 1 - np.exp((-time_array + 0.02) / 0.3)
        tunnel = t_val * tunnel_exp
        return np.where(time_array < event_time, 0, tunnel)
