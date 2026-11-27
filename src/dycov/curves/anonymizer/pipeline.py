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
import glob
import re
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from dycov.curves import naming
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
    They are prepared in a copy next to `output_folder`, which receives one folder per
    producer of the set, each with its index, and the source is left as it was.

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
        Path of a set of curves. If not provided, the curves are those `results` copies into
        `output_folder`, which is emptied first. Defaults to None.
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
    manage_files.create_dir(output_folder)
    _remove_interrupted_staging(output_folder)

    with tempfile.TemporaryDirectory(
        dir=output_folder.parent, prefix=_staging_prefix(output_folder)
    ) as staging_dir:
        staging = Path(staging_dir)
        if curves_folder is not None:
            _stage_curves(curves_folder, staging)
        if results:
            dycov_logging.get_logger("Anonymizer").info(
                f"Copying curves_calculated.csv and simulation_inputs.ini from {results}"
            )
            copy_from_pipeline(results, staging)

        for curves_path in _producer_dirs(staging):
            output_path = output_folder / curves_path.relative_to(staging)
            dycov_logging.get_logger("Anonymizer").info(f"Processing producer path: {output_path}")
            output_path.mkdir(parents=True, exist_ok=True)

            create_curves_files_ini(curves_path)
            metadata: Dict[str, Dict] = extract_metadata_from_logs(curves_path)
            create_dict_files(curves_path, metadata)
            _process_curves(curves_path, output_path, noisestd, frequency, compression, deripple)
            (output_path / "CurvesFiles.ini").write_text(
                _anonymized_index(curves_path / "CurvesFiles.ini", output_path)
            )

    dycov_logging.get_logger("Anonymizer").info(
        f"Anonymization completed. Anonymized curves saved to {output_folder}"
    )


def _staging_prefix(output_folder: Path) -> str:
    return f".{output_folder.name}.staging."


def _remove_interrupted_staging(output_folder: Path) -> None:
    """Remove the copies a run into the same output left when a signal ended it."""
    for staging in output_folder.parent.glob(glob.escape(_staging_prefix(output_folder)) + "*"):
        shutil.rmtree(staging, ignore_errors=True)


def _producer_dirs(curves_folder: Path) -> list:
    """The folders of a set of curves: one per producer that holds curves, or the set itself."""
    producer_dirs = [
        d for d in sorted(curves_folder.iterdir()) if d.is_dir() and any(curve_files(d))
    ]
    return producer_dirs or [curves_folder]


def _stage_curves(curves_folder: Path, staging: Path) -> None:
    """Copy the files of every producer folder of the set into the folder the anonymization
    prepares them in, which writes their index and dictionaries and consumes their records."""
    for producer_dir in _producer_dirs(curves_folder):
        target = staging / producer_dir.relative_to(curves_folder)
        target.mkdir(parents=True, exist_ok=True)
        for file in producer_dir.iterdir():
            if file.is_file():
                shutil.copy2(file, target / file.name)


def _anonymized_index(index: Path, output_folder: Path) -> str:
    """The index of the anonymized curves of a folder: each test names the ``.csv`` its curves
    were anonymized into, a test whose curves were not is left out, and the dictionaries keep
    none of the names of the producer's columns, which the dictionary of each curve declares."""
    lines, section = [], None
    for line in index.read_text().splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("["):
            section = stripped
        elif "=" in stripped and not stripped.startswith("#"):
            if section != "[Curves-Files]":
                continue
            test, curves_file = (part.strip() for part in stripped.split("=", 1))
            anonymized = f"{Path(curves_file).stem}.csv"
            if not (output_folder / anonymized).is_file():
                dycov_logging.get_logger("Anonymizer").warning(
                    f"{test} is left out of the anonymized index: its curves file "
                    f"{curves_file} is not one of the files anonymized"
                )
                continue
            line = f"{test} = {anonymized}\n"
        lines.append(line)
    return "".join(lines)


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
        # The importer has read the curve under its current name, and the file just written
        # carries that name: a curve declared under a previous one is declared again under it.
        curve_name = naming.from_legacy_name(original_id)
        # Use word boundaries to avoid replacing parts of other names
        filedata = re.sub(r"\b{}\b".format(re.escape(dict_name)), curve_name, filedata)
        filedata = re.sub(
            r"^{}\b".format(re.escape(original_id)), curve_name, filedata, flags=re.MULTILINE
        )
    output_path.write_text(filedata)
