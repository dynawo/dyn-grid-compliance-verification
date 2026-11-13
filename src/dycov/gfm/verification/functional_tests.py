#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

from pathlib import Path
from typing import Optional

import pandas as pd


def compare_csv_directories(baseline_dir: Path, output_dir: Path) -> tuple[bool, str]:
    """
    Recursively compares all CSV files from a baseline directory against an output directory.

    Parameters
    ----------
    baseline_dir : Path
        The directory containing the baseline CSV files for comparison.
    output_dir : Path
        The directory containing the generated output CSV files.

    Returns
    -------
    tuple[bool, str]
        Whether every CSV of the baseline has a match in the output directory, and the error
        of the first that does not. A baseline without CSV files is an error.
    """
    baseline_csvs = list(baseline_dir.rglob("*.csv"))
    if not baseline_csvs:
        return (
            False,
            f"Setup Error: No CSV files were found in the baseline directory '{baseline_dir}'.",
        )

    for baseline_csv in baseline_csvs:
        error = _compare_csv(baseline_csv, baseline_dir, output_dir)
        if error:
            return False, error
    return True, ""


def _compare_csv(baseline_csv: Path, baseline_dir: Path, output_dir: Path) -> Optional[str]:
    """The error of comparing a CSV of the baseline with its namesake in the output, if any."""
    relative_path = baseline_csv.relative_to(baseline_dir)
    output_csv = output_dir / relative_path

    if not output_csv.exists():
        return f"Missing File Error: Expected output file not found at '{output_csv}'."

    try:
        df_baseline = pd.read_csv(baseline_csv, sep=";")
    except Exception as e:
        return f"I/O Error: Could not read baseline CSV at '{baseline_csv}'. Details: {e}"

    try:
        df_output = pd.read_csv(output_csv, sep=";")
    except Exception as e:
        return f"I/O Error: Could not read output CSV at '{output_csv}'. Details: {e}"

    try:
        pd.testing.assert_frame_equal(
            df_baseline, df_output, check_exact=False, rtol=1e-5, atol=1e-8
        )
    except AssertionError as e:
        return f"Data Mismatch Error in file '{relative_path}':\n{e}"
    return None
