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


class PhaseJump(GFMCalculator):
    """
    Class to calculate the GFM phase jump response.
    This class handles all core calculations for delta_p and active power
    envelopes, differentiating between overdamped and underdamped system
    responses.
    """

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> tuple[bool, np.ndarray, np.ndarray, np.ndarray]:
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
        time_array : np.array
            Array of time points for simulation.
        event_time : float
            The time (in seconds) at which the phase jump event occurs.

        Returns
        -------
        tuple[bool, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - is_overdamped: True if the initial system is overdamped, False otherwise.
            - p_pcc_final: The final calculated active power at the point of common
              coupling.
            - p_up_final: The final upper active power envelope.
            - p_down_final: The final lower active power envelope.
        """
        (
            is_overdamped,
            delta_p_array,
            delta_p_min,
            delta_p_max,
            p_peak_array,
            _,  # epsilon_array is returned but not used here
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
        return is_overdamped, p_pcc, p_up, p_down

    def _get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> tuple[bool, list, np.ndarray, np.ndarray, list, list]:
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
        time_array : np.array
            Array of time points for simulation.
        event_time : float
            The time (in seconds) at which the phase jump event occurs.

        Returns
        -------
        tuple[bool, list, np.ndarray, np.ndarray, list, list]
            A tuple containing:
            - is_overdamped: True if the initial system is overdamped, False otherwise.
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
        x_gr = 1 / self._gfm_params.SCR  # Grid reactance derived from SCR
        x_total_initial = (
            Xeff + x_gr
        )  # Total initial reactance, sum of effective and grid reactances.
        # Calculate initial epsilon to determine damping type (overdamped/underdamped).
        epsilon_initial_check = self._calculate_epsilon_initial_check(D, H, x_total_initial)

        # Prepare arrays for D (damping factor) and H (inertia constant) parameters,
        # including nominal, minimum, and maximum variations.
        d_array = np.array([D, D * self._gfm_params.RatioMin, D * self._gfm_params.RatioMax])
        h_array = np.array([H, H / self._gfm_params.RatioMin, H / self._gfm_params.RatioMax])

        delta_p_array = []  # Stores delta_p for nominal, min, max D/H variations
        p_peak_array = []  # Stores p_peak for nominal, min, max D/H variations
        epsilon_array = []  # Stores epsilon for nominal, min, max D/H variations

        # Loop through parameter variations (nominal, min, max) to calculate
        # delta_p, p_peak, and epsilon for each.
        for i in range(len(d_array)):
            delta_p, p_peak, epsilon = self._calculate_delta_p_for_damping(
                d_array[i], h_array[i], Xeff, time_array, event_time, epsilon_initial_check
            )
            delta_p_array.append(delta_p)
            p_peak_array.append(p_peak)
            epsilon_array.append(epsilon)

        # Calculate specific delta_p for min and max parameter cases using the
        # appropriate damping model (overdamped or underdamped) determined by
        # epsilon_initial_check.
        if epsilon_initial_check > self._EPSILON_THRESHOLD:
            # If overdamped, use overdamped specific min/max delta_p calculations.
            delta_p_min = self._get_overdamped_delta_p_min(D, H, Xeff, time_array, event_time)
            delta_p_max = self._get_overdamped_delta_p_max(D, H, Xeff, time_array, event_time)
        else:
            # If underdamped, use underdamped specific min/max delta_p calculations.
            delta_p_min = self._get_underdamped_delta_p_min(D, H, Xeff, time_array, event_time)
            delta_p_max = self._get_underdamped_delta_p_max(D, H, Xeff, time_array, event_time)

        # Print debug information for delta_p values.
        dycov_logging.get_logger("PhaseJump").debug(
            f"DeltaP Nom {delta_p_array[self._ORIGINAL_PARAMS_IDX]}"
        )
        dycov_logging.get_logger("PhaseJump").debug(
            f"DeltaP Min {delta_p_array[self._MINIMUM_PARAMS_IDX]}"
        )
        dycov_logging.get_logger("PhaseJump").debug(
            f"DeltaP Max {delta_p_array[self._MAXIMUM_PARAMS_IDX]}"
        )
        dycov_logging.get_logger("PhaseJump").debug(f"P Min {delta_p_min}")
        dycov_logging.get_logger("PhaseJump").debug(f"P Max {delta_p_max}")

        # Return all calculated delta_p arrays, p_peak values, and damping
        # information. The boolean indicates if the initial system is overdamped.
        return (
            epsilon_initial_check > self._EPSILON_THRESHOLD,
            delta_p_array,
            delta_p_min,
            delta_p_max,
            p_peak_array,
            epsilon_array,
        )

    def _get_envelopes(
        self,
        delta_p_array: list,
        delta_p_min: np.ndarray,
        delta_p_max: np.ndarray,
        p_peak_array: list,
        time_array: np.array,
        event_time: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates and limits the final active power envelopes (PCC power, upper
        envelope, lower envelope). This involves combining various delta_p
        calculations, applying a time-dependent tunnel effect, and enforcing
        operational limits.

        Parameters
        ----------
        delta_p_array : list
            List of delta_p arrays for original, min, and max parameters.
        delta_p_min : np.ndarray
            delta_p array calculated with minimum parameters.
        delta_p_max : np.ndarray
            delta_p array calculated with maximum parameters.
        p_peak_array : list
            List of p_peak values for original, min, and max parameters.
        time_array : np.array
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - p_pcc_final: The final calculated active power at the point of common
              coupling.
            - p_up_final: The final upper active power envelope.
            - p_down_final: The final lower active power envelope.
        """
        # Extract the original (nominal) delta_p and p_peak values from the provided
        # lists.
        delta_p = delta_p_array[self._ORIGINAL_PARAMS_IDX]
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]

        # Calculate the time-dependent tunnel effect, which creates a dynamic band
        # around the power response.
        tunnel_time_dep = self._get_time_tunnel(
            p_peak=p_peak, time_array=time_array, event_time=event_time
        )

        # Calculate the theoretical active power at the point of Common Coupling (PCC).
        # This is based on the initial power (P0) and delta_p, adjusted by the sign
        # of delta_theta to reflect the direction of power change.
        p_pcc = self._gfm_params.P0 + delta_p * -(
            self._gfm_params.delta_theta / np.abs(self._gfm_params.delta_theta)
        )
        # Clip the calculated PCC power to stay within defined minimum and maximum
        # power limits.
        p_pcc = self._cut_signal(self._gfm_params.PMin, p_pcc, self._gfm_params.PMax)

        # Combine all relevant delta_p arrays into a single list for envelope
        # calculations. This includes nominal, min/max D/H variations, and the
        # specific min/max delta_p.
        list_of_arrays = delta_p_array + [delta_p_min, delta_p_max]

        # Calculate initial unlimited active power envelopes (down and up) by
        # considering the minimum/maximum of all delta_p arrays and applying the
        # time-dependent tunnel.
        pdown_no_p0, pup_no_p0 = self._calculate_unlimited_power_envelopes(
            list_of_arrays, tunnel_time_dep
        )

        # Apply final operational limits to the active power envelopes using a
        # constant tunnel value.
        pdown_limited, pup_limited = self._limit_power_envelopes(
            pdown_no_p0, pup_no_p0, self._get_tunnel(p_peak_array)
        )

        # If EMT simulation flag is true, apply a small delay to the final power
        # signals.
        if self._gfm_params.EMT:
            p_up_final = self._apply_delay(0.02, pup_limited[0], time_array, pup_limited)
            p_down_final = self._apply_delay(0.02, pdown_limited[0], time_array, pdown_limited)
            p_pcc_final = self._apply_delay(0.02, p_pcc[0], time_array, p_pcc)
        else:
            # Otherwise, the limited envelopes are the final envelopes.
            p_up_final = pup_limited
            p_down_final = pdown_limited
            p_pcc_final = p_pcc

        # Ensure that the upper envelope is always greater than or equal to the
        # lower envelope at the end of the simulation. If not, swap them.
        if p_up_final[-1] < p_down_final[-1]:
            p_temp = p_down_final
            p_down_final = p_up_final
            p_up_final = p_temp

        # Return the final calculated power signals for PCC, upper envelope, and
        # lower envelope.
        return p_pcc_final, p_up_final, p_down_final

    def _calculate_common_params(self, D: float, H: float, Xeff: float) -> tuple:
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
        tuple
            A tuple containing:
            - x_total_initial: Total initial reactance.
            - epsilon: Damping ratio.
            - wn: Natural frequency.
            - p_peak_calc: Calculated peak power.
        """
        x_gr = (
            1 / self._gfm_params.SCR
        )  # Grid reactance, calculated from Short Circuit Ratio (SCR).
        x_total_initial = Xeff + x_gr  # Sum of effective reactance and grid reactance.
        u_prod = (
            self._gfm_params.Ucv * self._gfm_params.Ugr
        )  # Product of converter voltage and grid voltage.

        # Calculate damping ratio (epsilon) based on D, H, and reactances/voltages.
        epsilon = D / 2 * np.sqrt(x_total_initial / (2 * H * self._gfm_params.Wb * u_prod))
        # Calculate natural frequency (wn) based on H, reactances/voltages, and base
        # frequency.
        wn = np.sqrt(self._gfm_params.Wb * u_prod / (2 * H * x_total_initial))

        # Convert delta_theta from degrees to radians and calculate peak power.
        delta_theta_rad = np.abs(self._gfm_params.delta_theta * np.pi / 180)
        p_peak_calc = delta_theta_rad * u_prod / x_total_initial

        return x_total_initial, epsilon, wn, p_peak_calc

    def _calculate_epsilon_initial_check(
        self, D: float, H: float, x_total_initial: float
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
        # Calculate epsilon based on the damping factor, inertia constant,
        # total reactance, base frequency, and voltages.
        return (
            D
            / 2
            * np.sqrt(
                x_total_initial
                / (2 * H * self._gfm_params.Wb * self._gfm_params.Ucv * self._gfm_params.Ugr)
            )
        )

    def _calculate_delta_p_for_damping(
        self,
        D: float,
        H: float,
        Xeff: float,
        time_array: np.array,
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
        time_array : np.array
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
            # If epsilon is above the threshold, the system is considered overdamped.
            return self._get_overdamped_delta_p(D, H, Xeff, time_array, event_time)
        else:
            # Otherwise, the system is considered underdamped.
            return self._get_underdamped_delta_p(D, H, Xeff, time_array, event_time)

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.array
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
        time_array : np.array
            Array of time points.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing:
            - delta_p1: The base delta_p waveform.
            - p_peak: The peak power.
            - epsilon: The damping ratio.
        """
        # Calculate common parameters like epsilon, natural frequency (wn), and peak
        # power (p_peak).
        _, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)
        # Calculate the damped natural frequency specific to an overdamped system.
        wd = wn * np.sqrt(epsilon**2 - 1)

        # Calculate the roots of the characteristic equation for an overdamped system.
        alpha = epsilon * wn + wd
        beta = epsilon * wn - wd

        # Calculate coefficients A and B for the overdamped response equation.
        A = 1 / (beta - alpha)
        B = -A

        # Calculate individual terms of the delta_p1 equation, which is a combination
        # of exponential functions characteristic of an overdamped system response.
        term1 = 2 * H * A * (1 - alpha * np.exp(-alpha * time_array))
        term2 = 2 * H * B * (1 - beta * np.exp(-beta * time_array))
        term3 = D * A * np.exp(-alpha * time_array)
        term4 = D * B * np.exp(-beta * time_array)

        # Combine terms to get the base delta_p1 waveform.
        delta_p1 = (p_peak / (2 * H)) * (term1 + term2 + term3 + term4)
        return delta_p1, p_peak, epsilon

    def _get_overdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
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
        time_array : np.array
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
        # Get the base delta_p waveform, peak power, and damping ratio for an
        # overdamped system.
        delta_p1, p_peak, epsilon = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        # Set delta_p to 0 for all time points occurring before the event_time.
        delta_p = np.where(time_array < event_time, 0, delta_p1)
        return delta_p, p_peak, epsilon

    def _get_overdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
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
        time_array : np.array
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The minimum delta_p array for the overdamped system.
        """
        # Get the base delta_p waveform for an overdamped system.
        delta_p1, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        # Apply the lower margin specified in gfm_params to the base delta_p.
        delta_p1_margined = (1 + self._gfm_params.MarginLow) * delta_p1
        # Set delta_p to 0 for all time points occurring before the event_time.
        delta_p = np.where(time_array < event_time, 0, delta_p1_margined)
        return delta_p

    def _get_overdamped_delta_p_max(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
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
        time_array : np.array
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The maximum delta_p array for the overdamped system.
        """
        # Get the base delta_p waveform for an overdamped system.
        delta_p1, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        # Apply the upper margin specified in gfm_params to the base delta_p.
        delta_p1_margined = self._gfm_params.MarginHigh * delta_p1
        # Apply a small delay to the margined delta_p waveform.
        delta_p1_delayed = self._apply_delay(0.01, 0, time_array, delta_p1_margined)
        # Set delta_p to 0 for all time points occurring before the event_time.
        delta_p = np.where(time_array < event_time, 0, delta_p1_delayed)
        return delta_p

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.array
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
        time_array : np.array
            Array of time points.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing:
            - delta_p1: The base delta_p waveform.
            - p_peak: The peak power.
            - epsilon: The damping ratio.
        """
        # Calculate common parameters like epsilon, natural frequency (wn), and peak
        # power (p_peak).
        _, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)
        # Calculate the damped natural frequency specific to an underdamped system.
        wd = wn * np.sqrt(1 - epsilon**2)

        # Calculate individual terms of the delta_p1 equation, which involves
        # exponential decay and sinusoidal oscillation characteristic of an
        # underdamped system.
        term1 = np.exp(-epsilon * wn * time_array)
        term2 = np.cos(wd * time_array)
        term3 = np.sin(wd * time_array)

        # Combine terms to get the base delta_p1 waveform.
        delta_p1 = term1 * (term2 - (epsilon * wn - 1) / wd * term3) * p_peak
        return delta_p1, p_peak, epsilon

    def _get_underdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
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
        time_array : np.array
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
        # Get the base delta_p waveform, peak power, and damping ratio for an
        # underdamped system.
        delta_p1, p_peak, epsilon = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        # Set delta_p to 0 for all time points occurring before the event_time.
        delta_p = np.where(time_array < event_time, 0, delta_p1)
        return delta_p, p_peak, epsilon

    def _get_underdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
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
        time_array : np.array
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The minimum delta_p array for the underdamped system.
        """
        # Get the peak power from the base underdamped delta_p calculation.
        _, p_peak, _ = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        # Calculate the decay rate (sigma) for the exponential envelope.
        sigma = D / (4 * H)
        # Apply the lower margin and an exponential decay to the peak power to get
        # the margined delta_p.
        delta_p_margined = p_peak * (1 - self._gfm_params.MarginLow) * np.exp(-sigma * time_array)
        # Apply a small delay to the margined delta_p.
        delta_p_delayed = self._apply_delay(0.01, 0, time_array, delta_p_margined)
        # Set delta_p to 0 for all time points occurring before the event_time.
        delta_p = np.where(time_array < event_time, 0, delta_p_delayed)
        return delta_p

    def _get_underdamped_delta_p_max(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
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
        time_array : np.array
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The maximum delta_p array for the underdamped system.
        """
        # Get the base delta_p waveform and peak power for an underdamped system.
        _, p_peak, _ = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        # Calculate the decay rate (sigma) for the exponential envelope.
        sigma = D / (4 * H)
        # Apply the upper margin and an exponential decay to the peak power to get
        # the margined delta_p.
        delta_p_margined = p_peak * (1 + self._gfm_params.MarginHigh) * np.exp(-sigma * time_array)
        # Apply a small delay to the margined delta_p, using the first value of the
        # margined signal as the fill value for the delay period.
        delta_p_delayed = self._apply_delay(
            0.01, delta_p_margined[0], time_array, delta_p_margined
        )
        # Set delta_p to 0 for all time points occurring before the event_time.
        delta_p = np.where(time_array < event_time, 0, delta_p_delayed)
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
        # Calculate the lower envelope by taking the minimum across all delta_p arrays
        # and then subtracting the time-dependent tunnel.
        pdown_no_p0 = np.minimum.reduce(list_of_arrays) - tunnel
        # Calculate the upper envelope by taking the maximum across all delta_p arrays
        # and then adding the time-dependent tunnel.
        pup_no_p0 = np.maximum.reduce(list_of_arrays) + tunnel
        return pdown_no_p0, pup_no_p0

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
        # Determine the sign of delta_theta. This is crucial for correctly applying
        # the power change direction relative to the initial power P0.
        delta_theta_sign = 1 if self._gfm_params.delta_theta > 0 else -1

        # Limit the lower power envelope (pdown_limited):
        # 1. Adjust the 'pdown_no_p0' by adding the initial power P0 and applying
        #    the delta_theta_sign to reflect the power change direction.
        # 2. Ensure the resulting signal stays within the range defined by
        #    [-1 + tunnel_value] and [1 - tunnel_value], effectively clipping it.
        pdown_limited = np.minimum(
            np.maximum(
                self._gfm_params.P0 - delta_theta_sign * pdown_no_p0,
                -1 + tunnel_value,
            ),
            1 - tunnel_value,
        )
        # Limit the upper power envelope (pup_limited):
        # 1. Adjust the 'pup_no_p0' by adding the initial power P0 and applying
        #    the delta_theta_sign. Note the multiplication by -1, which effectively
        #    flips the direction of the change for the upper envelope in this
        #    context.
        # 2. Ensure the resulting signal stays within the global PMin and PMax limits.
        pup_limited = np.minimum(
            np.maximum(
                self._gfm_params.P0 - 1 * delta_theta_sign * pup_no_p0,
                self._gfm_params.PMin,
            ),
            self._gfm_params.PMax,
        )
        return pdown_limited, pup_limited

    def _get_tunnel(self, p_peak_array: list) -> float:
        """
        Calculates a constant "tunnel" value. This value defines a static band
        around the power response. It is determined as the maximum of a fixed
        power component and a component proportional to the peak power (p_peak).

        Parameters
        ----------
        p_peak_array : list
            List of p_peak values, where the first element (`_ORIGINAL_PARAMS_IDX`)
            is assumed to be the nominal p_peak.

        Returns
        -------
        float
            The calculated constant tunnel value.
        """
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]
        # The tunnel value is the greater of a fixed minimum (FinalAllowedTunnelPn)
        # or a value proportional to the peak power (FinalAllowedTunnelVariation *
        # p_peak).
        return max(
            self._gfm_params.FinalAllowedTunnelPn,  # Fixed power component
            self._gfm_params.FinalAllowedTunnelVariation * p_peak,
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
        # Calculate the final magnitude 't_val' of the tunnel. This is similar to
        # how the constant tunnel is calculated in _get_tunnel.
        t_val = max(
            self._gfm_params.FinalAllowedTunnelPn,
            self._gfm_params.FinalAllowedTunnelVariation * p_peak,
        )
        # Calculate the exponential component that defines the tunnel's growth over
        # time. The (time_array - 0.02) term effectively shifts the exponential start,
        # and 0.3 controls the rate of growth.
        tunnel_exp = 1 - np.exp((-time_array + 0.02) / 0.3)
        # Scale the exponential component by the final tunnel value.
        tunnel = t_val * tunnel_exp
        # Ensure that the tunnel value is zero for all time points before the
        # event_time.
        return np.where(time_array < event_time, 0, tunnel)

    def _apply_delay(
        self, delay: float, delayed_value: float, time_array: np.ndarray, signal: np.ndarray
    ) -> np.ndarray:
        """
        Applies a time delay to a given signal. The delay is implemented by prepending
        a constant `delayed_value` for the duration of the `delay` time. The output
        signal is truncated to the original signal's length.

        Parameters
        ----------
        delay : float
            The desired delay time in seconds.
        delayed_value : float
            The constant value to fill the signal during the delay period.
        time_array : np.ndarray
            The time array corresponding to the `signal`. Assumed to have a constant
            time step.
        signal : np.ndarray
            The original signal (waveform) to be delayed.

        Returns
        -------
        np.ndarray
            The delayed signal, which has the same length as the original `signal`.
        """
        if len(time_array) < 2:
            # If there are fewer than 2 time points, a sampling frequency cannot be
            # determined, so return the original signal as no delay can be applied
            # meaningfully.
            return signal
        fs = time_array[1] - time_array[0]  # Calculate the sampling interval (time step).

        # Calculate the number of samples corresponding to the desired delay.
        # Rounding is used to get an integer number of samples.
        delay_samples = int(round(delay / fs))

        if delay_samples >= len(time_array):
            # If the calculated delay in samples is greater than or equal to the
            # length of the original signal, the entire signal will effectively
            # be replaced by the `delayed_value`.
            return np.full_like(signal, delayed_value)

        # Create an array filled with `delayed_value` for the duration of the delay.
        sample = np.full(delay_samples, delayed_value)
        # Concatenate this delay 'prefix' with the original signal.
        # Then, truncate the combined array to the original signal's length,
        # effectively shifting the signal values.
        return np.concatenate((sample, signal))[: len(time_array)]

    def _cut_signal(self, value_min: float, signal: np.ndarray, value_max: float) -> np.ndarray:
        """
        Clips the values of a given signal array to ensure they stay
        within a specified minimum (`value_min`) and maximum (`value_max`) range.
        Values below `value_min` are set to `value_min`, and values above `value_max`
        are set to `value_max`.

        Parameters
        ----------
        value_min : float
            The minimum allowed value for the signal.
        signal : np.ndarray
            The input signal array whose values need to be clipped.
        value_max : float
            The maximum allowed value for the signal.

        Returns
        -------
        np.ndarray
            The signal with its values clipped within the specified limits.
        """
        # Use np.where to efficiently apply the clipping.
        # First, ensure no value is below value_min.
        signal = np.where(signal < value_min, value_min, signal)
        # Second, ensure no value is above value_max.
        signal = np.where(signal > value_max, value_max, signal)
        return signal
