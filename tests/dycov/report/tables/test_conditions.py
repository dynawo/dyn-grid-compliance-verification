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
        ["SCR", r"\texttt{\detokenize{10}}"],
        ["$P$", r"\texttt{\detokenize{0.5*PmaxInjection}}"],
        ["$Q$", r"\texttt{\detokenize{0}}"],
        ["Phase jump of the grid voltage (rad)", r"\texttt{\detokenize{0.3*(Xeff+Xgrid)}}"],
        ["Start of the event (s)", r"\texttt{\detokenize{20}}"],
    ]


def test_a_test_without_description_has_no_conditions():
    assert conditions.create_map("PCS.Undescribed.OC") == []
