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

from dycov.sigpro.sigpro import lowpass_filter


def _make_test_signal():
    """
    Creates a 1-second signal sampled densely enough,
    composed of a low-frequency component (5 Hz) and
    a high-frequency one (200 Hz) to test the filtering effect.
    """
    t = np.linspace(0, 1, 2000)  # 2 kHz sampling
    y = np.sin(2 * np.pi * 5 * t) + 0.3 * np.sin(2 * np.pi * 200 * t)
    return t, y


def _fs_from_t(t):
    """Compute sampling frequency from time grid."""
    return 1.0 / np.mean(np.diff(t))


# ------------------------------------------------------------
#  Test 1 — Critically Damped Filter
# ------------------------------------------------------------
def test_lowpass_filter_critdamped():
    t, y = _make_test_signal()
    fs = _fs_from_t(t)

    y_f = lowpass_filter(y, fc=20, fs=fs, filter="critdamped")

    # Output sanity
    assert len(y_f) == len(y)
    assert np.all(np.isfinite(y_f))

    # High-frequency content must be reduced
    assert y_f.std() < y.std()


# ------------------------------------------------------------
#  Test 2 — Bessel Filter
# ------------------------------------------------------------
def test_lowpass_filter_bessel():
    t, y = _make_test_signal()
    fs = _fs_from_t(t)

    y_f = lowpass_filter(y, fc=20, fs=fs, filter="bessel")

    assert len(y_f) == len(y)
    assert np.all(np.isfinite(y_f))
    assert y_f.std() < y.std()


# ------------------------------------------------------------
#  Test 3 — Butterworth Filter
# ------------------------------------------------------------
def test_lowpass_filter_butter():
    t, y = _make_test_signal()
    fs = _fs_from_t(t)

    y_f = lowpass_filter(y, fc=20, fs=fs, filter="butter")

    assert len(y_f) == len(y)
    assert np.all(np.isfinite(y_f))
    assert y_f.std() < y.std()


# ------------------------------------------------------------
#  Test 4 — Chebyshev I Filter
# ------------------------------------------------------------
def test_lowpass_filter_cheby1():
    t, y = _make_test_signal()
    fs = _fs_from_t(t)

    y_f = lowpass_filter(y, fc=20, fs=fs, filter="cheby1")

    assert len(y_f) == len(y)
    assert np.all(np.isfinite(y_f))
    assert y_f.std() < y.std()


# ------------------------------------------------------------
#  Test 5 — Constant signal should remain unchanged
# ------------------------------------------------------------
def test_lowpass_filter_constant_signal_no_artifacts():
    t = np.linspace(0, 1, 500)
    y = np.ones_like(t)
    fs = _fs_from_t(t)

    y_f = lowpass_filter(y, fc=20, fs=fs)

    # Filtering a constant signal should not introduce artifacts
    assert np.allclose(y_f, y)
