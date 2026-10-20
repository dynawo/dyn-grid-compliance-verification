#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

import configparser
from pathlib import Path
from typing import Optional

import numpy as np

from dycov.gfm import constants
from dycov.gfm.calculators import calculator_factory
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.outputs import (
    plot_results,
    save_compliance_results,
    save_ini_dump,
    save_results_to_csv,
)
from dycov.gfm.parameters import GFMParameters
from dycov.gfm.report import GFMTestReport
from dycov.gfm.verification import curves_compliance
from dycov.logging import dycov_logging
from dycov.model.compliance import Compliance

LOGGER = dycov_logging.get_logger(__name__)


class GridForming:
    """Core orchestrator class for Grid Forming (GFM) model results generation."""

    def generate(
        self,
        working_path: Path,
        parameters: GFMParameters,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
        producer_name: str,
    ) -> GFMTestReport:
        """
        Executes the primary pipeline for GFM simulation results generation.

        Parameters
        ----------
        working_path : Path
            The directory path for intermediate and final outputs.
        parameters : GFMParameters
            The parsed parameter configuration object.
        pcs_name : str
            The name of the Point of Connection (PCS).
        bm_name : str
            The Base Model identifier.
        oc_name : str
            The Operating Condition identifier.
        producer_name : str
            The name of the producer, that of the directory holding its curves.

        Returns
        -------
        GFMTestReport
            What the report shows of the test: its parameters and, when the producer curves are
            given, their compliance and checks.
        """
        parameters.set_section(pcs_name, bm_name, oc_name)
        x_eff = parameters.get_effective_reactance()

        calculator_name = parameters.get_calculator_name()
        calculator = calculator_factory.get_calculator(calculator_name, parameters)

        time_array, event_time = self._get_time(calculator_name)
        params_list = calculator.get_plot_parameter_names() if calculator else None

        hybrid_params = parameters.get_hybrid_parameters()
        standard_params = parameters.get_standard_parameters()

        magnitude_name = ""
        pcc_signal = np.array([])
        upper_envelope = np.array([])
        lower_envelope = np.array([])
        extra_envelopes = None
        title = f"{pcs_name}.{bm_name}.{oc_name}"

        # Branch execution based on the presence of hybrid parameters (overdamped vs
        # underdamped limits)
        if hybrid_params:
            LOGGER.info(
                f"Hybrid parameters detected for {pcs_name}. Running Merged Envelope generation."
            )
            d_over, h_over, d_under, h_under = hybrid_params

            # Execution Phase 1: Overdamped Parameters
            mag_name, pcc_over, up_over, low_over = self._calculate_envelopes(
                calculator, time_array, event_time, d_over, h_over, x_eff
            )
            producer = parameters.get_producer()
            producer_config = producer.get_config() if producer else None
            save_ini_dump(
                path=working_path / f"{title}_ini_dump_overdamped.txt",
                parameters=parameters,
                producer_config=producer_config,
                calculator=calculator,
            )

            # Execution Phase 2: Underdamped Parameters
            _, pcc_under, up_under, low_under = self._calculate_envelopes(
                calculator, time_array, event_time, d_under, h_under, x_eff
            )
            producer = parameters.get_producer()
            producer_config = producer.get_config() if producer else None
            save_ini_dump(
                path=working_path / f"{title}_ini_dump_underdamped.txt",
                parameters=parameters,
                producer_config=producer_config,
                calculator=calculator,
            )

            # Envelope Merging Logic: Calculate absolute worst-case boundaries from both executions
            upper_envelope1 = np.maximum(up_over, up_under)
            lower_envelope1 = np.minimum(low_over, low_under)
            upper_envelope2 = np.maximum(low_over, low_under)
            lower_envelop2 = np.minimum(up_over, up_under)

            upper_envelope = np.maximum(upper_envelope1, upper_envelope2)
            lower_envelope = np.minimum(lower_envelope1, lower_envelop2)

            # For the visual PCC signal, the Overdamped trace acts as the primary reference
            pcc_signal = pcc_over
            magnitude_name = mag_name

            if parameters.should_save_all_envelopes():
                extra_envelopes = {
                    "upper_overdamped": up_over,
                    "lower_overdamped": low_over,
                    "upper_underdamped": up_under,
                    "lower_underdamped": low_under,
                }

            # Filter out raw D and H values from the legend since they are bifurcated in hybrid
            # mode
            if params_list:
                params_list = [p for p in params_list if p not in ["D", "H"]]

        elif standard_params:
            LOGGER.debug(f"Standard parameters (D, H) detected for {pcs_name}.")
            d_val, h_val = standard_params
            magnitude_name, pcc_signal, upper_envelope, lower_envelope = self._calculate_envelopes(
                calculator, time_array, event_time, d_val, h_val, x_eff
            )

        else:
            error_msg = (
                f"Configuration Error in {pcs_name}: Neither standard parameters (D, H) "
                "nor hybrid parameters are defined in the Producer.ini."
            )
            LOGGER.error(error_msg)
            raise ValueError(error_msg)

        max_current = parameters.get_max_current()
        if max_current is not None:
            # The DTR Fiche I18 bounds every envelope by the short-duration maximum current
            pcc_signal, lower_envelope, upper_envelope = (
                np.clip(signal, -max_current, max_current)
                for signal in (pcc_signal, lower_envelope, upper_envelope)
            )

        # Retrieve any integrity warnings triggered during calculator execution
        is_inconsistent = getattr(calculator, "_is_inconsistent", False)
        disclaimer_msg = getattr(calculator, "_disclaimer_message", None)

        curves_check = self._check_producer_curves(
            working_path,
            parameters,
            producer_name,
            title,
            magnitude_name,
            time_array,
            event_time,
            calculator.get_event_duration(),
            lower_envelope,
            upper_envelope,
        )
        producer_signal = curves_check.signal if curves_check else None

        self._export_csv(
            working_path,
            title,
            magnitude_name,
            time_array,
            pcc_signal,
            lower_envelope,
            upper_envelope,
            extra_envelopes=extra_envelopes,
            producer_signal=producer_signal,
        )

        if not hybrid_params:
            producer = parameters.get_producer()
            producer_config = producer.get_config() if producer else None
            save_ini_dump(
                path=working_path / f"{title}_ini_dump.txt",
                parameters=parameters,
                producer_config=producer_config,
                calculator=calculator,
            )

        params_info = self._get_params_plot_info(parameters, params_list, calculator)
        self._plot(
            working_path,
            title,
            magnitude_name,
            time_array,
            event_time,
            pcc_signal,
            lower_envelope,
            upper_envelope,
            params_info,
            is_inconsistent,
            disclaimer_msg,
            extra_envelopes=extra_envelopes,
            producer_signal=producer_signal,
        )

        return GFMTestReport(
            producer_name=producer_name,
            pcs=pcs_name,
            benchmark=bm_name,
            operating_condition=oc_name,
            magnitude=magnitude_name,
            parameters=params_info,
            compliance=curves_check.compliance if curves_check else None,
            envelope=curves_check.envelope if curves_check else None,
            modes=curves_check.modes if curves_check else [],
        )

    def _check_producer_curves(
        self,
        working_path: Path,
        parameters: GFMParameters,
        producer_name: str,
        title: str,
        magnitude_name: str,
        time_array: np.ndarray,
        event_time: float,
        event_duration: float,
        lower_envelope: np.ndarray,
        upper_envelope: np.ndarray,
    ) -> Optional[curves_compliance.CurvesCheck]:
        """
        Checks the producer curves of the test against its envelopes, when they are given.

        Parameters
        ----------
        working_path : Path
            The directory path for intermediate and final outputs.
        parameters : GFMParameters
            The parsed parameter configuration object.
        producer_name : str
            The name of the producer, that of the directory holding its curves.
        title : str
            The name of the test.
        magnitude_name : str
            The magnitude the envelopes bound.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp of the grid event.
        event_duration : float
            How long the grid event lasts.
        lower_envelope : np.ndarray
            The calculated lower boundary array.
        upper_envelope : np.ndarray
            The calculated upper boundary array.

        Returns
        -------
        Optional[curves_compliance.CurvesCheck]
            The result of the check, None when no producer curves are given.
        """
        curves_path = parameters.get_producer_curves_path()
        if curves_path is None:
            return None

        try:
            curves_check = curves_compliance.check(
                curves_path / producer_name,
                working_path,
                title,
                magnitude_name,
                time_array,
                event_time,
                event_duration,
                lower_envelope,
                upper_envelope,
            )
        except (OSError, ValueError, configparser.Error) as e:
            # The envelopes are still delivered: only the producer curves cannot be judged
            LOGGER.error(f"The producer curves of {title} cannot be checked. {e}")
            curves_check = curves_compliance.CurvesCheck(Compliance.InvalidTest, None, None, [])

        save_compliance_results(working_path / "results.json", curves_check)
        return curves_check

    def _get_time(self, calculator_name: str) -> tuple[np.ndarray, float]:
        """
        Generates the simulation time array and event time based on calculator type.

        Parameters
        ----------
        calculator_name : str
            The name identifier of the calculator in use.

        Returns
        -------
        tuple[np.ndarray, float]
            The numpy array containing simulation time steps
            and the float value of the event time.
        """
        # Provide extended pre-event stabilization time for calculators needing it
        if calculator_name in ["SCRJump", "RoCoF"]:
            start_time = constants.SIMULATION_START_TIME_EXTENDED
        else:
            start_time = constants.SIMULATION_START_TIME_DEFAULT

        end_time = constants.SIMULATION_END_TIME
        event_time = constants.SIMULATION_EVENT_TIME
        nb_points = constants.SIMULATION_POINTS

        return np.linspace(start_time, end_time, nb_points), event_time

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
        Computes analytical response envelopes delegating to the specific calculator.

        Parameters
        ----------
        calculator : GFMCalculator
            The instantiated calculator object.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp of the grid event.
        damping_constant : float
            The system damping parameter (D).
        inertia_constant : float
            The system inertia parameter (H).
        x_eff : float
            The effective reactance.

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            The magnitude identifier,
            power signal, upper envelope, and lower envelope arrays.
        """
        return calculator.calculate_envelopes(
            D=damping_constant,
            H=inertia_constant,
            Xeff=x_eff,
            time_array=time_array,
            event_time=event_time,
        )

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
        producer_signal: np.ndarray = None,
    ) -> None:
        """
        Exports generated signals to a CSV file.

        Parameters
        ----------
        csv_path : Path
            The directory path to save the CSV.
        title : str
            The file name for the CSV (without extension).
        magnitude_name : str
            The descriptive name of the physical magnitude.
        time_array : np.ndarray
            The time array vector.
        pcc_signal : np.ndarray
            The main signal value array.
        lower_envelope : np.ndarray
            The computed lower limit array.
        upper_envelope : np.ndarray
            The computed upper limit array.
        extra_envelopes : dict, optional
            Additional debugging envelopes to append.
        producer_signal : np.ndarray, optional
            The filtered producer curve on the same time values.
        """
        save_results_to_csv(
            path=csv_path / f"{title}.csv",
            magnitude=magnitude_name,
            time_array=time_array,
            pcc_signal=pcc_signal,
            lower_envelope=lower_envelope,
            upper_envelope=upper_envelope,
            extra_envelopes=extra_envelopes,
            producer_signal=producer_signal,
        )

    def _get_params_plot_info(
        self, parameters: GFMParameters, params_list: list, calculator: GFMCalculator
    ) -> list[str]:
        """
        Extracts and formats key simulation variables for UI rendering.

        Parameters
        ----------
        parameters : GFMParameters
            The main parameter configuration object.
        params_list : list
            The list of parameter names requested by the calculator.
        calculator : GFMCalculator
            The instantiated calculator object to query.

        Returns
        -------
        list[str]
            A list of formatted string lines for display on plots.
        """
        if params_list is None:
            return []

        text_params_info = []

        # Map backend parameters to standard physical units (pu, Hz, ms) for plot text overlay
        if "P0" in params_list:
            text_params_info.append(f"P0 = {parameters.get_initial_active_power():.3f} pu")
        if "Q0" in params_list:
            text_params_info.append(f"Q0 = {parameters.get_initial_reactive_power():.3f} pu")
        if "TimeTo90" in params_list:
            text_params_info.append(f"t_90% = {(parameters.get_time_to_90() * 1000):.3f} ms")
        if "Pmax" in params_list:
            text_params_info.append(f"Pmax = {parameters.get_max_active_power():.3f} pu")
        if "Qmax" in params_list:
            text_params_info.append(f"Qmax = {parameters.get_max_reactive_power():.3f} pu")
        if "Pmin" in params_list:
            text_params_info.append(f"Pmin = {parameters.get_min_active_power():.3f} pu")
        if "Qmin" in params_list:
            text_params_info.append(f"Qmin = {parameters.get_min_reactive_power():.3f} pu")
        if "DeltaPhase" in params_list:
            text_params_info.append(f"Δθ_grid = {parameters.get_delta_phase():.3f}°")
        if "SCR" in params_list:
            text_params_info.append(f"SCR = {parameters.get_scr():.3f}")
        if "VoltageStepAtGrid" in params_list:
            text_params_info.append(
                f"ΔV_Grid = {parameters.get_voltage_step_at_grid() / 100:.3f} pu"
            )
        if "VoltageStepAtPDR" in params_list:
            text_params_info.append(
                f"ΔV_PGU = {parameters.get_voltage_step_at_pdr() / 100:.3f} pu"
            )
        if "AngleStepAtPDR" in params_list:
            text_params_info.append(f"Δθ_PGU = {parameters.get_delta_step():.3f}°")
        if "SCRinitial" in params_list:
            text_params_info.append(f"SCR_initial = {parameters.get_initial_scr():.3f}")
        if "SCRfinal" in params_list:
            text_params_info.append(f"SCR_final = {parameters.get_final_scr():.3f}")
        if "Frequency0" in params_list:
            text_params_info.append(f"f0 = {(parameters.get_initial_frequency() * 50):.3f} Hz")
        if "RoCoF" in params_list:
            text_params_info.append(f"RoCoF = {(parameters.get_change_frequency() * 50):.3f} Hz/s")
        if "RoCoFDuration" in params_list:
            text_params_info.append(
                f"RoCoF Duration = {(parameters.get_change_frequency_duration() * 1000):.3f} ms"
            )
        if "Xeff" in params_list:
            text_params_info.append(f"Xeff = {parameters.get_effective_reactance():.3f} pu")
        if "D" in params_list:
            text_params_info.append(f"D = {parameters.get_damping_constant():.3f}")
        if "H" in params_list:
            text_params_info.append(f"H = {parameters.get_inertia_constant():.3f} s")
        if "Epsilon" in params_list:
            text_params_info.append(f"Epsilon = {calculator._epsilon:.3f}")
        if parameters.get_max_current() is not None:
            text_params_info.append(f"Imax = {parameters.get_max_current():.3f} pu")

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
        params_info: list[str],
        is_inconsistent: bool = False,
        disclaimer_msg: str = None,
        extra_envelopes: dict = None,
        producer_signal: np.ndarray = None,
    ) -> None:
        """
        Dispatches variables to render visual plots in PNG and HTML format.

        Parameters
        ----------
        png_path : Path
            The directory path to save the visual plots.
        title : str
            The title of the plot and filename.
        magnitude_name : str
            The physical magnitude measured (e.g., P, Iq).
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp when the grid event happens.
        pcc_signal : np.ndarray
            The primary physical signal array.
        lower_envelope : np.ndarray
            The calculated lower boundary array.
        upper_envelope : np.ndarray
            The calculated upper boundary array.
        params_info : list[str]
            The parameters to print on the plot, one 'name = value' line each.
        is_inconsistent : bool, optional
            Whether to display a warning flag on the plot.
        disclaimer_msg : str, optional
            A custom text to display if inconsistencies exist.
        extra_envelopes : dict, optional
            Extra boundary arrays for UI rendering.
        producer_signal : np.ndarray, optional
            The filtered producer curve on the same time values.
        """
        plot_results(
            path=png_path / f"{title}.png",
            title=title,
            magnitude=magnitude_name,
            time_array=time_array,
            event_time=event_time,
            shift_time=0,
            pcc_signal=pcc_signal,
            lower_envelope=lower_envelope,
            upper_envelope=upper_envelope,
            output_format="png&html",
            params_list=params_info,
            show_disclaimer=is_inconsistent,
            disclaimer_message=disclaimer_msg,
            extra_envelopes=extra_envelopes,
            producer_signal=producer_signal,
        )
