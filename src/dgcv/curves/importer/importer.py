import configparser
import errno
import os
from pathlib import Path

import pandas as pd

from dgcv.curves.importer.reader import get_curves_reader


class CurvesImporter:
    """Curves importer.

    Regarding the digital format accepted for reference signals provided by the producer, we have:
    - COMTRADE: all versions of the COMTRADE standard up to version C37.111-2013 are admissible.
        The reference signals can optionally be provided in the form of a pair of files in
        DAT+CFG formats (the two files must in this case have the same name and differ only by
        their extension) or a single file in the format SBB.
    - EUROSTAG: EXP ASCII format is supported
    - CSV: the separator used must be ";". A "time" column is required.

    Args
    ----
    path: Path
        Path where the curve files are located
    filename: str
        Name of the curve file without extension
    remove_working_dict: bool
        Remove dictionary from working directory once read
    """

    def __init__(self, path: Path, filename: str, remove_working_dict: bool = True):
        self._path = path
        self._filename = filename

        self._default_curves = configparser.ConfigParser()
        self._default_curves.optionxform = str
        if (path / "CurvesFiles.ini").exists():
            self._default_curves.read(path / "CurvesFiles.ini")
        else:
            self._default_curves.add_section("Curves-Dictionary")
            self._default_curves.add_section("Curves-Dictionary-Zone1")
            self._default_curves.add_section("Curves-Dictionary-Zone3")

        files = [f for f in path.glob(filename + ".[dD][iI][cC][tT]")]
        if not files:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), filename + ".dict")

        dict_file = files[0]
        self._curves_cfg = configparser.ConfigParser()
        self._curves_cfg.optionxform = str
        self._curves_cfg.read(dict_file)
        if remove_working_dict:
            dict_file.unlink()

    @property
    def config(self) -> configparser.ConfigParser:
        """Get the curves configuration file.

        Returns
        -------
        Path
            Defined configuration Curves.
        """
        return self._curves_cfg

    def get_curves_dataframe(
        self, zone, remove_file=True
    ) -> tuple[pd.DataFrame, dict, float, float]:
        """Import a curve file and return its relevant data.

        Returns
        -------
        DataFrame
           Curves imported from the file
        dict
            A dictionary to match the columns of the imported file with the columns expected by
            the tool
        float
            Time at which the event is triggered
        float
            Frequency sampling of the imported curves

        """

        if zone == 1:
            curves_dict = (
                {value: key for key, value in self._default_curves.items("Curves-Dictionary")}
                | {
                    value: key
                    for key, value in self._default_curves.items("Curves-Dictionary-Zone1")
                }
                | {value: key for key, value in self._curves_cfg.items("Curves-Dictionary")}
            )
        elif zone == 3:
            curves_dict = (
                {value: key for key, value in self._default_curves.items("Curves-Dictionary")}
                | {
                    value: key
                    for key, value in self._default_curves.items("Curves-Dictionary-Zone3")
                }
                | {value: key for key, value in self._curves_cfg.items("Curves-Dictionary")}
            )
        else:
            curves_dict = {
                value: key for key, value in self._default_curves.items("Curves-Dictionary")
            } | {value: key for key, value in self._curves_cfg.items("Curves-Dictionary")}
        df_dict = {}
        if self._curves_cfg.has_option("Curves-Dictionary", "time"):
            time_name = self._curves_cfg.get("Curves-Dictionary", "time")
        elif self._default_curves.has_option("Curves-Dictionary", "time"):
            time_name = self._default_curves.get("Curves-Dictionary", "time")
        else:
            time_name = None

        curves_reader = get_curves_reader(self._path, self._filename, time_name)
        curves_reader.load(remove_file)
        df_dict["time"] = curves_reader.time
        for idx, channel_id in enumerate(curves_reader.analog_channel_ids):
            if channel_id not in curves_dict:
                continue

            df_dict[curves_dict[channel_id]] = curves_reader.analog[idx]

        return (
            pd.DataFrame.from_dict(df_dict, orient="columns"),
            curves_dict,
            curves_reader.trigger_time,
            curves_reader.frequency_sampling,
        )
