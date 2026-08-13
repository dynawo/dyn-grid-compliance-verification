#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import numpy as np
from dycov.gfm import constants
from dycov.gfm.calculators import calculator_factory
from dycov.gfm.calculators.gfm_calculator import GFMCalculator
from dycov.gfm.outputs import plot_results, save_ini_dump, save_results_to_csv
from dycov.gfm.parameters import GFMParameters
from dycov.logging.logging import dycov_logging

LOGGER = dycov_logging.get_logger(name=__name__)


class GridForming:
    def _merge_hybrid_envelopes(
        self,
        up_over: np.ndarray,
        low_over: np.ndarray,
        up_under: np.ndarray,
        low_under: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Parameters
        ----------
        up_over : np.ndarray
        low_over : np.ndarray
        up_under : np.ndarray
        low_under : np.ndarray

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
        """
        upper_envelope1 = np.maximum(up_over, up_under)
        lower_envelope1 = np.minimum(low_over, low_under)
        upper_envelope2 = np.maximum(low_over, low_under)
        lower_envelope2 = np.minimum(up_over, up_under)
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
        Parameters
        ----------
        working_path : Path
        parameters : GFMParameters
        pcs_name : str
        bm_name : str
        oc_name : str
        """
        parameters.set_section(pcs_name=pcs_name, bm_name=bm_name, oc_name=oc_name)
        x_eff = parameters.get_effective_reactance()
        calculator_name = parameters.get_calculator_name()
        calculator = calculator_factory.get_calculator(name=calculator_name, gfm_params=parameters)
        time_array, event_time = self._get_time(calculator_name=calculator_name)
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
                msg=f"Hybrid parameters detected for {pcs_name}. Running Merged Envelope generation."
            )
            d_over, h_over, d_under, h_under = hybrid_params
            mag_name, pcc_over, up_over, low_over = self._calculate_envelopes(
                calculator=calculator,
                time_array=time_array,
                event_time=event_time,
                damping_constant=d_over,
                inertia_constant=h_over,
                x_eff=x_eff,
            )
            producer = parameters.get_producer()
            producer_config = producer.get_config() if producer else None
            save_ini_dump(
                path=working_path / f"{title}_ini_dump_overdamped.txt",
                parameters=parameters,
                producer_config=producer_config,
                calculator=calculator,
            )
            _, pcc_under, up_under, low_under = self._calculate_envelopes(
                calculator=calculator,
                time_array=time_array,
                event_time=event_time,
                damping_constant=d_under,
                inertia_constant=h_under,
                x_eff=x_eff,
            )
            save_ini_dump(
                path=working_path / f"{title}_ini_dump_underdamped.txt",
                parameters=parameters,
                producer_config=producer_config,
                calculator=calculator,
            )
            upper_envelope, lower_envelope = self._merge_hybrid_envelopes(
                up_over=up_over, low_over=low_over, up_under=up_under, low_under=low_under
            )
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
                params_list = [p for p in params_list if p not in ["D", "H"]]
        elif standard_params:
            LOGGER.debug(msg=f"Standard parameters (D, H) detected for {pcs_name}.")
            d_val, h_val = standard_params
            magnitude_name, pcc_signal, upper_envelope, lower_envelope = self._calculate_envelopes(
                calculator=calculator,
                time_array=time_array,
                event_time=event_time,
                damping_constant=d_val,
                inertia_constant=h_val,
                x_eff=x_eff,
            )
        else:
            error_msg = (
                f"Configuration Error in {pcs_name}: Parameters D, H or hybrid not defined."
            )
            LOGGER.error(msg=error_msg)
            raise ValueError(error_msg)

        is_inconsistent = calculator.is_inconsistent
        disclaimer_msg = calculator.disclaimer_message
        self._export_csv(
            csv_path=working_path,
            title=title,
            magnitude_name=magnitude_name,
            time_array=time_array,
            pcc_signal=pcc_signal,
            lower_envelope=lower_envelope,
            upper_envelope=upper_envelope,
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
            png_path=working_path,
            title=title,
            magnitude_name=magnitude_name,
            time_array=time_array,
            event_time=event_time,
            pcc_signal=pcc_signal,
            lower_envelope=lower_envelope,
            upper_envelope=upper_envelope,
            parameters=parameters,
            params_list=params_list,
            calculator=calculator,
            is_inconsistent=is_inconsistent,
            disclaimer_msg=disclaimer_msg,
            extra_envelopes=extra_envelopes,
        )

    def _get_time(self, calculator_name: str) -> tuple[np.ndarray, float]:
        """
        Parameters
        ----------
        calculator_name : str

        Returns
        -------
        tuple[np.ndarray, float]
        """
        start_time = (
            constants.SIMULATION_START_TIME_EXTENDED
            if calculator_name in ["SCRJump", "RoCoF"]
            else constants.SIMULATION_START_TIME_DEFAULT
        )
        time_array = np.linspace(
            start=start_time, stop=constants.SIMULATION_END_TIME, num=constants.SIMULATION_POINTS
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
        Parameters
        ----------
        calculator : GFMCalculator
        time_array : np.ndarray
        event_time : float
        damping_constant : float
        inertia_constant : float
        x_eff : float

        Returns
        -------
        tuple[str, np.ndarray, np.ndarray, np.ndarray]
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
        """
        Parameters
        ----------
        csv_path : Path
        title : str
        magnitude_name : str
        time_array : np.ndarray
        pcc_signal : np.ndarray
        lower_envelope : np.ndarray
        upper_envelope : np.ndarray
        extra_envelopes : dict, optional
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
        Parameters
        ----------
        parameters : GFMParameters
        params_list : list
        calculator : GFMCalculator

        Returns
        -------
        list[str]
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
        """
        Parameters
        ----------
        png_path : Path
        title : str
        magnitude_name : str
        time_array : np.ndarray
        event_time : float
        pcc_signal : np.ndarray
        lower_envelope : np.ndarray
        upper_envelope : np.ndarray
        parameters : GFMParameters
        params_list : list
        calculator : GFMCalculator
        is_inconsistent : bool, optional
        disclaimer_msg : str, optional
        extra_envelopes : dict, optional
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
            params_list=self._get_params_plot_info(
                parameters=parameters, params_list=params_list, calculator=calculator
            ),
            show_disclaimer=is_inconsistent,
            disclaimer_message=disclaimer_msg,
            extra_envelopes=extra_envelopes,
        )
