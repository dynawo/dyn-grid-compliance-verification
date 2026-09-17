#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from typing import List

import numpy as np
import pandas as pd

from dycov.curves.anonymizer.window import blend_weights
from dycov.sigpro.sigpro import lowpass_filter

# What tells a numerical oscillation apart from a response: swings of at least this size,
# alternating faster than this period, repeated at least this many times in a row.
RIPPLE_GATE = 0.01  # pu
RIPPLE_PERIOD = 0.1  # s
RIPPLE_SWINGS = 6
RIPPLE_GRID = 1e-3  # s


def _ripple_spans(time: np.ndarray, values: np.ndarray) -> List[tuple]:
    turns = []
    last_extreme = values[0]
    direction = 0
    for instant, value in zip(time, values):
        if abs(value - last_extreme) < RIPPLE_GATE:
            continue
        new_direction = 1 if value > last_extreme else -1
        if direction and new_direction != direction:
            turns.append(instant)
        direction = new_direction
        last_extreme = value

    spans = []
    run_start = None
    run_length = 0
    for turn, next_turn in zip(turns, turns[1:]):
        if next_turn - turn <= RIPPLE_PERIOD:
            run_start = turn if run_start is None else run_start
            run_length += 1
            continue
        if run_length >= RIPPLE_SWINGS:
            spans.append((run_start, turn))
        run_start, run_length = None, 0
    if run_length >= RIPPLE_SWINGS:
        spans.append((run_start, turns[-1]))

    return spans


def _remove_spikes(values: np.ndarray) -> np.ndarray:
    if len(values) < 3:
        return values

    previous, current, following = values[:-2], values[1:-1], values[2:]
    spikes = (
        (np.abs(current - previous) > RIPPLE_GATE)
        & (np.abs(current - following) > RIPPLE_GATE)
        & (np.abs(following - previous) <= RIPPLE_GATE)
    )

    without_spikes = values.copy()
    without_spikes[1:-1][spikes] = 0.5 * (previous[spikes] + following[spikes])
    return without_spikes


def _filtered_weights(time: np.ndarray, spans: List[tuple], event_time: float) -> np.ndarray:
    """How much of the filtered signal replaces the original, at each instant.

    The filter has no phase, so it carries what happens in a span to both of its sides. A
    span that begins with the event must not be entered before it, or the reference answers
    a fault that has not happened yet.
    """
    reach = [
        (start - RIPPLE_PERIOD, end + RIPPLE_PERIOD) for start, end in spans if end < event_time
    ]
    weights = blend_weights(time, reach)

    caused_by_event = [
        (max(start - RIPPLE_PERIOD, event_time), end + RIPPLE_PERIOD)
        for start, end in spans
        if end >= event_time
    ]
    if caused_by_event:
        after_event = blend_weights(time, caused_by_event)
        after_event[time < event_time] = 0.0
        weights = np.maximum(weights, after_event)

    return weights


def _deripple_signal(
    time: np.ndarray, values: np.ndarray, cutoff: float, event_time: float
) -> np.ndarray:
    values = _remove_spikes(values)
    spans = _ripple_spans(time, values)
    if not spans:
        return values

    instants, first_of_instant = np.unique(time, return_index=True)
    grid = np.arange(instants[0], instants[-1], RIPPLE_GRID)
    smooth = lowpass_filter(
        np.interp(grid, instants, values[first_of_instant]), fc=cutoff, fs=1 / RIPPLE_GRID
    )

    weights = _filtered_weights(time, spans, event_time)
    return values * (1 - weights) + np.interp(time, grid, smooth) * weights


def deripple_curves(df: pd.DataFrame, cutoff: float, event_time: float) -> pd.DataFrame:
    time = df["time"].to_numpy(dtype=float)
    cleaned = {"time": time}
    for column in df.columns:
        if column == "time":
            continue
        cleaned[column] = _deripple_signal(
            time, df[column].to_numpy(dtype=float), cutoff, event_time
        )

    return pd.DataFrame(cleaned)[df.columns]
