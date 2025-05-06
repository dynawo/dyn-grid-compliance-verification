#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
import pytest

from dycov.report.tables import thresholds


class DummyThresholdVariables:
    @staticmethod
    def get_setpoint_tracking_threshold_values():
        return {
            "before": {"mxe": 0.11, "me": 0.12, "mae": 0.13},
            "during": {"mxe": 0.21, "me": 0.22, "mae": 0.23},
            "after": {"mxe": 0.31, "me": 0.32, "mae": 0.33},
        }

    @staticmethod
    def get_voltage_dip_threshold_values(measurement_name, is_field_measurements):
        return {
            "before": {"mxe": 0.41, "me": 0.42, "mae": 0.43},
            "during": {"mxe": 0.51, "me": 0.52, "mae": 0.53},
            "after": {"mxe": 0.61, "me": 0.62, "mae": 0.63},
        }


@pytest.fixture(autouse=True)
def patch_threshold_variables(monkeypatch):
    monkeypatch.setattr(thresholds, "threshold_variables", DummyThresholdVariables)
    yield


def test_create_map_all_checks_present():
    results = {
        "setpoint_tracking_controlled_magnitude_check": True,
        "setpoint_tracking_controlled_magnitude_name": "CM",
        "during_mxe_controlled_magnitude_value": 1,
        "setpoint_tracking_active_power_check": True,
        "setpoint_tracking_active_power_name": "P",
        "during_mxe_active_power_value": 1,
        "setpoint_tracking_reactive_power_check": True,
        "setpoint_tracking_reactive_power_name": "Q",
        "during_mxe_reactive_power_value": 1,
        "voltage_dips_voltage_check": True,
        "during_mxe_voltage_value": 1,
        "voltage_dips_active_power_check": True,
        "during_mxe_active_power_value": 1,
        "voltage_dips_reactive_power_check": True,
        "during_mxe_reactive_power_value": 1,
        "voltage_dips_active_current_check": True,
        "during_mxe_active_current_value": 1,
        "voltage_dips_reactive_current_check": True,
        "during_mxe_reactive_current_value": 1,
    }
    is_field_measurements = False
    result = thresholds.create_map(results, is_field_measurements)
    # Each entry should have 10 elements (name + 3*3 windows)
    assert len(result) == 8
    for entry in result:
        assert len(entry) == 10
    # Check that the first entry matches the expected values for controlled_magnitude
    assert result[0][0] == "CM"
    assert result[0][1:] == [0.11, 0.12, 0.13, 0.21, 0.22, 0.23, 0.31, 0.32, 0.33]


def test_create_map_all_keys_present():
    results = {
        "setpoint_tracking_controlled_magnitude_check": True,
        "setpoint_tracking_controlled_magnitude_name": "CM",
        "during_mxe_controlled_magnitude_value": 0.0,
        "setpoint_tracking_active_power_check": True,
        "setpoint_tracking_active_power_name": "P",
        "during_mxe_active_power_value": 0.0,
        "setpoint_tracking_reactive_power_check": True,
        "setpoint_tracking_reactive_power_name": "Q",
        "during_mxe_reactive_power_value": 0.0,
        "voltage_dips_voltage_check": True,
        "during_mxe_voltage_value": 0.0,
        "voltage_dips_active_power_check": True,
        "during_mxe_active_power_value": 0.0,
        "voltage_dips_reactive_power_check": True,
        "during_mxe_reactive_power_value": 0.0,
        "voltage_dips_active_current_check": True,
        "during_mxe_active_current_value": 0.0,
        "voltage_dips_reactive_current_check": True,
        "during_mxe_reactive_current_value": 0.0,
    }
    is_field_measurements = False
    result = thresholds.create_map(results, is_field_measurements)
    # All entries should have 10 elements (with 'during' window)
    assert len(result) == 8
    for row in result:
        assert len(row) == 10


def test_setpoint_tracking_thresholds_with_during_window():
    results = {
        "setpoint_tracking_active_power_check": True,
        "setpoint_tracking_active_power_name": "P",
        "during_mxe_active_power_value": 0.0,
    }
    thresholds_map = []
    thresholds._setpoint_tracking_thresholds(results, "active_power", thresholds_map)
    assert len(thresholds_map) == 1
    entry = thresholds_map[0]
    assert entry[0] == "P"
    assert entry[1:] == [0.11, 0.12, 0.13, 0.21, 0.22, 0.23, 0.31, 0.32, 0.33]


def test_voltage_dips_thresholds_missing_during():
    results = {
        "voltage_dips_voltage_check": True,
    }
    thresholds_map = []
    thresholds._voltage_dips_thresholds(results, "V", "voltage", False, thresholds_map)
    assert len(thresholds_map) == 1
    entry = thresholds_map[0]
    assert entry[0] == "V"
    # Should only have before and after (7 elements)
    assert entry[1:] == [0.41, 0.42, 0.43, 0.61, 0.62, 0.63]
    assert len(entry) == 7


def test_create_map_no_checks_present():
    results = {}
    is_field_measurements = True
    result = thresholds.create_map(results, is_field_measurements)
    assert result == []


def test_get_measurement_name_unknown():
    assert thresholds._get_measurement_name("unknown_measurement") is None


def test_setpoint_tracking_thresholds_missing_check_key():
    results = {
        # No "setpoint_tracking_active_power_check" key
        "setpoint_tracking_active_power_name": "P",
        "during_mxe_active_power_value": 1,
    }
    thresholds_map = []
    thresholds._setpoint_tracking_thresholds(results, "active_power", thresholds_map)
    assert thresholds_map == []
