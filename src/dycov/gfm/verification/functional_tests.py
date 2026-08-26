#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es

from pathlib import Path
from typing import Tuple

import pandas as pd


def compare_csv_directories(baseline_dir: Path, output_dir: Path) -> Tuple[bool, str]:
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
    Tuple[bool, str]
        A boolean indicating success, and an error message string if it fails.
    """
    baseline_csvs = list(baseline_dir.rglob("*.csv"))

    # Halt early if baseline is empty to prevent false positives
    if not baseline_csvs:
        return (
            False,
            f"Setup Error: No CSV files were found in the baseline directory '{baseline_dir}'.",
        )

    for baseline_csv in baseline_csvs:
        relative_path = baseline_csv.relative_to(baseline_dir)
        output_csv = output_dir / relative_path

        # 1. Structural Validation
        if not output_csv.exists():
            return False, f"Missing File Error: Expected output file not found at '{output_csv}'."

        # 2. Data Extraction
        try:
            df_baseline = pd.read_csv(baseline_csv, sep=";")
        except Exception as e:
            return (
                False,
                f"I/O Error: Could not read baseline CSV at '{baseline_csv}'. Details: {e}",
            )

        try:
            df_output = pd.read_csv(output_csv, sep=";")
        except Exception as e:
            return False, f"I/O Error: Could not read output CSV at '{output_csv}'. Details: {e}"

        # 3. Mathematical Validation
        try:
            # Allow minor floating-point differences to prevent strict equality failures
            pd.testing.assert_frame_equal(
                df_baseline, df_output, check_exact=False, rtol=1e-5, atol=1e-8
            )
        except AssertionError as e:
            return False, f"Data Mismatch Error in file '{relative_path}':\n{e}"

    return True, ""
