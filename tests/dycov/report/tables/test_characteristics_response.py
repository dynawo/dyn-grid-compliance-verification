#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
from dycov.report.tables import characteristics_response


def test_create_map_with_complete_valid_results():
    results = {
        "calc_reaction_time": 1.23,
        "ref_reaction_time": 1.20,
        "reaction_time_error": 0.03,
        "reaction_time_thr": 0.05,
        "reaction_time_check": "True",
        "calc_rise_time": 2.34,
        "ref_rise_time": 2.30,
        "rise_time_error": 0.04,
        "rise_time_thr": 0.06,
        "rise_time_check": "True",
        "calc_settling_time": 3.45,
        "ref_settling_time": 3.40,
        "settling_time_error": 0.05,
        "settling_time_thr": 0.07,
        "settling_time_check": "True",
        "calc_overshoot": 4.56,
        "ref_overshoot": 4.50,
        "overshoot_error": 0.06,
        "overshoot_thr": 0.08,
        "overshoot_check": "True",
        "ramp_time_lag": 0.12,
        "ramp_time_thr": 0.15,
        "ramp_time_check": True,
        "ramp_error": 0.22,
        "ramp_error_thr": 0.25,
        "ramp_error_check": True,
    }
    table = characteristics_response.create_map(results)
    # There should be 6 rows: 4 time errors + 2 ramp errors
    assert len(table) == 6
    # Check structure of first row (Reaction time)
    row = table[0]
    assert row[0] == "Reaction time"
    assert isinstance(row[1], str)
    assert isinstance(row[2], str)
    assert isinstance(row[3], str)
    assert isinstance(row[4], str)
    assert isinstance(row[5], str)
    # Check that ramp error row is present and formatted
    ramp_row = table[4]
    assert ramp_row[0] == "Ramp time lag"
    assert ramp_row[3] == "0.12"
    assert ramp_row[5] == "{ True }"


def test_time_error_with_valid_time_keys():
    results = {
        "calc_test_time": 5.67,
        "ref_test_time": 5.60,
        "test_time_error": 0.07,
        "test_time_thr": 0.09,
        "test_time_check": "N/A",
    }
    errors_map = []
    characteristics_response._time_error(results, "Test time", "test_time", errors_map)
    assert len(errors_map) == 1
    row = errors_map[0]
    assert row[0] == "Test time"
    assert row[1] == "5.67"
    assert row[2] == "5.6"
    assert row[3] == "0.07"
    assert row[4] == "0.09"
    assert row[5] == "{ N/A }"


def test_ramp_error_with_valid_ramp_keys():
    results = {
        "ramp_var": 0.33,
        "ramp_thr_var": 0.44,
        "ramp_check_var": False,
    }
    errors_map = []
    characteristics_response._ramp_error(
        results, "Ramp test", "ramp_var", "ramp_thr_var", "ramp_check_var", errors_map
    )
    assert len(errors_map) == 1
    row = errors_map[0]
    assert row[0] == "Ramp test"
    assert row[3].startswith("\\textcolor{red}{")
    assert row[4] == "0.44"
    assert row[5] == "\\textcolor{red}{ False }"


def test_create_map_with_missing_keys():
    results = {
        # Only overshoot keys present
        "calc_overshoot": 1.1,
        "ref_overshoot": 1.0,
        "overshoot_error": 0.1,
        "overshoot_thr": 0.2,
        "overshoot_check": "True",
    }
    table = characteristics_response.create_map(results)
    # Only one time error row should be present
    assert len(table) == 1
    assert table[0][0] == "Overshoot"
