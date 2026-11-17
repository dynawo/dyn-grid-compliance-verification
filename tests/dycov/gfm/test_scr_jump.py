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
import pytest

import dycov

# Assuming the classes are in the same project structure
from dycov.configuration.cfg import config
from dycov.core.parameters import Parameters
from dycov.gfm import gfm
from dycov.gfm.calculators.scr_jump import SCRJump
from dycov.gfm.gfm import GridForming
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
        self._f_nom = 50.0


class ParametersHelper(GFMParameters):
    def __init__(self, config_str: str):
        Parameters.__init__(self, None, "", None, False)
        self._emt = True
        self._producer = ProducerHelper(config_str)
        self._pcs_section = "DEFAULT"
        self._bm_section = "DEFAULT"
        self._oc_section = "DEFAULT"
        self._eval_sections = (self._oc_section, self._bm_section, self._pcs_section)

        config._pcs_default_config.read_string(config_str)


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


class _PowerLimits:
    """GFM parameters with the given power limits and 1.0 for anything else."""

    def __init__(self, p_min: float, p_max: float):
        self._p_min = p_min
        self._p_max = p_max

    def is_emt(self) -> bool:
        return False

    def get_min_active_power(self) -> float:
        return self._p_min

    def get_max_active_power(self) -> float:
        return self._p_max

    def __getattr__(self, name):
        return lambda *args, **kwargs: 1.0


@pytest.mark.parametrize(
    "p_min, p_max, envelope_value, held_value, expected_in_window",
    [(0.1, 1.0, 0.5, 0.05, 0.3), (-1.0, -0.1, -0.5, -0.05, -0.3)],
)
def test_the_hold_leaves_the_envelope_outside_its_window_whatever_the_power_limits(
    p_min, p_max, envelope_value, held_value, expected_in_window
):
    scr_jump = SCRJump(gfm_params=_PowerLimits(p_min, p_max))
    time = np.linspace(-0.1, 0.2, 31)
    envelope = np.full_like(time, envelope_value)

    held = scr_jump._modify_envelope(envelope, np.full_like(time, held_value), time, 0.0)

    in_window = (time >= 0.0) & (time <= 0.03)
    assert np.all(held[~in_window] == envelope_value)
    assert held[in_window] == pytest.approx(np.full(in_window.sum(), expected_in_window))


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


_PRODUCER_LIMITS = """
[DEFAULT]
p_max_injection = 110
p_min_injection = -110
u_nom = 225
q_max = 40
q_min = -40
"""

_SINGLE_SET_PRODUCER = (
    _PRODUCER_LIMITS
    + """
[GFM Parameters]
Snom = 90.0
D = 152.0
H = 2.0
Xeff = 0.27
"""
)

_HYBRID_PRODUCER = (
    _PRODUCER_LIMITS
    + """
[GFM Parameters]
Snom = 90.0
D_Overdamped = 152
D_Underdamped = 95
H_Overdamped = 2
H_Underdamped = 5
Xeff = 0.27
"""
)


@pytest.fixture
def scr_jump_pcs():
    # The calculator tests above leave their [DEFAULT] values in this layer, and a PCS loaded
    # afterwards would inherit them.
    layer_defaults = config._pcs_default_config.defaults()
    leftover_defaults = dict(layer_defaults)
    layer_defaults.clear()
    pcs_path = Path(dycov.__file__).parent / "templates/PCS/gfm/PCS_RTE-IGFM3/PCSDescription.ini"
    config.load_pcs_config(pcs_path)
    yield
    config.load_pcs_config(None)
    layer_defaults.update(leftover_defaults)


def _figure_parameters(tmp_path, monkeypatch, producer: str) -> list[str]:
    producer_ini = tmp_path / "Producer.ini"
    producer_ini.write_text(producer)
    parameters = GFMParameters(
        producer_ini=producer_ini,
        selected_pcs="PCS_RTE-IGFM3",
        output_dir=tmp_path / "Results",
        only_dtr=True,
        emt=False,
    )
    figures = []
    monkeypatch.setattr(gfm, "plot_results", lambda **kwargs: figures.append(kwargs))
    try:
        GridForming().generate(tmp_path, parameters, "PCS_RTE-IGFM3", "S_SCRdown1", "OC1")
    finally:
        parameters.cleanup_working_dir(preserve_on_debug=False)
    (figure,) = figures
    return figure["params_list"]


def test_figures_show_the_damping_ratio_of_the_producer(scr_jump_pcs, tmp_path, monkeypatch):
    figure = _figure_parameters(tmp_path, monkeypatch, _SINGLE_SET_PRODUCER)

    assert "D = 152.000" in figure
    assert "H = 2.000 s" in figure
    assert "Epsilon = 1.882" in figure


def test_hybrid_figures_show_no_value_of_a_single_set(scr_jump_pcs, tmp_path, monkeypatch):
    figure = _figure_parameters(tmp_path, monkeypatch, _HYBRID_PRODUCER)

    assert "Xeff = 0.270 pu" in figure
    assert not [line for line in figure if line.startswith(("D =", "H =", "Epsilon ="))]


_MIXED_REGIMES_PARAMS = """
[DEFAULT]
P0=0.5
Q0=0.0
SCRinitial=2
SCRfinal=20
RatioMin=0.85
RatioMax=1.15
Wb=314
U0=1.0
Ugr=1.0
MarginHigh=0.3
MarginLow=0.3
FinalAllowedTunnelVariation=0.05
FinalAllowedTunnelPn=0.02
p_max_injection=1.2
p_min_injection=-1.2
[GFM Parameters]
Snom=1.0
"""


def test_variations_on_both_sides_of_critical_damping_each_take_their_own_regime():
    """S_SCRup1 with H = 5 and D = 200, the case of RTE's reference envelopes: the nominal set
    and one variation are overdamped and the other underdamped."""
    time_array = np.linspace(-1, 5, 3001)
    scr_jump = SCRJump(gfm_params=ParametersHelper(_MIXED_REGIMES_PARAMS))
    scr_jump._is_emt_flag = False

    _, _, upper, lower = scr_jump.calculate_envelopes(
        D=200, H=5, Xeff=0.27, time_array=time_array, event_time=0
    )

    assert scr_jump._epsilon_vals == pytest.approx([1.0095, 1.2592, 0.8002], abs=1e-4)
    after_event = time_array > 0.05
    for damping, inertia in zip(scr_jump._d_vals, scr_jump._h_vals):
        delta_p, *_ = scr_jump._calculate_delta_p_for_damping(
            damping, inertia, 0.27, time_array, 0
        )
        response = 0.5 + delta_p[after_event]
        assert (lower[after_event] <= response + 1e-9).all(), (damping, inertia)
        assert (response <= upper[after_event] + 1e-9).all(), (damping, inertia)


def test_the_bounds_of_an_underdamped_variation_take_part_whatever_the_last_one_is():
    time_array = np.linspace(-1, 5, 3001)
    swapped = _MIXED_REGIMES_PARAMS.replace("RatioMin=0.85", "RatioMin=1.15").replace(
        "RatioMax=1.15", "RatioMax=0.85"
    )
    envelopes = []
    for params in (_MIXED_REGIMES_PARAMS, swapped):
        scr_jump = SCRJump(gfm_params=ParametersHelper(params))
        scr_jump._is_emt_flag = False
        envelopes.append(
            scr_jump.calculate_envelopes(
                D=200, H=5, Xeff=0.27, time_array=time_array, event_time=0
            )
        )

    # The last variation, overdamped once the ratios are swapped, no longer brings in half of
    # its change, but the underdamped one still brings the bounds of its oscillation
    assert envelopes[1][2] == pytest.approx(envelopes[0][2])
