#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Damping of the oscillations of a signal, estimated with the Matrix Pencil method.

The method (Hua & Sarkar, 1990) fits the signal with a sum of damped complex exponentials and
returns their poles, from which the frequency and the damping ratio of every oscillating mode
follow. It is the method the DTR Fiche I18 prescribes to check the damping of the currents of a
Grid Forming unit.
"""

from collections import namedtuple

import numpy as np
import numpy.typing as npt

Mode = namedtuple("Mode", ["frequency", "damping_ratio", "amplitude"])

# The signal is resampled to this multiple of the highest frequency of interest: enough to
# resolve it, while keeping the Hankel matrix small enough for its SVD to stay cheap.
_SAMPLES_PER_PERIOD = 10
# Singular values below this fraction of the largest one are taken as noise, which fixes the
# number of exponentials of the fit. A lower fraction lets the fit spend exponentials on the
# features of a response that are not oscillations, such as the corner where a current leaves
# its limit, and those exponentials show up as lightly damped modes that are not there.
_SVD_TOLERANCE = 5e-2
# Modes whose amplitude is below this fraction of the peak-to-peak span of the signal are fitting
# residue rather than an oscillation present in the signal.
_AMPLITUDE_TOLERANCE = 0.01


def oscillation_modes(
    time: npt.ArrayLike,
    signal: npt.ArrayLike,
    f_min: float,
    f_max: float,
    min_amplitude: float,
) -> list[Mode]:
    """Gets the oscillating modes of a signal whose frequency lies in a band.

    Parameters
    ----------
    time: npt.ArrayLike
        Time values, increasing, in seconds.
    signal: npt.ArrayLike
        Signal values. It must not hold any discontinuity, so a signal crossing several events
        is to be analyzed one window at a time.
    f_min: float
        Lowest frequency of interest, in Hz.
    f_max: float
        Highest frequency of interest, in Hz.
    min_amplitude: float
        Smallest amplitude of an oscillation, in the units of the signal. Below it, the fit
        finds modes in the numerical noise of a nearly flat signal, with any damping.

    Returns
    -------
    list[Mode]
        Frequency (Hz), damping ratio and amplitude (relative to the peak-to-peak span of the
        signal) of every mode found in the band, an empty list when the signal does not
        oscillate.
    """
    # Shorter than a period of the highest frequency, the window cannot show an oscillation
    if len(time) < 2 or time[-1] - time[0] < 1 / f_max:
        return []

    sampling_rate = _SAMPLES_PER_PERIOD * f_max
    uniform_time = np.arange(time[0], time[-1], 1 / sampling_rate)
    values = np.interp(uniform_time, time, signal)
    # The final value is a pole at z = 1 that the fit would otherwise spend an exponential on
    values = values - values[-1]
    span = np.ptp(values)
    if span < min_amplitude:
        return []

    poles = _poles(values)
    amplitudes = _amplitudes(poles, values)
    exponents = np.log(poles.astype(complex)) * sampling_rate

    modes = []
    for exponent, amplitude in zip(exponents, amplitudes):
        # Each oscillation is a pair of conjugate poles, only the one of positive frequency
        # is kept, carrying the amplitude of both
        if exponent.imag <= 0:
            continue
        frequency = exponent.imag / (2 * np.pi)
        relative_amplitude = 2 * abs(amplitude) / span
        is_present = (
            relative_amplitude >= _AMPLITUDE_TOLERANCE
            and relative_amplitude * span >= min_amplitude
        )
        if f_min <= frequency <= f_max and is_present:
            modes.append(
                Mode(
                    frequency=frequency,
                    damping_ratio=-exponent.real / abs(exponent),
                    amplitude=relative_amplitude,
                )
            )
    return modes


def _poles(values: np.ndarray) -> np.ndarray:
    """Poles of the exponentials that fit a uniformly sampled signal."""
    # A pencil parameter of a third of the samples is the one Hua & Sarkar find the least
    # sensitive to noise
    pencil = len(values) // 3
    hankel = np.lib.stride_tricks.sliding_window_view(values, pencil + 1)
    _, singular_values, right_vectors = np.linalg.svd(hankel, full_matrices=False)
    order = int(np.sum(singular_values > _SVD_TOLERANCE * singular_values[0]))
    signal_space = right_vectors[:order].conj().T
    return np.linalg.eigvals(np.linalg.pinv(signal_space[:-1]) @ signal_space[1:])


def _amplitudes(poles: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Complex amplitudes of the exponentials of the given poles, in the least-squares sense."""
    vandermonde = np.vander(poles, len(values), increasing=True).T
    return np.linalg.lstsq(vandermonde, values.astype(complex), rcond=None)[0]
