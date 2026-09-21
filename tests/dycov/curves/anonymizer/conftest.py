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

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def create_flat_csv_and_log(curves_dir: Path, name="curve_flat"):
    t = np.linspace(0.0, 5.0, 6)
    df = pd.DataFrame({"time": t, "signal1": np.ones_like(t)})
    csv = curves_dir / f"{name}.csv"
    log = curves_dir / f"{name}.log"

    df.to_csv(csv, sep=";", index=False)
    log.write_text(
        "sim_t_event_start=1.0\nfault_duration=2.0\nfrequency_sampling=50.0\n",
        encoding="utf-8",
    )
    return csv


def create_nonflat_csv_and_log(curves_dir: Path, name="curve_nf"):
    t = np.linspace(0.0, 5.0, 256)
    signal = 1.0 + 0.05 * np.sin(2 * np.pi * t / 5.0)
    df = pd.DataFrame({"time": t, "signal1": signal})

    csv = curves_dir / f"{name}.csv"
    log = curves_dir / f"{name}.log"

    df.to_csv(csv, sep=";", index=False)
    log.write_text(
        "sim_t_event_start=1.0\nfault_duration=2.0\nfrequency_sampling=50.0\n",
        encoding="utf-8",
    )
    return csv


@pytest.fixture()
def tmp_dirs(tmp_path: Path):
    curves = tmp_path / "curves"
    out = tmp_path / "out"
    curves.mkdir()
    out.mkdir()
    return curves, out
