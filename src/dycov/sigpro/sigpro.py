import warnings

import numpy as np
import pandas as pd
from scipy import signal
from scipy.interpolate import PchipInterpolator

from dycov.configuration.cfg import config
from dycov.logging.logging import dycov_logging
from dycov.sigpro import lp_filters

# For avoiding overflows in PChipInterpolator
ZERO_THRESHOLD = 1.0e-10


def shortfft(x, fs):
    f, t, Zxx = signal.stft(x, fs, nperseg=100, noverlap=99)
    return f, t, Zxx


def positive_sequence(abc):
    a = np.exp(2j * np.pi / 3)
    A = (1 / 3) * np.linalg.inv(np.array([[1, 1, 1], [1, a**2, a], [1, a, a**2]]))
    return A.dot(abc)


def abc_to_psrms(abc, fs):
    Zxx_abc_50 = []
    for x in abc:
        f, t, Zxx = shortfft(x, fs)
        idx = np.argmin(np.abs(f - 50))
        Zxx_abc_50.append(
            Zxx[idx][0:-1]
        )  # the stft function returns a 1 element longer array than the input
    ps = positive_sequence(Zxx_abc_50)[1]
    return (1 / np.sqrt(2)) * np.abs(ps)


def ensure_rms_signals(curves):
    time_step = np.mean(np.diff(curves["time"].to_numpy()))
    fs = 1 / time_step

    processed_curve_dict = {}
    abc_items, rms_items = find_abc_signal(curves)
    for abc_item in abc_items:
        a = curves[abc_item + "_a"]
        b = curves[abc_item + "_b"]
        c = curves[abc_item + "_c"]
        ps_rms = abc_to_psrms([a, b, c], fs)
        processed_curve_dict[abc_item] = ps_rms

    for rms_item in rms_items:
        processed_curve_dict[rms_item] = curves[rms_item]

    return pd.DataFrame.from_dict(processed_curve_dict, orient="columns")


def find_abc_signal(curves):
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


def resample_to_fixed_step(curves: pd.DataFrame, fs_max=1000):
    """
    Resamples a set of curves to ensure they have a fixed time step.

    Simulated signals typically have a variable time step, and this functions converts them to
    a fixed time step via mathematical interpolation (of the monotone kind, to avoid overshooting
    artifacts).  The actual step is not prescribed, but calculated from the time grid of the
    original signal, to preserve as much as possible the signal's bandwidth.
    """
    # Simulations may have repeated time points. Get rid of them using unique().
    orig_tgrid = curves["time"].to_numpy()
    uniq_idx = np.unique(orig_tgrid, return_index=True)[1]
    uniq_tgrid = orig_tgrid[uniq_idx]

    # Calculate the new fixed time step.
    curve_tsteps = np.diff(uniq_tgrid)
    min_tstep = np.min(curve_tsteps)
    new_tstep = max(min_tstep, 1 / fs_max)

    # Construct the new time grid
    t_start, t_end = uniq_tgrid[0], uniq_tgrid[-1]
    new_tgrid = np.arange(t_start, t_end, step=new_tstep)

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
# In our datasets the signals are almost flat and sampled on a dense, strictly increasing time grid.
# PchipInterpolator computes local slopes mk = Δy/Δx and then uses a weighted harmonic mean that
# includes terms of the form w / mk. When |Δy| is ~0 (plateaus) or Δx is extremely small, mk → 0,
# so 1/mk becomes numerically huge, which triggers "overflow encountered in divide". The same
# instability can propagate into subsequent weighted sums inside the derivative smoothing step,
# surfacing as "overflow encountered in add". In short: near-zero slopes from quasi-constant curves
# (or tiny time steps) make the internal reciprocal-weight calculations blow up.
def resample_to_common_tgrid(sim_curves, ref_curves):
    """
    Resamples TWO sets of curves to a common fixed time step, t_com.

    To be able to compare point-wise the waveforms of the Simulated curves (either obtained from
    Dynawo simulation or user-provided) curves versus the Reference ones, both sets must be
    resampled so that they share the same time grid. The new sampling rate (fs = 1 / t_com) is a
    configurable value, but obviously it must be *higher* than twice the cutoff frequency used in
    the low-pass filtering stage (which must have happened before we reach this function).
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
    for col in ref_curves:
        if "time" == col or col not in sim_curves:
            continue
        sim_values = sim_curves[col][sim_uniq_idx]
        ref_values = ref_curves[col][ref_uniq_idx]

        # Capture RuntimeWarnings during interpolation and log them at debug level
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", RuntimeWarning)

            rs_sim_curves[col] = PchipInterpolator(sim_times, sim_values)(new_tgrid)
            rs_ref_curves[col] = PchipInterpolator(ref_times, ref_values)(new_tgrid)
            for warn in w:
                if issubclass(warn.category, RuntimeWarning):
                    dycov_logging.get_logger("SigPro").debug(
                        f"RuntimeWarning during interpolation of column '{col}': {warn.message}"
                    )

    return pd.DataFrame(rs_sim_curves), pd.DataFrame(rs_ref_curves)


def lowpass_filter(signal, fc=15, fs=1000, filter="critdamped", padding_method="gust"):
    """
    Applies a low-pass second-order filter to a 1-d signal.

    Parameters:
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

    Returns:
    output_signal: npt.ArrayLike
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


def get_time_positions(time_values, t_from, t_to):
    w_init_pos = np.searchsorted(time_values, t_from)
    w_end_pos = np.searchsorted(time_values, t_to)

    return w_init_pos, w_end_pos


def filter_curves(curves, windows, f_cutoff=15, filter_name="critdamped"):
    """
    This function applies a low-pass filter to a set of curves, with these options:
       * filters each window separately (default) or the whole signal
       * filtering can be disabled altogether via user config
       * cutoff frequency f_c (default: IEC's 15 Hz)
       * choice of filter (default: IEC's 2nd-order critically damped)
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
                w_init, w_end = get_time_positions(time_values, t_from, t_to)
                c_filt[w_init:w_end] = lowpass_filter(c[w_init:w_end], f_cutoff, fs, filter_name)

                t_from, t_to = windows["during"]
                if t_to > t_from:
                    w_init, w_end = get_time_positions(time_values, t_from, t_to)
                    c_filt[w_init:w_end] = lowpass_filter(
                        c[w_init:w_end], f_cutoff, fs, filter_name
                    )

                t_from, t_to = windows["after"]
                w_init, w_end = get_time_positions(time_values, t_from, t_to)
                c_filt[w_init:w_end] = lowpass_filter(c[w_init:w_end], f_cutoff, fs, filter_name)

            # TODO: double-check if this is still necessary
            # c_filt[abs(c_filt) < ZERO_THRESHOLD] = 0.0

        lowpass_curve_dict[col] = c_filt

    lowpass_curve_dict["time"] = curves["time"]
    return pd.DataFrame.from_dict(lowpass_curve_dict, orient="columns")
