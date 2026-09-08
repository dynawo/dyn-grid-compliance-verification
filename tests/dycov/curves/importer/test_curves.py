#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#
"""Import of producer curves and of the metadata that describes them."""

import logging
from pathlib import Path

import pytest

from dycov.curves.importer.curves import ImportedCurves

_IC = "dycov.curves.importer.curves"

_PCS = "PCSX"
_BM = "Bm"
_OC = "Oc"
_CFG_OC_NAME = f"{_PCS}.{_BM}.{_OC}"
_DICT_NAME = f"{_CFG_OC_NAME}.dict"

_FILLED_METADATA = (
    "[Curves-Metadata]\n"
    "sim_t_event_start = 20.0\n"
    "fault_duration = 1.5\n"
    "is_field_measurements = False\n"
)

_METADATA_WITHOUT_EVENT_START = "[Curves-Metadata]\nfrequency_sampling = 15\n"

_UNFILLED_METADATA = (
    "[Curves-Metadata]\n"
    "sim_t_event_start =\n"
    "fault_duration =\n"
    "is_field_measurements =\n"
)

_METADATA_WITH_UNFILLED_IMAX = (
    "[Curves-Metadata]\n"
    "sim_t_event_start = 20.0\n"
    "fault_duration = 1.5\n"
    "is_field_measurements = False\n"
    "Wind_Turbine_GEN_MaxInjectedCurrentPu =\n"
)

_CURVES_DICTIONARY = (
    "\n[Curves-Dictionary]\ntime = time\nBusPDR_BUS_ActivePower = BusPDR_BUS_ActivePower\n"
)

_DICT_WITHOUT_METADATA = _CURVES_DICTIONARY.lstrip()


class DummyProducer:
    """Producer reduced to what the curves importer asks of it.

    Parameters
    ----------
    zone : int, optional
        Zone the curves belong to. By default, 3.
    curves_path : Path, optional
        Directory holding the producer curves. By default, None.
    """

    def __init__(self, zone: int = 3, curves_path: Path = None):
        self._zone = zone
        self._curves_path = curves_path
        self.generators = []
        self.is_field_measurements = None
        self.consumption = None

    def get_zone(self) -> int:
        return self._zone

    def get_producer_curves_path(self) -> Path:
        return self._curves_path

    def set_generators(self, generators: list) -> None:
        self.generators = generators

    def set_is_field_measurements(self, is_field_measurements: bool) -> None:
        self.is_field_measurements = is_field_measurements

    def set_consumption(self, consumption: bool) -> None:
        self.consumption = consumption


class DummyConfig:
    """Tool configuration reduced to the options the curves importer reads."""

    def get_value(self, section: str, key: str):
        return "Pmax" if key == "pdr_P" else None

    def has_option(self, section: str, key: str) -> bool:
        return False


@pytest.fixture
def tool_config(monkeypatch) -> DummyConfig:
    """Replaces the tool configuration read while importing the curves."""
    config = DummyConfig()
    monkeypatch.setattr(f"{_IC}.config", config)
    return config


@pytest.fixture
def curves_logs(monkeypatch, caplog):
    """Captures what the curves importer logs."""
    monkeypatch.setattr("dycov.logging.dycov_logging.get_logger", logging.getLogger)
    caplog.set_level(logging.WARNING)
    return caplog


def _write_curves(curves_dir: Path, metadata: str = _FILLED_METADATA) -> Path:
    producer_dir = curves_dir / "Producer"
    producer_dir.mkdir(parents=True)
    (producer_dir / "CurvesFiles.ini").write_text(
        "[Curves-Files]\n"
        f"{_CFG_OC_NAME} = {_CFG_OC_NAME}.csv\n"
        "\n"
        "[Curves-Dictionary]\n"
        "time = time\n"
        "BusPDR_BUS_ActivePower = BusPDR_BUS_ActivePower\n"
        "\n"
        "[Curves-Dictionary-Zone1]\n"
        "\n"
        "[Curves-Dictionary-Zone3]\n"
    )
    (producer_dir / _DICT_NAME).write_text(metadata + _CURVES_DICTIONARY)
    (producer_dir / f"{_CFG_OC_NAME}.csv").write_text(
        "time;BusPDR_BUS_ActivePower\n0.0;1.0\n10.0;1.0\n20.0;0.5\n"
    )
    return producer_dir


def _overwrite_dict(curves_dir: Path, content: str) -> None:
    (curves_dir / "Producer" / _DICT_NAME).write_text(content)


def _make_working_dir(tmp_path: Path) -> Path:
    working_oc_dir = tmp_path / "working"
    working_oc_dir.mkdir()
    return working_oc_dir


# ---------------------------------------------------------------------------
# Reference curves
# ---------------------------------------------------------------------------


def test_obtain_reference_curve_returns_the_declared_event_start(tmp_path, tool_config):
    ref_dir = tmp_path / "ReferenceCurves"
    _write_curves(ref_dir)
    imported_curves = ImportedCurves(DummyProducer())

    start_time, curves_df = imported_curves.obtain_reference_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
    )

    assert start_time == pytest.approx(20.0)
    assert not curves_df.empty
    assert "BusPDR_BUS_ActivePower" in curves_df


def test_obtain_reference_curve_without_files_returns_none(tmp_path, tool_config):
    ref_dir = tmp_path / "ReferenceCurves"
    (ref_dir / "Producer").mkdir(parents=True)
    imported_curves = ImportedCurves(DummyProducer())

    start_time, curves_df = imported_curves.obtain_reference_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
    )

    assert start_time is None
    assert curves_df.empty


def test_obtain_reference_curve_without_curves_file_returns_none(tmp_path, tool_config):
    ref_dir = tmp_path / "ReferenceCurves"
    _write_curves(ref_dir)
    (ref_dir / "Producer" / f"{_CFG_OC_NAME}.csv").unlink()
    imported_curves = ImportedCurves(DummyProducer())

    start_time, curves_df = imported_curves.obtain_reference_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
    )

    assert start_time is None
    assert curves_df.empty


def test_obtain_reference_curve_without_event_start_uses_the_default(tmp_path, tool_config):
    ref_dir = tmp_path / "ReferenceCurves"
    _write_curves(ref_dir, _METADATA_WITHOUT_EVENT_START)
    producer = DummyProducer()
    imported_curves = ImportedCurves(producer)

    start_time, curves_df = imported_curves.obtain_reference_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
    )

    assert start_time == pytest.approx(0.0)
    assert not curves_df.empty
    assert producer.is_field_measurements is False


# ---------------------------------------------------------------------------
# Invalid dictionaries
# ---------------------------------------------------------------------------


def test_obtain_reference_curve_with_an_empty_dict_warns_and_skips(
    tmp_path, tool_config, curves_logs
):
    ref_dir = tmp_path / "ReferenceCurves"
    _write_curves(ref_dir)
    _overwrite_dict(ref_dir, "")
    imported_curves = ImportedCurves(DummyProducer())

    start_time, curves_df = imported_curves.obtain_reference_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
    )

    assert start_time is None
    assert curves_df.empty
    assert any(_DICT_NAME in record.message for record in curves_logs.records)


def test_obtain_reference_curve_without_metadata_section_warns_and_skips(
    tmp_path, tool_config, curves_logs
):
    ref_dir = tmp_path / "ReferenceCurves"
    _write_curves(ref_dir)
    _overwrite_dict(ref_dir, _DICT_WITHOUT_METADATA)
    imported_curves = ImportedCurves(DummyProducer())

    start_time, curves_df = imported_curves.obtain_reference_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
    )

    assert start_time is None
    assert curves_df.empty
    assert any(_DICT_NAME in record.message for record in curves_logs.records)


def test_obtain_simulated_curve_with_an_empty_dict_warns_and_skips(
    tmp_path, tool_config, curves_logs
):
    curves_dir = tmp_path / "ProducerCurves"
    _write_curves(curves_dir)
    _overwrite_dict(curves_dir, "")
    imported_curves = ImportedCurves(DummyProducer(curves_path=curves_dir))

    _, _, simulation_result, curves_df = imported_curves.obtain_simulated_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, None
    )

    assert simulation_result.has_simulated_curves is False
    assert curves_df.empty
    assert any(_DICT_NAME in record.message for record in curves_logs.records)


# ---------------------------------------------------------------------------
# Unfilled metadata
# ---------------------------------------------------------------------------


def test_obtain_reference_curve_with_unfilled_event_start_names_the_dictionary(
    tmp_path, tool_config
):
    """Guards against issue #481, reported as a float conversion of an empty string."""
    ref_dir = tmp_path / "ReferenceCurves"
    _write_curves(ref_dir, _UNFILLED_METADATA)
    imported_curves = ImportedCurves(DummyProducer())

    with pytest.raises(ValueError) as unfilled_error:
        imported_curves.obtain_reference_curve(
            _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
        )

    assert "sim_t_event_start" in str(unfilled_error.value)
    assert _DICT_NAME in str(unfilled_error.value)


def test_obtain_reference_curve_with_unfilled_generator_imax_names_the_dictionary(
    tmp_path, tool_config
):
    """Guards against issue #481: the maximum injected current fails the same way."""
    ref_dir = tmp_path / "ReferenceCurves"
    _write_curves(ref_dir, _METADATA_WITH_UNFILLED_IMAX)
    imported_curves = ImportedCurves(DummyProducer())

    with pytest.raises(ValueError) as unfilled_error:
        imported_curves.obtain_reference_curve(
            _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
        )

    assert "Wind_Turbine_GEN_MaxInjectedCurrentPu" in str(unfilled_error.value)
    assert _DICT_NAME in str(unfilled_error.value)


def test_obtain_simulated_curve_with_unfilled_event_start_names_the_dictionary(
    tmp_path, tool_config
):
    """Guards against issue #481: user curves are read through the same metadata."""
    curves_dir = tmp_path / "ProducerCurves"
    _write_curves(curves_dir, _UNFILLED_METADATA)
    imported_curves = ImportedCurves(DummyProducer(curves_path=curves_dir))

    with pytest.raises(ValueError) as unfilled_error:
        imported_curves.obtain_simulated_curve(
            _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, None
        )

    assert "sim_t_event_start" in str(unfilled_error.value)
    assert _DICT_NAME in str(unfilled_error.value)
