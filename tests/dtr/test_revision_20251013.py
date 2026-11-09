#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""What the revision 20251013 writes differently from the base 20240215.

Each test reads the two revisions one after the other, so the table of the test shows the
change itself and not only the value that applies today. A run reads the base plus one
delta, which is what the fixture ``revision`` selects here.

Article 8.3.3 v3.6, which 20260723 carries, keeps what v3.5 changed in the fiches both
revisions share, and article 5.1.1 has the same text in both: the last test reads the two
deltas side by side.
"""

import configparser
from pathlib import Path

import pytest

import dycov
from dycov.configuration.cfg import config, is_base_revision
from dycov.electrical.generator_variables import generator_variables

BASE_REVISION = "20240215"
REVISION = "20251013"


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
    """The base makes every unit above 110 kV a type D. 20251013 reads its power."""
    revision(selected)

    assert generator_variables.get_generator_category(225, 20, False) == category


@pytest.mark.parametrize("p_max, category", [(0.5, "A"), (10, "B"), (20, "C"), (60, "D")])
def test_20251013_gives_a_unit_above_110_kV_a_table_of_its_own(revision, p_max, category):
    """Article 5.1.1 takes the thresholds 1, 18 and 30 MW, where the base took none."""
    revision(REVISION)

    assert generator_variables.get_generator_category(225, p_max, False) == category


def test_20251013_leaves_the_table_of_a_storage_unit_as_it_is(revision):
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
    """20251013 keeps the indicator of the fiche I16 and gives it no criterion.

    The report then states the time and its deviation, and gives no verdict.
    """
    revision(selected)

    assert config.get_threshold("GridCode", "thr_reaction_time", -1.0) == limit


@pytest.mark.parametrize("selected, voltage", [(BASE_REVISION, "Udim"), (REVISION, "Unom")])
def test_the_short_circuit_impedance_is_that_of_the_nominal_voltage(revision, selected, voltage):
    """The fiche I6 gave Zcc = Uc^2/Scc, Uc being Udim, and I7 an infinite bus at the
    connection point; both now give Zcc = Un^2/Scc."""
    revision(selected)

    assert config.get_value("GridCode", "zcc_voltage") == voltage


REVISIONS = Path(dycov.__file__).resolve().parent / "templates" / "revisions"


def _options(path: Path) -> dict:
    parser = configparser.ConfigParser(inline_comment_prefixes=("#",), interpolation=None)
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    return {section: dict(parser.items(section, raw=True)) for section in parser.sections()}


def _delta_files(revision: str) -> list[Path]:
    return sorted(
        path.relative_to(REVISIONS / revision)
        for path in (REVISIONS / revision).rglob("*")
        if path.is_file()
    )


@pytest.mark.parametrize("path", _delta_files(REVISION), ids=str)
def test_20260723_writes_what_20251013_writes(path):
    """A delta is written against the base and read alone, so each carries its own copy."""
    later = REVISIONS / "20260723" / path

    assert later.is_file()
    if path.suffix == ".ini":
        assert _options(REVISIONS / REVISION / path) == _options(later)
    else:
        assert (REVISIONS / REVISION / path).read_bytes() == later.read_bytes()


@pytest.mark.parametrize(
    "selected, technology, p_max, b",
    [
        (BASE_REVISION, "PPM", 40.0, 0.2),
        (REVISION, "PPM", 40.0, 0.3),
        (REVISION, "PPM", 240.0, 0.3),
        (REVISION, "PPM", 250.0, 0.54),
        (REVISION, "PPM", 260.0, 0.54),
        (BASE_REVISION, "BESS", 40.0, 0.2),
        (REVISION, "BESS", 40.0, 0.3),
        (REVISION, "BESS", 60.0, 0.3),
        (BASE_REVISION, "SM", 40.0, 0.2),
        (REVISION, "SM", 40.0, 0.2),
    ],
)
def test_a_unit_at_htb1_takes_the_reactance_b_of_its_technology(
    revision, selected, technology, p_max, b
):
    """The capability specifications of PPM and storage give HTB1 a b of 0.3 below 250 MW."""
    revision(selected)

    line_xpu = generator_variables.calculate_line_xpu(
        "b", -p_max / 100, 100.0, 90.0, 100.0, technology
    )

    assert line_xpu == pytest.approx(b)


@pytest.mark.parametrize("selected, zcc", [(BASE_REVISION, False), (REVISION, True)])
def test_the_overvoltage_gains_the_short_circuit_impedance(revision, swell_zcc, selected, zcc):
    """The fiche I7 had the infinite network at the PDR, and now has it behind Zcc, in every
    case of its swell."""
    revision(selected)

    cases = swell_zcc()

    assert cases == dict.fromkeys(cases, zcc)
