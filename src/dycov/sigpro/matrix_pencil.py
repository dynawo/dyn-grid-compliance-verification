#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Damping of the oscillations of a signal, estimated with the Matrix Pencil method as RTE
implements it.

The DTR Fiche I18 names RTE's implementation as the one the compliance of an installation is
checked with: the signal is sampled at a fixed step, a pencil of fixed order is fitted to it, and
each of its poles gives the frequency, the damping ratio and the amplitude of a mode. This module
follows it step by step, so that a test gets the damping RTE finds in it.
"""

from collections import namedtuple

import numpy as np
import numpy.typing as npt
from scipy import linalg

Mode = namedtuple("Mode", ["frequency", "damping_ratio", "amplitude"])


def oscillation_modes(
    time: npt.ArrayLike,
    signal: npt.ArrayLike,
    t_from: float,
    t_to: float,
    f_min: float,
    f_max: float,
    time_step: float,
    pencil: int,
) -> list[Mode]:
    """Gets the oscillating modes of a window of a signal whose frequency lies in a band.

    Parameters
    ----------
    time: npt.ArrayLike
        Time values of the whole signal, in seconds.
    signal: npt.ArrayLike
        Signal values.
    t_from: float
        Start of the window analysed, in seconds.
    t_to: float
        End of the window analysed, in seconds. The window must not hold any discontinuity of
        the signal.
    f_min: float
        Lowest frequency of interest, in Hz.
    f_max: float
        Highest frequency of interest, in Hz.
    time_step: float
        Step the signal is sampled at for the fit, in seconds.
    pencil: int
        Pencil parameter: the number of poles the signal is fitted with.

    Returns
    -------
    list[Mode]
        Damped frequency (Hz), damping ratio and amplitude (in the units of the signal) of every
        mode found in the band, by increasing frequency; an empty list when there is none, or
        when the window holds too few samples for the pencil.
    """
    values = _sampled(time, signal, t_from, t_to, time_step)
    if len(values) <= 2 * pencil:
        return []

    poles = _poles(values, pencil)
    with np.errstate(divide="ignore", invalid="ignore"):
        decay = np.log(np.abs(poles)) / time_step
        frequency = np.angle(poles) / (2 * np.pi * time_step)
        damping_ratio = -decay / np.sqrt((2 * np.pi * frequency) ** 2 + decay**2)
    amplitude = np.abs(2 * _amplitudes(poles, values))

    in_band = (frequency >= f_min) & (frequency <= f_max)
    return sorted(
        Mode(float(f), float(z), float(a))
        for f, z, a in zip(frequency[in_band], damping_ratio[in_band], amplitude[in_band])
    )


def _sampled(
    time: npt.ArrayLike, signal: npt.ArrayLike, t_from: float, t_to: float, time_step: float
) -> np.ndarray:
    """The signal on a grid of the given step that starts with the signal, inside the window."""
    # An instant repeated at a discontinuity keeps the value before it
    instants, first = np.unique(np.asarray(time, dtype=float), return_index=True)
    if instants.size < 2:
        return np.array([])
    values = np.asarray(signal, dtype=float)[first]
    grid = np.arange(instants[0], instants[-1], time_step)
    grid = grid[(grid >= t_from) & (grid <= t_to)]
    return np.interp(grid, instants, values)


def _poles(values: np.ndarray, pencil: int) -> np.ndarray:
    """Poles of the exponentials that fit a uniformly sampled signal."""
    # The pencil is ill-conditioned: only the complex fit and the eigenvalues of SciPy that RTE's
    # implementation uses find its poles in the same samples
    hankel = np.lib.stride_tricks.sliding_window_view(values.astype(complex), pencil + 1)
    return linalg.eigvals(np.linalg.pinv(hankel[:, :-1]) @ hankel[:, 1:])


def _amplitudes(poles: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Complex amplitudes of the exponentials of the given poles, in the least-squares sense."""
    with np.errstate(over="ignore", invalid="ignore"):
        vandermonde = poles[np.newaxis, :] ** np.arange(len(values))[:, np.newaxis]
    # A growing pole overflows over a long window, and least squares needs finite values
    vandermonde[~np.isfinite(vandermonde)] = np.finfo(float).max
    return np.linalg.lstsq(vandermonde, values.astype(complex), rcond=None)[0]
