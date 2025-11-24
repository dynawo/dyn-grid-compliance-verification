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

# Configure logger for this module
logger = dycov_logging.get_logger(__name__)


class RoCoF(GFMCalculator):
    """
    Calculates the GFM response to a Rate of Change of Frequency (RoCoF) event.

    This class handles all core calculations for active power envelopes,
    differentiating between overdamped and underdamped system responses
    following a frequency ramp event.
    """

    def __init__(self, gfm_params: GFMParameters) -> None:
        """
        Initializes the RoCoF calculator with GFM parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            An object containing all necessary parameters for GFM calculations.
        """
        super().__init__(gfm_params=gfm_params)

        # GFM and Grid Parameters
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()
        self._base_angular_frequency = gfm_params.get_base_angular_frequency()
        self._initial_voltage = gfm_params.get_initial_voltage()
        self._grid_voltage = gfm_params.get_grid_voltage()

        # RoCoF Specific Parameters
        self._rocof = gfm_params.get_change_frequency()
        self._rocof_duration = gfm_params.get_change_frequency_duration()
        self._tpll = gfm_params.get_pll_time_constant()

        # Envelope Calculation Parameters
        self._final_allowed_tunnel_pn = gfm_params.get_final_allowed_tunnel_pn()
        self._final_allowed_tunnel_variation = gfm_params.get_final_allowed_tunnel_variation()
        self._pmax_mois_tunnel = gfm_params.get_pmax_mois_tunnel()
        self._pmin_mois_tunnel = gfm_params.get_pmin_mois_tunnel()

        # Flag for inconsistent damping behavior
        self._is_inconsistent = False
        self._disclaimer_message: str | None = None

        # Initialize epsilon for plotting
        self._epsilon = 0.0

    def get_plot_parameter_names(self) -> list[str]:
        """Returns the list of parameter names relevant for RoCoF plots."""
        return ["P0", "Q0", "SCR", "RoCoF", "RoCoFDuration", "Xeff", "D", "H", "Epsilon"]

    def calculate_envelopes(
        self,
        D: float,
        H: float,
        Xeff: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the change in power (delta_p) and active power envelopes
        (PCC, upper, and lower) for a RoCoF event.
        """
        logger.debug(f"Input Params D={D} H={H} Xeff {Xeff} RoCoF={self._rocof}")

        # Step 1: Calculate DeltaP for different D and H variations.
        (
            delta_p_results,
            min_envelope_results,
            max_envelope_results,
            peak_power_results,
            _,
        ) = self._get_delta_p(
            D=D,
            H=H,
            Xeff=Xeff,
            time_array=time_array,
            event_time=event_time,
        )

        # Step 2: Generate the final envelopes from all DeltaP candidate traces.
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
        """
        Calculates delta_p for the nominal D, H and their variations.
        """
        # Create arrays for Damping and Inertia with nominal, max, and min variations.
        damping_variations = np.array([D, D * self._max_ratio, D * self._min_ratio])
        inertia_variations = np.array([H, H * self._max_ratio, H * self._min_ratio])

        num_variations = len(damping_variations)
        num_time_points = len(time_array)

        # Initialize arrays
        delta_p_results = np.zeros((num_variations, num_time_points))
        min_envelope_results = np.full((num_variations, num_time_points), np.nan)
        max_envelope_results = np.full((num_variations, num_time_points), np.nan)
        peak_power_results = np.zeros(num_variations)
        epsilon_results = np.zeros(num_variations)

        # Calculate the response for each combination of parameters.
        for i in range(num_variations):
            delta_p, delta_p_min, delta_p_max, p_peak, epsilon = (
                self._calculate_delta_p_for_damping(
                    damping_variations[i], inertia_variations[i], Xeff, time_array, event_time
                )
            )
            delta_p_results[i, :] = delta_p
            peak_power_results[i] = p_peak
            epsilon_results[i] = epsilon

            # Store min/max envelopes if they exist
            if delta_p_min is not None:
                min_envelope_results[i, :] = delta_p_min
            if delta_p_max is not None:
                max_envelope_results[i, :] = delta_p_max

        # Check consistency
        is_overdamped = epsilon_results >= 1
        if not np.all(is_overdamped == is_overdamped[0]):
            eps_str = np.array2string(epsilon_results, precision=2)
            msg = (
                f"Inconsistent damping behavior across parameter variations.\n"
                f"Epsilon values: {eps_str}."
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

    def _calculate_common_params(
        self, D: float, H: float, Xeff: float
    ) -> tuple[float, float, float, float, float, float]:
        """
        Calculates common parameters used in power response calculations.

        Returns
        -------
        tuple
            (omega_n, xi, alpha, beta, common_denom, wd)
        """
        total_reactance = Xeff
        voltage_product = self._initial_voltage * self._grid_voltage
        base_angular_freq = self._base_angular_frequency

        # Natural frequency (omega_n) and Damping Ratio (xi)
        omega_n = np.sqrt(base_angular_freq * voltage_product / (2 * H * total_reactance))
        xi = omega_n * D * total_reactance / (2 * base_angular_freq * voltage_product)

        # Set epsilon for plotting
        self._epsilon = xi

        # Common Terms
        alpha = 2 * H * self._tpll * self._rocof
        beta = (2 * H + D * self._tpll) / (2 * H * self._tpll)

        common_denom = 1 - 2 * xi * omega_n * self._tpll + omega_n**2 * self._tpll**2

        # Damped frequency for underdamped case
        if xi < 1:
            wd = omega_n * np.sqrt(1 - xi**2)
        else:
            wd = 0.0

        return omega_n, xi, alpha, beta, common_denom, wd

    def _calculate_delta_p_for_damping(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None, float, float]:
        """
        Selects the delta_p calculation method based on the damping ratio.
        """
        _, xi, _, _, _, _ = self._calculate_common_params(D, H, Xeff)

        if xi >= 1:
            # Overdamped
            delta_p, p_peak, calculated_xi = self._get_overdamped_delta_p(
                D, H, Xeff, time_array, event_time
            )
            return delta_p, None, None, p_peak, calculated_xi
        else:
            # Underdamped
            delta_p, delta_p_min, delta_p_max, p_peak, calculated_xi = (
                self._get_underdamped_delta_p(D, H, Xeff, time_array, event_time)
            )
            return delta_p, delta_p_min, delta_p_max, p_peak, calculated_xi

    def _get_overdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates delta_p for an overdamped system using superposition.
        """
        rocof_stop_time = event_time + self._rocof_duration

        # Response 1: Ramp starting at event_time
        response_1, xi = self._get_overdamped_response_continuous(
            D, H, Xeff, time_array - event_time
        )
        delta_p1 = np.where(time_array > event_time, response_1, 0)

        # Response 2: Ramp starting at rocof_stop_time (Superposition)
        response_2, _ = self._get_overdamped_response_continuous(
            D, H, Xeff, time_array - rocof_stop_time
        )
        # Logic: DeltaP_Recovered = ... * -1
        delta_p2 = np.where(time_array > rocof_stop_time, response_2, 0) * -1

        # Total DeltaP = (DeltaP1 + DeltaP2) * -1
        delta_p = (delta_p1 + delta_p2) * -1

        p_steady = abs(delta_p[-1])

        return delta_p, p_steady, xi

    def _get_overdamped_response_continuous(
        self, D: float, H: float, Xeff: float, t_rel: np.ndarray
    ) -> tuple[np.ndarray, float]:
        """
        Calculates the continuous overdamped response.
        """
        omega_n, xi, alpha, _, denom, _ = self._calculate_common_params(D, H, Xeff)

        # Coefficient D_val for Overdamped logic (Short Formula)
        D_val_alt = (
            self._rocof
            * D
            * omega_n**2
            / (omega_n**2 + 1 / self._tpll**2 - 2 * xi * omega_n / self._tpll)
        )

        A_val = -self._rocof * (2 * H + D * self._tpll)
        B_val = -A_val - (D_val_alt / self._tpll)
        C_val = (
            -self._rocof * 2 * H * self._tpll * omega_n**2
            - A_val * (2 * xi * omega_n + omega_n**2 * self._tpll)
            - D_val_alt * omega_n**2
        )

        # Roots
        alpha1 = omega_n * (xi + np.sqrt(xi**2 - 1))
        alpha2 = omega_n * (xi - np.sqrt(xi**2 - 1))

        term1 = (B_val * alpha1 - C_val) * np.exp(-alpha1 * t_rel) / (alpha1 - alpha2)
        term2 = (B_val * alpha2 - C_val) * np.exp(-alpha2 * t_rel) / (alpha1 - alpha2)

        response = A_val + term1 - term2 + D_val_alt * np.exp(-t_rel / self._tpll) / self._tpll

        return response, xi

    def _get_underdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None, float, float]:
        """
        Calculates delta_p for an underdamped system using superposition.

        CRITICAL CHANGE: We rely on margin-based envelopes calculated later
        using the final DeltaP signal, rather than trying to superimpose
        analytical exponential bounds, which causes discontinuities.
        """
        rocof_stop_time = event_time + self._rocof_duration

        # Response 1: t > event_time
        (resp1, xi) = self._get_underdamped_response_continuous(
            D, H, Xeff, time_array - event_time
        )
        delta_p1 = np.where(time_array > event_time, resp1, 0)

        # Response 2: t > rocof_stop_time (Superposition)
        (resp2, _) = self._get_underdamped_response_continuous(
            D, H, Xeff, time_array - rocof_stop_time
        )

        # Invert response 2 for superposition logic
        delta_p2 = np.where(time_array > rocof_stop_time, resp2, 0) * -1

        # Combine Signals: (R1 + R2_inverted) * -1
        delta_p = (delta_p1 + delta_p2) * -1

        # We return None for envelopes here to force the usage of
        # margin-based envelopes in _get_envelopes/calculate_envelopes.
        # This avoids the "spikes" caused by adding analytical bounds at discontinuity points.

        p_steady = abs(delta_p[-1])

        return delta_p, None, None, p_steady, xi

    def _get_underdamped_response_continuous(
        self, D: float, H: float, Xeff: float, t_rel: np.ndarray
    ) -> tuple[np.ndarray, float]:
        """
        Calculates the continuous underdamped response.
        """
        omega_n, xi, alpha, beta, common_denom, wd = self._calculate_common_params(D, H, Xeff)

        # Coefficients specific to Underdamped logic (Long Formula)
        A_coeff = alpha * beta
        B_coeff = -(self._tpll**2 * alpha * omega_n**2 * (self._tpll * beta - 1)) / common_denom
        C_coeff = (
            alpha * (2 * self._tpll * beta * xi * omega_n - self._tpll * omega_n**2 - beta)
        ) / common_denom

        # D_coeff using the long formula
        D_coeff = (
            alpha
            * (
                4 * self._tpll * beta * omega_n**2 * xi**2
                - self._tpll * beta * omega_n**2
                - 2 * self._tpll * omega_n**3 * xi
                - 2 * beta * omega_n * xi
                + omega_n**2
            )
        ) / common_denom

        # Terms
        term2 = np.exp(-t_rel / self._tpll)
        term3 = np.exp(-xi * omega_n * t_rel) * np.cos(wd * t_rel)
        term4 = np.exp(-xi * omega_n * t_rel) * np.sin(wd * t_rel)

        delta_p = (
            A_coeff
            + B_coeff / self._tpll * term2
            + C_coeff * term3
            + C_coeff * (D_coeff / C_coeff - xi * omega_n) / wd * term4
        )

        # Return inverted values as per user script logic
        return -delta_p, xi

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
        """
        Generates upper and lower envelope traces from a delta_p waveform
        based on margins.
        """
        p0 = self._initial_active_power
        rocof_stop_time = event_time + self._rocof_duration

        # Masks
        mask_pre = time_array < event_time
        mask_ramp = (time_array >= event_time) & (time_array <= rocof_stop_time)
        mask_post = time_array > rocof_stop_time

        if self._rocof <= 0:
            # Case: Power increases (DeltaP > 0)
            margin_ramp_up = delta_p * (1 + self._margin_high)
            up_ramp = (margin_ramp_up + p0 + tunnel_value) * mask_ramp
            up_post = (delta_p * (1 + self._margin_high) + p0 + tunnel_value) * mask_post
            up_pre = (p0 + tunnel_value) * mask_pre

            upper_trace = up_pre + up_ramp + up_post

            margin_ramp_low = delta_p * (1 - self._margin_low)
            low_ramp = (margin_ramp_low + p0 - tunnel_value) * mask_ramp
            low_post = (delta_p * (1 - self._margin_low) + p0 - tunnel_value) * mask_post
            low_pre = (p0 - tunnel_value) * mask_pre

            lower_trace = low_pre + low_ramp + low_post

            # 50% logic
            power_at_50 = p0 + np.where(time_array >= event_time, delta_p * 0.5 + 0.005, delta_p)
            lower_trace = self._modify_envelope(lower_trace, power_at_50, time_array, event_time)

        else:
            # Case: Power decreases (DeltaP < 0)
            up_ramp = (delta_p * (1 - self._margin_high) + p0 + tunnel_value) * mask_ramp
            up_post = (delta_p * (1 - self._margin_high) + p0 + tunnel_value) * mask_post
            up_pre = (p0 + tunnel_value) * mask_pre

            upper_trace = up_pre + up_ramp + up_post

            low_ramp = (delta_p * (1 + self._margin_low) + p0 - tunnel_value) * mask_ramp
            low_post = (delta_p * (1 + self._margin_low) + p0 - tunnel_value) * mask_post
            low_pre = (p0 - tunnel_value) * mask_pre

            lower_trace = low_pre + low_ramp + low_post

            # 50% logic
            power_at_50 = p0 + np.where(time_array >= event_time, delta_p * 0.5 + 0.005, delta_p)
            upper_trace = self._modify_envelope(upper_trace, power_at_50, time_array, event_time)

        return self._limit_signal(upper_trace), self._limit_signal(lower_trace)

    def _modify_envelope(
        self,
        envelope_signal: np.ndarray,
        power_at_50_percent: np.ndarray,
        time_array: np.ndarray,
        event_time: float,
    ) -> np.ndarray:
        """
        Modifies an envelope by holding it at 50% of the expected power change.
        """
        duration = 0.03

        modification_mask = (time_array >= event_time) & (time_array <= event_time + duration)
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

    def _apply_initial_limiting(
        self,
        upper_envelope: np.ndarray,
        lower_envelope: np.ndarray,
        delta_p_nominal: np.ndarray,
        time_array: np.ndarray,
        event_time: float,
        tunnel_value: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Applies a limit to the envelopes for the first 100 ms.
        """
        limit_mask = (time_array >= event_time) & (time_array <= event_time + 0.1)

        if self._rocof <= 0:
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
        """Helper function to apply min/max active power limits."""
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
        """
        Calculates and limits the final active power envelopes.
        """
        upper_trace_candidates = []
        lower_trace_candidates = []

        delta_p_nominal = delta_p_array[0, :]

        for i in range(delta_p_array.shape[0]):
            current_delta_p = delta_p_array[i, :]
            current_peak_power = p_peak_array[i]
            tunnel_value = self._get_tunnel(current_peak_power)

            # 1. Standard Margins Envelopes (For BOTH Overdamped and Underdamped)
            # We ignore analytical bounds (min/max_env_array) to avoid spikes.
            upper_trace, lower_trace = self._get_envelope_traces(
                delta_p=current_delta_p,
                time_array=time_array,
                event_time=event_time,
                tunnel_value=tunnel_value,
                is_overdamped=np.isnan(delta_p_min_env_array[i, 0]),
                delta_p_at_event=0,
                delta_p_base=delta_p_nominal,
            )
            upper_trace_candidates.append(upper_trace)
            lower_trace_candidates.append(lower_trace)

            # Removed "Analytical Envelopes" section to ensure only smooth margin envelopes are used.

        # Combine traces
        combined_upper = np.nanmax(np.vstack(upper_trace_candidates), axis=0)
        combined_lower = np.nanmin(np.vstack(lower_trace_candidates), axis=0)

        # Nominal PCC
        power_at_pcc = self._initial_active_power + delta_p_nominal
        power_at_pcc = self._limit_signal(power_at_pcc)

        # Initial Limiting
        tunnel_nominal = self._get_tunnel(p_peak_array[0])
        combined_upper, combined_lower = self._apply_initial_limiting(
            combined_upper, combined_lower, delta_p_nominal, time_array, event_time, tunnel_nominal
        )

        # Apply EMT delays
        if self._is_emt_flag:
            power_at_pcc = self._apply_delay(
                constants.EMT_FINAL_DELAY_S, power_at_pcc[0], time_array, power_at_pcc
            )
            combined_upper = self._apply_delay(
                constants.EMT_FINAL_DELAY_S, combined_upper[0], time_array, combined_upper
            )
            combined_lower = self._apply_delay(
                constants.EMT_FINAL_DELAY_S, combined_lower[0], time_array, combined_lower
            )

        return power_at_pcc, combined_upper, combined_lower

    def _get_tunnel(self, peak_power: float) -> float:
        """
        Calculates the tolerance "tunnel" value.
        """
        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * np.abs(peak_power),
        )
