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
        """
        Initializes the SCRJump calculator with GFM parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            An object containing all necessary parameters for the GFM
            calculations.
        """
        super().__init__(gfm_params=gfm_params)

        initial_scr = gfm_params.get_initial_scr()
        self._final_scr = gfm_params.get_final_scr()
        self._delta_impedance = 1 / self._final_scr - 1 / initial_scr
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the change in power (delta_p) and active power envelopes
        (PCC, upper, and lower) based on damping characteristics for an SCR
        jump event.

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
            time_array=time_array,
            event_time=event_time,
        )
        return "P", p_pcc, p_up, p_down

    def _get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[list[np.ndarray], list[np.ndarray], list[np.ndarray], list[float], list[float]]:
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
        tuple[list[np.ndarray], list[np.ndarray], list[np.ndarray], list[float], list[float]]
            A tuple containing:
            - delta_p_array: List of delta_p arrays for parameter variations.
            - delta_p_min: List of analytical lower envelopes of delta_p.
            - delta_p_max: List of analytical upper envelopes of delta_p.
            - p_peak_array: List of p_peak values.
            - epsilon_array: List of epsilon values.
        """
        x_total_initial = Xeff + 1 / self._final_scr

        d_array = np.array([D, D * self._min_ratio, D * self._max_ratio])
        h_array = np.array([H, H / self._min_ratio, H / self._max_ratio])

        epsilon_initial_check = self._calculate_epsilon_initial_check(
            d_array, h_array, x_total_initial
        )
        dycov_logging.get_logger("SCRJump").debug(f"Epsilon={epsilon_initial_check}")

        delta_p_array: list[np.ndarray] = []
        p_peak_array: list[float] = []
        epsilon_array: list[float] = []

        for i in range(len(d_array)):
            delta_p, p_peak, epsilon = self._calculate_delta_p_for_damping(
                d_array[i],
                h_array[i],
                Xeff,
                time_array,
                event_time,
                epsilon_initial_check[i],
            )
            delta_p_array.append(delta_p)
            p_peak_array.append(p_peak)
            epsilon_array.append(epsilon)

        delta_p_min: list[np.ndarray] = []
        delta_p_max: list[np.ndarray] = []
        if epsilon_initial_check[self._ORIGINAL_PARAMS_IDX] < self._EPSILON_THRESHOLD:
            for i in range(len(d_array)):
                delta_p = self._get_underdamped_amplitude_envelope(
                    d_array[i],
                    h_array[i],
                    Xeff,
                    time_array,
                )

                delta_p_min.append(np.where(time_array < event_time, 0, delta_p * -1))
                delta_p_max.append(np.where(time_array < event_time, 0, delta_p))

        return (
            delta_p_array,
            delta_p_min,
            delta_p_max,
            p_peak_array,
            epsilon_array,
        )

    def _modify_envelope(
        self,
        signal: np.ndarray,
        p_50_percent: np.ndarray,
        time_array: np.ndarray,
        event_time: float,
    ) -> np.ndarray:
        """
        Modifies the envelope signal around the event time to ensure it stays
        within acceptable limits.

        Parameters
        ----------
        signal : np.ndarray
            The power signal to be modified.
        p_50_percent : np.ndarray
            A 50% power threshold signal.
        time_array : np.ndarray
            The time array.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The modified signal.
        """
        delta = 0.03
        mask = (time_array >= event_time) & (time_array <= event_time + delta)
        signal = np.where(mask, p_50_percent, signal)

        signal = np.where(
            signal * mask < self._min_active_power,
            self._min_active_power + 0.2,
            signal,
        )
        signal = np.where(
            signal * mask > self._max_active_power,
            self._max_active_power - 0.2,
            signal,
        )
        return signal

    def _get_envelope_traces(
        self,
        delta_p: np.ndarray,
        time_array: np.ndarray,
        event_time: float,
        tunnel: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Generates the envelope traces for the upper and lower active power
        envelopes based on the change in power direction.

        Parameters
        ----------
        delta_p : np.ndarray
            The delta_p array for the system.
        time_array : np.ndarray
            The time array for the simulation.
        event_time : float
            The time at which the event occurs.
        tunnel : float
            The tunnel value for margin calculations.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing the upper and lower envelope traces.
        """
        # Check the direction of power change right after the event
        delta_p_at_event = delta_p[np.where(time_array >= event_time + 0.01)[0][1]]
        p_50_percent = self._initial_active_power + np.where(
            time_array >= event_time, delta_p * 0.5 + 0.005, delta_p
        )

        if delta_p_at_event > 0:
            # Power increases, so upper envelope is above and lower is below
            p_up_trace = self._initial_active_power + delta_p * (1 + self._margin_high) + tunnel

            p_down_trace = self._initial_active_power + delta_p * (1 - self._margin_low) - tunnel
            p_down_trace = self._modify_envelope(
                p_down_trace, p_50_percent, time_array, event_time
            )

            mask = (time_array >= event_time) & (time_array <= time_array[-1])
            condition = mask & (p_down_trace > self._max_active_power * 0.95)
            p_down_trace = np.where(condition, self._max_active_power * 0.95, p_down_trace)

        else:
            # Power decreases, so margins are inverted relative to delta_p
            p_up_trace = self._initial_active_power + delta_p * (1 - self._margin_high) + tunnel
            p_up_trace = self._modify_envelope(p_up_trace, p_50_percent, time_array, event_time)

            mask = (time_array >= event_time) & (time_array <= time_array[-1])
            condition = mask & (p_up_trace < self._min_active_power * 0.95)
            p_up_trace = np.where(condition, self._min_active_power * 0.95, p_up_trace)

            p_down_trace = self._initial_active_power + delta_p * (1 + self._margin_low) - tunnel

        return p_up_trace, p_down_trace

    def _apply_initial_limiting(
        self,
        p_up: np.ndarray,
        p_down: np.ndarray,
        delta_p: np.ndarray,
        time_array: np.ndarray,
        event_time: float,
        tunnel: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Applies an initial limit to the envelopes to prevent unrealistic
        reverse power excursions during the first 100 ms of the event.

        Parameters
        ----------
        p_up : np.ndarray
            The unlimited upper envelope.
        p_down : np.ndarray
            The unlimited lower envelope.
        delta_p : np.ndarray
            The power change array to determine the event's direction.
        time_array : np.ndarray
            The simulation's time array.
        event_time : float
            The time at which the event occurs.
        tunnel : float
            The tolerance tunnel value.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            The upper and lower envelopes with the initial limit applied.
        """
        # Determine the direction of the power change right after the event
        delta_p_at_event = delta_p[np.where(time_array >= event_time + 0.01)[0][1]]

        # Create a mask for the first 100 ms after the event
        mask = (time_array >= event_time) & (time_array <= event_time + 0.1)

        if delta_p_at_event > 0:
            # If power increases, the lower envelope is limited to prevent it from dropping too low.
            condition = mask & (p_down < (self._initial_active_power - tunnel))
            p_down = np.where(condition, self._initial_active_power - tunnel, p_down)
        else:
            # If power decreases, the upper envelope is limited to prevent it from rising too high.
            condition = mask & (p_up > (self._initial_active_power + tunnel))
            p_up = np.where(condition, self._initial_active_power + tunnel, p_up)

        return p_up, p_down

    def _get_envelopes(
        self,
        delta_p_array: list[np.ndarray],
        delta_p_min: list[np.ndarray],
        delta_p_max: list[np.ndarray],
        p_peak_array: list[float],
        time_array: np.ndarray,
        event_time: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates and limits the final active power envelopes.

        Parameters
        ----------
        delta_p_array : list[np.ndarray]
            List of delta_p arrays.
        delta_p_min : list[np.ndarray]
            List of delta_p_min arrays.
        delta_p_max : list[np.ndarray]
            List of delta_p_max arrays.
        p_peak_array : list[float]
            List of p_peak values.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            Time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple containing p_pcc_final, p_up_final, p_down_final.
        """
        delta_p = delta_p_array[self._ORIGINAL_PARAMS_IDX]
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]

        p_pcc = self._initial_active_power + delta_p
        p_50_percent = self._initial_active_power + delta_p * 0.5
        tunnel = self._get_tunnel(p_peak)

        all_traces_up = []
        all_traces_down = []

        for i in range(len(delta_p_array)):
            p_up_trace, p_down_trace = self._get_envelope_traces(
                delta_p_array[i], time_array, event_time, tunnel
            )

            all_traces_up.append(p_up_trace)
            all_traces_down.append(p_down_trace)

            if delta_p_min:
                p_up_trace, p_down_trace = self._get_envelope_traces(
                    delta_p_min[i], time_array, event_time, tunnel
                )

                all_traces_up.append(p_up_trace)
                all_traces_down.append(p_down_trace)

            if delta_p_max:
                p_up_trace, p_down_trace = self._get_envelope_traces(
                    delta_p_max[i], time_array, event_time, tunnel
                )

                all_traces_up.append(p_up_trace)
                all_traces_down.append(p_down_trace)

        all_traces_up.append(p_50_percent)
        all_traces_down.append(p_50_percent)

        p_up_unlimited = np.maximum.reduce(all_traces_up)
        p_down_unlimited = np.minimum.reduce(all_traces_down)

        p_up_unlimited, p_down_unlimited = self._apply_initial_limiting(
            p_up=p_up_unlimited,
            p_down=p_down_unlimited,
            delta_p=delta_p,
            time_array=time_array,
            event_time=event_time,
            tunnel=tunnel,
        )

        p_up_limited = np.clip(p_up_unlimited, self._min_active_power, self._max_active_power)
        p_down_limited = np.clip(p_down_unlimited, self._min_active_power, self._max_active_power)

        if self._is_emt_flag:
            p_up_final = self._apply_delay(0.02, p_up_limited[0], time_array, p_up_limited)
            p_down_final = self._apply_delay(0.02, p_down_limited[0], time_array, p_down_limited)
            p_pcc_final = self._apply_delay(0.02, p_pcc[0], time_array, p_pcc)
        else:
            p_up_final = p_up_limited
            p_down_final = p_down_limited
            p_pcc_final = p_pcc

        return p_pcc_final, p_up_final, p_down_final

    def _calculate_common_params(
        self, D: float, H: float, Xeff: float
    ) -> tuple[float, float, float, float]:
        """
        Calculates common parameters required for delta_p calculations.

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
        x_total_initial = Xeff + 1 / self._final_scr
        u_prod = self._initial_voltage * self._grid_voltage

        wn = np.sqrt(self._base_angular_frequency * u_prod / (2 * H * x_total_initial))
        epsilon = D / (4 * H * wn)

        p_peak_calc = self._delta_impedance * self._initial_active_power / x_total_initial

        return x_total_initial, epsilon, wn, p_peak_calc

    def _get_underdamped_amplitude_envelope(
        self,
        D: float,
        H: float,
        Xeff: float,
        time_array: np.ndarray,
    ) -> np.ndarray:
        """
        Calculates the amplitude envelope for an underdamped system response.

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

        Returns
        -------
        np.ndarray
            The amplitude envelope array.
        """
        x_total, epsilon, wn, _ = self._calculate_common_params(D, H, Xeff)
        wd = wn * np.sqrt(1 - epsilon**2)

        p_peak = self._delta_impedance * self._initial_active_power / x_total

        amplitude_envelops = np.sqrt(1 + ((D - 2 * H * epsilon * wn) / (2 * H * wd)) ** 2)
        delta_p = np.abs(amplitude_envelops * p_peak * np.exp(-epsilon * wn * time_array))
        return delta_p

    def _calculate_delta_p_for_damping(
        self,
        D: float,
        H: float,
        Xeff: float,
        time_array: np.ndarray,
        event_time: float,
        epsilon_initial_check: float,
    ) -> tuple[np.ndarray, float, float]:
        """
        Selects the delta_p calculation method based on damping.

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
        epsilon_initial_check : float
            Initial check value for epsilon to determine damping type.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing delta_p, p_peak, and epsilon.
        """
        if epsilon_initial_check >= 1:
            return self._get_overdamped_delta_p(D, H, Xeff, time_array, event_time)
        else:
            return self._get_underdamped_delta_p(D, H, Xeff, time_array, event_time)

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the base delta_p waveform for an overdamped system.

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

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing the base delta_p, peak power, and epsilon.
        """
        x_total, epsilon, _, _ = self._calculate_common_params(D, H, Xeff)

        alpha_val = D / (2 * H)
        beta_val = self._base_angular_frequency / (2 * H * x_total)

        p1 = (alpha_val - np.sqrt(alpha_val**2 - 4 * beta_val)) / 2
        p2 = (alpha_val + np.sqrt(alpha_val**2 - 4 * beta_val)) / 2

        A = (2 * H * (-p1) + D) / (p2 - p1) / (2 * H)
        B = (2 * H * (-p2) + D) / (p1 - p2) / (2 * H)

        term1 = A * np.exp(-p1 * time_array)
        term2 = B * np.exp(-p2 * time_array)

        delta_p1 = (self._delta_impedance * self._initial_active_power / x_total) * (term1 + term2)

        p_peak = (
            self._initial_active_power
            * self._delta_impedance
            / (x_total * (np.sqrt((D**2) - 8 * H * self._base_angular_frequency / x_total)))
        )
        return delta_p1, p_peak, epsilon

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
        tuple[np.ndarray, float, float]
            A tuple containing delta_p, p_peak, and epsilon.
        """
        delta_p1, p_peak, epsilon = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p = np.where(time_array < event_time, 0, delta_p1 * -1)

        return delta_p, p_peak, epsilon

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the base delta_p waveform for an underdamped system.

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

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing the base delta_p, peak power, and epsilon.
        """
        x_total, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)
        wd = wn * np.sqrt(1 - epsilon**2)

        exp_term = np.exp(-epsilon * wn * time_array)
        cos_term = np.cos(wd * time_array)
        sin_term = np.sin(wd * time_array)

        term2 = ((D / (2 * H) - epsilon * wn) / wd) * sin_term

        delta_p1 = p_peak * exp_term * (cos_term + term2) * -1

        p_peak = self._delta_impedance * self._initial_active_power / x_total

        return delta_p1, p_peak, epsilon

    def _get_underdamped_delta_p(
        self,
        D: float,
        H: float,
        Xeff: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates delta_p and its envelopes for an underdamped system.

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
        tuple[np.ndarray, float, float]
            A tuple containing delta_p, p_peak, and epsilon.
        """
        delta_p1, p_peak, epsilon = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p = np.where(time_array < event_time, 0, delta_p1)

        return delta_p, p_peak, epsilon

    def _get_tunnel(self, p_peak: float) -> float:
        """
        Calculates the tolerance "tunnel" value.

        Parameters
        ----------
        p_peak : float
            The peak change in active power.

        Returns
        -------
        float
            The calculated tunnel value.
        """
        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * np.abs(p_peak),
        )
