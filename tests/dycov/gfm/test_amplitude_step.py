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

from dycov.gfm.calculators.amplitude_step import AmplitudeStep
from dycov.gfm.parameters import GFM_Params

# Float tolerance
epsilon = 1e-3

gfm_params = GFM_Params(
    P0=0.0,
    Q0=0.2,
    delta_theta=0.0,
    voltage_step=2.0,
    SCR=10.0,
    EMT=True,
    RatioMin=0.9,
    RatioMax=1.1,
    Wb=0,
    Ucv=1.0,
    Ugr=1.0,
    MarginHigh=0.3,
    MarginLow=0.0,
    FinalAllowedTunnelVariation=0.05,
    FinalAllowedTunnelPn=0.02,
    TimeTo90=0.01,
    TimeForTunnel=0.06,
    PMax=1.1,
    PMin=-1.1,
    QMax=0.35,
    QMin=-0.35,
)


s_vol_ang_step_1_params = GFM_Params(
    P0=0.0,
    Q0=0.0,
    delta_theta=0.0,
    voltage_step=3.0,
    SCR=10.0,
    EMT=True,
    RatioMin=0.9,
    RatioMax=1.1,
    Wb=0,
    Ucv=1.0,
    Ugr=1.0,
    MarginHigh=0.3,
    MarginLow=0.0,
    FinalAllowedTunnelVariation=0.05,
    FinalAllowedTunnelPn=0.02,
    TimeTo90=0.01,
    TimeForTunnel=0.06,
    PMax=1.1,
    PMin=-1.1,
    QMax=0.4,
    QMin=-0.4,
)


def test_phase_jump_initialization():
    phase_jump = AmplitudeStep(gfm_params=gfm_params)

    assert phase_jump._gfm_params == gfm_params


def test_phase_jump_envelopes_event_at_0s():

    start_time = 0
    end_time = 1.315
    event_time = 0
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    phase_jump = AmplitudeStep(gfm_params=gfm_params)
    magnitude, q_pcc, q_up, q_down = phase_jump.calculate_envelopes(
        D=152.0, H=3.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    title = "AmplitudeStep_DeltaP_0s"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PCC (pu)"] - q_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} down (pu)"] - q_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} up (pu)"] - q_up)), 0, abs_tol=epsilon)


def test_phase_jump_envelopes_event_at_200ms():

    start_time = 0
    end_time = 1.315
    event_time = 0.2
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    phase_jump = AmplitudeStep(gfm_params=gfm_params)
    magnitude, q_pcc, q_up, q_down = phase_jump.calculate_envelopes(
        D=152.0, H=3.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    title = "AmplitudeStep_DeltaP_event"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PCC (pu)"] - q_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} down (pu)"] - q_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} up (pu)"] - q_up)), 0, abs_tol=epsilon)


def test_s_vol_ang_step_1_phase_jump():

    start_time = 0
    end_time = 10
    event_time = 0
    nb_points = 2000
    time_array = np.linspace(start_time, end_time, nb_points)

    phase_jump = AmplitudeStep(gfm_params=s_vol_ang_step_1_params)
    magnitude, q_pcc, q_up, q_down = phase_jump.calculate_envelopes(
        D=133.0, H=10.0, Xeff=0.25, time_array=time_array, event_time=event_time
    )

    title = "AmplitudeStep_S_VolAngStep1_OC1"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PCC (pu)"] - q_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} down (pu)"] - q_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} up (pu)"] - q_up)), 0, abs_tol=epsilon)
