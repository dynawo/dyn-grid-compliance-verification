#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

from pathlib import Path
import numpy as np
from dycov.gfm import constants
from dycov.gfm.calculators import calculator_factory
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.outputs import plot_results, save_ini_dump, save_results_to_csv
from dycov.gfm.parameters import GFMParameters
from dycov.logging.logging import dycov_logging

LOGGER = dycov_logging.get_logger(__name__)


class GridForming:
    """
    Core orchestrator class designed to handle the generation and analysis of
    Grid Forming (GFM) model results for single simulation scenarios.
    """

    def _merge_hybrid_envelopes(
        self,
        up_over: np.ndarray,
        low_over: np.ndarray,
        up_under: np.ndarray,
        low_under: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Merges overdamped and underdamped envelopes applying Min/Max boundary logic.

        Parameters
        ----------
        up_over : np.ndarray
            The upper envelope calculated for the overdamped condition.
        low_over : np.ndarray
            The lower envelope calculated for the overdamped condition.
        up_under : np.ndarray
            The upper envelope calculated for the underdamped condition.
        low_under : np.ndarray
            The lower envelope calculated for the underdamped condition.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            A tuple containing the final merged upper and lower envelopes.
        """
        # Synthesize maximum allowable boundaries evaluating both damping profiles
        upper_envelope1 = np.maximum(up_over, up_under)
        lower_envelope1 = np.minimum(low_over, low_under)

        # Cross-reference profiles to map the absolute worst-case scenario
        upper_envelope2 = np.maximum(low_over, low_under)
        lower_envelope2 = np.minimum(up_over, up_under)

        # Output strictly constrained final envelopes
        upper_envelope = np.maximum(upper_envelope1, upper_envelope2)
        lower_envelope = np.minimum(lower_envelope1, lower_envelope2)
        return upper_envelope, lower_envelope

    def generate(
        self,
        working_path: Path,
        parameters: GFMParameters,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
    ) -> None:
        """
        Executes the primary pipeline for GFM simulation results generation.

        This method orchestrates the calculation of envelopes, CSV data exports,
        and plotting. It detects if "Hybrid" parameters are defined to generate
        and merge dual damping conditions, otherwise it uses standard parameters.

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

        if hybrid_params:
            LOGGER.info(
                f"Hybrid parameters detected for {pcs_name}. Running Merged Envelope generation."
            )
            d_over, h_over, d_under, h_under = hybrid_params

            # Phase 1: Retrieve and record overdamped performance
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

            # Phase 2: Retrieve and record underdamped performance
            _, pcc_under, up_under, low_under = self._calculate_envelopes(
                calculator, time_array, event_time, d_under, h_under, x_eff
            )
            save_ini_dump(
                path=working_path / f"{title}_ini_dump_underdamped.txt",
                parameters=parameters,
                producer_config=producer_config,
                calculator=calculator,
            )

            # Merge both conditions to find absolute boundaries
            upper_envelope, lower_envelope = self._merge_hybrid_envelopes(
                up_over, low_over, up_under, low_under
            )
            pcc_signal = pcc_over
            magnitude_name = mag_name

            # Package intermediate mathematical traces for detailed plotting if enabled
            if parameters.should_save_all_envelopes():
                extra_envelopes = {
                    "upper_overdamped": up_over,
                    "lower_overdamped": low_over,
                    "upper_underdamped": up_under,
                    "lower_underdamped": low_under,
                }

            # Filter standard constraints from legends for hybrid mode
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
                f"Configuration Error in {pcs_name}: Parameters D, H or hybrid not defined."
            )
            LOGGER.error(error_msg)
            raise ValueError(error_msg)

        # Interrogate calculator state securely via properties
        is_inconsistent = calculator.is_inconsistent
        disclaimer_msg = calculator.disclaimer_message

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
            save_ini_dump(
                path=working_path / f"{title}_ini_dump.txt",
                parameters=parameters,
                producer_config=producer.get_config() if producer else None,
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
        Generates the simulation time array and determines the precise event time.

        Parameters
        ----------
        calculator_name : str
            The specific identifier string of the active calculator strategy.

        Returns
        -------
        tuple[np.ndarray, float]
            A tuple containing the complete time array and the calculated event time.
        """
        # Pre-event initialization required explicitly for frequency and SCR deviations
        start_time = (
            constants.SIMULATION_START_TIME_EXTENDED
            if calculator_name in ["SCRJump", "RoCoF"]
            else constants.SIMULATION_START_TIME_DEFAULT
        )
        time_array = np.linspace(
            start_time, constants.SIMULATION_END_TIME, constants.SIMULATION_POINTS
        )
        return time_array, constants.SIMULATION_EVENT_TIME

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
        Computes the analytical response envelopes using the active calculation strategy.

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
            A tuple containing the magnitude name, PCC signal, upper envelope, and lower envelope.
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
    ) -> None:
        """Marshals the generated mathematical signals and exports them to a structured CSV format."""
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
        Extracts and formats key simulation variables into human-readable strings for UI rendering.

        Parameters
        ----------
        parameters : GFMParameters
            The central configuration object queried for parameter values.
        params_list : list
            A filter list of string identifiers specifying which parameters should be extracted.
        calculator : GFMCalculator
            The calculator providing internal runtime variables.

        Returns
        -------
        list[str]
            A comprehensive list of cleanly formatted strings representing parameters and values.
        """
        if not params_list:
            return []
        text_params_info = []
        param_mapping = {
            "P0": (parameters.get_initial_active_power, "P0 = {:.3f} pu"),
            "Q0": (parameters.get_initial_reactive_power, "Q0 = {:.3f} pu"),
            "TimeTo90": (lambda: parameters.get_time_to_90() * 1000, "t_90% = {:.3f} ms"),
            "Pmax": (parameters.get_max_active_power, "Pmax = {:.3f} pu"),
            "Qmax": (parameters.get_max_reactive_power, "Qmax = {:.3f} pu"),
            "Pmin": (parameters.get_min_active_power, "Pmin = {:.3f} pu"),
            "Qmin": (parameters.get_min_reactive_power, "Qmin = {:.3f} pu"),
            "DeltaPhase": (parameters.get_delta_phase, "Phase = {:.3f} deg"),
            "SCR": (parameters.get_scr, "SCR = {:.3f}"),
            "VoltageStepAtGrid": (
                lambda: parameters.get_voltage_step_at_grid() / 100,
                "V_Grid = {:.3f} pu",
            ),
            "VoltageStepAtPDR": (
                lambda: parameters.get_voltage_step_at_pdr() / 100,
                "V_PGU = {:.3f} pu",
            ),
            "AngleStepAtPDR": (parameters.get_delta_step, "Angle = {:.3f} deg"),
            "SCRinitial": (parameters.get_initial_scr, "SCR_initial = {:.3f}"),
            "SCRfinal": (parameters.get_final_scr, "SCR_final = {:.3f}"),
            "Frequency0": (lambda: parameters.get_initial_frequency() * 50, "f0 = {:.3f} Hz"),
            "RoCoF": (lambda: parameters.get_change_frequency() * 50, "RoCoF = {:.3f} Hz/s"),
            "RoCoFDuration": (
                lambda: parameters.get_change_frequency_duration() * 1000,
                "RoCoF Duration = {:.3f} ms",
            ),
            "Xeff": (parameters.get_effective_reactance, "Xeff = {:.3f} pu"),
            "D": (parameters.get_damping_constant, "D = {:.3f}"),
            "H": (parameters.get_inertia_constant, "H = {:.3f} s"),
        }
        for param in params_list:
            if param in param_mapping:
                func, fmt = param_mapping[param]
                text_params_info.append(fmt.format(func()))
            elif param == "Epsilon":
                text_params_info.append(f"Epsilon = {calculator.epsilon:.3f}")
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
        """Dispatches the internal variables to render and export the final visual plots."""
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
            params_list=self._get_params_plot_info(parameters, params_list, calculator),
            show_disclaimer=is_inconsistent,
            disclaimer_message=disclaimer_msg,
            extra_envelopes=extra_envelopes,
        )
