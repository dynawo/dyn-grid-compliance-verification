#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path


def test_fix_after_windows():
    from dycov.curves.manager import _fix_after_windows

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
    from dycov.curves.manager import CurvesManager

    cm = CurvesManager.__new__(CurvesManager)
    cm._missed_curves = {"calculated": ["a"], "reference": []}

    assert cm.get_missed_curves("calculated") == ["a"]


def test_get_curves_empty():
    import pandas as pd

    from dycov.curves.manager import CurvesManager

    cm = CurvesManager.__new__(CurvesManager)
    cm._curves = {"calculated": pd.DataFrame()}

    res = cm.get_curves("calculated")

    assert res.empty


def test_get_exclusion_windows():
    from dycov.curves.manager import CurvesManager

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


def test_wrappers(monkeypatch):
    from dycov.curves.manager import CurvesManager

    class DummyGen:
        def get_voltage_dip(self): return 0.5
        def get_generators_imax(self): return {"g": 1}

    cm = CurvesManager.__new__(CurvesManager)
    cm._producer_curves_generator = DummyGen()

    assert cm.get_voltage_dip() == 0.5
    assert cm.get_generators_imax()["g"] == 1


def test_has_required_curves_all(monkeypatch, tmp_path):
    from types import SimpleNamespace

    import pandas as pd

    from dycov.curves.manager import CurvesManager
    from dycov.model.parameters import CurvesAvailability

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
    )

    cm._working_dir = tmp_path

    tmp_path.mkdir(parents=True, exist_ok=True)

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
