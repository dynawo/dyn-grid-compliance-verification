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

DEBUG = False
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
    ],
)

BaseGFM_Values = namedtuple(
    "BaseGFM_Values",
    [
        "D_array",  # Array of damping constant (D) in pu.
        "H_array",  # Array of inertia constant (H) in pu.
        "delta_theta_array",  # Array of phase angle change (delta_theta) in radians.
        "Xgr_array",  # Array of grid reactance (Xgr) in pu.
        "Xtot_array",  # Array of total reactance (Xtot) in pu.
        "Ts_array",  # Array of system response time constant.
        "Sigma_array",  # Array of damping factor (sigma = epsilon * Wn).
        "Wn_array",  # Array of system undamped natural frequency (Wn).
        "Tunnel_array",  # Array defining the "tunnel region" or power variation limits.
        "epsilon_array",  # Array of damping coefficient (epsilon).
        "wd_array",  # Array of damped natural frequency (wd).
        "a_array",  # Array containing roots r1 of the characteristic equation.
        "b_array",  # Array containing roots r2 of the characteristic equation.
        "A_array",  # Array of coefficients C1 for the transient response.
        "B_array",  # Array of coefficients C2 for the transient response.
        "Ppeak_array",  # Array of peak power (Ppeak) reached in pu.
        "is_overdamped_global",  # Boolean indicating if the system is globally overdamped.
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
        self._base_values = None
        self._theoretical_response_from_vsm = None
        self._pdown = None
        self._pup = None

    def calculate_base_values(self, D: float, H: float, Xeff: float) -> None:
        """
        Calculate and store the base values for the GFM phase jump.

        Parameters
        ----------
        D : float
            The damping constant (pu).
        H : float
            The inertia constant (pu).
        Xeff : float
            The effective reactance (pu).
        """
        D_array, H_array, delta_theta_array = self._initialize_parameter_arrays(D, H)
        Xgr_array, Xtot_array = self._calculate_total_reactances(Xeff)

        # Determine global damping type based on epsilon_array[0]
        epsilon_initial_check = (
            D_array[self._ORIGINAL_PARAMS_IDX]
            / 2
            * np.sqrt(
                Xtot_array[self._ORIGINAL_PARAMS_IDX]
                / (
                    2
                    * H_array[self._ORIGINAL_PARAMS_IDX]
                    * self._gfm_params.Wb
                    * self._gfm_params.Ucv
                    * self._gfm_params.Ugr
                )
            )
        )
        is_overdamped_global = epsilon_initial_check >= self._EPSILON_THRESHOLD

        Ts_array, Sigma_array, Wn_array, epsilon_array, wd_array = (
            self._calculate_system_frequencies_and_damping(
                D_array, H_array, Xtot_array, is_overdamped_global
            )
        )

        a_array, b_array, A_array, B_array = self._calculate_response_amplitudes(
            epsilon_array, Sigma_array, Wn_array, wd_array, is_overdamped_global
        )

        Ppeak_array, Tunnel_array = self._calculate_peak_and_tunnel_power(
            delta_theta_array, Xtot_array
        )

        self._base_values = BaseGFM_Values(
            D_array=D_array,
            H_array=H_array,
            delta_theta_array=delta_theta_array,
            Xgr_array=Xgr_array,
            Xtot_array=Xtot_array,
            Ts_array=Ts_array,
            Sigma_array=Sigma_array,
            Wn_array=Wn_array,
            Tunnel_array=Tunnel_array,
            epsilon_array=epsilon_array,
            wd_array=wd_array,
            a_array=a_array,
            b_array=b_array,
            A_array=A_array,
            B_array=B_array,
            Ppeak_array=Ppeak_array,
            is_overdamped_global=is_overdamped_global,
        )
        if DEBUG:
            print("Valores individuales de BaseGFM_Values:")
            for field, value in self._base_values._asdict().items():
                print(f"  {field}: {value}")

    def calculate_envelopes(self, time_array: np.ndarray, event_time: float) -> None:
        """
        Calculate and store the theoretical response from VSM, power down, and
        power up arrays.

        Parameters
        ----------
        time_array : np.ndarray
            The time array for the simulation.
        event_time : float
            The time of the event in seconds.
        """
        if event_time < time_array.min() or event_time > time_array.max():
            print("Warning: event_time is outside the provided time_array range.")

        (
            theoretical_response_from_vsm_no_P0,
            active_power_multipled_by_1_plus_margin_high,
            theoretical_response_with_minimum_values,
            theoretical_response_with_maximum_values,
            active_power_multipled_by_margin_low,
        ) = self._calculate_initial_responses(time_array)

        if DEBUG:
            # Debugging prints for initial responses
            print("\nDebugging prints for calculate_envelopes:")
            print(f"  theoretical_response_from_vsm_no_P0: {theoretical_response_from_vsm_no_P0}")
            print(
                f"  active_power_multipled_by_1_plus_margin_high: "
                f"{active_power_multipled_by_1_plus_margin_high}"
            )
            print(
                f"  theoretical_response_with_minimum_values: "
                f"{theoretical_response_with_minimum_values}"
            )
            print(
                f"  theoretical_response_with_maximum_values: "
                f"{theoretical_response_with_maximum_values}"
            )
            print(
                f"  active_power_multipled_by_margin_low: "
                f"{active_power_multipled_by_margin_low}"
            )

        tunnel = self._calculate_tunnel(time_array)

        list_of_arrays = [
            theoretical_response_from_vsm_no_P0,
            active_power_multipled_by_1_plus_margin_high,
            theoretical_response_with_minimum_values,
            theoretical_response_with_maximum_values,
            active_power_multipled_by_margin_low,
        ]

        pdown_no_P0, pup_no_P0 = self._calculate_unlimited_power_envelopes(list_of_arrays, tunnel)
        pdown_limited, pup_limited = self._limit_power_envelopes(pdown_no_P0, pup_no_P0)

        delta_theta_sign = 1 if self._gfm_params.delta_theta > 0 else -1
        self._theoretical_response_from_vsm = np.where(
            time_array < event_time,
            self._gfm_params.P0,
            theoretical_response_from_vsm_no_P0 * -1 * delta_theta_sign + self._gfm_params.P0,
        )

        pdown_final, pup_final = self._apply_emt_delay_if_needed(
            pdown_limited, pup_limited, time_array
        )

        self._pdown = np.where(time_array < event_time, self._gfm_params.P0, pdown_final)
        self._pup = np.where(time_array < event_time, self._gfm_params.P0, pup_final)

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
            self._theoretical_response_from_vsm,
            label="Theoretical response from VSM",
            linewidth="3",
        )
        plt.plot(time, self._pdown, label="Pdown", linewidth=2)
        plt.plot(time, self._pup, label="Pup", linewidth=2)
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

    def get_base_values(self) -> BaseGFM_Values:
        """
        Returns the BaseGFM_Values namedtuple containing base calculation results.

        Returns
        -------
        BaseGFM_Values
            The namedtuple containing base calculation results.
        """
        return self._base_values

    def get_theoretical_response_from_vsm(self) -> np.ndarray:
        """
        Returns the theoretical response from VSM array.

        Returns
        -------
        np.ndarray
            The theoretical response from VSM array.
        """
        return self._theoretical_response_from_vsm

    def get_pdown(self) -> np.ndarray:
        """
        Returns the power down array.

        Returns
        -------
        np.ndarray
            The power down array.
        """
        return self._pdown

    def get_pup(self) -> np.ndarray:
        """
        Returns the power up array.

        Returns
        -------
        np.ndarray
            The power up array.
        """
        return self._pup

    def _initialize_parameter_arrays(
        self, D: float, H: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Initializes D, H, and delta_theta arrays based on input parameters.

        Parameters
        ----------
        D : float
            The damping constant (pu).
        H : float
            The inertia constant (pu).

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            D_array, H_array, delta_theta_array.
        """
        D_array = np.array([D, D * self._gfm_params.RatioMin, D * self._gfm_params.RatioMax])
        H_array = np.array([H, H / self._gfm_params.RatioMin, H / self._gfm_params.RatioMax])
        delta_theta_array = np.full(3, np.abs(self._gfm_params.delta_theta * np.pi / 180))
        return D_array, H_array, delta_theta_array

    def _calculate_total_reactances(self, Xeff: float) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculates grid and total reactances.

        Parameters
        ----------
        Xeff : float
            The effective reactance (pu).

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            Xgr_array, Xtot_array.
        """
        Xgr_array = np.full(3, 1 / self._gfm_params.SCR)
        Xtot_array = self._gfm_params.Xtr + Xeff + Xgr_array
        return Xgr_array, Xtot_array

    def _calculate_system_frequencies_and_damping(
        self,
        D_array: np.ndarray,
        H_array: np.ndarray,
        Xtot_array: np.ndarray,
        is_overdamped_global: bool,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates time constants, damping ratios, natural frequencies, and
        damped frequencies. The calculation of damped frequency (wd_array)
        now depends on the global damping type.

        Parameters
        ----------
        D_array : np.ndarray
            Damping constant array.
        H_array : np.ndarray
            Inertia constant array.
        Xtot_array : np.ndarray
            Total reactance array.
        is_overdamped_global : bool
            Flag indicating if the system is globally considered overdamped.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]
            Ts_array, Sigma_array, Wn_array, epsilon_array, wd_array.
        """
        Ts_array = (
            D_array
            * Xtot_array
            / (self._gfm_params.Wb * self._gfm_params.Ucv * self._gfm_params.Ugr)
        )

        Wn_array = np.sqrt(
            self._gfm_params.Wb
            * self._gfm_params.Ucv
            * self._gfm_params.Ugr
            / (2 * H_array * Xtot_array)
        )

        epsilon_array = (
            D_array
            / 2
            * np.sqrt(
                Xtot_array
                / (2 * H_array * self._gfm_params.Wb * self._gfm_params.Ucv * self._gfm_params.Ugr)
            )
        )

        # Calculate wd_array based on the global damping type
        if is_overdamped_global:
            # Overdamped or critically damped: wd = Wn * sqrt(epsilon^2 - 1)
            wd_array = Wn_array * np.sqrt(np.square(epsilon_array) - 1)
        else:
            # Underdamped: wd = Wn * sqrt(1 - epsilon^2)
            wd_array = Wn_array * np.sqrt(1 - np.square(epsilon_array))

        Sigma_array = epsilon_array * Wn_array

        return (
            Ts_array,
            Sigma_array,
            Wn_array,
            epsilon_array,
            wd_array,
        )

    def _calculate_response_amplitudes(
        self,
        epsilon_array: np.ndarray,
        Sigma_array: np.ndarray,
        Wn_array: np.ndarray,
        wd_array: np.ndarray,
        is_overdamped_global: bool,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the roots (a, b) and their corresponding coefficients (A, B)
        for the theoretical response equation. These are determined uniformly
        based on the global damping type.

        Parameters
        ----------
        epsilon_array : np.ndarray
            Damping ratio array.
        Sigma_array : np.ndarray
            Damping factor (epsilon * Wn) array.
        Wn_array : np.ndarray
            Natural frequency array.
        wd_array : np.ndarray
            Damped natural frequency array (calculated based on global damping type).
        is_overdamped_global : bool
            Flag indicating if the system is globally considered overdamped.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
            a_array (roots r1), b_array (roots r2), A_array (coefficients C1),
            B_array (coefficients C2).
        """
        a_array = np.zeros_like(epsilon_array, dtype=complex)
        b_array = np.zeros_like(epsilon_array, dtype=complex)
        A_array = np.zeros_like(epsilon_array, dtype=complex)
        B_array = np.zeros_like(epsilon_array, dtype=complex)

        for i in range(len(epsilon_array)):
            sigma = Sigma_array[i]
            wd = wd_array[i]  # This wd is already correct for the global damping type

            if is_overdamped_global:
                # Roots are real and distinct (or equal for critically damped)
                r1 = -sigma + wd
                r2 = -sigma - wd

                a_array[i] = r1
                b_array[i] = r2

                # Coefficients for overdamped case based on original logic's
                # structure for positive 'a' and 'b' (which were sigma +/- wd).
                # Here, we map these `a_orig_positive` and `b_orig_positive` to
                # the calculation of A and B. Assuming A, B are still derived from
                # 1/(b-a) and -1/(b-a), but using the positive form of the exponents.
                # This is the most consistent way to generalize the original formula
                # for A, B.
                positive_exp_term_val1 = sigma + wd
                positive_exp_term_val2 = sigma - wd

                denominator = positive_exp_term_val2 - positive_exp_term_val1
                A_array[i] = 1 / denominator if denominator != 0 else np.inf
                B_array[i] = -1 * A_array[i]

            else:  # Underdamped
                # Roots are complex conjugates
                r1 = -sigma + 1j * wd
                r2 = -sigma - 1j * wd

                a_array[i] = r1
                b_array[i] = r2

                # Coefficients for underdamped case, calculated from complex roots
                denominator = r2 - r1  # This will be -2j*wd
                if abs(denominator) < 1e-9:  # Check for near zero denominator
                    A_array[i] = complex(np.inf, 0)
                    B_array[i] = complex(-np.inf, 0)
                else:
                    A_array[i] = 1 / denominator
                    B_array[i] = -1 * A_array[i]

        return a_array, b_array, A_array, B_array

    def _calculate_peak_and_tunnel_power(
        self, delta_theta_array: np.ndarray, Xtot_array: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculates peak power and tunnel arrays.

        Parameters
        ----------
        delta_theta_array : np.ndarray
            Delta theta array.
        Xtot_array : np.ndarray
            Total reactance array.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            Ppeak_array, Tunnel_array.
        """
        Ppeak_array = delta_theta_array * self._gfm_params.Ucv * self._gfm_params.Ugr / Xtot_array
        Tunnel_array = np.maximum(
            self._gfm_params.FinalAllowedTunnelVariation * Ppeak_array,
            self._gfm_params.FinalAllowedTunnelPn,
        )
        return Ppeak_array, Tunnel_array

    def _calculate_initial_responses(
        self, time_array: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates various initial theoretical responses and power values.

        Parameters
        ----------
        time_array : np.ndarray
            The time array for the simulation.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - theoretical_response_from_vsm_no_P0
            - active_power_multipled_by_1_plus_margin_high
            - theoretical_response_with_minimum_values
            - theoretical_response_with_maximum_values
            - active_power_multipled_by_margin_low
        """
        theoretical_response_from_vsm_no_P0 = self._calculate_theoretical_response_no_p0(
            time_array, self._ORIGINAL_PARAMS_IDX
        )
        active_power_multipled_by_1_plus_margin_high = (
            self._calculate_shifted_response_margin_high(
                time_array, theoretical_response_from_vsm_no_P0, self._ORIGINAL_PARAMS_IDX
            )
        )
        theoretical_response_with_minimum_values = self._calculate_theoretical_response_no_p0(
            time_array, self._MINIMUM_PARAMS_IDX
        )
        theoretical_response_with_maximum_values = self._calculate_theoretical_response_no_p0(
            time_array, self._MAXIMUM_PARAMS_IDX
        )
        active_power_multipled_by_margin_low = self._calculate_shifted_response_margin_low(
            time_array, theoretical_response_from_vsm_no_P0, self._ORIGINAL_PARAMS_IDX
        )

        return (
            theoretical_response_from_vsm_no_P0,
            active_power_multipled_by_1_plus_margin_high,
            theoretical_response_with_minimum_values,
            theoretical_response_with_maximum_values,
            active_power_multipled_by_margin_low,
        )

    def _calculate_tunnel(self, time_array: np.ndarray) -> np.ndarray:
        """
        Calculates the tunnel response.

        Parameters
        ----------
        time_array : np.ndarray
            The time array for the simulation.

        Returns
        -------
        np.ndarray
            The tunnel response.
        """
        return self._base_values.Tunnel_array[self._ORIGINAL_PARAMS_IDX] * (
            1 - np.exp((-1 * time_array + 0.02) / 0.3)
        )

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
        # Ensure elements in list_of_arrays are real before reduction, if they
        # became complex
        list_of_real_arrays = [arr.real for arr in list_of_arrays]

        pdown_no_P0 = np.minimum.reduce(list_of_real_arrays) - tunnel
        pup_no_P0 = np.maximum.reduce(list_of_real_arrays) + tunnel
        return pdown_no_P0, pup_no_P0

    def _limit_power_envelopes(
        self, pdown_no_P0: np.ndarray, pup_no_P0: np.ndarray
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
        tunnel_original = self._base_values.Tunnel_array[self._ORIGINAL_PARAMS_IDX]

        pdown_limited = np.minimum(
            np.maximum(
                self._gfm_params.P0 - delta_theta_sign * pdown_no_P0,
                -1 + tunnel_original,
            ),
            1 - tunnel_original,
        )
        pup_limited = np.minimum(
            np.maximum(
                self._gfm_params.P0 - 1 * delta_theta_sign * pup_no_P0,
                -1 * self._gfm_params.PMax,
            ),
            self._gfm_params.PMax,
        )
        return pdown_limited, pup_limited

    def _apply_emt_delay_if_needed(
        self, pdown_limited: np.ndarray, pup_limited: np.ndarray, time_array: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Applies EMT delay to power envelopes if the EMT flag is true.

        Parameters
        ----------
        pdown_limited : np.ndarray
            Limited power down array.
        pup_limited : np.ndarray
            Limited power up array.
        time_array : np.ndarray
            The time array.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing the potentially delayed power down and power up arrays.
        """
        if self._gfm_params.EMT:
            pdown_limited = self._apply_delay(
                delay=0.02,
                delayed_value=pdown_limited[0],
                time_array=time_array,
                signal=pdown_limited,
            )
            pup_limited = self._apply_delay(
                delay=0.02,
                delayed_value=pup_limited[0],
                time_array=time_array,
                signal=pup_limited,
            )
        return pdown_limited, pup_limited

    def _calculate_shifted_response_margin_high(
        self, time_array: np.ndarray, theoretical_response_from_vsm_no_P0: np.ndarray, index: int
    ) -> np.ndarray:
        if self._base_values.is_overdamped_global:
            return (1 + self._gfm_params.MarginHigh) * theoretical_response_from_vsm_no_P0
        else:
            Ppeak = self._base_values.Ppeak_array[index]
            Sigma = self._base_values.Sigma_array[index]

            response_margin_high = (
                Ppeak * (1 + self._gfm_params.MarginHigh) * np.exp(-1 * Sigma * time_array)
            )
            return self._apply_delay(
                delay=0.01,
                delayed_value=response_margin_high[0],
                time_array=time_array,
                signal=response_margin_high,
            )

    def _calculate_shifted_response_margin_low(
        self, time_array: np.ndarray, theoretical_response_from_vsm_no_P0: np.ndarray, index: int
    ) -> np.ndarray:
        if self._base_values.is_overdamped_global:
            shifted_theoretical_response_from_vsm_no_P0 = self._apply_delay(
                delay=0.01,
                delayed_value=0.0,
                time_array=time_array,
                signal=theoretical_response_from_vsm_no_P0,
            )

            return self._gfm_params.MarginLow * shifted_theoretical_response_from_vsm_no_P0
        else:
            Ppeak = self._base_values.Ppeak_array[index]
            Sigma = self._base_values.Sigma_array[index]

            return self._apply_delay(
                delay=0.01,
                delayed_value=0.0,
                time_array=time_array,
                signal=Ppeak * (1 - self._gfm_params.MarginLow) * np.exp(-1 * Sigma * time_array),
            )

    def _calculate_theoretical_response_no_p0(
        self, time_array: np.ndarray, index: int
    ) -> np.ndarray:
        """
        Calculates the theoretical response from VSM without initial power (P0)
        for a given index. This function uses the pre-determined global damping
        type for all calculations.

        Parameters
        ----------
        time_array : np.ndarray
            The time array for the simulation.
        index : int
            The index referring to the specific set of base values
            (original, min, or max).

        Returns
        -------
        np.ndarray
            The real part of the theoretical response from VSM without P0.
        """
        Ppeak = self._base_values.Ppeak_array[index]
        H = self._base_values.H_array[index]
        D = self._base_values.D_array[index]

        # Coefficients (C1, C2) from base values
        C1 = self._base_values.A_array[index]
        C2 = self._base_values.B_array[index]

        # Get global damping type
        is_overdamped_global = self._base_values.is_overdamped_global

        if is_overdamped_global:
            # Overdamped or critically damped: all calculations use real
            # exponentials. The original formula used `a` and `b` as positive
            # values (sigma +/- wd_overdamped). These were effectively `-r1`
            # and `-r2` for the purposes of the original formula structure.

            # Using the sigma and wd_array (which is wd_overdamped_array here)
            # for clarity with original terms:
            sigma_val = self._base_values.Sigma_array[index]
            wd_val = self._base_values.wd_array[index]

            # The parameters 'a' and 'b' in the original formula's terms
            # (1 - a*exp(-a*t)) are equivalent to (sigma + wd) and
            # (sigma - wd) for overdamped.
            formula_a = sigma_val + wd_val
            formula_b = sigma_val - wd_val

            term1 = 2 * H * C1.real * (1 - formula_a * np.exp(-formula_a * time_array))
            term2 = 2 * H * C2.real * (1 - formula_b * np.exp(-formula_b * time_array))
            term3 = D * C1.real * np.exp(-formula_a * time_array)
            term4 = D * C2.real * np.exp(-formula_b * time_array)

            response = (Ppeak / (2 * H)) * (term1 + term2 + term3 + term4)

        else:  # Underdamped

            epsilon_val = self._base_values.epsilon_array[index]
            wd_val = self._base_values.wd_array[index]
            wn_val = self._base_values.Wn_array[index]

            formula_sin = np.sin(wd_val * time_array)

            term1 = np.exp(-1 * epsilon_val * wn_val * time_array)
            term2 = np.cos(wd_val * time_array) - (epsilon_val * wn_val - 1) / wd_val * formula_sin

            response = term1 * term2 * Ppeak

        return response.real

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
