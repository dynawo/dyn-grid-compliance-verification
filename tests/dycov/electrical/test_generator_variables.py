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
    ("GridCode", "Udim_90kV"): 90.0,
    ("GridCode", "Udim_225kV"): 235.0,
    ("GridCode", "Udim_400kV"): 405.0,
    ("GridCode", "category_voltage_threshold"): 110.0,
}

HTB_LISTS = {
    "HTB1_Udims": ["90"],
    "HTB2_Udims": ["225"],
    "HTB3_Udims": ["400"],
    "HTB1_External_Udims": [],
    "HTB2_External_Udims": [],
    "HTB3_External_Udims": [],
    "category_thresholds": ["1", "18", "75"],
    "category_thresholds_high_voltage": ["0", "0", "0"],
    "category_storage_thresholds_high_voltage": ["1", "18", "50"],
}


def _read_grid_code_from(monkeypatch, table: dict) -> None:
    """The configuration answers from the table, whatever its layers hold."""
    monkeypatch.setattr(
        "dycov.configuration.cfg.Config.get_float",
        lambda self, section, key, default=0.0: float(table.get((section, key), default)),
    )
    monkeypatch.setattr(
        "dycov.configuration.cfg.Config.get_value",
        lambda self, section, key, default=None: (
            str(table[(section, key)]) if (section, key) in table else default
        ),
    )
    monkeypatch.setattr(
        "dycov.configuration.cfg.Config.has_option",
        lambda self, section, key: (section, key) in table,
    )
    monkeypatch.setattr(
        "dycov.configuration.cfg.Config.get_list",
        lambda self, section, key: (
            str(table[(section, key)]).split(",")
            if (section, key) in table
            else HTB_LISTS.get(key, [])
        ),
    )


@pytest.fixture
def generator_variables(monkeypatch):
    _read_grid_code_from(monkeypatch, GRID_CODE_FLOATS)
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


@pytest.mark.parametrize("s_nom", [100.0, 200.0])
def test_calculate_fault_xpu_gives_the_example_of_the_dtr(generator_variables, s_nom):
    """A unit of 225 kV at Pmax = 0.94 Snom, where b = 0.3, faults through 0.29 pu (Udim, Snom)."""
    x_dynawo = generator_variables.calculate_fault_xpu(-0.94 * s_nom / 100.0, s_nom, 225, 100.0)

    x_dtr = x_dynawo / ((235.0 / 225.0) ** 2 * (100.0 / s_nom))
    assert x_dtr == pytest.approx(0.29, abs=0.005)


@pytest.mark.parametrize(
    "u_nom, u_dim, p_max, s_nom, b",
    [
        (90, 90.0, 40.0, 45.0, 0.2),
        (90, 90.0, 60.0, 70.0, 0.3),
        (225, 235.0, 94.0, 100.0, 0.3),
        (225, 235.0, 300.0, 320.0, 0.54),
        (400, 405.0, 500.0, 600.0, 0.54),
        (400, 405.0, 900.0, 1000.0, 0.6),
    ],
)
def test_calculate_fault_xpu_holds_the_pdr_at_60_percent_of_unom(
    generator_variables, u_nom, u_dim, p_max, s_nom, b
):
    """Behind the four lines of 3*b, from the infinite bus that gives Udim at Pmax, the fault
    divides the voltage down to 0.6 Unom at the PDR once the unit injects no current."""
    s_nref = 100.0
    grid_x = 0.75 * b * (u_dim / u_nom) ** 2 * (s_nref / s_nom)
    u_pdr = u_dim / u_nom
    u_inf = abs(u_pdr - 1j * grid_x * (p_max / s_nref) / u_pdr)

    fault_x = generator_variables.calculate_fault_xpu(-p_max / s_nref, s_nom, u_nom, s_nref)

    assert u_inf * fault_x / (fault_x + grid_x) == pytest.approx(0.6)


def test_calculate_fault_xpu_raises_for_unknown_level(generator_variables):
    with pytest.raises(ValueError, match="33"):
        generator_variables.calculate_fault_xpu(-0.1, 100.0, 33, 100.0)


@pytest.mark.parametrize(
    "u_nom, p_max, category",
    [
        (90, 0.5, "A"),
        (90, 1.0, "B"),
        (90, 18.0, "C"),
        (90, 74.9, "C"),
        (90, 75.0, "D"),
        (225, 0.5, "D"),
        (225, 18.0, "D"),
        (400, 1.0, "D"),
    ],
)
def test_get_generator_category_of_a_production_unit(generator_variables, u_nom, p_max, category):
    """Above 110 kV a production unit is type D whatever its power, and below it from 75 MW."""
    assert generator_variables.get_generator_category(u_nom, p_max, False) == category


def test_a_revision_moves_the_category_by_moving_a_threshold(generator_variables, monkeypatch):
    """A revision that gives the type D a floor of 30 MW writes the powers and nothing else."""
    assert generator_variables.get_generator_category(225, 18.0, False) == "D"

    monkeypatch.setitem(HTB_LISTS, "category_thresholds_high_voltage", ["1", "18", "30"])

    assert generator_variables.get_generator_category(225, 18.0, False) == "C"
    assert generator_variables.get_generator_category(225, 30.0, False) == "D"


@pytest.mark.parametrize(
    "u_nom, p_max, category",
    [
        (90, 74.9, "C"),
        (90, 75.0, "D"),
        (225, 18.0, "C"),
        (225, 49.9, "C"),
        (225, 50.0, "D"),
    ],
)
def test_get_generator_category_of_a_storage_unit(generator_variables, u_nom, p_max, category):
    """Above 110 kV a storage unit is type D from 50 MW, by its own table of the DTR."""
    assert generator_variables.get_generator_category(u_nom, p_max, True) == category


@pytest.fixture
def reactances(monkeypatch, generator_variables):
    """The [GridCode] of a revision that gives a technology reactances of its own: a PPM in
    four steps, a storage unit in the two steps of _b_low and _b_high."""
    table = dict(GRID_CODE_FLOATS)
    table[("GridCode", "HTB1_reactance_b_PPM")] = "0.2, 0.3, 0.54, 0.6"
    table[("GridCode", "HTB1_p_max_PPM")] = "50, 250, 800"
    table[("GridCode", "HTB1_reactance_b_low_BESS")] = 0.3
    table[("GridCode", "HTB1_reactance_b_high_BESS")] = 0.3
    _read_grid_code_from(monkeypatch, table)
    return table


@pytest.mark.parametrize(
    "technology, p_max, b",
    [
        ("PPM", 40.0, 0.2),
        ("PPM", 60.0, 0.3),
        ("PPM", 250.0, 0.54),
        ("PPM", 300.0, 0.54),
        ("PPM", 800.0, 0.6),
        ("SM", 40.0, 0.2),
        ("SM", 50.0, 0.3),
        ("SM", 900.0, 0.3),
        ("BESS", 40.0, 0.3),
        ("BESS", 60.0, 0.3),
        (None, 40.0, 0.2),
    ],
)
def test_the_reactance_b_of_a_technology_wins_over_the_plain_one(
    generator_variables, reactances, technology, p_max, b
):
    result = generator_variables.calculate_line_xpu(
        "b", -p_max / 100.0, 100.0, 90, 100.0, technology
    )

    assert result == pytest.approx(b)


def test_the_reactances_are_read_when_they_are_computed(
    generator_variables, reactances, monkeypatch
):
    """A revision of the DTR is selected after the tool has started."""
    monkeypatch.setitem(reactances, ("GridCode", "HTB1_reactance_b_PPM"), "0.25, 0.3, 0.54, 0.6")

    result = generator_variables.calculate_line_xpu("b", -0.4, 100.0, 90, 100.0, "PPM")

    assert result == pytest.approx(0.25)


def test_steps_of_b_that_do_not_match_their_powers_are_rejected(
    generator_variables, reactances, monkeypatch
):
    """The message names the keys of the technology it read, so the user finds them."""
    monkeypatch.setitem(reactances, ("GridCode", "HTB1_reactance_b_PPM"), "0.2, 0.3, 0.54")

    with pytest.raises(ValueError, match="HTB1_reactance_b_PPM.*HTB1_p_max_PPM"):
        generator_variables.calculate_line_xpu("b", -0.4, 100.0, 90, 100.0, "PPM")


def test_two_steps_of_b_that_do_not_match_their_powers_name_the_keys_read(
    generator_variables, reactances, monkeypatch
):
    monkeypatch.setitem(reactances, ("GridCode", "HTB1_p_max_BESS"), "50, 250")

    with pytest.raises(
        ValueError, match="HTB1_reactance_b_low_BESS.*HTB1_reactance_b_high_BESS.*HTB1_p_max_BESS"
    ):
        generator_variables.calculate_line_xpu("b", -0.4, 100.0, 90, 100.0, "BESS")


def test_powers_of_b_that_do_not_rise_are_rejected(generator_variables, reactances, monkeypatch):
    monkeypatch.setitem(reactances, ("GridCode", "HTB1_p_max_PPM"), "800, 250, 50")

    with pytest.raises(ValueError, match="HTB1_p_max_PPM.*rise"):
        generator_variables.calculate_line_xpu("b", -0.4, 100.0, 90, 100.0, "PPM")


def test_a_power_of_b_that_is_no_number_names_its_key(
    generator_variables, reactances, monkeypatch
):
    monkeypatch.setitem(reactances, ("GridCode", "HTB1_p_max_PPM"), "50, x, 800")

    with pytest.raises(ValueError, match="HTB1_p_max_PPM"):
        generator_variables.calculate_line_xpu("b", -0.4, 100.0, 90, 100.0, "PPM")


def test_the_fault_takes_the_reactance_b_of_the_technology(generator_variables, reactances):
    storage = generator_variables.calculate_fault_xpu(-0.4, 100.0, 90, 100.0, "BESS")
    synchronous = generator_variables.calculate_fault_xpu(-0.4, 100.0, 90, 100.0, "SM")

    assert storage > synchronous


def test_the_short_circuit_power_is_that_of_the_configuration(generator_variables, monkeypatch):
    monkeypatch.setitem(GRID_CODE_FLOATS, ("GridCode", "HTB2_Scc"), 1600.0)

    assert generator_variables.get_scc(225) == pytest.approx(1600.0)
