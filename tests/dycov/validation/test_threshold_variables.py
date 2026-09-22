#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Unit tests for the compliance thresholds (DTR tables) served to the validators."""

import pytest

from dycov.validation.threshold_variables import (
    get_setpoint_tracking_threshold_values,
    get_voltage_dip_threshold_values,
)

THRESHOLD_MODULE = "dycov.validation.threshold_variables"

# Maximum permissible errors of the DTR tables, in pu.
SIMULATION_THRESHOLDS = {
    "before": {"mxe": 0.05, "me": 0.02, "mae": 0.03},
    "during": {"mxe": 0.08, "me": 0.05, "mae": 0.07},
    "after": {"mxe": 0.05, "me": 0.02, "mae": 0.03},
}
FIELD_MEASUREMENT_THRESHOLDS = {
    "before": {"mxe": 0.08, "me": 0.04, "mae": 0.07},
    "during": {"mxe": 0.10, "me": 0.05, "mae": 0.08},
    "after": {"mxe": 0.08, "me": 0.04, "mae": 0.07},
}
UNDEFINED_THRESHOLDS = {
    "before": {"mxe": None, "me": None, "mae": None},
    "during": {"mxe": None, "me": None, "mae": None},
    "after": {"mxe": None, "me": None, "mae": None},
}

MEASUREMENT_NAMES = [
    "BusPDR_BUS_ActivePower",
    "BusPDR_BUS_ReactivePower",
    "BusPDR_BUS_ActiveCurrent",
    "BusPDR_BUS_ReactiveCurrent",
]


class DummyConfig:
    """Configuration stand-in returning the requested default, or a declared override."""

    def __init__(self, **overrides):
        self._overrides = overrides

    def get_float(self, section: str, key: str, default: float) -> float:
        return self._overrides.get(key, default)


@pytest.fixture(autouse=True)
def default_config(monkeypatch):
    """Serve the documented defaults regardless of the user configuration."""
    monkeypatch.setattr(f"{THRESHOLD_MODULE}.config", DummyConfig())


# ---------------------------------------------------------------------------
# Voltage dip thresholds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("measurement_name", MEASUREMENT_NAMES)
def test_get_voltage_dip_threshold_values_for_simulation_references(measurement_name):
    result = get_voltage_dip_threshold_values(measurement_name, is_field_measurements=False)

    assert result == SIMULATION_THRESHOLDS


@pytest.mark.parametrize("measurement_name", MEASUREMENT_NAMES)
def test_get_voltage_dip_threshold_values_for_field_measurement_references(measurement_name):
    result = get_voltage_dip_threshold_values(measurement_name, is_field_measurements=True)

    assert result == FIELD_MEASUREMENT_THRESHOLDS


@pytest.mark.parametrize("is_field_measurements", [False, True])
def test_get_voltage_dip_threshold_values_of_an_unmapped_measurement_is_undefined(
    is_field_measurements,
):
    result = get_voltage_dip_threshold_values("BusPDR_BUS_Voltage", is_field_measurements)

    # Voltage dips are not checked on magnitudes without a configured prefix.
    assert result == UNDEFINED_THRESHOLDS


@pytest.mark.parametrize(
    "is_field_measurements, key",
    [(False, "thr_P_mxe_during"), (True, "thr_FT_P_mxe_during")],
)
def test_get_voltage_dip_threshold_values_honours_the_configuration(
    monkeypatch, is_field_measurements, key
):
    monkeypatch.setattr(f"{THRESHOLD_MODULE}.config", DummyConfig(**{key: 0.42}))

    result = get_voltage_dip_threshold_values("BusPDR_BUS_ActivePower", is_field_measurements)

    assert result["during"]["mxe"] == pytest.approx(0.42)


# ---------------------------------------------------------------------------
# Setpoint tracking thresholds
# ---------------------------------------------------------------------------


def test_get_setpoint_tracking_threshold_values_returns_the_dtr_defaults():
    result = get_setpoint_tracking_threshold_values()

    assert result == SIMULATION_THRESHOLDS


def test_get_setpoint_tracking_threshold_values_honours_the_configuration(monkeypatch):
    monkeypatch.setattr(f"{THRESHOLD_MODULE}.config", DummyConfig(thr_reftrack_mae_after=0.42))

    result = get_setpoint_tracking_threshold_values()

    assert result["after"]["mae"] == pytest.approx(0.42)
