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

from dycov.gfm.parameters import GFM_Params


class PhaseJump:
    """
    Class to calculate the GFM phase jump response.
    This class handles all core calculations for delta_p and power envelopes.
    """

    # Constants for indexing parameter arrays: original, minimum, and maximum values.
    _ORIGINAL_PARAMS_IDX = 0
    _MINIMUM_PARAMS_IDX = 1
    _MAXIMUM_PARAMS_IDX = 2
    # Threshold to differentiate between overdamped and underdamped systems.
    # Critically damped systems are grouped with overdamped.
    _EPSILON_THRESHOLD = 1.0

    def __init__(self, gfm_params: GFM_Params, debug: bool = False):
        """
        Initializes the PhaseJump class with GFM parameters.

        Parameters
        ----------
        gfm_params: GFM_Params
            Parameters for the GFM phase jump calculations.
        """
        self._gfm_params = gfm_params
        self._debug = debug

    def get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> tuple[bool, list, list, list]:
        """
        Calculates the change in power (delta_p) based on damping characteristics.

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
        tuple[bool, list, list, list]
            A tuple containing:
            - is_overdamped: True if the initial system is overdamped, False otherwise.
            - delta_p_array: List of delta_p arrays for original, min, and max parameters.
            - delta_p_min: delta_p array calculated with minimum parameters.
            - delta_p_max: delta_p array calculated with maximum parameters.
            - p_peak_array: List of p_peak values for original, min, and max parameters.
            - epsilon_array: List of epsilon values for original, min, and max parameters.
        """
        x_gr = 1 / self._gfm_params.SCR  # Grid reactance derived from SCR
        x_total_initial = Xeff + x_gr  # Total initial reactance
        # Calculate initial epsilon to determine damping type (overdamped/underdamped).
        epsilon_initial_check = self._calculate_epsilon_initial_check(D, H, x_total_initial)

        # Prepare arrays for D and H parameters, including min and max variations.
        d_array = np.array([D, D * self._gfm_params.RatioMin, D * self._gfm_params.RatioMax])
        h_array = np.array([H, H / self._gfm_params.RatioMin, H / self._gfm_params.RatioMax])

        delta_p_array = []
        p_peak_array = []
        epsilon_array = []

        # Loop through parameter variations to calculate delta_p, p_peak, and epsilon.
        for i in range(len(d_array)):
            delta_p, p_peak, epsilon = self._calculate_delta_p_for_damping(
                d_array[i], h_array[i], Xeff, time_array, event_time, epsilon_initial_check
            )
            delta_p_array.append(delta_p)
            p_peak_array.append(p_peak)
            epsilon_array.append(epsilon)

        # Calculate specific delta_p for min and max parameter cases using the
        # appropriate damping model (overdamped or underdamped).
        if epsilon_initial_check > self._EPSILON_THRESHOLD:
            delta_p_min = self._get_overdamped_delta_p_min(D, H, Xeff, time_array, event_time)
            delta_p_max = self._get_overdamped_delta_p_max(D, H, Xeff, time_array, event_time)
        else:
            delta_p_min = self._get_underdamped_delta_p_min(D, H, Xeff, time_array, event_time)
            delta_p_max = self._get_underdamped_delta_p_max(D, H, Xeff, time_array, event_time)

        if self._debug:
            print(f"DeltaP Nom {delta_p_array[self._ORIGINAL_PARAMS_IDX]}")
            print(f"DeltaP Min {delta_p_array[self._MINIMUM_PARAMS_IDX]}")
            print(f"DeltaP Max {delta_p_array[self._MAXIMUM_PARAMS_IDX]}")
            print(f"P Min {delta_p_min}")
            print(f"P Max {delta_p_max}")

        # Return all calculated delta_p arrays, p_peak, and damping information.
        return (
            epsilon_initial_check > self._EPSILON_THRESHOLD,
            delta_p_array,
            delta_p_min,
            delta_p_max,
            p_peak_array,
            epsilon_array,
        )

    def get_envelopes(
        self,
        delta_p_array: list,
        delta_p_min: np.ndarray,
        delta_p_max: np.ndarray,
        p_peak_array: list,
        time_array: np.array,
        event_time: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates and limits the power envelopes (p_pcc, p_up_final, p_down_final).

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
            - p_pcc_final: The final calculated power at the point of common coupling.
            - p_up_final: The final upper power envelope.
            - p_down_final: The final lower power envelope.
        """
        # Extract the original delta_p and p_peak values.
        delta_p = delta_p_array[self._ORIGINAL_PARAMS_IDX]
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]

        # Calculate the time-dependent tunnel effect.
        tunnel_time_dep = self._get_time_tunnel(
            p_peak=p_peak, time_array=time_array, event_time=event_time
        )

        # Calculate the theoretical power at PCC and limit it by PMin/PMax.
        p_pcc = self._gfm_params.P0 + delta_p * -(
            self._gfm_params.delta_theta / np.abs(self._gfm_params.delta_theta)
        )
        p_pcc = self._cut_signal(self._gfm_params.PMin, p_pcc, self._gfm_params.PMax)

        # Combine all delta_p arrays for envelope calculations.
        list_of_arrays = delta_p_array + [delta_p_min, delta_p_max]

        # Calculate initial unlimited power envelopes.
        pdown_no_p0, pup_no_p0 = self._calculate_unlimited_power_envelopes(
            list_of_arrays, tunnel_time_dep
        )
        if self._debug:
            print(f"Pdown No P0 {pdown_no_p0}")
            print(f"Pup No P0 {pup_no_p0}")

        # Apply final limits to the power envelopes using the static tunnel value.
        pdown_limited, pup_limited = self._limit_power_envelopes(
            pdown_no_p0, pup_no_p0, self._get_tunnel(p_peak_array)
        )
        if self._debug:
            print(f"Pdown Limited {pdown_limited}")
            print(f"Pup Limited {pup_limited}")

        # Apply a delay if EMT simulation flag is true.
        if self._gfm_params.EMT:
            p_up_final = self._apply_delay(0.02, pup_limited[0], time_array, pup_limited)
            p_down_final = self._apply_delay(0.02, pdown_limited[0], time_array, pdown_limited)
            p_pcc_final = self._apply_delay(0.02, p_pcc[0], time_array, p_pcc)
        else:
            p_up_final = pup_limited
            p_down_final = pdown_limited
            p_pcc_final = p_pcc

        # Return the final calculated power signals.
        return p_pcc_final, p_up_final, p_down_final

    def _calculate_common_params(self, D: float, H: float, Xeff: float) -> tuple:
        """
        Calculates common parameters required for delta_p calculations,
        such as total initial reactance, damping ratio (epsilon),
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
        x_gr = 1 / self._gfm_params.SCR  # Grid reactance.
        x_total_initial = Xeff + x_gr  # Sum of reactances.
        u_prod = self._gfm_params.Ucv * self._gfm_params.Ugr  # Product of voltages.

        # Calculate damping ratio (epsilon).
        epsilon = D / 2 * np.sqrt(x_total_initial / (2 * H * self._gfm_params.Wb * u_prod))
        # Calculate natural frequency (wn).
        wn = np.sqrt(self._gfm_params.Wb * u_prod / (2 * H * x_total_initial))

        # Convert delta_theta to radians and calculate peak power.
        delta_theta_rad = np.abs(self._gfm_params.delta_theta * np.pi / 180)
        p_peak_calc = delta_theta_rad * u_prod / x_total_initial

        return x_total_initial, epsilon, wn, p_peak_calc

    def _calculate_epsilon_initial_check(
        self, D: float, H: float, x_total_initial: float
    ) -> float:
        """
        Calculates the initial damping ratio (epsilon) to determine
        whether the system's response is overdamped or underdamped.

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
        appropriate method based on whether the system is overdamped or
        underdamped.

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
            The pre-calculated initial damping ratio to determine damping type.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing:
            - delta_p: The delta_p array for the system.
            - p_peak: The peak power.
            - epsilon: The damping ratio.
        """
        if epsilon_initial_check > self._EPSILON_THRESHOLD:
            # Call method for overdamped system.
            return self._get_overdamped_delta_p(D, H, Xeff, time_array, event_time)
        else:
            # Call method for underdamped system.
            return self._get_underdamped_delta_p(D, H, Xeff, time_array, event_time)

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.array
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the base delta_p waveform and related parameters for
        an overdamped system, before applying event time or margins.

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
        _, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)
        wd = wn * np.sqrt(epsilon**2 - 1)  # Damped natural frequency for overdamped.

        alpha = epsilon * wn + wd  # Root 1
        beta = epsilon * wn - wd  # Root 2

        A = 1 / (beta - alpha)  # Coefficient A
        B = -A  # Coefficient B

        # Calculate individual terms for delta_p1 based on overdamped response.
        term1 = 2 * H * A * (1 - alpha * np.exp(-alpha * time_array))
        term2 = 2 * H * B * (1 - beta * np.exp(-beta * time_array))
        term3 = D * A * np.exp(-alpha * time_array)
        term4 = D * B * np.exp(-beta * time_array)

        # Combine terms to get the base delta_p1.
        delta_p1 = (p_peak / (2 * H)) * (term1 + term2 + term3 + term4)
        return delta_p1, p_peak, epsilon

    def _get_overdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates delta_p, p_peak, and epsilon for an overdamped system,
        setting pre-event values to zero.

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
            - delta_p: The delta_p array for the overdamped system.
            - p_peak: The peak power.
            - epsilon: The damping ratio.
        """
        # Get the base delta_p waveform, p_peak, and epsilon.
        delta_p1, p_peak, epsilon = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        # Set delta_p to 0 before the event time.
        delta_p = np.where(time_array < event_time, 0, delta_p1)
        return delta_p, p_peak, epsilon

    def _get_overdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> np.ndarray:
        """
        Calculates the minimum delta_p for an overdamped system, applying
        the lower margin and setting pre-event values to zero.

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
        # Get the base delta_p waveform.
        delta_p1, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        # Apply the lower margin.
        delta_p1_margined = (1 + self._gfm_params.MarginLow) * delta_p1
        # Set delta_p to 0 before the event time.
        delta_p = np.where(time_array < event_time, 0, delta_p1_margined)
        return delta_p

    def _get_overdamped_delta_p_max(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> np.ndarray:
        """
        Calculates the maximum delta_p for an overdamped system, applying
        the upper margin, an additional delay, and setting pre-event
        values to zero.

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
        # Get the base delta_p waveform.
        delta_p1, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        # Apply the upper margin.
        delta_p1_margined = self._gfm_params.MarginHigh * delta_p1
        # Apply a small delay to the margined delta_p.
        delta_p1_delayed = self._apply_delay(0.01, 0, time_array, delta_p1_margined)
        # Set delta_p to 0 before the event time.
        delta_p = np.where(time_array < event_time, 0, delta_p1_delayed)
        return delta_p

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.array
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the base delta_p waveform and related parameters for
        an underdamped system, before applying event time or margins.

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
        _, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)
        wd = wn * np.sqrt(1 - epsilon**2)  # Damped natural frequency for underdamped.

        # Calculate individual terms for delta_p1 based on underdamped response.
        term1 = np.exp(-epsilon * wn * time_array)
        term2 = np.cos(wd * time_array)
        term3 = np.sin(wd * time_array)

        # Combine terms to get the base delta_p1.
        delta_p1 = term1 * (term2 - (epsilon * wn - 1) / wd * term3) * p_peak
        return delta_p1, p_peak, epsilon

    def _get_underdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates delta_p, p_peak, and epsilon for an underdamped system,
        setting pre-event values to zero.

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
            - delta_p: The delta_p array for the system.
            - p_peak: The peak power.
            - epsilon: The damping ratio.
        """
        # Get the base delta_p waveform, p_peak, and epsilon.
        delta_p1, p_peak, epsilon = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        # Set delta_p to 0 before the event time.
        delta_p = np.where(time_array < event_time, 0, delta_p1)
        return delta_p, p_peak, epsilon

    def _get_underdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> np.ndarray:
        """
        Calculates the minimum delta_p for an underdamped system, applying
        the lower margin and setting pre-event values to zero.

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
        _, p_peak, _ = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        sigma = D / (4 * H)  # Decay rate.
        # Apply lower margin and exponential decay.
        delta_p_margined = p_peak * (1 - self._gfm_params.MarginLow) * np.exp(-sigma * time_array)
        # Apply a small delay.
        delta_p_delayed = self._apply_delay(0.01, 0, time_array, delta_p_margined)
        # Set delta_p to 0 before the event time.
        delta_p = np.where(time_array < event_time, 0, delta_p_delayed)
        return delta_p

    def _get_underdamped_delta_p_max(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> np.ndarray:
        """
        Calculates the maximum delta_p for an underdamped system, applying
        the upper margin and setting pre-event values to zero.

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
        delta_p1, p_peak, _ = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        sigma = D / (4 * H)  # Decay rate.
        # Apply upper margin and exponential decay.
        delta_p_margined = p_peak * (1 + self._gfm_params.MarginHigh) * np.exp(-sigma * time_array)
        # Apply a small delay.
        delta_p_delayed = self._apply_delay(
            0.01, delta_p_margined[0], time_array, delta_p_margined
        )
        # Set delta_p to 0 before the event time.
        delta_p = np.where(time_array < event_time, 0, delta_p_delayed)
        return delta_p

    def _calculate_unlimited_power_envelopes(
        self, list_of_arrays: list[np.ndarray], tunnel: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculates the unlimited power down and power up envelopes by
        finding the minimum and maximum across various delta_p arrays
        and adjusting by the time-dependent tunnel.

        Parameters
        ----------
        list_of_arrays : list[np.ndarray]
            A list of delta_p arrays to be used for min/max reduction.
        tunnel : np.ndarray
            The time-dependent tunnel response array.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing:
            - pdown_no_p0: Unlimited power down without initial power (P0).
            - pup_no_p0: Unlimited power up without initial power (P0).
        """
        # Calculate the lower envelope by taking the minimum of all delta_p arrays
        # and subtracting the tunnel.
        pdown_no_p0 = np.minimum.reduce(list_of_arrays) - tunnel
        # Calculate the upper envelope by taking the maximum of all delta_p arrays
        # and adding the tunnel.
        pup_no_p0 = np.maximum.reduce(list_of_arrays) + tunnel
        return pdown_no_p0, pup_no_p0

    def _limit_power_envelopes(
        self,
        pdown_no_p0: np.ndarray,
        pup_no_p0: np.ndarray,
        tunnel_value: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Applies final operational limits to the power down and power up
        envelopes, incorporating the initial power (P0) and a constant
        tunnel value.

        Parameters
        ----------
        pdown_no_p0 : np.ndarray
            Unlimited power down signal, not yet adjusted by P0.
        pup_no_p0 : np.ndarray
            Unlimited power up signal, not yet adjusted by P0.
        tunnel_value : float
            The constant tunnel value used for final limiting.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing:
            - pdown_limited: Limited power down envelope.
            - pup_limited: Limited power up envelope.
        """
        # Determine the sign of delta_theta for directional limiting.
        delta_theta_sign = 1 if self._gfm_params.delta_theta > 0 else -1

        # Limit the lower envelope:
        # 1. Adjust by P0 and delta_theta_sign.
        # 2. Ensure it stays within [-1 + tunnel_value, 1 - tunnel_value].
        pdown_limited = np.minimum(
            np.maximum(
                self._gfm_params.P0 - delta_theta_sign * pdown_no_p0,
                -1 + tunnel_value,
            ),
            1 - tunnel_value,
        )
        # Limit the upper envelope:
        # 1. Adjust by P0 and delta_theta_sign.
        # 2. Ensure it stays within [PMin, PMax].
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
        Calculates a constant "tunnel" value, which defines a band
        around the power response. The value is the maximum of a fixed
        power value and a variation proportional to p_peak.

        Parameters
        ----------
        p_peak_array : list
            List of p_peak values, where the first element is the original p_peak.

        Returns
        -------
        float
            The calculated constant tunnel value.
        """
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]
        return max(
            self._gfm_params.FinalAllowedTunnelPn,  # Fixed power component
            self._gfm_params.FinalAllowedTunnelVariation * p_peak,  # Proportional
        )

    def _get_time_tunnel(
        self, p_peak: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Calculates a time-dependent "tunnel" array, which represents
        a dynamic band around the power response that expands over time.

        Parameters
        ----------
        p_peak : float
            The peak power value, used to determine the final tunnel magnitude.
        time_array : np.ndarray
            The array of time points for the simulation.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The time-dependent tunnel array, which starts at zero before
            the event and increases exponentially afterwards.
        """
        # Calculate the final magnitude 't_val' of the tunnel, similar to _get_tunnel.
        t_val = max(
            self._gfm_params.FinalAllowedTunnelPn,
            self._gfm_params.FinalAllowedTunnelVariation * p_peak,
        )
        # Calculate the exponential decay for the tunnel shape.
        tunnel_exp = 1 - np.exp((-time_array + 0.02) / 0.3)
        tunnel = t_val * tunnel_exp
        # Ensure the tunnel is zero before the event_time.
        return np.where(time_array < event_time, 0, tunnel)

    def _apply_delay(
        self, delay: float, delayed_value: float, time_array: np.ndarray, signal: np.ndarray
    ) -> np.ndarray:
        """
        Applies a time delay to a given signal by prepending a constant
        `delayed_value` for the duration of the `delay`.

        Parameters
        ----------
        delay : float
            The delay time in seconds.
        delayed_value : float
            The constant value to fill the signal during the delay period.
        time_array : np.ndarray
            The time array corresponding to the signal.
        signal : np.ndarray
            The original signal to be delayed.

        Returns
        -------
        np.ndarray
            The delayed signal, truncated to the original signal length.
        """
        if len(time_array) < 2:
            return signal  # Cannot calculate sampling frequency if only one or no point.
        fs = time_array[1] - time_array[0]  # Assume constant time step (sampling freq).

        # Calculate the number of samples corresponding to the delay.
        delay_samples = int(round(delay / fs))

        if delay_samples >= len(time_array):
            # If delay is greater than or equal to signal length,
            # the entire signal becomes the delayed value.
            return np.full_like(signal, delayed_value)

        # Create an array of `delayed_value` for the delay duration.
        sample = np.full(delay_samples, delayed_value)
        # Concatenate the delay samples with the original signal and
        # truncate to the original length.
        return np.concatenate((sample, signal))[: len(time_array)]

    def _cut_signal(self, value_min: float, signal: np.ndarray, value_max: float) -> np.ndarray:
        """
        Clips the values of a given signal array to ensure they stay
        within a specified minimum and maximum range.

        Parameters
        ----------
        value_min : float
            The minimum allowed value for the signal.
        signal : np.ndarray
            The input signal array.
        value_max : float
            The maximum allowed value for the signal.

        Returns
        -------
        np.ndarray
            The signal with values clipped within the specified limits.
        """
        # Replace values below value_min with value_min.
        signal = np.where(signal < value_min, value_min, signal)
        # Replace values above value_max with value_max.
        signal = np.where(signal > value_max, value_max, signal)
        return signal
