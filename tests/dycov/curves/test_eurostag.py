#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import math
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from dycov.curves.importer.importer import CurvesImporter


def _get_resources_path():
    return (Path(__file__).resolve().parent) / "resources"


def test_eurostag():
    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        shutil.copytree(_get_resources_path(), path, dirs_exist_ok=True)

        importer = CurvesImporter(path, "fiche8")
        df_eurostag_curve = importer.get_curves_dataframe(0)

        assert not df_eurostag_curve.empty
        assert "time" in df_eurostag_curve
        assert df_eurostag_curve["time"].iloc[0] == 0.0
        assert math.isclose(df_eurostag_curve["time"].iloc[-1], 9.882547, rel_tol=1e-5)
        assert "bus_PDR_V" in df_eurostag_curve
        assert "generator_Omega" in df_eurostag_curve
