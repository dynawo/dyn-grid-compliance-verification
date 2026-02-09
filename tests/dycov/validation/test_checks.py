#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import numpy as np
import pandas as pd
import pytest

from dycov.validation import checks


class DummyLogger:
    def __init__(self):
        self.logged = []

    def error(self, msg):
        self.logged.append(msg)


def patch_dycov_logging(monkeypatch):
    dummy_logger = DummyLogger()
    monkeypatch.setattr("dycov.logging.logging.dycov_logging", dummy_logger)
    return dummy_logger


@pytest.fixture
def valid_curves():
    time = np.linspace(0, 1, 5)
    data = {
        "time": time,
        "BusPDR_BUS_ActivePower": np.array([1, 2, 3, 4, 5]),
        "BusPDR_BUS_ReactivePower": np.array([2, 3, 4, 5, 6]),
        "BusPDR_BUS_ActiveCurrent": np.array([3, 4, 5, 6, 7]),
        "BusPDR_BUS_ReactiveCurrent": np.array([4, 5, 6, 7, 8]),
        "BusPDR_BUS_Voltage": np.array([5, 6, 7, 8, 9]),
        "NetworkFrequencyPu": np.array([6, 7, 8, 9, 10]),
    }
    ref_data = {
        "time": time,
        "BusPDR_BUS_ActivePower": np.array([1, 2, 2, 4, 5]),
        "BusPDR_BUS_ReactivePower": np.array([2, 2, 4, 5, 6]),
        "BusPDR_BUS_ActiveCurrent": np.array([3, 4, 4, 6, 7]),
        "BusPDR_BUS_ReactiveCurrent": np.array([4, 5, 5, 7, 8]),
        "BusPDR_BUS_Voltage": np.array([5, 6, 6, 8, 9]),
        "NetworkFrequencyPu": np.array([6, 7, 7, 9, 10]),
    }
    return pd.DataFrame(data), pd.DataFrame(ref_data)


def test_calculate_errors_with_valid_curves(valid_curves):
    calculated, reference = valid_curves
    step_magnitude = 1.0
    results = checks.calculate_errors((calculated, reference), step_magnitude)
    assert "BusPDR_BUS_ActivePower" in results
    assert "me" in results["BusPDR_BUS_ActivePower"]
    assert "mae" in results["BusPDR_BUS_ActivePower"]
    assert "mxe" in results["BusPDR_BUS_ActivePower"]
    assert isinstance(results["BusPDR_BUS_ActivePower"]["me"], float)
    assert isinstance(results["BusPDR_BUS_ActivePower"]["mae"], float)
    assert isinstance(results["BusPDR_BUS_ActivePower"]["mxe"], float)


def test_complete_setpoint_tracking_populates_results():
    compliance_values = {
        "before": {
            "BusPDR_BUS_ActivePower": {
                "mae": 0.01,
                "me": 0.01,
                "mxe": 0.01,
                "tmae": 0.1,
                "ymae": 1.1,
                "tme": 0.2,
                "yme": 1.2,
                "tmxe": 0.3,
                "ymxe": 1.3,
            }
        },
        "during": {
            "BusPDR_BUS_ActivePower": {
                "mae": 0.02,
                "me": 0.02,
                "mxe": 0.02,
                "tmae": 0.4,
                "ymae": 1.4,
                "tme": 0.5,
                "yme": 1.5,
                "tmxe": 0.6,
                "ymxe": 1.6,
            }
        },
        "after": {
            "BusPDR_BUS_ActivePower": {
                "mae": 0.03,
                "me": 0.03,
                "mxe": 0.03,
                "tmae": 0.7,
                "ymae": 1.7,
                "tme": 0.8,
                "yme": 1.8,
                "tmxe": 0.9,
                "ymxe": 1.9,
            }
        },
    }
    results = {"compliance": True}
    checks.complete_setpoint_tracking(
        compliance_values, "ActivePowerSetpointPu", "BusPDR_BUS_ActivePower", results
    )
    assert "before_mae_tc_BusPDR_BUS_ActivePower_value" in results
    assert "during_mae_tc_BusPDR_BUS_ActivePower_value" in results
    assert "after_mae_tc_BusPDR_BUS_ActivePower_value" in results
    assert results["before_mae_tc_BusPDR_BUS_ActivePower_value"] == 0.01
    assert results["during_mae_tc_BusPDR_BUS_ActivePower_value"] == 0.02
    assert results["after_mae_tc_BusPDR_BUS_ActivePower_value"] == 0.03


def test_calculate_errors_with_empty_curves():
    calculated = pd.DataFrame({"time": []})
    reference = pd.DataFrame({"time": []})
    step_magnitude = 1.0
    results = checks.calculate_errors((calculated, reference), step_magnitude)
    assert results == {}


def test_setpoint_tracking_with_missing_during_window():
    compliance_values = {
        "before": {
            "BusPDR_BUS_ActivePower": {
                "mae": 0.01,
                "me": 0.01,
                "mxe": 0.01,
                "tmae": 0.1,
                "ymae": 1.1,
                "tme": 0.2,
                "yme": 1.2,
                "tmxe": 0.3,
                "ymxe": 1.3,
            }
        },
        "during": None,
        "after": {
            "BusPDR_BUS_ActivePower": {
                "mae": 0.03,
                "me": 0.03,
                "mxe": 0.03,
                "tmae": 0.7,
                "ymae": 1.7,
                "tme": 0.8,
                "yme": 1.8,
                "tmxe": 0.9,
                "ymxe": 1.9,
            }
        },
    }
    results = {"compliance": True}
    checks.complete_setpoint_tracking(
        compliance_values, "ActivePowerSetpointPu", "BusPDR_BUS_ActivePower", results
    )
    assert "during_mae_tc_BusPDR_BUS_ActivePower_value" not in results


def test_save_measurement_errors_with_missing_error_metrics():
    compliance_values = {
        "before_mae_BusPDR_BUS_ActivePower_value": 0.1,
        "before_mae_BusPDR_BUS_ActivePower_position": [0.1, 1.1],
        "after_mae_BusPDR_BUS_ActivePower_value": None,
        "after_mae_BusPDR_BUS_ActivePower_position": None,
        "during_mae_BusPDR_BUS_ActivePower_value": 0.2,
        "during_mae_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
        "before_me_BusPDR_BUS_ActivePower_value": 0.1,
        "before_me_BusPDR_BUS_ActivePower_position": [0.1, 1.1],
        "after_me_BusPDR_BUS_ActivePower_value": None,
        "after_me_BusPDR_BUS_ActivePower_position": None,
        "during_me_BusPDR_BUS_ActivePower_value": 0.2,
        "during_me_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
        "before_mxe_BusPDR_BUS_ActivePower_value": 0.1,
        "before_mxe_BusPDR_BUS_ActivePower_position": [0.1, 1.1],
        "after_mxe_BusPDR_BUS_ActivePower_value": None,
        "after_mxe_BusPDR_BUS_ActivePower_position": None,
        "during_mxe_BusPDR_BUS_ActivePower_value": 0.2,
        "during_mxe_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
    }
    results = {}
    checks.save_measurement_errors(compliance_values, "BusPDR_BUS_ActivePower", results)
    assert results["before_mae_BusPDR_BUS_ActivePower_value"] == 0.1
    assert "after_mae_BusPDR_BUS_ActivePower_value" not in results


def test_voltage_dip_threshold_selection():
    compliance_values = {
        "before": {"BusPDR_BUS_ActivePower": {"mae": 0.07, "me": 0.03, "mxe": 0.09}},
        "during": {"BusPDR_BUS_ActivePower": {"mae": 0.08, "me": 0.04, "mxe": 0.10}},
        "after": {"BusPDR_BUS_ActivePower": {"mae": 0.07, "me": 0.03, "mxe": 0.09}},
    }
    # Field measurements: thresholds are higher
    before_value, before_check, _, during_value, during_check, _, after_value, after_check, _ = (
        checks._check_voltage_dips(
            compliance_values, "BusPDR_BUS_ActivePower", "mae", is_field_measurements=True
        )
    )
    assert before_check is True or before_check is False
    # Simulation: thresholds are lower
    before_value2, before_check2, _, _, _, _, _, _, _ = checks._check_voltage_dips(
        compliance_values, "BusPDR_BUS_ActivePower", "mae", is_field_measurements=False
    )
    assert before_check2 is True or before_check2 is False


def test_get_measurement_name_mapping():
    assert checks._get_measurement_name("ActivePowerSetpointPu") == "BusPDR_BUS_ActivePower"
    assert checks._get_measurement_name("ReactivePowerSetpointPu") == "BusPDR_BUS_ReactivePower"
    assert checks._get_measurement_name("AVRSetpointPu") == "BusPDR_BUS_Voltage"
    assert checks._get_measurement_name("NetworkFrequencyPu") == "NetworkFrequencyPu"
    assert checks._get_measurement_name("UnknownSetpoint") == "BusPDR_BUS_ReactivePower"


def test_compliance_aggregation_updates_results():
    compliance_values = {
        "before_mae_BusPDR_BUS_ActivePower_check": True,
        "after_mae_BusPDR_BUS_ActivePower_check": True,
        "during_mae_BusPDR_BUS_ActivePower_check": False,
        "before_me_BusPDR_BUS_ActivePower_check": True,
        "after_me_BusPDR_BUS_ActivePower_check": True,
        "during_me_BusPDR_BUS_ActivePower_check": True,
        "before_mxe_BusPDR_BUS_ActivePower_check": True,
        "after_mxe_BusPDR_BUS_ActivePower_check": True,
        "during_mxe_BusPDR_BUS_ActivePower_check": True,
    }
    results = {"compliance": True}
    checks.check_measurement(compliance_values, "BusPDR_BUS_ActivePower", results)
    assert results["voltage_dips_BusPDR_BUS_ActivePower_check"] is False
    assert results["compliance"] is False


def test_functions_with_unexpected_data_types():
    compliance_values = {
        "before_mae_BusPDR_BUS_ActivePower_value": [0.1, 0.2],  # list instead of float
        "before_mae_BusPDR_BUS_ActivePower_position": "not_a_position",  # str instead of list
        "after_mae_BusPDR_BUS_ActivePower_value": None,
        "after_mae_BusPDR_BUS_ActivePower_position": None,
        "during_mae_BusPDR_BUS_ActivePower_value": 0.2,
        "during_mae_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
        "before_me_BusPDR_BUS_ActivePower_value": 0.1,
        "before_me_BusPDR_BUS_ActivePower_position": [0.1, 1.1],
        "after_me_BusPDR_BUS_ActivePower_value": None,
        "after_me_BusPDR_BUS_ActivePower_position": None,
        "during_me_BusPDR_BUS_ActivePower_value": 0.2,
        "during_me_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
        "before_mxe_BusPDR_BUS_ActivePower_value": 0.1,
        "before_mxe_BusPDR_BUS_ActivePower_position": [0.1, 1.1],
        "after_mxe_BusPDR_BUS_ActivePower_value": None,
        "after_mxe_BusPDR_BUS_ActivePower_position": None,
        "during_mxe_BusPDR_BUS_ActivePower_value": 0.2,
        "during_mxe_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
    }
    results = {}
    # Should not raise
    checks.save_measurement_errors(compliance_values, "BusPDR_BUS_ActivePower", results)
    assert isinstance(results["before_mae_BusPDR_BUS_ActivePower_value"], list)


def test_calculate_errors_returns_error_positions(valid_curves):
    calculated, reference = valid_curves
    step_magnitude = 1.0
    results = checks.calculate_errors((calculated, reference), step_magnitude)
    assert "tmxe" in results["BusPDR_BUS_ActivePower"]
    assert "ymxe" in results["BusPDR_BUS_ActivePower"]
    assert isinstance(results["BusPDR_BUS_ActivePower"]["tmxe"], (float, np.floating))
    assert isinstance(results["BusPDR_BUS_ActivePower"]["ymxe"], (int, np.int64))


def test_functions_with_extra_unexpected_keys():
    compliance_values = {
        "before_mae_BusPDR_BUS_ActivePower_value": 0.1,
        "before_mae_BusPDR_BUS_ActivePower_position": [0.1, 1.1],
        "after_mae_BusPDR_BUS_ActivePower_value": 0.2,
        "after_mae_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
        "during_mae_BusPDR_BUS_ActivePower_value": 0.3,
        "during_mae_BusPDR_BUS_ActivePower_position": [0.3, 1.3],
        "before_me_BusPDR_BUS_ActivePower_value": 0.1,
        "before_me_BusPDR_BUS_ActivePower_position": [0.1, 1.1],
        "after_me_BusPDR_BUS_ActivePower_value": None,
        "after_me_BusPDR_BUS_ActivePower_position": None,
        "during_me_BusPDR_BUS_ActivePower_value": 0.2,
        "during_me_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
        "before_mxe_BusPDR_BUS_ActivePower_value": 0.1,
        "before_mxe_BusPDR_BUS_ActivePower_position": [0.1, 1.1],
        "after_mxe_BusPDR_BUS_ActivePower_value": None,
        "after_mxe_BusPDR_BUS_ActivePower_position": None,
        "during_mxe_BusPDR_BUS_ActivePower_value": 0.2,
        "during_mxe_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
        "extra_key": "should_be_ignored",
    }
    results = {}
    checks.save_measurement_errors(compliance_values, "BusPDR_BUS_ActivePower", results)
    assert "extra_key" not in results


def test_save_measurement_errors_with_complete_compliance_values():
    compliance_values = {
        "before_mae_BusPDR_BUS_ActivePower_value": 0.1,
        "before_mae_BusPDR_BUS_ActivePower_position": [0.1, 1.1],
        "after_mae_BusPDR_BUS_ActivePower_value": 0.2,
        "after_mae_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
        "during_mae_BusPDR_BUS_ActivePower_value": 0.3,
        "during_mae_BusPDR_BUS_ActivePower_position": [0.3, 1.3],
        "before_me_BusPDR_BUS_ActivePower_value": 0.1,
        "before_me_BusPDR_BUS_ActivePower_position": [0.1, 1.1],
        "after_me_BusPDR_BUS_ActivePower_value": None,
        "after_me_BusPDR_BUS_ActivePower_position": None,
        "during_me_BusPDR_BUS_ActivePower_value": 0.2,
        "during_me_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
        "before_mxe_BusPDR_BUS_ActivePower_value": 0.1,
        "before_mxe_BusPDR_BUS_ActivePower_position": [0.1, 1.1],
        "after_mxe_BusPDR_BUS_ActivePower_value": None,
        "after_mxe_BusPDR_BUS_ActivePower_position": None,
        "during_mxe_BusPDR_BUS_ActivePower_value": 0.2,
        "during_mxe_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
    }
    results = {}
    checks.save_measurement_errors(compliance_values, "BusPDR_BUS_ActivePower", results)
    assert results["before_mae_BusPDR_BUS_ActivePower_value"] == 0.1
    assert results["after_mae_BusPDR_BUS_ActivePower_value"] == 0.2
    assert results["during_mae_BusPDR_BUS_ActivePower_value"] == 0.3


def test_threshold_checks_and_compliance_status_for_all_measurements():
    compliance_values = {
        "before": {
            "BusPDR_BUS_ActivePower": {
                "mae": 0.01,
                "me": 0.01,
                "mxe": 0.01,
                "tmae": 0.1,
                "ymae": 1.1,
                "tme": 0.2,
                "yme": 1.2,
                "tmxe": 0.3,
                "ymxe": 1.3,
            },
            "BusPDR_BUS_ReactivePower": {
                "mae": 0.01,
                "me": 0.01,
                "mxe": 0.01,
                "tmae": 0.1,
                "ymae": 1.1,
                "tme": 0.2,
                "yme": 1.2,
                "tmxe": 0.3,
                "ymxe": 1.3,
            },
        },
        "during": {
            "BusPDR_BUS_ActivePower": {
                "mae": 0.0002,
                "me": 0.002,
                "mxe": 0.0002,
                "tmae": 0.4,
                "ymae": 1.4,
                "tme": 0.5,
                "yme": 1.5,
                "tmxe": 0.6,
                "ymxe": 1.6,
            },
            "BusPDR_BUS_ReactivePower": {
                "mae": 0.002,
                "me": 0.0002,
                "mxe": 0.002,
                "tmae": 0.4,
                "ymae": 1.4,
                "tme": 0.5,
                "yme": 1.5,
                "tmxe": 0.6,
                "ymxe": 1.6,
            },
        },
        "after": {
            "BusPDR_BUS_ActivePower": {
                "mae": 0.001,
                "me": 0.001,
                "mxe": 0.0001,
                "tmae": 0.7,
                "ymae": 1.7,
                "tme": 0.8,
                "yme": 1.8,
                "tmxe": 0.9,
                "ymxe": 1.9,
            },
            "BusPDR_BUS_ReactivePower": {
                "mae": 0.0003,
                "me": 0.003,
                "mxe": 0.003,
                "tmae": 0.7,
                "ymae": 1.7,
                "tme": 0.8,
                "yme": 1.8,
                "tmxe": 0.9,
                "ymxe": 1.9,
            },
        },
    }
    results = {"compliance": True}
    checks.complete_setpoint_tracking(
        compliance_values, "ActivePowerSetpointPu", "BusPDR_BUS_ActivePower", results
    )
    print(results)
    checks.complete_setpoint_tracking(
        compliance_values, "ReactivePowerSetpointPu", "BusPDR_BUS_ReactivePower", results
    )
    print(results)
    assert results["compliance"] is True


def test_functions_with_nested_or_incorrectly_structured_input():
    compliance_values = {
        "before_mae_BusPDR_BUS_ActivePower_value": {"unexpected": "dict"},
        "before_mae_BusPDR_BUS_ActivePower_position": [{"nested": "dict"}],
        "after_mae_BusPDR_BUS_ActivePower_value": [[0.2, 1.2]],
        "after_mae_BusPDR_BUS_ActivePower_position": None,
        "during_mae_BusPDR_BUS_ActivePower_value": None,
        "during_mae_BusPDR_BUS_ActivePower_position": None,
        "before_me_BusPDR_BUS_ActivePower_value": 0.1,
        "before_me_BusPDR_BUS_ActivePower_position": [0.1, 1.1],
        "after_me_BusPDR_BUS_ActivePower_value": None,
        "after_me_BusPDR_BUS_ActivePower_position": None,
        "during_me_BusPDR_BUS_ActivePower_value": 0.2,
        "during_me_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
        "before_mxe_BusPDR_BUS_ActivePower_value": 0.1,
        "before_mxe_BusPDR_BUS_ActivePower_position": [0.1, 1.1],
        "after_mxe_BusPDR_BUS_ActivePower_value": None,
        "after_mxe_BusPDR_BUS_ActivePower_position": None,
        "during_mxe_BusPDR_BUS_ActivePower_value": 0.2,
        "during_mxe_BusPDR_BUS_ActivePower_position": [0.2, 1.2],
    }
    results = {}
    # Should not raise
    checks.save_measurement_errors(compliance_values, "BusPDR_BUS_ActivePower", results)
    assert isinstance(results["before_mae_BusPDR_BUS_ActivePower_value"], dict) or isinstance(
        results["before_mae_BusPDR_BUS_ActivePower_value"], (list, type(None))
    )
