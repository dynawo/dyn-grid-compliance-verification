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


class AmplitudeStep(GFMCalculator):
    """
    Class to calculate the GFM amplitude step response.

    This class handles all core calculations for delta_iq and reactive current
    envelopes.
    """

    def __init__(
        self,
        gfm_params: GFMParameters,
    ) -> None:
        """
        Initializes the AmplitudeStep calculator with GFM parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            An object containing all necessary parameters for GFM calculations.
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
        """Returns the list of parameter names relevant for AmplitudeStep plots."""
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
        """
        Calculates the change in current (delta_iq) and reactive current envelopes
        (PCC, upper, and lower) based on damping characteristics for an
        amplitude step event.

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
            The time (in seconds) at which the amplitude step event occurs.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - magnitude_name: Name of the calculated magnitude ("Iq").
            - iq_pcc_final: The final calculated reactive current at the PCC.
            - iq_up_final: The final upper reactive current envelope.
            - iq_down_final: The final lower reactive current envelope.
        """
        # Log the input parameters for debugging.
        logger = dycov_logging.get_logger("AmplitudeStep")
        logger.debug(f"Input Params D={D} H={H} Xeff {Xeff}")
        logger.debug(
            f"Input Params ΔVoltage={self._voltage_step} "
            f"SCR={self._scr} "
            f"Q0={self._initial_reactive_power} "
            f"QMin={self._min_reactive_power} "
            f"QMax={self._max_reactive_power}"
        )

        # 1. Get the delta_iq curves (base, min, max)
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

        # 2. Get the reactive power (Q) envelopes
        q_pcc, q_up, q_down = self._get_envelopes(
            delta_iq_base=delta_iq_base,
            delta_iq_min=delta_iq_min,
            delta_iq_max=delta_iq_max,
            Xeff=Xeff,
        )

        # 3. Apply a final delay for EMT-type simulations
        if self._is_emt_flag:
            # Safely get initial values, handling both arrays and scalars.
            initial_upper_val = q_up[0] if not np.isscalar(q_up) else q_up
            initial_lower_val = q_down[0] if not np.isscalar(q_down) else q_down
            initial_pcc_val = q_pcc[0] if not np.isscalar(q_pcc) else q_pcc

            iq_up_final = self._apply_delay(
                constants.EMT_FINAL_DELAY_S, initial_upper_val, time_array, q_up
            )
            iq_down_final = self._apply_delay(
                constants.EMT_FINAL_DELAY_S, initial_lower_val, time_array, q_down
            )
            iq_pcc_final = self._apply_delay(
                constants.EMT_FINAL_DELAY_S, initial_pcc_val, time_array, q_pcc
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
        """
        Calculates the change in reactive current (delta_iq) and related
        parameters based on damping characteristics, considering variations
        for nominal, minimum, and maximum parameters.

        Parameters
        ----------
        D : float
            Damping factor. (Currently unused)
        H : float
            Inertia constant. (Currently unused)
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Array of time points for simulation.
        event_time : float
            The time (in seconds) at which the amplitude step event occurs.
            (Currently unused by sub-methods)

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - delta_iq_base: delta_iq array for the nominal (original)
              parameter case.
            - delta_iq_min: delta_iq array specifically calculated for the minimum
              parameter case.
            - delta_iq_max: delta_iq array specifically calculated for the maximum
              parameter case.
        """
        # The formulas do not depend on D and H variations,
        # so we no longer use them in the loop.
        # Note: The event_time is also not used in the calculations below,
        # as per the logic in the sub-methods.
        delta_iq_base = self._calculate_delta_iq_base(Xeff, time_array)

        # 'q_expected_base + tunnel' and 'q_expected_base - tunnel'
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
        """
        Calculates and limits the final reactive *power* envelopes (PCC power,
        upper envelope, lower envelope) based on the plant's operational limits.

        This function applies the following Excel logic:
        Qmin = Q0 - SIGN(Vstep) * MIN(delta_iq_min, Qmax - Q0 - tunnel)
        Qmax = Q0 - SIGN(Vstep) * MIN(delta_iq_max, Qmax - Q0)
        Qexpected = MAX(MIN(Q0 - SIGN(Vstep) * delta_iq_base, Qmax), -Qmax)

        Parameters
        ----------
        delta_iq_base : np.ndarray
            The base delta_iq curve (change in reactive current).
        delta_iq_min : np.ndarray
            The delta_iq curve for the lower envelope.
        delta_iq_max : np.ndarray
            The delta_iq curve for the upper envelope.
        Xeff : float
            Effective reactance.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple containing the final reactive *power* envelopes:
            - q_expected: The final calculated reactive power at the PCC.
            - q_up: The final upper reactive power envelope.
            - q_down: The final lower reactive power envelope.
        """

        # 1. Calculate prerequisite values

        # Calculate the voltage step at the PCC (Point of Common Coupling)
        volt_step_upcc = (self._voltage_step / 100.0) * Xeff / (Xeff + self._Xgrid)

        # Get the sign of the voltage step. Corresponds to: SIGN(Vstep)
        sign_K = np.sign(volt_step_upcc)

        # Get the tunnel value
        tunnel = self._get_tunnel(Xeff)

        # 2. Calculate the lower reactive power envelope (Qmin)
        # Formula: Q0 - SIGN(Vstep) * MIN(delta_iq_min, Qmax - Q0 - tunnel)

        q_down = np.maximum(
            np.minimum(
                self._initial_reactive_power - sign_K * delta_iq_min, self._max_reactive_power
            ),
            -self._max_reactive_power,
        )

        # 3. Calculate the upper reactive power envelope (Qmax)
        # Formula: Q0 - SIGN(Vstep) * MIN(delta_iq_max, Qmax - Q0)

        q_up = np.maximum(
            np.minimum(
                self._initial_reactive_power - sign_K * delta_iq_max,
                self._max_reactive_power + tunnel,
            ),
            -self._max_reactive_power - tunnel,
        )

        # 4. Calculate the expected reactive power curve (Qexpected)
        # This is the base curve, saturated by the plant's Qmax/Qmin limits.
        # Formula: MAX(MIN(Q0 - SIGN(Vstep) * delta_iq_base, Qmax), -Qmax)

        # Unclamped expected Q: Q0 - SIGN(Vstep) * delta_iq_base
        q_expected_unclamped = self._initial_reactive_power - sign_K * delta_iq_base

        # Apply plant saturation limits (Qmax and -Qmax)
        q_expected = np.maximum(
            np.minimum(q_expected_unclamped, self._max_reactive_power),
            -self._max_reactive_power,
        )

        # 5. Return reactive power (Q) envelopes.
        # Delay and conversion to Iq are handled in calculate_envelopes.
        return q_expected, q_up, q_down

    def _get_delta_iq_base(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
        """
        Calculates the fundamental delta_iq waveform ('Qexpe sane (0)' from Excel)
        based on a first-order exponential response.

        Parameters
        ----------
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Array of time points (assumed to start at t=0 for the response).

        Returns
        -------
        np.ndarray
            The base delta_iq waveform (without applying event_time).
        """
        voltage_step = self._voltage_step / 100.0

        # Final DeltaIQ value
        delta_iq_final = np.abs(voltage_step / (Xeff + self._Xgrid))
        # Time constant tau
        tau = -self._time_to_90 / np.log(0.1)

        # Formula: DeltaIQ_final * (1 - EXP(-t / tau))
        exponential_part = delta_iq_final * (1 - np.exp(-time_array / tau))

        return exponential_part

    def _calculate_delta_iq_base(
        self,
        Xeff: float,
        time_array: np.ndarray,
    ) -> np.ndarray:
        """
        Calculates the base delta_iq curve ('Qexpe sane (0)').
        Note: This implementation assumes the response starts at time_array[0].

        Parameters
        ----------
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Array of time points.

        Returns
        -------
        np.ndarray
            The delta_iq array for the base curve.
        """
        delta_iq = self._get_delta_iq_base(Xeff, time_array)
        return delta_iq

    def _get_delta_iq_min(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
        """
        Calculates the delta_iq curve for the **lower envelope**.

        This logic implements the Excel formula:
        =IF(time < t90pc, 0, MIN(base_curve, max_delta_iq - tunnel))

        Note: The docstring formula 'q_expected_base - tunnel' seems to be a
            simplification. The actual logic calculates a MIN(base_curve, limit).

        Parameters
        ----------
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Array of time points.

        Returns
        -------
        np.ndarray
            The delta_iq array for the lower envelope.
        """

        # 1. Calculate the base exponential curve
        # This corresponds to: DeltaIQ*(1-EXP(-time/tau))
        base_curve = 0.9 * self._get_delta_iq_base(Xeff, time_array)

        # 2. Calculate the components for the lower limit (the ceiling)
        tunnel = self._get_tunnel(Xeff)
        voltage_step_pu = self._voltage_step / 100.0

        # This is the steady-state or maximum DeltaIQ
        max_delta_iq = np.abs(voltage_step_pu / (Xeff + self._Xgrid))

        # This is the 'DeltaIQ - tunnel' part of the formula, which acts as
        # the upper limit for this *lower* envelope curve.
        lower_envelope_limit = max_delta_iq - tunnel

        # 3. Apply the MIN function
        # This clips the base curve so it never exceeds the lower_envelope_limit
        # This corresponds to: MIN(base_curve, max_delta_iq - tunnel)
        delta_iq_lower = np.minimum(base_curve, lower_envelope_limit)

        # 4. Apply the initial time condition
        # This corresponds to: IF(time < t90pc, 0, ...)
        delta_iq_lower = np.where(time_array < self._time_to_90, 0.0, delta_iq_lower)

        return delta_iq_lower

    def _get_delta_iq_max(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
        """
        Calculates the delta_iq curve for the **upper envelope**.

        This logic implements the Excel formula:
        =IF(time < ttunnel,
            DeltaIQ + Marge_haute*DeltaIQ*EXP(-time/(ttunnel/3)) + tunnel,
            tunnel + DeltaIQ)

        Note: The docstring formula 'q_expected_base + tunnel' seems to be a
            simplification. The actual logic adds a transient component.

        Parameters
        ----------
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Array of time points.

        Returns
        -------
        np.ndarray
            The delta_iq array for the upper envelope.
        """

        # 1. Calculate common components
        tunnel = self._get_tunnel(Xeff)
        voltage_step_pu = self._voltage_step / 100.0

        # This is the steady-state or maximum DeltaIQ
        max_delta_iq = np.abs(voltage_step_pu / (Xeff + self._Xgrid))

        # 2. Calculate the steady-state upper limit: 'tunnel + DeltaIQ'
        # This is the base value for the entire curve
        steady_state_upper_limit = tunnel + max_delta_iq

        # 3. Calculate the transient "boost" part of the formula
        # This boost is added only before self._time_for_tunnel

        # Condition for when the transient boost applies
        transient_condition = time_array < self._time_for_tunnel

        # Calculate the exponential decay term for the boost
        # Corresponds to: EXP(-time / (ttunnel / 3))
        time_constant_transient = self._time_for_tunnel / 3.0

        # Initialize transient_boost to zero
        transient_boost_value = 0.0

        # Avoid division by zero if _time_for_tunnel is 0
        if time_constant_transient > 1e-9:  # Use a small epsilon to check
            exponential_decay = np.exp(-time_array / time_constant_transient)

            # Calculate the transient boost magnitude
            # Corresponds to: Marge_haute * DeltaIQ * exponential_decay
            transient_boost_value = self._margin_high * max_delta_iq * exponential_decay

        # 4. Combine the steady-state limit with the conditional transient boost
        #
        # The logic is:
        # value = steady_state_upper_limit + (transient_boost IF condition ELSE 0)

        delta_iq_upper = steady_state_upper_limit + np.where(
            transient_condition, transient_boost_value, 0.0
        )

        return delta_iq_upper

    def _get_tunnel(self, Xeff: float) -> float:
        """
        Calculates a constant "tunnel" value.
        (This function matches the new Excel formula)

        Parameters
        ----------
        Xeff : float
            Effective reactance.

        Returns
        -------
        float
            The calculated constant tunnel value.
        """
        voltage_step = self._voltage_step / 100.0
        delta_iq = np.abs(voltage_step / (Xeff + self._Xgrid))

        return max(
            self._final_allowed_tunnel_pn,  # Final band (% Pn)
            self._final_allowed_tunnel_variation * delta_iq,  # Final band (% step)
        )
