#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The category the DTR gives a unit, under the base revision 20240215.

Article 5.1.1 reads the connection voltage and the maximum power at injection. The
gabarit of a fiche follows the category, so a revision that moves these thresholds
moves which profile a unit is tested against.
"""

import pytest

from dycov.electrical.generator_variables import generator_variables


@pytest.mark.parametrize(
    "u_nom, p_max, category",
    [
        (90, 0.5, "A"),
        (90, 10, "B"),
        (90, 40, "C"),
        (90, 100, "D"),
    ],
)
def test_a_production_unit_under_110_kV_takes_its_category_from_its_power(u_nom, p_max, category):
    assert generator_variables.get_generator_category(u_nom, p_max, False) == category


@pytest.mark.parametrize("p_max", [0.5, 10, 100])
def test_every_production_unit_at_110_kV_and_above_is_of_type_D(p_max):
    """The base says "Uracc >= 110 kV" and reads no power. A later revision adds one."""
    assert generator_variables.get_generator_category(225, p_max, False) == "D"


@pytest.mark.parametrize(
    "p_max, category",
    [
        (10, "B"),
        (20, "C"),
        (60, "D"),
    ],
)
def test_a_storage_unit_at_110_kV_and_above_reads_its_own_table(p_max, category):
    assert generator_variables.get_generator_category(225, p_max, True) == category


def test_the_same_unit_is_of_another_category_when_it_stores():
    """20 MW at 225 kV: type D as a production unit, type C as a storage one."""
    assert generator_variables.get_generator_category(225, 20, False) == "D"
    assert generator_variables.get_generator_category(225, 20, True) == "C"
