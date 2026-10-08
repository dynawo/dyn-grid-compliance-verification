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
# A response to an event also swings fast for a while, but it dies out: only an oscillation that
# lasts this long, with this many swings of at least this fraction of its largest one, is ripple.
RIPPLE_SUSTAIN = 0.2  # s
RIPPLE_COMPARABLE = 0.5
RIPPLE_COMPARABLE_SWINGS = 4


def _turns(time: np.ndarray, values: np.ndarray) -> List[tuple]:
    """Where the signal reverses by at least the gate, with the value of the extreme it leaves."""
    turns = []
    last_extreme = values[0]
    direction = 0
    for instant, value in zip(time, values):
        if abs(value - last_extreme) < RIPPLE_GATE:
            continue
        new_direction = 1 if value > last_extreme else -1
        if direction and new_direction != direction:
            turns.append((instant, last_extreme))
        direction = new_direction
        last_extreme = value
    return turns


def _is_sustained(run: List[tuple]) -> bool:
    if run[-1][0] - run[0][0] < RIPPLE_SUSTAIN:
        return False
    swings = np.abs(np.diff([extreme for _, extreme in run]))
    return np.count_nonzero(swings >= RIPPLE_COMPARABLE * swings.max()) >= RIPPLE_COMPARABLE_SWINGS


def _fast_runs(turns: List[tuple]) -> List[List[tuple]]:
    """The turns grouped in runs whose consecutive turns are at most a ripple period apart."""
    runs = []
    for turn in turns:
        if runs and turn[0] - runs[-1][-1][0] <= RIPPLE_PERIOD:
            runs[-1].append(turn)
        else:
            runs.append([turn])
    return runs


def _ripple_spans(time: np.ndarray, values: np.ndarray) -> List[tuple]:
    return [
        (run[0][0], run[-1][0])
        for run in _fast_runs(_turns(time, values))
        if len(run) > RIPPLE_SWINGS and _is_sustained(run)
    ]


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
