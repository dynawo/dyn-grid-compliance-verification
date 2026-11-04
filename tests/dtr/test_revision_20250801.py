#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""What the revision 20250801 writes differently from the base 20240215.

Of what the tool implements, the revision changes the categories of a unit alone: article
5.1.1 v1.4 gives a unit above 110 kV a table of its own, and article 8.3.3 v3.4 leaves the
fiches as the base writes them. Each test reads two revisions one after the other, so the table
of the test shows the difference itself: the base for what 20250801 changes, and 20260723 for
what 20250801 does not change yet.
"""

from pathlib import Path

import pytest

import dycov
from dycov.configuration.cfg import config
from dycov.electrical.generator_variables import generator_variables

BASE_REVISION = "20240215"
REVISION = "20250801"
LATER_REVISION = "20260723"


def test_the_tool_implements_the_revision():
    """A run that asks for a revision the tool does not implement stops."""
    assert REVISION in config.get_list("DTR", "available")


def test_20250801_writes_the_description_of_no_PCS():
    delta = Path(dycov.__file__).resolve().parent / "templates" / "revisions" / REVISION

    assert sorted(path.name for path in delta.iterdir()) == ["revision_art_5_1_1.ini"]


@pytest.mark.parametrize("selected, category", [(BASE_REVISION, "D"), (REVISION, "C")])
def test_a_production_unit_of_20_MW_at_225_kV_changes_category(revision, selected, category):
    """The base makes every unit above 110 kV a type D. 20250801 reads its power."""
    revision(selected)

    assert generator_variables.get_generator_category(225, 20, False) == category


@pytest.mark.parametrize("p_max, category", [(0.5, "A"), (10, "B"), (20, "C"), (60, "D")])
def test_20250801_gives_a_unit_above_110_kV_a_table_of_its_own(revision, p_max, category):
    """Article 5.1.1 v1.4 takes the thresholds 1, 18 and 30 MW, where the base took none."""
    revision(REVISION)

    assert generator_variables.get_generator_category(225, p_max, False) == category


@pytest.mark.parametrize("p_max, category", [(0.5, "A"), (10, "B"), (40, "C"), (80, "D")])
def test_20250801_leaves_the_table_below_110_kV_as_it_is(revision, p_max, category):
    revision(REVISION)
    below = generator_variables.get_generator_category(63, p_max, False)

    revision(BASE_REVISION)

    assert below == generator_variables.get_generator_category(63, p_max, False) == category


def test_20250801_leaves_the_table_of_a_storage_unit_as_it_is(revision):
    """A unit of 40 MW above 110 kV: type D when it produces, type C when it stores."""
    revision(REVISION)

    assert generator_variables.get_generator_category(225, 40, False) == "D"
    assert generator_variables.get_generator_category(225, 40, True) == "C"


@pytest.mark.parametrize(
    "selected, cases", [(REVISION, ["QMax", "QMin"]), (LATER_REVISION, ["Qzero"])]
)
def test_the_overvoltage_still_tests_each_end_of_the_reactive_range(
    revision, description, selected, cases
):
    revision(selected)
    description("performance", "PPM", "PCS_RTE-I7")

    assert config.get_list("PCS-OperatingConditions", "PCS_RTE-I7.GridVoltageSwell") == cases


@pytest.mark.parametrize(
    "selected, cases",
    [(REVISION, ["TransientBolted"]), (LATER_REVISION, ["TransientBolted", "TransientImpedant"])],
)
def test_the_short_circuit_is_still_a_bolted_fault_alone(revision, description, selected, cases):
    revision(selected)
    description("performance", "PPM", "PCS_RTE-I5")

    assert config.get_list("PCS-OperatingConditions", "PCS_RTE-I5.ThreePhaseFault") == cases


@pytest.mark.parametrize("selected, pdr_u", [(REVISION, "Udim"), (LATER_REVISION, "Unom")])
def test_the_dip_still_starts_from_the_dimensioning_voltage(
    revision, description, value, selected, pdr_u
):
    revision(selected)
    description("performance", "PPM", "PCS_RTE-I6")

    assert value("PCS_RTE-I6.GridVoltageDip.Qzero.Model", "pdr_U") == pdr_u


@pytest.mark.parametrize("selected, limit", [(REVISION, 0.10), (LATER_REVISION, None)])
def test_the_reaction_time_keeps_its_limit(revision, selected, limit):
    revision(selected)

    assert config.get_threshold("GridCode", "thr_reaction_time", -1.0) == limit


@pytest.mark.parametrize("selected, voltage", [(REVISION, "Udim"), (LATER_REVISION, "Unom")])
def test_the_short_circuit_impedance_is_still_that_of_the_dimensioning_voltage(
    revision, selected, voltage
):
    revision(selected)

    assert config.get_value("GridCode", "zcc_voltage") == voltage
