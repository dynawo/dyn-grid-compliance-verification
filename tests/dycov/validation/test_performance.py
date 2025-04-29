#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
from pathlib import Path

from dycov.validation.performance import (
    GENERATOR_DISCONNECT_MSG,
    LOAD_DISCONNECT_MSG,
    _check_compliance,
    _check_timeline,
    _is_disconnection_event,
)


def _get_resources_path():
    return (Path(__file__).resolve().parent) / "resources"


# _check_compliance correctly updates results dictionary with scaled compliance value
def test_check_compliance_updates_results_with_scaled_value():
    # Arrange
    results = {"compliance": True}
    compliance_value = 0.75
    results_name = "test_metric"
    threshold = 0.8
    scale = 2.0

    # Act
    _check_compliance(results, compliance_value, results_name, threshold, scale)

    # Assert
    assert results["test_metric"] == 1.5  # 0.75 * 2.0
    assert results["test_metric_check"] is False  # 1.5 is not < 0.8
    assert results["compliance"] is False  # compliance is updated with AND operation


# _check_compliance handles None threshold by not performing compliance check
def test_check_compliance_with_none_threshold():
    # Arrange
    results = {"compliance": True}
    compliance_value = 0.75
    results_name = "test_metric"
    threshold = None
    scale = 1.0

    # Act
    _check_compliance(results, compliance_value, results_name, threshold, scale)

    # Assert
    assert results["test_metric"] == 0.75
    assert "test_metric_check" not in results
    assert results["compliance"] is True  # compliance remains unchanged


# Generator disconnection event with element_type "gen" returns True
def test_generator_disconnection_returns_true():
    # Arrange
    event = {"message": GENERATOR_DISCONNECT_MSG}
    element_type = "gen"

    # Act
    result = _is_disconnection_event(event, element_type)

    # Assert
    assert result is True


# Load disconnection event with element_type "load" returns True
def test_load_disconnection_returns_true():
    # Arrange
    event = {"message": LOAD_DISCONNECT_MSG}
    element_type = "load"

    # Act
    result = _is_disconnection_event(event, element_type)

    # Assert
    assert result is True


# Timeline file with no disconnection events returns true and empty list
def test_timeline_with_no_disconnection_events():
    # Arrange
    timeline_file = _get_resources_path() / "timeline_no_disconnections.xml"
    element_type = "gen"

    # Act
    result, disconnection_list = _check_timeline(timeline_file, element_type)

    # Assert
    assert result is True
    assert disconnection_list == []


# Timeline file with disconnection events returns false and 'Wind_Turbine'
def test_timeline_with_disconnection_events():
    # Arrange
    timeline_file = _get_resources_path() / "timeline_disconnection.xml"
    element_type = "gen"

    # Act
    result, disconnection_list = _check_timeline(timeline_file, element_type)

    # Assert
    assert result is False
    assert disconnection_list == ["Wind_Turbine"]
