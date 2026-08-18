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
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.parameters import GFMParameters
from dycov.logging.logging import dycov_logging


class PhaseJump(GFMCalculator):
    """
    Calculator class dedicated to handling the GFM response to a phase jump event.

    This class performs all core calculations for active power deviations (delta_p)
    and synthesizes the operational boundary envelopes. It employs distinct
    mathematical strategies to differentiate between overdamped and underdamped
    system responses.
    """

    def __init__(
        self,
        gfm_params: GFMParameters,
    ) -> None:
        """
        Initializes the PhaseJump calculator with the specified Grid Forming parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            An object containing all necessary parameters required for the GFM
            calculations, including specific settings for phase variations.
        """
        super().__init__(gfm_params=gfm_params)

        # Load specific parameters governing the phase jump response boundaries
        self._delta_phase = gfm_params.get_delta_phase()
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()

    def get_plot_parameter_names(self) -> list[str]:
        """
        Retrieves the list of parameter names relevant for rendering PhaseJump plots.

        Returns
        -------
        list[str]
            A predefined list of string identifiers corresponding to the parameters
            displayed on the output plots.
        """
        return ["P0", "Q0", "DeltaPhase", "AngleStepAtPDR", "SCR", "Xeff", "D", "H", "Epsilon"]

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the active power deviation (delta_p) and its bounding envelopes
        (PCC, upper, and lower) evaluated across a phase jump event timeframe.

        Parameters
        ----------
        D : float
            The system damping factor.
        H : float
            The system inertia constant.
        Xeff : float
            The effective reactance of the system.
        time_array : np.ndarray
            The array of time points corresponding to the simulation window.
        event_time : float
            The absolute time (in seconds) at which the phase jump event initiates.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - str: The physical magnitude identifier (e.g., "Ip").
            - np.ndarray: The main calculated active power signal at the PCC.
            - np.ndarray: The upper bounded active power envelope constraint.
            - np.ndarray: The lower bounded active power envelope constraint.
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

        # Retain current validation parameters for serialization and debugging dumps
        self._d_val = D
        self._h_val = H
        _, self._epsilon, _, _ = self._calculate_common_params(D, H, Xeff)

        # Dispatch core calculation to retrieve foundational waveforms and peak values
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

        # Synthesize the final definitive envelopes from the candidate traces
        p_pcc, p_up, p_down = self._get_envelopes(
            delta_p_array=delta_p_array,
            delta_p_min=delta_p_min,
            delta_p_max=delta_p_max,
            p_peak_array=p_peak_array,
            time_array=time_array,
            event_time=event_time,
        )

        # Apply a uniform delay translation if utilizing the Electro-Magnetic Transients (EMT)
        # engine
        if self._is_emt_flag:
            upper_envelope = self._apply_delay(self._emt_initial_delay, p_up[0], time_array, p_up)
            lower_envelope = self._apply_delay(
                self._emt_initial_delay, p_down[0], time_array, p_down
            )
            pcc_signal = self._apply_delay(self._emt_initial_delay, p_pcc[0], time_array, p_pcc)
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
        Computes the delta_p sequences across nominal, minimum, and maximum
        parameter variations, taking the damping profile into consideration.

        Parameters
        ----------
        D : float
            The nominal system damping factor.
        H : float
            The nominal system inertia constant.
        Xeff : float
            The effective reactance of the system.
        time_array : np.ndarray
            The continuous time array mapped for the simulation window.
        event_time : float
            The absolute time at which the event initiates.

        Returns
        -------
        tuple[list[np.ndarray], np.ndarray, np.ndarray, list[float], list[float]]
            A tuple returning:
            - list[np.ndarray]: The sequence of base delta_p variation arrays.
            - np.ndarray: The specifically calculated minimum delta_p constraint array.
            - np.ndarray: The specifically calculated maximum delta_p constraint array.
            - list[float]: The evaluated peak active power values for each variation.
            - list[float]: The extracted damping ratios (epsilon) corresponding to the variations.
        """
        x_gr = 1 / self._scr
        x_total_initial = Xeff + x_gr

        # Formulate testing vectors mapping nominal values and their extreme boundaries
        d_array = np.array([D, D * self._min_ratio, D * self._max_ratio])
        h_array = np.array([H, H * self._min_ratio, H * self._max_ratio])

        # Validate base damping archetypes across the variation spectrum
        epsilon_initial_check = self._calculate_epsilon_initial_check(
            d_array, h_array, x_total_initial
        )
        dycov_logging.get_logger("PhaseJump").debug(f"Epsilon={epsilon_initial_check}")

        delta_p_array: list[np.ndarray] = []
        p_peak_array: list[float] = []
        epsilon_array: list[float] = []

        # Generate fundamental response traces for each permutation
        for i in range(len(d_array)):
            delta_p, p_peak, epsilon = self._calculate_delta_p_for_damping(
                d_array[i], h_array[i], Xeff, time_array, event_time, epsilon_initial_check[i]
            )
            delta_p_array.append(delta_p)
            p_peak_array.append(p_peak)
            epsilon_array.append(epsilon)

        # Dispatch bounding envelope generation based strictly on the nominal damping
        # classification
        if epsilon_initial_check[self._ORIGINAL_PARAMS_IDX] > self._EPSILON_THRESHOLD:
            delta_p_min = self._get_overdamped_delta_p_min(D, H, Xeff, time_array, event_time)
            delta_p_max = self._get_overdamped_delta_p_max(D, H, Xeff, time_array, event_time)
        else:
            delta_p_min = self._get_underdamped_delta_p_min(D, H, Xeff, time_array, event_time)
            delta_p_max = self._get_underdamped_delta_p_max(D, H, Xeff, time_array, event_time)

        # Register configurations internally for state evaluation tracking
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
        Consolidates raw traces to calculate and limit the final active power envelopes
        (inclusive of the primary PCC signal and its upper/lower thresholds).

        Parameters
        ----------
        delta_p_array : list[np.ndarray]
            The foundational list of delta_p traces evaluating parameter drift.
        delta_p_min : np.ndarray
            The specific lower constraint array derived from the damping behavior.
        delta_p_max : np.ndarray
            The specific upper constraint array derived from the damping behavior.
        p_peak_array : list[float]
            The peak power values mapped to each parameter variation.
        time_array : np.ndarray
            The continuous time array defining the simulation scope.
        event_time : float
            The established trigger point for the phase variation event.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple returning the final synchronized PCC operational signal,
            along with its maximum allowable upper and lower boundary envelopes.
        """
        delta_p = delta_p_array[self._ORIGINAL_PARAMS_IDX]
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]
        sign = np.sign(self._delta_phase)

        # Acquire dynamic time-dependent tunnel mapping
        tunnel_time_dep = self._get_time_tunnel(
            p_peak=p_peak, time_array=time_array, event_time=event_time
        )

        # Baseline evaluation adjusting signal trajectory inversely to the delta_phase sign
        p_pcc = self._initial_active_power + delta_p * -(sign)

        list_of_arrays: list[np.ndarray] = delta_p_array + [delta_p_min, delta_p_max]

        # Extract theoretically unbound maximum capabilities from superimposed arrays
        lower_env_unlimited, upper_env_unlimited = self._calculate_unlimited_power_envelopes(
            list_of_arrays, tunnel_time_dep
        )

        # Confine the raw capability envelopes strictly within hardware constraints
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
        Derives fundamental mechanical and electrical parameters universally
        required for constructing the delta_p response waveforms.

        Parameters
        ----------
        D : float
            The system damping factor.
        H : float
            The system inertia constant.
        Xeff : float
            The effective reactance of the simulated setup.

        Returns
        -------
        tuple[float, float, float, float]
            A tuple containing: the aggregated system initial reactance, the calculated
            damping ratio (epsilon), the natural response frequency (wn), and the
            theoretically projected peak power (p_peak_calc).
        """
        x_gr = 1 / self._scr
        x_total_initial = Xeff + x_gr
        u_prod = self._initial_voltage * self._grid_voltage

        # Formulate the dimensionless damping ratio defining oscillatory potential
        epsilon = (
            D / 2 * np.sqrt(x_total_initial / (2 * H * self._base_angular_frequency * u_prod))
        )
        # Calculate the base natural frequency of the oscillation (rad/s)
        wn = np.sqrt(self._base_angular_frequency * u_prod / (2 * H * x_total_initial))

        delta_theta_rad = np.abs(self._delta_phase * np.pi / 180)

        # Project theoretical absolute maximum deviation utilizing angular displacement
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
        Acts as the primary execution dispatcher, routing the delta_p logic mathematically
        based on the system's verified damping state classification.

        Parameters
        ----------
        D : float
            The tested system damping factor.
        H : float
            The tested system inertia constant.
        Xeff : float
            The effective system reactance.
        time_array : np.ndarray
            The designated evaluation timeline array.
        event_time : float
            The absolute execution trigger coordinate.
        epsilon_initial_check : float
            The pre-calculated damping ratio establishing the required mathematical branch.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple resolving the required delta_p array, the peak response magnitude,
            and the associated epsilon value.
        """
        if epsilon_initial_check > self._EPSILON_THRESHOLD:
            return self._get_overdamped_delta_p(D, H, Xeff, time_array, event_time)
        else:
            return self._get_underdamped_delta_p(D, H, Xeff, time_array, event_time)

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Mathematically resolves the fundamental delta_p waveform defining an overdamped
        system, representing raw dynamic behavior devoid of event constraints.

        Parameters
        ----------
        D : float
            The system damping factor.
        H : float
            The system inertia constant.
        Xeff : float
            The effective operational reactance.
        time_array : np.ndarray
            The continuous time array anchored for mathematical generation.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple returning the continuous base delta_p waveform, the projected
            peak power derivation, and the epsilon constant.
        """
        _, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)
        wd = wn * np.sqrt(epsilon**2 - 1)

        # Alpha and Beta mathematically represent the real roots defining the overdamped
        # characteristic equation
        alpha = epsilon * wn + wd
        beta = epsilon * wn - wd

        # A and B formulate the initial integration constants for the second-order response
        A = 1 / (beta - alpha)
        B = -A

        # Deconstruct the solution into its elemental exponential decay responses
        term1 = 2 * H * A * (1 - alpha * np.exp(-alpha * time_array))
        term2 = 2 * H * B * (1 - beta * np.exp(-beta * time_array))
        term3 = D * A * np.exp(-alpha * time_array)
        term4 = D * B * np.exp(-beta * time_array)

        # Synthesize the final aggregated power deviation solution
        delta_p1 = (p_peak / (2 * H)) * (term1 + term2 + term3 + term4)
        return delta_p1, p_peak, epsilon

    def _get_overdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Truncates the calculated overdamped system delta_p to enforce strict
        zero-value stability before the specified event initiation.

        Parameters
        ----------
        D : float
            The system damping factor.
        H : float
            The system inertia constant.
        Xeff : float
            The system effective reactance.
        time_array : np.ndarray
            The simulation evaluation mapping block.
        event_time : float
            The absolute threshold triggering dynamic generation.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple returning the temporally mapped delta_p waveform, peak power,
            and the driving epsilon parameter.
        """
        delta_p1, p_peak, epsilon = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)

        # Apply the physical constraint rendering pre-event signals completely static
        delta_p = np.where(time_array < event_time, 0, delta_p1)
        return delta_p, p_peak, epsilon

    def _get_overdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Derives the minimum acceptable operational delta_p for an overdamped system
        by mathematically scaling down the base response utilizing the lower margin.

        Parameters
        ----------
        D : float
            The damping factor.
        H : float
            The inertia constant.
        Xeff : float
            The effective system reactance.
        time_array : np.ndarray
            The full simulation timeline mapping.
        event_time : float
            The defined initialization point for the event.

        Returns
        -------
        np.ndarray
            The calculated minimum bound delta_p array tailored for overdamped mechanics.
        """
        delta_p1, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p1_margined = (1 + self._margin_low) * delta_p1
        delta_p = np.where(time_array < event_time, 0, delta_p1_margined)
        return delta_p

    def _get_overdamped_delta_p_max(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Derives the maximum acceptable operational delta_p for an overdamped system
        by scaling the response and injecting an engineered delay parameter.

        Parameters
        ----------
        D : float
            The damping factor.
        H : float
            The inertia constant.
        Xeff : float
            The effective system reactance.
        time_array : np.ndarray
            The evaluation timeline structure.
        event_time : float
            The precise point marking event commencement.

        Returns
        -------
        np.ndarray
            The calculated maximum bound delta_p array strictly configured for
            overdamped behavior.
        """
        delta_p, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p_margined = self._margin_high * delta_p

        # Superimpose the static delay standard for bounding extreme conditions
        delta_p_delayed = self._apply_delay(
            constants.OVERDAMPED_MAX_DELAY_S, 0, time_array, delta_p_margined
        )
        delta_p = np.where(time_array < event_time, 0, delta_p_delayed)
        return delta_p

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> tuple[np.ndarray, float, float]:
        """
        Mathematically resolves the fundamental delta_p waveform capturing the
        oscillatory traits inherent to an underdamped dynamic response.

        Parameters
        ----------
        D : float
            The system damping factor.
        H : float
            The system inertia constant.
        Xeff : float
            The effective operational reactance.
        time_array : np.ndarray
            The continuous time array anchored for mathematical generation.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple returning the base oscillatory delta_p array, the absolute peak
            power extraction, and the derived epsilon constant.
        """
        _, epsilon, wn, p_peak = self._calculate_common_params(D, H, Xeff)

        # Calculate the adjusted damped natural frequency (wd) tracking the actual oscillation
        wd = wn * np.sqrt(1 - epsilon**2)

        # Synthesize components: An exponential decay boundary bounding sinusoidal oscillation
        term1 = np.exp(-epsilon * wn * time_array)
        term2 = np.cos(wd * time_array)
        term3 = np.sin(wd * time_array)

        # Aggregate the complete dynamic response
        delta_p1 = term1 * (term2 - (epsilon * wn - 1) / wd * term3) * p_peak
        return delta_p1, p_peak, epsilon

    def _get_underdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Truncates the calculated underdamped system delta_p, enforcing zero-state
        stability before the event trigger to align with physical constraints.

        Parameters
        ----------
        D : float
            The damping factor.
        H : float
            The inertia constant.
        Xeff : float
            The system effective reactance.
        time_array : np.ndarray
            The full timeline array mapped for simulation evaluation.
        event_time : float
            The operational threshold initiating dynamic tracking.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple yielding the constrained delta_p array, the evaluated peak power,
            and the applied epsilon metric.
        """
        delta_p1, p_peak, epsilon = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        delta_p = np.where(time_array < event_time, 0, delta_p1)
        return delta_p, p_peak, epsilon

    def _get_underdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Synthesizes the minimum bounding delta_p for an underdamped system utilizing
        a combination of lower margin scaling and mathematically defined exponential decay.

        Parameters
        ----------
        D : float
            The applied damping factor.
        H : float
            The applied inertia constant.
        Xeff : float
            The effective network reactance.
        time_array : np.ndarray
            The evaluation timeline map.
        event_time : float
            The absolute threshold triggering system evolution.

        Returns
        -------
        np.ndarray
            The specifically computed minimum delta_p boundary tailored to underdamped models.
        """
        _, p_peak, _ = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)

        # Formulate pure decay coefficient mapping bounding limits explicitly
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
        Synthesizes the maximum bounding delta_p for an underdamped system applying
        an upward operational margin and integrating a specific delay tracking mechanism.

        Parameters
        ----------
        D : float
            The system damping factor.
        H : float
            The system inertia constant.
        Xeff : float
            The determined effective reactance.
        time_array : np.ndarray
            The timeline mapping evaluated by the algorithm.
        event_time : float
            The defining event trigger moment.

        Returns
        -------
        np.ndarray
            The explicitly designated maximum delta_p envelope evaluating underdamped physics.
        """
        _, p_peak, _ = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)

        # Formulate pure decay coefficient tracking extreme upper bounds
        sigma = D / (4 * H)
        delta_p_margined = p_peak * (1 + self._margin_high) * np.exp(-sigma * time_array)

        delta_p_delayed = self._apply_delay(
            constants.UNDERDAMPED_MAX_DELAY_S, delta_p_margined[0], time_array, delta_p_margined
        )
        delta_p = np.where(time_array < event_time, 0, delta_p_delayed)
        return delta_p

    def _get_tunnel(self, p_peak_array: list[float]) -> float:
        """
        Derives the static tolerance margin "tunnel" outlining the acceptable operational
        power boundary relative to generated peak tracking.

        Parameters
        ----------
        p_peak_array : list[float]
            The list mapping tracked peak power shifts, with the zeroth element
            acting as the operational nominal standard.

        Returns
        -------
        float
            The statically extracted boundary limit required for evaluation constraints.
        """
        p_peak = p_peak_array[self._ORIGINAL_PARAMS_IDX]
        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * p_peak,
        )
