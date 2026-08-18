#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA

from pathlib import Path
import numpy as np

from dycov.gfm import constants
from dycov.gfm.calculators import calculator_factory
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.outputs import plot_results, save_ini_dump, save_results_to_csv
from dycov.gfm.parameters import GFMParameters
from dycov.logging import dycov_logging

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
    ) -> None:
        """Executes the primary pipeline for GFM simulation results generation."""
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

            if parameters.should_save_all_envelopes():
                extra_envelopes = {
                    "upper_overdamped": up_over,
                    "lower_overdamped": low_over,
                    "upper_underdamped": up_under,
                    "lower_underdamped": low_under,
                }

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
            error_msg = (
                f"Configuration Error in {pcs_name}: Neither standard parameters (D, H) "
                "nor hybrid parameters are defined in the Producer.ini."
            )
            LOGGER.error(error_msg)
            raise ValueError(error_msg)

        # Retrieve calculator operational flags (e.g., inconsistent damping triggers)
        is_inconsistent = getattr(calculator, "_is_inconsistent", False)
        disclaimer_msg = getattr(calculator, "_disclaimer_message", None)

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
        """Generates the simulation time array and event time."""
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
        """Computes analytical response envelopes."""
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
        """Exports generated signals to CSV."""
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
        """Extracts and formats key simulation variables for UI rendering."""
        if params_list is None:
            return []

        text_params_info = []
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
            text_params_info.append(f"∆_grid = {parameters.get_delta_phase():.3f}º")
        if "SCR" in params_list:
            text_params_info.append(f"SCR = {parameters.get_scr():.3f}")
        if "VoltageStepAtGrid" in params_list:
            text_params_info.append(
                f"∆V_Grid = {parameters.get_voltage_step_at_grid() / 100:.3f} pu"
            )
        if "VoltageStepAtPDR" in params_list:
            text_params_info.append(
                f"∆V_PGU = {parameters.get_voltage_step_at_pdr() / 100:.3f} pu"
            )
        if "AngleStepAtPDR" in params_list:
            text_params_info.append(f"∆_PGU = {parameters.get_delta_step():.3f}º")
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
        """Dispatches variables to render visual plots."""
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
