import configparser
import os
import re
import shutil
import statistics
from pathlib import Path

import numpy as np

from dycov.configuration.cfg import config
from dycov.curves.importer.importer import CurvesImporter
from dycov.sigpro.sigpro import lowpass_filter

NOISE_DAMPING = 100
MIN_SCALE = 0.0003


def _get_files(path: Path, extensions: list) -> list:
    """Get all files in a directory with specified extensions."""
    all_files = []
    for ext in extensions:
        all_files.extend(path.glob(ext))
    return all_files


def _create_directory_if_not_exists(directory: Path) -> None:
    """Create the directory if it does not exist."""
    directory.mkdir(parents=True, exist_ok=True)


def _copy_files_from_pipeline(results: Path, target_folder: Path) -> None:
    """Copy the 'curves_calculated.csv' and 'dycov.log' files from results to
    target_folder and rename them to 'pcs.benchmark.operatingcondition.csv' and
    'pcs.benchmark.operatingcondition.log'."""
    for file in results.rglob("curves_calculated.csv"):
        relative_path = file.relative_to(results).parent
        target_name = ".".join(str(relative_path).split(os.sep)) + ".csv"
        shutil.copy(file, target_folder / target_name)

    for file in results.rglob("dycov.log"):
        relative_path = file.relative_to(results).parent
        target_name = ".".join(str(relative_path).split(os.sep)) + ".log"
        shutil.copy(file, target_folder / target_name)


def _create_curves_files_ini_if_not_exists(curves_folder: Path) -> None:
    curves_files = curves_folder / "CurvesFiles.ini"
    if curves_files.exists():
        return

    curves_files_content = {}
    for curves_file in _get_files(
        curves_folder, ["*.[eE][xX][pP]", "*.[cC][sS][vV]", "*.[cC][fF][fF]", "*.[dD][aA][tT]"]
    ):
        # Suffix includes the dot
        curves_files_content[curves_file.stem] = f"{curves_file.stem}{curves_file.suffix.lower()}"

    for curves_log in _get_files(curves_folder, ["*.log"]):
        if curves_log not in curves_files_content:
            curves_files_content[curves_log.stem] = f"{curves_log.stem}.csv"

    with open(curves_files, "w") as curves_ini:
        curves_ini.write("[Curves-Files]\n")
        for key, value in sorted(curves_files_content.items()):
            curves_ini.write(f"{key} = {value}\n")

        curves_ini.write("\n\n")
        curves_ini.write(
            "[Curves-Dictionary]\n"
            "# To represent a signal that is in raw abc three-phase form, "
            "the affected signal must be tripled\n"
            "# and the suffixes _a, _b and _c must be added as in the following example:\n"
            "#    BusPDR_BUS_Voltage_a =\n"
            "#    BusPDR_BUS_Voltage_b =\n"
            "#    BusPDR_BUS_Voltage_c =\n"
            "[Curves-Dictionary-Zone1]\n"
            "[Curves-Dictionary-Zone3]\n"
        )


def _create_dict_file_if_not_exists(csv_file: Path, metadata: dict) -> None:
    """Create a corresponding .dict file for each .csv file if it doesn't exist."""
    dict_file = csv_file.with_suffix(".dict")
    if dict_file.exists():
        return

    with open(dict_file, "w") as dict_f:
        dict_f.write("[Curves-Metadata]\n")
        dict_f.write(
            f"# True when the reference curves are field measurements\n"
            f"is_field_measurements = {metadata[dict_file.stem]['is_field_measurements']}\n"
            f"# Instant of time at which the event or fault starts\n"
            f"# Variable sim_t_event_start is called simply sim_t_event in the DTR\n"
            f"sim_t_event_start = {metadata[dict_file.stem]['sim_t_event_start']}\n"
            f"# Duration of the event or fault\n"
            f"fault_duration = {metadata[dict_file.stem]['fault_duration']}\n"
            f"# Frequency sampling of the reference curves\n"
            f"frequency_sampling = {metadata[dict_file.stem]['frequency_sampling']}\n"
        )
        dict_f.write("\n")

        dict_f.write("[Curves-Dictionary]\n")
        dict_f.write(
            "# To represent a signal that is in raw abc three-phase form, "
            "the affected signal must be tripled\n"
            "# and the suffixes _a, _b and _c must be added as in the following example:\n"
            "#    BusPDR_BUS_Voltage_a =\n"
            "#    BusPDR_BUS_Voltage_b =\n"
            "#    BusPDR_BUS_Voltage_c =\n"
        )

        with open(csv_file, "r") as csv_f:
            headers = csv_f.readline().strip().split(";")
            for header in headers:
                if not header:
                    continue

                dict_f.write(f"{header} = {header}\n")


def _extract_metadata_from_log(log_file: Path, metadata: dict) -> None:
    """Extract and print the sim_t_event_start parameter from the log file."""
    metadata[log_file.stem] = {}
    metadata[log_file.stem]["is_field_measurements"] = False
    metadata[log_file.stem]["frequency_sampling"] = 15
    with open(log_file, "r") as log_f:
        for line in log_f:
            if "sim_t_event_start" in line:
                metadata[log_file.stem]["sim_t_event_start"] = float(line.split("=")[-1])
            elif "fault_duration" in line:
                metadata[log_file.stem]["fault_duration"] = float(line.split("=")[-1])

    log_file.unlink()


def _apply_noise_to_curves(
    df_imported_curve, noisestd: float, frequency: float, event_time: float, event_duration: float
) -> None:
    """Apply noise to the curve data. Reduced noise before the event, and after the event, full
    noise in the event."""

    noise_event_start = event_time
    noise_event_end = event_time + event_duration
    for column in df_imported_curve:
        if column != "time":

            list_col = list(df_imported_curve[column])

            # Split the curve into before and after event based on event_time
            before_event = len(df_imported_curve[df_imported_curve["time"] <= noise_event_start])
            during_event = (
                len(df_imported_curve[df_imported_curve["time"] <= noise_event_end]) - before_event
            )
            after_event = len(list_col) - before_event - during_event

            median_col = statistics.median(list_col)
            if MIN_SCALE >= median_col:
                median_col = MIN_SCALE

            # Apply reduced noise before the event
            noise_before = (
                np.random.normal(0.0, noisestd, before_event) * median_col / NOISE_DAMPING
            )
            # Apply noise during the event
            noise_during = np.random.normal(0.0, noisestd, during_event) * median_col
            # Apply reduced noise after the event
            noise_after = np.random.normal(0.0, noisestd, after_event) * median_col / NOISE_DAMPING

            # Filter concatenated noises
            t_com = config.get_float("GridCode", "t_com", 0.002)
            resampling_fs = 1 / t_com
            noise = lowpass_filter(
                np.concatenate((noise_before, noise_during, noise_after)),
                fc=frequency,
                fs=resampling_fs,
            )

            # Apply the noise
            df_imported_curve[column] = np.add(list_col, noise)


def _process_curves(
    curves_folder: Path,
    output_folder: Path,
    noisestd: float,
    frequency: float,
) -> None:
    """Process the curves in the curves folder and apply noise according to event time."""
    for curves_path in _get_files(
        curves_folder, ["*.[eE][xX][pP]", "*.[cC][sS][vV]", "*.[cC][fF][fF]", "*.[dD][aA][tT]"]
    ):
        dict_file = curves_path.parent / f"{curves_path.stem}.dict"
        curves_cfg = configparser.ConfigParser(inline_comment_prefixes=("#",))
        curves_cfg.optionxform = str
        curves_cfg.read(dict_file)
        event_time = float(curves_cfg.get("Curves-Metadata", "sim_t_event_start"))
        fault_duration = float(curves_cfg.get("Curves-Metadata", "fault_duration")) + 5.0

        importer = CurvesImporter(curves_folder, curves_path.stem, False)
        if importer.config.has_section("Curves-Dictionary"):
            df_imported_curve = importer.get_curves_dataframe(zone=0, remove_file=False)

            if noisestd is not None:
                # Apply noise to the curve based on event time
                _apply_noise_to_curves(
                    df_imported_curve, noisestd, frequency, event_time, fault_duration
                )

            df_imported_curve = df_imported_curve.set_index("time")
            df_imported_curve.to_csv(output_folder / f"{curves_path.stem}.csv", sep=";")

            with open(dict_file, "r") as file:
                filedata = file.read()

            for item in importer.config.items("Curves-Dictionary"):
                filedata = re.sub(r"\b{}\b".format(re.escape(item[1])), item[0], filedata)

            with open(output_folder / f"{curves_path.stem}.dict", "w") as file:
                file.write(filedata)


def anonymize(
    output_folder: Path,
    noisestd: float,
    frequency: float,
    results: Path = None,
    curves_folder: Path = None,
) -> None:
    """Creates a set of anonymized curves from the input set of curves.

    Parameters
    ----------
    output_folder: Path
        Path where the set of anonymized curves is stored
    noisestd: float
        Standard deviation of the noise added to the curves, in pu
    frequency: float
        Cut-off frequency of the filter used for smoothing the noise, in Hz
    results: Path
        Path of a verification results
    curves_folder: Path
        Path of a set of curves
    """

    # If no curves_folder is provided, use the output_folder to store the pipeline output curves
    if curves_folder is None:
        curves_folder = output_folder

    # Create output_folder if it doesn't exist
    _create_directory_if_not_exists(output_folder)

    # If results is provided, copy the necessary files
    if results:
        _copy_files_from_pipeline(results, curves_folder)

    # Ensure CurvesFiles.ini file exists
    _create_curves_files_ini_if_not_exists(curves_folder)

    # Extract curves metadata from log files
    metadata = {}
    for log_file in curves_folder.glob("*.log"):
        _extract_metadata_from_log(log_file, metadata)

    # Ensure each CSV file has a corresponding .dict file
    for curves_file in _get_files(
        curves_folder, ["*.[eE][xX][pP]", "*.[cC][sS][vV]", "*.[cC][fF][fF]", "*.[dD][aA][tT]"]
    ):
        _create_dict_file_if_not_exists(curves_file, metadata)

    # Process curves and apply noise if needed
    _process_curves(curves_folder, output_folder, noisestd, frequency)
