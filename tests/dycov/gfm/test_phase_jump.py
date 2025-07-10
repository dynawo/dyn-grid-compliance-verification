#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import configparser
import math
from pathlib import Path

import numpy as np
import pandas as pd

from dycov.configuration.cfg import config
from dycov.core.parameters import Parameters
from dycov.gfm.calculators.phase_jump import PhaseJump
from dycov.gfm.parameters import GFMParameters
from dycov.gfm.producer import GFMProducer

# Float tolerance
epsilon = 1e-3

gfm_overdamped_params = """
[DEFAULT]
P0=0.5
Q0=0.0
DeltaPhase=-0.08726646259971647
VoltageStep=0.0
SCR=2.0
D=152
H=3
Xeff=0.06
RatioMin=0.9
RatioMax=1.1
Wb=314
U0=1.0
Ugr=1.0
MarginHigh=0.5
MarginLow=0.5
FinalAllowedTunnelVariation=0.05
FinalAllowedTunnelPn=0.02
TimeTo90=0.0
TimeForTunnel=0.0
p_max_injection=1.1
p_min_injection=-1.1
q_max=0.4
q_min=-0.4
"""


gfm_underdamped_params = """
[DEFAULT]
P0=0.8
Q0=0.0
DeltaPhase=-0.13962634015954636
VoltageStep=0.0
SCR=10.0
D=152
H=3
Xeff=0.06
RatioMin=0.8
RatioMax=1.2
Wb=314
U0=1.0
Ugr=1.0
MarginHigh=0.2
MarginLow=0.5
FinalAllowedTunnelVariation=0.05
FinalAllowedTunnelPn=0.02
TimeTo90=0.0
TimeForTunnel=0.0
p_max_injection=1.1
p_min_injection=-1.1
q_max=0.4
q_min=-0.4
"""


s_vol_ang_step_1_params = """
[DEFAULT]
P0=0.55  # 0.5*p_max_injection
Q0=0.0
DeltaPhase=0.10499900779997887  # +θ_jump
VoltageStep=0.0
SCR=10.0  # SCR_max
D=152
H=3
Xeff=0.06
RatioMin=0.9
RatioMax=1.1
Wb=314
U0=1.0
Ugr=1.0
MarginHigh=0.5
MarginLow=0.5
FinalAllowedTunnelVariation=0.05
FinalAllowedTunnelPn=0.02
TimeTo90=0.0
TimeForTunnel=0.0
p_max_injection=1.1
p_min_injection=-1.1
q_max=0.4
q_min=-0.4
"""


class TestProducer(GFMProducer):
    def __init__(self, config_str: str):
        self._config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        self._config.read_string(config_str)
        self._s_nref = 1.0


class TestParameters(GFMParameters):
    def __init__(self, config_str: str):
        Parameters.__init__(self, None, "", None, False)
        self._emt = True
        self._producer = TestProducer(config_str)
        self._pcs_section = "DEFAULT"
        self._bm_section = "DEFAULT"
        self._oc_section = "DEFAULT"

        config._pcs_config.read_string(config_str)


def test_phase_jump_initialization():
    test_params = TestParameters(gfm_overdamped_params)
    phase_jump = PhaseJump(gfm_params=test_params)

    assert phase_jump._gfm_params == test_params

    test_params = TestParameters(gfm_underdamped_params)
    phase_jump = PhaseJump(gfm_params=test_params)

    assert phase_jump._gfm_params == test_params


def test_phase_jump_overdamped_envelopes_event_at_0s():

    start_time = 0
    end_time = 1.315
    event_time = 0
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    test_params = TestParameters(gfm_overdamped_params)
    phase_jump = PhaseJump(gfm_params=test_params)
    magnitude, p_pcc, p_up, p_down = phase_jump.calculate_envelopes(
        D=152.0, H=3.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    title = "Overdamped_PhaseJump_DeltaP_0s"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PCC (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} down (pu)"] - p_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} up (pu)"] - p_up)), 0, abs_tol=epsilon)


def test_phase_jump_overdamped_envelopes_event_at_200ms():

    start_time = 0
    end_time = 1.315
    event_time = 0.2
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    test_params = TestParameters(gfm_overdamped_params)
    phase_jump = PhaseJump(gfm_params=test_params)
    magnitude, p_pcc, p_up, p_down = phase_jump.calculate_envelopes(
        D=152.0, H=3.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    title = "Overdamped_PhaseJump_DeltaP_event"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PCC (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} down (pu)"] - p_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} up (pu)"] - p_up)), 0, abs_tol=epsilon)


def test_phase_jump_underdamped_envelopes_event_at_0s():

    start_time = 0
    end_time = 1.315
    event_time = 0
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    test_params = TestParameters(gfm_underdamped_params)
    phase_jump = PhaseJump(gfm_params=test_params)
    magnitude, p_pcc, p_up, p_down = phase_jump.calculate_envelopes(
        D=200.0, H=10.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    title = "Underdamped_PhaseJump_DeltaP_0s"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PCC (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} down (pu)"] - p_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} up (pu)"] - p_up)), 0, abs_tol=epsilon)


def test_phase_jump_underdamped_envelopes_event_at_200ms():

    start_time = 0
    end_time = 1.315
    event_time = 0.2
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    test_params = TestParameters(gfm_underdamped_params)
    phase_jump = PhaseJump(gfm_params=test_params)
    magnitude, p_pcc, p_up, p_down = phase_jump.calculate_envelopes(
        D=200.0, H=10.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    title = "Underdamped_PhaseJump_DeltaP_event"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PCC (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} down (pu)"] - p_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} up (pu)"] - p_up)), 0, abs_tol=epsilon)


def test_s_vol_ang_step_1_phase_jump():

    start_time = 0
    end_time = 10
    event_time = 0
    nb_points = 2000
    time_array = np.linspace(start_time, end_time, nb_points)

    test_params = TestParameters(s_vol_ang_step_1_params)
    phase_jump = PhaseJump(gfm_params=test_params)
    magnitude, p_pcc, p_up, p_down = phase_jump.calculate_envelopes(
        D=133.0, H=10.0, Xeff=0.25, time_array=time_array, event_time=event_time
    )

    title = "PhaseJump_S_VolAngStep1_OC2"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PCC (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} down (pu)"] - p_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} up (pu)"] - p_up)), 0, abs_tol=epsilon)
