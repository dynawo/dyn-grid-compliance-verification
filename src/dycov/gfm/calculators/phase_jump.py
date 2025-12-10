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


class PhaseJump(GFMCalculator):
    """
    Class to calculate the GFM phase jump response.

    This class handles all core calculations for delta_p and active power
    envelopes, differentiating between overdamped and underdamped system
    responses.
    """

    def __init__(
        self,
        gfm_params: GFMParameters,
    ) -> None:
        """
        Initializes the PhaseJump calculator with GFM parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            An object containing all necessary parameters for GFM calculations.
        """
        super().__init__(gfm_params=gfm_params)
        self._delta_phase = gfm_params.get_delta_phase()
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()

    def get_plot_parameter_names(self) -> list[str]:
        """Returns the list of parameter names relevant for PhaseJump plots."""
        return ["P0", "Q0", "DeltaPhase", "AngleStepAtPDR", "SCR", "Xeff", "D", "H", "Epsilon"]

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the change in power (delta_p) and active power envelopes
        (PCC, upper, and lower) for a phase jump event.

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
            - magnitude_name: The name of the calculated magnitude ("P").
            - pcc_signal: The final calculated active power at the PCC.
            - upper_envelope: The final upper active power envelope.
            - lower_envelope: The final lower active power envelope.
        """
        logger = dycov_logging.get_logger("PhaseJump")
        logger.debug(f"Input Params D={D} H={H} Xeff {Xeff}")
        logger.debug(
            f"Input Params ΔPhase={self._delta_phase} "
            f"SCR={self._scr} "
            f"P0={self._initial_active_power} "
            f"PMin={self._min_active_power} "
            f"PMax={self._max_active_power}"
        )

        # Store validation values for INI dump
        self._d_val = D
        self._h_val = H
        _, self._epsilon, _, _ = self._calculate_common_params(D, H, Xeff)

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
        )

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
    ) -> tuple[list[np.ndarray], np.ndarray, np.ndarray, list[float], list[float]]:
        """
        Calculates delta_p and related parameters based on damping,
        considering nominal, minimum, and maximum parameter variations.

        Parameters
        ----------
        D : float
            Nominal damping factor.
        H : float
            Nominal inertia constant.
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Array of time points for simulation.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        tuple[list[np.ndarray], np.ndarray, np.ndarray, list[float], list[float]]
            A tuple with delta_p variations, min/max delta_p, peak powers,
            and epsilon values.
        """
        x_gr = 1 / self._scr
        x_total_initial = Xeff + x_gr

        d_array = np.array([D, D * self._min_ratio, D * self._max_ratio])
        h_array = np.array([H, H * self._min_ratio, H * self._max_ratio])

        epsilon_initial_check = self._calculate_epsilon_initial_check(
            d_array, h_array, x_total_initial
        )
        dycov_logging.get_logger("PhaseJump").debug(f"Epsilon={epsilon_initial_check}")

        delta_p_array: list[np.ndarray] = []
        p_peak_array: list[float] = []
        epsilon_array: list[float] = []

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

        self._d_vals = d_array
        self._h_vals = h_array
        self._epsilon_vals = np.array(epsilon_array)

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
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates and limits the final active power envelopes (PCC power,
        upper envelope, lower envelope).

        Parameters
        ----------
        delta_p_array : list[np.ndarray]
            List of delta_p arrays for parameter variations.
        delta_p_min : np.ndarray
            Specific delta_p array for the minimum case.
        delta_p_max : np.ndarray
            Specific delta_p array for the maximum case.
        p_peak_array : list[float]
            List of peak power values.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple with the PCC signal, upper envelope, and lower envelope.
        """
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
            A tuple with total reactance, epsilon, natural frequency, and peak power.
        """
        x_gr = 1 / self._scr
        x_total_initial = Xeff + x_gr
        u_prod = self._initial_voltage * self._grid_voltage

        epsilon = (
            D / 2 * np.sqrt(x_total_initial / (2 * H * self._base_angular_frequency * u_prod))
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
        """
        Dispatches the delta_p calculation to the appropriate method based on
        whether the system is determined to be overdamped or underdamped.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.
        epsilon_initial_check : float
            The pre-calculated damping ratio to determine the damping type.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple with delta_p, peak power, and epsilon.
        """
        if epsilon_initial_check > self._EPSILON_THRESHOLD:
            return self._get_overdamped_delta_p(D, H, Xeff, time_array, event_time)
        else:
            return self._get_underdamped_delta_p(D, H, Xeff, time_array, event_time)

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the fundamental delta_p waveform for an overdamped system
        response (raw dynamic behavior).

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Array of time points.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple with the base delta_p waveform, peak power, and epsilon.
        """
        _, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)
        wd = wn * np.sqrt(epsilon**2 - 1)

        alpha = epsilon * wn + wd
        beta = epsilon * wn - wd

        A = 1 / (beta - alpha)
        B = -A

        term1 = 2 * H * A * (1 - alpha * np.exp(-alpha * time_array))
        term2 = 2 * H * B * (1 - beta * np.exp(-beta * time_array))
        term3 = D * A * np.exp(-alpha * time_array)
        term4 = D * B * np.exp(-beta * time_array)

        delta_p1 = (p_peak / (2 * H)) * (term1 + term2 + term3 + term4)
        return delta_p1, p_peak, epsilon

    def _get_overdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates delta_p for an overdamped system, ensuring values are zero
        before the specified event time.

        Parameters
        ----------
        D : float, H: float, Xeff: float
            System parameters.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple with the final delta_p, peak power, and epsilon.
        """
        delta_p1, p_peak, epsilon = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p = np.where(time_array < event_time, 0, delta_p1)
        return delta_p, p_peak, epsilon

    def _get_overdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Calculates the minimum delta_p for an overdamped system, applying
        a lower margin.

        Parameters
        ----------
        D : float, H: float, Xeff: float
            System parameters.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The minimum delta_p array for the overdamped system.
        """
        delta_p1, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p1_margined = (1 + self._margin_low) * delta_p1
        delta_p = np.where(time_array < event_time, 0, delta_p1_margined)
        return delta_p

    def _get_overdamped_delta_p_max(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Calculates the maximum delta_p for an overdamped system, applying
        an upper margin and an additional delay.

        Parameters
        ----------
        D : float, H: float, Xeff: float
            System parameters.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The maximum delta_p array for the overdamped system.
        """
        delta_p, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p_margined = self._margin_high * delta_p
        delta_p_delayed = self._apply_delay(
            constants.OVERDAMPED_MAX_DELAY_S, 0, time_array, delta_p_margined
        )
        delta_p = np.where(time_array < event_time, 0, delta_p_delayed)
        return delta_p

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the fundamental delta_p waveform for an underdamped system
        response (raw dynamic behavior including oscillations).

        Parameters
        ----------
        D : float, H: float, Xeff: float
            System parameters.
        time_array : np.ndarray
            Array of time points.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple with the base delta_p waveform, peak power, and epsilon.
        """
        _, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)
        wd = wn * np.sqrt(1 - epsilon**2)

        term1 = np.exp(-epsilon * wn * time_array)
        term2 = np.cos(wd * time_array)
        term3 = np.sin(wd * time_array)

        delta_p1 = term1 * (term2 - (epsilon * wn - 1) / wd * term3) * p_peak
        return delta_p1, p_peak, epsilon

    def _get_underdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates delta_p for an underdamped system, ensuring values are zero
        before the specified event time.

        Parameters
        ----------
        D : float, H: float, Xeff: float
            System parameters.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple with the final delta_p, peak power, and epsilon.
        """
        delta_p1, p_peak, epsilon = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p = np.where(time_array < event_time, 0, delta_p1)
        return delta_p, p_peak, epsilon

    def _get_underdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Calculates the minimum delta_p for an underdamped system, applying
        a lower margin and an exponential decay.

        Parameters
        ----------
        D : float, H: float, Xeff: float
            System parameters.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The minimum delta_p array for the underdamped system.
        """
        _, p_peak, _ = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        sigma = D / (4 * H)
        delta_p_margined = p_peak * (1 - self._margin_low) * np.exp(-sigma * time_array)
        delta_p_delayed = self._apply_delay(
            constants.UNDERDAMPED_MIN_DELAY_S, 0, time_array, delta_p_margined
        )
        delta_p = np.where(time_array < event_time, 0, delta_p_delayed)
        return delta_p

    def _get_underdamped_delta_p_max(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Calculates the maximum delta_p for an underdamped system, applying
        an upper margin and an exponential decay.

        Parameters
        ----------
        D : float, H: float, Xeff: float
            System parameters.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The maximum delta_p array for the underdamped system.
        """
        _, p_peak, _ = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        sigma = D / (4 * H)
        delta_p_margined = p_peak * (1 + self._margin_high) * np.exp(-sigma * time_array)
        delta_p_delayed = self._apply_delay(
            constants.UNDERDAMPED_MAX_DELAY_S, delta_p_margined[0], time_array, delta_p_margined
        )
        delta_p = np.where(time_array < event_time, 0, delta_p_delayed)
        return delta_p

    def _get_tunnel(self, p_peak_array: list[float]) -> float:
        """
        Calculates a constant "tunnel" value.

        This value defines a static band around the power response.

        Parameters
        ----------
        p_peak_array : list[float]
            List of p_peak values, where the first element is the nominal p_peak.

        Returns
        -------
        float
            The calculated constant tunnel value.
        """
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]
        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * p_peak,
        )
