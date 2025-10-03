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


class SCRJump(GFMCalculator):
    """
    Class to calculate the GFM response to an SCR (Short-Circuit Ratio) Jump.

    This class handles all core calculations for delta_p and active power
    envelopes, differentiating between overdamped and underdamped system
    responses.
    """

    def __init__(self, gfm_params: GFMParameters) -> None:
        """
        Initializes the SCRJump calculator with GFM parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            An object containing all necessary parameters for the GFM
            calculations.
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

    def get_plot_parameter_names(self) -> list[str]:
        """Returns the list of parameter names relevant for SCRJump plots."""
        return ["P0", "Q0", "SCRinitial", "SCRfinal", "Xeff", "D", "H"]

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the change in power (delta_p) and active power envelopes
        (PCC, upper, and lower) for an SCR jump event.

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
            - magnitude_name: The name of the calculated magnitude ("P").
            - pcc_signal: The final calculated active power at the PCC.
            - upper_envelope: The final upper active power envelope.
            - lower_envelope: The final lower active power envelope.
        """
        logger.debug(f"Input Params D={D} H={H} Xeff {Xeff}")

        # Step 1: Calculate DeltaP for different D and H variations
        (
            delta_p_array,
            delta_p_min_env,
            delta_p_max_env,
            p_peak_array,
            _,
        ) = self._get_delta_p(
            D=D,
            H=H,
            Xeff=Xeff,
            time_array=time_array,
            event_time=event_time,
        )

        # Step 2: Generate final envelopes from all DeltaP candidates
        p_pcc, p_up, p_down = self._get_envelopes(
            delta_p_array=delta_p_array,
            delta_p_min_env_array=delta_p_min_env,
            delta_p_max_env_array=delta_p_max_env,
            p_peak_array=p_peak_array,
            time_array=time_array,
            event_time=event_time,
        )

        magnitude_name = "P"
        return magnitude_name, p_pcc, p_up, p_down

    def _get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates delta_p for the nominal D, H and their variations. This is
        the core dispatcher that determines the system's damping behavior.

        Parameters
        ----------
        D : float
            Nominal damping factor.
        H : float
            Nominal inertia constant.
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Array of time points for the simulation.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]
            A tuple of arrays containing: delta_p waveforms, min exponential
            envelopes, max exponential envelopes, peak power changes, and
            damping ratios for each D,H pair.
        """
        d_values = np.array([D, D * self._min_ratio, D * self._max_ratio])
        h_values = np.array([H, H / self._min_ratio, H / self._max_ratio])

        num_variations = len(d_values)
        num_time_points = len(time_array)

        delta_p_array = np.zeros((num_variations, num_time_points))
        delta_p_min_env_array = np.full((num_variations, num_time_points), np.nan)
        delta_p_max_env_array = np.full((num_variations, num_time_points), np.nan)
        p_peak_array = np.zeros(num_variations)
        epsilon_array = np.zeros(num_variations)

        for i in range(num_variations):
            delta_p, delta_p_min, delta_p_max, p_peak, epsilon = (
                self._calculate_delta_p_for_damping(
                    d_values[i], h_values[i], Xeff, time_array, event_time
                )
            )
            delta_p_array[i, :] = delta_p
            p_peak_array[i] = p_peak
            epsilon_array[i] = epsilon

            if delta_p_min is not None:
                delta_p_min_env_array[i, :] = delta_p_min
            if delta_p_max is not None:
                delta_p_max_env_array[i, :] = delta_p_max

        return (
            delta_p_array,
            delta_p_min_env_array,
            delta_p_max_env_array,
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
        Modifies an envelope by holding it at 50% of the expected power change
        for the first 30 ms after the event.

        Parameters
        ----------
        signal : np.ndarray
            The original envelope signal to be modified.
        p_50_percent : np.ndarray
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
        mask = (time_array >= event_time) & (
            time_array <= event_time + constants.SCRJUMP_MODIFY_ENVELOPE_S
        )
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
        Generates the upper and lower envelope traces based on a delta_p
        waveform, intentionally replicating legacy inconsistencies.

        Parameters
        ----------
        delta_p : np.ndarray
            The change in power waveform.
        time_array : np.ndarray
            Array of time points for the simulation.
        event_time : float
            The time at which the event occurs.
        tunnel : float
            The tolerance tunnel value to be applied.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing the upper and lower envelope traces.
        """
        event_idx = np.searchsorted(time_array, event_time + 0.01, side="right")
        delta_p_at_event = delta_p[event_idx] if event_idx < len(delta_p) else 0

        if delta_p_at_event > 0:
            # Correct behavior: use event_time as reference
            p_50_percent = self._initial_active_power + np.where(
                time_array >= event_time, delta_p * 0.5 + 0.005, delta_p
            )

            p_up_trace = self._initial_active_power + delta_p * (1 + self._margin_high) + tunnel
            p_down_trace = self._initial_active_power + delta_p * (1 - self._margin_low) - tunnel
            p_down_trace = self._modify_envelope(
                p_down_trace, p_50_percent, time_array, event_time
            )

            mask = time_array >= event_time
            condition = mask & (p_down_trace > self._max_active_power * 0.95)
            p_down_trace = np.where(condition, self._max_active_power * 0.95, p_down_trace)

        else:
            # Inconsistent legacy behavior: use start_time as reference
            # This is intentionally preserved to match the original script.
            start_time = time_array[0]
            p_50_percent = self._initial_active_power + np.where(
                time_array >= start_time, delta_p * 0.5 + 0.005, delta_p
            )

            p_up_trace = self._initial_active_power + delta_p * (1 - self._margin_high) + tunnel
            p_up_trace = self._modify_envelope(p_up_trace, p_50_percent, time_array, event_time)

            mask = time_array >= event_time
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
        Applies a limit to the envelopes for the first 100 ms to prevent
        unrealistic reverse power excursions.

        Parameters
        ----------
        p_up : np.ndarray
            The upper envelope signal.
        p_down : np.ndarray
            The lower envelope signal.
        delta_p : np.ndarray
            The nominal change in power waveform to determine event direction.
        time_array : np.ndarray
            Array of time points for the simulation.
        event_time : float
            The time at which the event occurs.
        tunnel : float
            The tolerance tunnel value.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing the limited upper and lower envelopes.
        """
        event_idx = np.searchsorted(time_array, event_time + 0.01, side="right")
        delta_p_at_event = delta_p[event_idx] if event_idx < len(delta_p) else 0

        mask = (time_array >= event_time) & (
            time_array <= event_time + constants.SCRJUMP_INITIAL_LIMITING_S
        )

        if delta_p_at_event > 0:
            condition = mask & (p_down < (self._initial_active_power - tunnel))
            p_down = np.where(condition, self._initial_active_power - tunnel, p_down)
        else:
            condition = mask & (p_up > (self._initial_active_power + tunnel))
            p_up = np.where(condition, self._initial_active_power + tunnel, p_up)

        return p_up, p_down

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
            A tuple containing the final PCC, upper, and lower power signals.
        """
        p_up_candidates = []
        p_down_candidates = []

        for i in range(delta_p_array.shape[0]):
            delta_p = delta_p_array[i, :]
            p_peak = p_peak_array[i]
            tunnel = self._get_tunnel(p_peak)

            p_up_trace, p_down_trace = self._get_envelope_traces(
                delta_p, time_array, event_time, tunnel
            )
            p_up_candidates.append(p_up_trace)
            p_down_candidates.append(p_down_trace)

            if not np.isnan(delta_p_min_env_array[i, 0]):
                p_up_from_min, p_down_from_min = self._get_envelope_traces(
                    delta_p_min_env_array[i, :], time_array, event_time, tunnel
                )
                p_up_candidates.append(p_up_from_min)
                p_down_candidates.append(p_down_from_min)

            if not np.isnan(delta_p_max_env_array[i, 0]):
                p_up_from_max, p_down_from_max = self._get_envelope_traces(
                    delta_p_max_env_array[i, :], time_array, event_time, tunnel
                )
                p_up_candidates.append(p_up_from_max)
                p_down_candidates.append(p_down_from_max)

        delta_p_nominal = delta_p_array[0, :]
        p_50_percent = self._initial_active_power + delta_p_nominal * 0.5
        p_up_candidates.append(p_50_percent)
        p_down_candidates.append(p_50_percent)

        p_up_matrix = np.vstack(p_up_candidates)
        p_down_matrix = np.vstack(p_down_candidates)

        p_up_combined = np.nanmax(p_up_matrix, axis=0)
        p_down_combined = np.nanmin(p_down_matrix, axis=0)

        p_pcc = self._initial_active_power + delta_p_nominal

        p_up_limited = self._limit_signal(p_up_combined)
        p_down_limited = self._limit_signal(p_down_combined)

        tunnel_nominal = self._get_tunnel(p_peak_array[0])
        upper_envelope, lower_envelope = self._apply_initial_limiting(
            p_up_limited,
            p_down_limited,
            delta_p_nominal,
            time_array,
            event_time,
            tunnel_nominal,
        )

        if self._is_emt_flag:
            upper_envelope = self._apply_delay(
                constants.EMT_FINAL_DELAY_S, upper_envelope[0], time_array, upper_envelope
            )
            lower_envelope = self._apply_delay(
                constants.EMT_FINAL_DELAY_S, lower_envelope[0], time_array, lower_envelope
            )
            p_pcc = self._apply_delay(constants.EMT_FINAL_DELAY_S, p_pcc[0], time_array, p_pcc)

        return p_pcc, upper_envelope, lower_envelope

    def _calculate_common_params(
        self, D: float, H: float, Xeff: float
    ) -> tuple[float, float, float, float]:
        """
        Calculates common parameters: total reactance, epsilon, wn, and p_peak.

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
            A tuple containing: total initial reactance, damping ratio,
            natural frequency, and calculated peak power change.
        """
        x_total_initial = Xeff + 1 / self._final_scr
        u_prod = self._initial_voltage * self._grid_voltage
        wb = self._base_angular_frequency

        if H <= 0 or x_total_initial <= 0:
            wn = 0
            epsilon = float("inf")
        else:
            wn = np.sqrt(wb * u_prod / (2 * H * x_total_initial))
            epsilon = D / (4 * H * wn) if wn > 0 else float("inf")

        p_peak_calc = (
            self._delta_impedance * self._initial_active_power / x_total_initial
            if x_total_initial > 0
            else 0
        )
        return x_total_initial, epsilon, wn, p_peak_calc

    def _calculate_delta_p_for_damping(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None, float, float]:
        """
        Selects the delta_p calculation method based on the damping ratio (epsilon).

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
            Time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, np.ndarray | None, np.ndarray | None, float, float]
            A tuple containing: the delta_p waveform, min envelope (None if
            overdamped), max envelope (None if overdamped), peak power change,
            and damping ratio.
        """
        _, epsilon, _, _ = self._calculate_common_params(D, H, Xeff)

        if epsilon >= 1:
            delta_p, p_peak, epsilon_calc = self._get_overdamped_delta_p(
                D, H, Xeff, time_array, event_time
            )
            return delta_p, None, None, p_peak, epsilon_calc
        else:
            delta_p, delta_p_min, delta_p_max, p_peak, epsilon_calc = (
                self._get_underdamped_delta_p(D, H, Xeff, time_array, event_time)
            )
            return delta_p, delta_p_min, delta_p_max, p_peak, epsilon_calc

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
            Time array for the simulation, starting from t=0 at the event.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing the base delta_p, peak power, and epsilon.
        """
        x_total, epsilon, _, p_peak = self._calculate_common_params(D, H, Xeff)

        alpha_val = D / (2 * H)
        beta_val = self._base_angular_frequency / (2 * H * x_total)

        sqrt_term = alpha_val**2 - 4 * beta_val
        if sqrt_term < 0:
            logger.warning(
                "Negative sqrt term in overdamped calc, may be misclassified. Clamping to 0."
            )
            sqrt_term = 0

        p1 = (alpha_val - np.sqrt(sqrt_term)) / 2
        p2 = (alpha_val + np.sqrt(sqrt_term)) / 2

        if abs(p2 - p1) < 1e-9:
            A = 0.5
            B = 0.5
        else:
            A = (2 * H * (-p1) + D) / ((p2 - p1) * (2 * H))
            B = (2 * H * (-p2) + D) / ((p1 - p2) * (2 * H))

        term1 = A * np.exp(-p1 * time_array)
        term2 = B * np.exp(-p2 * time_array)

        delta_p_base = p_peak * (term1 + term2)

        return delta_p_base, p_peak, epsilon

    def _get_overdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates final delta_p for an overdamped system by applying event time.

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
            A tuple containing the final delta_p, p_peak, and epsilon.
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
        """
        Calculates the base delta_p and its envelopes for an underdamped system.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Time array for the simulation, starting from t=0 at the event.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray, float, float]
            A tuple containing delta_p, min/max envelopes, p_peak, and epsilon.
        """
        _, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)

        wd = wn * np.sqrt(1 - epsilon**2)

        exp_term = np.exp(-epsilon * wn * time_array)
        cos_term = np.cos(wd * time_array)
        sin_term = np.sin(wd * time_array)
        sin_coeff = (D / (2 * H) - epsilon * wn) / wd if wd > 0 else 0

        delta_p_base = p_peak * -1 * (exp_term * cos_term + sin_coeff * exp_term * sin_term)

        amplitude_envelope = np.sqrt(1 + sin_coeff**2)
        delta_p_max_env = np.abs(amplitude_envelope * p_peak * exp_term)
        delta_p_min_env = -1 * delta_p_max_env

        return delta_p_base, delta_p_min_env, delta_p_max_env, p_peak, epsilon

    def _get_underdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
        """
        Calculates final delta_p and envelopes for an underdamped system.

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
            A tuple containing delta_p, min/max envelopes, p_peak, and epsilon.
        """
        time_since_event = np.maximum(0, time_array - event_time)

        delta_p_base, min_env_base, max_env_base, p_peak, epsilon = (
            self._get_underdamped_delta_p_base(D, H, Xeff, time_since_event)
        )

        delta_p = np.where(time_array < event_time, 0, delta_p_base)
        delta_p_min_env = np.where(time_array < event_time, 0, min_env_base)
        delta_p_max_env = np.where(time_array < event_time, 0, max_env_base)

        return delta_p, delta_p_min_env, delta_p_max_env, p_peak, epsilon

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
