#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
from dycov.report.tables.compliance import create_map


def test_create_map_all_keys_present():
    results = {
        "no_disconnection_gen": True,
        "stabilized": False,
        "no_disconnection_load": True,
        "freq1": 12.345,
        "freq1_check": True,
        "AVR_5": 0.123,
        "AVR_5_check": False,
        "static_diff": 0.05,
        "static_diff_check": True,
        "imax_reac": 1.234,
        "imax_reac_check": False,
        "time_5U": 9.876,
        "time_5U_check": True,
        "time_10U": 4.321,
        "time_10U_check": False,
        "time_5P": 8.765,
        "time_5P_check": True,
        "time_5P_clear": 7.654,
        "time_5P_clear_check": False,
        "time_10P": 3.210,
        "time_10P_check": True,
        "time_10P_clear": 2.109,
        "time_10P_clear_check": False,
        "time_10Pfloor_clear": 1.098,
        "time_10Pfloor_clear_check": True,
        "time_5P_85U": 6.543,
        "time_5P_85U_check": False,
        "time_10P_85U": 5.432,
        "time_10P_85U_check": True,
        "time_10Pfloor_85U": 0.987,
        "time_10Pfloor_85U_check": False,
    }
    table = create_map(results)
    assert isinstance(table, list)
    # There should be 7 main checks + 5 simple times + 3 composed times = 18 rows
    assert len(table) == 15
    # Check a few representative rows for correct structure and formatting
    assert table[0][0] == "Unit not disconnected by protections"
    assert table[0][2] in ("True", "\\textcolor{red}{ False }")
    assert table[3][0] == "Frequency remains within [49, 51] Hz"
    assert table[3][1].startswith("\\footnote")
    assert table[4][0] == "Stator voltage within $\pm 5\%$ of setpoint"
    assert table[10][0] == "$T_{10P}  - T_{clear} < 5 s$"
    assert table[-1][0] == "$T_{10P_{floor}} - T_{85U} < 2 s$"


def test_create_map_value_formatting():
    results = {
        "freq1": 0.00001,  # Should be formatted as "0.0" (below minimum_value)
        "freq1_check": True,
        "AVR_5": 1.23456,  # Should be formatted as "1.23"
        "AVR_5_check": False,
        "imax_reac": 2.34567,
        "imax_reac_check": True,
    }
    table = create_map(results)
    # freq1 should have seconds unit and be formatted as "0.0s"
    freq_row = next(row for row in table if row[0] == "Frequency remains within [49, 51] Hz")
    assert freq_row[1].endswith("s")
    assert "1e-05s" in freq_row[1]
    # AVR_5 should be formatted as "1.23s"
    avr_row = next(row for row in table if row[0].startswith("Stator voltage"))
    assert "1.23s" in avr_row[1]
    # imax_reac should be formatted as "2.35s"
    imax_row = next(row for row in table if row[0].startswith("Reactive inj."))
    assert "2.35s" in imax_row[1]


def test_create_map_time_checks_inclusion():
    results = {
        "time_5U": 1.1,
        "time_5U_check": True,
        "time_10U": 2.2,
        "time_10U_check": False,
        "time_5P_85U": 3.3,
        "time_5P_85U_check": True,
        "time_10P_85U": 4.4,
        "time_10P_85U_check": False,
        "time_10Pfloor_85U": 5.5,
        "time_10Pfloor_85U_check": True,
    }
    table = create_map(results)
    # Should include all simple and composed time checks present in results
    labels = [row[0] for row in table]
    assert "$T_{5U} < 10 s$" in labels
    assert "$T_{10U} < 5 s$" in labels
    assert "$T_{5P}  - T_{85U} < 10 s$" in labels
    assert "$T_{10P}  - T_{85U} < 5 s$" in labels
    assert "$T_{10P_{floor}} - T_{85U} < 2 s$" in labels


def test_create_map_empty_results():
    results = {}
    table = create_map(results)
    assert table == []


def test_create_map_missing_keys():
    # Only provide a subset of possible keys
    results = {
        "no_disconnection_gen": True,
        "freq1": 1.23,
        "freq1_check": False,
        # Missing "stabilized", "no_disconnection_load", etc.
    }
    table = create_map(results)
    labels = [row[0] for row in table]
    assert "Unit not disconnected by protections" in labels
    assert "Frequency remains within [49, 51] Hz" in labels
    assert "Unit remains stable (rotor stability)" not in labels
    assert "Aux not disconnected by protections" not in labels
