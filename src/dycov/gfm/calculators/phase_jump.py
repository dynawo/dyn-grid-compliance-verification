#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

from typing import Optional

import numpy as np
from scipy import signal

from dycov.gfm import constants
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.parameters import GFMParameters
from dycov.logging import dycov_logging


class PhaseJump(GFMCalculator):
    """Handles the GFM response to a phase jump event.

    The responses are those of the transfer function of a virtual synchronous machine whose PLL
    is a washout filter, which serves any damping without telling overdamped from underdamped.
    """

    def __init__(self, gfm_params: GFMParameters) -> None:
        """
        Initializes the PhaseJump calculator.

        Parameters
        ----------
        gfm_params : GFMParameters
            The shared configuration parameters.
        """
        super().__init__(gfm_params=gfm_params)
        self._delta_phase = gfm_params.get_delta_phase()
        self._initial_active_power = gfm_params.get_initial_active_power()
        self._min_active_power = gfm_params.get_min_active_power()
        self._max_active_power = gfm_params.get_max_active_power()
        self._t_pll = (
            gfm_params.get_pll_time_constant() or constants.PHASE_JUMP_PLL_TIME_CONSTANT_S
        )

    def get_plot_parameter_names(self) -> list[str]:
        """
        Retrieves parameters relevant for rendering Phase Jump plots.

        Returns
        -------
        list[str]
            A list of parameter names to be displayed.
        """
        return ["P0", "Q0", "DeltaPhase", "AngleStepAtPDR", "SCR", "Xeff", "D", "H"]

    def calculate_envelopes(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the active power response and bounding envelopes for a Phase Jump.

        Parameters
        ----------
        D : float
            The damping constant.
        H : float
            The inertia constant.
        Xeff : float
            The effective reactance.
        time_array : np.ndarray
            The simulation time vector, equally spaced.
        event_time : float
            The timestamp of the event.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            The magnitude name ("Ip"),
            main signal, upper envelope, and lower envelope arrays.
        """
        logger = dycov_logging.get_logger("PhaseJump")
        logger.debug(f"Input Params D={D} H={H} Xeff {Xeff}")
        logger.debug(
            f"Input Params Phase={self._delta_phase} SCR={self._scr} "
            f"P0={self._initial_active_power} "
            f"PMin={self._min_active_power} "
            f"PMax={self._max_active_power}"
        )

        x_total = Xeff + 1 / self._scr
        phase_jump = np.deg2rad(self._delta_phase)

        self._h_vals = np.array([H, H * self._min_ratio, H * self._max_ratio])
        self._d_vals = np.array([D, D * self._max_ratio, D * self._min_ratio])
        transfer_functions = [
            self._get_transfer_function(d_val, h_val, x_total)
            for d_val, h_val in zip(self._d_vals, self._h_vals)
        ]
        responses = [
            self._get_response(transfer_function, phase_jump, time_array, event_time)
            for transfer_function in transfer_functions
        ]

        nominal = responses[self._ORIGINAL_PARAMS_IDX]
        amplified = (1 + self._margin_high) * nominal
        reduced = (1 - self._margin_low) * nominal
        traces = responses + [
            amplified,
            reduced,
            self._delay(reduced, constants.PHASE_JUMP_REDUCED_RESPONSE_DELAY_S, time_array),
        ]
        decay_bound = self._get_decay_bound(
            amplified, transfer_functions[self._ORIGINAL_PARAMS_IDX], time_array, event_time
        )
        if decay_bound is not None:
            traces.append(decay_bound)

        p_peak = abs(phase_jump) * self._initial_voltage * self._grid_voltage / x_total
        tunnel = self._get_time_tunnel(p_peak=p_peak, time_array=time_array, event_time=event_time)
        final_tunnel = self._get_tunnel(p_peak)

        p_pcc = self._initial_active_power + nominal
        p_up = np.clip(
            self._initial_active_power + np.maximum.reduce(traces) + tunnel,
            final_tunnel - 1,
            self._max_active_power,
        )
        p_down = np.clip(
            self._initial_active_power + np.minimum.reduce(traces) - tunnel,
            self._min_active_power,
            1 - final_tunnel,
        )

        if self._is_emt_flag:
            p0 = self._initial_active_power
            upper_envelope = self._apply_delay(self._emt_delay, p0, time_array, p_up)
            lower_envelope = self._apply_delay(self._emt_delay, p0, time_array, p_down)
            pcc_signal = self._apply_delay(self._emt_delay, p0, time_array, p_pcc)
        else:
            upper_envelope, lower_envelope, pcc_signal = p_up, p_down, p_pcc

        return "Ip", pcc_signal, upper_envelope, lower_envelope

    def _get_transfer_function(
        self, D: float, H: float, x_total: float
    ) -> signal.TransferFunction:
        """
        Builds the transfer function from the phase of the infinite bus to the active power.

        Parameters
        ----------
        D : float
            The damping constant.
        H : float
            The inertia constant.
        x_total : float
            The reactance between the converter and the infinite bus.

        Returns
        -------
        signal.TransferFunction
            The transfer function, in pu of active power per radian.
        """
        u_prod = self._initial_voltage * self._grid_voltage
        w_b = self._base_angular_frequency
        wn = np.sqrt(w_b * u_prod / (2 * H * x_total))
        xi = D / 2 * np.sqrt(x_total / (2 * H * w_b * u_prod))
        angle_damping = constants.ANGLE_DAMPING_PER_DAMPING * D + constants.ANGLE_DAMPING_OFFSET
        t_pll = self._t_pll

        return signal.TransferFunction(
            [-2 * H * t_pll, -2 * H - D * t_pll, 0, 0],
            [
                w_b * t_pll / wn**2,
                w_b / wn**2 + w_b * t_pll * 2 * xi / wn + angle_damping * t_pll,
                w_b * t_pll + angle_damping,
                w_b,
            ],
        )

    @staticmethod
    def _get_response(
        transfer_function: signal.TransferFunction,
        phase_jump: float,
        time_array: np.ndarray,
        event_time: float,
    ) -> np.ndarray:
        """
        Simulates the active power deviation of the converter after the phase jump.

        Parameters
        ----------
        transfer_function : signal.TransferFunction
            The transfer function of the converter.
        phase_jump : float
            The phase jump of the infinite bus, in radians.
        time_array : np.ndarray
            The simulation time vector, equally spaced.
        event_time : float
            The timestamp of the event.

        Returns
        -------
        np.ndarray
            The active power deviation in pu, zero before the event.
        """
        phase_step = np.where(time_array >= event_time, phase_jump, 0.0)
        _, response, _ = signal.lsim(transfer_function, U=phase_step, T=time_array - time_array[0])
        return response

    @staticmethod
    def _delay(deviation: np.ndarray, delay: float, time_array: np.ndarray) -> np.ndarray:
        """
        Delays a deviation, which is zero meanwhile, its value before the event.

        Parameters
        ----------
        deviation : np.ndarray
            The deviation to delay.
        delay : float
            The delay in seconds.
        time_array : np.ndarray
            The simulation time vector.

        Returns
        -------
        np.ndarray
            The delayed deviation.
        """
        return np.interp(time_array - delay, time_array, deviation, left=0.0)

    def _get_decay_bound(
        self,
        deviation: np.ndarray,
        transfer_function: signal.TransferFunction,
        time_array: np.ndarray,
        event_time: float,
    ) -> Optional[np.ndarray]:
        """
        Fits an exponential to the decay of the peaks of a deviation.

        The exponential starts at the largest peak, the jump itself in practice, and takes three
        time constants to fall to the 5 % of it the peaks fall to. When no peak falls that low,
        the deviation stops oscillating before it does, and the exponential falls to 5 % when the
        deviation itself does. When the deviation does not fall that low within the time vector,
        the exponential decays as the slowest mode of the converter.

        Parameters
        ----------
        deviation : np.ndarray
            The deviation whose peaks it bounds.
        transfer_function : signal.TransferFunction
            The transfer function the deviation is the response of.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp of the event.

        Returns
        -------
        Optional[np.ndarray]
            The exponential, zero before the event, or None when the converter has a mode that
            does not decay.
        """
        after_event = time_array >= event_time
        time = time_array[after_event]
        values = deviation[after_event]

        slopes = np.diff(values)
        peak_indices = np.concatenate(([0], np.flatnonzero(slopes[:-1] * slopes[1:] < 0) + 1))
        noise_floor = constants.PHASE_JUMP_NOISE_FLOOR * np.max(np.abs(values))
        peak_indices = peak_indices[np.abs(values[peak_indices]) >= noise_floor]
        peaks = np.abs(values[peak_indices])
        peak_times = time[peak_indices]

        largest = int(np.argmax(peaks))
        amplitude = peaks[largest]
        threshold = constants.PHASE_JUMP_DECAY_THRESHOLD * amplitude
        slowest_decay_rate = np.min(-np.real(transfer_function.poles))
        if slowest_decay_rate <= 0:
            return None
        slowest_time_constant = 1 / slowest_decay_rate

        decay_time = self._get_decay_time(peaks[largest:], peak_times[largest:], threshold)
        if decay_time is None:
            decay_time = self._get_settling_time(
                np.abs(values),
                time,
                threshold,
                constants.PHASE_JUMP_DECAY_TIME_CONSTANTS * slowest_time_constant,
            )
        if decay_time is None:
            time_constant = slowest_time_constant
        else:
            time_constant = (decay_time - event_time) / constants.PHASE_JUMP_DECAY_TIME_CONSTANTS
        sign = np.sign(values[peak_indices[largest]])
        bound = sign * amplitude * np.exp(-(time_array - peak_times[largest]) / time_constant)
        return np.where(after_event, bound, 0.0)

    @staticmethod
    def _get_decay_time(
        peaks: np.ndarray, peak_times: np.ndarray, threshold: float
    ) -> Optional[float]:
        """
        Finds when the line between two consecutive peaks crosses the threshold.

        Parameters
        ----------
        peaks : np.ndarray
            The absolute values of the peaks, from the largest one.
        peak_times : np.ndarray
            The times of the peaks.
        threshold : float
            The value the peaks fall below.

        Returns
        -------
        Optional[float]
            The crossing time, or None when no peak falls below the threshold.
        """
        below = np.flatnonzero(peaks < threshold)
        if below.size == 0:
            return None
        last, first = below[0] - 1, below[0]
        slope = (peaks[first] - peaks[last]) / (peak_times[first] - peak_times[last])
        return peak_times[last] + (threshold - peaks[last]) / slope

    @staticmethod
    def _get_settling_time(
        magnitude: np.ndarray, time: np.ndarray, threshold: float, settling_duration: float
    ) -> Optional[float]:
        """
        Finds when a deviation falls below the threshold for good.

        Parameters
        ----------
        magnitude : np.ndarray
            The absolute value of the deviation.
        time : np.ndarray
            The times of the deviation.
        threshold : float
            The value the deviation falls below.
        settling_duration : float
            How long the deviation has to stay below the threshold to count as settled, since
            an oscillation that outlasts the time vector may only be between two peaks.

        Returns
        -------
        Optional[float]
            When the deviation crosses the threshold for the last time, or None when it does
            not stay below it for the settling duration.
        """
        above = np.flatnonzero(magnitude >= threshold)
        if above.size == 0 or above[-1] == len(magnitude) - 1:
            return None
        last, first = above[-1], above[-1] + 1
        crossing = np.interp(
            threshold, [magnitude[first], magnitude[last]], [time[first], time[last]]
        )
        if time[-1] - crossing < settling_duration:
            return None
        return crossing

    def _get_tunnel(self, p_peak: float) -> float:
        """
        Calculates the static tolerance margin ('tunnel') for Phase Jump.

        Parameters
        ----------
        p_peak : float
            The peak power of the jump.

        Returns
        -------
        float
            The calculated tunnel margin in pu.
        """
        return max(self._final_allowed_tunnel_pn, self._final_allowed_tunnel_variation * p_peak)
