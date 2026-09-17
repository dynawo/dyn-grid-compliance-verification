#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import numpy as np
import pandas as pd

from dycov.curves.anonymizer.window import event_window
from dycov.logging import dycov_logging

# A reference is a record of measurements, and no instrument samples faster than its own rate.
# Without a rate of its own a curve is stored as densely as the solver happened to step, which
# is what a numerical residue too small to matter costs: it is kept sample by sample.
MAX_RATE = 200.0  # Hz, away from the event
MAX_RATE_EVENT = 1000.0  # Hz, where the test looks
# A rate says how often a signal is read, and a step is not read: both of its ends are kept
# whatever the rate, or the instant a fault appears is stored as a ramp of one interval.
EDGE_FRACTION = 0.01  # of the range of a signal


def _interior_times(t_grid: np.ndarray, min_points: int) -> np.ndarray:
    lengths = np.diff(t_grid)
    splits = {index: 0 for index, length in enumerate(lengths) if length > 0.0}
    if not splits:
        return np.array([])

    for _ in range(min_points - len(t_grid)):
        widest = max(splits, key=lambda index: lengths[index] / (splits[index] + 1))
        splits[widest] += 1

    return np.array(
        [
            time
            for index, count in sorted(splits.items())
            if count
            for time in np.linspace(t_grid[index], t_grid[index + 1], count + 2)[1:-1]
        ]
    )


def ensure_min_points(df: pd.DataFrame, min_points: int = 10) -> pd.DataFrame:
    if len(df) >= min_points or df.empty:
        return df

    t_grid = df["time"].to_numpy(dtype=float)
    if len(df) == 1:
        t_new = np.linspace(t_grid[0], t_grid[0] + 1e-6, min_points)
        constants = {col: df[col].iloc[0] * np.ones(min_points) for col in df.columns}
        return pd.DataFrame({**constants, "time": t_new})[df.columns]

    t_interior = _interior_times(t_grid, min_points)
    if t_interior.size == 0:
        dycov_logging.get_logger("Anonymizer").warning(
            f"Cannot densify a curve whose {len(df)} samples share the same timestamp; "
            f"leaving it below the {min_points}-sample minimum."
        )
        return df

    order = np.argsort(np.concatenate((t_grid, t_interior)), kind="stable")
    densified = {"time": np.concatenate((t_grid, t_interior))[order]}
    for col in df.columns:
        if col == "time":
            continue
        values = df[col].to_numpy(dtype=float)
        densified[col] = np.concatenate((values, np.interp(t_interior, t_grid, values)))[order]

    return pd.DataFrame(densified)[df.columns]


def _rdp_mask_numpy(points: np.ndarray, epsilon: float) -> np.ndarray:
    mask = np.zeros(len(points), dtype=bool)
    mask[0] = True
    mask[-1] = True

    # Stack-based iterative approach to avoid recursion limit
    stack = [(0, len(points) - 1)]

    while stack:
        start, end = stack.pop()
        if end - start < 2:
            continue

        # Vectorized perpendicular distance from all points to the line start→end
        segment = points[end] - points[start]
        segment_len = np.hypot(segment[0], segment[1])

        if segment_len == 0.0:
            dists = np.hypot(
                points[start + 1 : end, 0] - points[start, 0],
                points[start + 1 : end, 1] - points[start, 1],
            )
        else:
            # Cross product magnitude / segment length = perpendicular distance
            d = points[start + 1 : end] - points[start]
            dists = np.abs(d[:, 0] * segment[1] - d[:, 1] * segment[0]) / segment_len

        idx = np.argmax(dists)
        max_dist = dists[idx]

        if max_dist > epsilon:
            pivot = start + 1 + idx
            mask[pivot] = True
            stack.append((start, pivot))
            stack.append((pivot, end))

    return mask


def _simplify_segment(segment: pd.DataFrame, compression: float) -> pd.DataFrame:
    if len(segment) <= 2:
        return segment

    time_values = segment["time"].to_numpy()
    keep = {0, len(segment) - 1}
    for column in segment.columns:
        if column == "time":
            continue
        values = segment[column].to_numpy()
        signal_range = float(np.ptp(values))
        if signal_range < 1e-12:
            continue
        mask = _rdp_mask_numpy(np.column_stack([time_values, values]), compression * signal_range)
        keep.update(np.where(mask)[0].tolist())

    return segment.iloc[sorted(keep)].reset_index(drop=True)


def _restore_event_points(
    segment: pd.DataFrame, simplified: pd.DataFrame, min_points: int
) -> pd.DataFrame:
    """The epsilon knows the shape of a signal but not where the test looks: the event is held
    to a floor of samples, and refilled with samples of the original, never interpolated ones.
    """
    if len(segment) <= min_points:
        return segment
    if len(simplified) >= min_points:
        return simplified

    refill = np.linspace(0, len(segment) - 1, min_points).astype(int)
    kept = np.where(segment["time"].isin(simplified["time"]).to_numpy())[0]
    return segment.iloc[sorted(set(kept.tolist()) | set(refill.tolist()))].reset_index(drop=True)


def simplify_curves(
    df: pd.DataFrame,
    event_time: float,
    event_duration: float,
    compression: float = 0.005,
    min_event_points: int = 20,
) -> pd.DataFrame:
    time_values = df["time"].to_numpy()
    before = df[time_values <= event_time].reset_index(drop=True)
    during = df[
        (time_values > event_time) & (time_values <= event_time + event_duration)
    ].reset_index(drop=True)
    after = df[time_values > event_time + event_duration].reset_index(drop=True)

    return pd.concat(
        [
            _simplify_segment(before, compression),
            _restore_event_points(
                during, _simplify_segment(during, compression), min_event_points
            ),
            _simplify_segment(after, compression),
        ],
        ignore_index=True,
    )


def _edge_samples(df: pd.DataFrame) -> np.ndarray:
    edges = np.zeros(len(df), dtype=bool)
    for column in df.columns:
        if column == "time":
            continue
        values = df[column].to_numpy()
        signal_range = float(np.ptp(values))
        if signal_range < 1e-12:
            continue
        steps = np.abs(np.diff(values)) > EDGE_FRACTION * signal_range
        edges[:-1] |= steps
        edges[1:] |= steps
    return edges


def cap_rate(df: pd.DataFrame, event_time: float, event_duration: float) -> pd.DataFrame:
    if len(df) <= 2:
        return df

    time_values = df["time"].to_numpy()
    low, high = event_window(event_time, event_duration)
    window = (time_values >= low) & (time_values <= high)
    rates = np.where(window, MAX_RATE_EVENT, MAX_RATE)

    interval = np.floor(time_values * rates).astype(np.int64)
    keep = np.empty(len(df), dtype=bool)
    keep[0] = True
    keep[1:] = (interval[1:] != interval[:-1]) | (rates[1:] != rates[:-1])
    keep |= _edge_samples(df)
    keep[-1] = True

    return df[keep].reset_index(drop=True)
