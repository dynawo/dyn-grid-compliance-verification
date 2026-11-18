#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import warnings

import numpy as np
import numpy.typing as npt
import pandas as pd
from scipy import signal
from scipy.interpolate import CubicSpline, PchipInterpolator

from dycov.configuration.cfg import config
from dycov.logging import dycov_logging
from dycov.sigpro import lp_filters

# For avoiding overflows in PChipInterpolator
ZERO_THRESHOLD = 1.0e-10

# Fraction of a step a sample may lie away from the grid of whole samples per cycle and still be
# taken as lying on it: time stamps written with few digits, or in single precision, wander so.
_ON_GRID_TOLERANCE = 0.01


def _fundamental_grid(time: np.ndarray, f_nom: float) -> tuple[np.ndarray, int]:
    """Build the uniform time grid with a whole number of samples per fundamental cycle.

    Its step is the one closest to the mean step of the samples that divides the cycle exactly,
    so that the sum over the samples of one cycle integrates every harmonic of that cycle exactly.

    Parameters
    ----------
    time : np.ndarray
        Time stamps of the samples, in seconds.
    f_nom : float
        Fundamental frequency, in Hz.

    Returns
    -------
    tuple[np.ndarray, int]
        The grid, spanning the samples, and its number of samples per cycle.
    """
    span = time[-1] - time[0]
    samples_per_cycle = round((len(time) - 1) / (span * f_nom))
    step = 1 / (f_nom * samples_per_cycle) if samples_per_cycle else np.inf
    grid = time[0] + step * np.arange(int(span / step + _ON_GRID_TOLERANCE) + 1)
    if samples_per_cycle < 3 or len(grid) < 2 * (samples_per_cycle // 2) + 2:
        raise ValueError(
            f"Three-phase curves sampled every {span / (len(time) - 1):g} s over {span:g} s "
            f"cannot be converted to RMS: the conversion needs three samples per cycle of "
            f"{f_nom:g} Hz at least, over more than one cycle"
        )
    return grid, samples_per_cycle


def _lies_on(time: np.ndarray, grid: np.ndarray) -> bool:
    """Tell whether each sample lies on its point of the grid, within the tolerance."""
    tolerance = _ON_GRID_TOLERANCE * (grid[1] - grid[0])
    return len(time) == len(grid) and np.max(np.abs(time - grid)) <= tolerance


def _resampled(time: np.ndarray, values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Resample a waveform on the grid with a cubic spline, the most precise interpolant of a
    sinusoid among the usual ones."""
    unique_time, first = np.unique(time, return_index=True)
    return CubicSpline(unique_time, values[first])(grid)


def _fundamental_phasor(
    samples: np.ndarray, grid: np.ndarray, samples_per_cycle: int, f_nom: float
) -> np.ndarray:
    """Calculate the fundamental phasor of a waveform over one cycle centred on each sample.

    The phasor is the Fourier coefficient of IEC 61400-21-1, Annex C: 2/T times the integral,
    over one cycle T, of the waveform times exp(-j 2 pi f_nom t). Its magnitude is the peak of the
    fundamental. The standard stamps it at the end of the cycle, which delays it by T/2; it is
    stamped here at the centre, as the synchrophasor standard IEC/IEEE 60255-118-1 does, so that
    it does not lag behind the RMS simulation it is compared with.

    With N samples per cycle, the integral is summed by the midpoint rule over N samples when N
    is odd, and by the trapezoidal rule over the N + 1 samples that span the cycle when N is even.
    Both are exact for every harmonic up to N - 2, and so reject all of them.

    Parameters
    ----------
    samples : np.ndarray
        Waveform sampled on the grid.
    grid : np.ndarray
        Uniform time grid with samples_per_cycle samples per cycle, in seconds.
    samples_per_cycle : int
        Number of samples per cycle of the grid.
    f_nom : float
        Fundamental frequency, in Hz.

    Returns
    -------
    np.ndarray
        Complex phasor at each sample of the grid half a cycle away from both of its ends.
    """
    weights = np.ones(samples_per_cycle + 1 - samples_per_cycle % 2)
    if samples_per_cycle % 2 == 0:
        weights[[0, -1]] = 0.5
    demodulated = samples * np.exp(-2j * np.pi * f_nom * grid)
    return 2 / samples_per_cycle * signal.convolve(demodulated, weights, mode="valid")


def _positive_sequence(phasor_a, phasor_b, phasor_c):
    """Calculate the positive-sequence component of three phase phasors (Fortescue)."""
    a = np.exp(2j * np.pi / 3)
    return (phasor_a + a * phasor_b + a**2 * phasor_c) / 3


def _warn_if_undersampled(sampling_frequency: float) -> None:
    minimum = config.get_float("GridCode", "emt_min_sampling_frequency", 2000.0)
    if round(sampling_frequency) < minimum:
        dycov_logging.get_logger("SigPro").warning(
            f"Three-phase curves sampled at {round(sampling_frequency)} Hz, below the "
            f"{minimum:.0f} Hz the DTR asks of EMT and measured reference signals: their "
            f"harmonics may alias onto the fundamental"
        )


def ensure_rms_signals(curves: pd.DataFrame) -> pd.DataFrame:
    """Ensures that the curves DataFrame contains RMS signals, converting from ABC if necessary.

    The columns of a three-phase signal end in "_a", "_b" and "_c", and hold the instantaneous
    values of its phases. They are replaced by one column, named after the signal, with the RMS
    value of the positive-sequence component of their fundamental, in the unit of the samples
    (IEC 61400-21-1, Annex C, without frequency tracking): a balanced voltage of 1 pu RMS, whose
    phases peak at sqrt(2) pu, gives 1 pu.

    Each phasor needs a whole cycle of samples around it, so the curves lose their first and last
    half cycle. Samples off a uniform grid with a whole number of samples per cycle are resampled
    on one, and their RMS value brought back to their own time stamps. The other columns keep
    their values.

    Parameters
    ----------
    curves : pd.DataFrame
        DataFrame containing the curves, with a "time" column and either ABC or RMS columns

    Returns
    -------
    pd.DataFrame
        DataFrame containing the curves in RMS format
    """
    abc_items, rms_items = _find_abc_signal(curves)
    if not abc_items:
        return curves

    f_nom = config.get_float("Dynawo", "f_nom", 50.0)
    time = curves["time"].to_numpy()
    grid, samples_per_cycle = _fundamental_grid(time, f_nom)
    _warn_if_undersampled((len(time) - 1) / (time[-1] - time[0]))
    on_grid = _lies_on(time, grid)
    half_cycle = samples_per_cycle // 2
    centres = grid[half_cycle : len(grid) - half_cycle]
    if on_grid:
        kept = np.arange(half_cycle, len(time) - half_cycle)
    else:
        kept = np.flatnonzero((time >= centres[0]) & (time <= centres[-1]))

    processed_curve_dict = {}
    for abc_item in abc_items:
        phasors = []
        for phase in ("a", "b", "c"):
            samples = curves[f"{abc_item}_{phase}"].to_numpy()
            if not on_grid:
                samples = _resampled(time, samples, grid)
            phasors.append(_fundamental_phasor(samples, grid, samples_per_cycle, f_nom))
        ps_rms = np.abs(_positive_sequence(*phasors)) / np.sqrt(2)
        processed_curve_dict[abc_item] = (
            ps_rms if on_grid else PchipInterpolator(centres, ps_rms)(time[kept])
        )

    for rms_item in rms_items:
        processed_curve_dict[rms_item] = curves[rms_item].to_numpy()[kept]

    return pd.DataFrame(processed_curve_dict)


def _find_abc_signal(curves):
    abc_items = []
    rms_items = []
    for col in curves.columns:
        if col.endswith("_c"):
            continue
        if col.endswith("_b"):
            continue
        if col.endswith("_a"):
            abc_items.append(col[:-2])
        else:
            rms_items.append(col)

    return abc_items, rms_items


def _build_fixed_tgrid(uniq_tgrid: np.ndarray, fs_max: float) -> np.ndarray:
    """Build a fixed-step time grid spanning the original time grid.

    The step is the smallest one present in the original grid, but never smaller than 1/fs_max.

    Parameters
    ----------
    uniq_tgrid : np.ndarray
        Original time grid, without repeated time points.
    fs_max : float
        Maximum allowed sampling frequency (in Hz).

    Returns
    -------
    np.ndarray
        Fixed-step time grid.
    """
    curve_tsteps = np.diff(uniq_tgrid)
    min_tstep = np.min(curve_tsteps)
    new_tstep = max(min_tstep, 1 / fs_max)

    t_start, t_end = uniq_tgrid[0], uniq_tgrid[-1]
    return np.arange(t_start, t_end, step=new_tstep)


def resample_to_fixed_step(curves: pd.DataFrame, fs_max: float = 1000) -> pd.DataFrame:
    """
    Resamples a set of curves to ensure they have a fixed time step.

    Simulated signals typically have a variable time step, and this functions converts them to
    a fixed time step via mathematical interpolation (of the monotone kind, to avoid overshooting
    artifacts).  The actual step is not prescribed, but calculated from the time grid of the
    original signal, to preserve as much as possible the signal's bandwidth.

    Parameters
    ----------
    curves : pd.DataFrame
        DataFrame containing the curves, with a "time" column and signal columns.
    fs_max : float
        Maximum allowed sampling frequency (in Hz) for the resampled curves. The actual sampling
        frequency will be determined based on the original time grid, but it will not exceed
        fs_max.

    Returns
    -------
    pd.DataFrame
        DataFrame containing the resampled curves with a fixed time step.
    """
    # Simulations may have repeated time points. Get rid of them using unique().
    orig_tgrid = curves["time"].to_numpy()
    uniq_idx = np.unique(orig_tgrid, return_index=True)[1]
    uniq_tgrid = orig_tgrid[uniq_idx]

    new_tgrid = _build_fixed_tgrid(uniq_tgrid, fs_max)

    # Resample using a monotone interpolator (PCHIP)
    resampled_curve_dict = {}
    resampled_curve_dict["time"] = new_tgrid
    for col in curves.columns:
        if "time" == col:
            continue
        uniq_curve = curves[col][uniq_idx]
        resampled_curve_dict[col] = PchipInterpolator(uniq_tgrid, uniq_curve)(new_tgrid)

    return pd.DataFrame.from_dict(resampled_curve_dict, orient="columns")


# RuntimeWarning explanation:
# In our datasets the signals are almost flat and sampled on a dense, strictly increasing time
# grid. PchipInterpolator computes local slopes mk = Δy/Δx and then uses a weighted harmonic mean
# that includes terms of the form w / mk. When |Δy| is ~0 (plateaus) or Δx is extremely small,
# mk → 0, so 1/mk becomes numerically huge, which triggers "overflow encountered in divide". The
# same instability can propagate into subsequent weighted sums inside the derivative smoothing
# step,surfacing as "overflow encountered in add". In short: near-zero slopes from quasi-constant
# curves (or tiny time steps) make the internal reciprocal-weight calculations blow up.
def resample_to_common_tgrid(
    sim_curves: pd.DataFrame, ref_curves: pd.DataFrame
) -> (pd.DataFrame, pd.DataFrame):
    """
    Resamples TWO sets of curves to a common fixed time step, t_com.

    To be able to compare point-wise the waveforms of the Simulated curves (either obtained from
    Dynawo simulation or user-provided) curves versus the Reference ones, both sets must be
    resampled so that they share the same time grid. The new sampling rate (fs = 1 / t_com) is a
    configurable value, but obviously it must be *higher* than twice the cutoff frequency used in
    the low-pass filtering stage (which must have happened before we reach this function).

    Parameters
    ----------
    sim_curves : pd.DataFrame
        DataFrame containing the simulated curves, with a "time" column and signal columns.
    ref_curves : pd.DataFrame
        DataFrame containing the reference curves, with a "time" column and signal columns.
        The time range of the reference curves must overlap with that of the simulated curves.

    Returns
    -------
    (pd.DataFrame, pd.DataFrame)
        Tuple of DataFrames containing the resampled simulated and reference curves, both sharing a
        common time grid.
    """
    t_com = config.get_float("GridCode", "t_com", 0.002)

    sim_times = sim_curves["time"].to_numpy()
    sim_uniq_idx = np.unique(sim_times, return_index=True)[1]
    sim_times = sim_times[sim_uniq_idx]
    ref_times = ref_curves["time"].to_numpy()
    ref_uniq_idx = np.unique(ref_times, return_index=True)[1]
    ref_times = ref_times[ref_uniq_idx]
    t_start = max(sim_times[0], ref_times[0])
    t_end = min(sim_times[-1], ref_times[-1])
    new_tgrid = np.arange(t_start, t_end, step=t_com)

    # warnings.filterwarnings("ignore", module="scipy")
    rs_sim_curves = dict()
    rs_ref_curves = dict()
    rs_sim_curves["time"] = new_tgrid
    rs_ref_curves["time"] = new_tgrid
    for col in sim_curves:
        if col == "time":
            continue

        sim_values = sim_curves[col][sim_uniq_idx]
        if col in ref_curves:
            ref_values = ref_curves[col][ref_uniq_idx]
        else:
            ref_values = np.full_like(sim_values, np.nan, dtype=float)

        # Capture RuntimeWarnings during interpolation and log them at debug level
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", RuntimeWarning)

            rs_sim_curves[col] = PchipInterpolator(sim_times, sim_values)(new_tgrid)
            if np.isnan(ref_values).all():
                rs_ref_curves[col] = np.full_like(new_tgrid, np.nan, dtype=float)
            else:
                rs_ref_curves[col] = PchipInterpolator(ref_times, ref_values)(new_tgrid)
            for warn in w:
                if issubclass(warn.category, RuntimeWarning):
                    dycov_logging.get_logger("SigPro").debug(
                        f"RuntimeWarning during interpolation of column '{col}': {warn.message}"
                    )

    return pd.DataFrame(rs_sim_curves), pd.DataFrame(rs_ref_curves)


def lowpass_filter(
    signal: npt.ArrayLike,
    fc: float = 15,
    fs: float = 1000,
    filter: str = "critdamped",
    padding_method: str = "gust",
) -> npt.ArrayLike:
    """
    Applies a low-pass second-order filter to a 1-d signal.

    Parameters
    ----------
    signal: npt.ArrayLike
        Input signal, a 1-d array is expected.
    fc: float
        Cutoff frequency of the filter in Hz.
    fs: float
        Sampling frequency in Hz.
    filter: str
        Name of the filter to use. One of: {critdamped, bessel, butter, cheby1}
    padding_method: str
        Method used to treat the signal boundaries in filtfilt. One of: {"gust", "odd_padding",
        "even_padding", "constant_padding", "no_padding"}.

    Returns
    -------
    npt.ArrayLike
        The filtered signal.
    """

    # Reminder of filter options: critdamped, bessel, butter, cheby1
    if filter == "critdamped":
        b, a = lp_filters.critically_damped_lpf(fc, fs)
    elif filter == "bessel":
        b, a = lp_filters.bessel_lpf(fc, fs)
    elif filter == "butter":
        b, a = lp_filters.butter_lpf(fc, fs)
    elif filter == "cheby1":
        b, a = lp_filters.cheby1_lpf(fc, fs)
    else:
        raise ValueError("Invalid filter selected")

    # Valid methods for treating the signal boundaries when filtering:
    if padding_method not in (
        "gust",
        "odd_padding",
        "even_padding",
        "constant_padding",
        "no_padding",
    ):
        raise ValueError("Invalid padding method selected for filtfilt")

    return lp_filters.apply_filtfilt(b, a, signal, padding_method)


def _get_time_positions(time_values, t_from, t_to):
    w_init_pos = np.searchsorted(time_values, t_from)
    w_end_pos = np.searchsorted(time_values, t_to)

    return w_init_pos, w_end_pos


def filter_curves(
    curves: pd.DataFrame, windows: dict, f_cutoff: float = 15, filter_name: str = "critdamped"
) -> pd.DataFrame:
    """
    This function applies a low-pass filter to a set of curves, with these options:
       * filters each window separately (default) or the whole signal
       * filtering can be disabled altogether via user config
       * cutoff frequency f_c (default: IEC's 15 Hz)
       * choice of filter (default: IEC's 2nd-order critically damped)

    Parameters
    ----------
    curves : pd.DataFrame
        DataFrame containing the curves, with a "time" column and signal columns.
    windows : dict
        Dictionary defining the time windows for filtering, with keys "before", "during", and
        "after", each mapping to a tuple (t_from, t_to).
    f_cutoff : float
        Cutoff frequency for the low-pass filter in Hz (default: 15 Hz).
    filter_name : str
        Name of the low-pass filter to use (default: "critdamped"). Valid options are:
        "critdamped", "bessel", "butter", "cheby1".

    Returns
    -------
    pd.DataFrame
        DataFrame containing the filtered curves, with the same structure as the input.
    """
    # Obtain the actual sampling rate of these curves, which is needed to invoke the filter
    time_step = np.mean(np.diff(curves["time"].to_numpy()))
    fs = 1 / time_step

    # Filter
    lowpass_curve_dict = {}
    time_values = list(curves["time"])
    for col in curves.columns:
        if "time" in col:
            continue

        # Disable filtering altogether when so configured, but also when the signal is a constant
        # because LP filters produce artifacts, potentially affecting our sanity check for flat
        # curves that takes place later on (at report building time).
        c = curves[col]
        if config.get_boolean("Debug", "disable_LP_filtering", False) or max(list(c)) == min(
            list(c)
        ):
            c_filt = c
        else:
            # For avoiding overflows in PChipInterpolator (used in the 2nd resampling later on)
            if np.ptp(c) < 1e-4:  # signal almost flat
                c_filt = c
            elif config.get_boolean("GridCode", "disable_window_filtering", False):
                c_filt = lowpass_filter(c, f_cutoff, fs, filter_name)
            else:
                c_filt = c

                t_from, t_to = windows["before"]
                w_init, w_end = _get_time_positions(time_values, t_from, t_to)
                c_filt[w_init:w_end] = lowpass_filter(c[w_init:w_end], f_cutoff, fs, filter_name)

                t_from, t_to = windows["during"]
                if t_to > t_from:
                    w_init, w_end = _get_time_positions(time_values, t_from, t_to)
                    c_filt[w_init:w_end] = lowpass_filter(
                        c[w_init:w_end], f_cutoff, fs, filter_name
                    )

                t_from, t_to = windows["after"]
                w_init, w_end = _get_time_positions(time_values, t_from, t_to)
                c_filt[w_init:w_end] = lowpass_filter(c[w_init:w_end], f_cutoff, fs, filter_name)

            # TODO: double-check if this is still necessary
            # c_filt[abs(c_filt) < ZERO_THRESHOLD] = 0.0

        lowpass_curve_dict[col] = c_filt

    lowpass_curve_dict["time"] = curves["time"]
    return pd.DataFrame.from_dict(lowpass_curve_dict, orient="columns")


def apply_time_shift(
    curves: pd.DataFrame, t_event_curves: float, t_event_reference: float
) -> pd.DataFrame:
    """
    Applies a time shift to align the event time of these curves with the reference event time.

    If both event times are equal, no shift is applied.

    Validates that the event time falls within the curve's time range, since otherwise the
    shift would be semantically incorrect.

    Parameters
    ----------
    curves : pd.DataFrame
        DataFrame containing the curves, with a "time" column and signal columns.
    t_event_curves : float
        The event time associated with these curves (e.g., the time of the fault in a step-response
        test).
    t_event_reference : float
        The event time associated with the reference curves, which we want to align to (e.g., the
        time of the fault in the reference step-response test).

    Returns
    -------
    pd.DataFrame
        DataFrame containing the time-shifted curves, with the same structure as the input.
    """

    if "time" not in curves.columns:
        raise ValueError("Curves do not contain a 'time' column.")

    # Validate event time location
    tmin, tmax = curves["time"].min(), curves["time"].max()
    if not (tmin <= t_event_curves <= tmax):
        raise ValueError(
            f"Event time {t_event_curves} is outside the curve time range [{tmin}, {tmax}]."
        )

    # Compute the required shift
    shift = t_event_reference - t_event_curves

    # If no shift is needed, return curves untouched
    if abs(shift) < 1e-12:
        return curves

    shifted = curves.copy()
    shifted["time"] = shifted["time"] + shift
    return shifted
