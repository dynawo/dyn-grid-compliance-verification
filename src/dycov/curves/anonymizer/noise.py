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

from dycov.curves.anonymizer.window import blend_weights, event_window
from dycov.logging import dycov_logging
from dycov.sigpro.sigpro import lowpass_filter

MIN_SCALE = 0.0003
NOISE_GRID = 1e-3  # s


def _is_nearly_flat(series: np.ndarray, threshold: float) -> bool:
    # Use range and std to detect flat signals robustly
    return (np.ptp(series) <= threshold) or (np.nanstd(series) <= threshold / 3.0)


def apply_noise_to_curves(
    df_imported_curve: pd.DataFrame,
    noisestd: float,
    frequency: float,
    event_time: float,
    event_duration: float,
    flat_threshold: float = 1e-4,
) -> None:
    window = [event_window(event_time, event_duration)]

    time_values = df_imported_curve["time"].to_numpy()
    noise_weights = blend_weights(time_values, window)
    noise_window = noise_weights > 0.0

    # The noise is drawn and filtered on a grid of its own, and only then read at the samples
    # of the curve: a reduced curve no longer has a step for the filter to work with.
    noise_grid = np.arange(time_values[0], time_values[-1] + NOISE_GRID, NOISE_GRID)
    grid_weights = blend_weights(noise_grid, window)

    span = time_values[-1] - time_values[0]
    samples_per_second = len(time_values) / span if span > 0 else 1.0

    for column in df_imported_curve.columns:
        if column == "time":
            continue

        values = df_imported_curve[column].to_numpy()

        # Flatness guard: skip noise + filtering if nearly flat
        if _is_nearly_flat(values, flat_threshold) or noisestd <= 0:
            # Keep the signal as-is to avoid introducing artifacts
            continue

        dycov_logging.get_logger("Anonymizer").debug(f"Applying noise to column: {column}")

        # Robust local scale using rolling MAD
        def local_scale(series: np.ndarray, window: int) -> np.ndarray:
            w = max(3, window | 1)
            s = pd.Series(series)
            med = s.rolling(w, center=True, min_periods=1).median()
            mad = (s - med).abs().rolling(w, center=True, min_periods=1).median()
            return np.maximum(mad.to_numpy(), MIN_SCALE)

        window_seconds = 0.5
        window_samples = max(3, int(window_seconds * samples_per_second))
        scale = local_scale(values, window_samples)

        noise = np.random.normal(0.0, noisestd, len(noise_grid)) * grid_weights

        # Smooth noise using constant padding to stabilize boundaries
        noise_smoothed = lowpass_filter(
            noise,
            fc=frequency,
            fs=1.0 / NOISE_GRID,
        )
        noise_smoothed = np.interp(time_values, noise_grid, noise_smoothed) * scale
        # The mean is removed where the noise lives: subtracting it from the whole signal
        # would shift the steady state of a curve that is only noisy around its event.
        noise_smoothed = (noise_smoothed - np.mean(noise_smoothed[noise_window])) * noise_weights

        # Apply noise to the column
        df_imported_curve[column] = values + noise_smoothed
