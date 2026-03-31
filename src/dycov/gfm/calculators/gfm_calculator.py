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

from dycov.gfm import constants
from dycov.gfm.parameters import GFMParameters


class GFMCalculator:
    """
    Abstract base class for all Grid Forming (GFM) calculators.

    This class establishes the foundational attributes and abstract methods required
    for calculating response envelopes across various GFM events. It defines critical
    constants for parameter array indexing and establishes the mathematical threshold
    used for damping profile classification.
    """

    # Constants representing the indices for parameter variation arrays
    _ORIGINAL_PARAMS_IDX = 0
    _MINIMUM_PARAMS_IDX = 1
    _MAXIMUM_PARAMS_IDX = 2

    # Threshold defining the boundary between underdamped (< 1.0) and overdamped (>= 1.0) systems.
    # Note: Critically damped systems (exactly 1.0) are mathematically grouped with the overdamped
    # logic.
    _EPSILON_THRESHOLD = 1.0

    def __init__(self, gfm_params: GFMParameters) -> None:
        """
        Initializes the foundational GFMCalculator state using provided system parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            An object containing all necessary parameters parsed from the configuration
            files, required to perform subsequent GFM calculations.
        """
        self._scr = gfm_params.get_scr()
        self._min_ratio = gfm_params.get_min_ratio()
        self._max_ratio = gfm_params.get_max_ratio()
        self._is_emt_flag = gfm_params.is_emt()
        self._emt_initial_delay = gfm_params.get_emt_initial_delay()
        self._initial_voltage = gfm_params.get_initial_voltage()
        self._grid_voltage = gfm_params.get_grid_voltage()
        self._base_angular_frequency = gfm_params.get_base_angular_frequency()
        self._margin_low = gfm_params.get_margin_low()
        self._margin_high = gfm_params.get_margin_high()
        self._final_allowed_tunnel_pn = gfm_params.get_final_allowed_tunnel_pn()
        self._final_allowed_tunnel_variation = gfm_params.get_final_allowed_tunnel_variation()
        self._pmax_mois_tunnel = gfm_params.get_pmax_mois_tunnel()
        self._pmin_mois_tunnel = gfm_params.get_pmin_mois_tunnel()

        # Internal attributes designated for INI dump state validation and tracking
        self._d_vals = None
        self._h_vals = None
        self._epsilon_vals = None

    def get_plot_parameter_names(self) -> list[str]:
        """
        Abstract method to retrieve the list of parameter names relevant for UI plotting.

        This method establishes a contract and must be explicitly implemented by each
        concrete calculator subclass (e.g., PhaseJump, RoCoF).

        Returns
        -------
        list[str]
            A predefined list of parameter string identifiers to be displayed on the
            rendered plots.
        """
        raise NotImplementedError

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Abstract method defining the core execution pipeline for calculating response envelopes.

        Must be implemented by subclasses to handle specific event mathematics.

        Parameters
        ----------
        D : float
            The system damping factor.
        H : float
            The system inertia constant.
        Xeff : float
            The effective reactance of the system.
        time_array : np.ndarray
            The continuous array of time points mapping the simulation window.
        event_time : float
            The absolute time (in seconds) at which the grid event triggers.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - str: The symbolic identifier of the calculated magnitude (e.g., 'P', 'Iq').
            - np.ndarray: The finalized analytical signal at the Point of Common Coupling (PCC).
            - np.ndarray: The array representing the upper operational envelope constraint.
            - np.ndarray: The array representing the lower operational envelope constraint.
        """
        raise NotImplementedError

    def _apply_delay(
        self,
        delay_time: float,
        delayed_value: float,
        time_array: np.ndarray,
        signal: np.ndarray,
        start_time: float = 0.0,
    ) -> np.ndarray:
        """
        Applies a temporal right-shift delay to a specified signal starting at a given coordinate.

        This mechanism holds the signal in its original state for t < start_time. Upon
        reaching t = start_time, it forcibly inserts the `delayed_value` for the exact duration
        of the specified delay, pushing all subsequent original signal values forward in time.

        Parameters
        ----------
        delay_time : float
            The required temporal shift duration (in seconds) to delay the signal.
        delayed_value : float
            The static placeholder value to maintain throughout the duration of the delay.
        time_array : np.ndarray
            The foundational time array defining the simulation steps.
        signal : np.ndarray
            The source signal array targeted for the temporal shift.
        start_time : float, optional
            The absolute time coordinate where the delay insertion should begin. Defaults to 0.0.

        Returns
        -------
        np.ndarray
            The processed signal array, strictly truncated to match the original array length.
        """
        # Step 1: Derive the simulation sample step (dt) assuming a uniformly spaced time array
        dt = time_array[1] - time_array[0]

        # Step 2: Translate the continuous delay time into a discrete sample count
        delay_samples = int(delay_time / dt) + 1

        # Safety Check: If the requested start time exceeds the simulation horizon, abort
        # modification
        if start_time > time_array[-1]:
            return signal

        # Step 3: Isolate the precise index corresponding to the delay initiation threshold
        start_idx = np.argmax(time_array >= start_time)

        # Step 4: Construct the constituent parts of the new shifted signal
        pre_delay_signal = signal[:start_idx]
        delay_block = np.full(delay_samples, delayed_value)
        post_delay_signal = signal[start_idx:]

        # Step 5: Synthesize the full array by concatenating the unshifted, delayed, and shifted
        # blocks
        combined_signal = np.concatenate((pre_delay_signal, delay_block, post_delay_signal))

        # Step 6: Enforce array dimensional consistency by truncating overflow data
        return combined_signal[: len(time_array)]

    def _cut_signal(self, value_min: float, signal: np.ndarray, value_max: float) -> np.ndarray:
        """
        Enforces absolute boundary constraints by clipping signal values that exceed
        specified operational limits.

        Parameters
        ----------
        value_min : float
            The absolute minimum allowable value threshold.
        signal : np.ndarray
            The target signal array to be constrained.
        value_max : float
            The absolute maximum allowable value threshold.

        Returns
        -------
        np.ndarray
            The definitively constrained signal array bounded within [value_min, value_max].
        """
        signal = np.where(signal < value_min, value_min, signal)
        signal = np.where(signal > value_max, value_max, signal)
        return signal

    def _calculate_epsilon_initial_check(
        self, D: np.ndarray, H: np.ndarray, x_total_initial: float
    ) -> np.ndarray:
        """
        Computes the dimensionless damping ratio (epsilon) to mathematically classify
        the system's dynamic response archetype (overdamped vs. underdamped).

        Parameters
        ----------
        D : np.ndarray
            An array containing the evaluated system damping factors.
        H : np.ndarray
            An array containing the evaluated system inertia constants.
        x_total_initial : float
            The aggregated initial reactance of the total system.

        Returns
        -------
        np.ndarray
            An array populated with the calculated damping ratios (epsilon) corresponding
            to each variation pair.
        """
        return (
            D
            / 2
            * np.sqrt(
                x_total_initial
                / (
                    2
                    * H
                    * self._base_angular_frequency
                    * self._initial_voltage
                    * self._grid_voltage
                )
            )
        )

    def _get_time_tunnel(
        self, p_peak: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Generates a dynamic, time-dependent tolerance band ("tunnel") mapped to the response.

        This mathematical structure dictates a variable operational tolerance margin that
        remains strictly zero prior to the event, and then expands exponentially towards
        a predefined asymptotic magnitude threshold post-event.

        Parameters
        ----------
        p_peak : float
            The theoretical absolute peak power deviation used to scale the tunnel's final
            amplitude.
        time_array : np.ndarray
            The continuous time array mapped for the simulation.
        event_time : float
            The absolute coordinate initiating the event and triggering the tunnel expansion.

        Returns
        -------
        np.ndarray
            The synthesized, time-dependent tolerance boundary array.
        """
        t_val = max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * p_peak,
        )
        tunnel_exp = 1 - np.exp(
            (-time_array + constants.TIME_TUNNEL_START_OFFSET) / constants.TIME_TUNNEL_EXP_TAU
        )
        tunnel = t_val * tunnel_exp
        return np.where(time_array < event_time, 0, tunnel)

    def _calculate_unlimited_power_envelopes(
        self, list_of_arrays: list[np.ndarray], tunnel: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Synthesizes the theoretical absolute bounding envelopes before hardware constraints
        are applied.

        The process aggregates the minimum and maximum boundaries across all generated
        delta_p deviation arrays and superimposes the expanding time-dependent tunnel.

        Parameters
        ----------
        list_of_arrays : list[np.ndarray]
            A list containing all candidate delta_p arrays (e.g., nominal, min/max variations)
            used to evaluate the extreme bounds of the system response.
        tunnel : np.ndarray
            The dynamic, time-dependent tunnel margin array.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple returning:
            - np.ndarray: The analytically determined unlimited lower boundary trace.
            - np.ndarray: The analytically determined unlimited upper boundary trace.
        """
        lower_env = np.minimum.reduce(list_of_arrays) - tunnel
        upper_env = np.maximum.reduce(list_of_arrays) + tunnel
        return np.minimum(lower_env, upper_env), np.maximum(lower_env, upper_env)

    def _limit_power_envelopes(
        self,
        lower_envelope_unlimited: np.ndarray,
        upper_envelope_unlimited: np.ndarray,
        tunnel_value: float,
        initial_power: float,
        max_power: float,
        min_power: float,
        sign: int,
        use_opposite_signs: bool,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Executes the final operational constraint logic, strictly mapping the theoretical
        envelopes to definitive hardware and software saturation boundaries.

        This method shifts the normalized arrays using the initial steady-state power (P0)
        and securely clips them to predefined capability thresholds.

        Parameters
        ----------
        lower_envelope_unlimited : np.ndarray
            The unconstrained lower boundary, strictly representing relative deviation
            (not yet shifted by P0).
        upper_envelope_unlimited : np.ndarray
            The unconstrained upper boundary, strictly representing relative deviation
            (not yet shifted by P0).
        tunnel_value : float
            The static margin value incorporated into the final boundary limitation.
        initial_power : float
            The absolute initial baseline power (active or reactive) characterizing steady state.
        max_power : float
            The absolute maximum physical capability limit of the system.
        min_power : float
            The absolute minimum physical capability limit of the system.
        sign : int
            The directional indicator defining the nature of the disturbance (e.g., phase
            variation direction).
        use_opposite_signs : bool
            A flag determining if specialized asymmetrical clipping logic must be applied based
            on trajectory.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple returning the securely limited, real-world lower and upper operational
            envelopes.
        """

        limit_max = self._pmax_mois_tunnel
        limit_min = self._pmin_mois_tunnel

        if use_opposite_signs:
            # Execution branch applying divergent clipping dependent on trajectory vs steady-state
            # opposition
            if np.sign(initial_power) * sign == -1:
                lower_envelope_limited = np.minimum(
                    np.maximum(
                        initial_power - sign * lower_envelope_unlimited,
                        limit_min,
                    ),
                    limit_max,
                )
                upper_envelope_limited = np.minimum(
                    np.maximum(
                        initial_power - sign * upper_envelope_unlimited,
                        min_power,
                    ),
                    max_power,
                )
            else:
                lower_envelope_limited = np.minimum(
                    np.maximum(
                        initial_power - sign * lower_envelope_unlimited,
                        min_power,
                    ),
                    max_power,
                )
                upper_envelope_limited = np.minimum(
                    np.maximum(
                        initial_power - sign * upper_envelope_unlimited,
                        limit_min,
                    ),
                    limit_max,
                )

        else:
            # Standard unified execution branch handling symmetrical capability bounding
            lower_envelope_limited = np.minimum(
                np.maximum(
                    initial_power - sign * lower_envelope_unlimited,
                    limit_min,
                ),
                limit_max,
            )
            upper_envelope_limited = np.minimum(
                np.maximum(
                    initial_power - sign * upper_envelope_unlimited,
                    min_power,
                ),
                max_power,
            )

        return lower_envelope_limited, upper_envelope_limited
