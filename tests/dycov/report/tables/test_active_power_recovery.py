#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import pytest

from dycov.report.tables.active_power_recovery import create_map


def test_create_map_returns_table_row_with_valid_input():
    results = {
        "t_P90_error": 0.012345,
        "t_P90_threshold": 0.1,
        "t_P90_check": True,
    }
    table = create_map(results)
    assert isinstance(table, list)
    assert len(table) == 1
    row = table[0]

    expected = r"$Err_{T_\text{90P}} < min(10\% T_\text{$90P_\text{ref}$}, 100ms)$"
    assert row[0] == expected
    assert row[1] == "0.0123"
    assert row[2] == "0.1"
    assert row[3] == "{ True }"


def test_create_map_applies_formatting_to_numerical_values():
    results = {
        "t_P90_error": 1e-10,  # Below minimum_value, should be formatted as "0.0"
        "t_P90_threshold": 1.23456,  # Should be formatted as "1.23"
        "t_P90_check": True,
    }
    table = create_map(results)
    assert table[0][1] == "0.0"
    assert table[0][2] == "1.23"


def test_create_map_formats_boolean_check_value():
    results_true = {
        "t_P90_error": 0.05,
        "t_P90_threshold": 0.2,
        "t_P90_check": True,
    }
    results_false = {
        "t_P90_error": 0.05,
        "t_P90_threshold": 0.2,
        "t_P90_check": False,
    }
    table_true = create_map(results_true)
    table_false = create_map(results_false)
    assert table_true[0][3] == "{ True }"
    assert table_false[0][3] == "\\textcolor{red}{ False }"


def test_create_map_returns_empty_list_when_key_missing():
    results = {
        "t_P90_threshold": 0.2,
        "t_P90_check": True,
    }
    table = create_map(results)
    assert table == []


def test_create_map_raises_keyerror_when_check_missing():
    results = {
        "t_P90_error": 0.05,
        "t_P90_threshold": 0.2,
        # "t_P90_check" is missing
    }
    with pytest.raises(KeyError):
        create_map(results)


def test_create_map_handles_invalid_value_types():
    # Non-numeric for t_P90_error and t_P90_threshold, non-boolean for t_P90_check
    results = {
        "t_P90_error": "not_a_number",
        "t_P90_threshold": None,
        "t_P90_check": "not_a_bool",
    }
    with pytest.raises((ValueError, TypeError)):
        create_map(results)
