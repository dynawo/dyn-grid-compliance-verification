#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum

import numpy as np
import pandas as pd

from dycov.configuration.cfg import config
from dycov.logging import dycov_logging
from dycov.validation.common import is_stable

VOLTAGE_DIP_THRESHOLD = 0.002
NO_FAULT_SENTINEL = 9999.0
ABS_TOLERANCE_FACTOR = 0.1
TIME_EPSILON = 1e-4


@dataclass(frozen=True)
class TrimmedCurves:
    pre_time: list[float]
    post_time: list[float]
    pre_voltage: list[float]
    post_voltage: list[float]


class VoltDipResult(IntEnum):
    """Result codes for voltage dip comparison."""

    COLUMN_MISSING = -2  # Error: BusPDR_BUS_Voltage column not found
    DIP_TOO_SMALL = -1  # Actual dip < expected (need more impedance)
    DIP_CORRECT = 0  # Actual dip ≈ expected (within tolerance)
    DIP_TOO_LARGE = 1  # Actual dip > expected (need less impedance)


def measure_voltage_dip(
    pcs_name: str,
    bm_name: str,
    oc_name: str,
    curves: pd.DataFrame,
    fault_start: float,
    fault_duration: float,
) -> float | None:
    """Measures the voltage dip magnitude from simulated or imported curves.

    Parameters
    ----------
    pcs_name : str
        Power System Case name for logging.
    bm_name : str
        Benchmark name for logging.
    oc_name : str
        Operating Condition name for logging.
    curves : pd.DataFrame
        DataFrame containing the curves, specifically "BusPDR_BUS_Voltage".
    fault_start : float
        The start time of the fault in seconds.
    fault_duration : float
        The duration of the fault in seconds.

    Returns
    -------
    float | None
        The measured voltage dip (pre_fault_voltage - post_fault_voltage), or None
        if fault_duration is zero or the required voltage column is missing.
    """
    if fault_duration == 0.0:
        return None
    return _compute_voltage_dip(pcs_name, bm_name, oc_name, curves, fault_start, fault_duration)


def classify_voltage_dip(
    pcs_name: str,
    bm_name: str,
    oc_name: str,
    curves: pd.DataFrame,
    fault_start: float,
    fault_duration: float,
    expected_dip: float,
) -> VoltDipResult:
    """Classifies the voltage dip magnitude relative to an expected value.

    Parameters
    ----------
    pcs_name : str
        Power System Case name for logging.
    bm_name : str
        Benchmark name for logging.
    oc_name : str
        Operating Condition name for logging.
    curves : pd.DataFrame
        DataFrame containing the curves, specifically "BusPDR_BUS_Voltage".
    fault_start : float
        The start time of the fault in seconds.
    fault_duration : float
        The duration of the fault in seconds.
    expected_dip : float
        The required voltage drop (positive value).

    Returns
    -------
    VoltDipResult
        Classification of the voltage dip:
        - COLUMN_MISSING: Required column not found in curves
        - DIP_TOO_SMALL: Increase fault impedance
        - DIP_CORRECT: Within tolerance
        - DIP_TOO_LARGE: Decrease fault impedance
    """
    if expected_dip == 0.0:
        return VoltDipResult.DIP_CORRECT

    voltage_dip = _compute_voltage_dip(
        pcs_name, bm_name, oc_name, curves, fault_start, fault_duration
    )
    if voltage_dip is None:
        return VoltDipResult.COLUMN_MISSING

    dycov_logging.get_logger("VoltageDip").debug(
        f"Calculated Voltage dip: {voltage_dip:.4f}, Expected dip: {expected_dip:.4f}"
    )

    rtol = VOLTAGE_DIP_THRESHOLD
    atol = ABS_TOLERANCE_FACTOR * rtol
    if math.isclose(voltage_dip, expected_dip, rel_tol=rtol, abs_tol=atol):
        return VoltDipResult.DIP_CORRECT
    if expected_dip < voltage_dip:
        return VoltDipResult.DIP_TOO_LARGE
    return VoltDipResult.DIP_TOO_SMALL


def classify_residual_voltage(
    pcs_name: str,
    bm_name: str,
    oc_name: str,
    curves: pd.DataFrame,
    fault_start: float,
    fault_duration: float,
    max_residual: float,
) -> VoltDipResult:
    """Classifies the during-fault residual voltage against a maximum threshold.

    Parameters
    ----------
    pcs_name : str
        Power System Case name for logging.
    bm_name : str
        Benchmark name for logging.
    oc_name : str
        Operating Condition name for logging.
    curves : pd.DataFrame
        DataFrame containing the curves, specifically "BusPDR_BUS_Voltage".
    fault_start : float
        The start time of the fault in seconds.
    fault_duration : float
        The duration of the fault in seconds.
    max_residual : float
        Maximum residual voltage (pu) allowed during the fault.

    Returns
    -------
    VoltDipResult
        Classification of the residual voltage:
        - COLUMN_MISSING: Required column not found in curves
        - DIP_TOO_SMALL: Residual voltage above the threshold (decrease fault impedance)
        - DIP_CORRECT: Residual voltage at or below the threshold
    """
    voltages = _compute_pre_post_voltages(
        pcs_name, bm_name, oc_name, curves, fault_start, fault_duration
    )
    if voltages is None:
        return VoltDipResult.COLUMN_MISSING

    _, residual_voltage = voltages
    dycov_logging.get_logger("VoltageDip").debug(
        f"Residual voltage during fault: {residual_voltage:.4f}, "
        f"maximum allowed: {max_residual:.4f}"
    )
    if residual_voltage > max_residual:
        return VoltDipResult.DIP_TOO_SMALL
    return VoltDipResult.DIP_CORRECT


def _is_flat_after_event(time, voltage, fault_start):
    thr_ss_tol = config.get_float("GridCode", "thr_ss_tol", 0.002)

    idx = np.argmin(abs(np.array(time) - fault_start)) - 1
    v_init = voltage[idx]

    v_max_diff = max(abs(np.array(voltage[idx:]) - v_init))

    rtol = thr_ss_tol
    atol = 0.1 * rtol

    return math.isclose(v_max_diff, 0.0, rel_tol=rtol, abs_tol=atol)


def _compute_voltage_dip(
    pcs_name: str,
    bm_name: str,
    oc_name: str,
    curves: pd.DataFrame,
    fault_start: float,
    fault_duration: float,
) -> float | None:
    bus_pdr_voltage_column = "BusPDR_BUS_Voltage"
    if bus_pdr_voltage_column not in curves.columns:
        return None

    time_values = curves["time"].tolist()
    voltage_values = curves[bus_pdr_voltage_column].tolist()
    if _is_flat_after_event(time_values, voltage_values, fault_start):
        return 0.0

    pre_fault_voltage, post_fault_voltage = _compute_pre_post_voltages(
        pcs_name, bm_name, oc_name, curves, fault_start, fault_duration
    )
    return pre_fault_voltage - post_fault_voltage


def _compute_pre_post_voltages(
    pcs_name: str,
    bm_name: str,
    oc_name: str,
    curves: pd.DataFrame,
    fault_start: float,
    fault_duration: float,
) -> tuple[float, float] | None:
    bus_pdr_voltage_column = "BusPDR_BUS_Voltage"
    if bus_pdr_voltage_column not in curves.columns:
        return None

    time_values = curves["time"].tolist()
    voltage_values = curves[bus_pdr_voltage_column].tolist()
    clamped_duration = _clamp_fault_duration(
        pcs_name, bm_name, oc_name, fault_start, fault_duration, time_values
    )
    trimmed = _trim_curves(time_values, voltage_values, fault_start, clamped_duration)

    try:
        _, pre_stable_idx = is_stable(trimmed.pre_time, trimmed.pre_voltage)
    except ValueError:
        pre_stable_idx = len(trimmed.pre_voltage) - 1 if trimmed.pre_voltage else 0

    _, post_stable_idx = is_stable(trimmed.post_time, trimmed.post_voltage)

    pre_fault_voltage = trimmed.pre_voltage[pre_stable_idx] if trimmed.pre_voltage else 0.0
    post_fault_voltage = trimmed.post_voltage[post_stable_idx] if trimmed.post_voltage else 0.0
    return pre_fault_voltage, post_fault_voltage


def _clamp_fault_duration(
    pcs_name: str,
    bm_name: str,
    oc_name: str,
    fault_start: float,
    fault_duration: float,
    time_values: list[float],
) -> float:
    simulation_end = time_values[-1]
    if fault_duration == NO_FAULT_SENTINEL:
        return simulation_end - fault_start
    if fault_start + fault_duration > simulation_end:
        clamped = simulation_end - fault_start
        dycov_logging.get_logger("VoltageDip").warning(
            f"{pcs_name}.{bm_name}.{oc_name}: "
            "Fault duration extends beyond simulation time. Adjusting fault_duration "
            f"from {fault_duration} to {clamped:.4f}."
        )
        return clamped
    return fault_duration


def _trim_curves(
    time_values: list[float],
    voltage_values: list[float],
    fault_start: float,
    fault_duration: float,
) -> TrimmedCurves:
    pre_idx = 0
    start_idx = 0
    end_idx = -1
    for i, t in enumerate(time_values):
        if t - fault_start < -TIME_EPSILON:
            pre_idx = i
        if fault_start - t > TIME_EPSILON:
            start_idx = i
        if t - (fault_start + fault_duration) < -TIME_EPSILON:
            end_idx = i

    return TrimmedCurves(
        pre_time=time_values[: pre_idx + 1],
        post_time=time_values[start_idx + 1 : end_idx + 1],
        pre_voltage=voltage_values[: pre_idx + 1],
        post_voltage=voltage_values[start_idx + 1 : end_idx + 1],
    )
