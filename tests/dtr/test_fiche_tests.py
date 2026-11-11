#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The tests a fiche is made of, under the base revision 20240215.

A revision may add or remove an operating condition, and it writes the new list in its
own delta. These are the lists of the base.
"""

import pytest

from dycov.configuration.cfg import config


@pytest.mark.parametrize(
    "technology, benchmark, cases",
    [
        ("SM", "PCS_RTE-I7.GridVoltageSwell", ["QMax", "QMin"]),
        ("PPM", "PCS_RTE-I7.GridVoltageSwell", ["QMax", "QMin"]),
        (
            "BESS",
            "PCS_RTE-I7.GridVoltageSwell",
            ["QMaxInjection", "QMinInjection", "QMaxConsumption", "QMinConsumption"],
        ),
    ],
)
def test_the_overvoltage_is_tested_at_both_ends_of_the_reactive_range(
    description, technology, benchmark, cases
):
    description("performance", technology, "PCS_RTE-I7")

    assert config.get_list("PCS-OperatingConditions", benchmark) == cases


@pytest.mark.parametrize(
    "technology, benchmark, cases",
    [
        ("SM", "PCS_RTE-I6.GridVoltageDip", ["Qzero"]),
        ("PPM", "PCS_RTE-I6.GridVoltageDip", ["Qzero"]),
        ("BESS", "PCS_RTE-I6.GridVoltageDip", ["QzeroInjection", "QzeroConsumption"]),
    ],
)
def test_the_dip_is_tested_at_zero_reactive_power(description, technology, benchmark, cases):
    description("performance", technology, "PCS_RTE-I6")

    assert config.get_list("PCS-OperatingConditions", benchmark) == cases


@pytest.mark.parametrize("technology", ["SM", "PPM", "BESS"])
def test_a_storage_unit_runs_every_test_in_injection_and_in_consumption(description, technology):
    description("performance", technology, "PCS_RTE-I6")
    cases = config.get_list("PCS-OperatingConditions", "PCS_RTE-I6.GridVoltageDip")

    sides = [case for case in cases if case.endswith(("Injection", "Consumption"))]
    assert bool(sides) is (technology == "BESS")
