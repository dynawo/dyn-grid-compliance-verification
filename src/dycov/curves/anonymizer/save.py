#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path

import numpy as np
import pandas as pd

# One microsecond: finer than the 1 ms grid the curves are resampled to before any check.
TIME_PRECISION = 6


def _separated_instants(time: np.ndarray, precision: int) -> np.ndarray:
    """Give every sample an instant of its own, at the precision it is written with.

    A simulation writes a discontinuity as two samples sharing one instant. Whoever reads the
    curve back keeps one of them — the resampling of the validation keeps the first — so the
    other end of the step is lost, and with it the value the curve holds from there on.
    """
    separated = time.astype(float).copy()
    step = 10.0**-precision
    repeated = np.flatnonzero(np.diff(separated) <= 0.0)
    for index in repeated:
        separated[index + 1] = separated[index] + step
    return separated


def save_curve(curves: pd.DataFrame, path: Path, precision: int = TIME_PRECISION):
    # Create a copy to avoid modifying the original DataFrame
    curves_to_save = curves.copy()

    if "time" in curves_to_save:
        curves_to_save["time"] = _separated_instants(
            pd.to_numeric(curves_to_save["time"], errors="coerce").to_numpy(), precision
        )
        # Format 'time' column with specified precision
        curves_to_save["time"] = curves_to_save["time"].map(
            lambda x: f"{x:.{precision}f}" if pd.notna(x) else ""
        )
        # Ensure 'time' is the first column
        cols = ["time"] + [col for col in curves_to_save.columns if col != "time"]
        curves_to_save = curves_to_save[cols]

    # Save to CSV without altering the original DataFrame
    curves_to_save.to_csv(path, sep=";", float_format="%.3e", index=False)
