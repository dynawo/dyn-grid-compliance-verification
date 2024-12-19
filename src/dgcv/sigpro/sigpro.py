import numpy as np
import pandas as pd
from scipy import signal
from scipy.interpolate import PchipInterpolator

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


def lowpass_filter(x, cutoff=15, fs=1000, filter="bessel"):
    # The filter type should have minimal ringing, so bessel is preferred
    # b, a = signal.butter(5, cutoff, fs=fs, btype="low", analog=False)
    if filter == "bessel":
        b, a = signal.bessel(2, cutoff, fs=fs, btype="low", analog=False)
    if filter == "butter":
        b, a = signal.butter(5, cutoff, fs=fs, btype="low", analog=False)
    return signal.filtfilt(b, a, x)


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


def lowpass_signal(curves, cutoff=15, fs=1000, filter="bessel"):
    lowpass_curve_dict = {}
    for col in curves.columns:
        if "time" in col:
            continue

        # The low pass filter introduces noise to the curve so a constant curve is no longer
        #  constant, introducing errors that were not there.
        c = curves[col]
        if max(list(c)) == min(list(c)) or config.get_boolean(
            "Debug", "disable_LP_filtering", False
        ):
            c_filt = c
        else:
            c_filt = lowpass_filter(c, cutoff, fs, filter)
            # For avoiding overflows in PChipInterpolator
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
