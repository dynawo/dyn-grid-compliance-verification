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
from dycov.gfm.outputs import plot_results, save_results_to_csv
from dycov.gfm.parameters import GFMParameters
from dycov.logging.logging import dycov_logging


class GridForming:
    def __init__(self, parameters: GFMParameters, pcs_name: str, bm_name: str, oc_name: str):
        self._parameters = parameters
        self._pcs_name = pcs_name
        self._bm_name = bm_name
        self._oc_name = oc_name

    def generate(self, working_path: Path, pcs_name: str, bm_name: str, oc_name: str):
        gfm_params = self._parameters.pcs_configuration(pcs_name, bm_name, oc_name)
        dycov_logging.get_logger("GridForming").debug(f"GFM Params {gfm_params}")
        time_array, event_time = self._get_time()
        damping_constant = self._parameters.get_damping_constant()
        inertia_constant = self._parameters.get_inertia_constant()
        x_eff = self._parameters.get_effective_reactance(pcs_name, bm_name, oc_name)
        dycov_logging.get_logger("GridForming").debug(
            f"Input Params D={damping_constant} H={inertia_constant} Xeff {x_eff}"
        )
        calculator = calculator_factory.get_calculator(gfm_params, pcs_name, bm_name)
        title, p_pcc, p_up, p_down = self._calculate_envelopes(
            calculator, time_array, event_time, damping_constant, inertia_constant, x_eff
        )
        self._export_csv(working_path, title, time_array, p_pcc, p_down, p_up)
        self._plot(working_path, title, time_array, event_time, p_pcc, p_down, p_up)

    def _get_time(self):
        start_time = 0
        end_time = 10
        event_time = 0
        nb_points = 2000
        time_array = np.linspace(start_time, end_time, nb_points)

        return time_array, event_time

    def _calculate_envelopes(
        self, calculator, time_array, event_time, damping_constant, inertia_constant, x_eff
    ):

        (
            is_overdamped,
            p_pcc,
            p_up,
            p_down,
        ) = calculator.calculate_envelopes(
            D=damping_constant,
            H=inertia_constant,
            Xeff=x_eff,
            time_array=time_array,
            event_time=event_time,
        )

        title = f"{self._pcs_name}.{self._bm_name}.{self._oc_name}"
        title += f".{'Overdamped' if is_overdamped else 'Underdamped'}"
        return title, p_pcc, p_up, p_down

    def _export_csv(self, working_path, title, time_array, p_pcc, p_down, p_up):
        csv_path = working_path / "CSVResults"
        csv_path.mkdir(parents=True, exist_ok=True)

        save_results_to_csv(csv_path / f"{title}.csv", time_array, p_pcc, p_down, p_up)

    def _plot(self, working_path, title, time_array, event_time, p_pcc, p_down, p_up):
        png_path = working_path / "PNGResults"
        png_path.mkdir(parents=True, exist_ok=True)
        plot_results(
            png_path / f"{title}.png",
            title,
            time_array,
            event_time,
            0,
            p_pcc,
            p_down,
            p_up,
        )
