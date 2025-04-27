#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
from dycov.report.tables.signal_error import (
    _setpoint_tracking_error,
    _voltage_dips_error,
    create_map,
)


def test_create_map_with_complete_results():
    results = {
        # Setpoint tracking for controlled_magnitude
        "setpoint_tracking_controlled_magnitude_check": True,
        "setpoint_tracking_controlled_magnitude_name": "Controlled Magnitude",
        "before_mxe_tc_controlled_magnitude_value": 0.123,
        "before_mxe_tc_controlled_magnitude_check": True,
        "before_me_tc_controlled_magnitude_value": 0.234,
        "before_me_tc_controlled_magnitude_check": True,
        "before_mae_tc_controlled_magnitude_value": 0.345,
        "before_mae_tc_controlled_magnitude_check": True,
        "after_mxe_tc_controlled_magnitude_value": 0.456,
        "after_mxe_tc_controlled_magnitude_check": True,
        "after_me_tc_controlled_magnitude_value": 0.567,
        "after_me_tc_controlled_magnitude_check": True,
        "after_mae_tc_controlled_magnitude_value": 0.678,
        "after_mae_tc_controlled_magnitude_check": True,
        "during_mxe_tc_controlled_magnitude_value": 0.789,
        "during_mxe_tc_controlled_magnitude_check": True,
        "during_me_tc_controlled_magnitude_value": 0.890,
        "during_me_tc_controlled_magnitude_check": True,
        "during_mae_tc_controlled_magnitude_value": 0.901,
        "during_mae_tc_controlled_magnitude_check": True,
        # Setpoint tracking for active_power
        "setpoint_tracking_active_power_check": False,
        "setpoint_tracking_active_power_name": "Active Power",
        "before_mxe_tc_active_power_value": 0.1,
        "before_mxe_tc_active_power_check": False,
        "before_me_tc_active_power_value": 0.2,
        "before_me_tc_active_power_check": False,
        "before_mae_tc_active_power_value": 0.3,
        "before_mae_tc_active_power_check": False,
        "after_mxe_tc_active_power_value": 0.4,
        "after_mxe_tc_active_power_check": False,
        "after_me_tc_active_power_value": 0.5,
        "after_me_tc_active_power_check": False,
        "after_mae_tc_active_power_value": 0.6,
        "after_mae_tc_active_power_check": False,
        # Setpoint tracking for reactive_power (no 'during' keys)
        "setpoint_tracking_reactive_power_check": True,
        "setpoint_tracking_reactive_power_name": "Reactive Power",
        "before_mxe_tc_reactive_power_value": 0.11,
        "before_mxe_tc_reactive_power_check": True,
        "before_me_tc_reactive_power_value": 0.22,
        "before_me_tc_reactive_power_check": True,
        "before_mae_tc_reactive_power_value": 0.33,
        "before_mae_tc_reactive_power_check": True,
        "after_mxe_tc_reactive_power_value": 0.44,
        "after_mxe_tc_reactive_power_check": True,
        "after_me_tc_reactive_power_value": 0.55,
        "after_me_tc_reactive_power_check": True,
        "after_mae_tc_reactive_power_value": 0.66,
        "after_mae_tc_reactive_power_check": True,
        # Voltage dips for voltage (with 'during')
        "voltage_dips_voltage_check": True,
        "before_mxe_voltage_value": 0.01,
        "before_mxe_voltage_check": True,
        "before_me_voltage_value": 0.02,
        "before_me_voltage_check": True,
        "before_mae_voltage_value": 0.03,
        "before_mae_voltage_check": True,
        "after_mxe_voltage_value": 0.04,
        "after_mxe_voltage_check": True,
        "after_me_voltage_value": 0.05,
        "after_me_voltage_check": True,
        "after_mae_voltage_value": 0.06,
        "after_mae_voltage_check": True,
        "during_mxe_voltage_value": 0.07,
        "during_mxe_voltage_check": True,
        "during_me_voltage_value": 0.08,
        "during_me_voltage_check": True,
        "during_mae_voltage_value": 0.09,
        "during_mae_voltage_check": True,
        # Voltage dips for active_power (no 'during')
        "voltage_dips_active_power_check": False,
        "before_mxe_active_power_value": 0.1,
        "before_mxe_active_power_check": False,
        "before_me_active_power_value": 0.2,
        "before_me_active_power_check": False,
        "before_mae_active_power_value": 0.3,
        "before_mae_active_power_check": False,
        "after_mxe_active_power_value": 0.4,
        "after_mxe_active_power_check": False,
        "after_me_active_power_value": 0.5,
        "after_me_active_power_check": False,
        "after_mae_active_power_value": 0.6,
        "after_mae_active_power_check": False,
        # Voltage dips for reactive_power (no 'during')
        "voltage_dips_reactive_power_check": True,
        "before_mxe_reactive_power_value": 0.11,
        "before_mxe_reactive_power_check": True,
        "before_me_reactive_power_value": 0.22,
        "before_me_reactive_power_check": True,
        "before_mae_reactive_power_value": 0.33,
        "before_mae_reactive_power_check": True,
        "after_mxe_reactive_power_value": 0.44,
        "after_mxe_reactive_power_check": True,
        "after_me_reactive_power_value": 0.55,
        "after_me_reactive_power_check": True,
        "after_mae_reactive_power_value": 0.66,
        "after_mae_reactive_power_check": True,
        # Voltage dips for active_current (no 'during')
        "voltage_dips_active_current_check": True,
        "before_mxe_active_current_value": 0.1,
        "before_mxe_active_current_check": True,
        "before_me_active_current_value": 0.2,
        "before_me_active_current_check": True,
        "before_mae_active_current_value": 0.3,
        "before_mae_active_current_check": True,
        "after_mxe_active_current_value": 0.4,
        "after_mxe_active_current_check": True,
        "after_me_active_current_value": 0.5,
        "after_me_active_current_check": True,
        "after_mae_active_current_value": 0.6,
        "after_mae_active_current_check": True,
        # Voltage dips for reactive_current (no 'during')
        "voltage_dips_reactive_current_check": True,
        "before_mxe_reactive_current_value": 0.11,
        "before_mxe_reactive_current_check": True,
        "before_me_reactive_current_value": 0.22,
        "before_me_reactive_current_check": True,
        "before_mae_reactive_current_value": 0.33,
        "before_mae_reactive_current_check": True,
        "after_mxe_reactive_current_value": 0.44,
        "after_mxe_reactive_current_check": True,
        "after_me_reactive_current_value": 0.55,
        "after_me_reactive_current_check": True,
        "after_mae_reactive_current_value": 0.66,
        "after_mae_reactive_current_check": True,
    }
    table = create_map(results)
    assert isinstance(table, list)
    # 3 setpoint tracking + 5 voltage dips = 8 rows
    assert len(table) == 8
    # Check structure of a row with 'during' (first row)
    assert len(table[0]) == 11
    # Check structure of a row without 'during' (second row)
    assert len(table[1]) == 8
    # Check that the check value is formatted as expected
    assert table[0][-1] == "{ True }"
    assert table[1][-1] == "\\textcolor{red}{ False }"
    # Check that a value is formatted as string
    assert table[0][1] == "0.123"
    # Check that a value with failed check is colored red
    assert table[1][1].startswith("\\textcolor{red}{ ")


def test_setpoint_tracking_error_with_all_keys():
    results = {
        "setpoint_tracking_test_check": True,
        "setpoint_tracking_test_name": "Test Name",
        "before_mxe_tc_test_value": 0.1,
        "before_mxe_tc_test_check": True,
        "before_me_tc_test_value": 0.2,
        "before_me_tc_test_check": False,
        "before_mae_tc_test_value": 0.3,
        "before_mae_tc_test_check": True,
        "after_mxe_tc_test_value": 0.4,
        "after_mxe_tc_test_check": False,
        "after_me_tc_test_value": 0.5,
        "after_me_tc_test_check": True,
        "after_mae_tc_test_value": 0.6,
        "after_mae_tc_test_check": True,
        "during_mxe_tc_test_value": 0.7,
        "during_mxe_tc_test_check": True,
        "during_me_tc_test_value": 0.8,
        "during_me_tc_test_check": True,
        "during_mae_tc_test_value": 0.9,
        "during_mae_tc_test_check": False,
    }
    errors_map = []
    _setpoint_tracking_error(results, "test", errors_map)
    assert len(errors_map) == 1
    row = errors_map[0]
    assert row[0] == "Test Name"
    # before_mxe_tc_test_check is True, so value is not colored
    assert row[1] == "0.1"
    # before_me_tc_test_check is False, so value is colored red
    assert row[2].startswith("\\textcolor{red}{ ")
    # during_mae_tc_test_check is False, so value is colored red
    assert row[6].startswith("\\textcolor{red}{ ")
    # after_mxe_tc_test_check is False, so value is colored red
    assert row[7].startswith("\\textcolor{red}{ ")
    # Check value is formatted as True
    assert row[-1] == "{ True }"


def test_voltage_dips_error_with_all_keys():
    results = {
        "voltage_dips_voltage_check": False,
        "before_mxe_voltage_value": 0.1,
        "before_mxe_voltage_check": True,
        "before_me_voltage_value": 0.2,
        "before_me_voltage_check": True,
        "before_mae_voltage_value": 0.3,
        "before_mae_voltage_check": True,
        "after_mxe_voltage_value": 0.4,
        "after_mxe_voltage_check": True,
        "after_me_voltage_value": 0.5,
        "after_me_voltage_check": True,
        "after_mae_voltage_value": 0.6,
        "after_mae_voltage_check": True,
        "during_mxe_voltage_value": 0.7,
        "during_mxe_voltage_check": False,
        "during_me_voltage_value": 0.8,
        "during_me_voltage_check": True,
        "during_mae_voltage_value": 0.9,
        "during_mae_voltage_check": True,
    }
    errors_map = []
    _voltage_dips_error(results, "V", "voltage", errors_map)
    assert len(errors_map) == 1
    row = errors_map[0]
    assert row[0] == "V"
    # during_mxe_voltage_check is False, so value is colored red
    assert row[4].startswith("\\textcolor{red}{ ")
    # voltage_dips_voltage_check is False, so check is colored red
    assert row[-1] == "\\textcolor{red}{ False }"


def test_create_map_with_missing_keys():
    results = {"some_irrelevant_key": 123, "another_key": "value"}
    table = create_map(results)
    assert table == []


def test_setpoint_tracking_error_missing_check_key():
    results = {
        # "setpoint_tracking_missing_check" is missing
        "setpoint_tracking_missing_name": "Missing",
        "before_mxe_tc_missing_value": 0.1,
        "before_mxe_tc_missing_check": True,
        "before_me_tc_missing_value": 0.2,
        "before_me_tc_missing_check": True,
        "before_mae_tc_missing_value": 0.3,
        "before_mae_tc_missing_check": True,
        "after_mxe_tc_missing_value": 0.4,
        "after_mxe_tc_missing_check": True,
        "after_me_tc_missing_value": 0.5,
        "after_me_tc_missing_check": True,
        "after_mae_tc_missing_value": 0.6,
        "after_mae_tc_missing_check": True,
    }
    errors_map = []
    _setpoint_tracking_error(results, "missing", errors_map)
    assert errors_map == []


def test_voltage_dips_error_without_during_keys():
    results = {
        "voltage_dips_voltage_check": True,
        "before_mxe_voltage_value": 0.1,
        "before_mxe_voltage_check": True,
        "before_me_voltage_value": 0.2,
        "before_me_voltage_check": True,
        "before_mae_voltage_value": 0.3,
        "before_mae_voltage_check": True,
        "after_mxe_voltage_value": 0.4,
        "after_mxe_voltage_check": True,
        "after_me_voltage_value": 0.5,
        "after_me_voltage_check": True,
        "after_mae_voltage_value": 0.6,
        "after_mae_voltage_check": True,
        # No 'during' keys
    }
    errors_map = []
    _voltage_dips_error(results, "V", "voltage", errors_map)
    assert len(errors_map) == 1
    row = errors_map[0]
    # Should have only before/after values and check (8 columns)
    assert len(row) == 8
    assert row[0] == "V"
    assert row[-1] == "{ True }"
