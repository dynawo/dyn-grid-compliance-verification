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

import pandas as pd

# One microsecond: finer than the 1 ms grid the curves are resampled to before any check.
TIME_PRECISION = 6


def save_curve(curves: pd.DataFrame, path: Path, precision: int = TIME_PRECISION):
    # Create a copy to avoid modifying the original DataFrame
    curves_to_save = curves.copy()

    if "time" in curves_to_save:
        # Format 'time' column with specified precision
        curves_to_save["time"] = pd.to_numeric(curves_to_save["time"], errors="coerce").map(
            lambda x: f"{x:.{precision}f}" if pd.notna(x) else ""
        )
        # Ensure 'time' is the first column
        cols = ["time"] + [col for col in curves_to_save.columns if col != "time"]
        curves_to_save = curves_to_save[cols]

    # Save to CSV without altering the original DataFrame
    curves_to_save.to_csv(path, sep=";", float_format="%.3e", index=False)
