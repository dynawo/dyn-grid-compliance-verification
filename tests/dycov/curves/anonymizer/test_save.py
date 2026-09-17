#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from __future__ import annotations

import numpy as np
import pandas as pd

from dycov.curves.anonymizer.save import save_curve


def test_save_curve_writes_time_first_with_the_requested_precision(tmp_path):
    df = pd.DataFrame({"signal1": [1.5, 2.5], "time": [0.0, 0.25]})
    path = tmp_path / "curve.csv"

    save_curve(df, path, precision=3)

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == "time;signal1"
    assert lines[1].startswith("0.000;")
    assert lines[2].startswith("0.250;")


def test_save_curve_writes_the_time_with_microsecond_precision(tmp_path):
    df = pd.DataFrame({"time": [0.0, 0.0005], "signal1": [1.0, 1.0]})
    path = tmp_path / "curve.csv"

    save_curve(df, path)

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert lines[1].startswith("0.000000;")
    assert lines[2].startswith("0.000500;")


def test_save_curve_does_not_modify_the_input(tmp_path):
    df = pd.DataFrame({"time": [0.0, 1.0], "signal1": [1.0, 2.0]})

    save_curve(df, tmp_path / "curve.csv")

    assert df["time"].dtype == np.float64
