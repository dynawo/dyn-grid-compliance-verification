#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, NamedTuple, Optional

import numpy as np

from dycov.gfm import constants
from dycov.gfm.calculators import calculator_factory
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.outputs import plot_results, save_ini_dump, save_results_to_csv
from dycov.gfm.parameters import GFMParameters
from dycov.logging import dycov_logging

LOGGER = dycov_logging.get_logger(__name__)

# The figures turn frequencies from pu to Hz on a 50 Hz base, whatever the nominal frequency.
_PLOT_FREQUENCY_BASE_HZ = 50


class _PlotParameter(NamedTuple):
    """A line of the parameter box of the figures."""

    name: str
    text: str
    value: Callable[[GFMParameters, GFMCalculator], float]


# In the order the figures show them.
_PLOT_PARAMETERS = (
    _PlotParameter("P0", "P0 = {:.3f} pu", lambda p, c: p.get_initial_active_power()),
    _PlotParameter("Q0", "Q0 = {:.3f} pu", lambda p, c: p.get_initial_reactive_power()),
    _PlotParameter("TimeTo90", "t_90% = {:.3f} ms", lambda p, c: p.get_time_to_90() * 1000),
    _PlotParameter("Pmax", "Pmax = {:.3f} pu", lambda p, c: p.get_max_active_power()),
    _PlotParameter("Qmax", "Qmax = {:.3f} pu", lambda p, c: p.get_max_reactive_power()),
    _PlotParameter("Pmin", "Pmin = {:.3f} pu", lambda p, c: p.get_min_active_power()),
    _PlotParameter("Qmin", "Qmin = {:.3f} pu", lambda p, c: p.get_min_reactive_power()),
    _PlotParameter("DeltaPhase", "Δθ_grid = {:.3f}°", lambda p, c: p.get_delta_phase()),
    _PlotParameter("SCR", "SCR = {:.3f}", lambda p, c: p.get_scr()),
    _PlotParameter(
        "VoltageStepAtGrid", "ΔV_Grid = {:.3f} pu", lambda p, c: p.get_voltage_step_at_grid() / 100
    ),
    _PlotParameter(
        "VoltageStepAtPDR", "ΔV_PGU = {:.3f} pu", lambda p, c: p.get_voltage_step_at_pdr() / 100
    ),
    _PlotParameter("AngleStepAtPDR", "Δθ_PGU = {:.3f}°", lambda p, c: p.get_delta_step()),
    _PlotParameter("SCRinitial", "SCR_initial = {:.3f}", lambda p, c: p.get_initial_scr()),
    _PlotParameter("SCRfinal", "SCR_final = {:.3f}", lambda p, c: p.get_final_scr()),
    _PlotParameter(
        "Frequency0",
        "f0 = {:.3f} Hz",
        lambda p, c: p.get_initial_frequency() * _PLOT_FREQUENCY_BASE_HZ,
    ),
    _PlotParameter(
        "RoCoF",
        "RoCoF = {:.3f} Hz/s",
        lambda p, c: p.get_change_frequency() * _PLOT_FREQUENCY_BASE_HZ,
    ),
    _PlotParameter(
        "RoCoFDuration",
        "RoCoF Duration = {:.3f} ms",
        lambda p, c: p.get_change_frequency_duration() * 1000,
    ),
    _PlotParameter("Xeff", "Xeff = {:.3f} pu", lambda p, c: p.get_effective_reactance()),
    _PlotParameter("D", "D = {:.3f}", lambda p, c: p.get_damping_constant()),
    _PlotParameter("H", "H = {:.3f} s", lambda p, c: p.get_inertia_constant()),
    _PlotParameter("Epsilon", "Epsilon = {:.3f}", lambda p, c: c.get_damping_ratio()),
)

# A hybrid run calculates with two sets of D and H, so the figures do not show the values of a
# single set.
_SINGLE_DAMPING_PARAMETERS = ("D", "H", "Epsilon")


@dataclass
class _Envelopes:
    """What a calculation gives: the expected signal and the envelopes around it."""

    magnitude_name: str
    pcc_signal: np.ndarray
    upper_envelope: np.ndarray
    lower_envelope: np.ndarray
    extra_envelopes: Optional[dict[str, np.ndarray]] = None


class GridForming:
    """Generates the envelopes of one operating condition of a GFM test."""

    def generate(
        self,
        working_path: Path,
        parameters: GFMParameters,
        pcs_name: str,
        bm_name: str,
        oc_name: str,
    ) -> None:
        """
        Calculates the envelopes of an operating condition and writes them, with the
        simulation dump and the figures, under working_path.

        The producer gives either one set of D and H, or two (overdamped and underdamped), in
        which case the envelopes cover both.

        Parameters
        ----------
        working_path : Path
            The directory path for intermediate and final outputs.
        parameters : GFMParameters
            The parsed parameter configuration object.
        pcs_name : str
            The name of the PCS.
        bm_name : str
            The name of the benchmark.
        oc_name : str
            The name of the operating condition.

        Raises
        ------
        ValueError
            If neither one set of D and H nor the overdamped and underdamped sets are given.
        """
        parameters.set_section(pcs_name, bm_name, oc_name)
        x_eff = parameters.get_effective_reactance()

        calculator_name = parameters.get_calculator_name()
        calculator = calculator_factory.get_calculator(calculator_name, parameters)

        time_array, event_time = self._get_time(calculator_name)
        params_list = calculator.get_plot_parameter_names() if calculator else None

        hybrid_params = parameters.get_hybrid_parameters()
        standard_params = parameters.get_standard_parameters()
        title = f"{pcs_name}.{bm_name}.{oc_name}"

        if hybrid_params:
            LOGGER.info(
                f"Hybrid parameters detected for {pcs_name}. Running Merged Envelope generation."
            )
            envelopes = self._calculate_hybrid_envelopes(
                working_path,
                title,
                parameters,
                calculator,
                time_array,
                event_time,
                hybrid_params,
                x_eff,
            )
            if params_list:
                params_list = [p for p in params_list if p not in _SINGLE_DAMPING_PARAMETERS]
        elif standard_params:
            LOGGER.debug(f"Standard parameters (D, H) detected for {pcs_name}.")
            d_val, h_val = standard_params
            envelopes = self._calculate_envelopes(
                calculator, time_array, event_time, d_val, h_val, x_eff
            )
        else:
            error_msg = (
                f"Configuration Error in {pcs_name}: Neither standard parameters (D, H) "
                "nor hybrid parameters are defined in the Producer.ini."
            )
            LOGGER.error(error_msg)
            raise ValueError(error_msg)

        save_results_to_csv(
            path=working_path / f"{title}.csv",
            magnitude=envelopes.magnitude_name,
            time_array=time_array,
            pcc_signal=envelopes.pcc_signal,
            lower_envelope=envelopes.lower_envelope,
            upper_envelope=envelopes.upper_envelope,
            extra_envelopes=envelopes.extra_envelopes,
        )
        if not hybrid_params:
            self._save_dump(working_path / f"{title}_ini_dump.txt", parameters, calculator)

        self._plot(
            working_path,
            title,
            envelopes,
            time_array,
            event_time,
            parameters,
            params_list,
            calculator,
        )

    def _calculate_hybrid_envelopes(
        self,
        working_path: Path,
        title: str,
        parameters: GFMParameters,
        calculator: GFMCalculator,
        time_array: np.ndarray,
        event_time: float,
        hybrid_params: tuple[float, float, float, float],
        x_eff: float,
    ) -> _Envelopes:
        """
        Calculates the envelopes of both sets of D and H and merges them.

        Each calculation writes the simulation dump of its own set.

        Parameters
        ----------
        working_path : Path
            The directory the dumps are written to.
        title : str
            The name of the operating condition, which the dumps start with.
        parameters : GFMParameters
            The parsed parameter configuration object.
        calculator : GFMCalculator
            The instantiated calculator object.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp of the grid event.
        hybrid_params : tuple[float, float, float, float]
            D and H of the overdamped set, then D and H of the underdamped one.
        x_eff : float
            The effective reactance.

        Returns
        -------
        _Envelopes
            The signal of the overdamped set and the envelopes that cover both sets.
        """
        d_over, h_over, d_under, h_under = hybrid_params

        over = self._calculate_envelopes(calculator, time_array, event_time, d_over, h_over, x_eff)
        self._save_dump(working_path / f"{title}_ini_dump_overdamped.txt", parameters, calculator)

        under = self._calculate_envelopes(
            calculator, time_array, event_time, d_under, h_under, x_eff
        )
        self._save_dump(working_path / f"{title}_ini_dump_underdamped.txt", parameters, calculator)

        upper_envelope, lower_envelope = self._merge_envelopes(
            over.upper_envelope, over.lower_envelope, under.upper_envelope, under.lower_envelope
        )

        extra_envelopes = None
        if parameters.should_save_all_envelopes():
            extra_envelopes = {
                "upper_overdamped": over.upper_envelope,
                "lower_overdamped": over.lower_envelope,
                "upper_underdamped": under.upper_envelope,
                "lower_underdamped": under.lower_envelope,
            }
        return _Envelopes(
            over.magnitude_name, over.pcc_signal, upper_envelope, lower_envelope, extra_envelopes
        )

    @staticmethod
    def _merge_envelopes(
        up_over: np.ndarray, low_over: np.ndarray, up_under: np.ndarray, low_under: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Merges the envelopes of the two sets of D and H into the widest band.

        The four envelopes are compared all with all, since the envelopes of a set can cross.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            The upper and lower envelopes.
        """
        upper_envelope1 = np.maximum(up_over, up_under)
        lower_envelope1 = np.minimum(low_over, low_under)
        upper_envelope2 = np.maximum(low_over, low_under)
        lower_envelope2 = np.minimum(up_over, up_under)
        return (
            np.maximum(upper_envelope1, upper_envelope2),
            np.minimum(lower_envelope1, lower_envelope2),
        )

    @staticmethod
    def _save_dump(path: Path, parameters: GFMParameters, calculator: GFMCalculator) -> None:
        producer = parameters.get_producer()
        save_ini_dump(
            path=path,
            parameters=parameters,
            producer_config=producer.get_config() if producer else None,
            calculator=calculator,
        )

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
            The simulation time steps and the event time.
        """
        if calculator_name in ["SCRJump", "RoCoF"]:
            start_time = constants.SIMULATION_START_TIME_EXTENDED
        else:
            start_time = constants.SIMULATION_START_TIME_DEFAULT

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
    ) -> _Envelopes:
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
        _Envelopes
            The magnitude identifier, the expected signal and the upper and lower envelopes.
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
        return _Envelopes(magnitude_name, pcc_signal, upper_envelope, lower_envelope)

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
        return [
            parameter.text.format(parameter.value(parameters, calculator))
            for parameter in _PLOT_PARAMETERS
            if parameter.name in params_list
        ]

    def _plot(
        self,
        png_path: Path,
        title: str,
        envelopes: _Envelopes,
        time_array: np.ndarray,
        event_time: float,
        parameters: GFMParameters,
        params_list: list,
        calculator: GFMCalculator,
    ) -> None:
        """
        Draws the envelopes in PNG and HTML format.

        Parameters
        ----------
        png_path : Path
            The directory path to save the visual plots.
        title : str
            The title of the plot and filename.
        envelopes : _Envelopes
            The signal and envelopes to draw.
        time_array : np.ndarray
            The simulation time vector.
        event_time : float
            The timestamp when the grid event happens.
        parameters : GFMParameters
            The simulation parameter configuration.
        params_list : list
            The list of variables to print on the plot legend.
        calculator : GFMCalculator
            The calculator instance used for simulation; a calculator that found its
            envelopes unreliable has the figure carry its disclaimer.
        """
        plot_results(
            path=png_path / f"{title}.png",
            title=title,
            magnitude=envelopes.magnitude_name,
            time_array=time_array,
            event_time=event_time,
            shift_time=0,
            pcc_signal=envelopes.pcc_signal,
            lower_envelope=envelopes.lower_envelope,
            upper_envelope=envelopes.upper_envelope,
            output_format="png&html",
            params_list=self._get_params_plot_info(parameters, params_list, calculator),
            show_disclaimer=getattr(calculator, "_is_inconsistent", False),
            disclaimer_message=getattr(calculator, "_disclaimer_message", None),
            extra_envelopes=envelopes.extra_envelopes,
        )
