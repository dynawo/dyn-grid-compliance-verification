# !/usr/bin/env python3
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
from dycov.logging.logging import dycov_logging


class AmplitudeStep(GFMCalculator):
    """
    Class to calculate the GFM amplitude step response.
    This class handles all core calculations for delta_q and reactive power
    envelopes.
    """

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> tuple[bool, np.ndarray, np.ndarray, np.ndarray]:
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
        time_array : np.array
            Array of time points for simulation.
        event_time : float
            The time (in seconds) at which the amplitude step event occurs.

        Returns
        -------
        tuple[bool, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - is_overdamped: True if the initial system is overdamped, False
              otherwise.
            - q_pcc_final: The final calculated reactive power at the point of
              common coupling.
            - q_up_final: The final upper reactive power envelope.
            - q_down_final: The final lower reactive power envelope.
        """
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
        return None, q_pcc, q_up, q_down

    def _get_delta_q(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
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
        time_array : np.array
            Array of time points for simulation.
        event_time : float
            The time (in seconds) at which the amplitude step event occurs.

        Returns
        -------
        tuple[bool, list, np.ndarray, np.ndarray, list, list]
            A tuple containing:
            - is_overdamped: True if the initial system is overdamped, False
              otherwise.
            - delta_q_array: List of delta_q arrays for original, min, and max
              parameter variations.
            - delta_q_min: delta_q array specifically calculated for the minimum
              parameter case.
            - delta_q_max: delta_q array specifically calculated for the maximum
              parameter case.
        """
        # Prepare arrays for D (damping factor) and H (inertia constant)
        # parameters, including nominal, minimum, and maximum variations.
        d_array = np.array([D, D * self._gfm_params.RatioMin, D * self._gfm_params.RatioMax])
        h_array = np.array([H, H / self._gfm_params.RatioMin, H / self._gfm_params.RatioMax])

        # Stores delta_q for nominal, min, max D/H variations.
        delta_q_array = []

        # Loop through parameter variations (nominal, min, max) to calculate
        # delta_q, p_peak, and epsilon for each.
        for i in range(len(d_array)):
            delta_q = self._calculate_delta_q_for_damping(
                d_array[i], h_array[i], Xeff, time_array, event_time
            )
            delta_q_array.append(delta_q)

        # Calculate specific delta_q for min and max parameter cases.
        delta_q_min = self._get_delta_q_min(D, H, Xeff, time_array, event_time)
        delta_q_max = self._get_delta_q_max(D, H, Xeff, time_array, event_time)

        # Print debug information for delta_q values.
        dycov_logging.get_logger("AmplitudeStep").debug(
            f"DeltaQ Nom {delta_q_array[self._ORIGINAL_PARAMS_IDX]}"
        )
        dycov_logging.get_logger("AmplitudeStep").debug(
            f"DeltaQ Min {delta_q_array[self._MINIMUM_PARAMS_IDX]}"
        )
        dycov_logging.get_logger("AmplitudeStep").debug(
            f"DeltaQ Max {delta_q_array[self._MAXIMUM_PARAMS_IDX]}"
        )
        dycov_logging.get_logger("AmplitudeStep").debug(f"Q Min {delta_q_min}")
        dycov_logging.get_logger("AmplitudeStep").debug(f"Q Max {delta_q_max}")

        # Return all calculated delta_q arrays, p_peak values, and damping
        # information. The boolean indicates if the initial system is overdamped.
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
        time_array: np.array,
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
        time_array : np.array
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
        # Extract the original (nominal) delta_q from the provided lists.
        delta_q = delta_q_array[self._ORIGINAL_PARAMS_IDX]

        # Calculate the theoretical reactive power at the Point of Common
        # Coupling (PCC). This is based on the initial power (Q0) and delta_q,
        # adjusted by the sign of voltage_step to reflect the direction of
        # power change.
        q_pcc = self._gfm_params.Q0 + delta_q * -(
            self._gfm_params.voltage_step / np.abs(self._gfm_params.voltage_step)
        )
        # Clip the calculated PCC power to stay within defined minimum and
        # maximum power limits.
        q_pcc = self._cut_signal(self._gfm_params.QMin, q_pcc, self._gfm_params.QMax)

        q_up = self._gfm_params.Q0 + np.minimum(
            delta_q_max, self._gfm_params.QMax - self._gfm_params.Q0
        ) * -(self._gfm_params.voltage_step / np.abs(self._gfm_params.voltage_step))

        tunnel = self._get_tunnel(Xeff)
        q_down = self._gfm_params.Q0 + np.minimum(
            delta_q_min, self._gfm_params.QMax - self._gfm_params.Q0 - tunnel
        ) * -(self._gfm_params.voltage_step / np.abs(self._gfm_params.voltage_step))

        # If EMT simulation flag is true, apply a small delay to the final
        # power signals.
        if self._gfm_params.EMT:
            q_up_final = self._apply_delay(0.02, q_up[0], time_array, q_up)
            q_down_final = self._apply_delay(0.02, q_down[0], time_array, q_down)
            q_pcc_final = self._apply_delay(0.02, q_pcc[0], time_array, q_pcc)
        else:
            # Otherwise, the limited envelopes are the final envelopes.
            q_up_final = q_up
            q_down_final = q_down
            q_pcc_final = q_pcc

        # Ensure that the upper envelope is always greater than or equal to the
        # lower envelope at the end of the simulation. If not, swap them.
        if q_up_final[-1] < q_down_final[-1]:
            q_temp = q_down_final
            q_down_final = q_up_final
            q_up_final = q_temp

        # Return the final calculated power signals for PCC, upper envelope,
        # and lower envelope.
        return q_pcc_final, q_up_final, q_down_final

    def _get_delta_q_base(
        self, D: float, H: float, Xeff: float, time_array: np.array
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
        time_array : np.array
            Array of time points.

        Returns
        -------
        np.ndarray
            The base delta_q waveform.
        """
        # Grid reactance, calculated from Short Circuit Ratio (SCR).
        x_gr = 1 / self._gfm_params.SCR
        # Sum of effective reactance and grid reactance.
        x_total_initial = Xeff + x_gr

        voltage_step = self._gfm_params.voltage_step / 100.0

        delta_v_inf = -np.abs(voltage_step * x_total_initial / Xeff)
        delta_iq = np.abs(delta_v_inf / x_total_initial)

        tau = -self._gfm_params.TimeTo90 / np.log(0.1)

        # Calculate individual terms of the delta_q1 equation.
        delta_q1 = delta_iq * (1 - np.exp(-time_array / tau))
        return delta_q1

    def _calculate_delta_q_for_damping(
        self,
        D: float,
        H: float,
        Xeff: float,
        time_array: np.array,
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
        time_array : np.array
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The delta_q array for the system, with pre-event values zeroed.
        """
        # Get the base delta_q waveform.
        delta_q1 = self._get_delta_q_base(D, H, Xeff, time_array)
        # Set delta_q to 0 for all time points occurring before the event_time.
        delta_q = np.where(time_array < event_time, 0, delta_q1)
        return delta_q

    def _get_delta_q_min(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
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
        time_array : np.array
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The minimum delta_q array for the overdamped system.
        """
        # Grid reactance, calculated from Short Circuit Ratio (SCR).
        x_gr = 1 / self._gfm_params.SCR
        # Sum of effective reactance and grid reactance.
        x_total_initial = Xeff + x_gr

        voltage_step = self._gfm_params.voltage_step / 100.0

        delta_v_inf = np.abs(voltage_step * x_total_initial / Xeff)
        delta_iq = np.abs(delta_v_inf / x_total_initial)

        tunnel = self._get_tunnel(Xeff)

        delta_q1 = self._get_delta_q_base(D, H, Xeff, time_array)
        delta_q1_margined = np.minimum(delta_q1, delta_iq - tunnel)
        delta_q1_delayed = self._apply_delay(0.01, 0, time_array, delta_q1_margined)
        delta_q = np.where(time_array < event_time, 0, delta_q1_delayed)
        return delta_q

    def _get_delta_q_max(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
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
        time_array : np.array
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        np.ndarray
            The maximum delta_q array for the overdamped system.
        """
        ttunnel = self._gfm_params.TimeForTunnel
        # Grid reactance, calculated from Short Circuit Ratio (SCR).
        x_gr = 1 / self._gfm_params.SCR
        # Sum of effective reactance and grid reactance.
        x_total_initial = Xeff + x_gr

        voltage_step = self._gfm_params.voltage_step / 100.0

        delta_v_inf = np.abs(voltage_step * x_total_initial / Xeff)
        delta_iq = np.abs(delta_v_inf / x_total_initial)

        tunnel = self._get_tunnel(Xeff)

        delta_q1 = (
            delta_iq
            + self._gfm_params.MarginHigh * delta_iq * np.exp(-time_array / (ttunnel / 3))
            + tunnel
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
        # Grid reactance, calculated from Short Circuit Ratio (SCR).
        x_gr = 1 / self._gfm_params.SCR
        # Sum of effective reactance and grid reactance.
        x_total_initial = Xeff + x_gr

        voltage_step = self._gfm_params.voltage_step / 100.0

        delta_v_inf = np.abs(voltage_step * x_total_initial / Xeff)
        delta_iq = np.abs(delta_v_inf / x_total_initial)

        return max(
            self._gfm_params.FinalAllowedTunnelPn,  # Fixed power component
            self._gfm_params.FinalAllowedTunnelVariation * delta_iq,
        )

    def _apply_delay(
        self, delay: float, delayed_value: float, time_array: np.ndarray, signal: np.ndarray
    ) -> np.ndarray:
        """
        Applies a time delay to a given signal. The delay is implemented by
        prepending a constant `delayed_value` for the duration of the `delay`
        time. The output signal is truncated to the original signal's length.

        Parameters
        ----------
        delay : float
            The desired delay time in seconds.
        delayed_value : float
            The constant value to fill the signal during the delay period.
        time_array : np.ndarray
            The time array corresponding to the `signal`. Assumed to have a
            constant time step.
        signal : np.ndarray
            The original signal (waveform) to be delayed.

        Returns
        -------
        np.ndarray
            The delayed signal, which has the same length as the original
            `signal`.
        """
        if len(time_array) < 2:
            # If there are fewer than 2 time points, a sampling frequency
            # cannot be determined, so return the original signal as no delay
            # can be applied meaningfully.
            return signal
        # Calculate the sampling interval.
        fs = time_array[1] - time_array[0]

        # Calculate the number of samples corresponding to the desired delay.
        # Rounding is used to get an integer number of samples.
        delay_samples = int(round(delay / fs))

        if delay_samples >= len(time_array):
            # If the calculated delay in samples is greater than or equal to
            # the length of the original signal, the entire signal will
            # effectively be replaced by the `delayed_value`.
            return np.full_like(signal, delayed_value)

        # Create an array filled with `delayed_value` for the duration of
        # the delay.
        sample = np.full(delay_samples, delayed_value)
        # Concatenate this delay 'prefix' with the original signal.
        # Then, truncate the combined array to the original signal's length,
        # effectively shifting the signal values.
        return np.concatenate((sample, signal))[: len(time_array)]

    def _cut_signal(self, value_min: float, signal: np.ndarray, value_max: float) -> np.ndarray:
        """
        Clips the values of a given signal array to ensure they stay
        within a specified minimum (`value_min`) and maximum (`value_max`)
        range. Values below `value_min` are set to `value_min`, and values
        above `value_max` are set to `value_max`.

        Parameters
        ----------
        value_min : float
            The minimum allowed value for the signal.
        signal : np.ndarray
            The input signal array whose values need to be clipped.
        value_max : float
            The maximum allowed value for the signal.

        Returns
        -------
        np.ndarray
            The signal with its values clipped within the specified limits.
        """
        # Use np.where to efficiently apply the clipping.
        # First, ensure no value is below value_min.
        signal = np.where(signal < value_min, value_min, signal)
        # Second, ensure no value is above value_max.
        signal = np.where(signal > value_max, value_max, signal)
        return signal
