#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

from typing import NamedTuple, Optional

import numpy as np

from dycov.gfm import constants
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.parameters import GFMParameters
from dycov.logging import dycov_logging

LOGGER = dycov_logging.get_logger(__name__)


class _SwingParameters(NamedTuple):
    """The swing equation of the unit on the grid after the jump."""

    total_reactance: float
    damping_ratio: float
    natural_frequency: float
    peak_power_change: float


class SCRJump(GFMCalculator):
    """Handles the GFM response to a Short-Circuit Ratio (SCR) jump."""

    def __init__(self, gfm_params: GFMParameters) -> None:
        """
        Initializes the SCRJump calculator.

        Parameters
        ----------
        gfm_params : GFMParameters
            The shared configuration parameters.
        """
        super().__init__(gfm_params=gfm_params)

        initial_scr = gfm_params.get_initial_scr()
        self._final_scr = gfm_params.get_final_scr()
        self._delta_impedance = 1 / self._final_scr - 1 / initial_scr

        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()

        self._is_inconsistent = False
        self._disclaimer_message: Optional[str] = None

    def get_plot_parameter_names(self) -> list[str]:
        """
        Retrieves parameters relevant for rendering SCRJump plots.

        Returns
        -------
        list[str]
            A list of parameter names to be displayed.
        """
        return ["P0", "Q0", "SCRinitial", "SCRfinal", "Xeff", "D", "H", "Epsilon"]

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the active power deviation and bounding envelopes.

        Parameters
        ----------
        D : float
            The damping constant.
        H : float
            The inertia constant.
        Xeff : float
            The effective reactance.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp when the grid event occurs.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            The magnitude name ("Ip"), the main power signal, the upper envelope and the lower
            envelope.
        """
        LOGGER.debug(f"Input Params D={D} H={H} Xeff {Xeff}")

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
        return "Ip", power_at_pcc, upper_envelope, lower_envelope

    def _get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Computes the response of the nominal D and H and of their two variations.

        The variations change D and H in opposite directions: D times RatioMax with H times
        RatioMin, and D times RatioMin with H times RatioMax. A variation that damps differently
        from the others (one overdamped, another underdamped) marks the envelopes as
        inconsistent.

        Parameters
        ----------
        D : float
            The base damping constant.
        H : float
            The base inertia constant.
        Xeff : float
            The effective reactance.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp of the event.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]
            The delta_p of each variation, its lower and upper oscillation bounds (NaN for an
            overdamped one), its peak power and its damping ratio.
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
        self._check_damping_consistency(epsilon_results, damping_variations, inertia_variations)

        return (
            delta_p_results,
            min_envelope_results,
            max_envelope_results,
            peak_power_results,
            epsilon_results,
        )

    def _check_damping_consistency(
        self,
        epsilon_results: np.ndarray,
        damping_variations: np.ndarray,
        inertia_variations: np.ndarray,
    ) -> None:
        """
        Marks the envelopes as inconsistent when the variations do not all damp the same way.

        Parameters
        ----------
        epsilon_results : np.ndarray
            The damping ratio of each variation.
        damping_variations : np.ndarray
            The D of each variation.
        inertia_variations : np.ndarray
            The H of each variation.
        """
        is_overdamped = epsilon_results >= 1
        if np.all(is_overdamped == is_overdamped[0]):
            return

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
        LOGGER.warning(msg)
        self._is_inconsistent = True
        self._disclaimer_message = msg

    def _modify_envelope(
        self,
        envelope_signal: np.ndarray,
        power_at_50_percent: np.ndarray,
        time_array: np.ndarray,
        event_time: float,
    ) -> np.ndarray:
        """
        Anchors an envelope to 50% of the expected power change during the initial window.

        Parameters
        ----------
        envelope_signal : np.ndarray
            The raw envelope signal array.
        power_at_50_percent : np.ndarray
            The targeted 50% power threshold array.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp of the event.

        Returns
        -------
        np.ndarray
            The modified envelope signal.
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
        delta_p_at_event: float,
        delta_p_base: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Synthesizes upper and lower boundary traces from a delta_p waveform.

        The trace on the side the power moves away from is anchored to half the nominal change
        right after the event, and held at the MOIS limit wherever it was beyond it.

        Parameters
        ----------
        delta_p : np.ndarray
            The specific delta_p waveform.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp of the event.
        tunnel_value : float
            The static tolerance margin limit.
        delta_p_at_event : float
            The power change value at the moment of the event.
        delta_p_base : np.ndarray
            The nominal baseline power change.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            The upper and lower trace arrays.
        """
        power_rises = delta_p_at_event > 0
        upper_margin = (1 + self._margin_high) if power_rises else (1 - self._margin_high)
        lower_margin = (1 - self._margin_low) if power_rises else (1 + self._margin_low)
        upper_trace = self._initial_active_power + delta_p * upper_margin + tunnel_value
        lower_trace = self._initial_active_power + delta_p * lower_margin - tunnel_value

        power_at_50_percent = self._initial_active_power + np.where(
            time_array >= event_time, delta_p_base * 0.5 + 0.005, delta_p
        )
        time_mask = (time_array >= event_time) & (time_array <= constants.SIMULATION_END_TIME)

        if power_rises:
            beyond_mois = time_mask & (lower_trace > self._pmax_mois_tunnel)
            lower_trace = self._modify_envelope(
                lower_trace, power_at_50_percent, time_array, event_time
            )
            lower_trace = np.where(beyond_mois, self._pmax_mois_tunnel, lower_trace)
        else:
            beyond_mois = time_mask & (upper_trace < self._pmin_mois_tunnel)
            upper_trace = self._modify_envelope(
                upper_trace, power_at_50_percent, time_array, event_time
            )
            upper_trace = np.where(beyond_mois, self._pmin_mois_tunnel, upper_trace)

        return self._limit_signal(upper_trace), self._limit_signal(lower_trace)

    def _limit_signal(self, signal: np.ndarray) -> np.ndarray:
        """
        Utility function to enforce absolute active power hardware limits.

        Parameters
        ----------
        signal : np.ndarray
            The array to be constrained.

        Returns
        -------
        np.ndarray
            The limited signal array.
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
        Constructs active power envelopes by evaluating and merging traces.

        Each variation gives an upper and a lower trace. An underdamped one also gives an upper
        trace from the upper bound of its oscillation and a lower trace from the lower bound.
        Whether those extra traces, together with half the change of the last variation, take
        part in an envelope is decided by the last variation alone.

        Parameters
        ----------
        delta_p_array : np.ndarray
            Array containing power deviation trajectories.
        delta_p_min_env_array : np.ndarray
            Array of lower boundaries for underdamped cases.
        delta_p_max_env_array : np.ndarray
            Array of upper boundaries for underdamped cases.
        p_peak_array : np.ndarray
            Array of peak power deviations.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp of the event.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            The primary power trace, the upper envelope and the lower envelope.
        """
        upper_trace_candidates = []
        lower_trace_candidates = []
        upper_traces_from_max_env = []
        lower_traces_from_min_env = []

        delta_p_nominal = delta_p_array[0, :]
        delta_p_at_event = self._value_after(delta_p_nominal, time_array, event_time)

        def traces(delta_p: np.ndarray, tunnel_value: float) -> tuple[np.ndarray, np.ndarray]:
            return self._get_envelope_traces(
                delta_p=delta_p,
                time_array=time_array,
                event_time=event_time,
                tunnel_value=tunnel_value,
                delta_p_at_event=delta_p_at_event,
                delta_p_base=delta_p_nominal,
            )

        for i in range(delta_p_array.shape[0]):
            tunnel_value = self._get_tunnel(p_peak_array[i])

            upper_trace, lower_trace = traces(delta_p_array[i, :], tunnel_value)
            upper_trace_candidates.append(upper_trace)
            lower_trace_candidates.append(lower_trace)

            if not np.isnan(delta_p_max_env_array[i, 0]):
                upper_from_max, _ = traces(delta_p_max_env_array[i, :], tunnel_value)
                upper_traces_from_max_env.append(upper_from_max)

            if not np.isnan(delta_p_min_env_array[i, 0]):
                _, lower_from_min = traces(delta_p_min_env_array[i, :], tunnel_value)
                lower_traces_from_min_env.append(lower_from_min)

        last = delta_p_array.shape[0] - 1
        power_at_pcc = self._limit_signal(self._initial_active_power + delta_p_nominal)
        power_at_50_percent = self._limit_signal(
            self._initial_active_power + delta_p_array[last, :] * 0.5
        )

        if np.isnan(delta_p_max_env_array[last, 0]):
            upper_matrix = np.vstack(upper_trace_candidates)
        else:
            upper_matrix = np.vstack(
                (upper_trace_candidates, [power_at_50_percent], upper_traces_from_max_env)
            )
        if np.isnan(delta_p_min_env_array[last, 0]):
            lower_matrix = np.vstack(lower_trace_candidates)
        else:
            lower_matrix = np.vstack(
                (lower_trace_candidates, [power_at_50_percent], lower_traces_from_min_env)
            )

        rises_from_nonzero_power = delta_p_at_event > 0 and (
            self._initial_active_power > 0 or self._initial_active_power < 0
        )
        return self._delay_envelopes(
            power_at_pcc,
            np.nanmax(upper_matrix, axis=0),
            np.nanmin(lower_matrix, axis=0),
            rises_from_nonzero_power,
            time_array,
        )

    @staticmethod
    def _value_after(signal: np.ndarray, time_array: np.ndarray, time: float) -> float:
        """The value of signal at the first time step after time, or 0 if there is none."""
        index = np.searchsorted(time_array, time, side="right")
        return signal[index] if index < len(signal) else 0

    def _delay_envelopes(
        self,
        power_at_pcc: np.ndarray,
        upper_envelope: np.ndarray,
        lower_envelope: np.ndarray,
        rises_from_nonzero_power: bool,
        time_array: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Delays the envelopes so that they hold their pre-event side through the event.

        When the power rises at the event from a non-zero initial power, the lower envelope is
        delayed by SCR_BOUND_DELAY_S, plus the EMT delay in EMT mode, holding its initial value;
        in EMT mode the upper envelope and the power are also delayed, by the EMT delay, holding
        their maximum. Otherwise the roles swap: the upper envelope takes the first delay and
        the lower envelope and the power hold their minimum.

        Parameters
        ----------
        power_at_pcc : np.ndarray
            The expected power.
        upper_envelope : np.ndarray
            The upper envelope.
        lower_envelope : np.ndarray
            The lower envelope.
        rises_from_nonzero_power : bool
            Whether the power rises at the event from a non-zero initial power.
        time_array : np.ndarray
            The simulation time vector.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            The power, the upper envelope and the lower envelope, delayed.
        """
        bound_delay = (
            self._emt_delay + constants.SCR_BOUND_DELAY_S
            if self._is_emt_flag
            else constants.SCR_BOUND_DELAY_S
        )
        extreme = np.max if rises_from_nonzero_power else np.min

        def delay(signal: np.ndarray, delay_time: float, initial_value: float) -> np.ndarray:
            return self._apply_delay(delay_time, initial_value, time_array, signal)

        if rises_from_nonzero_power:
            if self._is_emt_flag:
                upper_envelope = delay(upper_envelope, self._emt_delay, extreme(upper_envelope))
            lower_envelope = delay(lower_envelope, bound_delay, lower_envelope[0])
        else:
            upper_envelope = delay(upper_envelope, bound_delay, upper_envelope[0])
            if self._is_emt_flag:
                lower_envelope = delay(lower_envelope, self._emt_delay, extreme(lower_envelope))
        if self._is_emt_flag:
            power_at_pcc = delay(power_at_pcc, self._emt_delay, extreme(power_at_pcc))
        return power_at_pcc, upper_envelope, lower_envelope

    def _calculate_common_params(self, D: float, H: float, Xeff: float) -> _SwingParameters:
        """
        Derives the swing equation after the jump.

        Parameters
        ----------
        D : float
            The damping constant.
        H : float
            The inertia constant.
        Xeff : float
            The effective reactance.

        Returns
        -------
        _SwingParameters
            The total reactance, damping ratio, natural frequency and peak power change.
        """
        total_reactance = Xeff + 1 / self._final_scr

        if H <= 0 or total_reactance <= 0:
            natural_frequency = 0
            damping_ratio = float("inf")
        else:
            alpha = D / (2 * H)
            betha = self._base_angular_frequency / (2 * H * total_reactance)
            natural_frequency = self._natural_frequency(H, total_reactance)

            if (alpha**2 - 4 * betha) < 0:
                damping_ratio = (
                    D / (4 * H * natural_frequency) if natural_frequency > 0 else float("inf")
                )
            else:
                sqrt_term_val = alpha**2 - 4 * betha
                p1 = (alpha - np.sqrt(sqrt_term_val)) / 2
                p2 = (alpha + np.sqrt(sqrt_term_val)) / 2
                damping_ratio = (p1 + p2) / (2 * np.sqrt(p1 * p2))

        peak_power_change = (
            (self._delta_impedance * self._initial_active_power / total_reactance)
            if total_reactance > 0
            else 0
        )

        return _SwingParameters(
            total_reactance, damping_ratio, natural_frequency, peak_power_change
        )

    def _calculate_delta_p_for_damping(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray], float, float]:
        """
        Calculates the response of one variation, overdamped or underdamped.

        Parameters
        ----------
        D : float
            The damping constant.
        H : float
            The inertia constant.
        Xeff : float
            The effective reactance.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp of the event.

        Returns
        -------
        tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray], float, float]
            The delta_p, its lower and upper oscillation bounds (None when overdamped), the
            peak power and the damping ratio.
        """
        swing = self._calculate_common_params(D, H, Xeff)
        time_since_event = np.maximum(0, time_array - event_time)
        before_event = time_array < event_time

        if swing.damping_ratio >= 1:
            delta_p_base = self._get_overdamped_delta_p_base(D, H, swing, time_since_event)
            delta_p = np.where(before_event, 0, delta_p_base * -1)
            return delta_p, None, None, swing.peak_power_change, swing.damping_ratio

        delta_p_base, min_env_base, max_env_base = self._get_underdamped_delta_p_base(
            D, H, swing, time_since_event
        )
        return (
            np.where(before_event, 0, delta_p_base),
            np.where(before_event, 0, min_env_base),
            np.where(before_event, 0, max_env_base),
            swing.peak_power_change,
            swing.damping_ratio,
        )

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, swing: _SwingParameters, time_array: np.ndarray
    ) -> np.ndarray:
        """
        Resolves the differential equation defining an overdamped response.

        Parameters
        ----------
        D : float
            The damping constant.
        H : float
            The inertia constant.
        swing : _SwingParameters
            The swing equation after the jump.
        time_array : np.ndarray
            The time since the event.

        Returns
        -------
        np.ndarray
            The power deviation, before its sign is turned.
        """
        alpha_coeff = D / (2 * H)
        beta_coeff = self._base_angular_frequency / (2 * H * swing.total_reactance)

        sqrt_term_val = alpha_coeff**2 - 4 * beta_coeff
        if sqrt_term_val < 0:
            LOGGER.warning("Negative sqrt term detected in overdamped execution; forced to 0.")
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
        return swing.peak_power_change * (term1 + term2)

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, swing: _SwingParameters, time_array: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Synthesizes the oscillating delta_p base response for underdamped evaluations.

        Parameters
        ----------
        D : float
            The damping constant.
        H : float
            The inertia constant.
        swing : _SwingParameters
            The swing equation after the jump.
        time_array : np.ndarray
            The time since the event.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            The power deviation and the lower and upper bounds of its oscillation.
        """
        epsilon = swing.damping_ratio
        natural_frequency = swing.natural_frequency
        peak_power = swing.peak_power_change

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

        return delta_p_base, delta_p_min_env, delta_p_max_env

    def _get_tunnel(self, peak_power: float) -> float:
        """
        Calculates and maps the mathematical static tolerance margin ('tunnel').

        Parameters
        ----------
        peak_power : float
            The peak power deviation used as a reference.

        Returns
        -------
        float
            The calculated tunnel margin in pu.
        """
        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * np.abs(peak_power),
        )
