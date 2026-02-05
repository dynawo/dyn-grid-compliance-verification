#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from __future__ import annotations

import array
from abc import abstractmethod
from pathlib import Path
from typing import TextIO

import pandas as pd
from comtrade import Comtrade

UNLIMITED_COLUMNS = -1


def get_curves_reader(path: Path, filename: str, time_name: str) -> CurvesReader:
    """Get a Curves Reader by file type.

    Parameters
    ----------
    path: Path
        Path where the curve files are located
    filename: str
        Name of the curve file
    time_name: str
        Name of the column with the simulations steps

    Returns
    -------
    CurvesReader
        A reader for the selected file

    Raises
    ------
    Exception
        Not supported type
    """
    exp_files = list(path.glob(filename + ".[eE][xX][pP]"))
    csv_files = list(path.glob(filename + ".[cC][sS][vV]"))
    cff_files = list(path.glob(filename + ".[cC][fF][fF]"))
    dat_files = list(path.glob(filename + ".[dD][aA][tT]"))

    if exp_files:
        reader = EurostagReader(path, filename, time_name)
    elif csv_files:
        reader = CsvReader(path, filename, time_name)
    elif cff_files or dat_files:
        reader = ComtradeReader(path, filename, time_name)
    else:
        raise IOError(f"Not supported data: {filename}")

    return reader


def read_sep_values(
    line: str, sep: str, expected: int = UNLIMITED_COLUMNS, default: str = ""
) -> list:
    """Split a line in several columns.

    Parameters
    ----------
    line: str
        Line to split
    sep: str
        Separator string/character
    expected: int
        Expected number of columns
    default: str
        Default text if column do not exists

    Returns
    -------
    list
        A list of values
    """
    values = list(map(str.strip, line.split(sep)))
    if expected != UNLIMITED_COLUMNS and len(values) > expected:
        values = values[:expected]
    return values


class CurvesReader:
    """Curves Reader Interface.

    Args
    ----
    path: Path
        Path where the curve files are located
    filename: str
        Name of the curve file
    time_name: str
        Name of the column with the simulations steps
    """

    def __init__(self, path: Path, filename: str, time_name: str):
        self._path = path
        self._filename = filename

        self._analog_channel_ids = []
        self._time_values = []
        self._analog_values = []
        self._analog_count = 0
        self._column_count = 0

        self._time_name = time_name
        self._frequency_sampling = 0
        self._trigger_time = 0

    @property
    def analog_channel_ids(self) -> list:
        """Returns the names of the columns.

        Returns
        -------
        list
            Names of the columns
        """
        return self._analog_channel_ids

    @property
    def analog(self) -> list:
        """Returns a list of values by column.

        Returns
        -------
        list
            A list of values by column
        """
        return self._analog_values

    @property
    def time(self) -> list:
        """Returns the simulation time steps.

        Returns
        -------
        list
            A list of the simulation time steps
        """
        return self._time_values

    @property
    def trigger_time(self) -> float:
        """Returns the time at which the event is triggered.

        Returns
        -------
        float
            Instant of time
        """
        return self._trigger_time

    @property
    def frequency_sampling(self) -> float:
        """Returns the frequency sampling of the imported curves.

        Returns
        -------
        float
            The frequency sampling
        """
        return self._frequency_sampling

    @abstractmethod
    def load(self, remove_file: bool = True) -> None:
        """Parse file contents

        Parameters
        ----------
        remove_file: bool, optional
            Whether to remove the file after reading. Default is True.
        """
        pass


class ComtradeReader(CurvesReader):
    def load(self, remove_file: bool = True) -> None:
        """Load a COMTRADE file.

        Parameters
        ----------
        remove_file: bool, optional
            Whether to remove the file after reading. Default is True.
        """
        rec = Comtrade()
        cfg_files = list(self._path.glob(self._filename + ".[cC][fF][gG]"))
        if cfg_files:
            cfg_file = cfg_files[0]
            dat_file = next(self._path.glob(self._filename + ".[dD][aA][tT]"))
            rec.load(cfg_file.as_posix(), dat_file.as_posix())
            if remove_file:
                cfg_file.unlink()
                dat_file.unlink()

        cff_files = list(self._path.glob(self._filename + ".[cC][fF][fF]"))
        if cff_files:
            cff_file = cff_files[0]
            rec.load(cff_file.as_posix())
            if remove_file:
                cff_file.unlink()

        self._analog_channel_ids = rec.analog_channel_ids
        self._time_values = rec.time
        self._analog_values = rec.analog
        self._frequency_sampling = rec.cfg.sample_rates[-1][0]
        self._trigger_time = rec.trigger_time


class CsvReader(CurvesReader):
    def __read(self, data: pd.DataFrame) -> None:
        """Read and import the data from the file.

        Parameters
        ----------
        data: DataFrame
            Dataframe with all the curves data
        """
        self._time_values = data[self._time_name]
        self._analog_count = int(len(data[self._time_name]))

        value_data = data.loc[:, ~data.columns.isin([self._time_name])]
        self._column_count = len(value_data.columns)
        self._analog_channel_ids = [None] * self._column_count
        self._analog_values = [None] * self._column_count

        for idx, column_name in enumerate(value_data.columns):
            self._analog_channel_ids[idx] = column_name
            self._analog_values[idx] = value_data[column_name]

    def load(self, remove_file: bool = True) -> None:
        """Load a CSV file.

        Parameters
        ----------
        remove_file: bool, optional
            Whether to remove the file after reading. Default is True.
        """
        file = next(self._path.glob(self._filename + ".[cC][sS][vV]"))
        data = pd.read_csv(file.as_posix(), sep=None, engine="python")
        self.__read(data)
        if remove_file:
            file.unlink()


class EurostagReader(CurvesReader):
    def __read(self, data: TextIO) -> None:
        """Read and import the data from the file.

        Parameters
        ----------
        data: TextIO
            Object with all the curves data
        """
        # First line: obtain number of results
        line = data.readline()
        packed = read_sep_values(line, " ")
        self._analog_count = int(packed[len(packed) - 2])
        self._time_values = array.array("f", [0] * self._analog_count)

        # Variable lines
        line = data.readline()
        packed = read_sep_values(line, ";")
        while len(packed) == 1:
            line = data.readline()
            packed = read_sep_values(line, ";")

        # Column names line
        self._column_count = len(packed) - 2
        self._analog_channel_ids = [None] * self._column_count
        column_idx = 0
        for idx, channel_idx in enumerate(packed):
            if channel_idx == self._time_name:
                time_idx = idx
            elif channel_idx == "":
                pass
            else:
                self._analog_channel_ids[column_idx] = channel_idx
                column_idx = column_idx + 1

        # Preallocate analog values
        self._analog_values = [None] * self._column_count
        for i in range(self._column_count):
            self._analog_values[i] = array.array("f", [0] * self._analog_count)

        # Column values lines
        for idx in range(self._analog_count):
            line = data.readline()
            values = line.strip().split(";")

            ts = values[time_idx]
            self._time_values[idx] = float(ts)

            column_idx = 0
            for value_idx, value in enumerate(values):
                if value_idx == time_idx or value_idx > self._column_count:
                    pass
                else:
                    self._analog_values[column_idx][idx] = float(value)
                    column_idx = column_idx + 1

    def load(self, remove_file: bool = True) -> None:
        """Load an EUROSTAG file.

        Parameters
        ----------
        remove_file: bool, optional
            Whether to remove the file after reading. Default is True.
        """
        file = next(self._path.glob(self._filename + ".[eE][xX][pP]"))
        with open(file.as_posix(), "r") as data:
            self.__read(data)
        if remove_file:
            file.unlink()
