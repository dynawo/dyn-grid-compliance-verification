#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import matplotlib.pyplot as plt
import numpy as np

from dgcv.sigpro.sigpro import abc_to_psrms, lowpass_filter, resample, shortfft

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
    abc, fs, tsteps = gen_abc(300)
    for x in abc:
        f, t, Zxx = shortfft(x, fs)
        assert f is not None
        assert t is not None
        assert Zxx is not None

        idx = np.argmin(np.abs(f - 50))
        assert idx is not None

        if PLOT:
            plt.figure()
            plt.pcolormesh(t, f, np.abs(Zxx))
            plt.title("STFT Magnitude")
            plt.ylabel("Frequency [Hz]")
            plt.xlabel("Time [sec]")
            plt.colorbar()
            plt.ylim([40, 60])
            plt.figure()
            plt.pcolormesh(t, f, np.angle(Zxx))
            plt.title("STFT Angle")
            plt.ylabel("Frequency [Hz]")
            plt.xlabel("Time [sec]")
            plt.colorbar()
            plt.ylim([40, 60])
            plt.show(block=False)

    if PLOT:
        plt.close("all")
        plt.figure()
        plt.plot(t, np.angle(Zxx[idx]))
        plt.plot(t, np.abs(np.angle(Zxx[idx])))
        plt.show(block=False)


def test_sigpro():
    fs_r = 2000
    abc, fs, tsteps = gen_abc(300)
    ps_rms = abc_to_psrms(abc, fs)
    assert ps_rms is not None
    t_r, r = resample(ps_rms, tsteps, fs_r)
    assert len(t_r) == int(fs_r * tsteps[-1])
    assert len(r) == int(fs_r * tsteps[-1])
    r_filt = lowpass_filter(r, 50, fs_r)
    assert len(r_filt) == int(fs_r * tsteps[-1])

    if PLOT:
        plt.plot(r)
        plt.plot(r_filt)
        plt.show(block=False)
