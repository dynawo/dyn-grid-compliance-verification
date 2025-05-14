#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import shutil
from pathlib import Path

from dycov.curves.importer.importer import CurvesImporter


def _get_resources_path():
    return (Path(__file__).resolve().parent) / "resources"


def test_csv():

    path = _get_resources_path() / "tmp"
    shutil.copytree(_get_resources_path(), path, dirs_exist_ok=True)

    try:
        importer = CurvesImporter(path, "curves_final")
        df_csv_curve = importer.get_curves_dataframe(0)

        assert not df_csv_curve.empty
        assert "time" in df_csv_curve
        assert df_csv_curve["time"].iloc[0] == 0.0
        assert df_csv_curve["time"].iloc[-1] == 100.0
        assert "BusPDR_bus_terminal_V" in df_csv_curve
        assert "Synch_Gen_generator_UStatorPu_value" in df_csv_curve
    finally:
        shutil.rmtree(path)
