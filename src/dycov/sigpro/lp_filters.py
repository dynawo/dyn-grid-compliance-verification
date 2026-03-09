from typing import List, Tuple

import numpy as np
import numpy.typing as npt
from scipy.signal import bessel, bilinear, butter, cheby1, filtfilt, lfilter, tf2zpk


def apply_filtfilt(
    b: List[float],
    a: List[float],
    input_signal: npt.ArrayLike,
    padding_method: str = "gust",
) -> npt.ArrayLike:
    """
    Applies a filter using a forward+backward pass (filtfilt).

    Parameters:
    b, a: List[float], List[float]
        Numerator and denominator of the digital filter transfer function.
    input_signal: npt.ArrayLike
        Input signal, a 1-d array is expected.
    padding_method: str
        Method used to treat the signal boundaries in filtfilt. One of: {
            "gust",
            "odd_padding",
            "even_padding",
            "constant_padding",
            "no_padding",
        }

    Returns:
    output_signal: npt.ArrayLike
        The filtered signal.
    """
    if padding_method == "gust":
        # Gustaffson's padding method for determining the initial states
        # First calculate the approx. impulse response length (saves computation time)
        _, p, _ = tf2zpk(b, a)
        eps = 1.0e-9
        r = np.max(np.abs(p))
        approx_ir_len = int(np.ceil(np.log(eps) / np.log(r)))
        output_signal = filtfilt(b, a, input_signal, method="gust", irlen=approx_ir_len)
    elif padding_method == "odd_padding":
        output_signal = filtfilt(b, a, input_signal, method="pad", padtype="odd")
    elif padding_method == "even_padding":
        output_signal = filtfilt(b, a, input_signal, method="pad", padtype="even")
    elif padding_method == "constant_padding":
        output_signal = filtfilt(b, a, input_signal, method="pad", padtype="constant")
    elif padding_method == "no_padding":
        output_signal = filtfilt(b, a, input_signal, method="pad", padtype=None)
    else:
        raise ValueError("Invalid method specified for use in filtfilt()")
    return output_signal


def apply_lfilter(b: List[float], a: List[float], input_signal: npt.ArrayLike) -> npt.ArrayLike:
    """
    Applies a filter using a single forward (lfilter). Not used since it introduces delays.

    Parameters:
    b, a: List[float], List[float]
        Numerator and denominator of the digital filter transfer function.
    input_signal: npt.ArrayLike
        Input signal, a 1-d array is expected.

    Returns:
    output_signal: npt.ArrayLike
        The filtered signal.
    """
    output_signal = lfilter(b, a, input_signal)
    return output_signal


def critically_damped_lpf(fc: float, fs: float) -> Tuple[List[float], List[float]]:
    """
    Implements a second-order, critically damped low-pass filter.

    Parameters:
    fc: float
        Cutoff frequency of the filter in Hz.
    fs: float
        Sampling frequency in Hz.

    Returns:
    b, a: List[float], List[float]
        Numerator and denominator of the digital filter transfer function.
    """
    # Normalized cutoff frequency (as a fraction of the Nyquist frequency)
    omega_c = 2 * np.pi * fc

    # Define the continuous-time transfer function coefficients for critical damping
    b_continuous = [omega_c**2]
    a_continuous = [1, 2 * omega_c, omega_c**2]

    # Convert to discrete-time using the bilinear transform
    b, a = bilinear(b_continuous, a_continuous, fs)

    return b, a


def bessel_lpf(fc: float, fs: float) -> Tuple[List[float], List[float]]:
    """
    Implements a second-order Bessel low-pass filter.

    Parameters:
    fc: float
        Cutoff frequency of the filter in Hz.
    fs: float
        Sampling frequency in Hz.

    Returns:
    b, a: List[float], List[float]
        Numerator and denominator of the digital filter transfer function.
    """
    # Normalize the cutoff frequency
    Wn = fc / (fs / 2)

    # Design the Bessel filter
    b, a = bessel(2, Wn, btype="low", analog=False, output="ba")

    return b, a


def butter_lpf(fc: float, fs: float) -> Tuple[List[float], List[float]]:
    """
    Implements a second-order Butterworth low-pass filter.

    Parameters:
    fc: float
        Cutoff frequency of the filter in Hz.
    fs: float
        Sampling frequency in Hz.

    Returns:
    b, a: List[float], List[float]
        Numerator and denominator of the digital filter transfer function.
    """
    # Normalize the cutoff frequency
    Wn = fc / (fs / 2)

    # Design the Butterworth filter
    b, a = butter(2, Wn, btype="low", analog=False, output="ba")

    return b, a


def cheby1_lpf(fc: float, fs: float) -> Tuple[List[float], List[float]]:
    """
    Implements a second-order type-I Chebyshev low-pass filter.

    Parameters:
    fc: float
        Cutoff frequency of the filter in Hz.
    fs: float
        Sampling frequency in Hz.

    Returns:
    b, a: List[float], List[float]
        Numerator and denominator of the digital filter transfer function.
    """
    # Normalize the cutoff frequency
    Wn = fc / (fs / 2)

    # Design the Butterworth filter
    rp = 5  # Max ripple below unity gain in the passband, in decibels
    b, a = cheby1(2, rp, Wn, btype="low", analog=False, output="ba")

    return b, a
