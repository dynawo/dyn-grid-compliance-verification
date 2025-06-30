#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from collections import namedtuple
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

DEBUG = True
# Named tuples for GFM parameters and base values.
# These are used to store the parameters and computed values for the GFM
# phase jump calculations.
GFM_Params = namedtuple(
    "GFM_Params",
    [
        "EMT",  # EMT simulation flag
        "RatioMin",
        "RatioMax",
        "P0",  # Initial power (pu)
        "delta_theta",
        "SCR",
        "Xtr",  # Transformer reactance (pu)
        "Wb",  # Base angular frequency (rad/s)
        "Ucv",  # RMS voltage Uconverter (pu)
        "Ugr",  # RMS voltage Ugrid (pu)
        "MarginHigh",
        "MarginLow",
        "FinalAllowedTunnelVariation",
        "FinalAllowedTunnelPn",
        "PMax",
        "PMin",
    ],
)


class PhaseJump:
    """
    Class to calculate the GFM phase jump and generate related plots and CSVs.
    """

    # Constants for parameter array indexing (original, min, max)
    _ORIGINAL_PARAMS_IDX = 0
    _MINIMUM_PARAMS_IDX = 1
    _MAXIMUM_PARAMS_IDX = 2
    # Threshold to differentiate overdamped from underdamped (critically damped
    # included with overdamped)
    _EPSILON_THRESHOLD = 1.0

    def __init__(self, gfm_params: GFM_Params):
        """
        Initializes the PhaseJump class with GFM parameters.

        Parameters
        ----------
        gfm_params: GFM_Params
            Parameters for the GFM phase jump calculations.
        """
        self._gfm_params = gfm_params

    def get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> tuple[bool, list, list, list]:
        Xgr = 1 / self._gfm_params.SCR
        Xtotal_initial = self._gfm_params.Xtr + Xeff + Xgr
        epsilon_initial_check = (
            D
            / 2
            * np.sqrt(
                Xtotal_initial
                / (2 * H * self._gfm_params.Wb * self._gfm_params.Ucv * self._gfm_params.Ugr)
            )
        )

        D_array = np.array([D, D * self._gfm_params.RatioMin, D * self._gfm_params.RatioMax])
        H_array = np.array([H, H / self._gfm_params.RatioMin, H / self._gfm_params.RatioMax])

        DeltaP_array = []
        Ppeak_array = []
        epsilon_array = []

        for i in range(len(D_array)):
            if epsilon_initial_check > self._EPSILON_THRESHOLD:
                DeltaP, Ppeak, epsilon = self._get_overdamped_delta_p(
                    D_array[i],
                    H_array[i],
                    Xeff,
                    time_array,
                    event_time,
                )
                DeltaP_array.append(DeltaP)
                Ppeak_array.append(Ppeak)
                epsilon_array.append(epsilon)
            else:
                DeltaP, Ppeak, epsilon = self._get_underdamped_delta_p(
                    D_array[i],
                    H_array[i],
                    Xeff,
                    time_array,
                    event_time,
                )
                DeltaP_array.append(DeltaP)
                Ppeak_array.append(Ppeak)
                epsilon_array.append(epsilon)

        if epsilon_initial_check > self._EPSILON_THRESHOLD:
            DeltaP_min = self._get_overdamped_delta_p_min(D, H, Xeff, time_array, event_time)
            DeltaP_max = self._get_overdamped_delta_p_max(D, H, Xeff, time_array, event_time)
        else:
            DeltaP_min = self._get_underdamped_delta_p_min(D, H, Xeff, time_array, event_time)
            DeltaP_max = self._get_underdamped_delta_p_max(D, H, Xeff, time_array, event_time)

        return (
            epsilon_initial_check > self._EPSILON_THRESHOLD,
            DeltaP_array,
            DeltaP_min,
            DeltaP_max,
            Ppeak_array,
            epsilon_array,
        )

    def get_envelopes(
        self,
        DeltaP_array: list,
        DeltaP_min: np.ndarray,
        DeltaP_max: np.ndarray,
        Ppeak_array: list,
        time_array: np.array,
        event_time: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:

        DeltaP = DeltaP_array[self._ORIGINAL_PARAMS_IDX]
        Ppeak = Ppeak_array[self._ORIGINAL_PARAMS_IDX]

        tunnel = self._get_time_tunnel(Ppeak=Ppeak, time_array=time_array, event_time=event_time)

        P_pcc = self.cut_signal(
            self._gfm_params.PMin, self._gfm_params.P0 + DeltaP, self._gfm_params.PMax
        )

        list_of_arrays = DeltaP_array + [DeltaP_min, DeltaP_max]

        pdown_no_P0, pup_no_P0 = self._calculate_unlimited_power_envelopes(list_of_arrays, tunnel)
        pdown_limited, pup_limited = self._limit_power_envelopes(
            pdown_no_P0, pup_no_P0, self._get_tunnel(Ppeak_array)
        )

        if self._gfm_params.EMT:
            P_up_final = self._apply_delay(0.02, pup_limited[0], time_array, pup_limited)
            P_down_final = self._apply_delay(0.02, pdown_limited[0], time_array, pdown_limited)
            P_pcc = self._apply_delay(0.02, P_pcc[0], time_array, P_pcc)
        else:
            P_up_final = pup_limited
            P_down_final = pdown_limited

        return P_pcc, P_up_final, P_down_final

    def save_results_to_csv(
        self,
        path: Path,
        time_array: np.ndarray,
    ) -> None:
        """
        Save the calculated results to a CSV file.

        Parameters
        ----------
        path : Path
            The path where the CSV file will be saved.
        time_array : np.ndarray
            The time array.
        """
        df = pd.DataFrame(
            {
                "Time (s)": time_array,
                "P_PCC (pu)": self._theoretical_response_from_vsm,
                "P_down (pu)": self._pdown,
                "P_up (pu)": self._pup,
            }
        )
        df.to_csv(path, index=False)

    def plot_results(
        self,
        path: Path,
        P_pcc: np.ndarray,
        P_up: np.ndarray,
        P_down: np.ndarray,
        time: np.ndarray,
        event_time: float,
        shift_time: float,
        title: str,
    ) -> None:
        """
        Plot the results of the GFM phase jump.

        Parameters
        ----------
        path : Path
            The path where the plot will be saved.
        time : np.ndarray
            The time array.
        event_time : float
            The time of the event in seconds.
        shift_time : float
            The time shift in milliseconds to adjust the event time for plotting.
        title : str
            The title of the plot, which will also be used for the saved file name.
        """
        plt.figure(figsize=(8, 5))
        plt.plot(
            time,
            P_pcc,
            label="Theoretical response from VSM",
            linewidth="3",
        )
        plt.plot(time, P_down, label="Pdown", linewidth=2)
        plt.plot(time, P_up, label="Pup", linewidth=2)
        plt.xlabel("sec")
        plt.ylabel("P at PCC (pu)")
        plt.title(title)
        plt.axvline(
            x=event_time + shift_time / 1000,
            color="black",
            linestyle="--",
            label="t at Event Time",
        )
        plt.legend(loc="lower right")
        plt.grid(True)
        plt.savefig(path, bbox_inches="tight", dpi=300)
        plt.close()  # Close the figure to free up memory

    def _calculate_unlimited_power_envelopes(
        self, list_of_arrays: list[np.ndarray], tunnel: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculates the unlimited power down and power up envelopes.

        Parameters
        ----------
        list_of_arrays : list[np.ndarray]
            A list of arrays to be used for min/max reduction.
        tunnel : np.ndarray
            The tunnel response array.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing:
            - pdown_no_P0: Unlimited power down without P0.
            - pup_no_P0: Unlimited power up without P0.
        """
        pdown_no_P0 = np.minimum.reduce(list_of_arrays) - tunnel
        pup_no_P0 = np.maximum.reduce(list_of_arrays) + tunnel
        return pdown_no_P0, pup_no_P0

    def _limit_power_envelopes(
        self,
        pdown_no_P0: np.ndarray,
        pup_no_P0: np.ndarray,
        tunnel: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Limits the power down and power up envelopes.

        Parameters
        ----------
        pdown_no_P0 : np.ndarray
            Unlimited power down without P0.
        pup_no_P0 : np.ndarray
            Unlimited power up without P0.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing:
            - pdown_limited: Limited power down.
            - pup_limited: Limited power up.
        """
        delta_theta_sign = 1 if self._gfm_params.delta_theta > 0 else -1

        pdown_limited = np.minimum(
            np.maximum(
                self._gfm_params.P0 - delta_theta_sign * pdown_no_P0,
                -1 + tunnel,
            ),
            1 - tunnel,
        )
        pup_limited = np.minimum(
            np.maximum(
                self._gfm_params.P0 - 1 * delta_theta_sign * pup_no_P0,
                -1 * self._gfm_params.PMax,
            ),
            self._gfm_params.PMax,
        )
        return pdown_limited, pup_limited

    def _apply_delay(
        self, delay: float, delayed_value: float, time_array: np.ndarray, signal: np.ndarray
    ) -> np.ndarray:
        """
        Applies a delay to a given signal.

        Parameters
        ----------
        delay : float
            The delay time in seconds.
        delayed_value : float
            The value to fill during the delay period.
        time_array : np.ndarray
            The time array corresponding to the signal.
        signal : np.ndarray
            The original signal to be delayed.

        Returns
        -------\
        np.ndarray
            The delayed signal.
        """
        if len(time_array) < 2:
            return signal  # Cannot calculate fs if there's only one or no point.
        fs = time_array[1] - time_array[0]  # Assumes constant time step.

        delay_samples = int(round(delay / fs))

        if delay_samples >= len(time_array):
            # If the delay is greater than the signal length, the entire signal
            # will be the delayed value.
            return np.full_like(signal, delayed_value)

        sample = np.full(delay_samples, delayed_value)
        return np.concatenate((sample, signal))[: len(time_array)]

    def _get_overdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> np.ndarray:
        delta_theta = np.abs(self._gfm_params.delta_theta * np.pi / 180)
        Xgr = 1 / self._gfm_params.SCR
        Xtotal_initial = self._gfm_params.Xtr + Xeff + Xgr

        epsilon = (
            D
            / 2
            * np.sqrt(
                Xtotal_initial
                / (2 * H * self._gfm_params.Wb * self._gfm_params.Ucv * self._gfm_params.Ugr)
            )
        )
        wn = np.sqrt(
            self._gfm_params.Wb
            * self._gfm_params.Ucv
            * self._gfm_params.Ugr
            / (2 * H * Xtotal_initial)
        )
        wd = wn * np.sqrt(epsilon**2 - 1)

        alpha = epsilon * wn + wd
        beta = epsilon * wn - wd

        A = 1 / (beta - alpha)
        B = -A

        Ppeak = delta_theta * self._gfm_params.Ucv * self._gfm_params.Ugr / Xtotal_initial

        term1 = 2 * H * A * (1 - alpha * np.exp(-alpha * time_array))
        term2 = 2 * H * B * (1 - beta * np.exp(-beta * time_array))
        term3 = D * A * np.exp(-alpha * time_array)
        term4 = D * B * np.exp(-beta * time_array)

        DeltaP1 = (
            (1 + self._gfm_params.MarginLow) * Ppeak / (2 * H) * (term1 + term2 + term3 + term4)
        )
        DeltaP = np.where(time_array < event_time, 0, DeltaP1)

        return DeltaP

    def _get_overdamped_delta_p_max(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> np.ndarray:
        delta_theta = np.abs(self._gfm_params.delta_theta * np.pi / 180)
        Xgr = 1 / self._gfm_params.SCR
        Xtotal_initial = self._gfm_params.Xtr + Xeff + Xgr

        epsilon = (
            D
            / 2
            * np.sqrt(
                Xtotal_initial
                / (2 * H * self._gfm_params.Wb * self._gfm_params.Ucv * self._gfm_params.Ugr)
            )
        )
        wn = np.sqrt(
            self._gfm_params.Wb
            * self._gfm_params.Ucv
            * self._gfm_params.Ugr
            / (2 * H * Xtotal_initial)
        )
        wd = wn * np.sqrt(epsilon**2 - 1)

        alpha = epsilon * wn + wd
        beta = epsilon * wn - wd

        A = 1 / (beta - alpha)
        B = -A

        Ppeak = delta_theta * self._gfm_params.Ucv * self._gfm_params.Ugr / Xtotal_initial

        term1 = 2 * H * A * (1 - alpha * np.exp(-alpha * time_array))
        term2 = 2 * H * B * (1 - beta * np.exp(-beta * time_array))
        term3 = D * A * np.exp(-alpha * time_array)
        term4 = D * B * np.exp(-beta * time_array)

        DeltaP1 = (self._gfm_params.MarginHigh * Ppeak / (2 * H)) * (term1 + term2 + term3 + term4)
        DeltaP1 = self._apply_delay(0.01, 0, time_array, DeltaP1)
        DeltaP = np.where(time_array < event_time, 0, DeltaP1)

        return DeltaP

    def _get_overdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:

        delta_theta = np.abs(self._gfm_params.delta_theta * np.pi / 180)
        Xgr = 1 / self._gfm_params.SCR
        Xtotal_initial = self._gfm_params.Xtr + Xeff + Xgr

        epsilon = (
            D
            / 2
            * np.sqrt(
                Xtotal_initial
                / (2 * H * self._gfm_params.Wb * self._gfm_params.Ucv * self._gfm_params.Ugr)
            )
        )
        wn = np.sqrt(
            self._gfm_params.Wb
            * self._gfm_params.Ucv
            * self._gfm_params.Ugr
            / (2 * H * Xtotal_initial)
        )
        wd = wn * np.sqrt(epsilon**2 - 1)

        alpha = epsilon * wn + wd
        beta = epsilon * wn - wd

        A = 1 / (beta - alpha)
        B = -A

        Ppeak = delta_theta * self._gfm_params.Ucv * self._gfm_params.Ugr / Xtotal_initial

        term1 = 2 * H * A * (1 - alpha * np.exp(-alpha * time_array))
        term2 = 2 * H * B * (1 - beta * np.exp(-beta * time_array))
        term3 = D * A * np.exp(-alpha * time_array)
        term4 = D * B * np.exp(-beta * time_array)

        DeltaP1 = (Ppeak / (2 * H)) * (term1 + term2 + term3 + term4)
        DeltaP = np.where(time_array < event_time, 0, DeltaP1)

        return DeltaP, Ppeak, epsilon

    def _get_underdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> np.ndarray:

        delta_theta = np.abs(self._gfm_params.delta_theta * np.pi / 180)
        Xgr = 1 / self._gfm_params.SCR
        Xtotal_initial = self._gfm_params.Xtr + Xeff + Xgr

        Ppeak = delta_theta * self._gfm_params.Ucv * self._gfm_params.Ugr / Xtotal_initial

        sigma = D / (4 * H)
        DeltaP1 = Ppeak * (1 - self._gfm_params.MarginLow) * np.exp(-sigma * time_array)
        DeltaP1 = self._apply_delay(0.01, 0, time_array, DeltaP1)
        DeltaP = np.where(time_array < event_time, 0, DeltaP1)

        return DeltaP

    def _get_underdamped_delta_p_max(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> np.ndarray:

        delta_theta = np.abs(self._gfm_params.delta_theta * np.pi / 180)
        Xgr = 1 / self._gfm_params.SCR
        Xtotal_initial = self._gfm_params.Xtr + Xeff + Xgr

        Ppeak = delta_theta * self._gfm_params.Ucv * self._gfm_params.Ugr / Xtotal_initial

        sigma = D / (4 * H)
        DeltaP1 = Ppeak * (1 + self._gfm_params.MarginHigh) * np.exp(-sigma * time_array)
        DeltaP1 = self._apply_delay(0.01, DeltaP1[0], time_array, DeltaP1)
        DeltaP = np.where(time_array < event_time, 0, DeltaP1)

        return DeltaP

    def _get_underdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:

        delta_theta = np.abs(self._gfm_params.delta_theta * np.pi / 180)
        Xgr = 1 / self._gfm_params.SCR
        Xtotal_initial = self._gfm_params.Xtr + Xeff + Xgr

        epsilon = (
            D
            / 2
            * np.sqrt(
                Xtotal_initial
                / (2 * H * self._gfm_params.Wb * self._gfm_params.Ucv * self._gfm_params.Ugr)
            )
        )
        wn = np.sqrt(
            self._gfm_params.Wb
            * self._gfm_params.Ucv
            * self._gfm_params.Ugr
            / (2 * H * Xtotal_initial)
        )
        wd = wn * np.sqrt(1 - epsilon**2)

        Ppeak = delta_theta * self._gfm_params.Ucv * self._gfm_params.Ugr / Xtotal_initial

        term1 = np.exp(-epsilon * wn * time_array)
        term2 = np.cos(wd * time_array)
        term3 = np.sin(wd * time_array)

        DeltaP1 = term1 * (term2 - (epsilon * wn - 1) / wd * term3) * Ppeak
        DeltaP = np.where(time_array < event_time, 0, DeltaP1)

        return DeltaP, Ppeak, epsilon

    def _get_final_envelopes(
        self,
        DeltaP_up_anal: np.ndarray,
        DeltaP_down_anal: np.ndarray,
        tunnel: np.ndarray,
        time_array: np.array,
        event_time: float,
    ) -> tuple[list, list]:

        DeltaP_up_anal = DeltaP_up_anal + tunnel + self._gfm_params.P0
        DeltaP_down_anal = DeltaP_down_anal - tunnel + self._gfm_params.P0

        DeltaP_up_anal = self.cut_signal(
            self._gfm_params.PMin, DeltaP_up_anal, self._gfm_params.PMax
        )
        DeltaP_down_anal = self.cut_signal(
            self._gfm_params.PMin, DeltaP_down_anal, self._gfm_params.PMax
        )

        return DeltaP_up_anal, DeltaP_down_anal

    def cut_signal(self, value_min, signal, value_max):
        Signal = np.where(signal < value_min, value_min, signal)
        Signal = np.where(signal > value_max, value_max, signal)
        return Signal

    def _get_value_at_specific_time(self, selected_time, signal, time_array):

        index = np.argmin(
            np.abs(time_array - (selected_time - 0.01))
        )  # taking the value of P 10ms before RoCofStop_Time
        # Get value from the signal
        value_at_time = signal[index]
        return value_at_time

    def _get_tunnel(self, Ppeak_array: list) -> float:
        Ppeak = Ppeak_array[self._ORIGINAL_PARAMS_IDX]
        return max(
            self._gfm_params.FinalAllowedTunnelPn,
            self._gfm_params.FinalAllowedTunnelVariation * Ppeak,
        )

    def _get_time_tunnel(
        self, Ppeak: np.ndarray, time_array: np.ndarray, event_time: float
    ) -> list:
        t = max(
            self._gfm_params.FinalAllowedTunnelPn,
            self._gfm_params.FinalAllowedTunnelVariation * Ppeak,
        )
        tunnel = t * (1 - np.exp((-time_array + 0.02) / 0.3))
        return np.where(time_array < event_time, 0, tunnel)
