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
        time_array, event_time = self._get_time()

        parameters.set_section(pcs_name, bm_name, oc_name)
        damping_constant = parameters.get_damping_constant()
        inertia_constant = parameters.get_inertia_constant()
        x_eff = parameters.get_effective_reactance()

        calculator = calculator_factory.get_calculator(
            parameters.get_calculator_name(), parameters
        )

        magnitude, pcc, up, down = self._calculate_envelopes(
            calculator, time_array, event_time, damping_constant, inertia_constant, x_eff
        )

        title = f"{pcs_name}.{bm_name}.{oc_name}"
        self._export_csv(working_path, title, magnitude, time_array, pcc, down, up)
        self._plot(working_path, title, magnitude, time_array, event_time, pcc, down, up)

    def _get_time(self) -> tuple[np.ndarray, float]:
        """
        Generates the time array and defines the event time for the simulation.

        Returns
        -------
        tuple[np.ndarray, float]
            A tuple containing the time array (numpy array) and the event time
            (float).
        """
        start_time = 0
        end_time = 5
        event_time = 0
        nb_points = 1000
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
        )
