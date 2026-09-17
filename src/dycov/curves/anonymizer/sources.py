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
from typing import Dict, List

from dycov.files import manage_files
from dycov.logging import dycov_logging


def get_files(path: Path, extensions: List[str]) -> List[Path]:
    all_files = []
    for ext in extensions:
        all_files.extend(path.glob(ext))
    return all_files


def copy_from_pipeline(results: Path, target_folder: Path) -> None:
    for producer_path in results.iterdir():
        if producer_path.is_dir() and producer_path.name != "Reports":
            dycov_logging.get_logger("Anonymizer").debug(
                f"Processing producer directory: {producer_path}"
            )
            manage_files.create_dir(target_folder / producer_path.name)
            # Copy files from the producer directory
            copy_from_producer(
                producer_path,
                target_folder / producer_path.name,
            )


def copy_from_producer(results: Path, target_folder: Path) -> None:
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


def create_curves_files_ini(curves_folder: Path) -> None:
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
    for curves_file in get_files(curves_folder, curve_extensions):
        curves_files_content[curves_file.stem] = f"{curves_file.stem}{curves_file.suffix.lower()}"

    for curves_log in get_files(curves_folder, ["*.log"]):
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


def create_dict_files(curves_folder: Path, metadata: Dict[str, Dict]) -> None:
    curve_extensions = [
        "*.[eE][xX][pP]",
        "*.[cC][sS][vV]",
        "*.[cC][fF][fF]",
        "*.[dD][aA][tT]",
    ]
    for curves_file in get_files(curves_folder, curve_extensions):
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


def extract_metadata_from_logs(curves_folder: Path) -> Dict[str, Dict]:
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
