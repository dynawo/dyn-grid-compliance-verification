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

# Debug flag, typically used to enable/disable debug-specific features.
DEBUG = True
# Named tuple to store Grid Forming (GFM) parameters. This structure
# provides immutable and descriptive access to configuration values.
GFM_Params = namedtuple(
    "GFM_Params",
    [
        "EMT",  # Electro-Magnetic Transients simulation flag
        "RatioMin",  # Minimum ratio for parameter variations
        "RatioMax",  # Maximum ratio for parameter variations
        "P0",  # Initial active power (per unit - pu)
        "delta_theta",  # Phase angle jump magnitude (degrees)
        "SCR",  # Short Circuit Ratio, indicating grid strength
        "Xtr",  # Transformer reactance (pu)
        "Wb",  # Base angular frequency (radians/second)
        "Ucv",  # Converter RMS voltage (pu)
        "Ugr",  # Grid RMS voltage (pu)
        "MarginHigh",  # Upper margin for power envelopes
        "MarginLow",  # Lower margin for power envelopes
        "FinalAllowedTunnelVariation",  # Parameter for tunnel function
        "FinalAllowedTunnelPn",  # Parameter for tunnel function
        "PMax",  # Maximum allowed active power (pu)
        "PMin",  # Minimum allowed active power (pu)
    ],
)


class PhaseJump:
    """
    Class to calculate the GFM phase jump response and generate related
    plots and CSVs for analysis.
    """

    # Constants for indexing parameter arrays: original, minimum, and maximum values.
    _ORIGINAL_PARAMS_IDX = 0
    _MINIMUM_PARAMS_IDX = 1
    _MAXIMUM_PARAMS_IDX = 2
    # Threshold to differentiate between overdamped and underdamped systems.
    # Critically damped systems are grouped with overdamped.
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
        # Attributes to store calculated results for later saving and plotting.
        # These are initialized to None and populated after calculations in
        # get_envelopes().
        self._theoretical_response_from_vsm = None
        self._pdown = None
        self._pup = None

    def get_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> tuple[bool, list, list, list]:
        """
        Calculates the change in power (DeltaP) based on damping characteristics.

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
            The time (in seconds) at which the phase jump event occurs.

        Returns
        -------
        tuple[bool, list, list, list]
            A tuple containing:
            - is_overdamped: True if the initial system is overdamped, False otherwise.
            - DeltaP_array: List of DeltaP arrays for original, min, and max parameters.
            - DeltaP_min: DeltaP array calculated with minimum parameters.
            - DeltaP_max: DeltaP array calculated with maximum parameters.
            - Ppeak_array: List of Ppeak values for original, min, and max parameters.
            - epsilon_array: List of epsilon values for original, min, and max parameters.
        """
        Xgr = 1 / self._gfm_params.SCR  # Grid reactance derived from SCR
        Xtotal_initial = self._gfm_params.Xtr + Xeff + Xgr  # Total initial reactance
        # Calculate initial epsilon to determine damping type (overdamped/underdamped).
        epsilon_initial_check = self._calculate_epsilon_initial_check(D, H, Xtotal_initial)

        # Prepare arrays for D and H parameters, including min and max variations.
        D_array = np.array([D, D * self._gfm_params.RatioMin, D * self._gfm_params.RatioMax])
        H_array = np.array([H, H / self._gfm_params.RatioMin, H / self._gfm_params.RatioMax])

        DeltaP_array = []
        Ppeak_array = []
        epsilon_array = []

        # Loop through parameter variations to calculate DeltaP, Ppeak, and epsilon.
        for i in range(len(D_array)):
            DeltaP, Ppeak, epsilon = self._calculate_delta_p_for_damping(
                D_array[i], H_array[i], Xeff, time_array, event_time, epsilon_initial_check
            )
            DeltaP_array.append(DeltaP)
            Ppeak_array.append(Ppeak)
            epsilon_array.append(epsilon)

        # Calculate specific DeltaP for min and max parameter cases using the
        # appropriate damping model (overdamped or underdamped).
        if epsilon_initial_check > self._EPSILON_THRESHOLD:
            DeltaP_min = self._get_overdamped_delta_p_min(D, H, Xeff, time_array, event_time)
            DeltaP_max = self._get_overdamped_delta_p_max(D, H, Xeff, time_array, event_time)
        else:
            DeltaP_min = self._get_underdamped_delta_p_min(D, H, Xeff, time_array, event_time)
            DeltaP_max = self._get_underdamped_delta_p_max(D, H, Xeff, time_array, event_time)

        # Return all calculated DeltaP arrays, Ppeak, and damping information.
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
        """
        Calculates and limits the power envelopes (P_pcc, P_up_final, P_down_final).

        Parameters
        ----------
        DeltaP_array : list
            List of DeltaP arrays for original, min, and max parameters.
        DeltaP_min : np.ndarray
            DeltaP array calculated with minimum parameters.
        DeltaP_max : np.ndarray
            DeltaP array calculated with maximum parameters.
        Ppeak_array : list
            List of Ppeak values for original, min, and max parameters.
        time_array : np.array
            Array of time points.
        event_time : float
            The time at which the event occurs.

        Returns
        -------
        tuple[np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - P_pcc_final: The final calculated power at the point of common coupling.
            - P_up_final: The final upper power envelope.
            - P_down_final: The final lower power envelope.
        """
        # Extract the original DeltaP and Ppeak values.
        DeltaP = DeltaP_array[self._ORIGINAL_PARAMS_IDX]
        Ppeak = Ppeak_array[self._ORIGINAL_PARAMS_IDX]

        # Calculate the time-dependent tunnel effect.
        tunnel_time_dep = self._get_time_tunnel(
            Ppeak=Ppeak, time_array=time_array, event_time=event_time
        )

        # Calculate the theoretical power at PCC and limit it by PMin/PMax.
        P_pcc = self.cut_signal(
            self._gfm_params.PMin, self._gfm_params.P0 + DeltaP, self._gfm_params.PMax
        )

        # Combine all DeltaP arrays for envelope calculations.
        list_of_arrays = DeltaP_array + [DeltaP_min, DeltaP_max]

        # Calculate initial unlimited power envelopes.
        pdown_no_P0, pup_no_P0 = self._calculate_unlimited_power_envelopes(
            list_of_arrays, tunnel_time_dep
        )
        # Apply final limits to the power envelopes using the static tunnel value.
        pdown_limited, pup_limited = self._limit_power_envelopes(
            pdown_no_P0, pup_no_P0, self._get_tunnel(Ppeak_array)
        )

        # Apply a delay if EMT simulation flag is true.
        if self._gfm_params.EMT:
            P_up_final = self._apply_delay(0.02, pup_limited[0], time_array, pup_limited)
            P_down_final = self._apply_delay(0.02, pdown_limited[0], time_array, pdown_limited)
            P_pcc_final = self._apply_delay(0.02, P_pcc[0], time_array, P_pcc)
        else:
            P_up_final = pup_limited
            P_down_final = pdown_limited
            P_pcc_final = P_pcc

        # Store the final results as instance attributes for later use in
        # saving and plotting methods.
        self._theoretical_response_from_vsm = P_pcc_final
        self._pdown = P_down_final
        self._pup = P_up_final

        # Return the final calculated power signals.
        return P_pcc_final, P_up_final, P_down_final

    def save_results_to_csv(
        self,
        path: Path,
        time_array: np.ndarray,
    ) -> None:
        """
        Save the calculated results (P_PCC, P_down, P_up) to a CSV file.

        Parameters
        ----------
        path : Path
            The file path where the CSV file will be saved.
        time_array : np.ndarray
            The time array corresponding to the power signals.
        """
        df = pd.DataFrame(
            {
                "Time (s)": time_array,
                "P_PCC (pu)": self._theoretical_response_from_vsm,
                "P_down (pu)": self._pdown,
                "P_up (pu)": self._pup,
            }
        )
        # Save the DataFrame to a CSV file without including the index.
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
        Plot the results of the GFM phase jump: theoretical response,
        upper envelope, and lower envelope.

        Parameters
        ----------
        path : Path
            The file path where the plot image will be saved.
        time : np.ndarray
            The time array for the x-axis.
        event_time : float
            The time (in seconds) when the phase jump event occurred.
        shift_time : float
            A time shift (in milliseconds) to adjust the event time marker
            for plotting purposes.
        title : str
            The title of the plot, which will also be used as the filename.
        """
        plt.figure(figsize=(8, 5))  # Create a new figure with a specified size.
        # Plot the theoretical power response.
        plt.plot(
            time,
            self._theoretical_response_from_vsm,
            label="Theoretical response from VSM",
            linewidth="3",
        )
        # Plot the lower power envelope.
        plt.plot(time, self._pdown, label="Pdown", linewidth=2)
        # Plot the upper power envelope.
        plt.plot(time, self._pup, label="Pup", linewidth=2)
        plt.xlabel("sec")  # Set x-axis label.
        plt.ylabel("P at PCC (pu)")  # Set y-axis label.
        plt.title(title)  # Set the plot title.
        # Add a vertical line to mark the event time.
        plt.axvline(
            x=event_time + shift_time / 1000,  # Convert ms to seconds
            color="black",
            linestyle="--",
            label="t at Event Time",
        )
        plt.legend(loc="lower right")  # Display legend.
        plt.grid(True)  # Show grid.
        plt.savefig(path, bbox_inches="tight", dpi=300)  # Save the figure.
        plt.close()  # Close the figure to free up memory.

    def _calculate_unlimited_power_envelopes(
        self, list_of_arrays: list[np.ndarray], tunnel: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculates the unlimited power down and power up envelopes by
        finding the minimum and maximum across various DeltaP arrays
        and adjusting by the time-dependent tunnel.

        Parameters
        ----------
        list_of_arrays : list[np.ndarray]
            A list of DeltaP arrays to be used for min/max reduction.
        tunnel : np.ndarray
            The time-dependent tunnel response array.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing:
            - pdown_no_P0: Unlimited power down without initial power (P0).
            - pup_no_P0: Unlimited power up without initial power (P0).
        """
        # Calculate the lower envelope by taking the minimum of all DeltaP arrays
        # and subtracting the tunnel.
        pdown_no_P0 = np.minimum.reduce(list_of_arrays) - tunnel
        # Calculate the upper envelope by taking the maximum of all DeltaP arrays
        # and adding the tunnel.
        pup_no_P0 = np.maximum.reduce(list_of_arrays) + tunnel
        return pdown_no_P0, pup_no_P0

    def _limit_power_envelopes(
        self,
        pdown_no_P0: np.ndarray,
        pup_no_P0: np.ndarray,
        tunnel_value: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Applies final operational limits to the power down and power up
        envelopes, incorporating the initial power (P0) and a constant
        tunnel value.

        Parameters
        ----------
        pdown_no_P0 : np.ndarray
            Unlimited power down signal, not yet adjusted by P0.
        pup_no_P0 : np.ndarray
            Unlimited power up signal, not yet adjusted by P0.
        tunnel_value : float
            The constant tunnel value used for final limiting.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing:
            - pdown_limited: Limited power down envelope.
            - pup_limited: Limited power up envelope.
        """
        # Determine the sign of delta_theta for directional limiting.
        delta_theta_sign = 1 if self._gfm_params.delta_theta > 0 else -1

        # Limit the lower envelope:
        # 1. Adjust by P0 and delta_theta_sign.
        # 2. Ensure it stays within [-1 + tunnel_value, 1 - tunnel_value].
        pdown_limited = np.minimum(
            np.maximum(
                self._gfm_params.P0 - delta_theta_sign * pdown_no_P0,
                -1 + tunnel_value,
            ),
            1 - tunnel_value,
        )
        # Limit the upper envelope:
        # 1. Adjust by P0 and delta_theta_sign.
        # 2. Ensure it stays within [-PMax, PMax].
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
        Applies a time delay to a given signal by prepending a constant
        `delayed_value` for the duration of the `delay`.

        Parameters
        ----------
        delay : float
            The delay time in seconds.
        delayed_value : float
            The constant value to fill the signal during the delay period.
        time_array : np.ndarray
            The time array corresponding to the signal.
        signal : np.ndarray
            The original signal to be delayed.

        Returns
        -------
        np.ndarray
            The delayed signal, truncated to the original signal length.
        """
        if len(time_array) < 2:
            return signal  # Cannot calculate sampling frequency if only one or no point.
        fs = time_array[1] - time_array[0]  # Assume constant time step (sampling freq).

        # Calculate the number of samples corresponding to the delay.
        delay_samples = int(round(delay / fs))

        if delay_samples >= len(time_array):
            # If delay is greater than or equal to signal length,
            # the entire signal becomes the delayed value.
            return np.full_like(signal, delayed_value)

        # Create an array of `delayed_value` for the delay duration.
        sample = np.full(delay_samples, delayed_value)
        # Concatenate the delay samples with the original signal and
        # truncate to the original length.
        return np.concatenate((sample, signal))[: len(time_array)]

    def _calculate_common_params(self, D: float, H: float, Xeff: float) -> tuple:
        """
        Calculates common parameters required for DeltaP calculations,
        such as total initial reactance, damping ratio (epsilon),
        natural frequency (wn), and peak power (Ppeak).

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xeff : float
            Effective reactance.

        Returns
        -------
        tuple
            A tuple containing:
            - Xtotal_initial: Total initial reactance.
            - epsilon: Damping ratio.
            - wn: Natural frequency.
            - Ppeak_calc: Calculated peak power.
        """
        Xgr = 1 / self._gfm_params.SCR  # Grid reactance.
        Xtotal_initial = self._gfm_params.Xtr + Xeff + Xgr  # Sum of reactances.
        Uprod = self._gfm_params.Ucv * self._gfm_params.Ugr  # Product of voltages.

        # Calculate damping ratio (epsilon).
        epsilon = D / 2 * np.sqrt(Xtotal_initial / (2 * H * self._gfm_params.Wb * Uprod))
        # Calculate natural frequency (wn).
        wn = np.sqrt(self._gfm_params.Wb * Uprod / (2 * H * Xtotal_initial))

        # Convert delta_theta to radians and calculate peak power.
        delta_theta_rad = np.abs(self._gfm_params.delta_theta * np.pi / 180)
        Ppeak_calc = delta_theta_rad * Uprod / Xtotal_initial

        return Xtotal_initial, epsilon, wn, Ppeak_calc

    def _get_overdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.array
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the base DeltaP waveform and related parameters for
        an overdamped system, before applying event time or margins.

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
        tuple[np.ndarray, float, float]
            A tuple containing:
            - DeltaP1: The base DeltaP waveform.
            - Ppeak: The peak power.
            - epsilon: The damping ratio.
        """
        Xtotal_initial, epsilon, wn, Ppeak = self._calculate_common_params(D, H, Xeff)
        wd = wn * np.sqrt(epsilon**2 - 1)  # Damped natural frequency for overdamped.

        alpha = epsilon * wn + wd  # Root 1
        beta = epsilon * wn - wd  # Root 2

        A = 1 / (beta - alpha)  # Coefficient A
        B = -A  # Coefficient B

        # Calculate individual terms for DeltaP1 based on overdamped response.
        term1 = 2 * H * A * (1 - alpha * np.exp(-alpha * time_array))
        term2 = 2 * H * B * (1 - beta * np.exp(-beta * time_array))
        term3 = D * A * np.exp(-alpha * time_array)
        term4 = D * B * np.exp(-beta * time_array)

        # Combine terms to get the base DeltaP1.
        DeltaP1 = (Ppeak / (2 * H)) * (term1 + term2 + term3 + term4)
        return DeltaP1, Ppeak, epsilon

    def _get_overdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> np.ndarray:
        """
        Calculates the minimum DeltaP for an overdamped system, applying
        the lower margin and setting pre-event values to zero.

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
            The minimum DeltaP array for the overdamped system.
        """
        # Get the base DeltaP waveform.
        DeltaP1, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        # Apply the lower margin.
        DeltaP1_margined = (1 + self._gfm_params.MarginLow) * DeltaP1
        # Set DeltaP to 0 before the event time.
        DeltaP = np.where(time_array < event_time, 0, DeltaP1_margined)
        return DeltaP

    def _get_overdamped_delta_p_max(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> np.ndarray:
        """
        Calculates the maximum DeltaP for an overdamped system, applying
        the upper margin, an additional delay, and setting pre-event
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
            The maximum DeltaP array for the overdamped system.
        """
        # Get the base DeltaP waveform.
        DeltaP1, _, _ = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        # Apply the upper margin.
        DeltaP1_margined = self._gfm_params.MarginHigh * DeltaP1
        # Apply a small delay to the margined DeltaP.
        DeltaP1_delayed = self._apply_delay(0.01, 0, time_array, DeltaP1_margined)
        # Set DeltaP to 0 before the event time.
        DeltaP = np.where(time_array < event_time, 0, DeltaP1_delayed)
        return DeltaP

    def _get_overdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates DeltaP, Ppeak, and epsilon for an overdamped system,
        setting pre-event values to zero.

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
        tuple[np.ndarray, float, float]
            A tuple containing:
            - DeltaP: The DeltaP array for the overdamped system.
            - Ppeak: The peak power.
            - epsilon: The damping ratio.
        """
        # Get the base DeltaP waveform, Ppeak, and epsilon.
        DeltaP1, Ppeak, epsilon = self._get_overdamped_delta_p_base(D, H, Xeff, time_array)
        # Set DeltaP to 0 before the event time.
        DeltaP = np.where(time_array < event_time, 0, DeltaP1)
        return DeltaP, Ppeak, epsilon

    def _get_underdamped_delta_p_base(
        self, D: float, H: float, Xeff: float, time_array: np.array
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates the base DeltaP waveform and related parameters for
        an underdamped system, before applying event time or margins.

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
        tuple[np.ndarray, float, float]
            A tuple containing:
            - DeltaP1: The base DeltaP waveform.
            - Ppeak: The peak power.
            - epsilon: The damping ratio.
        """
        Xtotal_initial, epsilon, wn, Ppeak = self._calculate_common_params(D, H, Xeff)
        wd = wn * np.sqrt(1 - epsilon**2)  # Damped natural frequency for underdamped.

        # Calculate individual terms for DeltaP1 based on underdamped response.
        term1 = np.exp(-epsilon * wn * time_array)
        term2 = np.cos(wd * time_array)
        term3 = np.sin(wd * time_array)

        # Combine terms to get the base DeltaP1.
        DeltaP1 = term1 * (term2 - (epsilon * wn - 1) / wd * term3) * Ppeak
        return DeltaP1, Ppeak, epsilon

    def _get_underdamped_delta_p_min(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> np.ndarray:
        """
        Calculates the minimum DeltaP for an underdamped system, applying
        the lower margin and setting pre-event values to zero.
        Note: This specific implementation uses a simplified exponential decay
        formula for min/max envelopes consistent with the original script's logic.

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
            The minimum DeltaP array for the underdamped system.
        """
        Xgr = 1 / self._gfm_params.SCR
        Xtotal_initial = self._gfm_params.Xtr + Xeff + Xgr
        # Recalculate Ppeak as the base was not used in original logic for min/max
        Ppeak_val = (
            np.abs(self._gfm_params.delta_theta * np.pi / 180)
            * self._gfm_params.Ucv
            * self._gfm_params.Ugr
            / Xtotal_initial
        )
        sigma = D / (4 * H)  # Decay rate.
        # Apply lower margin and exponential decay.
        DeltaP1 = Ppeak_val * (1 - self._gfm_params.MarginLow) * np.exp(-sigma * time_array)
        # Apply a small delay.
        DeltaP1_delayed = self._apply_delay(0.01, 0, time_array, DeltaP1)
        # Set DeltaP to 0 before the event time.
        DeltaP = np.where(time_array < event_time, 0, DeltaP1_delayed)
        return DeltaP

    def _get_underdamped_delta_p_max(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> np.ndarray:
        """
        Calculates the maximum DeltaP for an underdamped system, applying
        the upper margin and setting pre-event values to zero.
        Note: This specific implementation uses a simplified exponential decay
        formula for min/max envelopes consistent with the original script's logic.

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
            The maximum DeltaP array for the underdamped system.
        """
        Xgr = 1 / self._gfm_params.SCR
        Xtotal_initial = self._gfm_params.Xtr + Xeff + Xgr
        # Recalculate Ppeak as the base was not used in original logic for min/max
        Ppeak_val = (
            np.abs(self._gfm_params.delta_theta * np.pi / 180)
            * self._gfm_params.Ucv
            * self._gfm_params.Ugr
            / Xtotal_initial
        )
        sigma = D / (4 * H)  # Decay rate.
        # Apply upper margin and exponential decay.
        DeltaP1 = Ppeak_val * (1 + self._gfm_params.MarginHigh) * np.exp(-sigma * time_array)
        # Apply a small delay.
        DeltaP1_delayed = self._apply_delay(0.01, DeltaP1[0], time_array, DeltaP1)
        # Set DeltaP to 0 before the event time.
        DeltaP = np.where(time_array < event_time, 0, DeltaP1_delayed)
        return DeltaP

    def _get_underdamped_delta_p(
        self, D: float, H: float, Xeff: float, time_array: np.array, event_time: float
    ) -> tuple[np.ndarray, float, float]:
        """
        Calculates DeltaP, Ppeak, and epsilon for an underdamped system,
        setting pre-event values to zero.

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
        tuple[np.ndarray, float, float]
            A tuple containing:
            - DeltaP: The DeltaP array for the system.
            - Ppeak: The peak power.
            - epsilon: The damping ratio.
        """
        # Get the base DeltaP waveform, Ppeak, and epsilon.
        DeltaP1, Ppeak, epsilon = self._get_underdamped_delta_p_base(D, H, Xeff, time_array)
        # Set DeltaP to 0 before the event time.
        DeltaP = np.where(time_array < event_time, 0, DeltaP1)
        return DeltaP, Ppeak, epsilon

    def _calculate_epsilon_initial_check(self, D: float, H: float, Xtotal_initial: float) -> float:
        """
        Calculates the initial damping ratio (epsilon) to determine
        whether the system's response is overdamped or underdamped.

        Parameters
        ----------
        D : float
            Damping factor.
        H : float
            Inertia constant.
        Xtotal_initial : float
            Total initial reactance of the system.

        Returns
        -------
        float
            The calculated initial damping ratio (epsilon).
        """
        return (
            D
            / 2
            * np.sqrt(
                Xtotal_initial
                / (2 * H * self._gfm_params.Wb * self._gfm_params.Ucv * self._gfm_params.Ugr)
            )
        )

    def _calculate_delta_p_for_damping(
        self,
        D: float,
        H: float,
        Xeff: float,
        time_array: np.array,
        event_time: float,
        epsilon_initial_check: float,
    ) -> tuple[np.ndarray, float, float]:
        """
        Dispatches the calculation of DeltaP, Ppeak, and epsilon to the
        appropriate method based on whether the system is overdamped or
        underdamped.

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
        epsilon_initial_check : float
            The pre-calculated initial damping ratio to determine damping type.

        Returns
        -------
        tuple[np.ndarray, float, float]
            A tuple containing:
            - DeltaP: The DeltaP array for the system.
            - Ppeak: The peak power.
            - epsilon: The damping ratio.
        """
        if epsilon_initial_check > self._EPSILON_THRESHOLD:
            # Call method for overdamped system.
            return self._get_overdamped_delta_p(D, H, Xeff, time_array, event_time)
        else:
            # Call method for underdamped system.
            return self._get_underdamped_delta_p(D, H, Xeff, time_array, event_time)

    def cut_signal(self, value_min: float, signal: np.ndarray, value_max: float) -> np.ndarray:
        """
        Clips the values of a given signal array to ensure they stay
        within a specified minimum and maximum range.

        Parameters
        ----------
        value_min : float
            The minimum allowed value for the signal.
        signal : np.ndarray
            The input signal array.
        value_max : float
            The maximum allowed value for the signal.

        Returns
        -------
        np.ndarray
            The signal with values clipped within the specified limits.
        """
        # Replace values below value_min with value_min.
        Signal = np.where(signal < value_min, value_min, signal)
        # Replace values above value_max with value_max.
        Signal = np.where(signal > value_max, value_max, signal)
        return Signal

    def _get_value_at_specific_time(
        self, selected_time: float, signal: np.ndarray, time_array: np.ndarray
    ) -> float:
        """
        Retrieves the signal value at a specific time, considering a small
        offset of 10ms prior to the selected time. This is useful for
        capturing values just before an event.

        Parameters
        ----------
        selected_time : float
            The target time (in seconds) to get the value from.
        signal : np.ndarray
            The signal array from which to retrieve the value.
        time_array : np.ndarray
            The time array corresponding to the signal.

        Returns
        -------
        float
            The value of the signal at the specified time minus a 10ms offset.
        """
        # Find the index in time_array closest to (selected_time - 0.01) seconds.
        # This captures the value approximately 10ms before the selected time.
        index = np.argmin(np.abs(time_array - (selected_time - 0.01)))
        # Retrieve the value from the signal array at the identified index.
        value_at_time = signal[index]
        return value_at_time

    def _get_tunnel(self, Ppeak_array: list) -> float:
        """
        Calculates a constant "tunnel" value, which defines a band
        around the power response. The value is the maximum of a fixed
        power value and a variation proportional to Ppeak.

        Parameters
        ----------
        Ppeak_array : list
            List of Ppeak values, where the first element is the original Ppeak.

        Returns
        -------
        float
            The calculated constant tunnel value.
        """
        Ppeak = Ppeak_array[self._ORIGINAL_PARAMS_IDX]
        return max(
            self._gfm_params.FinalAllowedTunnelPn,  # Fixed power component
            self._gfm_params.FinalAllowedTunnelVariation * Ppeak,  # Proportional component
        )

    def _get_time_tunnel(
        self, Ppeak: float, time_array: np.ndarray, event_time: float
    ) -> np.ndarray:
        """
        Calculates a time-dependent "tunnel" array, which represents
        a dynamic band around the power response that expands over time.

        Parameters
        ----------
        Ppeak : float
            The peak power value, used to determine the final tunnel magnitude.
        time_array : np.ndarray
            The array of time points for the simulation.
        event_time : float
            The time at which the phase jump event occurs.

        Returns
        -------
        np.ndarray
            The time-dependent tunnel array, which starts at zero before
            the event and increases exponentially afterwards.
        """
        # Calculate the final magnitude 't_val' of the tunnel, similar to _get_tunnel.
        t_val = max(
            self._gfm_params.FinalAllowedTunnelPn,
            self._gfm_params.FinalAllowedTunnelVariation * Ppeak,
        )
        # Calculate the exponential decay for the tunnel shape.
        tunnel_exp = 1 - np.exp((-time_array + 0.02) / 0.3)
        tunnel = t_val * tunnel_exp
        # Ensure the tunnel is zero before the event_time.
        return np.where(time_array < event_time, 0, tunnel)
