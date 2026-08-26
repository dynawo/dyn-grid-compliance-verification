#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from dycov.curves.importer.curves import ImportedCurves

_IC = "dycov.curves.importer.curves"

_PCS = "PCSX"
_BM = "Bm"
_OC = "Oc"
_CFG_OC_NAME = f"{_PCS}.{_BM}.{_OC}"


def _make_producer(zone: int = 3) -> MagicMock:
    producer = MagicMock()
    producer.get_zone.return_value = zone
    return producer


def _make_config_mock() -> MagicMock:
    config = MagicMock()
    config.get_value.side_effect = lambda section, key: {"pdr_P": "Pmax"}.get(key)
    config.has_option.return_value = False
    return config


def _write_reference_curves(ref_dir: Path) -> None:
    producer_dir = ref_dir / "Producer"
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
    (producer_dir / f"{_CFG_OC_NAME}.dict").write_text(
        "[Curves-Metadata]\n"
        "sim_t_event_start = 20.0\n"
        "fault_duration = 1.5\n"
        "is_field_measurements = False\n"
        "\n"
        "[Curves-Dictionary]\n"
        "time = time\n"
        "BusPDR_BUS_ActivePower = BusPDR_BUS_ActivePower\n"
    )
    (producer_dir / f"{_CFG_OC_NAME}.csv").write_text(
        "time;BusPDR_BUS_ActivePower\n0.0;1.0\n10.0;1.0\n20.0;0.5\n"
    )


class TestObtainReferenceCurve:
    @patch(f"{_IC}.config", new_callable=_make_config_mock)
    def test_valid_reference_returns_dict_event_start_time(self, mock_config, tmp_path):
        ref_dir = tmp_path / "ReferenceCurves"
        _write_reference_curves(ref_dir)
        working_oc_dir = tmp_path / "working"
        working_oc_dir.mkdir()
        imported_curves = ImportedCurves(_make_producer())

        start_time, curves_df = imported_curves.obtain_reference_curve(
            working_oc_dir, "Producer", _PCS, _BM, _OC, ref_dir
        )

        assert start_time == 20.0
        assert not curves_df.empty
        assert "BusPDR_BUS_ActivePower" in curves_df

    @patch(f"{_IC}.config", new_callable=_make_config_mock)
    def test_missing_reference_returns_none(self, mock_config, tmp_path):
        ref_dir = tmp_path / "ReferenceCurves"
        (ref_dir / "Producer").mkdir(parents=True)
        working_oc_dir = tmp_path / "working"
        working_oc_dir.mkdir()
        imported_curves = ImportedCurves(_make_producer())

        start_time, curves_df = imported_curves.obtain_reference_curve(
            working_oc_dir, "Producer", _PCS, _BM, _OC, ref_dir
        )

        assert start_time is None
        assert curves_df.empty

    @patch(f"{_IC}.config", new_callable=_make_config_mock)
    def test_dict_without_curves_file_returns_none(self, mock_config, tmp_path):
        ref_dir = tmp_path / "ReferenceCurves"
        _write_reference_curves(ref_dir)
        (ref_dir / "Producer" / f"{_CFG_OC_NAME}.csv").unlink()
        working_oc_dir = tmp_path / "working"
        working_oc_dir.mkdir()
        imported_curves = ImportedCurves(_make_producer())

        start_time, curves_df = imported_curves.obtain_reference_curve(
            working_oc_dir, "Producer", _PCS, _BM, _OC, ref_dir
        )

        assert start_time is None
        assert curves_df.empty


_DICT_WITHOUT_METADATA = (
    "[Curves-Dictionary]\ntime = time\nBusPDR_BUS_ActivePower = BusPDR_BUS_ActivePower\n"
)


def _overwrite_dict(ref_dir: Path, content: str) -> None:
    (ref_dir / "Producer" / f"{_CFG_OC_NAME}.dict").write_text(content)


def _patch_dycov_logging(monkeypatch):
    monkeypatch.setattr(
        "dycov.logging.dycov_logging.get_logger",
        logging.getLogger,
        raising=True,
    )


class TestInvalidDict:
    @patch(f"{_IC}.config", new_callable=_make_config_mock)
    def test_empty_dict_skips_reference_with_warning(
        self, mock_config, tmp_path, monkeypatch, caplog
    ):
        _patch_dycov_logging(monkeypatch)
        ref_dir = tmp_path / "ReferenceCurves"
        _write_reference_curves(ref_dir)
        _overwrite_dict(ref_dir, "")
        working_oc_dir = tmp_path / "working"
        working_oc_dir.mkdir()
        imported_curves = ImportedCurves(_make_producer())

        caplog.set_level(logging.WARNING)
        start_time, curves_df = imported_curves.obtain_reference_curve(
            working_oc_dir, "Producer", _PCS, _BM, _OC, ref_dir
        )

        assert start_time is None
        assert curves_df.empty
        assert any(f"'{_CFG_OC_NAME}.dict'" in record.message for record in caplog.records)

    @patch(f"{_IC}.config", new_callable=_make_config_mock)
    def test_dict_without_metadata_skips_reference_with_warning(
        self, mock_config, tmp_path, monkeypatch, caplog
    ):
        _patch_dycov_logging(monkeypatch)
        ref_dir = tmp_path / "ReferenceCurves"
        _write_reference_curves(ref_dir)
        _overwrite_dict(ref_dir, _DICT_WITHOUT_METADATA)
        working_oc_dir = tmp_path / "working"
        working_oc_dir.mkdir()
        imported_curves = ImportedCurves(_make_producer())

        caplog.set_level(logging.WARNING)
        start_time, curves_df = imported_curves.obtain_reference_curve(
            working_oc_dir, "Producer", _PCS, _BM, _OC, ref_dir
        )

        assert start_time is None
        assert curves_df.empty
        assert any(f"'{_CFG_OC_NAME}.dict'" in record.message for record in caplog.records)

    @patch(f"{_IC}.config", new_callable=_make_config_mock)
    def test_empty_dict_skips_simulated_curve_with_warning(
        self, mock_config, tmp_path, monkeypatch, caplog
    ):
        _patch_dycov_logging(monkeypatch)
        curves_dir = tmp_path / "ProducerCurves"
        _write_reference_curves(curves_dir)
        _overwrite_dict(curves_dir, "")
        working_oc_dir = tmp_path / "working"
        working_oc_dir.mkdir()
        producer = _make_producer()
        producer.get_producer_curves_path.return_value = curves_dir
        imported_curves = ImportedCurves(producer)

        caplog.set_level(logging.WARNING)
        _, _, simulation_result, curves_df = imported_curves.obtain_simulated_curve(
            working_oc_dir, "Producer", _PCS, _BM, _OC, None
        )

        assert simulation_result.has_simulated_curves is False
        assert curves_df.empty
        assert any(f"'{_CFG_OC_NAME}.dict'" in record.message for record in caplog.records)
