#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from typing import Optional
import numpy as np

from dycov.gfm import constants
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.parameters import GFMParameters
from dycov.logging import dycov_logging

logger = dycov_logging.get_logger(__name__)


class SCRJump(GFMCalculator):
    """Handles the GFM response to a Short-Circuit Ratio (SCR) jump."""

    def __init__(self, gfm_params: GFMParameters) -> None:
        """Initializes the SCRJump calculator.

        Args:
            gfm_params (GFMParameters): The shared configuration parameters.
        """
        super().__init__(gfm_params=gfm_params)
        initial_scr = gfm_params.get_initial_scr()
        self._final_scr = gfm_params.get_final_scr()
        self._delta_impedance = 1 / self._final_scr - 1 / initial_scr
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()
        self._base_angular_frequency = gfm_params.get_base_angular_frequency()
        self._initial_voltage = gfm_params.get_initial_voltage()
        self._grid_voltage = gfm_params.get_grid_voltage()
        self._final_allowed_tunnel_pn = gfm_params.get_final_allowed_tunnel_pn()
        self._final_allowed_tunnel_variation = gfm_params.get_final_allowed_tunnel_variation()
        self._pmax_mois_tunnel = gfm_params.get_pmax_mois_tunnel()
        self._pmin_mois_tunnel = gfm_params.get_pmin_mois_tunnel()
        self._is_inconsistent = False
        self._disclaimer_message: Optional[str] = None

    def get_plot_parameter_names(self) -> list[str]:
        """Retrieves parameters relevant for rendering SCRJump plots.

        Returns:
            list[str]: A list of parameter names to be displayed.
        """
        return ["P0", "Q0", "SCRinitial", "SCRfinal", "Xeff", "D", "H", "Epsilon"]

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """Calculates the active power deviation and bounding envelopes.

        Args:
            D (float): The damping constant.
            H (float): The inertia constant.
            Xeff (float): The effective reactance.
            time_array (np.ndarray): The simulation time vector.
            event_time (float): The timestamp when the grid event occurs.

        Returns:
            tuple[str, np.ndarray, np.ndarray, np.ndarray]: A tuple containing the
                magnitude name ("Ip"), the main power signal, upper envelope, and lower envelope.
        """
        logger.debug(f"Input Params D={D} H={H} Xeff {Xeff}")

        delta_p_results, min_envelope_results, max_envelope_results, peak_power_results, _ = (
            self._get_delta_p(D=D, H=H, Xeff=Xeff, time_array=time_array, event_time=event_time)
        )

        power_at_pcc, upper_envelope, lower_envelope = self._get_envelopes(
            delta_p_array=delta_p_results,
            delta_p_min_env_array=min_envelope_results,
            delta_p_max_env_array=max_envelope_results,
            p_peak_array=peak_power_results,
            time_array=time_array,
            event_time=event_time,
        )

        magnitude_name = "Ip"
        return magnitude_name, power_at_pcc, upper_envelope, lower_envelope

    def _get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Computes the delta_p sequences defining system damping behavior.

        Args:
            D (float): The base damping constant.
            H (float): The base inertia constant.
            Xeff (float): The effective reactance.
            time_array (np.ndarray): The simulation time vector.
            event_time (float): The timestamp of the event.

        Returns:
            tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]: A tuple with
                delta_p arrays, min envelope arrays, max envelope arrays, peak powers, and epsilon values.
        """
        damping_variations = np.array([D, D * self._max_ratio, D * self._min_ratio])
        inertia_variations = np.array([H, H * self._min_ratio, H * self._max_ratio])
        num_variations = len(damping_variations)
        num_time_points = len(time_array)

        delta_p_results = np.zeros((num_variations, num_time_points))
        min_envelope_results = np.full((num_variations, num_time_points), np.nan)
        max_envelope_results = np.full((num_variations, num_time_points), np.nan)
        peak_power_results = np.zeros(num_variations)
        epsilon_results = np.zeros(num_variations)

        for i in range(num_variations):
            delta_p, delta_p_min, delta_p_max, p_peak, epsilon = (
                self._calculate_delta_p_for_damping(
                    damping_variations[i], inertia_variations[i], Xeff, time_array, event_time
                )
            )
            delta_p_results[i, :] = delta_p
            peak_power_results[i] = p_peak
            epsilon_results[i] = epsilon

            if delta_p_min is not None:
                min_envelope_results[i, :] = delta_p_min
            if delta_p_max is not None:
                max_envelope_results[i, :] = delta_p_max

        self._d_vals = damping_variations
        self._h_vals = inertia_variations
        self._epsilon_vals = epsilon_results

        is_overdamped = epsilon_results >= 1
        if not np.all(is_overdamped == is_overdamped[0]):
            eps_str = np.array2string(epsilon_results, precision=2)
            d_str = np.array2string(damping_variations, precision=2)
            h_str = np.array2string(inertia_variations, precision=2)
            msg = (
                f"Inconsistent damping behavior across parameter variations.\n"
                f"Epsilon values: {eps_str}.\n"
                f"Is Overdamped (>=1): {is_overdamped}.\n"
                f"D values: {d_str}. H values: {h_str}.\n"
                f"Variations must maintain the same damping type."
            )
            logger.warning(msg)
            self._is_inconsistent = True
            self._disclaimer_message = msg

        return (
            delta_p_results,
            min_envelope_results,
            max_envelope_results,
            peak_power_results,
            epsilon_results,
        )

    def _modify_envelope(
        self,
        envelope_signal: np.ndarray,
        power_at_50_percent: np.ndarray,
        time_array: np.ndarray,
        event_time: float,
    ) -> np.ndarray:
        """Anchors an envelope to 50% of the expected power change during the initial window.

        Args:
            envelope_signal (np.ndarray): The raw envelope signal array.
            power_at_50_percent (np.ndarray): The targeted 50% power threshold array.
            time_array (np.ndarray): The simulation time vector.
            event_time (float): The timestamp of the event.

        Returns:
            np.ndarray: The modified envelope signal.
        """
        modification_mask = (time_array >= event_time) & (
            time_array <= event_time + constants.SCRJUMP_MODIFY_ENVELOPE_S
        )
        modified_signal = np.where(modification_mask, power_at_50_percent, envelope_signal)
        modified_signal = np.where(
            modified_signal * modification_mask < self._min_active_power,
            self._min_active_power + 0.2,
            modified_signal,
        )
        modified_signal = np.where(
            modified_signal * modification_mask > self._max_active_power,
            self._max_active_power - 0.2,
            modified_signal,
        )
        return modified_signal

    def _get_envelope_traces(
        self,
        delta_p: np.ndarray,
        time_array: np.ndarray,
        event_time: float,
        tunnel_value: float,
        is_overdamped: bool,
        delta_p_at_event: float,
        delta_p_base: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Synthesizes upper and lower boundary traces from a delta_p waveform.

        Args:
            delta_p (np.ndarray): The specific delta_p waveform.
            time_array (np.ndarray): The simulation time vector.
            event_time (float): The timestamp of the event.
            tunnel_value (float): The static tolerance margin limit.
            is_overdamped (bool): Flag indicating if the system is overdamped.
            delta_p_at_event (float): The power change value at the moment of the event.
            delta_p_base (np.ndarray): The nominal baseline power change.

        Returns:
            tuple[np.ndarray, np.ndarray]: The upper and lower trace arrays.
        """
        if delta_p_at_event > 0:
            upper_trace = (
                self._initial_active_power + delta_p * (1 + self._margin_high) + tunnel_value
            )
            lower_trace = (
                self._initial_active_power + delta_p * (1 - self._margin_low) - tunnel_value
            )
            power_at_50_percent = self._initial_active_power + np.where(
                time_array >= event_time, delta_p_base * 0.5 + 0.005, delta_p
            )
            time_mask = (time_array >= event_time) & (time_array <= constants.SIMULATION_END_TIME)
            condition = time_mask & (lower_trace > self._pmax_mois_tunnel)
            lower_trace = self._modify_envelope(
                lower_trace, power_at_50_percent, time_array, event_time
            )
            lower_trace = np.where(condition, self._pmax_mois_tunnel, lower_trace)
        else:
            upper_trace = (
                self._initial_active_power + delta_p * (1 - self._margin_high) + tunnel_value
            )
            lower_trace = (
                self._initial_active_power + delta_p * (1 + self._margin_low) - tunnel_value
            )
            power_at_50_percent = self._initial_active_power + np.where(
                time_array >= event_time, delta_p_base * 0.5 + 0.005, delta_p
            )
            time_mask = (time_array >= event_time) & (time_array <= constants.SIMULATION_END_TIME)
            condition = time_mask & (upper_trace < self._pmin_mois_tunnel)
            upper_trace = self._modify_envelope(
                upper_trace, power_at_50_percent, time_array, event_time
            )
            upper_trace = np.where(condition, self._pmin_mois_tunnel, upper_trace)

        return self._limit_signal(upper_trace), self._limit_signal(lower_trace)

    def _apply_initial_limiting(
        self,
        upper_envelope: np.ndarray,
        lower_envelope: np.ndarray,
        delta_p_nominal: np.ndarray,
        time_array: np.ndarray,
        event_time: float,
        tunnel_value: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Enforces a strict limitation protocol over the initial transient period.

        Args:
            upper_envelope (np.ndarray): The upper envelope array.
            lower_envelope (np.ndarray): The lower envelope array.
            delta_p_nominal (np.ndarray): The nominal power deviation array.
            time_array (np.ndarray): The simulation time vector.
            event_time (float): The timestamp of the event.
            tunnel_value (float): The static tolerance margin limit.

        Returns:
            tuple[np.ndarray, np.ndarray]: The constrained upper and lower envelope arrays.
        """
        event_index = np.searchsorted(time_array, event_time + 0.01, side="right")
        delta_p_at_event = (
            delta_p_nominal[event_index] if event_index < len(delta_p_nominal) else 0
        )
        limit_mask = (time_array >= event_time) & (
            time_array <= event_time + constants.SCRJUMP_INITIAL_LIMITING_S
        )

        if delta_p_at_event > 0:
            limit_condition = limit_mask & (
                lower_envelope < (self._initial_active_power - tunnel_value)
            )
            lower_envelope = np.where(
                limit_condition, self._initial_active_power - tunnel_value, lower_envelope
            )
        else:
            limit_condition = limit_mask & (
                upper_envelope > (self._initial_active_power + tunnel_value)
            )
            upper_envelope = np.where(
                limit_condition, self._initial_active_power + tunnel_value, upper_envelope
            )
        return upper_envelope, lower_envelope

    def _limit_signal(self, signal: np.ndarray) -> np.ndarray:
        """Utility function to enforce absolute active power hardware limits.

        Args:
            signal (np.ndarray): The array to be constrained.

        Returns:
            np.ndarray: The limited signal array.
        """
        return np.clip(signal, self._min_active_power, self._max_active_power)

    def _get_envelopes(
        self,
        delta_p_array: np.ndarray,
        delta_p_min_env_array: np.ndarray,
        delta_p_max_env_array: np.ndarray,
        p_peak_array: np.ndarray,
        time_array: np.ndarray,
        event_time: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Constructs active power envelopes by evaluating and merging traces.

        Args:
            delta_p_array (np.ndarray): Array containing power deviation trajectories.
            delta_p_min_env_array (np.ndarray): Array of lower boundaries for underdamped cases.
            delta_p_max_env_array (np.ndarray): Array of upper boundaries for underdamped cases.
            p_peak_array (np.ndarray): Array of peak power deviations.
            time_array (np.ndarray): The simulation time vector.
            event_time (float): The timestamp of the event.

        Returns:
            tuple[np.ndarray, np.ndarray, np.ndarray]: A tuple with the primary power trace,
                upper envelope, and lower envelope.
        """
        upper_trace_candidates = []
        lower_trace_candidates = []
        upper_traces_from_max_env = []
        lower_traces_from_max_env = []
        upper_traces_from_min_env = []
        lower_traces_from_min_env = []

        delta_p_nominal = delta_p_array[0, :]
        event_index = np.searchsorted(time_array, event_time, side="right")
        delta_p_at_event = (
            delta_p_nominal[event_index] if event_index < len(delta_p_nominal) else 0
        )

        for i in range(delta_p_array.shape[0]):
            current_delta_p = delta_p_array[i, :]
            current_peak_power = p_peak_array[i]
            tunnel_value = self._get_tunnel(current_peak_power)

            upper_trace, lower_trace = self._get_envelope_traces(
                delta_p=current_delta_p,
                time_array=time_array,
                event_time=event_time,
                tunnel_value=tunnel_value,
                is_overdamped=np.isnan(delta_p_min_env_array[i, 0]),
                delta_p_at_event=delta_p_at_event,
                delta_p_base=delta_p_nominal,
            )
            upper_trace_candidates.append(upper_trace)
            lower_trace_candidates.append(lower_trace)

            if not np.isnan(delta_p_max_env_array[i, 0]):
                upper_from_max, lower_from_max = self._get_envelope_traces(
                    delta_p=delta_p_max_env_array[i, :],
                    time_array=time_array,
                    event_time=event_time,
                    tunnel_value=tunnel_value,
                    is_overdamped=np.isnan(delta_p_max_env_array[i, 0]),
                    delta_p_at_event=delta_p_at_event,
                    delta_p_base=delta_p_nominal,
                )
                upper_traces_from_max_env.append(upper_from_max)
                lower_traces_from_max_env.append(lower_from_max)

            if not np.isnan(delta_p_min_env_array[i, 0]):
                upper_from_min, lower_from_min = self._get_envelope_traces(
                    delta_p=delta_p_min_env_array[i, :],
                    time_array=time_array,
                    event_time=event_time,
                    tunnel_value=tunnel_value,
                    is_overdamped=np.isnan(delta_p_min_env_array[i, 0]),
                    delta_p_at_event=delta_p_at_event,
                    delta_p_base=delta_p_nominal,
                )
                upper_traces_from_min_env.append(upper_from_min)
                lower_traces_from_min_env.append(lower_from_min)

        power_at_pcc = self._limit_signal(self._initial_active_power + delta_p_nominal)
        power_at_50_percent = self._limit_signal(
            self._initial_active_power
            + np.where(time_array >= time_array[0], current_delta_p * 0.5, current_delta_p)
        )

        if np.isnan(delta_p_max_env_array[i, 0]):
            upper_matrix = np.vstack(upper_trace_candidates)
            combined_upper_envelope = np.nanmax(upper_matrix, axis=0)
        else:
            upper_matrix = np.vstack(
                (upper_trace_candidates, [power_at_50_percent], upper_traces_from_max_env)
            )
            combined_upper_envelope = np.nanmax(upper_matrix, axis=0)

        if np.isnan(delta_p_min_env_array[i, 0]):
            lower_matrix = np.vstack(lower_trace_candidates)
        else:
            lower_matrix = np.vstack(
                (lower_trace_candidates, [power_at_50_percent], lower_traces_from_min_env)
            )
        combined_lower_envelope = np.nanmin(lower_matrix, axis=0)

        upper_envelope = combined_upper_envelope
        lower_envelope = combined_lower_envelope

        if (self._initial_active_power > 0 and delta_p_at_event > 0) or (
            self._initial_active_power < 0 and delta_p_at_event > 0
        ):
            if self._is_emt_flag:
                initial_upper_val = (
                    np.max(upper_envelope) if not np.isscalar(upper_envelope) else upper_envelope
                )
                initial_lower_val = (
                    lower_envelope[0] if not np.isscalar(lower_envelope) else lower_envelope
                )
                initial_pcc_val = (
                    np.max(power_at_pcc) if not np.isscalar(power_at_pcc) else power_at_pcc
                )
                upper_envelope = self._apply_delay(
                    self._emt_delay, initial_upper_val, time_array, upper_envelope
                )
                lower_envelope = self._apply_delay(
                    self._emt_delay + constants.SCR_BOUND_DELAY_S,
                    initial_lower_val,
                    time_array,
                    lower_envelope,
                )
                power_at_pcc = self._apply_delay(
                    self._emt_delay, initial_pcc_val, time_array, power_at_pcc
                )
            else:
                initial_lower_val = (
                    lower_envelope[0] if not np.isscalar(lower_envelope) else lower_envelope
                )
                lower_envelope = self._apply_delay(
                    constants.SCR_BOUND_DELAY_S, initial_lower_val, time_array, lower_envelope
                )
        else:
            if self._is_emt_flag:
                initial_upper_val = (
                    upper_envelope[0] if not np.isscalar(upper_envelope) else upper_envelope
                )
                initial_lower_val = (
                    np.min(lower_envelope) if not np.isscalar(lower_envelope) else lower_envelope
                )
                initial_pcc_val = (
                    np.min(power_at_pcc) if not np.isscalar(power_at_pcc) else power_at_pcc
                )
                upper_envelope = self._apply_delay(
                    self._emt_delay + constants.SCR_BOUND_DELAY_S,
                    initial_upper_val,
                    time_array,
                    upper_envelope,
                )
                lower_envelope = self._apply_delay(
                    self._emt_delay, initial_lower_val, time_array, lower_envelope
                )
                power_at_pcc = self._apply_delay(
                    self._emt_delay, initial_pcc_val, time_array, power_at_pcc
                )
            else:
                initial_upper_val = (
                    upper_envelope[0] if not np.isscalar(upper_envelope) else upper_envelope
                )
                upper_envelope = self._apply_delay(
                    constants.SCR_BOUND_DELAY_S, initial_upper_val, time_array, upper_envelope
                )

        return power_at_pcc, upper_envelope, lower_envelope

    def _calculate_common_params(
        self, D: float, H: float, Xeff: float
    ) -> tuple[float, float, float, float]:
        """Derives foundational system parameters central to power response evaluations.

        Args:
            D (float): The damping constant.
            H (float): The inertia constant.
            Xeff (float): The effective reactance.

        Returns:
            tuple[float, float, float, float]: A tuple containing total reactance, damping ratio,
                natural frequency, and peak power change.
        """
        total_reactance = Xeff + 1 / self._final_scr
        voltage_product = self._initial_voltage * self._grid_voltage
        base_angular_freq = self._base_angular_frequency

        if H <= 0 or total_reactance <= 0:
            natural_frequency = 0
            damping_ratio = float("inf")
        else:
            alpha = D / (2 * H)
            betha = base_angular_freq / (2 * H * total_reactance)
            if (alpha**2 - 4 * betha) < 0:
                natural_frequency = np.sqrt(
                    base_angular_freq * voltage_product / (2 * H * total_reactance)
                )
                damping_ratio = (
                    D / (4 * H * natural_frequency) if natural_frequency > 0 else float("inf")
                )
            else:
                sqrt_term_val = alpha**2 - 4 * betha
                p1 = (alpha - np.sqrt(sqrt_term_val)) / 2
                p2 = (alpha + np.sqrt(sqrt_term_val)) / 2
                natural_frequency = np.sqrt(
                    base_angular_freq * voltage_product / (2 * H * total_reactance)
                )
                damping_ratio = (p1 + p2) / (2 * np.sqrt(p1 * p2))

        peak_power_change = (
            (self._delta_impedance * self._initial_active_power / total_reactance)
            if total_reactance > 0
            else 0
        )
        self._epsilon = damping_ratio
        return total_reactance, damping_ratio, natural_frequency, peak_power_change

    def _calculate_delta_p_for_damping(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray], float, float]:
        """Branches execution logic relative to the damping ratio profile.

        Args:
            D (float): The damping constant.
            H (float): The inertia constant.
            Xeff (float): The effective reactance.
            time_array (np.ndarray): The simulation time vector.
            event_time (float): The timestamp of the event.

        Returns:
            tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray], float, float]: A tuple
                containing the primary delta_p array, min bounds array, max bounds array,
                peak power, and epsilon value.
        """
        _, damping_ratio, _, _ = self._calculate_common_params(D, H, Xeff)

        if damping_ratio >= 1:
            delta_p, p_peak, calculated_epsilon = self._get_overdamped_delta_p(
                D, H, Xeff, time_array, event_time
            )
            return delta_p, None, None, p_peak, calculated_epsilon
        else:
            delta_p, delta_p_min, delta_p_max, p_peak, calculated_epsilon = (
                self._get_underdamped_delta_p(D, H, Xeff, time_array, event_time)
            )
            return delta_p, delta_p_min, delta_p_max, p_peak, calculated_epsilon

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """Resolves the differential equation defining an overdamped response.

        Args:
            D (float): The damping constant.
            H (float): The inertia constant.
            Xeff (float): The effective reactance.
            time_array (np.ndarray): The relative simulation time vector.

        Returns:
            tuple[np.ndarray, float, float]: The baseline power deviation, peak power, and epsilon.
        """
        total_reactance, epsilon, _, peak_power = self._calculate_common_params(D, H, Xeff)
        alpha_coeff = D / (2 * H)
        beta_coeff = self._base_angular_frequency / (2 * H * total_reactance)

        sqrt_term_val = alpha_coeff**2 - 4 * beta_coeff
        if sqrt_term_val < 0:
            logger.warning("Negative sqrt term detected in overdamped execution; forced to 0.")
            sqrt_term_val = 0

        p1 = (alpha_coeff - np.sqrt(sqrt_term_val)) / 2
        p2 = (alpha_coeff + np.sqrt(sqrt_term_val)) / 2

        if abs(p2 - p1) < 1e-9:
            A = 0.5
            B = 0.5
        else:
            A = (2 * H * (-p1) + D) / ((p2 - p1) * (2 * H))
            B = (2 * H * (-p2) + D) / ((p1 - p2) * (2 * H))

        term1 = A * np.exp(-p1 * time_array)
        term2 = B * np.exp(-p2 * time_array)
        delta_p_base = peak_power * (term1 + term2)
        return delta_p_base, peak_power, epsilon

    def _get_overdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """Truncates and aligns the overdamped delta_p mapping to the event time.

        Args:
            D (float): The damping constant.
            H (float): The inertia constant.
            Xeff (float): The effective reactance.
            time_array (np.ndarray): The simulation time vector.
            event_time (float): The event trigger timestamp.

        Returns:
            tuple[np.ndarray, float, float]: The shifted delta_p array, peak power, and epsilon.
        """
        time_since_event = np.maximum(0, time_array - event_time)
        delta_p_base, p_peak, epsilon = self._get_overdamped_delta_p_base(
            D, H, Xeff, time_since_event
        )
        delta_p = np.where(time_array < event_time, 0, delta_p_base * -1)
        return delta_p, p_peak, epsilon

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
        """Synthesizes the oscillating delta_p base response for underdamped evaluations.

        Args:
            D (float): The damping constant.
            H (float): The inertia constant.
            Xeff (float): The effective reactance.
            time_array (np.ndarray): The relative simulation time vector.

        Returns:
            tuple[np.ndarray, np.ndarray, np.ndarray, float, float]: The base signal, min bounds,
                max bounds, peak power, and epsilon value.
        """
        _, epsilon, natural_frequency, peak_power = self._calculate_common_params(D, H, Xeff)
        damped_frequency = natural_frequency * np.sqrt(1 - epsilon**2)

        exp_term = np.exp(-epsilon * natural_frequency * time_array)
        cos_term = np.cos(damped_frequency * time_array)
        sin_term = np.sin(damped_frequency * time_array)

        sin_coeff = (
            ((D / (2 * H) - epsilon * natural_frequency) / damped_frequency)
            if damped_frequency > 0
            else 0
        )

        delta_p_base = peak_power * -1 * (exp_term * cos_term + sin_coeff * exp_term * sin_term)
        amplitude_envelope = np.sqrt(1 + sin_coeff**2)
        delta_p_max_env = np.abs(amplitude_envelope * peak_power * exp_term)
        delta_p_min_env = -1 * delta_p_max_env

        return delta_p_base, delta_p_min_env, delta_p_max_env, peak_power, epsilon

    def _get_underdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
        """Truncates and aligns the oscillating underdamped elements to the event time.

        Args:
            D (float): The damping constant.
            H (float): The inertia constant.
            Xeff (float): The effective reactance.
            time_array (np.ndarray): The simulation time vector.
            event_time (float): The event trigger timestamp.

        Returns:
            tuple[np.ndarray, np.ndarray, np.ndarray, float, float]: The aligned base array, min array,
                max array, peak power, and epsilon value.
        """
        time_since_event = np.maximum(0, time_array - event_time)
        delta_p_base, min_env_base, max_env_base, p_peak, epsilon = (
            self._get_underdamped_delta_p_base(D, H, Xeff, time_since_event)
        )
        delta_p = np.where(time_array < event_time, 0, delta_p_base)
        delta_p_min_env = np.where(time_array < event_time, 0, min_env_base)
        delta_p_max_env = np.where(time_array < event_time, 0, max_env_base)
        return delta_p, delta_p_min_env, delta_p_max_env, p_peak, epsilon

    def _get_tunnel(self, peak_power: float) -> float:
        """Calculates and maps the mathematical static tolerance margin ('tunnel').

        Args:
            peak_power (float): The peak power deviation used as a reference.

        Returns:
            float: The calculated tunnel margin in pu.
        """
        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * np.abs(peak_power),
        )
