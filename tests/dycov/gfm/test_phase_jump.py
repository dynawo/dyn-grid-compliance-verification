#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import math
from pathlib import Path

import numpy as np
import pandas as pd

from dycov.gfm.calculators.phase_jump import PhaseJump
from dycov.gfm.parameters import GFM_Params

# Float tolerance
epsilon = 1e-3

gfm_overdamped_params = GFM_Params(
    P0=0.5,
    Q0=0.0,
    delta_theta=-5.0,
    voltage_step=0.0,
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
    TimeTo90=0.0,
    TimeForTunnel=0.0,
    PMax=1.1,
    PMin=-1.1,
    QMax=0.4,
    QMin=-0.4,
)


gfm_underdamped_params = GFM_Params(
    P0=0.8,
    Q0=0.0,
    delta_theta=-8.0,
    voltage_step=0.0,
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
    TimeTo90=0.0,
    TimeForTunnel=0.0,
    PMax=1.1,
    PMin=-1.1,
    QMax=0.4,
    QMin=-0.4,
)


s_vol_ang_step_1_params = GFM_Params(
    P0=0.55,  # 0.5*PMax
    Q0=0.0,
    delta_theta=6.016,  # +θ_jump
    voltage_step=0.0,
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
    TimeTo90=0.0,
    TimeForTunnel=0.0,
    PMax=1.1,
    PMin=-1.1,
    QMax=0.4,
    QMin=-0.4,
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
    _, p_pcc, p_up, p_down = phase_jump.calculate_envelopes(
        D=152.0, H=3.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    title = "Overdamped_PhaseJump_DeltaP_0s"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["PCC (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["down (pu)"] - p_down)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["up (pu)"] - p_up)), 0, abs_tol=epsilon)


def test_phase_jump_overdamped_envelopes_event_at_200ms():

    start_time = 0
    end_time = 1.315
    event_time = 0.2
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    phase_jump = PhaseJump(gfm_params=gfm_overdamped_params)
    _, p_pcc, p_up, p_down = phase_jump.calculate_envelopes(
        D=152.0, H=3.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    title = "Overdamped_PhaseJump_DeltaP_event"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["PCC (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["down (pu)"] - p_down)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["up (pu)"] - p_up)), 0, abs_tol=epsilon)


def test_phase_jump_underdamped_envelopes_event_at_0s():

    start_time = 0
    end_time = 1.315
    event_time = 0
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    phase_jump = PhaseJump(gfm_params=gfm_underdamped_params)
    _, p_pcc, p_up, p_down = phase_jump.calculate_envelopes(
        D=200.0, H=10.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    title = "Underdamped_PhaseJump_DeltaP_0s"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["PCC (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["down (pu)"] - p_down)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["up (pu)"] - p_up)), 0, abs_tol=epsilon)


def test_phase_jump_underdamped_envelopes_event_at_200ms():

    start_time = 0
    end_time = 1.315
    event_time = 0.2
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    phase_jump = PhaseJump(gfm_params=gfm_underdamped_params)
    _, p_pcc, p_up, p_down = phase_jump.calculate_envelopes(
        D=200.0, H=10.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    title = "Underdamped_PhaseJump_DeltaP_event"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["PCC (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["down (pu)"] - p_down)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["up (pu)"] - p_up)), 0, abs_tol=epsilon)


def test_s_vol_ang_step_1_phase_jump():

    start_time = 0
    end_time = 10
    event_time = 0
    nb_points = 2000
    time_array = np.linspace(start_time, end_time, nb_points)

    phase_jump = PhaseJump(gfm_params=s_vol_ang_step_1_params)
    overdamped, p_pcc, p_up, p_down = phase_jump.calculate_envelopes(
        D=133.0, H=10.0, Xeff=0.25, time_array=time_array, event_time=event_time
    )

    title = "PhaseJump_S_VolAngStep1_OC2"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["PCC (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["down (pu)"] - p_down)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data["up (pu)"] - p_up)), 0, abs_tol=epsilon)
