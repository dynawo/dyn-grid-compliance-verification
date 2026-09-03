#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the DTR PDR voltage-level classification (HTB1/HTB2/HTB3)."""

import pytest

from dycov.electrical.generator_variables import GeneratorVariables

GRID_CODE_FLOATS = {
    ("GridCode", "HTB1_reactance_a"): 0.05,
    ("GridCode", "HTB2_reactance_a"): 0.05,
    ("GridCode", "HTB3_reactance_a"): 0.05,
    ("GridCode", "HTB1_reactance_b_low"): 0.2,
    ("GridCode", "HTB2_reactance_b_low"): 0.3,
    ("GridCode", "HTB3_reactance_b_low"): 0.54,
    ("GridCode", "HTB1_reactance_b_high"): 0.3,
    ("GridCode", "HTB2_reactance_b_high"): 0.54,
    ("GridCode", "HTB3_reactance_b_high"): 0.6,
    ("GridCode", "HTB1_p_max"): 50.0,
    ("GridCode", "HTB2_p_max"): 250.0,
    ("GridCode", "HTB3_p_max"): 800.0,
    ("GridCode", "HTB1_Scc"): 400.0,
    ("GridCode", "HTB2_Scc"): 1500.0,
    ("GridCode", "HTB3_Scc"): 7000.0,
    ("GridCode", "Udim_225kV"): 235.0,
}

HTB_LISTS = {
    "HTB1_Udims": ["90"],
    "HTB2_Udims": ["225"],
    "HTB3_Udims": ["400"],
    "HTB1_External_Udims": [],
    "HTB2_External_Udims": [],
    "HTB3_External_Udims": [],
}


@pytest.fixture
def generator_variables(monkeypatch):
    monkeypatch.setattr(
        "dycov.configuration.cfg.Config.get_float",
        lambda self, section, key, default=0.0: GRID_CODE_FLOATS.get((section, key), default),
    )
    monkeypatch.setattr(
        "dycov.configuration.cfg.Config.get_list",
        lambda self, section, key: HTB_LISTS.get(key, []),
    )
    return GeneratorVariables()


def test_get_generator_type_classifies_known_levels(generator_variables):
    assert generator_variables.get_generator_type(90) == "HTB1"
    assert generator_variables.get_generator_type(225) == "HTB2"
    assert generator_variables.get_generator_type(400) == "HTB3"


def test_get_generator_type_unknown_level_returns_sentinel(generator_variables):
    # Used only for suffix matching / log messages by callers that tolerate a miss
    # (e.g. Zone 1, where the DTR does not normalize the voltage level).
    assert generator_variables.get_generator_type(33) == "INVALID UNOM"


def test_get_generator_u_dim_known_level(generator_variables):
    assert generator_variables.get_generator_u_dim(225) == pytest.approx(235.0)


def test_get_generator_u_dim_raises_for_unknown_level(generator_variables):
    with pytest.raises(ValueError, match="33"):
        generator_variables.get_generator_u_dim(33)


def test_get_scc_known_level(generator_variables):
    assert generator_variables.get_scc(225) == pytest.approx(1500.0)


def test_get_scc_raises_for_unknown_level(generator_variables):
    with pytest.raises(ValueError, match="33"):
        generator_variables.get_scc(33)


def test_calculate_line_xpu_known_level(generator_variables):
    result = generator_variables.calculate_line_xpu("a", -0.1, 100.0, 225, 100.0)
    assert result == pytest.approx(0.05 * (235.0**2 / 225.0**2))


def test_calculate_line_xpu_raises_for_unknown_level(generator_variables):
    with pytest.raises(ValueError, match="33"):
        generator_variables.calculate_line_xpu("a", -0.1, 100.0, 33, 100.0)
