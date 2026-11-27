#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The layers a PCS is described in, read without preparing the PCS."""

from dycov.configuration.cfg import config
from dycov.model import pcs_layers


def test_reading_the_tests_of_a_pcs_puts_back_the_pcs_prepared_before(tmp_path):
    prepared = tmp_path / "PCSDescription.ini"
    prepared.write_text("[PCS-Benchmarks]\nPCS_Prepared = Bench\n")
    config.load_pcs_config(prepared)
    try:
        tests = pcs_layers.tests_it_runs("PCS_RTE-I16z3", "model/PPM", None)

        assert tests and all(test.startswith("PCS_RTE-I16z3.") for test in tests)
        assert config.pcs_description_paths() == (prepared, None, None, None)
        assert config.get_list("PCS-Benchmarks", "PCS_Prepared") == ["Bench"]
    finally:
        config.load_pcs_config(None)


def test_an_operating_condition_runs_unless_it_is_an_optional_point_left_off(tmp_path):
    description = tmp_path / "PCSDescription.ini"
    description.write_text(
        "[PCS]\nrun_OC1 =\n[PCS.Bench.OC1]\noptional_operating_point = OC1\n[PCS.Bench.OC2]\n"
    )
    config.load_pcs_config(description)
    try:
        assert pcs_layers.is_run("PCS", "PCS.Bench.OC2")
        assert not pcs_layers.is_run("PCS", "PCS.Bench.OC1")
    finally:
        config.load_pcs_config(None)
