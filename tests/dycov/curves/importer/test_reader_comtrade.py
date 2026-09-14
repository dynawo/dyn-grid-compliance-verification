#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#
"""Reading of the COMTRADE curves supplied by a producer."""

import shutil
from pathlib import Path

import pytest

from dycov.curves.importer.reader import ComtradeReader, get_curves_reader

_FILENAME = "Wind_farm_comtrade_example"
_CFG_NAME = f"{_FILENAME}.cfg"
_DAT_NAME = f"{_FILENAME}.dat"

_TIME_CHANNEL = "time"

_RESOURCES_PATH = Path(__file__).resolve().parent.parent / "resources"

_CFF_FILENAME = "single_file_record"
_CFF_NAME = f"{_CFF_FILENAME}.cff"

_CFF_CONFIGURATION = (
    "DyCoV,ReaderTest,2013\n"
    "2,2A,0D\n"
    "1,Vac_a,,,V,1.0,0.0,0.0,-32767,32767,1.0,1.0,P\n"
    "2,Iac_a,,,A,1.0,0.0,0.0,-32767,32767,1.0,1.0,P\n"
    "50.0\n"
    "1\n"
    "1000.0,3\n"
    "01/01/2026,00:00:00.000000\n"
    "01/01/2026,00:00:00.001000\n"
    "ASCII\n"
    "1.0\n"
)

_CFF_DATA = "1,0,10,20\n2,1000,11,21\n3,2000,12,22\n"

_CFF_CONTENT = (
    "--- file type: CFG ---\n"
    f"{_CFF_CONFIGURATION}"
    "--- file type: INF ---\n"
    "--- file type: HDR ---\n"
    "--- file type: DAT ASCII ---\n"
    f"{_CFF_DATA}"
)


@pytest.fixture
def comtrade_path(tmp_path: Path) -> Path:
    """Directory holding a COMTRADE record as a CFG and DAT pair."""
    shutil.copy(_RESOURCES_PATH / _CFG_NAME, tmp_path / _CFG_NAME)
    shutil.copy(_RESOURCES_PATH / _DAT_NAME, tmp_path / _DAT_NAME)
    return tmp_path


@pytest.fixture
def orphan_dat_path(tmp_path: Path) -> Path:
    """Directory holding the data file of a COMTRADE record, without its configuration."""
    shutil.copy(_RESOURCES_PATH / _DAT_NAME, tmp_path / _DAT_NAME)
    return tmp_path


@pytest.fixture
def cff_path(tmp_path: Path) -> Path:
    """Directory holding a COMTRADE record as a single CFF file."""
    (tmp_path / _CFF_NAME).write_text(_CFF_CONTENT)
    return tmp_path


# ---------------------------------------------------------------------------
# Routing by file type
# ---------------------------------------------------------------------------


def test_get_curves_reader_routes_a_cff_file_to_the_comtrade_reader(cff_path):
    reader = get_curves_reader(cff_path, _CFF_FILENAME, _TIME_CHANNEL)

    assert isinstance(reader, ComtradeReader)


def test_get_curves_reader_routes_a_dat_file_to_the_comtrade_reader(comtrade_path):
    reader = get_curves_reader(comtrade_path, _FILENAME, _TIME_CHANNEL)

    assert isinstance(reader, ComtradeReader)


# ---------------------------------------------------------------------------
# Reading a record supplied as a CFG and DAT pair
# ---------------------------------------------------------------------------


def test_load_reads_the_channels_of_a_cfg_and_dat_pair(comtrade_path):
    reader = ComtradeReader(comtrade_path, _FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=False)

    assert reader.analog_channel_ids[0] == "meas_PCC1/Vac_a@control"
    assert reader.analog_channel_ids[-1] == "meas_PCC1/Ineg_q@control"
    assert len(reader.analog) == len(reader.analog_channel_ids)


def test_load_reads_the_time_steps_of_a_cfg_and_dat_pair(comtrade_path):
    reader = ComtradeReader(comtrade_path, _FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=False)

    assert reader.time[0] == pytest.approx(0.0)
    assert reader.time[-1] == pytest.approx(7.5)


def test_load_reads_the_sampling_frequency_and_the_trigger_time(comtrade_path):
    reader = ComtradeReader(comtrade_path, _FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=False)

    assert reader.frequency_sampling == pytest.approx(12500.0, rel=1e-6)
    assert reader.trigger_time == pytest.approx(2.584, abs=1e-3)


def test_load_removes_both_files_of_the_pair_when_asked_to(comtrade_path):
    reader = ComtradeReader(comtrade_path, _FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=True)

    assert not (comtrade_path / _CFG_NAME).exists()
    assert not (comtrade_path / _DAT_NAME).exists()


# ---------------------------------------------------------------------------
# Reading a record supplied as a single CFF file
# ---------------------------------------------------------------------------


def test_load_reads_the_channels_of_a_cff_file(cff_path):
    reader = ComtradeReader(cff_path, _CFF_FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=False)

    assert reader.analog_channel_ids == ["Vac_a", "Iac_a"]
    assert list(reader.analog[0]) == pytest.approx([10.0, 11.0, 12.0])
    assert reader.frequency_sampling == pytest.approx(1000.0)


def test_load_removes_the_cff_file_when_asked_to(cff_path):
    reader = ComtradeReader(cff_path, _CFF_FILENAME, _TIME_CHANNEL)

    reader.load(remove_file=True)

    assert not (cff_path / _CFF_NAME).exists()


# ---------------------------------------------------------------------------
# Records without a configuration file
# ---------------------------------------------------------------------------


def test_load_without_a_configuration_file_names_the_record_and_what_it_needs(orphan_dat_path):
    """Guards against issue #383: a DAT file routed here without its CFG companion."""
    reader = ComtradeReader(orphan_dat_path, _FILENAME, _TIME_CHANNEL)

    with pytest.raises(FileNotFoundError) as missing_cfg_error:
        reader.load(remove_file=False)

    assert _FILENAME in str(missing_cfg_error.value)
    assert _CFG_NAME in str(missing_cfg_error.value)
    assert f"{_FILENAME}.cff" in str(missing_cfg_error.value)


def test_load_without_a_configuration_file_keeps_the_data_file(orphan_dat_path):
    reader = ComtradeReader(orphan_dat_path, _FILENAME, _TIME_CHANNEL)

    with pytest.raises(FileNotFoundError):
        reader.load(remove_file=True)

    assert (orphan_dat_path / _DAT_NAME).exists()
