#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
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
from dycov.logging.logging import dycov_logging

# Configure logger for this module
logger = dycov_logging.get_logger(__name__)


class SCRJump(GFMCalculator):
    """
    Calculates the GFM response to a Short-Circuit Ratio (SCR) jump.

    This class handles all core calculations for active power envelopes,
    differentiating between overdamped and underdamped system responses
    following an SCR event.
    """

    def __init__(self, gfm_params: GFMParameters) -> None:
        """
        Initializes the SCRJump calculator with GFM parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            An object containing all necessary parameters for GFM calculations.
        """
        super().__init__(gfm_params=gfm_params)

        # GFM and Grid Parameters
        initial_scr = gfm_params.get_initial_scr()
        self._final_scr = gfm_params.get_final_scr()
        self._delta_impedance = 1 / self._final_scr - 1 / initial_scr
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()
        self._base_angular_frequency = gfm_params.get_base_angular_frequency()
        self._initial_voltage = gfm_params.get_initial_voltage()
        self._grid_voltage = gfm_params.get_grid_voltage()

        # Envelope Calculation Parameters
        self._final_allowed_tunnel_pn = gfm_params.get_final_allowed_tunnel_pn()
        self._final_allowed_tunnel_variation = gfm_params.get_final_allowed_tunnel_variation()
        self._pmax_mois_tunnel = gfm_params.get_pmax_mois_tunnel()
        self._pmin_mois_tunnel = gfm_params.get_pmin_mois_tunnel()

        # Flag for inconsistent damping behavior
        self._is_inconsistent = False
        self._disclaimer_message: Optional[str] = None

    def get_plot_parameter_names(self) -> list[str]:
        """Returns the list of parameter names relevant for SCRJump plots."""
        return ["P0", "Q0", "SCRinitial", "SCRfinal", "Xeff", "D", "H", "Epsilon"]

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
        (PCC, upper, and lower) for an SCR jump event.

        Parameters
        ----------
        D : float
            Damping factor (D) of the system.
        H : float
            Inertia constant (H) of the system.
        Xeff : float
            Effective reactance (Xeff) of the system.
        time_array : np.ndarray
            Array of time points for the simulation.
        event_time : float
            The time (in seconds) at which the SCR jump event occurs.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - magnitude_name: The name of the calculated magnitude ("P").
            - pcc_signal: The final calculated active power at the PCC.
            - upper_envelope: The final upper active power envelope.
            - lower_envelope: The final lower active power envelope.
        """
        logger.debug(f"Input Params D={D} H={H} Xeff {Xeff}")

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
        Calculates delta_p for the nominal D, H and their variations. This is
        the core dispatcher that determines the system's damping behavior.

        Parameters
        ----------
        D : float, H : float, Xeff : float
            Nominal system parameters.
        time_array : np.ndarray
            Array of time points for the simulation.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]
            A tuple of arrays containing: delta_p waveforms, min/max exponential
            envelopes, peak power changes, and damping ratios for each D,H pair.
        """
        # Create arrays for Damping and Inertia with nominal, max, and min variations.
        damping_variations = np.array([D, D * self._max_ratio, D * self._min_ratio])
        inertia_variations = np.array([H, H * self._min_ratio, H * self._max_ratio])

        num_variations = len(damping_variations)
        num_time_points = len(time_array)

        # Initialize arrays to store the results for each parameter variation.
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

            # Min/max envelopes only exist for underdamped cases.
            if delta_p_min is not None:
                min_envelope_results[i, :] = delta_p_min
            if delta_p_max is not None:
                max_envelope_results[i, :] = delta_p_max

        self._d_vals = damping_variations
        self._h_vals = inertia_variations
        self._epsilon_vals = epsilon_results

        # Check if all scenarios (nominal, min, max) have the same damping type
        is_overdamped = epsilon_results >= 1
        if not np.all(is_overdamped == is_overdamped[0]):
            # The parameter variations result in different damping behaviors
            # (e.g., nominal is overdamped, but max variation is underdamped).
            # Format numbers for the message
            eps_str = np.array2string(epsilon_results, precision=2)
            d_str = np.array2string(damping_variations, precision=2)
            h_str = np.array2string(inertia_variations, precision=2)

            msg = (
                f"Inconsistent damping behavior across parameter variations.\n"
                f"Epsilon values: {eps_str}.\n"
                f"Is Overdamped (>=1): {is_overdamped}.\n"
                f"D values: {d_str}. H values: {h_str}.\n"
                f"Variations must maintain the same damping type"
                " (all overdamped or all underdamped)."
            )
            logger.warning(msg)
            # Set the flag and the message for the plot
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
        """
        Modifies an envelope by holding it at 50% of the expected power change
        for the first 30 ms after the event.

        Parameters
        ----------
        envelope_signal : np.ndarray
            The original envelope signal to be modified.
        power_at_50_percent : np.ndarray
            The signal representing 50% of the expected power change.
        time_array : np.ndarray
            Array of time points for the simulation.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The modified envelope signal.
        """
        # Create a boolean mask for the first 30 ms post-event.
        modification_mask = (time_array >= event_time) & (
            time_array <= event_time + constants.SCRJUMP_MODIFY_ENVELOPE_S
        )
        # Apply the 50% power value within the masked time window.
        modified_signal = np.where(modification_mask, power_at_50_percent, envelope_signal)

        # Additional logic to adjust the signal within the mask.
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
        """
        Generates upper and lower envelope traces from a delta_p waveform.

        Note: This method intentionally replicates legacy logic to ensure result
        consistency with previous versions.

        Parameters
        ----------
        delta_p : np.ndarray
            The change in power waveform.
        time_array : np.ndarray
            Array of time points for the simulation.
        event_time : float
            The time at which the event occurs.
        tunnel_value : float
            The tolerance tunnel value to be applied.
        is_overdamped : bool
            Flag indicating if the system response is overdamped.
        delta_p_at_event : float
            Value of delta_p right after the event to determine direction.
        delta_p_base : np.ndarray
            The nominal delta_p waveform.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing the upper and lower envelope traces.
        """
        if delta_p_at_event > 0:
            # Case 1: Power increases (positive delta_p).
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

            if is_overdamped:
                lower_trace = self._modify_envelope(
                    lower_trace, power_at_50_percent, time_array, event_time
                )
                lower_trace = np.where(condition, self._pmax_mois_tunnel, lower_trace)
            else:  # Underdamped case
                lower_trace = np.where(condition, self._pmax_mois_tunnel, lower_trace)
                lower_trace = self._modify_envelope(
                    lower_trace, power_at_50_percent, time_array, event_time
                )
        else:
            # Case 2: Power decreases (negative delta_p).
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

            if is_overdamped:
                upper_trace = self._modify_envelope(
                    upper_trace, power_at_50_percent, time_array, event_time
                )
                upper_trace = np.where(condition, self._pmin_mois_tunnel, upper_trace)
            else:  # Underdamped case
                upper_trace = np.where(condition, self._pmin_mois_tunnel, upper_trace)
                upper_trace = self._modify_envelope(
                    upper_trace, power_at_50_percent, time_array, event_time
                )

        # Ensure final traces are within the operational power limits.
        final_upper_trace = self._limit_signal(upper_trace)
        final_lower_trace = self._limit_signal(lower_trace)
        return final_upper_trace, final_lower_trace

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
        Applies a limit to the envelopes for the first 100 ms to prevent
        unrealistic reverse power excursions.

        Parameters
        ----------
        upper_envelope : np.ndarray
            The upper envelope signal.
        lower_envelope : np.ndarray
            The lower envelope signal.
        delta_p_nominal : np.ndarray
            The nominal change in power waveform to determine event direction.
        time_array : np.ndarray
            Array of time points for the simulation.
        event_time : float
            The time at which the event occurs.
        tunnel_value : float
            The tolerance tunnel value.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing the limited upper and lower envelopes.
        """
        # Find the index right after the event to determine the direction of power change.
        event_index = np.searchsorted(time_array, event_time + 0.01, side="right")
        delta_p_at_event = (
            delta_p_nominal[event_index] if event_index < len(delta_p_nominal) else 0
        )

        # Create a boolean mask for the initial limiting period (first 100 ms).
        limit_mask = (time_array >= event_time) & (
            time_array <= event_time + constants.SCRJUMP_INITIAL_LIMITING_S
        )

        if delta_p_at_event > 0:
            # If power increases, prevent the lower envelope from dipping below the initial power.
            limit_condition = limit_mask & (
                lower_envelope < (self._initial_active_power - tunnel_value)
            )
            lower_envelope = np.where(
                limit_condition, self._initial_active_power - tunnel_value, lower_envelope
            )
        else:
            # If power decreases, prevent the upper envelope from spiking above the initial power.
            limit_condition = limit_mask & (
                upper_envelope > (self._initial_active_power + tunnel_value)
            )
            upper_envelope = np.where(
                limit_condition, self._initial_active_power + tunnel_value, upper_envelope
            )

        return upper_envelope, lower_envelope

    def _limit_signal(self, signal: np.ndarray) -> np.ndarray:
        """
        Helper function to apply min/max active power limits (saturation).

        Parameters
        ----------
        signal : np.ndarray
            The input signal to be limited.

        Returns
        -------
        np.ndarray
            The limited (clipped) signal.
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
        """
        Calculates and limits the final active power envelopes by combining
        all candidate traces.

        Parameters
        ----------
        delta_p_array : np.ndarray
            2D array of delta_p waveforms from D,H variations.
        delta_p_min_env_array : np.ndarray
            2D array of min exponential envelopes (contains NaN if overdamped).
        delta_p_max_env_array : np.ndarray
            2D array of max exponential envelopes (contains NaN if overdamped).
        p_peak_array : np.ndarray
            1D array of peak power changes corresponding to each delta_p.
        time_array : np.ndarray
            Array of time points for the simulation.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple containing the final PCC signal, upper, and lower envelopes.
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

        # Generate envelope traces for each parameter variation.
        for i in range(delta_p_array.shape[0]):
            current_delta_p = delta_p_array[i, :]
            current_peak_power = p_peak_array[i]
            tunnel_value = self._get_tunnel(current_peak_power)

            # Generate traces from the main delta_p waveform.
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

            # Generate traces from the max envelope (for underdamped cases).
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

            # Generate traces from the min envelope (for underdamped cases).
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

        # Calculate the nominal power signal at the PCC.
        power_at_pcc = self._initial_active_power + delta_p_nominal
        power_at_pcc = self._limit_signal(power_at_pcc)

        # Signal representing 50% of the power change.
        power_at_50_percent = self._initial_active_power + np.where(
            time_array >= time_array[0], current_delta_p * 0.5, current_delta_p
        )
        power_at_50_percent = self._limit_signal(power_at_50_percent)

        # Combine all candidate traces to find the final envelopes.
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

        # The following block was commented out in the original code.
        # It seems intended for applying initial limiting, which might be handled
        # elsewhere or was deemed unnecessary.
        """
        tunnel_nominal = self._get_tunnel(p_peak_array[0])

        upper_envelope, lower_envelope = self._apply_initial_limiting(
            p_up_limited,
            p_down_limited,
            delta_p_nominal,
            time_array,
            event_time,
            tunnel_nominal,
        )
        """

        upper_envelope = combined_upper_envelope
        lower_envelope = combined_lower_envelope

        # Apply a final delay for EMT-type simulations.
        if (self._initial_active_power > 0 and delta_p_at_event > 0) or (
            self._initial_active_power < 0 and delta_p_at_event > 0
        ):
            if self._is_emt_flag:
                # Safely get initial values, handling both arrays and scalars.
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
                    constants.EMT_FINAL_DELAY_S, initial_upper_val, time_array, upper_envelope
                )
                lower_envelope = self._apply_delay(
                    constants.EMT_FINAL_DELAY_S + constants.SCR_BOUND_DELAY_S,
                    initial_lower_val,
                    time_array,
                    lower_envelope,
                )
                power_at_pcc = self._apply_delay(
                    constants.EMT_FINAL_DELAY_S, initial_pcc_val, time_array, power_at_pcc
                )
            else:
                initial_lower_val = (
                    lower_envelope[0] if not np.isscalar(lower_envelope) else lower_envelope
                )
                lower_envelope = self._apply_delay(
                    constants.SCR_BOUND_DELAY_S,
                    initial_lower_val,
                    time_array,
                    lower_envelope,
                )
        else:
            if self._is_emt_flag:
                # Safely get initial values, handling both arrays and scalars.
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
                    constants.EMT_FINAL_DELAY_S + constants.SCR_BOUND_DELAY_S,
                    initial_upper_val,
                    time_array,
                    upper_envelope,
                )
                lower_envelope = self._apply_delay(
                    constants.EMT_FINAL_DELAY_S, initial_lower_val, time_array, lower_envelope
                )
                power_at_pcc = self._apply_delay(
                    constants.EMT_FINAL_DELAY_S, initial_pcc_val, time_array, power_at_pcc
                )
            else:
                initial_upper_val = (
                    upper_envelope[0] if not np.isscalar(upper_envelope) else upper_envelope
                )
                upper_envelope = self._apply_delay(
                    constants.SCR_BOUND_DELAY_S,
                    initial_upper_val,
                    time_array,
                    upper_envelope,
                )

        return power_at_pcc, upper_envelope, lower_envelope

    def _calculate_common_params(
        self, D: float, H: float, Xeff: float
    ) -> tuple[float, float, float, float]:
        """
        Calculates common parameters used in power response calculations.

        Parameters
        ----------
        D : float
            Damping factor (D).
        H : float
            Inertia constant (H).
        Xeff : float
            Effective reactance (Xeff).

        Returns
        -------
        tuple[float, float, float, float]
            A tuple containing: total reactance, damping ratio (epsilon),
            natural frequency (wn), and calculated peak power change.
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

            if (alpha**2 - 4 * betha) < 0:  # Underdamped
                # Natural frequency of oscillation (rad/s)
                natural_frequency = np.sqrt(
                    base_angular_freq * voltage_product / (2 * H * total_reactance)
                )
                # Damping ratio (dimensionless)
                damping_ratio = (
                    D / (4 * H * natural_frequency) if natural_frequency > 0 else float("inf")
                )
            else:  # Overdamped
                sqrt_term_val = alpha**2 - 4 * betha
                p1 = (alpha - np.sqrt(sqrt_term_val)) / 2
                p2 = (alpha + np.sqrt(sqrt_term_val)) / 2

                # Natural frequency of oscillation (rad/s)
                natural_frequency = np.sqrt(
                    base_angular_freq * voltage_product / (2 * H * total_reactance)
                )
                # Damping ratio (dimensionless)
                damping_ratio = (p1 + p2) / (2 * np.sqrt(p1 * p2))

        # Theoretical peak power change
        peak_power_change = (
            self._delta_impedance * self._initial_active_power / total_reactance
            if total_reactance > 0
            else 0
        )
        self._epsilon = damping_ratio
        return total_reactance, damping_ratio, natural_frequency, peak_power_change

    def _calculate_delta_p_for_damping(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray], float, float]:
        """
        Selects the delta_p calculation method based on the damping ratio.

        Parameters
        ----------
        D : float, H : float, Xeff : float
            System parameters for the current variation.
        time_array : np.ndarray
            Array of time points for the simulation.
        event_time : float
            Time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray], float, float]
            A tuple containing: the delta_p waveform, min/max envelopes (or None),
            peak power change, and damping ratio.
        """
        _, damping_ratio, _, _ = self._calculate_common_params(D, H, Xeff)

        # Epsilon >= 1 corresponds to an overdamped or critically damped system.
        if damping_ratio >= 1:
            delta_p, p_peak, calculated_epsilon = self._get_overdamped_delta_p(
                D, H, Xeff, time_array, event_time
            )
            return delta_p, None, None, p_peak, calculated_epsilon
        else:  # Epsilon < 1 corresponds to an underdamped system.
            delta_p, delta_p_min, delta_p_max, p_peak, calculated_epsilon = (
                self._get_underdamped_delta_p(D, H, Xeff, time_array, event_time)
            )
            return delta_p, delta_p_min, delta_p_max, p_peak, calculated_epsilon

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the base delta_p waveform for an overdamped system response.

        This solves the second-order differential equation for the system.

        Parameters
        ----------
        D : float, H: float, Xeff: float
            System parameters.
        time_array : np.ndarray
            Time array for the simulation, starting from t=0 at the event.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing the base delta_p, peak power, and epsilon.
        """
        total_reactance, epsilon, _, peak_power = self._calculate_common_params(D, H, Xeff)

        # Coefficients from the characteristic equation of the system's DE
        alpha_coeff = D / (2 * H)
        beta_coeff = self._base_angular_frequency / (2 * H * total_reactance)

        sqrt_term_val = alpha_coeff**2 - 4 * beta_coeff
        if sqrt_term_val < 0:
            logger.warning(
                "Negative sqrt term in overdamped calc, may be misclassified. Clamping to 0."
            )
            sqrt_term_val = 0

        # Roots of the characteristic equation
        p1 = (alpha_coeff - np.sqrt(sqrt_term_val)) / 2
        p2 = (alpha_coeff + np.sqrt(sqrt_term_val)) / 2

        # Calculate integration constants A and B for the solution
        if abs(p2 - p1) < 1e-9:  # Critically damped case
            A = 0.5
            B = 0.5
        else:
            A = (2 * H * (-p1) + D) / ((p2 - p1) * (2 * H))
            B = (2 * H * (-p2) + D) / ((p1 - p2) * (2 * H))

        # Full solution is of the form: p_peak * (A*e^(-p1*t) + B*e^(-p2*t))
        term1 = A * np.exp(-p1 * time_array)
        term2 = B * np.exp(-p2 * time_array)
        delta_p_base = peak_power * (term1 + term2)

        return delta_p_base, peak_power, epsilon

    def _get_overdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the final delta_p for an overdamped system by applying the
        event time (response is zero before the event).

        Parameters
        ----------
        D : float, H: float, Xeff: float
            System parameters.
        time_array : np.ndarray
            The full time array for the simulation.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing the final delta_p, peak power, and epsilon.
        """
        # Time relative to the event start
        time_since_event = np.maximum(0, time_array - event_time)
        delta_p_base, p_peak, epsilon = self._get_overdamped_delta_p_base(
            D, H, Xeff, time_since_event
        )

        # The response is zero before the event and has an inverted sign.
        delta_p = np.where(time_array < event_time, 0, delta_p_base * -1)

        return delta_p, p_peak, epsilon

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
        """
        Calculates the base delta_p and its envelopes for an underdamped system.

        Parameters
        ----------
        D : float, H: float, Xeff: float
            System parameters.
        time_array : np.ndarray
            Time array for the simulation, starting from t=0 at the event.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray, float, float]
            A tuple containing delta_p, min/max envelopes, peak power, and epsilon.
        """
        _, epsilon, natural_frequency, peak_power = self._calculate_common_params(D, H, Xeff)

        # Damped natural frequency
        damped_frequency = natural_frequency * np.sqrt(1 - epsilon**2)

        # Components of the underdamped solution
        exp_term = np.exp(-epsilon * natural_frequency * time_array)
        cos_term = np.cos(damped_frequency * time_array)
        sin_term = np.sin(damped_frequency * time_array)
        sin_coeff = (
            (D / (2 * H) - epsilon * natural_frequency) / damped_frequency
            if damped_frequency > 0
            else 0
        )

        # Full solution is an exponentially decaying sinusoid
        delta_p_base = peak_power * -1 * (exp_term * cos_term + sin_coeff * exp_term * sin_term)

        # The envelopes are determined by the amplitude of the oscillation
        amplitude_envelope = np.sqrt(1 + sin_coeff**2)
        delta_p_max_env = np.abs(amplitude_envelope * peak_power * exp_term)
        delta_p_min_env = -1 * delta_p_max_env

        return delta_p_base, delta_p_min_env, delta_p_max_env, peak_power, epsilon

    def _get_underdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
        """
        Calculates final delta_p and envelopes for an underdamped system,
        applying the event time.

        Parameters
        ----------
        D : float, H: float, Xeff: float
            System parameters.
        time_array : np.ndarray
            The full time array for the simulation.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray, float, float]
            A tuple containing delta_p, min/max envelopes, peak power, and epsilon.
        """
        # Time relative to the event start
        time_since_event = np.maximum(0, time_array - event_time)

        delta_p_base, min_env_base, max_env_base, p_peak, epsilon = (
            self._get_underdamped_delta_p_base(D, H, Xeff, time_since_event)
        )

        # Response is zero before the event.
        delta_p = np.where(time_array < event_time, 0, delta_p_base)
        delta_p_min_env = np.where(time_array < event_time, 0, min_env_base)
        delta_p_max_env = np.where(time_array < event_time, 0, max_env_base)

        return delta_p, delta_p_min_env, delta_p_max_env, p_peak, epsilon

    def _get_tunnel(self, peak_power: float) -> float:
        """
        Calculates the tolerance "tunnel" value.

        The tunnel defines a static band around the power response, determined by
        a fixed value or a percentage of the peak power change.

        Parameters
        ----------
        peak_power : float
            The peak change in active power.

        Returns
        -------
        float
            The calculated tunnel value.
        """
        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * np.abs(peak_power),
        )
