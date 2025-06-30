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
import pandas as pd

from dycov.gfm.phase_jump import GFM_Params, PhaseJump

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
    PMin=-1.1,
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
    time_array = np.linspace(start_time, end_time, nb_points)  # From Start_Time to End_Time

    phase_jump = PhaseJump(gfm_params=gfm_overdamped_params)
    (
        is_overdamped,
        DeltaP_array,
        DeltaP_min,
        DeltaP_max,
        Ppeak_array,
        epsilon_array,
    ) = phase_jump.get_delta_p(
        D=152.0, H=3.0, Xeff=0, time_array=time_array, event_time=event_time
    )

    P_pcc, P_up_anal, P_down_anal = phase_jump.get_envelopes(
        DeltaP_array=DeltaP_array,
        DeltaP_min=DeltaP_min,
        DeltaP_max=DeltaP_max,
        Ppeak_array=Ppeak_array,
        time_array=time_array,
        event_time=event_time,
    )

    title = "Overdamped_PhaseJump_DeltaP_0s"
    csv_path = Path(__file__).parent / "CSVResults"
    csv_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

    df = pd.DataFrame(
        {
            "Time (s)": time_array,
            "P_PCC (pu)": P_pcc,
            "P_down (pu)": P_down_anal,
            "P_up (pu)": P_up_anal,
        }
    )
    df.to_csv(csv_path / f"{title}.csv", index=False)

    png_path = Path(__file__).parent / "PNGResults"
    png_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    phase_jump.plot_results(
        png_path / f"{title}.png",
        P_pcc,
        P_up_anal,
        P_down_anal,
        time_array,
        event_time,
        0,
        title,
    )

    assert len(P_down_anal) == nb_points
    assert P_down_anal[0] == np.float64(0.5013787821149449)
    assert P_down_anal[-1] == np.float64(0.4804503537321287)

    assert len(P_up_anal) == nb_points
    assert P_up_anal[0] == np.float64(0.7323706712771527)
    assert P_up_anal[-1] == np.float64(0.5209853573483934)


def test_phase_jump_overdamped_envelopes_event_at_200ms():

    start_time = 0
    end_time = 1.315
    event_time = 0.2
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)  # From Start_Time to End_Time

    phase_jump = PhaseJump(gfm_params=gfm_overdamped_params)
    (
        is_overdamped,
        DeltaP_array,
        DeltaP_min,
        DeltaP_max,
        Ppeak_array,
        epsilon_array,
    ) = phase_jump.get_delta_p(
        D=152.0, H=3.0, Xeff=0, time_array=time_array, event_time=event_time
    )

    P_pcc, P_up_anal, P_down_anal = phase_jump.get_envelopes(
        DeltaP_array=DeltaP_array,
        DeltaP_min=DeltaP_min,
        DeltaP_max=DeltaP_max,
        Ppeak_array=Ppeak_array,
        time_array=time_array,
        event_time=event_time,
    )

    title = "Overdamped_PhaseJump_DeltaP_event"
    csv_path = Path(__file__).parent / "CSVResults"
    csv_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

    df = pd.DataFrame(
        {
            "Time (s)": time_array,
            "P_PCC (pu)": P_pcc,
            "P_down (pu)": P_down_anal,
            "P_up (pu)": P_up_anal,
        }
    )
    df.to_csv(csv_path / f"{title}.csv", index=False)

    png_path = Path(__file__).parent / "PNGResults"
    png_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    phase_jump.plot_results(
        png_path / f"{title}.png",
        P_pcc,
        P_up_anal,
        P_down_anal,
        time_array,
        event_time,
        0,
        title,
    )

    assert len(P_down_anal) == nb_points
    assert P_down_anal[0] == np.float64(0.5)
    assert P_down_anal[-1] == np.float64(0.4804503537321287)

    assert len(P_up_anal) == nb_points
    assert P_up_anal[0] == np.float64(0.5)
    assert P_up_anal[-1] == np.float64(0.5209853573483934)


def test_phase_jump_underdamped_envelopes_event_at_0s():

    start_time = 0
    end_time = 1.315
    event_time = 0
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)  # From Start_Time to End_Time

    phase_jump = PhaseJump(gfm_params=gfm_underdamped_params)
    (
        is_overdamped,
        DeltaP_array,
        DeltaP_min,
        DeltaP_max,
        Ppeak_array,
        epsilon_array,
    ) = phase_jump.get_delta_p(
        D=200.0, H=10.0, Xeff=0, time_array=time_array, event_time=event_time
    )

    P_pcc, P_up_anal, P_down_anal = phase_jump.get_envelopes(
        DeltaP_array=DeltaP_array,
        DeltaP_min=DeltaP_min,
        DeltaP_max=DeltaP_max,
        Ppeak_array=Ppeak_array,
        time_array=time_array,
        event_time=event_time,
    )

    title = "Underdamped_PhaseJump_DeltaP_0s"
    csv_path = Path(__file__).parent / "CSVResults"
    csv_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

    df = pd.DataFrame(
        {
            "Time (s)": time_array,
            "P_PCC (pu)": P_pcc,
            "P_down (pu)": P_down_anal,
            "P_up (pu)": P_up_anal,
        }
    )
    df.to_csv(csv_path / f"{title}.csv", index=False)

    png_path = Path(__file__).parent / "PNGResults"
    png_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    phase_jump.plot_results(
        png_path / f"{title}.png",
        P_pcc,
        P_up_anal,
        P_down_anal,
        time_array,
        event_time,
        0,
        title,
    )

    assert len(P_down_anal) == nb_points
    assert P_down_anal[0] == np.float64(0.803008035946675)
    assert P_down_anal[-1] == np.float64(0.7564723505574613)

    assert len(P_up_anal) == nb_points
    assert P_up_anal[0] == np.float64(1.1)
    assert P_up_anal[-1] == np.float64(0.8447078551626718)


def test_phase_jump_underdamped_envelopes_event_at_200ms():

    start_time = 0
    end_time = 1.315
    event_time = 0.2
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)  # From Start_Time to End_Time

    phase_jump = PhaseJump(gfm_params=gfm_underdamped_params)
    (
        is_overdamped,
        DeltaP_array,
        DeltaP_min,
        DeltaP_max,
        Ppeak_array,
        epsilon_array,
    ) = phase_jump.get_delta_p(
        D=200.0, H=10.0, Xeff=0, time_array=time_array, event_time=event_time
    )

    P_pcc, P_up_anal, P_down_anal = phase_jump.get_envelopes(
        DeltaP_array=DeltaP_array,
        DeltaP_min=DeltaP_min,
        DeltaP_max=DeltaP_max,
        Ppeak_array=Ppeak_array,
        time_array=time_array,
        event_time=event_time,
    )

    title = "Underdamped_PhaseJump_DeltaP_event"
    csv_path = Path(__file__).parent / "CSVResults"
    csv_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists

    df = pd.DataFrame(
        {
            "Time (s)": time_array,
            "P_PCC (pu)": P_pcc,
            "P_down (pu)": P_down_anal,
            "P_up (pu)": P_up_anal,
        }
    )
    df.to_csv(csv_path / f"{title}.csv", index=False)

    png_path = Path(__file__).parent / "PNGResults"
    png_path.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    phase_jump.plot_results(
        png_path / f"{title}.png",
        P_pcc,
        P_up_anal,
        P_down_anal,
        time_array,
        event_time,
        0,
        title,
    )

    assert len(P_down_anal) == nb_points
    assert P_down_anal[0] == np.float64(0.8)
    assert P_down_anal[-1] == np.float64(0.7564723505574613)

    assert len(P_up_anal) == nb_points
    assert P_up_anal[0] == np.float64(0.8)
    assert P_up_anal[-1] == np.float64(0.8447078551626718)
