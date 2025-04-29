#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
from dycov.validation.model import (
    _check_value_by_threshold,
    _get_column_name,
    _get_measurement_name,
    _get_ss_tolerance,
)


# Returns correct tolerance when setpoint_variation is 0
def test_zero_setpoint_variation():
    # Arrange
    setpoint_variation = 0.0

    # Act
    result = _get_ss_tolerance(setpoint_variation)

    # Assert
    assert result == 0.005


# Returns correct tolerance when setpoint_variation is 0.1
def test_ss_tolerance():
    # Arrange
    setpoint_variation = 0.1

    # Act
    result = _get_ss_tolerance(setpoint_variation)

    # Assert
    assert result == 0.0005


def test_check_value_by_threshold():
    # Arrange
    mxre = 0.001
    threshold = 0.01

    # Act
    ok_result = _check_value_by_threshold(mxre, threshold)
    ko_result = _check_value_by_threshold(mxre * 100, threshold)

    # Assert
    assert ok_result is True
    assert ko_result is False


# Returns "P" when input is "ActivePowerSetpointPu"
def test_returns_p_column_name():
    # Arrange
    modified_setpoint = "ActivePowerSetpointPu"

    # Act
    result = _get_column_name(modified_setpoint)

    # Assert
    assert result == "P"


# Returns "Q" when input is "ReactivePowerSetpointPu"
def test_returns_q_column_name():
    # Arrange
    modified_setpoint = "ReactivePowerSetpointPu"

    # Act
    result = _get_column_name(modified_setpoint)

    # Assert
    assert result == "Q"


# Returns "V" when input is "AVRSetpointPu"
def test_returns_v_column_name():
    # Arrange
    modified_setpoint = "AVRSetpointPu"

    # Act
    result = _get_column_name(modified_setpoint)

    # Assert
    assert result == "V"


# Returns "$\\omega" when input is "NetworkFrequencyPu"
def test_returns_omega_column_name():
    # Arrange
    modified_setpoint = "NetworkFrequencyPu"

    # Act
    result = _get_column_name(modified_setpoint)

    # Assert
    assert result == "$\\omega"


# Handles empty string input by returning default "Q"
def test_returns_default_column_name():
    # Arrange
    modified_setpoint = ""

    # Act
    result = _get_column_name(modified_setpoint)

    # Assert
    assert result == "Q"


# Returns "BusPDR_BUS_ActivePower" when modified_setpoint is "ActivePowerSetpointPu"
def test_returns_active_power_measurement_name():
    # Arrange
    modified_setpoint = "ActivePowerSetpointPu"

    # Act
    result = _get_measurement_name(modified_setpoint)

    # Assert
    assert result == "BusPDR_BUS_ActivePower"


# Returns "BusPDR_BUS_ReactivePower" when modified_setpoint is "ReactivePowerSetpointPu"
def test_returns_reactive_power_measurement_name():
    # Arrange
    modified_setpoint = "ReactivePowerSetpointPu"

    # Act
    result = _get_measurement_name(modified_setpoint)

    # Assert
    assert result == "BusPDR_BUS_ReactivePower"


# Returns "BusPDR_BUS_Voltage" when modified_setpoint is "AVRSetpointPu"
def test_returns_voltage_power_measurement_name():
    # Arrange
    modified_setpoint = "AVRSetpointPu"

    # Act
    result = _get_measurement_name(modified_setpoint)

    # Assert
    assert result == "BusPDR_BUS_Voltage"


# Returns "NetworkFrequencyPu" when modified_setpoint is "NetworkFrequencyPu"
def test_returns_network_frequency_measurement_name():
    # Arrange
    modified_setpoint = "NetworkFrequencyPu"

    # Act
    result = _get_measurement_name(modified_setpoint)

    # Assert
    assert result == "NetworkFrequencyPu"


# Handles empty string input by returning default "BusPDR_BUS_ReactivePower"
def test_returns_default_measurement_name():
    # Arrange
    modified_setpoint = ""

    # Act
    result = _get_measurement_name(modified_setpoint)

    # Assert
    assert result == "BusPDR_BUS_ReactivePower"
