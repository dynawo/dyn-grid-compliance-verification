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

from dycov.gfm.phase_jump import BaseGFM_Values, GFM_Params, PhaseJump

gfm_overdamped_params = GFM_Params(
    EMT=True,
    RatioMin=0.9,
    RatioMax=1.1,
    P0=0.5,
    delta_theta=-5.0,
    SCR=2.0,
    Xtr=0.06,
    Wb=314,
    Ucv=1,
    Ugr=1.0,
    MarginHigh=0.5,
    MarginLow=0.5,
    FinalAllowedTunnelVariation=0.05,
    FinalAllowedTunnelPn=0.02,
    PMax=1.1,
)

gfm_underdamped_params = GFM_Params(
    EMT=True,
    RatioMin=0.8,
    RatioMax=1.2,
    P0=0.8,
    delta_theta=-8.0,
    SCR=10.0,
    Xtr=0.06,
    Wb=314,
    Ucv=1,
    Ugr=1.0,
    MarginHigh=0.2,
    MarginLow=0.5,
    FinalAllowedTunnelVariation=0.05,
    FinalAllowedTunnelPn=0.02,
    PMax=1.1,
)

gfm_overdamped_values = BaseGFM_Values(
    D_array=np.array([152.0, 136.8, 167.20000000000002]),
    H_array=np.array([3.0, 3.333333333333333, 2.727272727272727]),
    delta_theta_array=np.array(
        [
            0.08726646259971647,
            0.08726646259971647,
            0.08726646259971647,
        ]
    ),
    Xgr_array=np.array([0.5, 0.5, 0.5]),
    Xtot_array=np.array([0.56, 0.56, 0.56]),
    Ts_array=np.array(
        [
            0.27108280254777073,
            0.24397452229299368,
            0.29819108280254786,
        ]
    ),
    Sigma_array=np.array(
        [
            12.66666667,
            10.26,
            15.32666667,
        ]
    ),
    Wn_array=np.array([9.667077166981805, 9.170994649281116, 10.138916068674158]),
    Tunnel_array=np.array([0.02, 0.02, 0.02]),
    epsilon_array=np.array(
        [
            1.3102891854354954,
            1.1187445192549805,
            1.5116671804810495,
        ]
    ),
    wd_array=np.array([8.184867958132463, 4.600049689172624, 11.493871935231063]),
    a_array=np.array([20.85153462479913, 14.860049689172627, 26.820538601897734]),
    b_array=np.array([4.481798708534203, 5.659950310827377, 3.832794731435609]),
    A_array=np.array(
        [
            -0.061088340405443115,
            -0.10869447805680793,
            -0.043501441708898636,
        ]
    ),
    B_array=np.array(
        [
            0.061088340405443115,
            0.10869447805680793,
            0.043501441708898636,
        ]
    ),
    Ppeak_array=np.array(
        [
            0.1558329689280651,
            0.1558329689280651,
            0.1558329689280651,
        ]
    ),
    is_overdamped_global=True,
)

gfm_underdamped_values = BaseGFM_Values(
    D_array=np.array([200.0, 160.0, 240.0]),
    H_array=np.array([10.0, 12.5, 8.3333333]),
    delta_theta_array=np.array([0.13962634, 0.13962634, 0.13962634]),
    Xgr_array=np.array([0.1, 0.1, 0.1]),
    Xtot_array=np.array([0.16, 0.16, 0.16]),
    Ts_array=np.array([0.10191083, 0.08152866, 0.12229299]),
    Sigma_array=np.array([5.0, 3.2, 7.2]),
    Wn_array=np.array([9.905806378, 8.860022573, 10.85126721]),
    Tunnel_array=np.array([0.04363323, 0.04363323, 0.04363323]),
    epsilon_array=np.array([0.504754465, 0.361172895, 0.663516976]),
    wd_array=np.array([8.551315688, 8.26196103, 8.1184974]),
    a_array=np.array([-5.0 + 8.55131569j, -3.2 + 8.26196103j, -7.2 + 8.1184974j]),
    b_array=np.array([-5.0 - 8.55131569j, -3.2 - 8.26196103j, -7.2 - 8.1184974j]),
    A_array=np.array([-0.0 + 0.05847053j, -0.0 + 0.06051832j, -0.0 + 0.06158775j]),
    B_array=np.array([0.0 - 0.05847053j, 0.0 - 0.06051832j, 0.0 - 0.06158775j]),
    Ppeak_array=np.array([0.872664626, 0.872664626, 0.872664626]),
    is_overdamped_global=False,
)


def test_phase_jump_initialization():
    phase_jump = PhaseJump(gfm_params=gfm_overdamped_params)

    assert phase_jump._gfm_params == gfm_overdamped_params
    assert not phase_jump._base_values
    assert not phase_jump._theoretical_response_from_vsm
    assert not phase_jump._pdown
    assert not phase_jump._pup


def test_phase_jump_overdamped_base_values():
    phase_jump = PhaseJump(gfm_params=gfm_overdamped_params)
    phase_jump.calculate_base_values(D=152.0, H=3.0, Xeff=0)
    base_values = phase_jump.get_base_values()

    assert np.allclose(base_values.D_array, gfm_overdamped_values.D_array)
    assert np.allclose(base_values.H_array, gfm_overdamped_values.H_array)
    assert np.allclose(base_values.delta_theta_array, gfm_overdamped_values.delta_theta_array)
    assert np.allclose(base_values.Xgr_array, gfm_overdamped_values.Xgr_array)
    assert np.allclose(base_values.Xtot_array, gfm_overdamped_values.Xtot_array)
    assert np.allclose(base_values.Ts_array, gfm_overdamped_values.Ts_array)
    assert np.allclose(base_values.Sigma_array, gfm_overdamped_values.Sigma_array)
    assert np.allclose(base_values.Wn_array, gfm_overdamped_values.Wn_array)
    assert np.allclose(base_values.Tunnel_array, gfm_overdamped_values.Tunnel_array)
    assert np.allclose(base_values.epsilon_array, gfm_overdamped_values.epsilon_array)
    assert np.allclose(base_values.wd_array, gfm_overdamped_values.wd_array)
    assert np.allclose(base_values.Ppeak_array, gfm_overdamped_values.Ppeak_array)


def test_phase_jump_overdamped_envelopes():

    start_time = 0
    end_time = 1.315
    event_time = 0
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)  # From Start_Time to End_Time

    phase_jump = PhaseJump(gfm_params=gfm_overdamped_params)
    phase_jump.calculate_base_values(D=152.0, H=3.0, Xeff=0)
    phase_jump.calculate_envelopes(time_array, event_time)
    pdown = phase_jump.get_pdown()
    pup = phase_jump.get_pup()

    title = "OverDamped_PhaseJump_0s"
    csv_path = Path(__file__).parent / "CSVResults"
    csv_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    phase_jump.save_results_to_csv(csv_path / f"{title}.csv", time_array)

    png_path = Path(__file__).parent / "PNGResults"
    png_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    phase_jump.plot_results(
        png_path / f"{title}.png",
        time_array,
        event_time,
        0,
        title,
    )

    assert len(pdown) == nb_points
    assert pdown[0] == np.float64(0.5013787821149449)
    assert pdown[-1] == np.float64(0.4804503537321287)

    assert len(pup) == nb_points
    assert pup[0] == np.float64(0.7323706712771527)
    assert pup[-1] == np.float64(0.5209853573483934)


def test_phase_jump_overdamped_envelopes_event_at_200ms():

    start_time = 0
    end_time = 1.315
    event_time = 0.2
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)  # From Start_Time to End_Time

    phase_jump = PhaseJump(gfm_params=gfm_overdamped_params)
    phase_jump.calculate_base_values(D=152.0, H=3.0, Xeff=0)
    phase_jump.calculate_envelopes(time_array, event_time)
    pdown = phase_jump.get_pdown()
    pup = phase_jump.get_pup()

    title = "OverDamped_PhaseJump_event"
    csv_path = Path(__file__).parent / "CSVResults"
    csv_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    phase_jump.save_results_to_csv(csv_path / f"{title}.csv", time_array)

    png_path = Path(__file__).parent / "PNGResults"
    png_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    phase_jump.plot_results(
        png_path / f"{title}.png",
        time_array,
        event_time,
        0,
        title,
    )

    assert len(pdown) == nb_points
    assert pdown[0] == np.float64(0.5)
    assert pdown[-1] == np.float64(0.4804503537321287)

    assert len(pup) == nb_points
    assert pup[0] == np.float64(0.5)
    assert pup[-1] == np.float64(0.5209853573483934)


def test_phase_jump_underdamped_base_values():
    phase_jump = PhaseJump(gfm_params=gfm_underdamped_params)
    phase_jump.calculate_base_values(D=200.0, H=10.0, Xeff=0)
    base_values = phase_jump.get_base_values()

    assert np.allclose(base_values.D_array, gfm_underdamped_values.D_array)
    assert np.allclose(base_values.H_array, gfm_underdamped_values.H_array)
    assert np.allclose(base_values.delta_theta_array, gfm_underdamped_values.delta_theta_array)
    assert np.allclose(base_values.Xgr_array, gfm_underdamped_values.Xgr_array)
    assert np.allclose(base_values.Xtot_array, gfm_underdamped_values.Xtot_array)
    assert np.allclose(base_values.Ts_array, gfm_underdamped_values.Ts_array)
    assert np.allclose(base_values.Sigma_array, gfm_underdamped_values.Sigma_array)
    assert np.allclose(base_values.Wn_array, gfm_underdamped_values.Wn_array)
    assert np.allclose(base_values.Tunnel_array, gfm_underdamped_values.Tunnel_array)
    assert np.allclose(base_values.epsilon_array, gfm_underdamped_values.epsilon_array)
    assert np.allclose(base_values.wd_array, gfm_underdamped_values.wd_array)
    assert np.allclose(base_values.Ppeak_array, gfm_underdamped_values.Ppeak_array)


def test_phase_jump_underdamped_envelopes():

    start_time = 0
    end_time = 1.315
    event_time = 0
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)  # From Start_Time to End_Time

    phase_jump = PhaseJump(gfm_params=gfm_underdamped_params)
    phase_jump.calculate_base_values(D=200.0, H=10.0, Xeff=0)
    phase_jump.calculate_envelopes(time_array, event_time)
    pdown = phase_jump.get_pdown()
    pup = phase_jump.get_pup()

    title = "Underdamped_PhaseJump_0s"
    csv_path = Path(__file__).parent / "CSVResults"
    csv_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    phase_jump.save_results_to_csv(csv_path / f"{title}.csv", time_array)

    png_path = Path(__file__).parent / "PNGResults"
    png_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    phase_jump.plot_results(
        png_path / f"{title}.png",
        time_array,
        event_time,
        0,
        title,
    )

    assert len(pdown) == nb_points
    assert pdown[0] == np.float64(0.803008035946675)
    assert pdown[-1] == np.float64(0.7564723505574613)

    assert len(pup) == nb_points
    assert pup[0] == np.float64(1.1)
    assert pup[-1] == np.float64(0.8447078551626718)


def test_phase_jump_underdamped_envelopes_event_at_200ms():

    start_time = 0
    end_time = 1.315
    event_time = 0.2
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)  # From Start_Time to End_Time

    phase_jump = PhaseJump(gfm_params=gfm_underdamped_params)
    phase_jump.calculate_base_values(D=200.0, H=10.0, Xeff=0)
    phase_jump.calculate_envelopes(time_array, event_time)
    pdown = phase_jump.get_pdown()
    pup = phase_jump.get_pup()

    title = "Underdamped_PhaseJump_event"
    csv_path = Path(__file__).parent / "CSVResults"
    csv_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    phase_jump.save_results_to_csv(csv_path / f"{title}.csv", time_array)

    png_path = Path(__file__).parent / "PNGResults"
    png_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    phase_jump.plot_results(
        png_path / f"{title}.png",
        time_array,
        event_time,
        0,
        title,
    )

    assert len(pdown) == nb_points
    assert pdown[0] == np.float64(0.8)
    assert pdown[-1] == np.float64(0.7564723505574613)

    assert len(pup) == nb_points
    assert pup[0] == np.float64(0.8)
    assert pup[-1] == np.float64(0.8447078551626718)
