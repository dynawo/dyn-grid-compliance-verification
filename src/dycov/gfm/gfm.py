#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path

import numpy as np

from dycov.gfm import constants
from dycov.gfm.calculators import calculator_factory
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.outputs import plot_results, save_ini_dump, save_results_to_csv
from dycov.gfm.parameters import GFMParameters
from dycov.logging.logging import dycov_logging

# Initialize logger
LOGGER = dycov_logging.get_logger(__name__)


class GridForming:
    """
    A class to handle the generation and analysis of Grid Forming (GFM)
    model results for a single simulation case.
    """

    def generate(
        self,
        working_path: Path,
        parameters: GFMParameters,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
    ) -> None:
        """
        Generates the GFM simulation results, including calculations,
        CSV export, and plotting.

        It automatically detects if "Hybrid" parameters (Overdamped/Underdamped)
        are defined in the configuration. If so, it generates envelopes for both
        sets and merges them (Max/Min). Otherwise, it proceeds with standard
        D and H parameters.

        Parameters
        ----------
        working_path : Path
            The base path for saving results.
        parameters : GFMParameters
            An object containing the GFM simulation parameters.
        pcs_name : str
            The name of the PCS (Power Conversion System).
        bm_name : str
            The name of the benchmark.
        oc_name : str
            The name of the operating condition.
        """
        parameters.set_section(pcs_name, bm_name, oc_name)

        # Retrieve common parameters and calculator
        x_eff = parameters.get_effective_reactance()
        calculator_name = parameters.get_calculator_name()
        calculator = calculator_factory.get_calculator(calculator_name, parameters)

        time_array, event_time = self._get_time(calculator_name)

        # Get initial plot parameters list from calculator
        params_list = calculator.get_plot_parameter_names() if calculator else None

        # Decision Logic: Hybrid (Merged) Mode vs Standard Mode
        hybrid_params = parameters.get_hybrid_parameters()
        standard_params = parameters.get_standard_parameters()

        magnitude_name = ""
        pcc_signal = np.array([])
        upper_envelope = np.array([])
        lower_envelope = np.array([])

        # Dictionary to hold extra curves if 'save_all_envelopes' is True
        extra_envelopes = None

        if hybrid_params:
            LOGGER.info(
                f"Hybrid parameters detected for {pcs_name}. Running Merged Envelope generation."
            )
            d_over, h_over, d_under, h_under = hybrid_params

            # Execution 1: Overdamped Parameters
            mag_name, pcc_over, up_over, low_over = self._calculate_envelopes(
                calculator, time_array, event_time, d_over, h_over, x_eff
            )

            # Execution 2: Underdamped Parameters
            _, pcc_under, up_under, low_under = self._calculate_envelopes(
                calculator, time_array, event_time, d_under, h_under, x_eff
            )

            # Merging: Maximum of upper envelopes, Minimum of lower envelopes
            upper_envelope1 = np.maximum(up_over, up_under)
            lower_envelope1 = np.minimum(low_over, low_under)
            upper_envelope2 = np.maximum(low_over, low_under)
            lower_envelop2 = np.minimum(up_over, up_under)
            upper_envelope = np.maximum(upper_envelope1, upper_envelope2)
            lower_envelope = np.minimum(lower_envelope1, lower_envelop2)

            # For the visual PCC signal, we use the Overdamped trace as the primary reference
            pcc_signal = pcc_over
            magnitude_name = mag_name

            # Check if user wants to save/plot all individual envelopes
            if parameters.should_save_all_envelopes():
                extra_envelopes = {
                    "upper_overdamped": up_over,
                    "lower_overdamped": low_over,
                    "upper_underdamped": up_under,
                    "lower_underdamped": low_under,
                }

            # Update params_list to reflect hybrid mode in the plot
            if params_list:
                # Remove generic D and H if they exist
                params_list = [p for p in params_list if p not in ["D", "H"]]

        elif standard_params:
            LOGGER.debug(f"Standard parameters (D, H) detected for {pcs_name}.")
            d_val, h_val = standard_params
            magnitude_name, pcc_signal, upper_envelope, lower_envelope = self._calculate_envelopes(
                calculator, time_array, event_time, d_val, h_val, x_eff
            )

        else:
            # Neither standard nor hybrid parameters found
            error_msg = (
                f"Configuration Error in {pcs_name}: "
                "Neither standard parameters (D, H) nor hybrid parameters "
                "(D_Overdamped, H_Overdamped, D_Underdamped, H_Underdamped) are defined "
                "in the Producer.ini or configuration files."
            )
            LOGGER.error(error_msg)
            raise ValueError(error_msg)

        # Check calculator flags (e.g., inconsistent damping warning)
        is_inconsistent = getattr(calculator, "_is_inconsistent", False)
        disclaimer_msg = getattr(calculator, "_disclaimer_message", None)

        # Export and Plot (passing extra_envelopes)
        title = f"{pcs_name}.{bm_name}.{oc_name}"
        self._export_csv(
            working_path,
            title,
            magnitude_name,
            time_array,
            pcc_signal,
            lower_envelope,
            upper_envelope,
            extra_envelopes=extra_envelopes,
        )

        producer = parameters.get_producer()
        producer_config = producer.get_config() if producer else None

        save_ini_dump(
            path=working_path / f"{title}_ini_dump.txt",
            parameters=parameters,
            producer_config=producer_config,
            calculator=calculator,
        )

        self._plot(
            working_path,
            title,
            magnitude_name,
            time_array,
            event_time,
            pcc_signal,
            lower_envelope,
            upper_envelope,
            parameters,
            params_list,
            calculator,
            is_inconsistent,
            disclaimer_msg,
            extra_envelopes=extra_envelopes,
        )

    def _get_time(self, calculator_name: str) -> tuple[np.ndarray, float]:
        """
        Generates the time array and defines the event time for the simulation.

        Note: SCRJump and RoCoF start earlier to establish a clear steady-state.

        Parameters
        ----------
        calculator_name : str
            The name of the calculator being used.

        Returns
        -------
        tuple[np.ndarray, float]
            A tuple containing the time array and the event time (float).
        """
        if calculator_name in ["SCRJump", "RoCoF"]:
            start_time = constants.SIMULATION_START_TIME_EXTENDED
        else:
            start_time = constants.SIMULATION_START_TIME_DEFAULT

        end_time = constants.SIMULATION_END_TIME
        event_time = constants.SIMULATION_EVENT_TIME
        nb_points = constants.SIMULATION_POINTS
        time_array = np.linspace(start_time, end_time, nb_points)

        return time_array, event_time

    def _calculate_envelopes(
        self,
        calculator: GFMCalculator,
        time_array: np.ndarray,
        event_time: float,
        damping_constant: float,
        inertia_constant: float,
        x_eff: float,
    ) -> tuple[str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the response envelopes using the provided calculator.

        Parameters
        ----------
        calculator : GFMCalculator
            The envelopes calculator object.
        time_array : np.ndarray
            The time array for the simulation.
        event_time : float
            The time of the event.
        damping_constant : float
            The damping constant (D).
        inertia_constant : float
            The inertia constant (H).
        x_eff : float
            The effective reactance (Xeff).

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - str: The name of the plot magnitude (e.g., "P", "Iq").
            - np.ndarray: The PCC signal data.
            - np.ndarray: The upper envelope data.
            - np.ndarray: The lower envelope data.
        """
        magnitude_name, pcc_signal, upper_envelope, lower_envelope = (
            calculator.calculate_envelopes(
                D=damping_constant,
                H=inertia_constant,
                Xeff=x_eff,
                time_array=time_array,
                event_time=event_time,
            )
        )

        return magnitude_name, pcc_signal, upper_envelope, lower_envelope

    def _export_csv(
        self,
        csv_path: Path,
        title: str,
        magnitude_name: str,
        time_array: np.ndarray,
        pcc_signal: np.ndarray,
        lower_envelope: np.ndarray,
        upper_envelope: np.ndarray,
        extra_envelopes: dict = None,
    ) -> None:
        """
        Exports the simulation results to a CSV file.
        """
        save_results_to_csv(
            path=csv_path / f"{title}.csv",
            magnitude=magnitude_name,
            time_array=time_array,
            pcc_signal=pcc_signal,
            lower_envelope=lower_envelope,
            upper_envelope=upper_envelope,
            extra_envelopes=extra_envelopes,
        )

    def _get_params_plot_info(
        self, parameters: GFMParameters, params_list: list, calculator: GFMCalculator
    ) -> list[str]:
        """
        Generates a list of formatted strings with parameter information for plots.

        Parameters
        ----------
        parameters : GFMParameters
            The GFM parameters object to query for values.
        params_list : list
            A list of strings specifying which parameters to extract.

        Returns
        -------
        list[str]
            A list of formatted strings, each representing a parameter and its value.
        """
        if params_list is None:
            return []

        text_params_info = []

        if "P0" in params_list:
            value = parameters.get_initial_active_power()
            text_params_info.append(f"P0 = {value:.3f} pu")
        if "Q0" in params_list:
            value = parameters.get_initial_reactive_power()
            text_params_info.append(f"Q0 = {value:.3f} pu")
        if "TimeTo90" in params_list:
            value = parameters.get_time_to_90()
            text_params_info.append(f"t_90% = {(value * 1000):.3f} ms")
        if "Pmax" in params_list:
            value = parameters.get_max_active_power()
            text_params_info.append(f"Pmax = {value:.3f} pu")
        if "Qmax" in params_list:
            value = parameters.get_max_reactive_power()
            text_params_info.append(f"Qmax = {value:.3f} pu")
        if "Pmin" in params_list:
            value = parameters.get_min_active_power()
            text_params_info.append(f"Pmin = {value:.3f} pu")
        if "Qmin" in params_list:
            value = parameters.get_min_reactive_power()
            text_params_info.append(f"Qmin = {value:.3f} pu")
        if "DeltaPhase" in params_list:
            value = parameters.get_delta_phase()
            text_params_info.append(f"Δθ_grid = {value:.3f}°")
        if "SCR" in params_list:
            value = parameters.get_scr()
            text_params_info.append(f"SCR = {value:.3f}")
        if "VoltageStepAtGrid" in params_list:
            value = parameters.get_voltage_step_at_grid()
            text_params_info.append(f"ΔV_Grid = {value / 100:.3f} pu")
        if "VoltageStepAtPDR" in params_list:
            value = parameters.get_voltage_step_at_pdr()
            text_params_info.append(f"ΔV_PGU = {value / 100:.3f} pu")
        if "AngleStepAtPDR" in params_list:
            value = parameters.get_delta_step()
            text_params_info.append(f"Δθ_PGU = {value:.3f}°")
        if "SCRinitial" in params_list:
            value = parameters.get_initial_scr()
            text_params_info.append(f"SCR_initial = {value:.3f}")
        if "SCRfinal" in params_list:
            value = parameters.get_final_scr()
            text_params_info.append(f"SCR_final = {value:.3f}")
        if "Frequency0" in params_list:
            value = parameters.get_initial_frequency()
            text_params_info.append(f"f0 = {(value * 50):.3f} Hz")
        if "RoCoF" in params_list:
            value = parameters.get_change_frequency()
            text_params_info.append(f"RoCoF = {(value * 50):.3f} Hz/s")
        if "RoCoFDuration" in params_list:
            value = parameters.get_change_frequency_duration()
            text_params_info.append(f"RoCoF Duration = {(value * 1000):.3f} ms")
        if "Xeff" in params_list:
            value = parameters.get_effective_reactance()
            text_params_info.append(f"Xeff = {value:.3f} pu")
        if "D" in params_list:
            value = parameters.get_damping_constant()
            text_params_info.append(f"D = {value:.3f}")
        if "H" in params_list:
            value = parameters.get_inertia_constant()
            text_params_info.append(f"H = {value:.3f} s")
        if "Epsilon" in params_list:
            value = calculator._epsilon
            text_params_info.append(f"Epsilon = {value:.3f}")

        return text_params_info

    def _plot(
        self,
        png_path: Path,
        title: str,
        magnitude_name: str,
        time_array: np.ndarray,
        event_time: float,
        pcc_signal: np.ndarray,
        lower_envelope: np.ndarray,
        upper_envelope: np.ndarray,
        parameters: GFMParameters,
        params_list: list,
        calculator: GFMCalculator,
        is_inconsistent: bool = False,
        disclaimer_msg: str = None,
        extra_envelopes: dict = None,
    ) -> None:
        """
        Generates and saves a plot of the simulation results.
        """
        plot_results(
            path=png_path / f"{title}.png",
            title=title,
            magnitude=magnitude_name,
            time_array=time_array,
            event_time=event_time,
            shift_time=0,  # This parameter might represent a y-axis offset or reference.
            pcc_signal=pcc_signal,
            lower_envelope=lower_envelope,
            upper_envelope=upper_envelope,
            output_format="png&html",
            params_list=self._get_params_plot_info(parameters, params_list, calculator),
            show_disclaimer=is_inconsistent,
            disclaimer_message=disclaimer_msg,
            extra_envelopes=extra_envelopes,
        )
