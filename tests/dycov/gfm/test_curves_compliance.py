#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import numpy as np
import pandas as pd
import pytest

from dycov.gfm.verification import curves_compliance
from dycov.model.compliance import Compliance

_TEST = "PCS_RTE-IGFM1.S_VolAngStep2.OC2"
_EVENT_IN_CURVES = 1.0
_ENVELOPE_TIME = np.linspace(0.0, 5.0, 2501)
_IDEAL = 0.5 + 0.3 * np.exp(-_ENVELOPE_TIME / 0.2)

_CURVES_FILES = """[Curves-Dictionary]
time = t

[Curves-Dictionary-Zone1]
InternalNode1_BUS_ActiveCurrent = ip
InternalNode1_BUS_ReactiveCurrent = iq
InternalNode1_BUS_Voltage = u

[Curves-Dictionary-Zone3]
"""


def _write_curves(curves_path, ip, with_iq=True):
    curves_path.mkdir()
    (curves_path / "CurvesFiles.ini").write_text(_CURVES_FILES)
    time = np.arange(0.0, 5.0, 0.001)
    data = {"t": time + _EVENT_IN_CURVES, "ip": ip(time), "u": np.ones_like(time)}
    if with_iq:
        data["iq"] = np.zeros_like(time)
    pd.DataFrame(data).to_csv(curves_path / f"{_TEST}.csv", sep=";", index=False)
    (curves_path / f"{_TEST}.dict").write_text(
        f"[Curves-Metadata]\nsim_t_event_start = {_EVENT_IN_CURVES}\n\n[Curves-Dictionary]\n"
    )


def _check(tmp_path, lower=_IDEAL - 0.05, upper=_IDEAL + 0.05):
    working_path = tmp_path / "working"
    working_path.mkdir()
    return curves_compliance.check(
        tmp_path / "curves",
        working_path,
        _TEST,
        "Ip",
        _ENVELOPE_TIME,
        0.0,
        0.0,
        lower,
        upper,
    )


def _ideal(time):
    return 0.5 + 0.3 * np.exp(-time / 0.2)


def test_curve_inside_its_envelope_without_oscillation_is_compliant(tmp_path):
    _write_curves(tmp_path / "curves", _ideal)

    result = _check(tmp_path)

    assert result.compliance == Compliance.Compliant
    assert result.envelope.within
    assert result.envelope.t_from == pytest.approx(0.0)
    assert result.modes == []
    # The 30 Hz filter rounds off the start of the decay
    assert np.nanmax(np.abs(result.signal - _IDEAL)) < 0.02


def test_envelope_bounds_may_come_in_either_order(tmp_path):
    _write_curves(tmp_path / "curves", _ideal)

    result = _check(tmp_path, lower=_IDEAL + 0.05, upper=_IDEAL - 0.05)

    assert result.compliance == Compliance.Compliant


def test_curve_leaving_its_envelope_is_not_compliant(tmp_path):
    _write_curves(
        tmp_path / "curves", lambda time: _ideal(time) + np.where((time > 1) & (time < 2), 0.2, 0)
    )

    result = _check(tmp_path)

    assert result.compliance == Compliance.NonCompliant
    assert not result.envelope.within
    assert result.envelope.max_excess == pytest.approx(0.15, abs=0.01)


def test_lightly_damped_oscillation_inside_the_envelope_is_not_compliant(tmp_path):
    def oscillating(time):
        return _ideal(time) + 0.03 * np.exp(-0.1 * 2 * np.pi * 2 * time) * np.sin(
            2 * np.pi * 2 * time
        )

    _write_curves(tmp_path / "curves", oscillating)

    result = _check(tmp_path)

    assert result.compliance == Compliance.NonCompliant
    assert result.envelope.within
    assert [(mode.curve, round(mode.damping_ratio, 1)) for mode in result.modes] == [("Ip", 0.1)]


def test_curves_without_the_reactive_current_are_missing(tmp_path):
    _write_curves(tmp_path / "curves", _ideal, with_iq=False)

    assert _check(tmp_path).compliance == Compliance.WithoutProducerCurves


def test_test_without_curves_is_missing(tmp_path):
    (tmp_path / "curves").mkdir()

    assert _check(tmp_path).compliance == Compliance.WithoutProducerCurves


def test_pre_event_value_held_during_the_admitted_delay_stays_inside():
    # A phase-jump envelope: the response may hold its pre-event value P0 during the first
    # 10 ms, while the time tunnel narrows the envelope by 0.0034 pu then
    time = np.linspace(0.0, 0.1, 61)
    lower = np.where(time < 0.01, 0.5034, 0.65)
    upper = np.full_like(time, 0.947)
    signal = np.where(time < 0.01, 0.5, 0.7)

    assert curves_compliance._check_envelope(time, signal, lower, upper).within
