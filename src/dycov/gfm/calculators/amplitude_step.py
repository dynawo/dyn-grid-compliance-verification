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
    This class handles all core calculations for delta_q and reactive power
    envelopes.
    """

    def __init__(
        self,
        gfm_params: GFMParameters,
    ) -> None:
        super().__init__(gfm_params=gfm_params)
        self._voltage_step = gfm_params.get_voltage_step()
        self._initial_reactive_power = gfm_params.get_initial_reactive_power()
        self._min_reactive_power = gfm_params.get_min_reactive_power()
        self._max_reactive_power = gfm_params.get_max_reactive_power()
        self._time_for_tunnel = gfm_params.get_time_for_tunnel()
        self._time_to_90 = gfm_params.get_time_to_90()

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the change in power (delta_q) and reactive power envelopes
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
            - q_pcc_final: The final calculated reactive power at the point of
              common coupling.
            - q_up_final: The final upper reactive power envelope.
            - q_down_final: The final lower reactive power envelope.
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
            delta_q_array,
            delta_q_min,
            delta_q_max,
        ) = self._get_delta_q(
            D=D,
            H=H,
            Xeff=Xeff,
            time_array=time_array,
            event_time=event_time,
        )

        q_pcc, q_up, q_down = self._get_envelopes(
            delta_q_array=delta_q_array,
            delta_q_min=delta_q_min,
            delta_q_max=delta_q_max,
            time_array=time_array,
            event_time=event_time,
            Xeff=Xeff,
        )
        return "Q", q_pcc, q_up, q_down

    def _get_delta_q(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[list, np.ndarray, np.ndarray]:
        """
        Calculates the change in reactive power (delta_q) and related
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
            - delta_q_array: List of delta_q arrays for original, min, and max
              parameter variations.
            - delta_q_min: delta_q array specifically calculated for the minimum
              parameter case.
            - delta_q_max: delta_q array specifically calculated for the maximum
              parameter case.
        """
        d_array = np.array([D, D * self._min_ratio, D * self._max_ratio])
        h_array = np.array([H, H / self._min_ratio, H / self._max_ratio])

        delta_q_array = []

        for i in range(len(d_array)):
            delta_q = self._calculate_delta_q_for_damping(
                d_array[i], h_array[i], Xeff, time_array, event_time
            )
            delta_q_array.append(delta_q)

        delta_q_min = self._get_delta_q_min(D, H, Xeff, time_array, event_time)
        delta_q_max = self._get_delta_q_max(D, H, Xeff, time_array, event_time)

        return (
            delta_q_array,
            delta_q_min,
            delta_q_max,
        )

    def _get_envelopes(
        self,
        delta_q_array: list,
        delta_q_min: np.ndarray,
        delta_q_max: np.ndarray,
        time_array: np.ndarray,
        event_time: float,
        Xeff: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates and limits the final reactive power envelopes (PCC power,
        upper envelope, lower envelope). This involves combining various
        delta_q calculations, applying a time-dependent tunnel effect, and
        enforcing operational limits.

        Parameters
        ----------
        delta_q_array : list
            List of delta_q arrays for original, min, and max parameters.
        delta_q_min : np.ndarray
            delta_q array calculated with minimum parameters.
        delta_q_max : np.ndarray
            delta_q array calculated with maximum parameters.
        time_array : np.ndarray
            Array of time points.
        event_time : float
            The time at which the event occurs.
        Xeff : float
            Effective reactance.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - q_pcc_final: The final calculated reactive power at the point of
              common coupling.
            - q_up_final: The final upper reactive power envelope.
            - q_down_final: The final lower reactive power envelope.
        """
        delta_q = delta_q_array[self._ORIGINAL_PARAMS_IDX]

        # Calculate the theoretical reactive power at the Point of Common
        # Coupling (PCC). This is based on the initial power (Q0) and delta_q,
        # adjusted by the sign of voltage_step to reflect the direction of
        # power change.
        q_pcc = self._initial_reactive_power + delta_q * -(
            self._voltage_step / np.abs(self._voltage_step)
        )

        q_up_raw = self._initial_reactive_power + np.minimum(
            delta_q_max,
            self._max_reactive_power - self._initial_reactive_power,
        ) * -(self._voltage_step / np.abs(self._voltage_step))

        tunnel = self._get_tunnel(Xeff)
        q_down_raw = self._initial_reactive_power + np.minimum(
            delta_q_min,
            self._max_reactive_power - self._initial_reactive_power - tunnel,
        ) * -(self._voltage_step / np.abs(self._voltage_step))

        q_up = np.maximum(q_up_raw, q_down_raw)
        q_down = np.minimum(q_up_raw, q_down_raw)

        # If EMT simulation flag is true, apply a small delay to the final
        # power signals.
        if self._is_emt_flag:
            q_up_final = self._apply_delay(0.02, q_up[0], time_array, q_up)
            q_down_final = self._apply_delay(0.02, q_down[0], time_array, q_down)
        else:
            q_up_final = q_up
            q_down_final = q_down
        q_pcc_final = q_pcc

        return q_pcc_final, q_up_final, q_down_final

    def _get_delta_q_base(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray
    ) -> np.ndarray:
        """
        Calculates the fundamental delta_q waveform for an overdamped system
        response, without applying event time conditions or margins. This
        represents the raw dynamic behavior.

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

        Returns
        -------
        np.ndarray
            The base delta_q waveform.
        """
        x_gr = 1 / self._scr
        x_total_initial = Xeff + x_gr

        voltage_step = self._voltage_step / 100.0

        delta_v_inf = -np.abs(voltage_step * x_total_initial / Xeff)
        delta_iq = np.abs(delta_v_inf / x_total_initial)

        tau = -self._time_to_90 / np.log(0.1)

        delta_q1 = delta_iq * (1 - np.exp(-time_array / tau))
        return delta_q1

    def _calculate_delta_q_for_damping(
        self,
        D: float,
        H: float,
        Xeff: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> np.ndarray:
        """
        Calculates delta_q for an overdamped system response, ensuring that
        the delta_q values are zero before the specified event time.

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
            The delta_q array for the system, with pre-event values zeroed.
        """
        delta_q1 = self._get_delta_q_base(D, H, Xeff, time_array)
        delta_q = np.where(time_array < event_time, 0, delta_q1)
        return delta_q

    def _get_delta_q_min(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Calculates the minimum delta_q for an overdamped system, by applying
        a lower margin to the base delta_q waveform and setting pre-event
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
            The minimum delta_q array for the overdamped system.
        """
        x_gr = 1 / self._scr
        x_total_initial = Xeff + x_gr

        voltage_step = self._voltage_step / 100.0

        delta_v_inf = np.abs(voltage_step * x_total_initial / Xeff)
        delta_iq = np.abs(delta_v_inf / x_total_initial)

        tunnel = self._get_tunnel(Xeff)

        delta_q1 = self._get_delta_q_base(D, H, Xeff, time_array)
        delta_q1_margined = np.minimum(delta_q1, delta_iq - tunnel)
        delta_q1_delayed = self._apply_delay(0.01, 0, time_array, delta_q1_margined)
        delta_q = np.where(time_array < event_time, 0, delta_q1_delayed)
        return delta_q

    def _get_delta_q_max(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Calculates the maximum delta_q for an overdamped system, by applying
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
            The maximum delta_q array for the overdamped system.
        """
        ttunnel = self._time_for_tunnel
        x_gr = 1 / self._scr
        x_total_initial = Xeff + x_gr

        voltage_step = self._voltage_step / 100.0

        delta_v_inf = np.abs(voltage_step * x_total_initial / Xeff)
        delta_iq = np.abs(delta_v_inf / x_total_initial)

        tunnel = self._get_tunnel(Xeff)

        delta_q1 = (
            delta_iq + self._margin_high * delta_iq * np.exp(-time_array / (ttunnel / 3)) + tunnel
        )
        delta_q1_margined = np.where(time_array < ttunnel, delta_q1, delta_iq + tunnel)
        delta_q = np.where(time_array < event_time, 0, delta_q1_margined)
        return delta_q

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
        x_gr = 1 / self._scr
        x_total_initial = Xeff + x_gr

        voltage_step = self._voltage_step / 100.0

        delta_v_inf = np.abs(voltage_step * x_total_initial / Xeff)
        delta_iq = np.abs(delta_v_inf / x_total_initial)

        return max(
            self._final_allowed_tunnel_pn,  # Fixed power component
            self._final_allowed_tunnel_variation * delta_iq,
        )
