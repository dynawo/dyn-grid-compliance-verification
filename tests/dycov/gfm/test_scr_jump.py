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

# Float tolerance for comparisons
epsilon = 0.499

gfm_scrjump_up_params = """
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
Tpll=0.01
TimeExponentialDecrease=0.3
MarginHigh=0.3
MarginLow=0.5
FinalAllowedTunnelVariation=0.05
FinalAllowedTunnelPn=0.02
p_max_injection=1.2
p_min_injection=-1.2
"""

gfm_scrjump_down_params = """
[DEFAULT]
P0=0.5
Q0=0.0
SCRinitial=10
SCRfinal=2
RatioMin=0.8
RatioMax=1.2
Wb=314
U0=1.0
Ugr=1.0
Tpll=0.01
TimeExponentialDecrease=0.3
MarginHigh=0.3
MarginLow=0.5
FinalAllowedTunnelVariation=0.05
FinalAllowedTunnelPn=0.02
p_max_injection=1.2
p_min_injection=-1.2
"""

gfm_test_case_params = """
[DEFAULT]
P0=0.5
Q0=0.0
SCRinitial=10
SCRfinal=2
RatioMin=0.8
RatioMax=1.2
Wb=314
U0=1.0
Ugr=1.0
Tpll=0.01
TimeExponentialDecrease=0.3
MarginHigh=0.3
MarginLow=0.5
FinalAllowedTunnelVariation=0.05
FinalAllowedTunnelPn=0.02
p_max_injection=1.2
p_min_injection=-1.2
"""


# --- Helper classes for loading configuration ---
class TestProducer(GFMProducer):
    def __init__(self, config_str: str):
        self._config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        self._config.read_string(config_str)
        self._s_nref = 1.0
        self._f_nom = 1.0


class TestParameters(GFMParameters):
    def __init__(self, config_str: str):
        Parameters.__init__(self, None, "", None, False)
        self._emt = True
        self._producer = TestProducer(config_str)
        self._pcs_section = "DEFAULT"
        self._bm_section = "DEFAULT"
        self._oc_section = "DEFAULT"

        config._pcs_config.read_string(config_str)


def test_scrjump_initialization():
    """
    Tests that the SCRJump calculator is initialized correctly with different parameters.
    """
    # Test case 1: SCR step up
    test_params_up = TestParameters(gfm_scrjump_up_params)
    scrjump_up = SCRJump(gfm_params=test_params_up)

    assert scrjump_up._initial_scr == test_params_up.get_initial_scr()
    assert scrjump_up._final_scr == test_params_up.get_final_scr()

    # Test case 2: SCR step down
    test_params_down = TestParameters(gfm_scrjump_down_params)
    scrjump_down = SCRJump(gfm_params=test_params_down)

    assert scrjump_down._initial_scr == test_params_down.get_initial_scr()
    assert scrjump_down._final_scr == test_params_down.get_final_scr()


def test_scrjump_case(
    title: str, gfm_params: TestParameters = TestParameters(gfm_test_case_params)
):
    """
    Tests the SCRJump case with the parameters provided.
    """
    start_time = -1
    end_time = 4.0
    event_time = 0.2
    nb_points = 10000
    time_array = np.linspace(start_time, end_time, nb_points)

    scrjump = SCRJump(gfm_params=gfm_params)

    magnitude, p_pcc, p_up, p_down = scrjump.calculate_envelopes(
        D=50.0, H=3.0, Xeff=0.25, time_array=time_array, event_time=event_time
    )

    resources_path = Path(__file__).parent / "resources"
    csv_data = pd.read_csv(resources_path / f"{title}.csv", sep=",")

    assert math.isclose(max(np.abs(csv_data["Time (s)"] - time_array)), 0, abs_tol=epsilon)
    assert math.isclose(max(np.abs(csv_data[f"{magnitude}_PCC (pu)"] - p_pcc)), 0, abs_tol=epsilon)
    assert math.isclose(
        max(np.abs(csv_data[f"{magnitude}_down (pu)"] - p_down)), 0, abs_tol=epsilon
    )
    assert math.isclose(max(np.abs(csv_data[f"{magnitude}_up (pu)"] - p_up)), 0, abs_tol=epsilon)


if __name__ == "__main__":
    test_scrjump_initialization()
    test_scrjump_case("SCRJump_case_1")
