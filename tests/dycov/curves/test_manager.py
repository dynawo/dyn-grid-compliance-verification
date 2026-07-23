#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from types import SimpleNamespace

import pandas as pd

from dycov.curves.manager import CurvesManager, _fix_after_windows
from dycov.model.parameters import CurvesAvailability


def test_fix_after_windows():
    calc = {
        "validate": {"after": (0, 10)},
        "sigpro": {"after": (0, 8)},
    }
    ref = {
        "validate": {"after": (0, 5)},
        "sigpro": {"after": (0, 6)},
    }

    c, r = _fix_after_windows(calc, ref)

    assert c["validate"]["after"][1] == 5
    assert c["sigpro"]["after"][1] == 6


def test_get_missed_curves():
    cm = CurvesManager.__new__(CurvesManager)
    cm._missed_curves = {"calculated": ["a"], "reference": []}

    assert cm.get_missed_curves("calculated") == ["a"]


def test_get_curves_empty():
    cm = CurvesManager.__new__(CurvesManager)
    cm._curves = {"calculated": pd.DataFrame()}

    res = cm.get_curves("calculated")

    assert res.empty


def test_get_exclusion_windows():
    cm = CurvesManager.__new__(CurvesManager)
    cm._windows = {
        "calculated": {
            "validate": {
                "before": (0, 1),
                "during": (1, 2),
                "after": (2, 3),
            }
        }
    }

    res = cm.get_exclusion_windows()

    assert res.event_start == 1


def test_wrappers():
    cm = CurvesManager.__new__(CurvesManager)
    cm._producer_curves_generator = SimpleNamespace(
        get_voltage_dip=lambda: 0.5,
        get_generators_imax=lambda: {"g": 1},
    )

    assert cm.get_voltage_dip() == 0.5
    assert cm.get_generators_imax()["g"] == 1


def test_has_required_curves_all(monkeypatch, tmp_path):
    cm = CurvesManager.__new__(CurvesManager)
    cm._curves = {
        "calculated": pd.DataFrame({"a": [1]}),
        "reference": pd.DataFrame({"a": [1]}),
    }
    cm._missed_curves = {"calculated": [], "reference": []}
    cm.get_curves = lambda x: cm._curves[x]
    cm._producer = SimpleNamespace(
        is_dynawo_model=lambda: False,
        has_reference_curves_path=lambda: True,
        get_zone=lambda: 0,
    )
    cm._working_dir = tmp_path
    dummy_sim = SimpleNamespace(
        success=True,
        time_exceeds=False,
        error=None,
        appicable=True,
        has_simulated_curves=True,
    )
    monkeypatch.setattr(
        cm,
        "_CurvesManager__obtain_curve",
        lambda *a, **k: (tmp_path, tmp_path, {"start_time": 1}, dummy_sim),
    )

    res = cm.has_required_curves(["a"], "bm", "oc")

    assert res.availability == CurvesAvailability.ALL


def _manager_with_curves(zone: int) -> CurvesManager:
    cm = CurvesManager.__new__(CurvesManager)
    cm._producer = SimpleNamespace(get_zone=lambda: zone)
    cm._curves = {
        "calculated": pd.DataFrame(
            {
                "time": [0.0, 1.0],
                "BusPDR_BUS_Voltage": [1.0, 0.9],
                "Wind_Turbine_GEN_InjectedActiveCurrent": [0.5, 0.6],
            }
        ),
        "reference": pd.DataFrame(
            {
                "time": [0.0, 1.0],
                "BusPDR_BUS_Voltage": [1.0, 0.95],
            }
        ),
    }
    cm.get_curves = lambda x: cm._curves[x]
    return cm


def test_save_curves_zone1_renames_bus_columns(tmp_path):
    cm = _manager_with_curves(zone=1)

    cm._CurvesManager__save_curves(tmp_path)

    calculated = pd.read_csv(tmp_path / "curves_calculated.csv", sep=";")
    reference = pd.read_csv(tmp_path / "curves_reference.csv", sep=";")
    assert "InternalNode1_BUS_Voltage" in calculated.columns
    assert "BusPDR_BUS_Voltage" not in calculated.columns
    assert "Wind_Turbine_GEN_InjectedActiveCurrent" in calculated.columns
    assert "InternalNode1_BUS_Voltage" in reference.columns
    assert list(cm._curves["calculated"].columns)[1] == "BusPDR_BUS_Voltage"


def test_save_curves_zone3_keeps_bus_columns(tmp_path):
    cm = _manager_with_curves(zone=3)

    cm._CurvesManager__save_curves(tmp_path)

    calculated = pd.read_csv(tmp_path / "curves_calculated.csv", sep=";")
    assert "BusPDR_BUS_Voltage" in calculated.columns
    assert "InternalNode1_BUS_Voltage" not in calculated.columns
