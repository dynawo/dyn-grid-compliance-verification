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
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from dycov.curves.importer.importer import CurvesImporter
from dycov.files import manage_files
from dycov.logging import dycov_logging
from dycov.sigpro.sigpro import lowpass_filter

MIN_SCALE = 0.0003
# The noise is what makes a reference look measured, and that only matters where the test
# looks: just before the event, during it, and along the response that follows. Away from
# there it buys nothing and costs an order of magnitude in the size of every curve, because
# it is of the same order as the epsilon of the simplification and RDP has to track it.
NOISE_LEAD = 1.0  # s before the event
NOISE_TAIL = 10.0  # s after it
NOISE_GRID = 1e-3  # s
# An event that never clears is declared as lasting longer than the simulation. What the test
# looks at is still the response to it, not the hours it would go on for.
EVENT_SPAN = 10.0  # s at most

# A reference is a record of measurements, and no instrument samples faster than its own rate.
# Without a rate of its own a curve is stored as densely as the solver happened to step, which
# is what a numerical residue too small to matter costs: it is kept sample by sample.
MAX_RATE = 200.0  # Hz, away from the event
MAX_RATE_EVENT = 1000.0  # Hz, where the test looks
# A rate says how often a signal is read, and a step is not read: both of its ends are kept
# whatever the rate, or the instant a fault appears is stored as a ramp of one interval.
EDGE_FRACTION = 0.01  # of the range of a signal
# One microsecond: finer than the 1 ms grid the curves are resampled to before any check.
TIME_PRECISION = 6

# What tells a numerical oscillation apart from a response: swings of at least this size,
# alternating faster than this period, repeated at least this many times in a row.
RIPPLE_GATE = 0.01  # pu
RIPPLE_PERIOD = 0.1  # s
RIPPLE_SWINGS = 6
# The span is filtered on a uniform grid and blended back over this margin at each end.
RIPPLE_GRID = 1e-3  # s
RIPPLE_MARGIN = 0.1  # s


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
        and 'dycov.log' files will be copied from here. Defaults to None.
    curves_folder: Optional[Path]
        Path of a set of curves. If not provided, `output_folder` will be used
        as the source for curves. Defaults to None.
    compression: Optional[float]
        Relative epsilon for curve simplification, as a fraction of each signal's
        range. If None, no compression is applied. Defaults to None.
    deripple: Optional[float]
        Cut-off frequency, in Hz, of the filter that removes the oscillation the simulation
        adds. If None, the curves keep it. Defaults to None.
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
        _process_curves(curves_path, output_path, noisestd, frequency, compression, deripple)

    dycov_logging.get_logger("Anonymizer").info(
        f"Anonymization completed. Anonymized curves saved to {output_folder}"
    )


def _interior_times(t_grid: np.ndarray, min_points: int) -> np.ndarray:
    lengths = np.diff(t_grid)
    splits = {index: 0 for index, length in enumerate(lengths) if length > 0.0}
    if not splits:
        return np.array([])

    for _ in range(min_points - len(t_grid)):
        widest = max(splits, key=lambda index: lengths[index] / (splits[index] + 1))
        splits[widest] += 1

    return np.array(
        [
            time
            for index, count in sorted(splits.items())
            if count
            for time in np.linspace(t_grid[index], t_grid[index + 1], count + 2)[1:-1]
        ]
    )


def _ensure_min_points(df: pd.DataFrame, min_points: int = 10) -> pd.DataFrame:
    if len(df) >= min_points or df.empty:
        return df

    t_grid = df["time"].to_numpy(dtype=float)
    if len(df) == 1:
        t_new = np.linspace(t_grid[0], t_grid[0] + 1e-6, min_points)
        constants = {col: df[col].iloc[0] * np.ones(min_points) for col in df.columns}
        return pd.DataFrame({**constants, "time": t_new})[df.columns]

    t_interior = _interior_times(t_grid, min_points)
    if t_interior.size == 0:
        dycov_logging.get_logger("Anonymizer").warning(
            f"Cannot densify a curve whose {len(df)} samples share the same timestamp; "
            f"leaving it below the {min_points}-sample minimum."
        )
        return df

    order = np.argsort(np.concatenate((t_grid, t_interior)), kind="stable")
    densified = {"time": np.concatenate((t_grid, t_interior))[order]}
    for col in df.columns:
        if col == "time":
            continue
        values = df[col].to_numpy(dtype=float)
        densified[col] = np.concatenate((values, np.interp(t_interior, t_grid, values)))[order]

    return pd.DataFrame(densified)[df.columns]


def _ripple_spans(time: np.ndarray, values: np.ndarray) -> List[tuple]:
    turns = []
    last_extreme = values[0]
    direction = 0
    for instant, value in zip(time, values):
        if abs(value - last_extreme) < RIPPLE_GATE:
            continue
        new_direction = 1 if value > last_extreme else -1
        if direction and new_direction != direction:
            turns.append(instant)
        direction = new_direction
        last_extreme = value

    spans = []
    run_start = None
    run_length = 0
    for turn, next_turn in zip(turns, turns[1:]):
        if next_turn - turn <= RIPPLE_PERIOD:
            run_start = turn if run_start is None else run_start
            run_length += 1
            continue
        if run_length >= RIPPLE_SWINGS:
            spans.append((run_start, turn))
        run_start, run_length = None, 0
    if run_length >= RIPPLE_SWINGS:
        spans.append((run_start, turns[-1]))

    return spans


def _blend_weights(time: np.ndarray, spans: List[tuple]) -> np.ndarray:
    weights = np.zeros(len(time))
    for start, end in spans:
        rising = (time >= start - RIPPLE_MARGIN) & (time < start)
        falling = (time > end) & (time <= end + RIPPLE_MARGIN)
        weights[(time >= start) & (time <= end)] = 1.0
        weights[rising] = np.maximum(
            weights[rising], (time[rising] - start + RIPPLE_MARGIN) / RIPPLE_MARGIN
        )
        weights[falling] = np.maximum(
            weights[falling], (end + RIPPLE_MARGIN - time[falling]) / RIPPLE_MARGIN
        )
    return weights


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


def _deripple_signal(time: np.ndarray, values: np.ndarray, cutoff: float) -> np.ndarray:
    values = _remove_spikes(values)
    spans = _ripple_spans(time, values)
    if not spans:
        return values

    instants, first_of_instant = np.unique(time, return_index=True)
    grid = np.arange(instants[0], instants[-1], RIPPLE_GRID)
    smooth = lowpass_filter(
        np.interp(grid, instants, values[first_of_instant]), fc=cutoff, fs=1 / RIPPLE_GRID
    )

    # The run is bounded by turning points, and the oscillation reaches half a swing beyond
    # each of them: filter that too, or what is left at the edges still oscillates.
    reach = [(start - RIPPLE_PERIOD, end + RIPPLE_PERIOD) for start, end in spans]
    weights = _blend_weights(time, reach)
    return values * (1 - weights) + np.interp(time, grid, smooth) * weights


def _deripple_curves(df: pd.DataFrame, cutoff: float) -> pd.DataFrame:
    time = df["time"].to_numpy(dtype=float)
    cleaned = {"time": time}
    for column in df.columns:
        if column == "time":
            continue
        cleaned[column] = _deripple_signal(time, df[column].to_numpy(dtype=float), cutoff)

    return pd.DataFrame(cleaned)[df.columns]


def _get_files(path: Path, extensions: List[str]) -> List[Path]:
    all_files = []
    for ext in extensions:
        all_files.extend(path.glob(ext))
    return all_files


def _copy_from_path_from_pipeline(results: Path, target_folder: Path) -> None:
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
                "#    SignalName_a =\n"
                "#    SignalName_b =\n"
                "#    SignalName_c =",
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
    curve_extensions = [
        "*.[eE][xX][pP]",
        "*.[cC][sS][vV]",
        "*.[cC][fF][fF]",
        "*.[dD][aA][tT]",
    ]
    for curves_file in _get_files(curves_folder, curve_extensions):
        _create_dict_file_if_not_exists(curves_file, metadata)


def _create_dict_file_if_not_exists(csv_file: Path, metadata: Dict[str, Dict]) -> None:
    dict_file = csv_file.with_suffix(".dict")
    if dict_file.exists():
        dycov_logging.get_logger("Anonymizer").debug(
            f"{dict_file} already exists. Skipping creation."
        )
        return

    if csv_file.stem not in metadata:
        dycov_logging.get_logger("Anonymizer").warning(
            f"No simulation record found for {csv_file.name}: its dictionary declares the event "
            f"at t = 0, which is almost certainly wrong. Check the results directory."
        )
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
            "#    SignalName_a =\n"
            "#    SignalName_b =\n"
            "#    SignalName_c =\n"
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
                for name in ("sim_t_event_start", "fault_duration", "frequency_sampling"):
                    if name in line:
                        metadata[stem][name] = float(line.split("=")[-1])
                        break
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
    noise_event_start = event_time
    noise_event_end = event_time + min(event_duration, EVENT_SPAN)

    time_values = df_imported_curve["time"].to_numpy()
    noise_weights = _blend_weights(
        time_values, [(noise_event_start - NOISE_LEAD, noise_event_end + NOISE_TAIL)]
    )
    noise_window = noise_weights > 0.0

    # The noise is drawn and filtered on a grid of its own, and only then read at the samples
    # of the curve: a reduced curve no longer has a step for the filter to work with.
    noise_grid = np.arange(time_values[0], time_values[-1] + NOISE_GRID, NOISE_GRID)
    grid_weights = _blend_weights(
        noise_grid, [(noise_event_start - NOISE_LEAD, noise_event_end + NOISE_TAIL)]
    )

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


def _process_curves(
    curves_folder: Path,
    output_folder: Path,
    noisestd: float,
    frequency: float,
    compression: Optional[float] = None,
    deripple: Optional[float] = None,
) -> None:
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
        fault_duration = float(curves_cfg.get("Curves-Metadata", "fault_duration"))

        importer = CurvesImporter(curves_folder, curves_path.stem, False)

        if importer.config.has_section("Curves-Dictionary"):
            df_imported_curve = importer.get_curves_dataframe(zone=0, remove_file=False)

            if deripple is not None:
                dycov_logging.get_logger("Anonymizer").debug(
                    f"Removing the simulation oscillation from {curves_path.stem}"
                )
                df_imported_curve = _deripple_curves(df_imported_curve, deripple)

            if compression is not None:
                original_len = len(df_imported_curve)
                df_imported_curve = _simplify_curves(
                    df_imported_curve,
                    event_time=event_time,
                    event_duration=fault_duration,
                    compression=compression,
                )
                df_imported_curve = _cap_rate(df_imported_curve, event_time, fault_duration)
                dycov_logging.get_logger("Anonymizer").debug(
                    f"Simplified {curves_path.stem}: "
                    f"{original_len} → {len(df_imported_curve)} points "
                    f"({100 * len(df_imported_curve) / original_len:.1f}%)"
                )

            # The noise goes on the samples that survive, so that it makes the curve unlike the
            # simulation without making it any larger.
            if noisestd is not None and noisestd > 0:
                dycov_logging.get_logger("Anonymizer").debug(
                    f"Applying noise to {curves_path.stem}"
                )
                _apply_noise_to_curves(
                    df_imported_curve, noisestd, frequency, event_time, fault_duration
                )

            df_imported_curve = _ensure_min_points(df_imported_curve, min_points=10)
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


def _save_curve(curves: pd.DataFrame, path: Path, precision: int = TIME_PRECISION):
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


def _simplify_segment(segment: pd.DataFrame, compression: float) -> pd.DataFrame:
    if len(segment) <= 2:
        return segment

    time_values = segment["time"].to_numpy()
    keep = {0, len(segment) - 1}
    for column in segment.columns:
        if column == "time":
            continue
        values = segment[column].to_numpy()
        signal_range = float(np.ptp(values))
        if signal_range < 1e-12:
            continue
        mask = _rdp_mask_numpy(np.column_stack([time_values, values]), compression * signal_range)
        keep.update(np.where(mask)[0].tolist())

    return segment.iloc[sorted(keep)].reset_index(drop=True)


def _restore_event_points(
    segment: pd.DataFrame, simplified: pd.DataFrame, min_points: int
) -> pd.DataFrame:
    """The epsilon knows the shape of a signal but not where the test looks: the event is held
    to a floor of samples, and refilled with samples of the original, never interpolated ones.
    """
    if len(segment) <= min_points:
        return segment
    if len(simplified) >= min_points:
        return simplified

    refill = np.linspace(0, len(segment) - 1, min_points).astype(int)
    kept = np.where(segment["time"].isin(simplified["time"]).to_numpy())[0]
    return segment.iloc[sorted(set(kept.tolist()) | set(refill.tolist()))].reset_index(drop=True)


def _simplify_curves(
    df: pd.DataFrame,
    event_time: float,
    event_duration: float,
    compression: float = 0.005,
    min_event_points: int = 20,
) -> pd.DataFrame:
    time_values = df["time"].to_numpy()
    before = df[time_values <= event_time].reset_index(drop=True)
    during = df[
        (time_values > event_time) & (time_values <= event_time + event_duration)
    ].reset_index(drop=True)
    after = df[time_values > event_time + event_duration].reset_index(drop=True)

    return pd.concat(
        [
            _simplify_segment(before, compression),
            _restore_event_points(
                during, _simplify_segment(during, compression), min_event_points
            ),
            _simplify_segment(after, compression),
        ],
        ignore_index=True,
    )


def _edge_samples(df: pd.DataFrame) -> np.ndarray:
    edges = np.zeros(len(df), dtype=bool)
    for column in df.columns:
        if column == "time":
            continue
        values = df[column].to_numpy()
        signal_range = float(np.ptp(values))
        if signal_range < 1e-12:
            continue
        steps = np.abs(np.diff(values)) > EDGE_FRACTION * signal_range
        edges[:-1] |= steps
        edges[1:] |= steps
    return edges


def _cap_rate(df: pd.DataFrame, event_time: float, event_duration: float) -> pd.DataFrame:
    if len(df) <= 2:
        return df

    time_values = df["time"].to_numpy()
    window = (time_values >= event_time - NOISE_LEAD) & (
        time_values <= event_time + min(event_duration, EVENT_SPAN) + NOISE_TAIL
    )
    rates = np.where(window, MAX_RATE_EVENT, MAX_RATE)

    interval = np.floor(time_values * rates).astype(np.int64)
    keep = np.empty(len(df), dtype=bool)
    keep[0] = True
    keep[1:] = (interval[1:] != interval[:-1]) | (rates[1:] != rates[:-1])
    keep |= _edge_samples(df)
    keep[-1] = True

    return df[keep].reset_index(drop=True)
