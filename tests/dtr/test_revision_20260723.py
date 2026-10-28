#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""What the revision 20260723 writes differently from the base 20240215.

Each test reads the two revisions one after the other, so the table of the test shows the
change itself and not only the value that applies today. A run reads the base plus one
delta, which is what the fixture ``revision`` selects here.
"""

import pytest

from dycov.configuration.cfg import config, is_base_revision
from dycov.electrical.generator_variables import generator_variables

BASE_REVISION = "20240215"
REVISION = "20260723"


def test_the_tool_implements_both_revisions():
    """A run that asks for a revision the tool does not implement stops."""
    available = config.get_list("DTR", "available")

    assert BASE_REVISION in available
    assert REVISION in available


def test_the_base_revision_reads_no_delta(revision, description):
    """The catalogue the tool ships is the base, so a run that follows it reads it alone."""
    assert is_base_revision(BASE_REVISION)

    revision(BASE_REVISION)
    description("performance", "PPM", "PCS_RTE-I7")

    assert config.get_list("GridCode", "category_thresholds_high_voltage") == ["0", "0", "0"]
    assert config.get_list("PCS-OperatingConditions", "PCS_RTE-I7.GridVoltageSwell") == [
        "QMax",
        "QMin",
    ]


@pytest.mark.parametrize("selected, category", [(BASE_REVISION, "D"), (REVISION, "C")])
def test_a_production_unit_of_20_MW_at_225_kV_changes_category(revision, selected, category):
    """The base makes every unit above 110 kV a type D. 20260723 reads its power."""
    revision(selected)

    assert generator_variables.get_generator_category(225, 20, False) == category


@pytest.mark.parametrize("p_max, category", [(0.5, "A"), (10, "B"), (20, "C"), (60, "D")])
def test_20260723_gives_a_unit_above_110_kV_a_table_of_its_own(revision, p_max, category):
    """Article 5.1.1 takes the thresholds 1, 18 and 30 MW, where the base took none."""
    revision(REVISION)

    assert generator_variables.get_generator_category(225, p_max, False) == category


def test_20260723_leaves_the_table_of_a_storage_unit_as_it_is(revision):
    """A unit of 40 MW above 110 kV: type D when it produces, type C when it stores."""
    revision(REVISION)

    assert generator_variables.get_generator_category(225, 40, False) == "D"
    assert generator_variables.get_generator_category(225, 40, True) == "C"


@pytest.mark.parametrize(
    "selected, technology, cases",
    [
        (BASE_REVISION, "SM", ["QMax", "QMin"]),
        (REVISION, "SM", ["Qzero"]),
        (BASE_REVISION, "PPM", ["QMax", "QMin"]),
        (REVISION, "PPM", ["Qzero"]),
        (
            BASE_REVISION,
            "BESS",
            ["QMaxInjection", "QMinInjection", "QMaxConsumption", "QMinConsumption"],
        ),
        (REVISION, "BESS", ["QzeroInjection", "QzeroConsumption"]),
    ],
)
def test_the_overvoltage_moves_to_one_reactive_setpoint(
    revision, description, selected, technology, cases
):
    """The fiche I7 tested each end of the reactive range, and now tests zero reactive power."""
    revision(selected)
    description("performance", technology, "PCS_RTE-I7")

    assert config.get_list("PCS-OperatingConditions", "PCS_RTE-I7.GridVoltageSwell") == cases


@pytest.mark.parametrize(
    "selected, technology, cases",
    [
        (BASE_REVISION, "PPM", ["TransientBolted"]),
        (REVISION, "PPM", ["TransientBolted", "TransientImpedant"]),
        (BASE_REVISION, "BESS", ["TransientBoltedInjection", "TransientBoltedConsumption"]),
        (
            REVISION,
            "BESS",
            [
                "TransientBoltedInjection",
                "TransientBoltedConsumption",
                "TransientImpedantInjection",
                "TransientImpedantConsumption",
            ],
        ),
    ],
)
def test_the_short_circuit_adds_an_impedant_fault(
    revision, description, selected, technology, cases
):
    """The fiche I5 tested a bolted fault alone, and now tests an impedant one as well."""
    revision(selected)
    description("performance", technology, "PCS_RTE-I5")

    assert config.get_list("PCS-OperatingConditions", "PCS_RTE-I5.ThreePhaseFault") == cases


@pytest.mark.parametrize(
    "selected, technology, cases",
    [
        (BASE_REVISION, "PPM", ["TransientBolted"]),
        (REVISION, "PPM", ["TransientBolted", "TransientImpedant"]),
        (BASE_REVISION, "BESS", ["TransientBoltedInjection", "TransientBoltedConsumption"]),
        (
            REVISION,
            "BESS",
            [
                "TransientBoltedInjection",
                "TransientBoltedConsumption",
                "TransientImpedantInjection",
                "TransientImpedantConsumption",
            ],
        ),
    ],
)
def test_the_model_validation_of_zone_3_runs_the_same_faults_as_the_fiche_I5(
    revision, description, selected, technology, cases
):
    """The fiche I16 validates the model with the tests of the performance fiches."""
    revision(selected)
    description("model", technology, "PCS_RTE-I16z3")

    assert config.get_list("PCS-OperatingConditions", "PCS_RTE-I16z3.ThreePhaseFault") == cases


@pytest.mark.parametrize("selected, pdr_u", [(BASE_REVISION, "Udim"), (REVISION, "Unom")])
@pytest.mark.parametrize(
    "technology, case", [("SM", "Qzero"), ("PPM", "Qzero"), ("BESS", "QzeroInjection")]
)
def test_the_dip_starts_from_the_nominal_voltage(
    revision, description, value, selected, pdr_u, technology, case
):
    """The unit held Udim before the dip of the fiche I6, and now holds Unom."""
    revision(selected)
    description("performance", technology, "PCS_RTE-I6")

    assert value(f"PCS_RTE-I6.GridVoltageDip.{case}.Model", "pdr_U") == pdr_u


@pytest.mark.parametrize(
    "selected, case, pdr_u",
    [(BASE_REVISION, "QMax", "Udim"), (REVISION, "Qzero", "Unom")],
)
def test_the_overvoltage_starts_from_the_nominal_voltage(
    revision, description, value, selected, case, pdr_u
):
    """The unit held Udim before the swell of the fiche I7, and now holds Unom."""
    revision(selected)
    description("performance", "PPM", "PCS_RTE-I7")

    assert value(f"PCS_RTE-I7.GridVoltageSwell.{case}.Model", "pdr_U") == pdr_u


@pytest.mark.parametrize("selected, limit", [(BASE_REVISION, 0.10), (REVISION, None)])
def test_the_reaction_time_loses_its_limit(revision, selected, limit):
    """20260723 keeps the indicator of the fiche I16 and gives it no criterion.

    The report then states the time and its deviation, and gives no verdict.
    """
    revision(selected)

    assert config.get_threshold("GridCode", "thr_reaction_time", -1.0) == limit
