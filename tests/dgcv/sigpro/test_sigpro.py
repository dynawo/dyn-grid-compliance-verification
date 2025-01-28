#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import numpy as np

from dgcv.sigpro.sigpro import abc_to_psrms, shortfft

PLOT = False


def gen_abc(N):
    end_time = 1
    step_size = end_time / N
    t = np.arange(0, end_time, step_size)
    wt = 2 * np.pi * 50 * t

    rad_angA = float(0) * np.pi / 180
    rad_angB = float(240) * np.pi / 180
    rad_angC = float(120) * np.pi / 180

    A = (np.sqrt(2) * float(1)) * np.sin(wt + rad_angA)
    B = (np.sqrt(2) * float(1)) * np.sin(wt + rad_angB)
    C = (np.sqrt(2) * float(1)) * np.sin(wt + rad_angC)

    return [A, B, C], 1 / step_size, t


def test_shortfft():
    abc, fs, _ = gen_abc(300)
    for x in abc:
        f, t, Zxx = shortfft(x, fs)
        assert f is not None
        assert t is not None
        assert Zxx is not None

        idx = np.argmin(np.abs(f - 50))
        assert idx is not None


def test_abc_to_psrms():
    abc, fs, _ = gen_abc(300)
    ps_rms = abc_to_psrms(abc, fs)
    assert ps_rms is not None
