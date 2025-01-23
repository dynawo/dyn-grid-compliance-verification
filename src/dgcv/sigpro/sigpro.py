import numpy as np
import pandas as pd
from scipy import signal
from scipy.interpolate import PchipInterpolator
from dgcv.sigpro import lp_filters
from dgcv.configuration.cfg import config

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


def resample(x, t, fs=1000):
    start_time = t[0]
    end_time = t[-1]
    N_r = int((end_time - start_time) * fs)
    t_r = np.linspace(start_time, end_time, N_r)
    return t_r, np.interp(t_r, t, x)


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


def ensure_rms_signals(curves, fs):
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


def resampling_signal(curves, fs=1000):
    resampled_curve_dict = {}
    for col in curves.columns:
        if "time" in col:
            continue

        t_r, r = resample(curves[col], curves["time"].values.tolist(), fs)
        resampled_curve_dict[col] = r

    resampled_curve_dict["time"] = t_r
    return pd.DataFrame.from_dict(resampled_curve_dict, orient="columns")


def filter_signal(curves, cutoff=15, fs=1000, filter_name="critdamped"):
    # This function applies a low-pass filter to the signal, with these options:
    #   * filters each window separately (default) or the whole signal
    #   * filtering can be disabled altogether via user config
    #   * cutoff frequency f_c (default: IEC's 15 Hz)
    #   * choice of filter (default: IEC's 2nd-order critically damped)
    lowpass_curve_dict = {}
    for col in curves.columns:
        if "time" in col:
            continue

        # Disable filtering altogether also when the signal is a (non-zero) constant because
        # LP filters produce artifacts at boundaries, potentially introducing spurious errors.
        # TODO: won't be necessary once we enable the exclusion windows needed by LP-filtering.
        c = curves[col]
        if config.get_boolean("Debug", "disable_LP_filtering", False) or max(list(c)) == min(
            list(c)
        ):
            c_filt = c
        else:
            c_filt = lowpass_filter(c, cutoff, fs, filter_name)
            # For avoiding overflows in PChipInterpolator (used in resampling later on)
            # TODO: this won't be necessary anymore once we filter the signals *after* the two
            # resamplings in CurvesManager.apply_signal_processing()
            c_filt[abs(c_filt) < ZERO_THRESHOLD] = 0.0

        lowpass_curve_dict[col] = c_filt

    lowpass_curve_dict["time"] = curves["time"]
    return pd.DataFrame.from_dict(lowpass_curve_dict, orient="columns")


def interpolate_same_time_grid(curves_final, curves_ref, fs=1000):
    final_times = curves_final["time"].to_numpy()
    final_unique_indices = np.unique(final_times, return_index=True)[1]
    final_times = final_times[final_unique_indices]
    ref_times = curves_ref["time"].to_numpy()
    ref_unique_indices = np.unique(ref_times, return_index=True)[1]
    ref_times = ref_times[ref_unique_indices]
    t_start = max(final_times[0], ref_times[0])
    t_end = min(final_times[-1], ref_times[-1])
    itime = np.arange(t_start, t_end, step=1 / fs)

    # warnings.filterwarnings("ignore", module="scipy")
    icurves_final = dict()
    icurves_ref = dict()
    for key in curves_ref:
        if "time" in key:
            continue

        if key not in curves_final:
            continue

        final_values = curves_final[key][final_unique_indices]
        ref_values = curves_ref[key][ref_unique_indices]
        icurves_final[key] = PchipInterpolator(final_times, final_values)(itime)
        icurves_ref[key] = PchipInterpolator(ref_times, ref_values)(itime)

    icurves_final["time"] = itime
    icurves_ref["time"] = itime
    return pd.DataFrame(icurves_final), pd.DataFrame(icurves_ref)
