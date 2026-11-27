#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import numpy as np
import pandas as pd
import pytest

from dycov.configuration.cfg import config
from dycov.curves.voltage_dip import (
    NO_FAULT_SENTINEL,
    TrimmedCurves,
    VoltDipResult,
    _trim_curves,
    classify_residual_voltage,
    classify_voltage_dip,
    measure_voltage_dip,
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
# MEASURED DIP
# -------------------------------------------------------------------

_EVENT = 1.0


def _measured_dip(time: np.ndarray, voltage: np.ndarray, fault_duration: float) -> float:
    curves = pd.DataFrame({"time": time, "BusPDR_BUS_Voltage": voltage})
    return measure_voltage_dip("PCS", "BM", "OC", curves, _EVENT, fault_duration)


def test_a_permanent_bolted_fault_measures_the_whole_depth_of_its_dip():
    """#814: Dynawo records the fault a few microseconds before its instant, and the voltage then
    stays at zero to the end, which is no reason to read the dip as none."""
    time = np.concatenate(
        [
            np.arange(0.0, _EVENT - 1e-5, 0.001),
            [_EVENT - 5e-6],
            _EVENT + np.arange(0.0, 1.0, 0.001),
        ]
    )
    voltage = np.where(time < _EVENT - 5e-6, 1.0, 1e-6)

    assert _measured_dip(time, voltage, NO_FAULT_SENTINEL) == pytest.approx(1.0, abs=1e-5)


def test_a_dip_of_a_voltage_table_is_measured_from_the_voltage_before_its_smoothed_step():
    """#814: the step of a table of the grid is smoothed over a width centred on the event, so the
    voltage is already falling when the event starts; the dip is from where it fell."""
    assert config.get_boolean("Dynawo", "transition_enabled", False)
    half_width = config.get_float("Dynawo", "transition_half_width", 0.01)
    time = np.round(np.arange(0.0, 2.0, 0.001), 6)
    voltage = np.interp(
        time,
        [
            0.0,
            _EVENT - half_width,
            _EVENT + half_width,
            _EVENT + 0.15,
            _EVENT + 0.15 + half_width,
            2.0,
        ],
        [1.0, 1.0, 0.05, 0.05, 0.85, 0.85],
    )

    assert _measured_dip(time, voltage, 0.15) == pytest.approx(0.95, abs=1e-3)


def test_without_smoothed_steps_the_voltage_before_the_event_is_read_up_to_it(monkeypatch):
    """With the smoothing of the tables off, nothing moves the voltage before the event but the
    instant Dynawo records it, so the pre-event window reaches the event."""
    from dycov.configuration.cfg import Config

    monkeypatch.setattr(
        Config,
        "get_boolean",
        lambda self, section, key, default=False: (
            False if (section, key) == ("Dynawo", "transition_enabled") else default
        ),
    )
    time = [0.0, 0.5, _EVENT - 0.005, _EVENT, _EVENT + 0.1]

    trimmed = _trim_curves(time, [1.0, 1.0, 1.0, 0.0, 0.0], _EVENT, 0.2)

    assert trimmed.pre_time == [0.0, 0.5, _EVENT - 0.005]


def test_an_event_before_the_first_sample_leaves_it_as_the_voltage_before_the_event():
    trimmed = _trim_curves([0.0, 0.1, 0.2], [0.5, 0.5, 0.5], 0.0, 0.1)

    assert trimmed.pre_time == [0.0]


def test_a_voltage_the_event_does_not_move_has_no_dip():
    time = np.round(np.arange(0.0, 2.0, 0.001), 6)

    assert _measured_dip(time, np.ones_like(time), 0.15) == 0.0


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


def test_a_residual_voltage_that_is_not_a_number_is_no_bolted_fault():
    """#675: a comparison with NaN is false, so it used to pass as under the threshold."""
    result = classify_residual_voltage(
        "PCS", "BM", "OC", _residual_curves(float("nan")), 0.15, 0.3, max_residual=0.005
    )

    assert result == VoltDipResult.DIP_TOO_SMALL


def test_residual_voltage_column_missing():
    curves = pd.DataFrame({"time": [0.0, 0.1, 0.2]})

    result = classify_residual_voltage("PCS", "BM", "OC", curves, 0.15, 0.3, max_residual=0.005)

    assert result == VoltDipResult.COLUMN_MISSING
