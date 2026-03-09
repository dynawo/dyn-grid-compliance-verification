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
from dycov.gfm.calculators.amplitude_step import AmplitudeStep
from dycov.gfm.parameters import GFMParameters
from dycov.gfm.producer import GFMProducer

# Float tolerance
epsilon = 1e-3


gfm_params = """
[DEFAULT]
Q0=0.2
VoltageStep=2.0
SCR=10.0
RatioMin=0.9
RatioMax=1.1
FinalAllowedTunnelVariation=0.05
FinalAllowedTunnelPn=0.02
TimeTo90=0.01
TimeForTunnel=0.06
q_max=0.35
q_min=-0.35
VoltageStepAtGrid = 0.15*(Xeff+Xgrid)
[GFM Parameters]
Snom=1.0
Xeff = 0.27
"""

s_vol_ang_step_1_params = """
[DEFAULT]
Q0=0.0
VoltageStep=3.0
SCR=10.0
RatioMin=0.9
RatioMax=1.1
FinalAllowedTunnelVariation=0.05
FinalAllowedTunnelPn=0.02
TimeTo90=0.01
TimeForTunnel=0.06
q_max=0.4
q_min=-0.4
VoltageStepAtGrid = 0.15*(Xeff+Xgrid)
[GFM Parameters]
Snom=1.0
Xeff = 0.27
"""


class ProducerHelper(GFMProducer):
    def __init__(self, config_str: str):
        self._config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        self._config.read_string(config_str)


class ParametersHelper(GFMParameters):
    def __init__(self, config_str: str):
        Parameters.__init__(self, None, "", None, False)
        self._emt = True
        self._producer = ProducerHelper(config_str)
        self._pcs_section = "DEFAULT"
        self._bm_section = "DEFAULT"
        self._oc_section = "DEFAULT"

        config._pcs_config.read_string(config_str)


def test_amplitude_step_initialization():
    test_params = ParametersHelper(gfm_params)
    amplitude_step = AmplitudeStep(gfm_params=test_params)

    assert amplitude_step._voltage_step == test_params.get_voltage_step_at_grid()


def test_amplitude_step_envelopes_event_at_0s():
    start_time = 0
    end_time = 1.315
    event_time = 0
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    test_params = ParametersHelper(gfm_params)
    test_params = ParametersHelper(gfm_params)
    amplitude_step = AmplitudeStep(gfm_params=test_params)
    magnitude, q_pcc, q_up, q_down = amplitude_step.calculate_envelopes(
        D=152.0, H=3.0, Xeff=0.26, time_array=time_array, event_time=event_time
    )

    title = "AmplitudeStep_DeltaP_0s"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PGU (pu)"] - q_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} lower (pu)"] - q_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} upper (pu)"] - q_up)), 0, abs_tol=epsilon
    )


def test_amplitude_step_envelopes_event_at_200ms():
    start_time = 0
    end_time = 1.315
    event_time = 0.2
    nb_points = 264
    time_array = np.linspace(start_time, end_time, nb_points)

    test_params = ParametersHelper(gfm_params)
    amplitude_step = AmplitudeStep(gfm_params=test_params)
    magnitude, q_pcc, q_up, q_down = amplitude_step.calculate_envelopes(
        D=152.0, H=3.0, Xeff=0.26, time_array=time_array, event_time=event_time
    )

    title = "AmplitudeStep_DeltaP_event"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PGU (pu)"] - q_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} lower (pu)"] - q_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} upper (pu)"] - q_up)), 0, abs_tol=epsilon
    )


def test_s_vol_ang_step_1_amplitude_step():
    start_time = 0
    end_time = 10
    event_time = 0
    nb_points = 2000
    time_array = np.linspace(start_time, end_time, nb_points)

    test_params = ParametersHelper(s_vol_ang_step_1_params)
    amplitude_step = AmplitudeStep(gfm_params=test_params)
    magnitude, q_pcc, q_up, q_down = amplitude_step.calculate_envelopes(
        D=133.0, H=10.0, Xeff=0.25, time_array=time_array, event_time=event_time
    )

    title = "AmplitudeStep_S_VolAngStep1_OC1"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PGU (pu)"] - q_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} lower (pu)"] - q_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} upper (pu)"] - q_up)), 0, abs_tol=epsilon
    )
