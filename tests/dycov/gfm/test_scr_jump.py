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

# Assuming the classes are in the same project structure
from dycov.configuration.cfg import config
from dycov.core.parameters import Parameters
from dycov.gfm.calculators.scr_jump import SCRJump
from dycov.gfm.parameters import GFMParameters
from dycov.gfm.producer import GFMProducer

# Float tolerance
epsilon = 1e-3

gfm_underdamped_params = """
[DEFAULT]
P0=0.5
SCRinitial=2
SCRfinal=4
RatioMin=0.8
RatioMax=1.2
Wb=314
U0=1.0
Ugr=1.0
MarginHigh=0.2
MarginLow=0.2
FinalAllowedTunnelVariation=0.05
FinalAllowedTunnelPn=0.02
p_max_injection=1.2
p_min_injection=-1.2
[GFM Parameters]
Snom=1.0
"""

gfm_overdamped_params = """
[DEFAULT]
P0=0.5
SCRinitial=10
SCRfinal=2
RatioMin=0.9
RatioMax=1.1
Wb=314
U0=1.0
Ugr=1.0
MarginHigh=0.4
MarginLow=0.4
FinalAllowedTunnelVariation=0.05
FinalAllowedTunnelPn=0.02
p_max_injection=1.2
p_min_injection=-1.2
[GFM Parameters]
Snom=1.0
"""

s_scrup1_oc1_params = """
[DEFAULT]
P0=0.5
Q0=0.0
SCRinitial=2
SCRfinal=10
RatioMin=0.8
RatioMax=1.2
Wb=314
U0=1.0
Ugr=1.0
MarginHigh=0.3
MarginLow=0.5
FinalAllowedTunnelVariation=0.05
FinalAllowedTunnelPn=0.02
p_max_injection=1.2
p_min_injection=-1.2
[GFM Parameters]
Snom=1.0
"""


# --- Helper classes for loading configuration ---
class ProducerHelper(GFMProducer):
    def __init__(self, config_str: str):
        self._config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        self._config.read_string(config_str)
        self._f_nom = 1.0


class ParametersHelper(GFMParameters):
    def __init__(self, config_str: str):
        Parameters.__init__(self, None, "", None, False)
        self._emt = True
        self._producer = ProducerHelper(config_str)
        self._pcs_section = "DEFAULT"
        self._bm_section = "DEFAULT"
        self._oc_section = "DEFAULT"

        config._pcs_config.read_string(config_str)


def test_scr_jump_initialization():
    """
    Tests that the SCRJump calculator is initialized correctly with different parameters.
    """
    # Test case 1: SCR step up
    test_params = ParametersHelper(gfm_underdamped_params)
    scr_jump = SCRJump(gfm_params=test_params)

    assert scr_jump._final_scr == test_params.get_final_scr()

    # Test case 2: SCR step down
    test_params = ParametersHelper(gfm_overdamped_params)
    scr_jump = SCRJump(gfm_params=test_params)

    assert scr_jump._final_scr == test_params.get_final_scr()


def test_scr_jump_overdamped_envelopes_event_at_0s():
    start_time = -1
    end_time = 2
    event_time = 0
    nb_points = 600
    time_array = np.linspace(start_time, end_time, nb_points)

    test_params = ParametersHelper(gfm_overdamped_params)
    scr_jump = SCRJump(gfm_params=test_params)
    magnitude, p_pcc, p_up, p_down = scr_jump.calculate_envelopes(
        D=133.0, H=2.2, Xeff=0.25, time_array=time_array, event_time=event_time
    )

    title = "Overdamped_SCRJump_DeltaZ_0s"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PGU (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} lower (pu)"] - p_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} upper (pu)"] - p_up)), 0, abs_tol=epsilon
    )


def test_scr_jump_underdamped_envelopes_event_at_0s():
    start_time = -1
    end_time = 4
    event_time = 0
    nb_points = 1000
    time_array = np.linspace(start_time, end_time, nb_points)

    test_params = ParametersHelper(gfm_underdamped_params)
    scr_jump = SCRJump(gfm_params=test_params)
    magnitude, p_pcc, p_up, p_down = scr_jump.calculate_envelopes(
        D=140.0, H=5.0, Xeff=0.06, time_array=time_array, event_time=event_time
    )

    title = "Underdamped_SCRJump_DeltaZ_0s"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PGU (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} lower (pu)"] - p_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} upper (pu)"] - p_up)), 0, abs_tol=epsilon
    )


def test_scr_jump_s_scrup1_oc1():
    """
    Tests the SCRJump case with the parameters provided.
    """
    start_time = -1
    end_time = 4.0
    event_time = 0.2
    nb_points = 10000
    time_array = np.linspace(start_time, end_time, nb_points)

    test_params = ParametersHelper(s_scrup1_oc1_params)
    scr_jump = SCRJump(gfm_params=test_params)

    magnitude, p_pcc, p_up, p_down = scr_jump.calculate_envelopes(
        D=133.0, H=10.0, Xeff=0.25, time_array=time_array, event_time=event_time
    )

    title = "SCRJump_S_SCRup1_OC1"
    csv_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(csv_path / f"{title}.csv", sep=";")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude} PGU (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} lower (pu)"] - p_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude} upper (pu)"] - p_up)), 0, abs_tol=epsilon
    )
