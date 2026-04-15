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

# Initialize logger for the Grid Forming module
LOGGER = dycov_logging.get_logger(__name__)


class GridForming:
    """Core orchestrator class designed to handle the generation and analysis of Grid Forming (GFM)
    model results for single simulation scenarios."""

    def generate(
        self,
        working_path: Path,
        parameters: GFMParameters,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
    ) -> None:
        """Executes the primary pipeline for GFM simulation results generation, including data
        calculations, CSV data exports, and plotting.

        It automatically detects if "Hybrid" parameters (Overdamped/Underdamped conditions)
        are defined within the configuration. If detected, it calculates envelopes for both
        damping conditions and merges them (applying Min/Max boundary logic). Otherwise,
        it proceeds with the standard predefined D and H parameters.

        Parameters
        ----------
        working_path : Path
            The base directory path designated for saving the generated output files.
        parameters : GFMParameters
            The loaded parameter configuration object guiding the simulation.
        pcs_name : str
            The identifier name of the specific Power Conversion System (PCS).
        bm_name : str
            The identifier name of the Benchmark applied.
        oc_name : str
            The identifier name of the specific Operating Condition.
        """
        parameters.set_section(pcs_name, bm_name, oc_name)

        # Retrieve common effective parameters and instantiate the correct calculator strategy
        x_eff = parameters.get_effective_reactance()
        calculator_name = parameters.get_calculator_name()
        calculator = calculator_factory.get_calculator(calculator_name, parameters)

        time_array, event_time = self._get_time(calculator_name)

        # Retrieve the initial list of parameters targeted for the plotting UI
        params_list = calculator.get_plot_parameter_names() if calculator else None

        # Determine the execution path: Hybrid (Merged) Mode vs Standard Mode
        hybrid_params = parameters.get_hybrid_parameters()
        standard_params = parameters.get_standard_parameters()

        magnitude_name = ""
        pcc_signal = np.array([])
        upper_envelope = np.array([])
        lower_envelope = np.array([])

        # Dictionary to hold supplementary curves if 'save_all_envelopes' is enabled
        extra_envelopes = None
        title = f"{pcs_name}.{bm_name}.{oc_name}"

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

            # Envelope Merging Logic: Calculate the absolute outermost bounds
            # Maximum of both upper envelopes, Minimum of both lower envelopes
            upper_envelope1 = np.maximum(up_over, up_under)
            lower_envelope1 = np.minimum(low_over, low_under)
            upper_envelope2 = np.maximum(low_over, low_under)
            lower_envelop2 = np.minimum(up_over, up_under)
            upper_envelope = np.maximum(upper_envelope1, upper_envelope2)
            lower_envelope = np.minimum(lower_envelope1, lower_envelop2)

            # For the visual PCC signal, the Overdamped trace acts as the primary reference
            pcc_signal = pcc_over
            magnitude_name = mag_name

            # Store individual boundary curves if the detailed output configuration is enabled
            if parameters.should_save_all_envelopes():
                extra_envelopes = {
                    "upper_overdamped": up_over,
                    "lower_overdamped": low_over,
                    "upper_underdamped": up_under,
                    "lower_underdamped": low_under,
                }

            # Update the plot parameters legend to accurately reflect the hybrid status
            if params_list:
                # Remove generic D and H labels, as hybrid uses dual configurations
                params_list = [p for p in params_list if p not in ["D", "H"]]

        elif standard_params:
            LOGGER.debug(f"Standard parameters (D, H) detected for {pcs_name}.")
            d_val, h_val = standard_params
            magnitude_name, pcc_signal, upper_envelope, lower_envelope = self._calculate_envelopes(
                calculator, time_array, event_time, d_val, h_val, x_eff
            )

        else:
            # Trigger exception if no valid calculation bounds are defined
            error_msg = (
                f"Configuration Error in {pcs_name}: "
                "Neither standard parameters (D, H) nor hybrid parameters "
                "(D_Overdamped, H_Overdamped, D_Underdamped, H_Underdamped) are defined "
                "in the Producer.ini or configuration files."
            )
            LOGGER.error(error_msg)
            raise ValueError(error_msg)

        # Retrieve calculator operational flags (e.g., inconsistent damping triggers)
        is_inconsistent = getattr(calculator, "_is_inconsistent", False)
        disclaimer_msg = getattr(calculator, "_disclaimer_message", None)

        # Execute data export and rendering routines
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

        if not hybrid_params:
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
        """Generates the simulation time array and determines the precise event time.

        Note: Specific calculators like SCRJump and RoCoF require an extended pre-event
        simulation window to establish a clear steady-state baseline.

        Parameters
        ----------
        calculator_name : str
            The specific identifier string of the active calculator strategy.

        Returns
        -------
        tuple[np.ndarray, float]
            A tuple containing the complete time array (np.ndarray) and the
            calculated event time (float).
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
        """Computes the analytical response envelopes using the active calculation strategy.

        Parameters
        ----------
        calculator : GFMCalculator
            The instantiated envelope calculator object.
        time_array : np.ndarray
            The X-axis time array mapped for the simulation.
        event_time : float
            The absolute point in time where the grid event is triggered.
        damping_constant : float
            The system damping constant value (D).
        inertia_constant : float
            The system inertia constant value (H).
        x_eff : float
            The effective reactance of the system (Xeff).

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
            A tuple containing:
            - str: The symbolic name of the magnitude plotted (e.g., 'P', 'Iq').
            - np.ndarray: The resulting PCC signal data array.
            - np.ndarray: The upper bound envelope data array.
            - np.ndarray: The lower bound envelope data array.
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
        """Marshals the generated mathematical signals and exports them to a structured CSV format.

        Parameters
        ----------
        csv_path : Path
            The directory path intended for the output CSV file.
        title : str
            The base filename for the output file.
        magnitude_name : str
            The physical magnitude being analyzed (e.g., 'P', 'Iq').
        time_array : np.ndarray
            Array containing all time steps evaluated.
        pcc_signal : np.ndarray
            The recorded system signal at the Point of Common Coupling.
        lower_envelope : np.ndarray
            The array bounding the lower limit of the response.
        upper_envelope : np.ndarray
            The array bounding the upper limit of the response.
        extra_envelopes : dict, optional
            A dictionary appending supplementary data series as additional columns.
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
        """Extracts and formats key simulation variables into human-readable strings for UI
        rendering.

        Parameters
        ----------
        parameters : GFMParameters
            The central configuration object queried for parameter values.
        params_list : list
            A filter list of string identifiers specifying which parameters should be extracted.
        calculator : GFMCalculator
            The calculator providing internal runtime variables (e.g., Epsilon).

        Returns
        -------
        list[str]
            A comprehensive list of cleanly formatted strings representing parameters and values.
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
        """Dispatches the internal variables to render and export the final visual plots.

        Parameters
        ----------
        png_path : Path
            Destination directory intended for the graphical output files.
        title : str
            The base title rendered onto the graph and used as the filename.
        magnitude_name : str
            The specific physical unit or magnitude being graphed (e.g., 'P', 'Iq').
        time_array : np.ndarray
            The complete X-axis time representation array.
        event_time : float
            The specific point marking the event initialization for rendering overlays.
        pcc_signal : np.ndarray
            The evaluated signal line derived from the simulation.
        lower_envelope : np.ndarray
            The continuous lower constraint threshold series.
        upper_envelope : np.ndarray
            The continuous upper constraint threshold series.
        parameters : GFMParameters
            The simulation parameter handler used to populate legend labels.
        params_list : list
            Target variables designated for inclusion within the visual legend.
        calculator : GFMCalculator
            The active calculator instance providing necessary derivation boundaries.
        is_inconsistent : bool, optional
            Flag to highlight data anomalies via graphical overlays. Defaults to False.
        disclaimer_msg : str, optional
            Specific warning message overlay injected into the plot.
        extra_envelopes : dict, optional
            Supplementary graphs triggered during hybrid evaluation structures.
        """
        plot_results(
            path=png_path / f"{title}.png",
            title=title,
            magnitude=magnitude_name,
            time_array=time_array,
            event_time=event_time,
            shift_time=0,  # Temporal shift reference indicating y-axis marker offset.
            pcc_signal=pcc_signal,
            lower_envelope=lower_envelope,
            upper_envelope=upper_envelope,
            output_format="png&html",
            params_list=self._get_params_plot_info(parameters, params_list, calculator),
            show_disclaimer=is_inconsistent,
            disclaimer_message=disclaimer_msg,
            extra_envelopes=extra_envelopes,
        )
