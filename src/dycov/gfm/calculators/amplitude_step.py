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
    """
    Class to calculate the GFM amplitude step response.
    This class handles all core calculations for delta_iq and reactive current
    envelopes.
    """

    def __init__(
        self,
        gfm_params: GFMParameters,
    ) -> None:
        super().__init__(gfm_params=gfm_params)
        self._voltage_step = gfm_params.get_voltage_step_at_grid()
        self._initial_reactive_power = gfm_params.get_initial_reactive_power()
        self._min_reactive_power = gfm_params.get_min_reactive_power()
        self._max_reactive_power = gfm_params.get_max_reactive_power()
        self._time_for_tunnel = gfm_params.get_time_for_tunnel()
        self._time_to_90 = gfm_params.get_time_to_90()

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
            - magnitude: Name of the calculated magnitude.
            - iq_pcc_final: The final calculated reactive current at the point of
              common coupling.
            - iq_up_final: The final upper reactive current envelope.
            - iq_down_final: The final lower reactive current envelope.
        """
        # Log the input parameters for debugging.
        dycov_logging.get_logger("AmplitudeStep").debug(f"Input Params D={D} H={H} Xeff {Xeff}")
        dycov_logging.get_logger("AmplitudeStep").debug(
            f"Input Params ΔVoltage={self._voltage_step} "
            f"SCR={self._scr} "
            f"Q0={self._initial_reactive_power} "
            f"QMin={self._min_reactive_power} "
            f"QMax={self._max_reactive_power}"
        )
        (
            delta_iq_array,
            delta_iq_min,
            delta_iq_max,
        ) = self._get_delta_iq(
            D=D,
            H=H,
            Xeff=Xeff,
            time_array=time_array,
            event_time=event_time,
        )

        if self._is_emt_flag:
            iq_up = self._apply_delay(0.02, delta_iq_min[0], time_array, delta_iq_min)
            iq_down = self._apply_delay(0.02, delta_iq_max[0], time_array, delta_iq_max)
        else:
            iq_up = delta_iq_min
            iq_down = delta_iq_max
        iq_pcc = delta_iq_array[self._ORIGINAL_PARAMS_IDX]

        return "Iq", iq_pcc, iq_up, iq_down

    def _get_delta_iq(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[list, np.ndarray, np.ndarray]:
        """
        Calculates the change in reactive current (delta_iq) and related
        parameters based on damping characteristics, considering variations
        for nominal, minimum, and maximum parameters.

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
        tuple[list, np.ndarray, np.ndarray]
            A tuple containing:
            - delta_iq_array: List of delta_iq arrays for original, min, and max
              parameter variations.
            - delta_iq_min: delta_iq array specifically calculated for the minimum
              parameter case.
            - delta_iq_max: delta_iq array specifically calculated for the maximum
              parameter case.
        """
        d_array = np.array([D, D * self._min_ratio, D * self._max_ratio])
        h_array = np.array([H, H / self._min_ratio, H / self._max_ratio])

        delta_iq_array = []

        for i in range(len(d_array)):
            delta_iq = self._calculate_delta_iq(
                d_array[i], h_array[i], Xeff, time_array, event_time
            )
            delta_iq_array.append(delta_iq)

        delta_iq_min = self._get_delta_iq_min(Xeff, time_array, event_time)
        delta_iq_max = self._get_delta_iq_max(Xeff, time_array, event_time)

        return (
            delta_iq_array,
            delta_iq_min,
            delta_iq_max,
        )

    def _calculate_delta_iq(
        self,
        D: float,
        H: float,
        Xeff: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> np.ndarray:
        """
        Calculates delta_iq for an overdamped system response, ensuring that
        the delta_iq values are zero before the specified event time.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The delta_iq array for the system, with pre-event values zeroed.
        """
        voltage_step = self._voltage_step / 100.0
        delta_iq = voltage_step / Xeff

        tau = -self._time_to_90 / np.log(0.1)

        # Create a relative time that starts at 0 at the 'event_time'
        relative_time = np.maximum(0, time_array - event_time)

        # This directly implements: DeltaIQ * (1 - EXP(-time/tau))
        calculated_delta_iq = delta_iq * (1 - np.exp(-relative_time / tau))

        # Ensure that pre-event values are zero
        delta_iq_base = np.where(time_array < event_time, 0, calculated_delta_iq)

        return delta_iq_base

    def _get_delta_iq_min(
        self, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Calculates the minimum delta_iq for an overdamped system, by applying
        a lower margin to the base delta_iq and setting pre-event
        values to zero.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The minimum delta_iq array for the overdamped system.
        """
        voltage_step = self._voltage_step / 100
        delta_iq = voltage_step / Xeff
        tunnel = self._get_tunnel(Xeff)
        tau = -self._time_to_90 / np.log(0.1)
        ttunnel = self._time_for_tunnel
        margin_high = self._margin_high
        relative_time = np.maximum(0, time_array - event_time)

        # Path A: if Vstep is positive (voltage_step > 0)
        growth_curve = delta_iq * (1 - np.exp(-relative_time / tau))
        ceiling = delta_iq - tunnel
        result_if_positive_vstep = np.minimum(growth_curve, ceiling)

        # Path B: if Vstep is NOT positive (voltage_step <= 0)
        decay_curve = (
            delta_iq + margin_high * delta_iq * np.exp(-relative_time / (ttunnel / 3.0)) + tunnel
        )
        constant_value = delta_iq + tunnel
        result_if_negative_vstep = np.where(relative_time < ttunnel, decay_curve, constant_value)

        # Combine Path A and Path B based on the primary condition
        calculated_delta_iq_ = np.where(
            voltage_step > 0, result_if_positive_vstep, result_if_negative_vstep
        )

        # Ensure all pre-event values are zero and assign to the final variable name
        delta_iq_min = np.where(time_array < event_time, 0, calculated_delta_iq_)

        return delta_iq_min

    def _get_delta_iq_max(
        self, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Calculates the maximum delta_iq for an overdamped system, by applying
        an upper margin, an additional delay, and setting pre-event values to
        zero.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The maximum delta_iq array for the overdamped system.
        """

        voltage_step = self._voltage_step / 100.0
        delta_iq = voltage_step / Xeff
        tunnel = self._get_tunnel(Xeff)
        ttunnel = self._time_for_tunnel
        margin_high = self._margin_high

        relative_time = np.maximum(0, time_array - event_time)

        # Value if 'relative_time < ttunnel' (Exponential Decay Phase)
        decay_curve = (
            delta_iq + margin_high * delta_iq * np.exp(-relative_time / (ttunnel / 3.0)) + tunnel
        )

        # Value if 'relative_time >= ttunnel' (Constant Phase)
        constant_value = delta_iq + tunnel

        calculated_delta_iq_ = np.where(relative_time < ttunnel, decay_curve, constant_value)

        # Ensure that pre-event values are zero
        delta_iq_max = np.where(time_array < event_time, 0, calculated_delta_iq_)

        return delta_iq_max

    def _get_tunnel(self, Xeff: float) -> float:
        """
        Calculates a constant "tunnel" value.

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
        delta_iq = voltage_step / Xeff

        return max(
            self._final_allowed_tunnel_pn,  # Fixed current component
            self._final_allowed_tunnel_variation * delta_iq,
        )
