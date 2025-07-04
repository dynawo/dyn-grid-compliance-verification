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

from dycov.validation.threshold_variables import (
    get_setpoint_tracking_threshold_values,
    get_voltage_dip_threshold_values,
)


def test_get_voltage_dip_threshold_values_simulation_known_measurement():
    # This test assumes that the config object returns the default values for missing keys.
    # The expected values are the defaults as per the implementation for simulation mode.
    expected = {
        "before": {"mxe": 0.05, "me": 0.02, "mae": 0.03},
        "during": {"mxe": 0.08, "me": 0.05, "mae": 0.07},
        "after": {"mxe": 0.05, "me": 0.02, "mae": 0.03},
    }
    result = get_voltage_dip_threshold_values(
        "BusPDR_BUS_ActivePower", is_field_measurements=False
    )
    assert result == expected


def test_get_voltage_dip_threshold_values_test_known_measurement():
    # This test assumes that the config object returns the default values for missing keys.
    # The expected values are the defaults as per the implementation for test mode.
    expected = {
        "before": {"mxe": 0.08, "me": 0.04, "mae": 0.07},
        "during": {"mxe": 0.10, "me": 0.05, "mae": 0.08},
        "after": {"mxe": 0.08, "me": 0.04, "mae": 0.07},
    }
    result = get_voltage_dip_threshold_values("BusPDR_BUS_ActivePower", is_field_measurements=True)
    assert result == expected


def test_get_setpoint_tracking_threshold_values_structure():
    expected = {
        "before": {"mxe": 0.05, "me": 0.02, "mae": 0.03},
        "during": {"mxe": 0.08, "me": 0.05, "mae": 0.07},
        "after": {"mxe": 0.05, "me": 0.02, "mae": 0.03},
    }
    result = get_setpoint_tracking_threshold_values()
    assert isinstance(result, dict)
    assert set(result.keys()) == {"before", "during", "after"}
    for window in ["before", "during", "after"]:
        assert set(result[window].keys()) == {"mxe", "me", "mae"}
        for key in ["mxe", "me", "mae"]:
            assert pytest.approx(result[window][key]) == expected[window][key]
