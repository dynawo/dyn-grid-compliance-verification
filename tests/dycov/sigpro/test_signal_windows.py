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

from dycov.sigpro import signal_windows


class DummyConfig:
    def __init__(self, values):
        self.values = values

    def get_float(self, section, key, default):
        return self.values.get((section, key), default)


@pytest.fixture(autouse=True)
def patch_config(monkeypatch):
    # Default config values for all tests unless overridden
    values = {
        ("GridCode", "t_windowLPF_excl_start"): 0.02,
        ("GridCode", "t_windowLPF_excl_end"): 0.02,
        ("GridCode", "t_integrator_tol"): 1e-6,
        ("GridCode", "t_faultLPF_excl"): 0.05,
        ("GridCode", "t_faultQS_excl"): 0.02,
        ("GridCode", "t_clearQS_excl"): 0.06,
    }
    dummy = DummyConfig(values)
    monkeypatch.setattr(signal_windows, "config", dummy)
    yield


def test_calculate_returns_expected_windows():
    time_values = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
    t_fault = 1.5
    fault_duration = 2.0
    setpoint_tracking_controlled_magnitude = False

    result = signal_windows.calculate(
        time_values, t_fault, fault_duration, setpoint_tracking_controlled_magnitude
    )

    # Validate window boundaries
    validate = result["validate"]
    assert "before" in validate and "during" in validate and "after" in validate
    during = validate["during"]
    after = validate["after"]

    # after window should end at time_values[-1] minus t_windowLPF_excl_end
    assert after[1] == pytest.approx(time_values[-1] - 0.02, abs=1e-8)
    # during window should be between
    # t_fault + tol + t_faultQS_excl and t_clear - tol - t_windowLPF_excl_end
    tol = 1e-6
    t_clear = t_fault + fault_duration
    t_faultQS_excl = max(0.02, 0.02)
    t_windowLPF_excl_end = 0.02
    assert during[0] == pytest.approx(t_fault + tol + t_faultQS_excl, abs=1e-8)
    assert during[1] == pytest.approx(t_clear - tol - t_windowLPF_excl_end, abs=1e-8)


def test_get_returns_dataframe_slice():
    df = pd.DataFrame({"time": np.arange(0, 10, 1), "value": np.arange(10, 20, 1)})
    t_from = 3
    t_to = 7
    result = signal_windows.get(df, t_from, t_to)
    expected = df[(df["time"] >= t_from) & (df["time"] < t_to)].reset_index(drop=True)
    pd.testing.assert_frame_equal(result.reset_index(drop=True), expected)


def test_get_exclusion_zones_flag_behavior(monkeypatch):
    # Patch config with distinct values to check flag effect
    values = {
        ("GridCode", "t_windowLPF_excl_start"): 0.03,
        ("GridCode", "t_windowLPF_excl_end"): 0.04,
        ("GridCode", "t_integrator_tol"): 1e-5,
        ("GridCode", "t_faultLPF_excl"): 0.07,
        ("GridCode", "t_faultQS_excl"): 0.05,
        ("GridCode", "t_clearQS_excl"): 0.09,
    }
    dummy = DummyConfig(values)
    monkeypatch.setattr(signal_windows, "config", dummy)

    # setpoint_tracking_controlled_magnitude = True
    ez_true = signal_windows._get_exclusion_zones(True)
    assert ez_true.t_faultQS_excl == 0.03
    assert ez_true.t_clearQS_excl == 0.03

    # setpoint_tracking_controlled_magnitude = False
    ez_false = signal_windows._get_exclusion_zones(False)
    assert ez_false.t_faultQS_excl == max(0.05, 0.03)
    assert ez_false.t_clearQS_excl == max(0.09, 0.03)


def test_calculate_empty_time_values():
    with pytest.raises(IndexError):
        signal_windows.calculate([], 1.0, 1.0, False)


def test_get_out_of_bounds_time_range():
    df = pd.DataFrame({"time": np.arange(0, 5, 1), "value": np.arange(10, 15, 1)})
    t_from = 10
    t_to = 12
    result = signal_windows.get(df, t_from, t_to)
    assert result.empty
    assert list(result.columns) == ["time", "value"]


def test_calculate_fault_duration_exceeds_time_range():
    time_values = [0.0, 1.0, 2.0, 3.0]
    t_fault = 1.0
    fault_duration = 10.0  # Exceeds last time value
    setpoint_tracking_controlled_magnitude = False

    result = signal_windows.calculate(
        time_values, t_fault, fault_duration, setpoint_tracking_controlled_magnitude
    )
    # The 'during' window should be calculated as if fault_duration is reset to 0
    tol = 1e-6
    t_clear = t_fault  # since fault_duration is reset to 0
    t_faultQS_excl = max(0.02, 0.02)
    t_windowLPF_excl_end = 0.02
    during = result["validate"]["during"]
    assert during[0] == pytest.approx(t_fault + tol + t_faultQS_excl, abs=1e-8)
    assert during[1] == pytest.approx(t_clear - tol - t_windowLPF_excl_end, abs=1e-8)


def test_get_preserves_dataframe_structure():
    df = pd.DataFrame(
        {
            "time": np.arange(0, 10, 1),
            "float_col": np.linspace(0, 1, 10),
            "int_col": np.arange(10, 20, 1),
            "str_col": [str(i) for i in range(10)],
            "bool_col": [i % 2 == 0 for i in range(10)],
        }
    )
    t_from = 2
    t_to = 5
    result = signal_windows.get(df, t_from, t_to)
    expected = df[(df["time"] >= t_from) & (df["time"] < t_to)].reset_index(drop=True)
    pd.testing.assert_frame_equal(result.reset_index(drop=True), expected)
    # Check dtypes
    for col in df.columns:
        assert result[col].dtype == df[col].dtype


def test_calculate_missing_exclusion_zone_keys(monkeypatch):
    # Remove a required key from config
    values = {
        ("GridCode", "t_windowLPF_excl_start"): 0.02,
        # ("GridCode", "t_windowLPF_excl_end") is missing
        ("GridCode", "t_integrator_tol"): 1e-6,
        ("GridCode", "t_faultLPF_excl"): 0.05,
        ("GridCode", "t_faultQS_excl"): 0.02,
        ("GridCode", "t_clearQS_excl"): 0.06,
    }
    dummy = DummyConfig(values)
    monkeypatch.setattr(signal_windows, "config", dummy)
    time_values = [0.0, 1.0, 2.0]
    t_fault = 1.0
    fault_duration = 1.0
    setpoint_tracking_controlled_magnitude = False

    # Since get_float returns default if missing, we simulate a missing key by raising an exception
    def raise_key_error(section, key, default):
        if key == "t_windowLPF_excl_end":
            raise KeyError("Missing key: t_windowLPF_excl_end")
        return values.get((section, key), default)

    dummy.get_float = raise_key_error
    monkeypatch.setattr(signal_windows, "config", dummy)

    with pytest.raises(KeyError, match="t_windowLPF_excl_end"):
        signal_windows.calculate(
            time_values, t_fault, fault_duration, setpoint_tracking_controlled_magnitude
        )
