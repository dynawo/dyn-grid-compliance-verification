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

from dycov.gfm.calculators import calculator_factory
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.outputs import plot_results, save_results_to_csv
from dycov.gfm.parameters import GFMParameters


class GridForming:
    """
    A class to handle the generation and analysis of Grid Forming (GFM)
    model results.
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
        damping_constant = parameters.get_damping_constant()
        inertia_constant = parameters.get_inertia_constant()
        x_eff = parameters.get_effective_reactance()

        calculator_name = parameters.get_calculator_name()
        calculator = calculator_factory.get_calculator(calculator_name, parameters)

        time_array, event_time = self._get_time(calculator_name)

        if calculator_name == "PhaseJump":
            params_list = ["P0", "Q0", "DeltaPhase", "AngleStepAtPDR", "SCR", "Xeff", "D", "H"]
        elif calculator_name == "AmplitudeStep":
            params_list = [
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
        elif calculator_name == "SCRJump":
            params_list = ["P0", "Q0", "SCRinitial", "SCRfinal", "Xeff", "D", "H"]
        elif calculator_name == "RoCoF":
            params_list = [
                "P0",
                "Q0",
                "Frequency0",
                "RoCoF",
                "RoCoFDuration",
                "SCR",
                "Xeff",
                "D",
                "H",
            ]
        else:
            params_list = None

        magnitude, pcc, up, down = self._calculate_envelopes(
            calculator, time_array, event_time, damping_constant, inertia_constant, x_eff
        )

        title = f"{pcs_name}.{bm_name}.{oc_name}"
        self._export_csv(working_path, title, magnitude, time_array, pcc, down, up)
        self._plot(
            working_path,
            title,
            magnitude,
            time_array,
            event_time,
            pcc,
            down,
            up,
            parameters,
            params_list,
        )

    def _get_time(self, calculator_name) -> tuple[np.ndarray, float]:
        """
        Generates the time array and defines the event time for the simulation.

        Returns
        -------
        tuple[np.ndarray, float]
            A tuple containing the time array (numpy array) and the event time
            (float).
        """
        if calculator_name == "SCRJump" or calculator_name == "RoCoF":
            start_time = -1
        else:
            start_time = 0
        
        end_time = 5
        event_time = 0
        nb_points = 3000
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
        Calculates the power envelopes (PCC, upper, and lower) based on
        the provided calculator and parameters.

        Parameters
        ----------
        calculator : GFMCalculator
            The envelopes calculator object, which performs the core calculations.
        time_array : np.ndarray
            The time array for the simulation.
        event_time : float
            The time of the event.
        damping_constant : float
            The damping constant (D) used in the GFM model.
        inertia_constant : float
            The inertia constant (H) used in the GFM model.
        x_eff : float
            The effective reactance (Xeff) used in the GFM model.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - str: The name of the plot magnitude (e.g., "Power", "Current").
            - np.ndarray: The PCC (Point of Common Coupling) power data.
            - np.ndarray: The lower envelope data.
            - np.ndarray: The upper envelope data.
        """
        (
            magnitude,  # Name of the magnitude being plotted (e.g., 'Power')
            pcc,  # Point of Common Coupling power
            up,  # Upper envelope
            down,  # Lower envelope
        ) = calculator.calculate_envelopes(
            D=damping_constant,
            H=inertia_constant,
            Xeff=x_eff,
            time_array=time_array,
            event_time=event_time,
        )

        return magnitude, pcc, up, down

    def _export_csv(
        self,
        csv_path: Path,
        title: str,
        magnitude: str,
        time_array: np.ndarray,
        pcc: np.ndarray,
        down: np.ndarray,
        up: np.ndarray,
    ) -> None:
        """
        Exports the simulation results to a CSV file.

        Parameters
        ----------
        csv_path : Path
            The base path for saving the CSV file. The filename will be
            constructed using the title.
        title : str
            The title to be used for the CSV filename.
        magnitude : str
            The name of the magnitude being plotted (e.g., "Power", "Current").
        time_array : np.ndarray
            The time array data.
        pcc : np.ndarray
            The PCC power data.
        down : np.ndarray
            The lower envelope data.
        up : np.ndarray
            The upper envelope data.
        """
        save_results_to_csv(csv_path / f"{title}.csv", magnitude, time_array, pcc, down, up)

    def _get_params_plot_info(self, parameters: GFMParameters, params_list: list):
        """
        Generates a list of formatted strings with parameter information.

        This helper function selectively extracts parameter values from a
        GFMParameters object based on a provided list of names and formats
        them into human-readable strings suitable for plotting.

        Parameters
        ----------
        parameters : GFMParameters
            An object containing the GFM simulation parameters and methods to
            access them.
        params_list : List[str]
            A list of strings specifying which parameters to extract.

        Returns
        -------
        List[str]
            A list of formatted strings, where each string represents a
            requested parameter and its value.
        """
        text_params_info = []

        if "P0" in params_list:
            value = parameters.get_initial_active_power()
            text_params_info.append(f"P0 = {value:.2f} pu")
        if "Q0" in params_list:
            value = parameters.get_initial_reactive_power()
            text_params_info.append(f"Q0 = {value:.2f}  pu")
        if "TimeTo90" in params_list:
            value = parameters.get_time_to_90()
            text_params_info.append(f"tt90 = {value:.2f} s")
        if "Pmax" in params_list:
            value = parameters.get_max_active_power()
            text_params_info.append(f"Pmax = {value:.2f} pu")
        if "Qmax" in params_list:
            value = parameters.get_max_reactive_power()
            text_params_info.append(f"Qmax = {value:.2f} pu")
        if "Pmin" in params_list:
            value = parameters.get_min_active_power()
            text_params_info.append(f"Pmin = {value:.2f} pu")
        if "Qmin" in params_list:
            value = parameters.get_min_reactive_power()
            text_params_info.append(f"Qmin = {value:.2f} pu")
        if "DeltaPhase" in params_list:
            value = parameters.get_delta_phase()
            text_params_info.append(f"Δθ = {value:.2f} °")
        if "SCR" in params_list:
            value = parameters.get_scr()
            text_params_info.append(f"SCR = {value:.2f}")
        if "VoltageStepAtGrid" in params_list:
            value = parameters.get_voltage_step_at_grid()
            text_params_info.append(f"ΔVGrid = {value / 100:.2f} pu")
        if "VoltageStepAtPDR" in params_list:
            value = parameters.get_voltage_step_at_pdr()
            text_params_info.append(f"ΔVPcc = {value / 100:.2f} pu")
        if "AngleStepAtPDR" in params_list:
            value = parameters.get_delta_step()
            text_params_info.append(f"ΔθPcc = {value:.2f} °")
        if "SCRinitial" in params_list:
            value = parameters.get_initial_scr()
            text_params_info.append(f"SCRini = {value:.2f}")
        if "SCRfinal" in params_list:
            value = parameters.get_final_scr()
            text_params_info.append(f"SCRfin = {value:.2f}")
        if "Frequency0" in params_list:
            value = parameters.get_initial_frequency()
            text_params_info.append(f"Frequency0 = {(value * 50):.2f} Hz")
        if "RoCoF" in params_list:
            value = parameters.get_change_frequency()
            text_params_info.append(f"RoCoF = {(value * 50):.2f} Hz/s")
        if "RoCoFDuration" in params_list:
            value = parameters.get_change_frequency_duration()
            text_params_info.append(f"RoCoFDuration = {value:.2f} s")
        if "Xeff" in params_list:
            value = parameters.get_effective_reactance()
            text_params_info.append(f"Xeff = {value:.2f} pu")
        if "D" in params_list:
            value = parameters.get_damping_constant()
            text_params_info.append(f"D = {value:.2f}")
        if "H" in params_list:
            value = parameters.get_inertia_constant()
            text_params_info.append(f"H = {value:.2f} s")

        return text_params_info

    def _plot(
        self,
        png_path: Path,
        title: str,
        magnitude: str,
        time_array: np.ndarray,
        event_time: float,
        pcc: np.ndarray,
        down: np.ndarray,
        up: np.ndarray,
        parameters: GFMParameters,
        params_list: list,
    ) -> None:
        """
        Generates and saves a plot of the simulation results.

        Parameters
        ----------
        png_path : Path
            The base path for saving the plot image. The filename will be
            constructed using the title.
        title : str
            The title for the plot and image filename.
        magnitude : str
            The name of the magnitude being plotted (e.g., "Power", "Current").
        time_array : np.ndarray
            The time array data.
        event_time : float
            The time of the event, used to mark on the plot.
        pcc : np.ndarray
            The PCC power data to be plotted.
        down : np.ndarray
            The lower envelope data to be plotted.
        up : np.ndarray
            The upper envelope data to be plotted.
        """

        plot_results(
            png_path / f"{title}.png",
            title,
            magnitude,
            time_array,
            event_time,
            0,  # This parameter might represent a y-axis offset or reference.
            pcc,
            down,
            up,
            "png&html",
            self._get_params_plot_info(parameters, params_list),
        )
