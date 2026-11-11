#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The gabarit the fiche I6 applies, under the base revision 20240215.

The DTR gives one profile to the classes B and C and another to the class D, so the
description writes the plain key for the first and the ``_D`` key for the second. The
tool reads the residual voltage of a class D as 1e-3 and not as the 0.00 of the DTR,
because not every model converges with a voltage of exactly zero.
"""

import pytest

SECTION = "PCS_RTE-I6.GridVoltageDip.{case}.Model"


@pytest.mark.parametrize(
    "technology, case, u_fault, u_clear, delta_t_rec2",
    [
        ("SM", "Qzero", "0.05", "0.7", "1.5"),
        ("PPM", "Qzero", "0.05", "0.05", "1.15"),
        ("BESS", "QzeroInjection", "0.05", "0.05", "1.15"),
    ],
)
def test_the_classes_B_and_C_take_the_plain_gabarit(
    description, value, technology, case, u_fault, u_clear, delta_t_rec2
):
    description("performance", technology, "PCS_RTE-I6")
    section = SECTION.format(case=case)

    assert value(section, "u_fault", "C") == u_fault
    assert value(section, "u_clear", "C") == u_clear
    assert value(section, "delta_t_rec2", "C") == delta_t_rec2


@pytest.mark.parametrize(
    "technology, case, u_clear, delta_t_rec2",
    [
        ("SM", "Qzero", "0.5", "1.35"),
        ("PPM", "Qzero", "1e-3", "1.50"),
        ("BESS", "QzeroInjection", "1e-3", "1.50"),
    ],
)
def test_the_class_D_takes_a_gabarit_of_its_own(
    description, value, technology, case, u_clear, delta_t_rec2
):
    description("performance", technology, "PCS_RTE-I6")
    section = SECTION.format(case=case)

    assert value(section, "u_fault", "D") == "1e-3"
    assert value(section, "u_clear", "D") == u_clear
    assert value(section, "delta_t_rec2", "D") == delta_t_rec2


@pytest.mark.parametrize("technology, case", [("SM", "Qzero"), ("PPM", "Qzero")])
def test_the_voltage_level_does_not_choose_the_gabarit(description, value, technology, case):
    """Only the fault elimination time depends on the level; the gabarit follows the class."""
    description("performance", technology, "PCS_RTE-I6")
    section = SECTION.format(case=case)

    assert value(section, "u_fault", "C", "HTB1") == value(section, "u_fault", "C", "HTB3")
