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

from dycov.gfm.outputs import plot_results, save_results_to_csv
from dycov.gfm.parameters import GFMParameters
from dycov.gfm.phase_jump import PhaseJump


class GridForming:
    def __init__(self, parameters: GFMParameters):
        self._parameters = parameters

    def generate(self, working_path: Path, pcs_name: str, bm_name: str, oc_name: str):
        gfm_params = self._parameters.pcs_configuration(pcs_name, bm_name, oc_name)
        print(f"GFM Params {gfm_params}")
        time_array, event_time = self._get_time()
        damping_constant = self._parameters.get_damping_constant()
        inertia_constant = self._parameters.get_inertia_constant()
        x_eff = self._parameters.get_effective_reactance(pcs_name, bm_name, oc_name)
        print(f"Input Params D={damping_constant} H={inertia_constant} Xeff {x_eff}")
        title, p_pcc, p_up, p_down = self._phase_jump(
            gfm_params, time_array, event_time, damping_constant, inertia_constant, x_eff
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

    def _phase_jump(
        self, gfm_params, time_array, event_time, damping_constant, inertia_constant, x_eff
    ):

        phase_jump = PhaseJump(gfm_params=gfm_params)
        (
            is_overdamped,
            delta_p_array,
            delta_p_min,
            delta_p_max,
            p_peak_array,
            _,
        ) = phase_jump.get_delta_p(
            D=damping_constant,
            H=inertia_constant,
            Xeff=x_eff,
            time_array=time_array,
            event_time=event_time,
        )

        p_pcc, p_up, p_down = phase_jump.get_envelopes(
            delta_p_array=delta_p_array,
            delta_p_min=delta_p_min,
            delta_p_max=delta_p_max,
            p_peak_array=p_peak_array,
            time_array=time_array,
            event_time=event_time,
        )

        title = "Overdamped_PhaseJump" if is_overdamped else "Underdamped_PhaseJump"
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
