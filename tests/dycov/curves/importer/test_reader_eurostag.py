#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#
"""Reading of the EUROSTAG (.exp) curves supplied by a producer."""

import shutil
from pathlib import Path

import pytest

from dycov.curves.importer.reader import EurostagReader, get_curves_reader

_FILENAME = "fiche8"
_EXP_NAME = f"{_FILENAME}.exp"
_TIME_CHANNEL = "TIME"

_ANALOG_CHANNEL_IDS = [
    "V/N1",
    "V/STAT",
    "GEN     -IEEEST4B-4",
    "- P",
    "- Q",
    "GEN     -OMEGA",
]

_RESOURCES_PATH = Path(__file__).resolve().parent.parent / "resources"


@pytest.fixture
def exp_path(tmp_path: Path) -> Path:
    """Directory holding a single EUROSTAG export."""
    shutil.copy(_RESOURCES_PATH / _EXP_NAME, tmp_path / _EXP_NAME)
    return tmp_path


# ---------------------------------------------------------------------------
# Routing by file type
# ---------------------------------------------------------------------------


def test_get_curves_reader_routes_an_exp_file_to_the_eurostag_reader(exp_path):
    reader = get_curves_reader(exp_path, _FILENAME, _TIME_CHANNEL)

    assert isinstance(reader, EurostagReader)


# ---------------------------------------------------------------------------
# Reading an export that declares its time channel
# ---------------------------------------------------------------------------


def test_load_reads_the_time_steps_of_the_export(exp_path):
    reader = EurostagReader(exp_path, _FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=False)

    assert len(reader.time) == 310
    assert reader.time[0] == pytest.approx(0.0)
    assert reader.time[-1] == pytest.approx(9.882547, rel=1e-5)


def test_load_reads_every_channel_but_the_time_one(exp_path):
    reader = EurostagReader(exp_path, _FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=False)

    assert reader.analog_channel_ids == _ANALOG_CHANNEL_IDS


def test_load_reads_the_values_of_each_channel(exp_path):
    reader = EurostagReader(exp_path, _FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=False)

    assert len(reader.analog) == len(_ANALOG_CHANNEL_IDS)
    assert reader.analog[0][0] == pytest.approx(1.044604, rel=1e-6)
    assert reader.analog[-1][0] == pytest.approx(1.0, rel=1e-6)


def test_load_removes_the_export_when_asked_to(exp_path):
    reader = EurostagReader(exp_path, _FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=True)

    assert not (exp_path / _EXP_NAME).exists()


def test_load_keeps_the_export_when_not_asked_to_remove_it(exp_path):
    reader = EurostagReader(exp_path, _FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=False)

    assert (exp_path / _EXP_NAME).exists()


# ---------------------------------------------------------------------------
# Exports whose time channel cannot be located
# ---------------------------------------------------------------------------


def test_load_without_a_matching_time_channel_names_the_file_and_the_channel(exp_path):
    """Guards against issue #382: an export naming its time column differently."""
    reader = EurostagReader(exp_path, _FILENAME, "Time")

    with pytest.raises(ValueError) as time_error:
        reader.load(remove_file=False)

    assert "Time" in str(time_error.value)
    assert _EXP_NAME in str(time_error.value)


@pytest.mark.parametrize("time_name", ["", None], ids=["blank", "absent"])
def test_load_with_an_undeclared_time_channel_names_the_file_and_the_option(exp_path, time_name):
    """Guards against issue #382: the shipped dictionary template leaves 'time' blank."""
    reader = EurostagReader(exp_path, _FILENAME, time_name)

    with pytest.raises(ValueError) as time_error:
        reader.load(remove_file=False)

    assert "time" in str(time_error.value)
    assert "Curves-Dictionary" in str(time_error.value)
    assert _EXP_NAME in str(time_error.value)
