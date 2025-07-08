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
from dycov.logging.logging import dycov_logging


class GridForming:
    """
    A class to handle the generation and analysis of Grid Forming (GFM)
    model results.
    """

    def __init__(
        self, parameters: GFMParameters, pcs_name: str, bm_name: str, oc_name: str
    ) -> None:
        """
        Initializes the GridForming class.

        Parameters
        ----------
        parameters : GFMParameters
            An object containing the GFM simulation parameters.
        pcs_name : str
            The name of the PCS (Power Conversion System).
        bm_name : str
            The name of the benchmark.
        oc_name : str
            The name of the operating condition.
        """
        self._parameters = parameters
        self._pcs_name = pcs_name
        self._bm_name = bm_name
        self._oc_name = oc_name

    def generate(self, working_path: Path, pcs_name: str, bm_name: str, oc_name: str) -> None:
        """
        Generates the GFM simulation results, including calculations,
        CSV export, and plotting.

        Parameters
        ----------
        working_path : Path
            The base path for saving results.
        pcs_name : str
            The name of the PCS.
        bm_name : str
            The name of the benchmark.
        oc_name : str
            The name of the operating condition.
        """
        gfm_params = self._parameters.pcs_configuration(pcs_name, bm_name, oc_name)
        dycov_logging.get_logger("GridForming").debug(f"GFM Params {gfm_params}")
        time_array, event_time = self._get_time()
        damping_constant = self._parameters.get_damping_constant()
        inertia_constant = self._parameters.get_inertia_constant()
        x_eff = self._parameters.get_effective_reactance(pcs_name, bm_name, oc_name)
        dycov_logging.get_logger("GridForming").debug(
            f"Input Params D={damping_constant} H={inertia_constant} Xeff {x_eff}"
        )
        calculator = calculator_factory.get_calculator(
            self._parameters.get_calculator_name(pcs_name, bm_name), gfm_params
        )
        title, magnitude, pcc, up, down = self._calculate_envelopes(
            calculator, time_array, event_time, damping_constant, inertia_constant, x_eff
        )
        self._export_csv(working_path, title, time_array, pcc, down, up)
        self._plot(working_path, title, magnitude, time_array, event_time, pcc, down, up)

    def _get_time(self) -> tuple[np.ndarray, float]:
        """
        Generates the time array and defines the event time for the simulation.

        Returns
        -------
        tuple[np.ndarray, float]
            A tuple containing the time array and the event time.
        """
        start_time = 0
        end_time = 2
        event_time = 0
        nb_points = 400
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
    ) -> tuple[str, str, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates the power envelopes (PCC, upper, and lower) based on
        the provided calculator and parameters.

        Parameters
        ----------
        calculator : GFMCalculator
            The envelopes calculator.
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
        tuple[str, str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing the plot title, magnitude name, PCC power, upper envelope,
            and lower envelope.
        """
        (
            magnitude,
            pcc,
            up,
            down,
        ) = calculator.calculate_envelopes(
            D=damping_constant,
            H=inertia_constant,
            Xeff=x_eff,
            time_array=time_array,
            event_time=event_time,
        )

        title = f"{self._pcs_name}.{self._bm_name}.{self._oc_name}"
        return title, magnitude, pcc, up, down

    def _export_csv(
        self,
        working_path: Path,
        title: str,
        time_array: np.ndarray,
        pcc: np.ndarray,
        down: np.ndarray,
        up: np.ndarray,
    ) -> None:
        """
        Exports the simulation results to a CSV file.

        Parameters
        ----------
        working_path : Path
            The base path for saving the CSV file.
        title : str
            The title to be used for the CSV filename.
        time_array : np.ndarray
            The time array.
        pcc : np.ndarray
            The PCC power data.
        down : np.ndarray
            The lower envelope data.
        up : np.ndarray
            The upper envelope data.
        """
        csv_path = working_path / "CSVResults"
        csv_path.mkdir(parents=True, exist_ok=True)

        save_results_to_csv(csv_path / f"{title}.csv", time_array, pcc, down, up)

    def _plot(
        self,
        working_path: Path,
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
        working_path : Path
            The base path for saving the plot image.
        title : str
            The title for the plot and image filename.
        time_array : np.ndarray
            The time array.
        event_time : float
            The time of the event.
        pcc : np.ndarray
            The PCC power data.
        down : np.ndarray
            The lower envelope data.
        up : np.ndarray
            The upper envelope data.
        """
        png_path = working_path / "PNGResults"
        png_path.mkdir(parents=True, exist_ok=True)
        plot_results(
            png_path / f"{title}.png",
            title,
            magnitude,
            time_array,
            event_time,
            0,
            pcc,
            down,
            up,
        )
