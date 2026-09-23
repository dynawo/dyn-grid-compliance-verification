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
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from dycov.curves.anonymizer.deripple import deripple_curves
from dycov.curves.anonymizer.noise import apply_noise_to_curves
from dycov.curves.anonymizer.reduce import cap_rate, ensure_min_points, simplify_curves
from dycov.curves.anonymizer.save import save_curve
from dycov.curves.anonymizer.sources import (
    copy_from_pipeline,
    create_curves_files_ini,
    create_dict_files,
    curve_files,
    extract_metadata_from_logs,
)
from dycov.curves.importer.importer import CurvesImporter
from dycov.files import manage_files
from dycov.logging import dycov_logging


def anonymize(
    output_folder: Path,
    noisestd: float,
    frequency: float,
    results: Optional[Path] = None,
    curves_folder: Optional[Path] = None,
    compression: Optional[float] = None,
    deripple: Optional[float] = None,
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
        and 'simulation_inputs.ini' files will be copied from here. Defaults to None.
    curves_folder: Optional[Path]
        Path of a set of curves. If not provided, `output_folder` will be used
        as the source for curves. Defaults to None.
    compression: Optional[float]
        Relative epsilon for curve simplification, as a fraction of each signal's range,
        which also holds the curve to a sampling rate. Zero keeps every sample.
    deripple: Optional[float]
        Cut-off frequency, in Hz, of the filter that removes the oscillation the simulation
        adds. Zero keeps the oscillation.
    """
    dycov_logging.get_logger("Anonymizer").info(
        f"Anonymizing curves to {output_folder} with noise std {noisestd} "
        f"and frequency {frequency} Hz, compression {compression} and deripple {deripple}"
    )
    if curves_folder is None:
        curves_folder = output_folder

    manage_files.create_dir(output_folder)

    if results:
        dycov_logging.get_logger("Anonymizer").info(
            f"Copying curves_calculated.csv and simulation_inputs.ini from {results} "
            f"to {curves_folder}"
        )
        copy_from_pipeline(results, curves_folder)

    # Detect producer dirs AFTER copying, so files are already in place
    producer_dirs = [
        d for d in sorted(curves_folder.iterdir()) if d.is_dir() and any(curve_files(d))
    ]
    if not producer_dirs:
        producer_dirs = [curves_folder]

    for curves_path in producer_dirs:
        dycov_logging.get_logger("Anonymizer").info(f"Processing producer path: {curves_path}")

        # output_path mirrors the producer subdir name under output_folder,
        # but must never coincide with curves_path (source == destination causes data loss)
        relative = curves_path.relative_to(curves_folder)
        output_path = output_folder / relative

        create_curves_files_ini(curves_path)

        metadata: Dict[str, Dict] = extract_metadata_from_logs(curves_path)
        create_dict_files(curves_path, metadata)
        _process_curves(curves_path, output_path, noisestd, frequency, compression, deripple)

    dycov_logging.get_logger("Anonymizer").info(
        f"Anonymization completed. Anonymized curves saved to {output_folder}"
    )


def _process_curves(
    curves_folder: Path,
    output_folder: Path,
    noisestd: float,
    frequency: float,
    compression: Optional[float] = None,
    deripple: Optional[float] = None,
) -> None:
    for curves_path in curve_files(curves_folder):
        dycov_logging.get_logger("Anonymizer").debug(f"Processing curve file: {curves_path.name}")
        _process_curve(
            curves_path, curves_folder, output_folder, noisestd, frequency, compression, deripple
        )


def _process_curve(
    curves_path: Path,
    curves_folder: Path,
    output_folder: Path,
    noisestd: float,
    frequency: float,
    compression: Optional[float],
    deripple: Optional[float],
) -> None:
    dict_file = curves_path.parent / f"{curves_path.stem}.dict"
    importer = CurvesImporter(curves_folder, curves_path.stem, False)
    if not importer.config.has_section("Curves-Dictionary"):
        dycov_logging.get_logger("Anonymizer").warning(
            f"No 'Curves-Dictionary' section found in {dict_file}. Skipping curve processing."
        )
        return

    event_time, event_duration = _declared_event(dict_file)
    curve = _anonymized_curve(
        importer.get_curves_dataframe(zone=0, remove_file=False),
        curves_path.stem,
        event_time,
        event_duration,
        noisestd,
        frequency,
        compression,
        deripple,
    )

    output_csv_path = output_folder / f"{curves_path.stem}.csv"
    save_curve(curve, output_csv_path)
    dycov_logging.get_logger("Anonymizer").debug(f"Saved anonymized curve to {output_csv_path}")

    output_dict_path = output_folder / f"{curves_path.stem}.dict"
    _save_dictionary(dict_file, importer, output_dict_path)
    dycov_logging.get_logger("Anonymizer").debug(
        f"Saved updated dictionary file to {output_dict_path}"
    )


def _declared_event(dict_file: Path) -> tuple:
    curves_cfg = configparser.ConfigParser(inline_comment_prefixes=("#",))
    curves_cfg.optionxform = str
    curves_cfg.read(dict_file)
    return (
        float(curves_cfg.get("Curves-Metadata", "sim_t_event_start")),
        float(curves_cfg.get("Curves-Metadata", "fault_duration")),
    )


def _anonymized_curve(
    curve: pd.DataFrame,
    name: str,
    event_time: float,
    event_duration: float,
    noisestd: float,
    frequency: float,
    compression: Optional[float],
    deripple: Optional[float],
) -> pd.DataFrame:
    if deripple:
        dycov_logging.get_logger("Anonymizer").debug(
            f"Removing the simulation oscillation from {name}"
        )
        curve = deripple_curves(curve, deripple, event_time)

    if compression:
        original_len = len(curve)
        curve = simplify_curves(
            curve,
            event_time=event_time,
            event_duration=event_duration,
            compression=compression,
        )
        curve = cap_rate(curve, event_time, event_duration)
        dycov_logging.get_logger("Anonymizer").debug(
            f"Simplified {name}: {original_len} → {len(curve)} points "
            f"({100 * len(curve) / original_len:.1f}%)"
        )

    # The noise goes on the samples that survive, so that it makes the curve unlike the
    # simulation without making it any larger.
    if noisestd is not None and noisestd > 0:
        dycov_logging.get_logger("Anonymizer").debug(f"Applying noise to {name}")
        apply_noise_to_curves(curve, noisestd, frequency, event_time, event_duration)

    return ensure_min_points(curve, min_points=10)


def _save_dictionary(dict_file: Path, importer: CurvesImporter, output_path: Path) -> None:
    filedata = dict_file.read_text()
    for original_id, dict_name in importer.config.items("Curves-Dictionary"):
        # A curve the set does not carry names no column, and an empty pattern would match
        # at every word boundary; it stays declared with nothing on its right.
        if not dict_name:
            continue
        # Use word boundaries to avoid replacing parts of other names
        filedata = re.sub(r"\b{}\b".format(re.escape(dict_name)), original_id, filedata)
    output_path.write_text(filedata)
