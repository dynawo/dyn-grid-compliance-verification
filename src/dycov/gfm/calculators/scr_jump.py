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
    Calculator class dedicated to handling the GFM response to a Short-Circuit
    Ratio (SCR) jump.

    This class performs all core calculations for active power envelopes,
    mathematically differentiating between overdamped and underdamped
    system responses following an abrupt SCR variation event.
    """

    def __init__(self, gfm_params: GFMParameters) -> None:
        """
        Initializes the SCRJump calculator with the specified Grid Forming parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            An object containing all necessary parameters required for the GFM
            calculations, including specific settings for SCR evaluation.
        """
        super().__init__(gfm_params=gfm_params)

        # Core GFM and Grid operational parameters
        initial_scr = gfm_params.get_initial_scr()
        self._final_scr = gfm_params.get_final_scr()
        self._delta_impedance = 1 / self._final_scr - 1 / initial_scr
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()
        self._base_angular_frequency = gfm_params.get_base_angular_frequency()
        self._initial_voltage = gfm_params.get_initial_voltage()
        self._grid_voltage = gfm_params.get_grid_voltage()

        # Constraints and boundary parameters for envelope generation
        self._final_allowed_tunnel_pn = gfm_params.get_final_allowed_tunnel_pn()
        self._final_allowed_tunnel_variation = gfm_params.get_final_allowed_tunnel_variation()
        self._pmax_mois_tunnel = gfm_params.get_pmax_mois_tunnel()
        self._pmin_mois_tunnel = gfm_params.get_pmin_mois_tunnel()

        # Internal operational flags for detecting inconsistent damping behavior
        self._is_inconsistent = False
        self._disclaimer_message: Optional[str] = None

    def get_plot_parameter_names(self) -> list[str]:
        """
        Retrieves the list of parameter names relevant for rendering SCRJump plots.

        Returns
        -------
        list[str]
            A predefined list of string identifiers corresponding to the parameters
            displayed on the output plots.
        """
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
        Calculates the active power deviation (delta_p) and its bounding envelopes
        (PCC, upper, and lower) evaluated across an SCR jump event timeframe.

        Parameters
        ----------
        D : float
            The system damping factor (D).
        H : float
            The system inertia constant (H).
        Xeff : float
            The effective reactance of the system (Xeff).
        time_array : np.ndarray
            The array of time points corresponding to the simulation window.
        event_time : float
            The absolute time (in seconds) at which the SCR jump event initiates.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - str: The physical magnitude identifier (e.g., "Ip").
            - np.ndarray: The main calculated active power signal at the PCC.
            - np.ndarray: The upper bounded active power envelope constraint.
            - np.ndarray: The lower bounded active power envelope constraint.
        """
        logger.debug(f"Input Params D={D} H={H} Xeff {Xeff}")

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

        # traces.
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
        Computes the delta_p sequences across nominal, minimum, and maximum
        parameter variations. This acts as the core dispatcher defining system damping behavior.

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
        tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]
            A tuple of arrays containing: delta_p waveforms, min/max exponential
            envelopes, peak power changes, and calculated damping ratios for each D,H pair.
        """
        # Construct testing arrays establishing the bounds of damping and inertia deviations.
        damping_variations = np.array([D, D * self._max_ratio, D * self._min_ratio])
        inertia_variations = np.array([H, H * self._min_ratio, H * self._max_ratio])

        num_variations = len(damping_variations)
        num_time_points = len(time_array)

        # Pre-allocate output arrays for processing efficiency.
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

            # Isolate and store Min/Max envelopes strictly for underdamped evaluations.
            if delta_p_min is not None:
                min_envelope_results[i, :] = delta_p_min
            if delta_p_max is not None:
                max_envelope_results[i, :] = delta_p_max

        self._d_vals = damping_variations
        self._h_vals = inertia_variations
        self._epsilon_vals = epsilon_results

        # Evaluate internal consistency: Ensure all evaluated scenarios share the same damping
        # archetype.
        is_overdamped = epsilon_results >= 1
        if not np.all(is_overdamped == is_overdamped[0]):
            # If behavior diverges (e.g., nominal is overdamped but max variation drops to
            # underdamped), flag it.
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
            # Register the inconsistency to append plotting disclaimers.
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
        Dynamically modifies an envelope by anchoring it to 50% of the expected
        power change during the initial 30 ms transient window following the event.

        Parameters
        ----------
        envelope_signal : np.ndarray
            The theoretical envelope signal targeted for modification.
        power_at_50_percent : np.ndarray
            The baseline signal reflecting 50% of the calculated power shift.
        time_array : np.ndarray
            The array of time points corresponding to the simulation.
        event_time : float
            The absolute time at which the event initiates.

        Returns
        -------
        np.ndarray
            The newly modified and bounded envelope signal.
        """
        # Generate a boolean evaluation mask capturing strictly the first 30 ms post-event.
        modification_mask = (time_array >= event_time) & (
            time_array <= event_time + constants.SCRJUMP_MODIFY_ENVELOPE_S
        )
        modified_signal = np.where(modification_mask, power_at_50_percent, envelope_signal)

        # Apply robust sanity checks to ensure modifications do not breach hardware limits.
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
        Synthesizes the upper and lower boundary traces derived from a delta_p waveform.

        Note: This specific method intentionally replicates legacy analytical logic
        to ensure stringent numerical consistency with prior validation benchmarks.

        Parameters
        ----------
        delta_p : np.ndarray
            The foundational change in power waveform.
        time_array : np.ndarray
            The array of time points corresponding to the simulation.
        event_time : float
            The absolute time at which the event occurs.
        tunnel_value : float
            The static tolerance margin applied to the operational band.
        is_overdamped : bool
            Flag denoting if the current system response is classified as overdamped.
        delta_p_at_event : float
            Instantaneous delta_p value immediately post-event utilized to infer vector direction.
        delta_p_base : np.ndarray
            The nominal baseline delta_p waveform.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing the synthesized upper and lower envelope traces.
        """
        if delta_p_at_event > 0:
            # Case 1: Trajectory indicates a power surge (positive delta_p).
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
            else:  # Underdamped execution branch
                lower_trace = self._modify_envelope(
                    lower_trace, power_at_50_percent, time_array, event_time
                )
                lower_trace = np.where(condition, self._pmax_mois_tunnel, lower_trace)
        else:
            # Case 2: Trajectory indicates a power drop (negative delta_p).
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
                # Artificial flattening constraint bypassed to preserve natural exponential decay
                upper_trace = np.where(condition, self._pmin_mois_tunnel, upper_trace)
            else:  # Underdamped execution branch
                upper_trace = np.where(condition, self._pmin_mois_tunnel, upper_trace)

        # Enforce hard limits restricting signals to physical hardware capabilities.
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
        Enforces a strict limitation protocol over the initial 100 ms transient period
        to mitigate mathematically unrealistic reverse power excursions.

        Parameters
        ----------
        upper_envelope : np.ndarray
            The calculated upper envelope signal array.
        lower_envelope : np.ndarray
            The calculated lower envelope signal array.
        delta_p_nominal : np.ndarray
            The nominal delta_p waveform used to evaluate the true trajectory direction.
        time_array : np.ndarray
            The array of time points corresponding to the simulation.
        event_time : float
            The absolute time at which the event initiates.
        tunnel_value : float
            The operational tolerance tunnel value.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple returning the procedurally limited upper and lower envelopes.
        """
        # Identify the precise index immediately succeeding the event to extract vector direction.
        event_index = np.searchsorted(time_array, event_time + 0.01, side="right")
        delta_p_at_event = (
            delta_p_nominal[event_index] if event_index < len(delta_p_nominal) else 0
        )

        # Construct a boolean mask isolating the initial limitation threshold window
        # (first 100 ms).
        limit_mask = (time_array >= event_time) & (
            time_array <= event_time + constants.SCRJUMP_INITIAL_LIMITING_S
        )

        if delta_p_at_event > 0:
            # Under surging power scenarios, prevent the lower boundary from sinking below
            # baseline.
            limit_condition = limit_mask & (
                lower_envelope < (self._initial_active_power - tunnel_value)
            )
            lower_envelope = np.where(
                limit_condition, self._initial_active_power - tunnel_value, lower_envelope
            )
        else:
            # Under dropping power scenarios, prevent the upper boundary from spiking above
            # baseline.
            limit_condition = limit_mask & (
                upper_envelope > (self._initial_active_power + tunnel_value)
            )
            upper_envelope = np.where(
                limit_condition, self._initial_active_power + tunnel_value, upper_envelope
            )

        return upper_envelope, lower_envelope

    def _limit_signal(self, signal: np.ndarray) -> np.ndarray:
        """Utility function enforcing absolute min/max active power hardware limits (saturation
        clipping).

        Parameters
        ----------
        signal : np.ndarray
            The raw input signal requiring constraint processing.

        Returns
        -------
        np.ndarray
            The processed and correctly bounded signal array.
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
        Processes and constructs the absolute final active power envelopes by evaluating,
        limiting, and merging all generated candidate traces.

        Parameters
        ----------
        delta_p_array : np.ndarray
            A 2D array matrix containing delta_p waveforms derived from D,H variations.
        delta_p_min_env_array : np.ndarray
            A 2D array representing minimum exponential envelopes (populated with NaNs if
            overdamped).
        delta_p_max_env_array : np.ndarray
            A 2D array representing maximum exponential envelopes (populated with NaNs if
            overdamped).
        p_peak_array : np.ndarray
            A 1D array reflecting the peak power deviations linked to each delta_p execution.
        time_array : np.ndarray
            The array of time points corresponding to the simulation.
        event_time : float
            The absolute time at which the SCR event occurs.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple outputting the final consolidated PCC signal, along with the max upper
            and min lower envelopes.
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

            # If underdamped, execute and extract traces strictly derived from the upper
            # exponential bounds.
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

            # If underdamped, execute and extract traces strictly derived from the lower
            # exponential bounds.
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

        # Reconstruct the expected nominal power signal traversing the Point of Common Coupling.
        power_at_pcc = self._initial_active_power + delta_p_nominal
        power_at_pcc = self._limit_signal(power_at_pcc)

        # Isolate the anchor line representing exactly 50% of the active power deviation.
        power_at_50_percent = self._initial_active_power + np.where(
            time_array >= time_array[0], current_delta_p * 0.5, current_delta_p
        )
        power_at_50_percent = self._limit_signal(power_at_50_percent)

        # Merge and aggregate all viable candidate traces to finalize the bounding structures.
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

        # Enforce temporal delays applicable strictly to Electro-Magnetic Transient (EMT)
        # simulations.
        if (self._initial_active_power > 0 and delta_p_at_event > 0) or (
            self._initial_active_power < 0 and delta_p_at_event > 0
        ):
            if self._is_emt_flag:
                # Robust extraction handling both vector arrays and isolated scalar values safely.
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
                    self._emt_initial_delay, initial_upper_val, time_array, upper_envelope
                )
                lower_envelope = self._apply_delay(
                    self._emt_initial_delay + constants.SCR_BOUND_DELAY_S,
                    initial_lower_val,
                    time_array,
                    lower_envelope,
                )
                power_at_pcc = self._apply_delay(
                    self._emt_initial_delay, initial_pcc_val, time_array, power_at_pcc
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
                # Robust extraction handling both vector arrays and isolated scalar values safely.
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
                    self._emt_initial_delay + constants.SCR_BOUND_DELAY_S,
                    initial_upper_val,
                    time_array,
                    upper_envelope,
                )
                lower_envelope = self._apply_delay(
                    self._emt_initial_delay, initial_lower_val, time_array, lower_envelope
                )
                power_at_pcc = self._apply_delay(
                    self._emt_initial_delay, initial_pcc_val, time_array, power_at_pcc
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
        Derives foundational system parameters central to power response evaluations.

        Parameters
        ----------
        D : float
            The specific damping factor value (D) being tested.
        H : float
            The specific inertia constant value (H) being tested.
        Xeff : float
            The effective reactance of the system setup (Xeff).

        Returns
        -------
        tuple[float, float, float, float]
            A tuple returning: the aggregated system reactance, the operational damping
            ratio (epsilon), the natural response frequency (wn), and the theoretical
            peak power calculation.
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

            if (alpha**2 - 4 * betha) < 0:  # Validates logic for Underdamped profiles
                # Calculate the natural frequency of oscillation (in rad/s)
                natural_frequency = np.sqrt(
                    base_angular_freq * voltage_product / (2 * H * total_reactance)
                )
                # Formulate the dimensionless damping ratio
                damping_ratio = (
                    D / (4 * H * natural_frequency) if natural_frequency > 0 else float("inf")
                )
            else:  # Validates logic for Overdamped profiles
                sqrt_term_val = alpha**2 - 4 * betha
                p1 = (alpha - np.sqrt(sqrt_term_val)) / 2
                p2 = (alpha + np.sqrt(sqrt_term_val)) / 2

                # Calculate the natural frequency of oscillation (in rad/s)
                natural_frequency = np.sqrt(
                    base_angular_freq * voltage_product / (2 * H * total_reactance)
                )
                # Formulate the dimensionless damping ratio
                damping_ratio = (p1 + p2) / (2 * np.sqrt(p1 * p2))

        # Define theoretical absolute peak power expected from the parameter shift
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
        Dynamically branches the delta_p execution logic relative to the derived
        damping ratio profile (overdamped vs. underdamped).

        Parameters
        ----------
        D : float
            The current system damping factor.
        H : float
            The current system inertia constant.
        Xeff : float
            The system's effective reactance.
        time_array : np.ndarray
            The continuous time array mapped for the simulation window.
        event_time : float
            The absolute time marking event initialization.

        Returns
        -------
        tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray], float, float]
            A tuple returning: the base delta_p waveform array, the optional min/max
            exponential envelopes (if underdamped), the absolute peak power evaluation,
            and the executed damping ratio.
        """
        _, damping_ratio, _, _ = self._calculate_common_params(D, H, Xeff)

        # An Epsilon value >= 1 inherently indicates an overdamped or critically damped state.
        if damping_ratio >= 1:
            delta_p, p_peak, calculated_epsilon = self._get_overdamped_delta_p(
                D, H, Xeff, time_array, event_time
            )
            return delta_p, None, None, p_peak, calculated_epsilon
        else:  # An Epsilon value < 1 explicitly confirms an underdamped behavior profile.
            delta_p, delta_p_min, delta_p_max, p_peak, calculated_epsilon = (
                self._get_underdamped_delta_p(D, H, Xeff, time_array, event_time)
            )
            return delta_p, delta_p_min, delta_p_max, p_peak, calculated_epsilon

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Mathematically resolves the second-order differential equation constructing
        the foundational delta_p waveform defining an overdamped response.

        Parameters
        ----------
        D : float
            The system damping factor.
        H : float
            The system inertia constant.
        Xeff : float
            The effective reactance value.
        time_array : np.ndarray
            The zero-aligned array establishing timeline boundaries (t=0 mapped to the event).

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple returning the unshifted base delta_p waveform, the theoretical peak
            power extraction, and the derived epsilon constant.
        """
        total_reactance, epsilon, _, peak_power = self._calculate_common_params(D, H, Xeff)

        # Extract roots defining the characteristic equation of the operational DE
        alpha_coeff = D / (2 * H)
        beta_coeff = self._base_angular_frequency / (2 * H * total_reactance)

        sqrt_term_val = alpha_coeff**2 - 4 * beta_coeff
        if sqrt_term_val < 0:
            logger.warning(
                "Negative sqrt term detected in overdamped execution; forced to 0 to prevent "
                "complex numbers."
            )
            sqrt_term_val = 0

        p1 = (alpha_coeff - np.sqrt(sqrt_term_val)) / 2
        p2 = (alpha_coeff + np.sqrt(sqrt_term_val)) / 2

        if abs(p2 - p1) < 1e-9:  # Logic handling strictly critically damped scenarios
            A = 0.5
            B = 0.5
        else:
            A = (2 * H * (-p1) + D) / ((p2 - p1) * (2 * H))
            B = (2 * H * (-p2) + D) / ((p1 - p2) * (2 * H))

        # Project the finalized form: p_peak * (A * e^(-p1*t) + B * e^(-p2*t))
        term1 = A * np.exp(-p1 * time_array)
        term2 = B * np.exp(-p2 * time_array)
        delta_p_base = peak_power * (term1 + term2)

        return delta_p_base, peak_power, epsilon

    def _get_overdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Truncates and aligns the foundational overdamped delta_p mapping by zeroing
        response vectors occurring prior to the event threshold.

        Parameters
        ----------
        D : float
            The system damping factor.
        H : float
            The system inertia constant.
        Xeff : float
            The effective system reactance.
        time_array : np.ndarray
            The full timeline array mapped for simulation evaluation.
        event_time : float
            The absolute threshold triggering the event data flow.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple returning the temporally mapped final delta_p, the peak power,
            and the applied epsilon.
        """
        # Formulate zero-floor offsets mapped directly to event initialization
        time_since_event = np.maximum(0, time_array - event_time)
        delta_p_base, p_peak, epsilon = self._get_overdamped_delta_p_base(
            D, H, Xeff, time_since_event
        )

        # Pre-event signals hold zero value, active signals are inverted post-event
        delta_p = np.where(time_array < event_time, 0, delta_p_base * -1)

        return delta_p, p_peak, epsilon

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
        """
        Mathematically synthesizes the oscillating delta_p base response, projecting
        bound limits exclusively required for underdamped evaluations.

        Parameters
        ----------
        D : float
            The system damping factor.
        H : float
            The system inertia constant.
        Xeff : float
            The calculated effective reactance.
        time_array : np.ndarray
            The zero-aligned time mapping block (t=0 anchored to the event).

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray, float, float]
            A tuple returning the foundational delta_p waveform, alongside explicitly
            derived min/max boundary envelopes, peak power tracking, and epsilon constants.
        """
        _, epsilon, natural_frequency, peak_power = self._calculate_common_params(D, H, Xeff)

        # Derive the explicitly damped operational frequency parameter
        damped_frequency = natural_frequency * np.sqrt(1 - epsilon**2)

        # Structure individual transient mathematical components resolving the underdamped DE
        exp_term = np.exp(-epsilon * natural_frequency * time_array)
        cos_term = np.cos(damped_frequency * time_array)
        sin_term = np.sin(damped_frequency * time_array)
        sin_coeff = (
            (D / (2 * H) - epsilon * natural_frequency) / damped_frequency
            if damped_frequency > 0
            else 0
        )

        # Aggregated solution resolves as an exponentially decaying sinusoidal wave
        delta_p_base = peak_power * -1 * (exp_term * cos_term + sin_coeff * exp_term * sin_term)

        amplitude_envelope = np.sqrt(1 + sin_coeff**2)
        delta_p_max_env = np.abs(amplitude_envelope * peak_power * exp_term)
        delta_p_min_env = -1 * delta_p_max_env

        return delta_p_base, delta_p_min_env, delta_p_max_env, peak_power, epsilon

    def _get_underdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
        """
        Truncates and aligns the oscillating underdamped elements, zeroing all vector
        arrays executing prior to the established threshold constraint.

        Parameters
        ----------
        D : float
            The system damping factor.
        H : float
            The system inertia constant.
        Xeff : float
            The active effective reactance parameter.
        time_array : np.ndarray
            The full continuous time mapping defining the evaluation scope.
        event_time : float
            The literal moment defining event logic initiation.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray, float, float]
            A tuple returning the temporally mapped delta_p waveform, bound min/max
            envelopes, explicit peak power evaluation, and epsilon constraint.
        """
        # Constrain processing solely mapping the temporal bounds extending post-event
        time_since_event = np.maximum(0, time_array - event_time)

        delta_p_base, min_env_base, max_env_base, p_peak, epsilon = (
            self._get_underdamped_delta_p_base(D, H, Xeff, time_since_event)
        )

        # Extinguish all generated analytical waveforms mapped before system activation
        delta_p = np.where(time_array < event_time, 0, delta_p_base)
        delta_p_min_env = np.where(time_array < event_time, 0, min_env_base)
        delta_p_max_env = np.where(time_array < event_time, 0, max_env_base)

        return delta_p, delta_p_min_env, delta_p_max_env, p_peak, epsilon

    def _get_tunnel(self, peak_power: float) -> float:
        """
        Calculates and maps the mathematical static tolerance margin ("tunnel"),
        outlining the required operational boundaries scaling relative to peak demand.

        Parameters
        ----------
        peak_power : float
            The absolute extracted peak change evaluated within the active power framework.

        Returns
        -------
        float
            The definitively formulated constant boundary margin value.
        """
        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * np.abs(peak_power),
        )
