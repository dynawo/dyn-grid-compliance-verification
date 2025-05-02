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

from dycov.report.tables import thresholds


class DummyThresholdVariables:
    @staticmethod
    def get_setpoint_tracking_threshold_values():
        return {
            "before": {"mxe": 0.1, "me": 0.2, "mae": 0.3},
            "during": {"mxe": 0.4, "me": 0.5, "mae": 0.6},
            "after": {"mxe": 0.7, "me": 0.8, "mae": 0.9},
        }

    @staticmethod
    def get_voltage_dip_threshold_values(measurement_name, is_field_measurements):
        return {
            "before": {"mxe": 1.1, "me": 1.2, "mae": 1.3},
            "during": {"mxe": 1.4, "me": 1.5, "mae": 1.6},
            "after": {"mxe": 1.7, "me": 1.8, "mae": 1.9},
        }


@pytest.fixture(autouse=True)
def patch_threshold_variables(monkeypatch):
    monkeypatch.setattr(thresholds, "threshold_variables", DummyThresholdVariables)
    yield


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
    row = thresholds_map[0]
    # Should include 'during' window, so 10 elements
    assert len(row) == 10
    assert row[0] == "P"
    assert row[1:4] == [0.1, 0.2, 0.3]
    assert row[4:7] == [0.4, 0.5, 0.6]
    assert row[7:10] == [0.7, 0.8, 0.9]


def test_voltage_dips_thresholds_with_during_window():
    results = {
        "voltage_dips_voltage_check": True,
        "during_mxe_voltage_value": 0.0,
    }
    thresholds_map = []
    thresholds._voltage_dips_thresholds(results, "V", "voltage", False, thresholds_map)
    assert len(thresholds_map) == 1
    row = thresholds_map[0]
    # Should include 'during' window, so 10 elements
    assert len(row) == 10
    assert row[0] == "V"
    assert row[1:4] == [1.1, 1.2, 1.3]
    assert row[4:7] == [1.4, 1.5, 1.6]
    assert row[7:10] == [1.7, 1.8, 1.9]


def test_create_map_no_keys_present():
    results = {}
    is_field_measurements = True
    result = thresholds.create_map(results, is_field_measurements)
    assert result == []


def test_get_measurement_name_unknown_measurement():
    assert thresholds._get_measurement_name("unknown_measurement") is None


def test_thresholds_functions_missing_check_key():
    # _setpoint_tracking_thresholds
    results_st = {
        "setpoint_tracking_active_power_name": "P",
        "during_mxe_active_power_value": 0.0,
    }
    thresholds_map_st = []
    thresholds._setpoint_tracking_thresholds(results_st, "active_power", thresholds_map_st)
    assert thresholds_map_st == []

    # _voltage_dips_thresholds
    results_vd = {
        "during_mxe_voltage_value": 0.0,
    }
    thresholds_map_vd = []
    thresholds._voltage_dips_thresholds(results_vd, "V", "voltage", False, thresholds_map_vd)
    assert thresholds_map_vd == []
