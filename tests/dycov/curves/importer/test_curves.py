#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#
"""Import of producer curves and of the metadata that describes them."""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
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
    "sim_t_event_start = 10.0\n"
    "fault_duration = 1.5\n"
    "is_field_measurements = False\n"
)

_METADATA_WITHOUT_EVENT_START = "[Curves-Metadata]\nfrequency_sampling = 15\n"

_UNFILLED_METADATA = (
    "[Curves-Metadata]\nsim_t_event_start =\nfault_duration =\nis_field_measurements =\n"
)

_METADATA_WITH_UNFILLED_IMAX = (
    "[Curves-Metadata]\n"
    "sim_t_event_start = 10.0\n"
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


def _csv_text(columns: str, first: str, rest: str) -> str:
    """Curves sampled every second over 20 s: *first* at their start, *rest* after it."""
    return f"time;{columns}\n0.0;{first}\n" + "".join(f"{t}.0;{rest}\n" for t in range(1, 21))


def _ends(curve) -> list:
    return [curve.iloc[0], curve.iloc[-1]]


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
        _csv_text("BusPDR_BUS_ActivePower", "1.0", "0.5")
    )
    return producer_dir


def _overwrite_dict(curves_dir: Path, content: str) -> None:
    (curves_dir / "Producer" / _DICT_NAME).write_text(content)


def _write_frequency_curves(curves_dir: Path, frequencies: dict) -> None:
    _write_curves(curves_dir)
    names = "".join(f"{name} = {name}\n" for name in frequencies)
    _overwrite_dict(curves_dir, f"{_FILLED_METADATA}\n[Curves-Dictionary]\ntime = time\n{names}")
    values = ";".join(str(value) for value in frequencies.values())
    (curves_dir / "Producer" / f"{_CFG_OC_NAME}.csv").write_text(
        _csv_text(";".join(frequencies), values, values)
    )


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

    assert start_time == pytest.approx(10.0)
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
# Network frequency
# ---------------------------------------------------------------------------


def test_reference_curves_name_the_network_frequency_after_the_unit_frequency(
    tmp_path, tool_config
):
    """#489: a dictionary that only declares the frequency each unit measures, as the one the
    tool scaffolds for a synchronous machine does, still carries the curve fig_WRef reads."""
    ref_dir = tmp_path / "ReferenceCurves"
    _write_frequency_curves(ref_dir, {"SM_GEN_NetworkFrequencyPu": 0.99})
    imported_curves = ImportedCurves(DummyProducer())

    _, curves_df = imported_curves.obtain_reference_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
    )

    assert _ends(curves_df["NetworkFrequencyPu"]) == pytest.approx([0.99, 0.99])


def test_producer_curves_name_the_network_frequency_after_the_unit_frequency(
    tmp_path, tool_config
):
    curves_dir = tmp_path / "ProducerCurves"
    _write_frequency_curves(curves_dir, {"SM_GEN_NetworkFrequencyPu": 0.99})
    imported_curves = ImportedCurves(DummyProducer(curves_path=curves_dir))

    _, _, _, curves_df = imported_curves.obtain_simulated_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, None
    )

    assert _ends(curves_df["NetworkFrequencyPu"]) == pytest.approx([0.99, 0.99])


@pytest.mark.parametrize("zone", [1, 3])
def test_reference_curves_read_the_names_the_generator_curves_had_before_the_nodes(
    tmp_path, tool_config, zone
):
    ref_dir = tmp_path / "ReferenceCurves"
    _write_curves(ref_dir)
    _overwrite_dict(
        ref_dir,
        f"{_FILLED_METADATA}\n[Curves-Dictionary]\ntime = time\n"
        "WT_GEN_VoltageInjTerminal = U2\nWT_GEN_ActiveCurrentInjTerminal = Ip2\n",
    )
    (ref_dir / "Producer" / f"{_CFG_OC_NAME}.csv").write_text(
        _csv_text("U2;Ip2", "1.0;0.8", "0.9;0.7")
    )
    imported_curves = ImportedCurves(DummyProducer(zone=zone))

    _, curves_df = imported_curves.obtain_reference_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
    )

    assert _ends(curves_df["WT_GEN_VoltageNode2"]) == pytest.approx([1.0, 0.9])
    assert _ends(curves_df["WT_GEN_ActiveCurrentNode2"]) == pytest.approx([0.8, 0.7])


def test_a_file_whose_columns_carry_the_names_before_the_nodes_serves_the_current_ones(
    tmp_path, tool_config
):
    ref_dir = tmp_path / "ReferenceCurves"
    _write_curves(ref_dir)
    _overwrite_dict(
        ref_dir,
        f"{_FILLED_METADATA}\n[Curves-Dictionary]\ntime = time\n"
        "WT_GEN_VoltageNode2 = WT_GEN_VoltageNode2\n"
        "WT_GEN_ActiveCurrentNode2 = WT_GEN_ActiveCurrentNode2\n",
    )
    (ref_dir / "Producer" / f"{_CFG_OC_NAME}.csv").write_text(
        _csv_text(
            "WT_GEN_VoltageInjTerminal;WT_GEN_ActiveCurrentInjTerminal;WT_GEN_ActiveCurrentNode2",
            "1.0;0.8;0.6",
            "0.9;0.7;0.5",
        )
    )
    imported_curves = ImportedCurves(DummyProducer(zone=1))

    _, curves_df = imported_curves.obtain_reference_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
    )

    assert _ends(curves_df["WT_GEN_VoltageNode2"]) == pytest.approx([1.0, 0.9])
    assert _ends(curves_df["WT_GEN_ActiveCurrentNode2"]) == pytest.approx([0.6, 0.5])


def test_imported_curves_keep_the_network_frequency_they_declare(tmp_path, tool_config):
    ref_dir = tmp_path / "ReferenceCurves"
    _write_frequency_curves(
        ref_dir, {"NetworkFrequencyPu": 1.0, "SM_GEN_NetworkFrequencyPu": 0.99}
    )
    imported_curves = ImportedCurves(DummyProducer())

    _, curves_df = imported_curves.obtain_reference_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
    )

    assert _ends(curves_df["NetworkFrequencyPu"]) == pytest.approx([1.0, 1.0])


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
# Event outside the curves
# ---------------------------------------------------------------------------


def _metadata_with_the_event(event_start: float, fault_duration: float = 0.0) -> str:
    return (
        "[Curves-Metadata]\n"
        f"sim_t_event_start = {event_start}\n"
        f"fault_duration = {fault_duration}\n"
        "is_field_measurements = False\n"
    )


@pytest.mark.parametrize(
    "event_start, fault_duration", [(30.0, 0.0), (20.0, 0.0), (19.0, 1.5), (18.95, 0.0)]
)
def test_reference_curves_that_end_too_soon_after_their_event_are_refused(
    tmp_path, tool_config, curves_logs, event_start, fault_duration
):
    """#862: the windows of the comparison ran past the end of the curves and the test ended
    in a traceback, for an event at or after their end, a fault cleared after it, or too short
    a time after the event for the window the comparison reads there."""
    ref_dir = tmp_path / "ReferenceCurves"
    _write_curves(ref_dir, _metadata_with_the_event(event_start, fault_duration))
    imported_curves = ImportedCurves(DummyProducer())

    start_time, curves_df = imported_curves.obtain_reference_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
    )

    assert start_time is None
    assert curves_df.empty
    [warning] = [record.message for record in curves_logs.records]
    assert f"The reference curves of '{_DICT_NAME}'" in warning
    assert f"event at {event_start:g} s, but end at 20 s" in warning


def test_producer_curves_that_end_before_their_event_count_as_missing(
    tmp_path, tool_config, curves_logs
):
    curves_dir = tmp_path / "ProducerCurves"
    _write_curves(curves_dir, _metadata_with_the_event(30.0))
    imported_curves = ImportedCurves(DummyProducer(curves_path=curves_dir))

    _, _, simulation_result, curves_df = imported_curves.obtain_simulated_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, None
    )

    assert simulation_result.has_simulated_curves is False
    assert curves_df.empty
    [warning] = [record.message for record in curves_logs.records]
    assert f"The producer curves of '{_DICT_NAME}'" in warning


@pytest.mark.parametrize(
    "event_start, fault_duration", [(10.0, 1.5), (18.9, 0.0), (10.0, 9999.0), (10.0, 20.0)]
)
def test_curves_that_run_past_their_event_are_kept(
    tmp_path, tool_config, curves_logs, event_start, fault_duration
):
    """A fault that lasts as long as the curves, or longer, is a permanent one, which ends with
    them."""
    ref_dir = tmp_path / "ReferenceCurves"
    _write_curves(ref_dir, _metadata_with_the_event(event_start, fault_duration))
    imported_curves = ImportedCurves(DummyProducer())

    start_time, curves_df = imported_curves.obtain_reference_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
    )

    assert start_time == pytest.approx(event_start)
    assert not curves_df.empty
    assert not curves_logs.records


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


class _EventConfig(DummyConfig):
    """The options of the event of one test, as the configuration serves them."""

    def __init__(self, connect_event_to: str):
        self._connect_event_to = connect_event_to

    def get_value(self, section: str, key: str):
        if key == "connect_event_to":
            return self._connect_event_to
        if key == "setpoint_step_value":
            return "step"
        return super().get_value(section, key)

    def has_option(self, section: str, key: str) -> bool:
        return key == "setpoint_step_value"


@pytest.mark.parametrize(
    "connect_event_to, scaled",
    [
        ("VoltageSetpointPu", False),
        ("NetworkFrequencyPu", False),
        ("ActivePowerSetpointPu", True),
        ("ReactivePowerSetpointPu", True),
    ],
)
def test_the_step_of_imported_curves_is_in_the_base_the_curves_are_compared_in(
    monkeypatch, connect_event_to, scaled
):
    monkeypatch.setattr(f"{_IC}.config", _EventConfig(connect_event_to))
    producer = DummyProducer()
    producer.s_nom = 4.0
    imported_curves = ImportedCurves(producer)
    monkeypatch.setattr(imported_curves, "obtain_value", lambda definition, origin=None: 0.01)

    event = imported_curves._ImportedCurves__process_event_parameters(_PCS, _BM, _OC, 20.0, 0.0)

    assert event["connect_to"] == connect_event_to
    assert event["step_value"] == pytest.approx(0.01 * 100.0 / 4.0 if scaled else 0.01)


# ---------------------------------------------------------------------------
# Curves given as abc waveforms
# ---------------------------------------------------------------------------


def _write_abc_voltage_curves(curves_dir: Path) -> None:
    """A balanced voltage given as its three phases, sampled at 1 kHz."""
    _write_curves(curves_dir)
    _overwrite_dict(
        curves_dir,
        f"{_metadata_with_the_event(0.1)}\n[Curves-Dictionary]\ntime = time\n"
        "BusPDR_BUS_Voltage_a = Va\nBusPDR_BUS_Voltage_b = Vb\nBusPDR_BUS_Voltage_c = Vc\n",
    )
    time = np.arange(0.0, 0.5, 1e-3)
    phases = {
        name: np.sqrt(2) * np.cos(2 * np.pi * 50 * time + shift)
        for name, shift in (("Va", 0.0), ("Vb", -2 * np.pi / 3), ("Vc", 2 * np.pi / 3))
    }
    pd.DataFrame({"time": time, **phases}).to_csv(
        curves_dir / "Producer" / f"{_CFG_OC_NAME}.csv", sep=";", index=False
    )


def _is_one_rms_voltage(curves_df) -> bool:
    return list(curves_df.columns) == ["time", "BusPDR_BUS_Voltage"] and bool(
        np.isfinite(curves_df["BusPDR_BUS_Voltage"]).all()
    )


def test_reference_curves_given_as_abc_waveforms_are_imported_as_their_rms_value(
    tmp_path, tool_config
):
    ref_dir = tmp_path / "ReferenceCurves"
    _write_abc_voltage_curves(ref_dir)
    imported_curves = ImportedCurves(DummyProducer())

    _, curves_df = imported_curves.obtain_reference_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, ref_dir
    )

    assert _is_one_rms_voltage(curves_df)


def test_producer_curves_given_as_abc_waveforms_are_imported_as_their_rms_value(
    tmp_path, tool_config
):
    curves_dir = tmp_path / "ProducerCurves"
    _write_abc_voltage_curves(curves_dir)
    imported_curves = ImportedCurves(DummyProducer(curves_path=curves_dir))

    _, _, _, curves_df = imported_curves.obtain_simulated_curve(
        _make_working_dir(tmp_path), "Producer", _PCS, _BM, _OC, None
    )

    assert _is_one_rms_voltage(curves_df)
