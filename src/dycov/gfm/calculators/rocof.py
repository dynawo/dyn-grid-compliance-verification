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
    Calculator class dedicated to handling the GFM response to a RoCoF
    (Rate of Change of Frequency) event.

    This class performs all core calculations for active power envelopes,
    mathematically differentiating between overdamped and underdamped
    system responses based on the damping characteristics.
    """

    def __init__(
        self,
        gfm_params: GFMParameters,
    ) -> None:
        """
        Initializes the RoCoF calculator with the specified Grid Forming parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            An object containing all necessary parameters required for the GFM
            calculations, including specific settings for frequency changes.
        """
        super().__init__(gfm_params=gfm_params)

        # Core RoCoF event parameters
        self._rocof_value = gfm_params.get_change_frequency()
        self._rocof_duration = gfm_params.get_change_frequency_duration()
        self._t_pll = gfm_params.get_pll_time_constant()

        # Active power limits and initial conditions
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()

        # Additional parameters integrated to enforce saturation limit constraints
        self._pmax_mois_tunnel = gfm_params.get_pmax_mois_tunnel()
        self._pmin_mois_tunnel = gfm_params.get_pmin_mois_tunnel()

    def get_plot_parameter_names(self) -> list[str]:
        """
        Retrieves the list of parameter names relevant for rendering RoCoF plots.

        Returns
        -------
        list[str]
            A predefined list of string identifiers corresponding to the parameters
            displayed on the output plots.
        """
        return ["P0", "Q0", "Frequency0", "RoCoF", "RoCoFDuration", "SCR", "Xeff", "D", "H"]

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the active power deviation (delta_p) and its bounding envelopes
        (PCC, upper, and lower) evaluated across the event timeframe.

        Parameters
        ----------
        D : float
            The system damping factor.
        H : float
            The system inertia constant.
        Xeff : float
            The effective reactance of the system.
        time_array : np.ndarray
            The array of time points corresponding to the simulation window.
        event_time : float
            The absolute time (in seconds) at which the RoCoF event initiates.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - str: The physical magnitude identifier (e.g., 'P').
            - np.ndarray: The main calculated signal at the PCC.
            - np.ndarray: The upper bounded envelope constraint.
            - np.ndarray: The lower bounded envelope constraint.
        """
        dycov_logging.get_logger("RoCoF").debug(f"Input Params D={D} H={H} Xeff {Xeff}")

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

        # Apply a final uniform delay if the simulation utilizes the EMT engine
        if self._is_emt_flag:
            upper_envelope = self._apply_delay(self._emt_initial_delay, p_up[0], time_array, p_up)
            lower_envelope = self._apply_delay(
                self._emt_initial_delay, p_down[0], time_array, p_down
            )
            pcc_signal = self._apply_delay(self._emt_initial_delay, p_pcc[0], time_array, p_pcc)
        else:
            upper_envelope = p_up
            lower_envelope = p_down
            pcc_signal = p_pcc

        magnitude_name = "P"
        return magnitude_name, pcc_signal, upper_envelope, lower_envelope

    def _get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[list, list, list]:
        """
        Computes the delta_p sequences across nominal, minimum, and maximum
        parameter variations.

        Parameters
        ----------
        D : float
            The nominal damping factor.
        H : float
            The nominal inertia constant.
        Xeff : float
            The effective reactance of the system.
        time_array : np.ndarray
            The array of time points corresponding to the simulation window.
        event_time : float
            The time at which the event initiates.

        Returns
        -------
        tuple[list, list, list]
            A tuple containing:
            - list: The delta_p arrays computed for each variation.
            - list: The peak power values determined for each variation.
            - list: The response times recorded for each variation.
        """
        x_total = Xeff + 1 / self._scr

        # Construct arrays representing the bounds of damping and inertia deviations
        d_array = np.array([D, D * self._min_ratio, D * self._max_ratio])
        h_array = np.array([H, H / self._min_ratio, H / self._max_ratio])

        delta_p_array = []
        p_peak_array = []
        t_response_array = []

        epsilon_vals = []
        u_prod = self._initial_voltage * self._grid_voltage

        for i in range(len(d_array)):
            wn_i = np.sqrt(self._base_angular_frequency * u_prod / (2 * h_array[i] * x_total))
            epsilon_vals.append(d_array[i] / (4 * h_array[i] * wn_i))

            delta_p, p_peak, t_response = self._calculate_delta_p_for_damping(
                d_array[i], h_array[i], x_total, time_array, event_time
            )
            delta_p_array.append(delta_p)
            p_peak_array.append(p_peak)
            t_response_array.append(t_response)

        # Store the computed variations internally for potential data dumps
        self._d_vals = d_array
        self._h_vals = h_array
        self._epsilon_vals = np.array(epsilon_vals)

        return delta_p_array, p_peak_array, t_response_array

    def _calculate_delta_p_for_damping(
        self, D: float, H: float, x_total: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Evaluates the appropriate mathematical strategy (overdamped vs. underdamped)
        and applies the superposition principle to model the finite duration of the event.

        Parameters
        ----------
        D : float
            The specific damping factor variation being processed.
        H : float
            The specific inertia constant variation being processed.
        x_total : float
            The total aggregated reactance of the system.
        time_array : np.ndarray
            The array of time points corresponding to the simulation.
        event_time : float
            The time at which the event initiates.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing the resultant delta_p waveform, its absolute peak
            value, and the derived system response time.
        """
        u_prod = self._initial_voltage * self._grid_voltage
        wn = np.sqrt(self._base_angular_frequency * u_prod / (2 * H * x_total))
        epsilon = D / (4 * H * wn)

        calc_func = (
            self._get_overdamped_delta_p_base
            if epsilon >= self._EPSILON_THRESHOLD
            else self._get_underdamped_delta_p_base
        )

        # A finite duration RoCoF event is modeled by superimposing two independent step responses
        rocof_stop_time = event_time + self._rocof_duration

        time_event_start = time_array - event_time
        p1, p_peak, t_response = calc_func(D, H, x_total, time_event_start)
        p1 = np.where(time_array < event_time, 0, p1)

        time_event_stop = time_array - rocof_stop_time
        p2, _, _ = calc_func(D, H, x_total, time_event_stop)
        p2 = np.where(time_array < rocof_stop_time, 0, p2)

        delta_p = p1 - p2

        return delta_p, p_peak, t_response

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, x_total: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Analytically solves the differential equations governing an overdamped
        system step response.

        Parameters
        ----------
        D : float
            The damping factor.
        H : float
            The inertia constant.
        x_total : float
            The total system reactance.
        time_array : np.ndarray
            The time array shifted relative to the event start (t=0 at event initiation).

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing the foundational delta_p array, the theoretical peak
            power magnitude, and the estimated response time.
        """
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

        # The theoretical response time is approximated as 4x the slowest time constant of the
        # system
        t_response = 4 * max(1 / alpha1, 1 / alpha2, self._t_pll)

        return -delta_p, p_peak, t_response

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, x_total: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Analytically solves the differential equations governing an underdamped
        system step response.

        Parameters
        ----------
        D : float
            The damping factor.
        H : float
            The inertia constant.
        x_total : float
            The total system reactance.
        time_array : np.ndarray
            The time array shifted relative to the event start (t=0 at event initiation).

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing the foundational delta_p array, the theoretical peak
            power magnitude, and the estimated response time.
        """
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

        # The theoretical response time is approximated as 4x the decay time constant of the
        # oscillation
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
        Computes the final active power envelopes by sequentially applying
        boundary limitations and dynamic logic rules specific to RoCoF events.

        Parameters
        ----------
        delta_p_array : list[np.ndarray]
            The list of delta_p waveforms extracted from parameter variations.
        p_peak_array : list[float]
            The list of corresponding peak power shifts.
        t_response_array : list[float]
            The list of corresponding system transient response times.
        time_array : np.ndarray
            The absolute time array mapped for the simulation.
        event_time : float
            The designated start time of the frequency event.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple returning the main PCC signal, the upper power constraint envelope,
            and the lower power constraint envelope.
        """
        p_pcc = self._initial_active_power + delta_p_array[self._ORIGINAL_PARAMS_IDX]
        tunnel_val = self._get_tunnel(p_peak_array)
        sign = np.sign(self._rocof_value)

        # Rule 1: Determine the initial, unconstrained envelopes utilizing the minimum and maximum
        # response traces.
        dp_min_trace = np.minimum.reduce(delta_p_array)
        dp_max_trace = np.maximum.reduce(delta_p_array)

        if sign > 0:  # Positive RoCoF implies Active Power decreases (delta_p is negative).
            p_up_unlimited = (
                self._initial_active_power + dp_max_trace * (1 - self._margin_high) + tunnel_val
            )
            p_down_unlimited = (
                self._initial_active_power + dp_min_trace * (1 + self._margin_low) - tunnel_val
            )
        else:  # Negative RoCoF implies Active Power increases (delta_p is positive).
            p_up_unlimited = (
                self._initial_active_power + dp_max_trace * (1 + self._margin_high) + tunnel_val
            )
            p_down_unlimited = (
                self._initial_active_power + dp_min_trace * (1 - self._margin_low) - tunnel_val
            )

        # Rule 2: Constrain envelopes to steady-state values following the completion of the
        # transient response time.
        t_response = t_response_array[self._ORIGINAL_PARAMS_IDX]
        clamp_start_time = event_time + t_response
        rocof_stop_time = event_time + self._rocof_duration

        if clamp_start_time < rocof_stop_time:
            mask = (time_array >= clamp_start_time) & (time_array < rocof_stop_time)
            pcc_steady_value = np.interp(clamp_start_time, time_array, p_pcc)
            p_up_unlimited = np.where(mask, pcc_steady_value + tunnel_val, p_up_unlimited)
            p_down_unlimited = np.where(mask, pcc_steady_value - tunnel_val, p_down_unlimited)

        # Rule 3: Prevent uncharacteristic dips or overshoots during the system recovery phase.
        indices_before_recovery = np.where(time_array < rocof_stop_time)[0]
        if len(indices_before_recovery) > 0:
            idx_before_recovery = indices_before_recovery[-1]
            mask_post_recovery = time_array >= rocof_stop_time

            if (
                sign > 0
            ):  # With power dropping, ensure the lower envelope recovers strictly upwards.
                clamp_val = p_down_unlimited[idx_before_recovery]
                p_down_unlimited = np.where(
                    mask_post_recovery, np.maximum(p_down_unlimited, clamp_val), p_down_unlimited
                )
            else:  # With power rising, ensure the upper envelope recovers strictly downwards.
                clamp_val = p_up_unlimited[idx_before_recovery]
                p_up_unlimited = np.where(
                    mask_post_recovery, np.minimum(p_up_unlimited, clamp_val), p_up_unlimited
                )

        # Rule 4: Apply saturation limit protection (MoisTunnel logic).
        # This safeguard ensures the required envelope bounds do not inherently demand performance
        # beyond the hardware saturation margin, even prior to hitting absolute physical limits.
        p_down_unlimited = np.where(
            p_down_unlimited > self._pmax_mois_tunnel, self._pmax_mois_tunnel, p_down_unlimited
        )
        p_up_unlimited = np.where(
            p_up_unlimited < self._pmin_mois_tunnel, self._pmin_mois_tunnel, p_up_unlimited
        )

        # Execute the absolute final clipping restricting signals to operational physical limits.
        p_up_limited = np.clip(p_up_unlimited, self._min_active_power, self._max_active_power)
        p_down_limited = np.clip(p_down_unlimited, self._min_active_power, self._max_active_power)

        return p_pcc, p_up_limited, p_down_limited

    def _get_tunnel(self, p_peak_array: list[float]) -> float:
        """
        Calculates the static tolerance margin "tunnel" value defining the
        acceptable operational band.

        Parameters
        ----------
        p_peak_array : list[float]
            The list of peak power shifts used to dimension the tunnel amplitude.

        Returns
        -------
        float
            The mathematically derived static tunnel value.
        """
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]
        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * p_peak,
        )
