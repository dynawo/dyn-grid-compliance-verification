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
import errno
import os
import re
from pathlib import Path

import pandas as pd

from dycov.curves.importer.reader import get_curves_reader


class CurvesImporter:
    """Curves importer.

    Regarding the digital format accepted for reference signals provided by the producer, we have:
    - COMTRADE: all versions of the COMTRADE standard up to version C37.111-2013 are admissible.
        The reference signals can optionally be provided in the form of a pair of files in
        DAT+CFG formats (the two files must in this case have the same name and differ only by
        their extension) or a single file in the format SBB.
    - EUROSTAG: EXP ASCII format is supported
    - CSV: the separator used must be ";". A "time" column is required.

    Parameters
    ----------
    path: Path
        Path where the curve files are located
    filename: str
        Name of the curve file without extension
    remove_working_dict: bool, optional
        Remove dictionary from working directory once read. Defaults to True.
    """

    def __init__(self, path: Path, filename: str, remove_working_dict: bool = True):
        self._path = path
        self._filename = filename

        self._default_curves = configparser.ConfigParser(inline_comment_prefixes=("#",))
        self._default_curves.optionxform = str
        if (path / "CurvesFiles.ini").exists():
            self._default_curves.read(path / "CurvesFiles.ini")
        else:
            # Initialize sections even if the file doesn't exist
            self._default_curves.add_section("Curves-Dictionary")
            self._default_curves.add_section("Curves-Dictionary-Zone1")
            self._default_curves.add_section("Curves-Dictionary-Zone3")

        # Search for the dictionary file matching the pattern
        pattern = re.compile(rf".*.{re.escape(filename)}.[dD][iI][cC][tT]")
        files = [file for file in path.resolve().iterdir() if pattern.match(str(file))]
        if not files:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), f"{filename}.dict")

        dict_file = files[0]
        self._curves_cfg = configparser.ConfigParser(inline_comment_prefixes=("#",))
        self._curves_cfg.optionxform = str
        self._curves_cfg.read(dict_file)

        # Remove the dictionary file from the working directory if requested
        if remove_working_dict:
            dict_file.unlink()

    def __get_curves_dict(self, zone: int) -> dict:
        """
        Constructs a dictionary of curve mappings based on default and zone-specific
        configurations.

        Parameters
        ----------
        zone: int
            The zone identifier (1 for Zone1, 3 for Zone3).

        Returns
        -------
        dict
            A dictionary mapping curve IDs to their corresponding names.
        """
        # Load default curves
        curves_dict = {
            value: key
            for key, value in self._default_curves.items("Curves-Dictionary")
            if value != ""
        }

        # Update with zone-specific curves
        if zone == 1:
            curves_dict.update(
                {
                    value: key
                    for key, value in self._default_curves.items("Curves-Dictionary-Zone1")
                    if value != ""
                }
            )
        elif zone == 3:
            curves_dict.update(
                {
                    value: key
                    for key, value in self._default_curves.items("Curves-Dictionary-Zone3")
                    if value != ""
                }
            )

        # Update with curves from the specific curve configuration file, overriding previous values
        curves_dict.update(
            {
                value: key
                for key, value in self._curves_cfg.items("Curves-Dictionary")
                if value != ""
            }
        )
        return curves_dict

    @property
    def config(self) -> configparser.ConfigParser:
        """
        Gets the curves configuration file.

        Returns
        -------
        configparser.ConfigParser
            The loaded curves configuration.
        """
        return self._curves_cfg

    def get_curves_dataframe(self, zone: int, remove_file: bool = True) -> pd.DataFrame:
        """
        Imports a curve file and returns its relevant data as a Pandas DataFrame.

        Parameters
        ----------
        zone: int
            If running the Model Validation:
            * 1: Zone1 (the individual generating unit)
            * 3: Zone3 (the whole plant)
        remove_file: bool, optional
            Whether to remove the original curve file after reading. Defaults to True.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the imported curves, including a 'time' column.
        """
        curves_dict = self.__get_curves_dict(zone)
        df_dict = {}
        section = "Curves-Dictionary"
        time_name = None

        # Determine the time channel name from curves_cfg or default_curves
        if self._curves_cfg.has_section(section) and self._curves_cfg.has_option(section, "time"):
            time_name = self._curves_cfg.get(section, "time")
        elif self._default_curves.has_section(section) and self._default_curves.has_option(
            section, "time"
        ):
            time_name = self._default_curves.get("Curves-Dictionary", "time")

        # Load curves using the appropriate reader
        curves_reader = get_curves_reader(self._path, self._filename, time_name)
        curves_reader.load(remove_file)

        # Populate the DataFrame dictionary
        df_dict["time"] = curves_reader.time
        for idx, channel_id in enumerate(curves_reader.analog_channel_ids):
            if channel_id not in curves_dict:
                continue
            df_dict[curves_dict[channel_id]] = curves_reader.analog[idx]

        return pd.DataFrame.from_dict(df_dict, orient="columns")
