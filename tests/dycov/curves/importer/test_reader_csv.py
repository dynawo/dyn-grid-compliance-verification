#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#
"""Reading of the CSV curves supplied by a producer."""

import shutil
from pathlib import Path

import pytest

from dycov.curves.importer.reader import CsvReader, get_curves_reader

_FILENAME = "curves_final"
_CSV_NAME = f"{_FILENAME}.csv"
_TIME_CHANNEL = "time"

_FIRST_CHANNEL = "LineAll_line_P2Pu"
_LAST_CHANNEL = "Synch_Gen_generator_UStatorPu_value"

_RESOURCES_PATH = Path(__file__).resolve().parent.parent / "resources"


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    """Directory holding a single CSV of curves."""
    shutil.copy(_RESOURCES_PATH / _CSV_NAME, tmp_path / _CSV_NAME)
    return tmp_path


# ---------------------------------------------------------------------------
# Routing by file type
# ---------------------------------------------------------------------------


def test_get_curves_reader_routes_a_csv_file_to_the_csv_reader(csv_path):
    reader = get_curves_reader(csv_path, _FILENAME, _TIME_CHANNEL)

    assert isinstance(reader, CsvReader)


# ---------------------------------------------------------------------------
# Reading a CSV that declares its time channel
# ---------------------------------------------------------------------------


def test_load_reads_the_time_steps_of_the_csv(csv_path):
    reader = CsvReader(csv_path, _FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=False)

    assert reader.time.iloc[0] == pytest.approx(0.0)
    assert reader.time.iloc[-1] == pytest.approx(100.0)


def test_load_reads_every_column_but_the_time_one(csv_path):
    reader = CsvReader(csv_path, _FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=False)

    assert _TIME_CHANNEL not in reader.analog_channel_ids
    assert reader.analog_channel_ids[0] == _FIRST_CHANNEL
    assert reader.analog_channel_ids[-1] == _LAST_CHANNEL
    assert len(reader.analog) == len(reader.analog_channel_ids)


def test_load_removes_the_csv_when_asked_to(csv_path):
    reader = CsvReader(csv_path, _FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=True)

    assert not (csv_path / _CSV_NAME).exists()


# ---------------------------------------------------------------------------
# CSVs whose time channel cannot be located
# ---------------------------------------------------------------------------


def test_load_without_a_matching_time_channel_names_the_file_and_the_channel(csv_path):
    """A mistyped time column must stop the run, not degrade it to "no curves"."""
    reader = CsvReader(csv_path, _FILENAME, "Time")

    with pytest.raises(ValueError) as time_error:
        reader.load(remove_file=False)

    assert "Time" in str(time_error.value)
    assert _CSV_NAME in str(time_error.value)


@pytest.mark.parametrize("time_name", ["", None], ids=["blank", "absent"])
def test_load_with_an_undeclared_time_channel_names_the_file_and_the_option(csv_path, time_name):
    """The shipped dictionary template leaves 'time' blank."""
    reader = CsvReader(csv_path, _FILENAME, time_name)

    with pytest.raises(ValueError) as time_error:
        reader.load(remove_file=False)

    assert "time" in str(time_error.value)
    assert "Curves-Dictionary" in str(time_error.value)
    assert _CSV_NAME in str(time_error.value)
