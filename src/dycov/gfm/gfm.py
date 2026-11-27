#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, NamedTuple, Optional

import numpy as np

from dycov.gfm import constants
from dycov.gfm.calculators import calculator_factory
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.outputs import (
    Envelopes,
    plot_results,
    read_envelopes,
    save_ini_dump,
    save_results,
    save_results_to_csv,
)
from dycov.gfm.parameters import GFMParameters
from dycov.gfm.report import GFMTestReport
from dycov.gfm.verification import curves_compliance
from dycov.logging import dycov_logging
from dycov.model.compliance import Compliance

LOGGER = dycov_logging.get_logger(__name__)


class _PlotParameter(NamedTuple):
    """A line of the parameter box of the figures."""

    name: str
    text: str
    value: Callable[[GFMParameters, GFMCalculator], Optional[float]]


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
        lambda p, c: p.get_initial_frequency() * p.get_nominal_frequency(),
    ),
    _PlotParameter(
        "RoCoF",
        "RoCoF = {:.3f} Hz/s",
        lambda p, c: p.get_change_frequency() * p.get_nominal_frequency(),
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
class _Calculation:
    """
    What a calculation of a set of D and H gives: the expected signal and the envelopes around
    it.
    """

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
        producer_name: str,
    ) -> GFMTestReport:
        """
        Obtains the envelopes of an operating condition and writes them, with the figures and,
        when the producer curves are given, their check, under working_path.

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
        producer_name : str
            The name of the producer, that of the directory holding its curves.

        Returns
        -------
        GFMTestReport
            What the report shows of the test: its parameters and, when the producer curves are
            given, their compliance and checks.
        """
        parameters.set_section(pcs_name, bm_name, oc_name)
        title = f"{pcs_name}.{bm_name}.{oc_name}"

        try:
            envelopes = self._obtain_envelopes(working_path, parameters, pcs_name, title)
            compliance = Compliance.WithoutEnvelopes
        except (ValueError, configparser.Error) as e:
            LOGGER.error(f"The envelopes of {title} cannot be obtained. {e}")
            envelopes = None
            compliance = Compliance.InvalidTest
        if envelopes is None:
            return GFMTestReport(
                producer_name=producer_name,
                pcs=pcs_name,
                benchmark=bm_name,
                operating_condition=oc_name,
                magnitude="",
                parameters=[],
                compliance=compliance,
                envelope=None,
                modes=[],
            )

        curves_check = self._check_producer_curves(
            working_path, parameters, producer_name, title, envelopes
        )
        producer_signal = curves_check.signal if curves_check else None

        self._export_csv(working_path, title, envelopes, producer_signal)
        save_results(working_path / "results.json", envelopes, curves_check)
        self._plot(working_path, title, envelopes, producer_signal)

        return GFMTestReport(
            producer_name=producer_name,
            pcs=pcs_name,
            benchmark=bm_name,
            operating_condition=oc_name,
            magnitude=envelopes.magnitude,
            parameters=envelopes.parameters,
            compliance=curves_check.compliance if curves_check else None,
            envelope=curves_check.envelope if curves_check else None,
            modes=curves_check.modes if curves_check else [],
        )

    def _obtain_envelopes(
        self, working_path: Path, parameters: GFMParameters, pcs_name: str, title: str
    ) -> Optional[Envelopes]:
        """
        Obtains the envelopes of the test: read from the directory of envelopes given, or else
        calculated from the parameters of the unit.

        Parameters
        ----------
        working_path : Path
            The directory path for intermediate and final outputs.
        parameters : GFMParameters
            The parsed parameter configuration object.
        pcs_name : str
            The name of the PCS.
        title : str
            The name of the test.

        Returns
        -------
        Optional[Envelopes]
            The envelopes of the test, None when the directory given lacks them or when the unit
            declares no parameters to calculate them.
        """
        envelopes_path = parameters.get_envelopes_path()
        if envelopes_path is None:
            if not parameters.declares_unit_parameters():
                return None
            return self._calculate_test_envelopes(working_path, parameters, pcs_name, title)

        test_path = envelopes_path.joinpath(*title.split("."))
        try:
            envelopes = read_envelopes(test_path, title)
        except (OSError, ValueError, KeyError) as e:
            LOGGER.error(f"The envelopes in '{test_path}' cannot be read. {e}")
            return None
        if envelopes is None:
            LOGGER.warning(f"No envelopes for the test in '{test_path}'")
        return envelopes

    def _calculate_test_envelopes(
        self, working_path: Path, parameters: GFMParameters, pcs_name: str, title: str
    ) -> Envelopes:
        """
        Calculates the envelopes of the test from the parameters of the unit, writing the
        simulation dump of each set of D and H.

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
        title : str
            The name of the test.

        Returns
        -------
        Envelopes
            The envelopes of the test.

        Raises
        ------
        ValueError
            If neither one set of D and H nor the overdamped and underdamped sets are given.
        """
        x_eff = parameters.get_effective_reactance()

        calculator_name = parameters.get_calculator_name()
        calculator = calculator_factory.get_calculator(calculator_name, parameters)

        time_array, event_time = self._get_time(calculator_name)
        params_list = calculator.get_plot_parameter_names() if calculator else None

        hybrid_params = parameters.get_hybrid_parameters()
        standard_params = parameters.get_standard_parameters()

        if hybrid_params:
            LOGGER.info(
                f"Hybrid parameters detected for {pcs_name}. Running Merged Envelope generation."
            )
            calculation = self._calculate_hybrid_envelopes(
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
            calculation = self._calculate_envelopes(
                calculator, time_array, event_time, d_val, h_val, x_eff
            )
            self._save_dump(working_path / f"{title}_ini_dump.txt", parameters, calculator)
        else:
            error_msg = (
                f"Configuration Error in {pcs_name}: Neither standard parameters (D, H) "
                "nor hybrid parameters are defined in the Producer.ini."
            )
            LOGGER.error(error_msg)
            raise ValueError(error_msg)

        pcc_signal = calculation.pcc_signal
        lower_envelope = calculation.lower_envelope
        upper_envelope = calculation.upper_envelope
        max_current = parameters.get_max_current()
        if max_current is not None:
            # The DTR Fiche I18 bounds every envelope by the short-duration maximum current
            pcc_signal, lower_envelope, upper_envelope = (
                np.clip(signal, -max_current, max_current)
                for signal in (pcc_signal, lower_envelope, upper_envelope)
            )

        return Envelopes(
            magnitude=calculation.magnitude_name,
            emt=parameters.is_emt(),
            time=time_array,
            event_time=event_time,
            event_duration=calculator.get_event_duration(),
            response=pcc_signal,
            lower=lower_envelope,
            upper=upper_envelope,
            extra=calculation.extra_envelopes,
            parameters=self._get_params_plot_info(parameters, params_list, calculator),
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
    ) -> _Calculation:
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
        _Calculation
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
        return _Calculation(
            over.magnitude_name,
            over.pcc_signal,
            upper_envelope,
            lower_envelope,
            extra_envelopes,
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

    def _check_producer_curves(
        self,
        working_path: Path,
        parameters: GFMParameters,
        producer_name: str,
        title: str,
        envelopes: Envelopes,
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
        envelopes : Envelopes
            The envelopes of the test.

        Returns
        -------
        Optional[curves_compliance.CurvesCheck]
            The result of the check, None when no producer curves are given.
        """
        curves_path = parameters.get_producer_curves_path()
        if curves_path is None:
            return None

        try:
            return curves_compliance.check(
                curves_path / producer_name,
                working_path,
                title,
                envelopes.magnitude,
                envelopes.time,
                envelopes.event_time,
                envelopes.event_duration,
                envelopes.lower,
                envelopes.upper,
            )
        except (OSError, ValueError, TypeError, KeyError, configparser.Error) as e:
            # The envelopes are still delivered: only the producer curves cannot be judged
            LOGGER.error(f"The producer curves of {title} cannot be checked. {e}")
            return curves_compliance.CurvesCheck(Compliance.InvalidTest, None, None, [])

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
    ) -> _Calculation:
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
        _Calculation
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
        return _Calculation(magnitude_name, pcc_signal, upper_envelope, lower_envelope)

    def _export_csv(
        self,
        csv_path: Path,
        title: str,
        envelopes: Envelopes,
        producer_signal: np.ndarray = None,
    ) -> None:
        """
        Exports the envelopes to a CSV file.

        Parameters
        ----------
        csv_path : Path
            The directory path to save the CSV.
        title : str
            The file name for the CSV (without extension).
        envelopes : Envelopes
            The envelopes of the test.
        producer_signal : np.ndarray, optional
            The filtered producer curve on the same time values.
        """
        save_results_to_csv(
            path=csv_path / f"{title}.csv",
            magnitude=envelopes.magnitude,
            time_array=envelopes.time,
            pcc_signal=envelopes.response,
            lower_envelope=envelopes.lower,
            upper_envelope=envelopes.upper,
            extra_envelopes=envelopes.extra,
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
            A list of formatted string lines for display on plots, leaving out a parameter the
            test does not give (such as the D and H a hybrid producer does not set), and the
            maximum current when the producer gives one.
        """
        if params_list is None:
            return []
        lines = []
        for parameter in _PLOT_PARAMETERS:
            if parameter.name not in params_list:
                continue
            value = parameter.value(parameters, calculator)
            if value is not None:
                lines.append(parameter.text.format(value))
        max_current = parameters.get_max_current()
        if max_current is not None:
            lines.append(f"Imax = {max_current:.3f} pu")
        return lines

    def _plot(
        self,
        png_path: Path,
        title: str,
        envelopes: Envelopes,
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
        envelopes : Envelopes
            The envelopes of the test.
        producer_signal : np.ndarray, optional
            The filtered producer curve on the same time values.
        """
        plot_results(
            path=png_path / f"{title}.png",
            title=title,
            magnitude=envelopes.magnitude,
            time_array=envelopes.time,
            event_time=envelopes.event_time,
            shift_time=0,
            pcc_signal=envelopes.response,
            lower_envelope=envelopes.lower,
            upper_envelope=envelopes.upper,
            output_format="png&html",
            params_list=envelopes.parameters,
            extra_envelopes=envelopes.extra,
            producer_signal=producer_signal,
        )
