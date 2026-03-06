#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import configparser
import re
import statistics
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from dycov.curves.importer.importer import CurvesImporter
from dycov.files import manage_files
from dycov.logging.logging import dycov_logging
from dycov.sigpro.sigpro import lowpass_filter

NOISE_DAMPING = 100
MIN_SCALE = 0.0003
ORIGINAL_IMPLEMENTATION = False  # Set to True to use the original noise application method


def anonymize(
    output_folder: Path,
    noisestd: float,
    frequency: float,
    results: Optional[Path] = None,
    curves_folder: Optional[Path] = None,
    epsilon_relative: Optional[float] = None,
) -> None:
    """Creates a set of anonymized curves from the input set of curves.

    This function can either process curves from a specified folder or from a
    pipeline's results, apply noise, and generate new curve and dictionary files.

    Parameters
    ----------
    output_folder: Path
        The path where the set of anonymized curves is stored.
    noisestd: float
        Standard deviation of the noise added to the curves, in pu.
    frequency: float
        Cut-off frequency of the filter used for smoothing the noise, in Hz.
    results: Optional[Path]
        Path of a verification results directory. If provided, 'curves_calculated.csv'
        and 'dycov.log' files will be copied from here. Defaults to None.
    curves_folder: Optional[Path]
        Path of a set of curves. If not provided, `output_folder` will be used
        as the source for curves. Defaults to None.
    epsilon_relative: Optional[float]
        Relative epsilon for curve simplification, as a fraction of each signal's
        range. If None, no compression is applied. Defaults to None.
    """
    dycov_logging.get_logger("Anonymizer").info(
        f"Anonymizing curves to {output_folder} with noise std {noisestd} "
        f"and frequency {frequency} Hz and epsilon_relative {epsilon_relative}"
    )
    if curves_folder is None:
        curves_folder = output_folder

    manage_files.create_dir(output_folder)

    if results:
        dycov_logging.get_logger("Anonymizer").info(
            f"Copying curves_calculated.csv and dycov.log from {results} to {curves_folder}"
        )
        _copy_from_path_from_pipeline(results, curves_folder)

    # Detect producer dirs AFTER copying, so files are already in place
    curve_extensions = ["*.[eE][xX][pP]", "*.[cC][sS][vV]", "*.[cC][fF][fF]", "*.[dD][aA][tT]"]
    producer_dirs = [
        d
        for d in sorted(curves_folder.iterdir())
        if d.is_dir() and any(_get_files(d, curve_extensions))
    ]
    if not producer_dirs:
        producer_dirs = [curves_folder]

    for curves_path in producer_dirs:
        dycov_logging.get_logger("Anonymizer").info(f"Processing producer path: {curves_path}")

        # output_path mirrors the producer subdir name under output_folder,
        # but must never coincide with curves_path (source == destination causes data loss)
        relative = curves_path.relative_to(curves_folder)
        output_path = output_folder / relative

        _create_curves_files_ini_if_not_exists(curves_path)

        metadata: Dict[str, Dict] = _extract_metadata_from_logs(curves_path)
        _create_dict_files_if_not_exist(curves_path, metadata)
        _process_curves(curves_path, output_path, noisestd, frequency, epsilon_relative)

    dycov_logging.get_logger("Anonymizer").info(
        f"Anonymization completed. Anonymized curves saved to {output_folder}"
    )


def _get_files(path: Path, extensions: List[str]) -> List[Path]:
    """Retrieves all files in a directory that match any of the specified extensions.

    Parameters
    ----------
    path: Path
        The directory to search for files.
    extensions: list
        A list of file extensions (e.g., ["*.exp", "*.csv"]).

    Returns
    -------
    list
        A list of Path objects for the matching files.
    """
    all_files = []
    for ext in extensions:
        all_files.extend(path.glob(ext))
    return all_files


def _copy_from_path_from_pipeline(results: Path, target_folder: Path) -> None:
    """Copies 'curves_calculated.csv' and 'dycov.log' files from the results
    directory to the target folder, renaming them based on their relative path.

    Parameters
    ----------
    results: Path
        The root directory containing the simulation results.
    target_folder: Path
        The destination folder where the files will be copied.
    """
    for producer_path in results.iterdir():
        if producer_path.is_dir() and producer_path.name != "Reports":
            dycov_logging.get_logger("Anonymizer").debug(
                f"Processing producer directory: {producer_path}"
            )
            manage_files.create_dir(target_folder / producer_path.name)
            # Copy files from the producer directory
            _copy_from_path_from_producer(
                producer_path,
                target_folder / producer_path.name,
            )


def _copy_from_path_from_producer(results: Path, target_folder: Path) -> None:
    """Copies 'curves_calculated.csv' and 'dycov.log' files from the producer results
    directory to the producer target folder, renaming them based on their relative path.

    Parameters
    ----------
    results: Path
        The root directory containing the simulation results.
    target_folder: Path
        The destination folder where the files will be copied.
    """
    # Define file types to copy and their target suffixes
    files_to_copy = {
        "curves_calculated.csv": ".csv",
        "dycov.log": ".log",
    }

    for original_filename, target_suffix in files_to_copy.items():
        for file in results.rglob(original_filename):
            relative_path = file.relative_to(results).parent
            # Convert relative path to a dot-separated name
            target_name = ".".join(map(str, relative_path.parts)) + target_suffix
            target_file_path = target_folder / target_name
            manage_files.copy_file(file, target_file_path)
            dycov_logging.get_logger("Anonymizer").debug(f"Copied {file} to {target_file_path}")


def _create_curves_files_ini_if_not_exists(curves_folder: Path) -> None:
    """Creates a 'CurvesFiles.ini' file in the specified curves folder if it does
    not already exist.

    This file lists the available curve files and defines default dictionary
    sections.

    Parameters
    ----------
    curves_folder: Path
        The directory where the 'CurvesFiles.ini' file should be created.
    """
    curves_files_ini_path = curves_folder / "CurvesFiles.ini"
    if curves_files_ini_path.exists():
        dycov_logging.get_logger("Anonymizer").debug(
            f"{curves_files_ini_path} already exists. Skipping creation."
        )
        return

    curves_files_content: Dict[str, str] = {}
    curve_extensions = [
        "*.[eE][xX][pP]",
        "*.[cC][sS][vV]",
        "*.[cC][fF][fF]",
        "*.[dD][aA][tT]",
    ]
    for curves_file in _get_files(curves_folder, curve_extensions):
        curves_files_content[curves_file.stem] = f"{curves_file.stem}{curves_file.suffix.lower()}"

    for curves_log in _get_files(curves_folder, ["*.log"]):
        if curves_log.stem not in curves_files_content:
            curves_files_content[curves_log.stem] = f"{curves_log.stem}.csv"

    ini_sections = {
        "Curves-Files": sorted(curves_files_content.items()),
        "Curves-Dictionary": [
            (
                None,
                "# To represent a signal that is in raw abc three-phase form, "
                "the affected signal must be tripled\n"
                "# and the suffixes _a, _b and _c must be added as in the "
                "following example:\n"
                "#    BusPDR_BUS_Voltage_a =\n"
                "#    BusPDR_BUS_Voltage_b =\n"
                "#    BusPDR_BUS_Voltage_c =",
            )
        ],
        "Curves-Dictionary-Zone1": [],
        "Curves-Dictionary-Zone3": [],
    }

    with open(curves_files_ini_path, "w") as curves_ini:
        for section, items in ini_sections.items():
            curves_ini.write(f"[{section}]\n")
            for key, value in items:
                if key is None:  # For comments or multi-line descriptions
                    curves_ini.write(f"{value}\n")
                else:
                    curves_ini.write(f"{key} = {value}\n")
            curves_ini.write("\n\n")
    dycov_logging.get_logger("Anonymizer").debug(
        f"Created CurvesFiles.ini at {curves_files_ini_path}"
    )


def _create_dict_files_if_not_exist(curves_folder: Path, metadata: Dict[str, Dict]) -> None:
    """Ensures each supported curve file has a corresponding .dict file, creating
    it if it doesn't exist.

    Parameters
    ----------
    curves_folder: Path
        The directory containing the original curve files.
    metadata: Dict[str, Dict]
        A dictionary containing metadata for various curve files, keyed by their
        stem.
    """
    curve_extensions = [
        "*.[eE][xX][pP]",
        "*.[cC][sS][vV]",
        "*.[cC][fF][fF]",
        "*.[dD][aA][tT]",
    ]
    for curves_file in _get_files(curves_folder, curve_extensions):
        _create_dict_file_if_not_exists(curves_file, metadata)


def _create_dict_file_if_not_exists(csv_file: Path, metadata: Dict[str, Dict]) -> None:
    """Creates a corresponding .dict file for a given .csv file if it doesn't
    already exist.

    This .dict file includes metadata extracted from log files and a default
    Curves-Dictionary section with headers from the CSV.

    Parameters
    ----------
    csv_file: Path
        The path to the CSV file for which a .dict file is to be created.
    metadata: Dict[str, Dict]
        A dictionary containing metadata for various curve files, keyed by their
        stem.
    """
    dict_file = csv_file.with_suffix(".dict")
    if dict_file.exists():
        dycov_logging.get_logger("Anonymizer").debug(
            f"{dict_file} already exists. Skipping creation."
        )
        return

    # Ensure metadata for this stem exists, provide defaults if not.
    # This scenario should ideally not happen if _extract_metadata_from_log is
    # called first for all relevant logs, but acts as a safeguard.
    stem_metadata = metadata.get(
        csv_file.stem,
        {
            "is_field_measurements": False,
            "sim_t_event_start": 0.0,
            "fault_duration": 0.0,
            "frequency_sampling": 15.0,
        },
    )

    with open(dict_file, "w") as dict_f:
        dict_f.write("[Curves-Metadata]\n")
        dict_f.write(
            f"# True when the reference curves are field measurements\n"
            f"is_field_measurements = {stem_metadata['is_field_measurements']}\n"
            f"# Instant of time at which the event or fault starts\n"
            f"# Variable sim_t_event_start is called simply sim_t_event in the DTR\n"
            f"sim_t_event_start = {stem_metadata['sim_t_event_start']}\n"
            f"# Duration of the event or fault\n"
            f"fault_duration = {stem_metadata['fault_duration']}\n"
            f"# Frequency sampling of the reference curves\n"
            f"frequency_sampling = {stem_metadata['frequency_sampling']}\n"
        )
        dict_f.write("\n")

        dict_f.write("[Curves-Dictionary]\n")
        dict_f.write(
            "# To represent a signal that is in raw abc three-phase form, "
            "the affected signal must be tripled\n"
            "# and the suffixes _a, _b and _c must be added as in the "
            "following example:\n"
            "#    BusPDR_BUS_Voltage_a =\n"
            "#    BusPDR_BUS_Voltage_b =\n"
            "#    BusPDR_BUS_Voltage_c =\n"
        )

        try:
            with open(csv_file, "r") as csv_f:
                headers = csv_f.readline().strip().split(";")
                for header in headers:
                    if header:
                        dict_f.write(f"{header} = {header}\n")
        except FileNotFoundError:
            dycov_logging.get_logger("Anonymizer").warning(
                f"CSV file {csv_file} not found when creating dictionary. "
                "Headers will not be added."
            )
    dycov_logging.get_logger("Anonymizer").debug(f"Created dictionary file {dict_file}")


def _extract_metadata_from_logs(curves_folder: Path) -> Dict[str, Dict]:
    """Extracts 'sim_t_event_start' and 'fault_duration' parameters from log
    files and stores them in the metadata dictionary. Log files are then deleted.

    Parameters
    ----------
    curves_folder: Path
        The directory containing the log files to parse.

    Returns
    -------
    Dict[str, Dict]
        The dictionary containing the extracted metadata, keyed by log file stem.
    """
    metadata: Dict[str, Dict] = {}
    for log_file in curves_folder.glob("*.log"):
        stem = log_file.stem
        metadata[stem] = {
            "is_field_measurements": False,
            "frequency_sampling": 15.0,
            "sim_t_event_start": 0.0,
            "fault_duration": 0.0,
        }
        with open(log_file, "r") as log_f:
            for line in log_f:
                if "sim_t_event_start" in line:
                    metadata[stem]["sim_t_event_start"] = float(line.split("=")[-1])
                elif "fault_duration" in line:
                    metadata[stem]["fault_duration"] = float(line.split("=")[-1])
        log_file.unlink()  # Delete the log file after extraction
        dycov_logging.get_logger("Anonymizer").debug(
            f"Extracted metadata from {log_file} and deleted it."
        )
    return metadata


def _apply_noise_to_curves(
    df_imported_curve: pd.DataFrame,
    noisestd: float,
    frequency: float,
    event_time: float,
    event_duration: float,
    flat_threshold: float = 1e-4,
) -> None:
    """Applies noise to the curve data in the DataFrame.

    Noise is reduced before and after the event and full during the event.
    The noise is then smoothed using a low-pass filter.

    Parameters
    ----------
    df_imported_curve: pd.DataFrame
        The DataFrame containing the curve data, including a 'time' column.
    noisestd: float
        Standard deviation of the noise to be applied.
    frequency: float
        Cut-off frequency for the low-pass filter (in Hz).
    event_time: float
        The start time of the event.
    event_duration: float
        The duration of the event.
    flat_threshold: float = 1e-4,
        Threshold to consider the signal nearly flat.
    """
    noise_event_start = event_time
    noise_event_end = event_time + event_duration

    # Calculate resampling frequency from the time column in the DataFrame
    time_step = np.mean(np.diff(df_imported_curve["time"].to_numpy()))
    resampling_fs = 1 / time_step
    dycov_logging.get_logger("Anonymizer").debug(
        f"Calculated resampling frequency: {resampling_fs} Hz"
    )

    for column in df_imported_curve.columns:
        if column == "time":
            continue

        values = df_imported_curve[column].to_numpy()

        # Flatness guard: skip noise + filtering if nearly flat
        if _is_nearly_flat(values, flat_threshold) or noisestd <= 0:
            # Keep the signal as-is to avoid introducing artifacts
            continue

        dycov_logging.get_logger("Anonymizer").debug(f"Applying noise to column: {column}")

        # Determine indices for before, during, and after event periods
        before_event_idx = df_imported_curve[df_imported_curve["time"] <= noise_event_start].shape[
            0
        ]
        during_event_idx = df_imported_curve[
            (df_imported_curve["time"] > noise_event_start)
            & (df_imported_curve["time"] <= noise_event_end)
        ].shape[0]
        after_event_idx = len(values) - before_event_idx - during_event_idx

        if ORIGINAL_IMPLEMENTATION:
            median_col = statistics.median(values.tolist())
            # Prevent excessive noise on small signals
            if abs(median_col) < MIN_SCALE:
                median_col = MIN_SCALE if median_col >= 0 else -MIN_SCALE

            noise_before = (
                np.random.normal(0.0, noisestd, before_event_idx) * median_col / NOISE_DAMPING
            )
            noise_during = np.random.normal(0.0, noisestd, during_event_idx) * median_col
            noise_after = (
                np.random.normal(0.0, noisestd, after_event_idx) * median_col / NOISE_DAMPING
            )
        else:
            # Robust local scale using rolling MAD
            def local_scale(series: np.ndarray, window: int) -> np.ndarray:
                w = max(3, window | 1)
                s = pd.Series(series)
                med = s.rolling(w, center=True, min_periods=1).median()
                mad = (s - med).abs().rolling(w, center=True, min_periods=1).median()
                return np.maximum(mad.to_numpy(), MIN_SCALE)

            window_seconds = 0.5
            window_samples = max(3, int(window_seconds * resampling_fs))
            scale = local_scale(values, window_samples)

            noise_before = np.random.normal(0.0, noisestd, before_event_idx) * (
                scale[:before_event_idx] / NOISE_DAMPING
            )
            noise_during = (
                np.random.normal(0.0, noisestd, during_event_idx)
                * scale[before_event_idx : before_event_idx + during_event_idx]
            )
            noise_after = np.random.normal(0.0, noisestd, after_event_idx) * (
                scale[-after_event_idx:] / NOISE_DAMPING
            )

        noise = np.concatenate((noise_before, noise_during, noise_after))

        # Smooth noise using constant padding to stabilize boundaries
        noise_smoothed = lowpass_filter(
            noise,
            fc=frequency,
            fs=resampling_fs,
        )

        # Apply noise to the column
        df_imported_curve[column] = values + noise_smoothed


def _process_curves(
    curves_folder: Path,
    output_folder: Path,
    noisestd: float,
    frequency: float,
    epsilon_relative: Optional[float] = None,
) -> None:
    """Processes all curve files in the specified folder, applies noise if
    `noisestd` is not None, and saves the anonymized curves and updated
    dictionary files to the output folder.

    Parameters
    ----------
    curves_folder: Path
        The directory containing the original curve files and their .dict files.
    output_folder: Path
        The directory where the processed (anonymized) curves and .dict files
        will be saved.
    noisestd: float
        Standard deviation of the noise to be applied. If None, no noise is
        applied.
    frequency: float
        Cut-off frequency for the low-pass filter (in Hz), used if noise is
        applied.
    epsilon_relative: Optional[float] = 0.001
        Relative epsilon for RDP compression. If None, no compression is applied.
    """
    curve_extensions = [
        "*.[eE][xX][pP]",
        "*.[cC][sS][vV]",
        "*.[cC][fF][fF]",
        "*.[dD][aA][tT]",
    ]
    for curves_path in _get_files(curves_folder, curve_extensions):
        dycov_logging.get_logger("Anonymizer").debug(f"Processing curve file: {curves_path.name}")
        dict_file = curves_path.parent / f"{curves_path.stem}.dict"

        curves_cfg = configparser.ConfigParser(inline_comment_prefixes=("#",))
        curves_cfg.optionxform = str
        curves_cfg.read(dict_file)

        event_time = float(curves_cfg.get("Curves-Metadata", "sim_t_event_start"))
        if ORIGINAL_IMPLEMENTATION:
            fault_duration = (
                float(curves_cfg.get("Curves-Metadata", "fault_duration")) + 5.0
            )  # Add 5.0 as per original script's logic
        else:
            fault_duration = float(curves_cfg.get("Curves-Metadata", "fault_duration"))

        importer = CurvesImporter(curves_folder, curves_path.stem, False)

        if importer.config.has_section("Curves-Dictionary"):
            df_imported_curve = importer.get_curves_dataframe(zone=0, remove_file=False)

            if noisestd is not None and noisestd > 0:
                dycov_logging.get_logger("Anonymizer").debug(
                    f"Applying noise to {curves_path.stem}"
                )
                _apply_noise_to_curves(
                    df_imported_curve, noisestd, frequency, event_time, fault_duration
                )

            if epsilon_relative is not None:
                original_len = len(df_imported_curve)
                df_imported_curve = _simplify_curves(  # renamed
                    df_imported_curve,
                    event_time=event_time,
                    event_duration=fault_duration,
                    epsilon_relative=epsilon_relative,
                )
                dycov_logging.get_logger("Anonymizer").debug(
                    f"Simplified {curves_path.stem}: "  # updated log message
                    f"{original_len} → {len(df_imported_curve)} points "
                    f"({100 * len(df_imported_curve) / original_len:.1f}%)"
                )

            df_imported_curve = df_imported_curve.set_index("time")
            output_csv_path = output_folder / f"{curves_path.stem}.csv"
            _save_curve(df_imported_curve.reset_index(), output_csv_path)
            dycov_logging.get_logger("Anonymizer").debug(
                f"Saved anonymized curve to {output_csv_path}"
            )

            with open(dict_file, "r") as file:
                filedata = file.read()

            for original_id, dict_name in importer.config.items("Curves-Dictionary"):
                # Use word boundaries to avoid replacing parts of other names
                filedata = re.sub(r"\b{}\b".format(re.escape(dict_name)), original_id, filedata)

            output_dict_path = output_folder / f"{curves_path.stem}.dict"
            with open(output_dict_path, "w") as file:
                file.write(filedata)
            dycov_logging.get_logger("Anonymizer").debug(
                f"Saved updated dictionary file to {output_dict_path}"
            )
        else:
            dycov_logging.get_logger("Anonymizer").warning(
                f"No 'Curves-Dictionary' section found in {dict_file}. Skipping curve processing."
            )


def _is_nearly_flat(series: np.ndarray, threshold: float) -> bool:
    # Use range and std to detect flat signals robustly
    return (np.ptp(series) <= threshold) or (np.nanstd(series) <= threshold / 3.0)


def _save_curve(curves: pd.DataFrame, path: Path, precision: int = 9):
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


def _rdp_mask_numpy(points: np.ndarray, epsilon: float) -> np.ndarray:
    """Iterative RDP using numpy vectorized distance calculation.
    Returns a boolean mask of points to keep.
    """
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


def _simplify_curves(
    df: pd.DataFrame,
    event_time: float,
    event_duration: float,
    epsilon_relative: float = 0.001,
    min_event_points: int = 20,
) -> pd.DataFrame:
    """Compress curve points using adaptive RDP simplification per signal range.

    Flat regions outside the event are reduced to ~2 points.
    The event zone retains at least min_event_points regardless of epsilon.
    Resulting timestamps are non-uniform — requires interpolation before comparison.
    """
    time_vals = df["time"].to_numpy()
    rows_to_keep = {0, len(df) - 1}

    # Always protect event zone with a minimum point density
    event_mask = (df["time"] > event_time) & (df["time"] <= event_time + event_duration)
    event_indices = df.index[event_mask].tolist()
    if len(event_indices) <= min_event_points:
        rows_to_keep.update(event_indices)
    else:
        step = max(1, len(event_indices) // min_event_points)
        rows_to_keep.update(event_indices[::step])

    for col in df.columns:
        if col == "time":
            continue

        values = df[col].to_numpy()
        signal_range = np.ptp(values)

        # Flat signal: keep only boundaries
        if signal_range < 1e-6:
            continue

        # Epsilon relative to each signal's own range to handle mixed units (V, A, pu, Hz...)
        epsilon = epsilon_relative * signal_range
        points = np.column_stack([time_vals, values])
        mask = _rdp_mask_numpy(points, epsilon)
        rows_to_keep.update(np.where(mask)[0])

    return df.iloc[sorted(rows_to_keep)].reset_index(drop=True)
