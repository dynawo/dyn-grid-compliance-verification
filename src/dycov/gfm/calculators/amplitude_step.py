#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

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

    def __init__(self, gfm_params: GFMParameters) -> None:
        super().__init__(gfm_params=gfm_params)
        self._voltage_step = gfm_params.get_voltage_step_at_grid()
        self._initial_reactive_power = gfm_params.get_initial_reactive_power()
        self._min_reactive_power = gfm_params.get_min_reactive_power()
        self._max_reactive_power = gfm_params.get_max_reactive_power()
        self._time_for_tunnel = gfm_params.get_time_for_tunnel()
        self._time_to_90 = gfm_params.get_time_to_90()
        self._Xgrid = gfm_params.get_grid_reactance()

    def get_plot_parameter_names(self) -> list[str]:
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
        logger = dycov_logging.get_logger("AmplitudeStep")
        logger.debug(f"Input Params D={D} H={H} Xeff={Xeff}")
        logger.debug(
            f"Input Params Voltage={self._voltage_step} SCR={self._scr} "
            f"Q0={self._initial_reactive_power} QMin={self._min_reactive_power} QMax={self._max_reactive_power}"
        )

        delta_iq_base, delta_iq_min, delta_iq_max = self._get_delta_iq(
            D=D,
            H=H,
            Xeff=Xeff,
            time_array=time_array,
            event_time=event_time,
        )

        q_pcc, q_up, q_down = self._get_envelopes(
            delta_iq_base=delta_iq_base,
            delta_iq_min=delta_iq_min,
            delta_iq_max=delta_iq_max,
            Xeff=Xeff,
        )

        iq_pcc_final, iq_up_final, iq_down_final = self.apply_emt_delay_to_envelopes(
            time_array, q_pcc, q_up, q_down
        )

        return "Iq", iq_pcc_final, iq_up_final, iq_down_final

    def _get_delta_iq(
        self, D: float, H: float, Xeff: float, time_array: np.ndarray, event_time: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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
        volt_step_upcc = (self._voltage_step / 100.0) * Xeff / (Xeff + self._Xgrid)
        sign_K = np.sign(volt_step_upcc)
        tunnel = self._get_tunnel(Xeff)

        q_down = np.maximum(
            np.minimum(
                self._initial_reactive_power - sign_K * delta_iq_min, self._max_reactive_power
            ),
            -self._max_reactive_power,
        )

        q_up = np.maximum(
            np.minimum(
                self._initial_reactive_power - sign_K * delta_iq_max,
                self._max_reactive_power + tunnel,
            ),
            -self._max_reactive_power - tunnel,
        )

        q_expected_unclamped = self._initial_reactive_power - sign_K * delta_iq_base
        q_expected = np.maximum(
            np.minimum(q_expected_unclamped, self._max_reactive_power),
            -self._max_reactive_power,
        )

        return q_expected, q_up, q_down

    def _get_delta_iq_base(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
        voltage_step = self._voltage_step / 100.0
        delta_iq_final = np.abs(voltage_step / (Xeff + self._Xgrid))
        tau = -self._time_to_90 / np.log(0.1)
        exponential_part = delta_iq_final * (1 - np.exp(-time_array / tau))
        return exponential_part

    def _calculate_delta_iq_base(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
        return self._get_delta_iq_base(Xeff, time_array)

    def _get_delta_iq_min(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
        base_curve = 0.9 * self._get_delta_iq_base(Xeff, time_array)
        tunnel = self._get_tunnel(Xeff)
        voltage_step_pu = self._voltage_step / 100.0

        max_delta_iq = np.abs(voltage_step_pu / (Xeff + self._Xgrid))
        lower_envelope_limit = max_delta_iq - tunnel

        delta_iq_lower = np.minimum(base_curve, lower_envelope_limit)
        delta_iq_lower = np.where(time_array < self._time_to_90, 0.0, delta_iq_lower)
        return delta_iq_lower

    def _get_delta_iq_max(self, Xeff: float, time_array: np.ndarray) -> np.ndarray:
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

        delta_iq_upper = steady_state_upper_limit + np.where(
            transient_condition, transient_boost_value, 0.0
        )
        return delta_iq_upper

    def _get_tunnel(self, Xeff: float) -> float:
        voltage_step = self._voltage_step / 100.0
        delta_iq = np.abs(voltage_step / (Xeff + self._Xgrid))
        return max(self._final_allowed_tunnel_pn, self._final_allowed_tunnel_variation * delta_iq)
