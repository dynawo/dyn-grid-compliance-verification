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
from dycov.gfm.phase_jump import GFM_Params, PhaseJump

# Float tolerance
epsilon = 1e-9

gfm_overdamped_params = GFM_Params(
    P0=0.5,
    delta_theta=-5.0,
    SCR=2.0,
    EMT=True,
    RatioMin=0.9,
    RatioMax=1.1,
    Wb=314,
    Ucv=1.0,
    Ugr=1.0,
    MarginHigh=0.5,
    MarginLow=0.5,
    FinalAllowedTunnelVariation=0.05,
    FinalAllowedTunnelPn=0.02,
    PMax=1.1,
    PMin=-1.1,
)


gfm_underdamped_params = GFM_Params(
    P0=0.8,
    delta_theta=-8.0,
    SCR=10.0,
    EMT=True,
    RatioMin=0.8,
    RatioMax=1.2,
    Wb=314,
    Ucv=1.0,
    Ugr=1.0,
    MarginHigh=0.2,
    MarginLow=0.5,
    FinalAllowedTunnelVariation=0.05,
    FinalAllowedTunnelPn=0.02,
    PMax=1.1,
    PMin=-1.1,
)


s_vol_ang_step_1_params = GFM_Params(
    P0=0.55,  # 0.5*PMax
    delta_theta=5.15,  # +θ_jump
    SCR=10.0,  # SCR_max
    EMT=True,
    RatioMin=0.9,
    RatioMax=1.1,
    Wb=314,
    Ucv=1.0,
    Ugr=1.0,
    MarginHigh=0.5,
    MarginLow=0.5,
    FinalAllowedTunnelVariation=0.05,
    FinalAllowedTunnelPn=0.02,
    PMax=1.1,
    PMin=-1.1,
)


def test_phase_jump_initialization():
    phase_jump = PhaseJump(gfm_params=gfm_overdamped_params)

    assert phase_jump._gfm_params == gfm_overdamped_params

    phase_jump = PhaseJump(gfm_params=gfm_underdamped_params)

    assert phase_jump._gfm_params == gfm_underdamped_params


def test_phase_jump_overdamped_envelopes_event_at_0s():

    start_time = 0
    end_time = 1.315
    event_time = 0
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    phase_jump = PhaseJump(gfm_params=gfm_overdamped_params)
    (
        _,
        delta_p_array,
        delta_p_min,
        delta_p_max,
        p_peak_array,
        _,
    ) = phase_jump.get_delta_p(
        D=152.0, H=3.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    p_pcc, p_up, p_down = phase_jump.get_envelopes(
        delta_p_array=delta_p_array,
        delta_p_min=delta_p_min,
        delta_p_max=delta_p_max,
        p_peak_array=p_peak_array,
        time_array=time_array,
        event_time=event_time,
    )

    title = "Overdamped_PhaseJump_DeltaP_0s"
    csv_path = Path(__file__).parent / "CSVResults"
    csv_path.mkdir(parents=True, exist_ok=True)

    save_results_to_csv(csv_path / f"{title}.csv", time_array, p_pcc, p_down, p_up)

    png_path = Path(__file__).parent / "PNGResults"
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

    assert len(p_down) == nb_points
    assert abs(p_down[0] - np.float64(0.5013787821149449)) < epsilon
    assert abs(p_down[-1] - np.float64(0.4804503537321287)) < epsilon

    assert len(p_up) == nb_points
    assert abs(p_up[0] - np.float64(0.7323706712771527)) < epsilon
    assert abs(p_up[-1] - np.float64(0.5209853573483934)) < epsilon


def test_phase_jump_overdamped_envelopes_event_at_200ms():

    start_time = 0
    end_time = 1.315
    event_time = 0.2
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    phase_jump = PhaseJump(gfm_params=gfm_overdamped_params)
    (
        _,
        delta_p_array,
        delta_p_min,
        delta_p_max,
        p_peak_array,
        _,
    ) = phase_jump.get_delta_p(
        D=152.0, H=3.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    p_pcc, p_up, p_down = phase_jump.get_envelopes(
        delta_p_array=delta_p_array,
        delta_p_min=delta_p_min,
        delta_p_max=delta_p_max,
        p_peak_array=p_peak_array,
        time_array=time_array,
        event_time=event_time,
    )

    title = "Overdamped_PhaseJump_DeltaP_event"
    csv_path = Path(__file__).parent / "CSVResults"
    csv_path.mkdir(parents=True, exist_ok=True)

    save_results_to_csv(csv_path / f"{title}.csv", time_array, p_pcc, p_down, p_up)

    png_path = Path(__file__).parent / "PNGResults"
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

    assert len(p_down) == nb_points
    assert abs(p_down[0] - np.float64(0.5)) < epsilon
    assert abs(p_down[-1] - np.float64(0.4804503537321287)) < epsilon

    assert len(p_up) == nb_points
    assert abs(p_up[0] - np.float64(0.5)) < epsilon
    assert abs(p_up[-1] - np.float64(0.5209853573483934)) < epsilon


def test_phase_jump_underdamped_envelopes_event_at_0s():

    start_time = 0
    end_time = 1.315
    event_time = 0
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    phase_jump = PhaseJump(gfm_params=gfm_underdamped_params)
    (
        _,
        delta_p_array,
        delta_p_min,
        delta_p_max,
        p_peak_array,
        _,
    ) = phase_jump.get_delta_p(
        D=200.0, H=10.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    p_pcc, p_up, p_down = phase_jump.get_envelopes(
        delta_p_array=delta_p_array,
        delta_p_min=delta_p_min,
        delta_p_max=delta_p_max,
        p_peak_array=p_peak_array,
        time_array=time_array,
        event_time=event_time,
    )

    title = "Underdamped_PhaseJump_DeltaP_0s"
    csv_path = Path(__file__).parent / "CSVResults"
    csv_path.mkdir(parents=True, exist_ok=True)

    save_results_to_csv(csv_path / f"{title}.csv", time_array, p_pcc, p_down, p_up)

    png_path = Path(__file__).parent / "PNGResults"
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

    assert len(p_down) == nb_points
    assert abs(p_down[0] - np.float64(0.803008035946675)) < epsilon
    assert abs(p_down[-1] - np.float64(0.7564723505574613)) < epsilon

    assert len(p_up) == nb_points
    assert abs(p_up[0] - np.float64(1.1)) < epsilon
    assert abs(p_up[-1] - np.float64(0.8447078551626718)) < epsilon


def test_phase_jump_underdamped_envelopes_event_at_200ms():

    start_time = 0
    end_time = 1.315
    event_time = 0.2
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    phase_jump = PhaseJump(gfm_params=gfm_underdamped_params)
    (
        _,
        delta_p_array,
        delta_p_min,
        delta_p_max,
        p_peak_array,
        _,
    ) = phase_jump.get_delta_p(
        D=200.0, H=10.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    p_pcc, p_up, p_down = phase_jump.get_envelopes(
        delta_p_array=delta_p_array,
        delta_p_min=delta_p_min,
        delta_p_max=delta_p_max,
        p_peak_array=p_peak_array,
        time_array=time_array,
        event_time=event_time,
    )

    title = "Underdamped_PhaseJump_DeltaP_event"
    csv_path = Path(__file__).parent / "CSVResults"
    csv_path.mkdir(parents=True, exist_ok=True)

    save_results_to_csv(csv_path / f"{title}.csv", time_array, p_pcc, p_down, p_up)

    png_path = Path(__file__).parent / "PNGResults"
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

    assert len(p_down) == nb_points
    assert abs(p_down[0] - np.float64(0.8)) < epsilon
    assert abs(p_down[-1] - np.float64(0.7564723505574613)) < epsilon

    assert len(p_up) == nb_points
    assert abs(p_up[0] - np.float64(0.8)) < epsilon
    assert abs(p_up[-1] - np.float64(0.8447078551626718)) < epsilon


def test_s_vol_ang_step_1_phase_jump():

    start_time = 0
    end_time = 10
    event_time = 0
    nb_points = 2000
    time_array = np.linspace(start_time, end_time, nb_points)

    phase_jump = PhaseJump(gfm_params=s_vol_ang_step_1_params, debug=True)
    (
        overdamped,
        delta_p_array,
        delta_p_min,
        delta_p_max,
        p_peak_array,
        _,
    ) = phase_jump.get_delta_p(
        D=133.0, H=10.0, Xeff=0.25, time_array=time_array, event_time=event_time
    )
    print(f"It's an {'overdamped' if overdamped else 'underdamped'} system")

    p_pcc, p_up, p_down = phase_jump.get_envelopes(
        delta_p_array=delta_p_array,
        delta_p_min=delta_p_min,
        delta_p_max=delta_p_max,
        p_peak_array=p_peak_array,
        time_array=time_array,
        event_time=event_time,
    )

    title = "S_VolAngStep1_OC2"
    csv_path = Path(__file__).parent / "CSVResults"
    csv_path.mkdir(parents=True, exist_ok=True)

    save_results_to_csv(csv_path / f"{title}.csv", time_array, p_pcc, p_down, p_up)

    png_path = Path(__file__).parent / "PNGResults"
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

    assert len(p_down) == nb_points
    assert abs(p_down[0] - np.float64(0.5486212178850551)) < epsilon
    assert abs(p_down[-1] - np.float64(0.5700000000000003)) < epsilon

    assert len(p_up) == nb_points
    assert abs(p_up[0] - np.float64(0.16615968292476785)) < epsilon
    assert abs(p_up[-1] - np.float64(0.5299999999997788)) < epsilon
