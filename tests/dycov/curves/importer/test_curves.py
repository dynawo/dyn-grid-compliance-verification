#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#
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
