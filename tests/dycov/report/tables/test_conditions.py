#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import pytest

from dycov.configuration.cfg import config
from dycov.report.tables import conditions


@pytest.fixture
def described_test(tmp_path):
    pcs = tmp_path / "PCSDescription.ini"
    pcs.write_text(
        "[PCS.Bench.OC2.Model]\n"
        "SCR = 10\n"
        "pdr_P = 0.5*PmaxInjection\n"
        "pdr_Q = 0\n"
        "[PCS.Bench.OC2.Event]\n"
        "grid_phase_jump = 0.3*(Xeff+Xgrid)\n"
        "sim_t_event_start = 20\n"
    )
    config.load_pcs_config(pcs)
    yield "PCS.Bench.OC2"
    config.load_pcs_config(None)


def test_the_conditions_of_a_test_are_the_definitions_of_its_description(described_test):
    test_conditions = conditions.create_map(described_test)

    assert test_conditions == [
        ["SCR", r"\texttt{\detokenize{10}}", ""],
        ["$P$", r"\texttt{\detokenize{0.5*PmaxInjection}}", ""],
        ["$Q$", r"\texttt{\detokenize{0}}", ""],
        ["Phase jump of the grid voltage (rad)", r"\texttt{\detokenize{0.3*(Xeff+Xgrid)}}", ""],
        ["Start of the event (s)", r"\texttt{\detokenize{20}}", ""],
    ]


def test_each_definition_comes_with_the_value_the_test_ran_with(described_test):
    ran_with = {
        "SCR": 10.0,
        "pdr_P": 0.6,
        "pdr_Q": 0.0,
        "grid_phase_jump": 0.0942,
        "sim_t_event_start": 20.0,
    }

    values = [row[2] for row in conditions.create_map(described_test, ran_with)]

    assert values == [
        "10",
        "60 MW (0.6 pu)",
        "0 Mvar (0 pu)",
        r"5.397$^\circ$ (0.0942 rad)",
        "20 s",
    ]


def test_a_test_without_description_has_no_conditions():
    assert conditions.create_map("PCS.Undescribed.OC") == []


@pytest.fixture
def stepped_test(tmp_path):
    pcs = tmp_path / "PCSDescription.ini"
    pcs.write_text("[PCS.Bench.OC5.Event]\nsetpoint_step_value = -0.5\n")
    config.load_pcs_config(pcs)
    yield "PCS.Bench.OC5"
    config.load_pcs_config(None)


@pytest.mark.parametrize(
    "ran_with, value",
    [
        ({"setpoint_step_value": 0.05}, "0.05"),
        ({"hiz_dip": 0.5}, "0.5 pu"),
        ({"grid_frequency_step": 0.01}, "0.5 Hz"),
    ],
)
def test_the_step_of_a_test_is_the_value_of_the_event_that_applies_it(
    stepped_test, ran_with, value
):
    """#833: a high-impedance fault records its step as the dip its search aims at."""
    (row,) = conditions.create_map(stepped_test, ran_with)

    assert row[0] == "Step (or depth of the voltage dip)"
    assert row[2].startswith(value)
