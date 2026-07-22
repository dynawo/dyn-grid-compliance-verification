#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import pandas as pd
import pytest

from dycov.curves.voltage_dip import (
    TrimmedCurves,
    VoltDipResult,
    _trim_curves,
    classify_residual_voltage,
    classify_voltage_dip,
)

# -------------------------------------------------------------------
# STABILITY TESTS
# -------------------------------------------------------------------


def test_is_stable_raises_on_length_mismatch():
    from dycov.validation.common import is_stable

    time = [0.0, 0.1, 0.2]
    curve = [1.0, 1.1]
    thr_ss_tol = 0.1

    with pytest.raises(ValueError) as excinfo:
        is_stable(time, curve, thr_ss_tol)

    assert "different length" in str(excinfo.value)


# -------------------------------------------------------------------
# VOLTAGE DIP TESTS
# -------------------------------------------------------------------


def test_voltage_dip_equals_expected_dip_within_tolerance(mocker):
    curves = pd.DataFrame(
        {
            "time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            "BusPDR_BUS_Voltage": [1.0, 1.0, 0.8, 0.8, 0.8, 0.8],
        }
    )

    fault_start = 0.15
    fault_duration = 0.3
    expected_dip = 0.2

    mocker.patch(
        "dycov.curves.voltage_dip._trim_curves",
        return_value=TrimmedCurves(
            pre_time=[0.0, 0.1],
            post_time=[0.2, 0.3, 0.4, 0.5],
            pre_voltage=[1.0, 1.0],
            post_voltage=[0.8, 0.8, 0.8, 0.8],
        ),
    )

    mock_is_stable = mocker.patch("dycov.curves.voltage_dip.is_stable")
    mock_is_stable.side_effect = [(True, 0), (True, 0)]

    mock_logger = mocker.MagicMock()
    mocker.patch("dycov.logging.dycov_logging.get_logger", return_value=mock_logger)

    result = classify_voltage_dip(
        "PCS", "BM", "OC", curves, fault_start, fault_duration, expected_dip
    )

    assert result == VoltDipResult.DIP_CORRECT


def test_fault_duration_exceeds_simulation_time(mocker):
    from pytest import approx

    curves = pd.DataFrame(
        {
            "time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            "BusPDR_BUS_Voltage": [1.0, 1.0, 0.8, 0.8, 0.8, 0.8],
        }
    )

    fault_start = 0.2
    fault_duration = 1.0
    expected_dip = 0.2

    mock_trim = mocker.patch(
        "dycov.curves.voltage_dip._trim_curves",
        return_value=TrimmedCurves(
            pre_time=[0.0, 0.1],
            post_time=[0.2, 0.3, 0.4, 0.5],
            pre_voltage=[1.0, 1.0],
            post_voltage=[0.8, 0.8, 0.8, 0.8],
        ),
    )

    mock_is_stable = mocker.patch("dycov.curves.voltage_dip.is_stable")
    mock_is_stable.side_effect = [(True, 0), (True, 0)]

    mock_logger = mocker.MagicMock()
    mocker.patch("dycov.logging.dycov_logging.get_logger", return_value=mock_logger)

    result = classify_voltage_dip(
        "PCS", "BM", "OC", curves, fault_start, fault_duration, expected_dip
    )

    mock_trim.assert_called_once()
    args, kwargs = mock_trim.call_args

    assert args[0] == curves["time"].tolist()
    assert args[1] == curves["BusPDR_BUS_Voltage"].tolist()
    assert args[2] == fault_start
    assert args[3] == approx(0.5 - fault_start)

    assert result == VoltDipResult.DIP_CORRECT


def test_correct_identification_of_pre_and_post_fault_values():
    time_values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    voltage_values = [1.0, 1.0, 1.0, 0.8, 0.6, 0.4, 0.6, 0.8, 0.9, 1.0, 1.0]

    fault_start = 0.4
    fault_duration = 0.4

    result = _trim_curves(time_values, voltage_values, fault_start, fault_duration)

    assert result.pre_time == [0.0, 0.1, 0.2, 0.3]
    assert result.pre_voltage == [1.0, 1.0, 1.0, 0.8]
    assert result.post_time == [0.4, 0.5, 0.6, 0.7]
    assert result.post_voltage == [0.6, 0.4, 0.6, 0.8]


def test_empty_input_lists():
    result = _trim_curves([], [], fault_start=0.3, fault_duration=0.4)

    assert result.pre_time == []
    assert result.post_time == []
    assert result.pre_voltage == []
    assert result.post_voltage == []


# -------------------------------------------------------------------
# RESIDUAL VOLTAGE TESTS
# -------------------------------------------------------------------


def _residual_curves(residual_voltage: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            "BusPDR_BUS_Voltage": [1.0, 1.0] + [residual_voltage] * 4,
        }
    )


def test_residual_voltage_below_threshold_is_correct():
    result = classify_residual_voltage(
        "PCS", "BM", "OC", _residual_curves(0.004), 0.15, 0.3, max_residual=0.005
    )

    assert result == VoltDipResult.DIP_CORRECT


def test_residual_voltage_above_threshold_is_too_small():
    result = classify_residual_voltage(
        "PCS", "BM", "OC", _residual_curves(0.02), 0.15, 0.3, max_residual=0.005
    )

    assert result == VoltDipResult.DIP_TOO_SMALL


def test_residual_voltage_column_missing():
    curves = pd.DataFrame({"time": [0.0, 0.1, 0.2]})

    result = classify_residual_voltage("PCS", "BM", "OC", curves, 0.15, 0.3, max_residual=0.005)

    assert result == VoltDipResult.COLUMN_MISSING
