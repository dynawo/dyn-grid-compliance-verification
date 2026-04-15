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


class AmplitudeStep(GFMCalculator):
    """Calculator class dedicated to handling the GFM amplitude step response.

    This module mathematically performs all core calculations for reactive current deviations
    (delta_iq) and synthesizes the corresponding bounding envelopes triggered by voltage amplitude
    variations within the grid.
    """

    def __init__(
        self,
        gfm_params: GFMParameters,
    ) -> None:
        """Initializes the AmplitudeStep calculator with the specified Grid Forming parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            An object containing all necessary parameters required for the GFM
            calculations, including specific settings for amplitude step evaluations.
        """
        super().__init__(gfm_params=gfm_params)
        self._voltage_step = gfm_params.get_voltage_step_at_grid()
        self._initial_reactive_power = gfm_params.get_initial_reactive_power()
        self._min_reactive_power = gfm_params.get_min_reactive_power()
        self._max_reactive_power = gfm_params.get_max_reactive_power()
        self._time_for_tunnel = gfm_params.get_time_for_tunnel()
        self._time_to_90 = gfm_params.get_time_to_90()
        self._Xgrid = gfm_params.get_grid_reactance()

    def get_plot_parameter_names(self) -> list[str]:
        """Retrieves the list of parameter names relevant for rendering AmplitudeStep plots.

        Returns
        -------
        list[str]
            A predefined list of string identifiers corresponding to the parameters
            displayed on the generated output plots.
        """
        return [
            "P0",
            "Q0",
            "VoltageStepAtGrid",
            "VoltageStepAtPDR",
            "SCR",
            "TimeTo90",
            "Xeff",
            "D",
            "H",
        ]

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """Calculates the reactive current deviation (delta_iq) and its bounding envelopes (PCC,
        upper, and lower) evaluated across an amplitude step event timeframe.

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
            The absolute time (in seconds) at which the amplitude step event initiates.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - str: The physical magnitude identifier (e.g., "Iq").
            - np.ndarray: The finalized reactive current signal calculated at the PCC.
            - np.ndarray: The array representing the upper reactive current envelope constraint.
            - np.ndarray: The array representing the lower reactive current envelope constraint.
        """
        # Initialize tracking logger and register initial boundary states for debugging
        logger = dycov_logging.get_logger("AmplitudeStep")
        logger.debug(f"Input Params D={D} H={H} Xeff {Xeff}")
        logger.debug(
            f"Input Params ΔVoltage={self._voltage_step} "
            f"SCR={self._scr} "
            f"Q0={self._initial_reactive_power} "
            f"QMin={self._min_reactive_power} "
            f"QMax={self._max_reactive_power}"
        )

        # Step 1: Compute the foundational delta_iq deviation curves (base, min, and max limits)
        (
            delta_iq_base,
            delta_iq_min,
            delta_iq_max,
        ) = self._get_delta_iq(
            D=D,
            H=H,
            Xeff=Xeff,
            time_array=time_array,
            event_time=event_time,
        )

        # Step 2: Synthesize the definitive operational envelopes referencing plant saturation
        # capabilities
        q_pcc, q_up, q_down = self._get_envelopes(
            delta_iq_base=delta_iq_base,
            delta_iq_min=delta_iq_min,
            delta_iq_max=delta_iq_max,
            Xeff=Xeff,
        )

        # Step 3: Enforce temporal delays applicable strictly to Electro-Magnetic Transient (EMT)
        # simulations
        if self._is_emt_flag:
            # Robust extraction of initial steady-state values handling both vector arrays and
            # scalar formats safely
            initial_upper_val = q_up[0] if not np.isscalar(q_up) else q_up
            initial_lower_val = q_down[0] if not np.isscalar(q_down) else q_down
            initial_pcc_val = q_pcc[0] if not np.isscalar(q_pcc) else q_pcc

            iq_up_final = self._apply_delay(
                self._emt_initial_delay, initial_upper_val, time_array, q_up
            )
            iq_down_final = self._apply_delay(
                self._emt_initial_delay, initial_lower_val, time_array, q_down
            )
            iq_pcc_final = self._apply_delay(
                self._emt_initial_delay, initial_pcc_val, time_array, q_pcc
            )
        else:
            iq_up_final = q_up
            iq_down_final = q_down
            iq_pcc_final = q_pcc

        magnitude_name = "Iq"
        return magnitude_name, iq_pcc_final, iq_up_final, iq_down_final

    def _get_delta_iq(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Derives the reactive current deviations (delta_iq) and their extreme boundary
        conditions, establishing the mathematical foundations for the step response.

        Note: Parameters D, H, and event_time are maintained in the signature to strictly
        adhere to the calculator interface, though amplitude step behavior is primarily
        governed by Xeff and defined time constants.

        Parameters
        ----------
        D : float
            The nominal damping factor (maintained for structural interface compliance).
        H : float
            The nominal inertia constant (maintained for structural interface compliance).
        Xeff : float
            The effective reactance of the system.
        time_array : np.ndarray
            The continuous time array mapped for the simulation window.
        event_time : float
            The established trigger point for the event sequence.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - np.ndarray: The baseline delta_iq trace representing nominal expected behavior.
            - np.ndarray: The minimum delta_iq trace establishing the lower response boundary.
            - np.ndarray: The maximum delta_iq trace establishing the upper response boundary.
        """
        # The analytical formulas governing the amplitude step rely intrinsically on Xeff,
        # sidestepping D and H variations for this specific grid event archetype.
        delta_iq_base = self._calculate_delta_iq_base(Xeff, time_array)

        # Formulate operational bounds mathematically constrained by defined tolerance tunnels
        delta_iq_min = self._get_delta_iq_min(Xeff, time_array)
        delta_iq_max = self._get_delta_iq_max(Xeff, time_array)

        return (
            delta_iq_base,
            delta_iq_min,
            delta_iq_max,
        )

    def _get_envelopes(
        self,
        delta_iq_base: np.ndarray,
        delta_iq_min: np.ndarray,
        delta_iq_max: np.ndarray,
        Xeff: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Translates raw reactive current derivations into final physical limits, applying
        saturation algorithms based on the plant's absolute operational boundaries.

        Parameters
        ----------
        delta_iq_base : np.ndarray
            The foundational delta_iq curve indicating nominal reactive current shifts.
        delta_iq_min : np.ndarray
            The pre-calculated lower boundary of the delta_iq response.
        delta_iq_max : np.ndarray
            The pre-calculated upper boundary of the delta_iq response.
        Xeff : float
            The effective system reactance required for limit scaling.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple returning the definitive, hardware-constrained signals:
            - np.ndarray: The final calculated expected reactive power equivalent at the PCC.
            - np.ndarray: The absolute maximum (upper) reactive power envelope constraint.
            - np.ndarray: The absolute minimum (lower) reactive power envelope constraint.
        """

        # Step 1: Resolve prerequisite transformation parameters

        # Calculate the localized voltage step projected at the Point of Common Coupling (PCC)
        volt_step_upcc = (self._voltage_step / 100.0) * Xeff / (Xeff + self._Xgrid)

        # Extract the vector direction (sign) of the incoming voltage disturbance
        sign_K = np.sign(volt_step_upcc)

        # Derive the static tolerance margin (tunnel) outlining the operational band
        tunnel = self._get_tunnel(Xeff)

        # Step 2: Formulate the lower analytical boundary (Qmin) applying hardware clipping logic
        q_down = np.maximum(
            np.minimum(
                self._initial_reactive_power - sign_K * delta_iq_min, self._max_reactive_power
            ),
            -self._max_reactive_power,
        )

        # Step 3: Formulate the upper analytical boundary (Qmax) scaling with the tolerance tunnel
        q_up = np.maximum(
            np.minimum(
                self._initial_reactive_power - sign_K * delta_iq_max,
                self._max_reactive_power + tunnel,
            ),
            -self._max_reactive_power - tunnel,
        )

        # Step 4: Synthesize the primary expected trace mapping the core response trajectory
        # This raw curve must inherently respect the absolute physical capabilities
        # (Qmax and -Qmax).

        # Derive the unconstrained nominal trajectory based on vector direction
        q_expected_unclamped = self._initial_reactive_power - sign_K * delta_iq_base

        # Apply absolute plant saturation clipping to enforce real-world mechanical limitations
        q_expected = np.maximum(
            np.minimum(q_expected_unclamped, self._max_reactive_power),
            -self._max_reactive_power,
        )

        # Step 5: Export the securely bounded operational arrays (conversion handling deferred to
        # caller)
        return q_expected, q_up, q_down

    def _get_delta_iq_base(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
        """Mathematically resolves the fundamental delta_iq trajectory utilizing a standard first-
        order exponential response equation.

        Parameters
        ----------
        Xeff : float
            The effective reactance parameter determining system impedance behavior.
        time_array : np.ndarray
            The continuous evaluation timeline array (implicitly zero-anchored for response).

        Returns
        -------
        np.ndarray
            The foundational unshifted delta_iq waveform derived purely from dynamic physics.
        """
        voltage_step = self._voltage_step / 100.0

        # Formulate the asymptotic theoretical limit of the reactive current shift
        delta_iq_final = np.abs(voltage_step / (Xeff + self._Xgrid))

        # Calculate the requisite time constant (tau) aligning to the 90% rise-time requirement
        tau = -self._time_to_90 / np.log(0.1)

        # Resolve the first-order exponential mapping function
        exponential_part = delta_iq_final * (1 - np.exp(-time_array / tau))

        return exponential_part

    def _calculate_delta_iq_base(
        self,
        Xeff: float,
        time_array: np.ndarray,
    ) -> np.ndarray:
        """A structural wrapper executing the base delta_iq waveform generation process.

        Parameters
        ----------
        Xeff : float
            The effective system reactance.
        time_array : np.ndarray
            The chronological evaluation map.

        Returns
        -------
        np.ndarray
            The generated baseline delta_iq trace representing nominal expected behavior.
        """
        delta_iq = self._get_delta_iq_base(Xeff, time_array)
        return delta_iq

    def _get_delta_iq_min(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
        """Synthesizes the specific delta_iq bounding array designated for the lower envelope.

        This mechanism scales the foundational base curve and strictly clips it against
        an upper limitation defined by the steady-state maximum minus the tolerance tunnel,
        ensuring the lower operational boundary never violates physical logic.

        Parameters
        ----------
        Xeff : float
            The defined effective system reactance.
        time_array : np.ndarray
            The evaluation timeline map.

        Returns
        -------
        np.ndarray
            The computed minimum limit delta_p boundary tailored for the lower envelope.
        """

        # Step 1: Retrieve the fundamental exponential trajectory and apply a slight baseline
        # reduction
        base_curve = 0.9 * self._get_delta_iq_base(Xeff, time_array)

        # Step 2: Establish the steady-state asymptote acting as the absolute ceiling
        tunnel = self._get_tunnel(Xeff)
        voltage_step_pu = self._voltage_step / 100.0

        # Calculate the ultimate theoretical maximum reactive shift magnitude
        max_delta_iq = np.abs(voltage_step_pu / (Xeff + self._Xgrid))

        # Define the structural ceiling specific to this lower boundary trace
        lower_envelope_limit = max_delta_iq - tunnel

        # Step 3: Enforce clipping to guarantee the baseline curve remains strictly beneath the
        # limit
        delta_iq_lower = np.minimum(base_curve, lower_envelope_limit)

        # Step 4: Constrain execution logic rendering the output completely inert prior to the 90%
        # rise mark
        delta_iq_lower = np.where(time_array < self._time_to_90, 0.0, delta_iq_lower)

        return delta_iq_lower

    def _get_delta_iq_max(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
        """Synthesizes the specific delta_iq bounding array designated for the upper envelope.

        This algorithm establishes a static steady-state plateau and introduces a decaying
        transient "boost" mapped to the initial reaction phase, simulating brief reactive power
        spikes.

        Parameters
        ----------
        Xeff : float
            The evaluated system effective reactance.
        time_array : np.ndarray
            The timeline mapped for the simulation.

        Returns
        -------
        np.ndarray
            The mathematically projected maximum delta_iq constraint boundary.
        """

        # Step 1: Derive structural baseline components regulating the magnitude limits
        tunnel = self._get_tunnel(Xeff)
        voltage_step_pu = self._voltage_step / 100.0

        # Formulate the asymptotic absolute magnitude of the reactive current shift
        max_delta_iq = np.abs(voltage_step_pu / (Xeff + self._Xgrid))

        # Step 2: Define the foundational static ceiling supporting the transient components
        steady_state_upper_limit = tunnel + max_delta_iq

        # Step 3: Compute the decaying transient boost representing initial capacitive/inductive
        # inertia
        # This exponential modifier is strictly constrained to the early operational window.

        # Generate a boolean evaluation mask activating the transient strictly within the tunnel
        # timeframe
        transient_condition = time_array < self._time_for_tunnel

        # Establish the specific exponential decay constant structuring the transient drop-off
        time_constant_transient = self._time_for_tunnel / 3.0

        # Initialize the transient boost modifier to zero
        transient_boost_value = 0.0

        # Guard against division by zero by verifying the time constant is physically meaningful
        if time_constant_transient > 1e-9:
            exponential_decay = np.exp(-time_array / time_constant_transient)

            # Evaluate the transient boost magnitude combining the upper margin and exponential
            # decay
            transient_boost_value = self._margin_high * max_delta_iq * exponential_decay

        # Step 4: Superimpose the conditional transient spike onto the stable maximum ceiling
        # plateau
        delta_iq_upper = steady_state_upper_limit + np.where(
            transient_condition, transient_boost_value, 0.0
        )

        return delta_iq_upper

    def _get_tunnel(self, Xeff: float) -> float:
        """Calculates and maps the mathematical static tolerance margin ("tunnel"), outlining the
        required operational variance boundary relative to the impedance.

        Parameters
        ----------
        Xeff : float
            The absolute effective reactance configuring system baseline impedance.

        Returns
        -------
        float
            The statically extracted boundary limit required to enforce tolerance mapping.
        """
        voltage_step = self._voltage_step / 100.0
        delta_iq = np.abs(voltage_step / (Xeff + self._Xgrid))

        return max(
            self._final_allowed_tunnel_pn,
            self._final_allowed_tunnel_variation * delta_iq,
        )
