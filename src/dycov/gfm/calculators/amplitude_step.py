#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

import numpy as np

from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.parameters import GFMParameters
from dycov.logging import dycov_logging


class AmplitudeStep(GFMCalculator):
    """Handles the GFM amplitude step response calculations."""

    def __init__(self, gfm_params: GFMParameters) -> None:
        """
        Initializes the AmplitudeStep calculator with GFM parameters.

        Parameters
        ----------
        gfm_params : GFMParameters
            The shared configuration parameters.
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
        """
        Retrieves parameters relevant for rendering Amplitude Step plots.

        Returns
        -------
        list[str]
            A list of parameter names to be displayed.
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
        """
        Calculates the reactive current deviation and bounding envelopes.

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
            A tuple containing the
            magnitude name (
            "Iq"),
            the main signal,
            the upper envelope,
            and the lower envelope.
        """
        logger = dycov_logging.get_logger("AmplitudeStep")
        logger.debug(f"Input Params D={D} H={H} Xeff {Xeff}")

        # Compute baseline and boundary reactive current deviations
        delta_iq_base, delta_iq_min, delta_iq_max = self._get_delta_iq(
            D=D, H=H, Xeff=Xeff, time_array=time_array, event_time=event_time
        )

        q_pcc, q_up, q_down = self._get_envelopes(
            delta_iq_base=delta_iq_base,
            delta_iq_min=delta_iq_min,
            delta_iq_max=delta_iq_max,
            Xeff=Xeff,
        )

        if self._is_emt_flag:
            # Apply time shift delays for EMT simulation parity
            initial_upper_val = q_up[0] if not np.isscalar(q_up) else q_up
            initial_lower_val = q_down[0] if not np.isscalar(q_down) else q_down
            initial_pcc_val = q_pcc[0] if not np.isscalar(q_pcc) else q_pcc

            iq_up_final = self._apply_delay(self._emt_delay, initial_upper_val, time_array, q_up)
            iq_down_final = self._apply_delay(
                self._emt_delay, initial_lower_val, time_array, q_down
            )
            iq_pcc_final = self._apply_delay(self._emt_delay, initial_pcc_val, time_array, q_pcc)
        else:
            iq_up_final, iq_down_final, iq_pcc_final = q_up, q_down, q_pcc

        return "Iq", iq_pcc_final, iq_up_final, iq_down_final

    def _get_delta_iq(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Computes the core, minimum, and maximum delta_iq sequences.

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
            The time the event occurs.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple with the baseline delta_iq,
            minimum delta_iq boundary, and maximum delta_iq boundary arrays.
        """
        delta_iq_base = self._calculate_delta_iq_base(Xeff, time_array)
        delta_iq_min = self._get_delta_iq_min(Xeff, time_array)
        delta_iq_max = self._get_delta_iq_max(Xeff, time_array)
        return delta_iq_base, delta_iq_min, delta_iq_max

    def _get_envelopes(
        self,
        delta_iq_base: np.ndarray,
        delta_iq_min: np.ndarray,
        delta_iq_max: np.ndarray,
        Xeff: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Translates raw reactive current derivations into final physical limits.

        Parameters
        ----------
        delta_iq_base : np.ndarray
            The baseline reactive current change array.
        delta_iq_min : np.ndarray
            The minimum boundary array.
        delta_iq_max : np.ndarray
            The maximum boundary array.
        Xeff : float
            The effective reactance.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple containing the expected
            reactive power array, upper limit envelope, and lower limit envelope.
        """
        volt_step_upcc = (self._voltage_step / 100.0) * Xeff / (Xeff + self._Xgrid)
        sign_K = np.sign(volt_step_upcc)
        tunnel = self._get_tunnel(Xeff)

        q_down = np.clip(
            self._initial_reactive_power - sign_K * delta_iq_min,
            -self._max_reactive_power,
            self._max_reactive_power,
        )
        q_up = np.clip(
            self._initial_reactive_power - sign_K * delta_iq_max,
            -self._max_reactive_power - tunnel,
            self._max_reactive_power + tunnel,
        )

        q_expected_unclamped = self._initial_reactive_power - sign_K * delta_iq_base
        q_expected = np.clip(
            q_expected_unclamped, -self._max_reactive_power, self._max_reactive_power
        )

        return q_expected, q_up, q_down

    def _get_delta_iq_base(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
        """
        Calculates the theoretical baseline reactive current response.

        Parameters
        ----------
        Xeff : float
            The effective reactance.
        time_array : np.ndarray
            The simulation time vector.

        Returns
        -------
        np.ndarray
            The mathematical baseline reactive current array.
        """
        voltage_step = self._voltage_step / 100.0
        delta_iq_final = np.abs(voltage_step / (Xeff + self._Xgrid))
        tau = -self._time_to_90 / np.log(0.1)
        return delta_iq_final * (1 - np.exp(-time_array / tau))

    def _calculate_delta_iq_base(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
        """
        Wrapper method to compute the baseline reactive current response.

        Parameters
        ----------
        Xeff : float
            The effective reactance.
        time_array : np.ndarray
            The simulation time vector.

        Returns
        -------
        np.ndarray
            The baseline reactive current array.
        """
        return self._get_delta_iq_base(Xeff, time_array)

    def _get_delta_iq_min(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
        """
        Calculates the minimum boundary for the reactive current response.

        Parameters
        ----------
        Xeff : float
            The effective reactance.
        time_array : np.ndarray
            The simulation time vector.

        Returns
        -------
        np.ndarray
            The array representing the minimum expected current trajectory.
        """
        base_curve = 0.9 * self._get_delta_iq_base(Xeff, time_array)
        tunnel = self._get_tunnel(Xeff)
        voltage_step_pu = self._voltage_step / 100.0
        max_delta_iq = np.abs(voltage_step_pu / (Xeff + self._Xgrid))

        lower_envelope_limit = max_delta_iq - tunnel
        delta_iq_lower = np.minimum(base_curve, lower_envelope_limit)
        return np.where(time_array < self._time_to_90, 0.0, delta_iq_lower)

    def _get_delta_iq_max(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
        """
        Calculates the maximum boundary for the reactive current response.

        Parameters
        ----------
        Xeff : float
            The effective reactance.
        time_array : np.ndarray
            The simulation time vector.

        Returns
        -------
        np.ndarray
            The array representing the maximum expected current trajectory.
        """
        tunnel = self._get_tunnel(Xeff)
        voltage_step_pu = self._voltage_step / 100.0
        max_delta_iq = np.abs(voltage_step_pu / (Xeff + self._Xgrid))

        steady_state_upper_limit = tunnel + max_delta_iq

        transient_condition = time_array < self._time_for_tunnel
        time_constant_transient = self._time_for_tunnel / 3.0
        transient_boost_value = 0.0

        if time_constant_transient > 1e-9:
            exponential_decay = np.exp(-time_array / time_constant_transient)
            transient_boost_value = self._margin_high * max_delta_iq * exponential_decay

        return steady_state_upper_limit + np.where(transient_condition, transient_boost_value, 0.0)

    def _get_tunnel(self, Xeff: float) -> float:
        """
        Calculates the static tolerance margin for the amplitude step.

        Parameters
        ----------
        Xeff : float
            The effective reactance.

        Returns
        -------
        float
            The permitted tunnel margin value.
        """
        voltage_step = self._voltage_step / 100.0
        delta_iq = np.abs(voltage_step / (Xeff + self._Xgrid))
        return max(self._final_allowed_tunnel_pn, self._final_allowed_tunnel_variation * delta_iq)
