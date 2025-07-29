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

# Initialize logger for the Anonymizer module
_LOGGER = dycov_logging.get_logger("Anonymizer")

NOISE_DAMPING = 100
MIN_SCALE = 0.0003


def anonymize(
    output_folder: Path,
    noisestd: float,
    frequency: float,
    results: Optional[Path] = None,
    curves_folder: Optional[Path] = None,
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
    """
    _LOGGER.info(
        f"Anonymizing curves to {output_folder} with noise std {noisestd} "
        f"and frequency {frequency} Hz"
    )
    if curves_folder is None:
        curves_folder = output_folder

    manage_files.create_dir(output_folder)

    if results:
        _LOGGER.info(
            f"Copying curves_calculated.csv and dycov.log from {results} to {curves_folder}"
        )
        _copy_files_from_pipeline(results, curves_folder)

    _create_curves_files_ini_if_not_exists(curves_folder)

    metadata: Dict[str, Dict] = _extract_metadata_from_logs(curves_folder)

    _create_dict_files_if_not_exist(curves_folder, metadata)

    _process_curves(curves_folder, output_folder, noisestd, frequency)


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


def _copy_files_from_pipeline(results: Path, target_folder: Path) -> None:
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
            _LOGGER.debug(f"Processing producer directory: {producer_path}")
            manage_files.create_dir(target_folder / producer_path.name)
            # Copy files from the producer directory
            _copy_files_from_producer(
                producer_path,
                target_folder / producer_path.name,
            )


def _copy_files_from_producer(results: Path, target_folder: Path) -> None:
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
            _LOGGER.debug(f"Copied {file} to {target_file_path}")


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
        _LOGGER.debug(f"{curves_files_ini_path} already exists. Skipping creation.")
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
    _LOGGER.info(f"Created CurvesFiles.ini at {curves_files_ini_path}")


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
        _LOGGER.debug(f"{dict_file} already exists. Skipping creation.")
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
            _LOGGER.warning(
                f"CSV file {csv_file} not found when creating dictionary. "
                "Headers will not be added."
            )
    _LOGGER.info(f"Created dictionary file {dict_file}")


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
        _LOGGER.debug(f"Extracted metadata from {log_file} and deleted it.")
    return metadata


def _apply_noise_to_curves(
    df_imported_curve: pd.DataFrame,
    noisestd: float,
    frequency: float,
    event_time: float,
    event_duration: float,
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
    """
    noise_event_start = event_time
    noise_event_end = event_time + event_duration

    # Calculate resampling frequency from the time column in the DataFrame
    time_step = np.mean(np.diff(df_imported_curve["time"].to_numpy()))
    resampling_fs = 1 / time_step
    _LOGGER.debug(f"Calculated resampling frequency: {resampling_fs} Hz")

    for column in df_imported_curve.columns:
        if column == "time":
            continue

        list_col = df_imported_curve[column].tolist()
        _LOGGER.debug(f"Applying noise to column: {column}")

        # Determine indices for before, during, and after event periods
        before_event_idx = df_imported_curve[df_imported_curve["time"] <= noise_event_start].shape[
            0
        ]
        during_event_idx = df_imported_curve[
            (df_imported_curve["time"] > noise_event_start)
            & (df_imported_curve["time"] <= noise_event_end)
        ].shape[0]
        after_event_idx = len(list_col) - before_event_idx - during_event_idx

        median_col = statistics.median(list_col)
        # Ensure median_col is not too small to prevent division by zero or
        # extremely large noise
        if abs(median_col) < MIN_SCALE:
            median_col = MIN_SCALE if median_col >= 0 else -MIN_SCALE
            _LOGGER.debug(f"Adjusted median_col to {median_col} due to MIN_SCALE.")

        # Apply reduced noise before the event
        noise_before = (
            np.random.normal(0.0, noisestd, before_event_idx) * median_col / NOISE_DAMPING
        )
        # Apply noise during the event
        noise_during = np.random.normal(0.0, noisestd, during_event_idx) * median_col
        # Apply reduced noise after the event
        noise_after = np.random.normal(0.0, noisestd, after_event_idx) * median_col / NOISE_DAMPING

        # Concatenate noises and apply low-pass filter
        noise = lowpass_filter(
            np.concatenate((noise_before, noise_during, noise_after)),
            fc=frequency,
            fs=resampling_fs,
        )

        # Apply the noise to the column
        df_imported_curve[column] = np.add(list_col, noise)


def _process_curves(
    curves_folder: Path,
    output_folder: Path,
    noisestd: float,
    frequency: float,
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
    """
    curve_extensions = [
        "*.[eE][xX][pP]",
        "*.[cC][sS][vV]",
        "*.[cC][fF][fF]",
        "*.[dD][aA][tT]",
    ]
    for curves_path in _get_files(curves_folder, curve_extensions):
        _LOGGER.info(f"Processing curve file: {curves_path.name}")
        dict_file = curves_path.parent / f"{curves_path.stem}.dict"

        curves_cfg = configparser.ConfigParser(inline_comment_prefixes=("#",))
        curves_cfg.optionxform = str
        curves_cfg.read(dict_file)

        event_time = float(curves_cfg.get("Curves-Metadata", "sim_t_event_start"))
        fault_duration = (
            float(curves_cfg.get("Curves-Metadata", "fault_duration")) + 5.0
        )  # Add 5.0 as per original script's logic

        importer = CurvesImporter(curves_folder, curves_path.stem, False)

        if importer.config.has_section("Curves-Dictionary"):
            df_imported_curve = importer.get_curves_dataframe(zone=0, remove_file=False)

            if noisestd is not None and noisestd > 0:
                _LOGGER.debug(f"Applying noise to {curves_path.stem}")
                _apply_noise_to_curves(
                    df_imported_curve, noisestd, frequency, event_time, fault_duration
                )

            df_imported_curve = df_imported_curve.set_index("time")
            output_csv_path = output_folder / f"{curves_path.stem}.csv"
            df_imported_curve.to_csv(output_csv_path, sep=";", float_format="%.3e")
            _LOGGER.info(f"Saved anonymized curve to {output_csv_path}")

            with open(dict_file, "r") as file:
                filedata = file.read()

            for original_id, dict_name in importer.config.items("Curves-Dictionary"):
                # Use word boundaries to avoid replacing parts of other names
                filedata = re.sub(r"\b{}\b".format(re.escape(dict_name)), original_id, filedata)

            output_dict_path = output_folder / f"{curves_path.stem}.dict"
            with open(output_dict_path, "w") as file:
                file.write(filedata)
            _LOGGER.info(f"Saved updated dictionary file to {output_dict_path}")
        else:
            _LOGGER.warning(
                f"No 'Curves-Dictionary' section found in {dict_file}. Skipping curve processing."
            )
