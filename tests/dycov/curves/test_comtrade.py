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


def test_comtrade():
    path = _get_resources_path() / "tmp"
    shutil.copytree(_get_resources_path(), path, dirs_exist_ok=True)

    try:
        importer = CurvesImporter(path, "Wind_farm_comtrade_example")
        df_comtrade_curve = importer.get_curves_dataframe(0)

        assert not df_comtrade_curve.empty
        assert "time" in df_comtrade_curve
        assert df_comtrade_curve["time"].iloc[0] == 0.0
        assert df_comtrade_curve["time"].iloc[-1] == 7.5
        assert "Vac_a" in df_comtrade_curve
        assert "Ineg_q" in df_comtrade_curve
    finally:
        shutil.rmtree(path)
