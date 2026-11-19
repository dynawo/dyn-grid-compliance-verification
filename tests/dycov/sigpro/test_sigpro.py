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
import pandas as pd
import pytest
from scipy import integrate

from dycov.sigpro import sigpro
from dycov.sigpro.sigpro import ensure_rms_signals

F_NOM = 50.0
PERIOD = 1 / F_NOM
SHIFTS = (0.0, -2 * np.pi / 3, 2 * np.pi / 3)


def _three_phase(t, amplitude=np.sqrt(2), frequency=F_NOM, negative=0.0, harmonics=()):
    """Phases a, b and c of a positive-sequence set, plus a negative sequence and harmonics."""
    peak = amplitude(t) if callable(amplitude) else amplitude
    angle = 2 * np.pi * frequency * t + 0.3
    phases = []
    for shift in SHIFTS:
        x = peak * (np.cos(angle + shift) + negative * np.cos(angle - shift))
        for order, share in harmonics:
            x = x + peak * share * np.cos(order * (angle + shift))
        phases.append(x)
    return phases


def _curves(t, phases, **rms_columns):
    columns = {"time": t, "V_a": phases[0], "V_b": phases[1], "V_c": phases[2]}
    return pd.DataFrame({**columns, **rms_columns})


def _grid(sampling_frequency, duration=0.5):
    return np.arange(int(round(duration * sampling_frequency)) + 1) / sampling_frequency


def _jittered(t, share=0.3):
    step = (t[-1] - t[0]) / (len(t) - 1)
    t = t.copy()
    t[1:-1] += np.random.default_rng(0).uniform(-share, share, len(t) - 2) * step
    return t


def _fault(t, start=0.25):
    """Phases of a current rising from 1 to 3 pu, with the decaying DC offset its continuity
    demands and a damped 400 Hz ringing, as an EMT simulation of a fault gives."""
    angle = 2 * np.pi * F_NOM * t + 0.3
    after = t - start
    phases = []
    for shift in SHIFTS:
        offset = -2 * np.sqrt(2) * np.cos(2 * np.pi * F_NOM * start + 0.3 + shift)
        during = (
            3 * np.sqrt(2) * np.cos(angle + shift)
            + offset * np.exp(-after / 0.05)
            + 0.3 * np.exp(-after / 0.01) * np.sin(2 * np.pi * 400 * after + shift)
        )
        phases.append(np.where(t < start, np.sqrt(2) * np.cos(angle + shift), during))
    return phases


def _set_resampling_frequency(mocker, frequency, f_nom=F_NOM):
    values = {"f_nom": f_nom, "emt_min_sampling_frequency": 2000.0}
    values["emt_resampling_frequency"] = frequency
    config = mocker.patch.object(sigpro, "config")
    config.get_float.side_effect = lambda section, key, default: values[key]
    return values


def _rows_with_a_whole_cycle(t, f_nom=F_NOM):
    half_cycle = 1 / (2 * f_nom)
    tolerance = 1e-6 * half_cycle
    return t[(t >= t[0] + half_cycle - tolerance) & (t <= t[-1] - half_cycle + tolerance)]


@pytest.mark.parametrize(
    "sampling_frequency, tolerance",
    [
        (1000, 1e-3),
        (2000, 1e-4),
        (3000, 2e-5),
        (4096, 1e-5),
        (10000, 1e-12),
        (12800, 1e-12),
        (16384, 1e-12),
        (20000, 1e-12),
    ],
)
def test_balanced_set_gives_its_rms_value(sampling_frequency, tolerance):
    t = _grid(sampling_frequency)

    rms = ensure_rms_signals(_curves(t, _three_phase(t)))["V"]

    assert np.max(np.abs(rms - 1.0)) < tolerance


def test_irregular_samples_at_the_resampling_frequency_or_above_give_their_rms_value():
    t = _jittered(_grid(20000))
    phases = _three_phase(t, negative=0.1, harmonics=((5, 0.05), (7, 0.04)))

    rms = ensure_rms_signals(_curves(t, phases))["V"]

    assert np.max(np.abs(rms - 1.0)) < 5e-6


@pytest.mark.parametrize(
    "t, resampled",
    [
        (_grid(9000), True),
        (_grid(9999.9), False),
        (_grid(10000), False),
        (_jittered(_grid(10000)), False),
        (_grid(16384), False),
    ],
    ids=["9 kHz", "9999.9 Hz", "10 kHz", "10 kHz jittered", "16384 Hz"],
)
def test_only_curves_sampled_below_the_resampling_frequency_are_interpolated(mocker, t, resampled):
    interpolator = mocker.spy(sigpro, "PchipInterpolator")

    ensure_rms_signals(_curves(t, _three_phase(t)))

    assert interpolator.called is resampled


def test_resampling_never_overshoots_the_samples_at_a_jump():
    t = _grid(2000)
    t_jump = 0.25037
    wave = np.sqrt(2) * np.where(t < t_jump, 1.0, 0.3) * np.cos(2 * np.pi * F_NOM * t + 0.3)
    grid = _grid(10000)

    resampled = sigpro._resampled(t, wave, grid)

    k = np.clip(np.searchsorted(t, grid) - 1, 0, len(t) - 2)
    assert np.all(resampled >= np.minimum(wave[k], wave[k + 1]) - 1e-12)
    assert np.all(resampled <= np.maximum(wave[k], wave[k + 1]) + 1e-12)


@pytest.mark.parametrize(
    "t",
    [np.arange(1502) / 3000, np.round(93.4 + np.arange(400) / 2500, 6)],
    ids=["span off the resampling grid", "time stamps written with six decimals"],
)
def test_resampled_curves_keep_every_row_with_a_whole_cycle_around_it(t):
    converted = ensure_rms_signals(_curves(t, _three_phase(t)))

    assert np.array_equal(converted["time"], _rows_with_a_whole_cycle(t))


def test_resampling_grid_has_an_even_number_of_samples_per_cycle(mocker):
    _set_resampling_frequency(mocker, 10000.0, f_nom=60.0)
    phasor = mocker.spy(sigpro, "_fundamental_phasor")
    t = _grid(9000)

    ensure_rms_signals(_curves(t, _three_phase(t, frequency=60.0)))

    assert phasor.call_args.args[2] == 168


def test_records_with_an_odd_number_of_samples_per_cycle_are_integrated_by_the_trapezoidal_rule(
    mocker,
):
    on_samples = mocker.spy(sigpro, "_fundamental_phasor_at")
    t = _grid(10050)
    phases = _three_phase(t, negative=0.1, harmonics=((5, 0.05), (7, 0.04)))

    converted = ensure_rms_signals(_curves(t, phases))

    assert on_samples.called
    assert np.array_equal(converted["time"], _rows_with_a_whole_cycle(t))
    assert np.max(np.abs(converted["V"] - 1.0)) < 1e-12


def test_resampling_makes_a_fault_more_accurate(mocker):
    values = _set_resampling_frequency(mocker, 10000.0)
    reference_time = _grid(50000)
    reference = ensure_rms_signals(_curves(reference_time, _fault(reference_time)))
    t = _grid(5000)

    errors = []
    for frequency in (10000.0, 0.0):
        values["emt_resampling_frequency"] = frequency
        converted = ensure_rms_signals(_curves(t, _fault(t)))
        after = converted[(converted["time"] > 0.27) & (converted["time"] < 0.45)]
        expected = np.interp(after["time"], reference["time"], reference["V"])
        errors.append(np.max(np.abs(after["V"] - expected)))

    with_resampling, without_resampling = errors
    assert with_resampling < without_resampling / 2


def test_harmonics_and_negative_sequence_do_not_reach_the_positive_sequence():
    t = _grid(10000)
    phases = _three_phase(t, negative=0.1, harmonics=((2, 0.1), (3, 0.1), (5, 0.1), (7, 0.1)))

    rms = ensure_rms_signals(_curves(t, phases))["V"]

    assert np.max(np.abs(rms - 1.0)) < 1e-9


def test_off_nominal_frequency_only_scales_the_balanced_positive_sequence():
    t = _grid(10000)

    rms = ensure_rms_signals(_curves(t, _three_phase(t, frequency=49.5)))["V"]

    assert np.max(np.abs(rms - np.sinc(0.5 / F_NOM))) < 1e-7


def _iec_61400_21_annex_c(phases, t):
    """RMS phase voltage of the positive sequence over [t - T, t], by equations C.5 to C.14."""
    cos_parts, sin_parts = [], []
    for phase in phases:
        for parts, carrier in ((cos_parts, np.cos), (sin_parts, np.sin)):
            integral = integrate.quad(
                lambda x: phase(x) * carrier(2 * np.pi * F_NOM * x), t - PERIOD, t, limit=200
            )[0]
            parts.append(2 / PERIOD * integral)
    (a_cos, b_cos, c_cos), (a_sin, b_sin, c_sin) = cos_parts, sin_parts
    u1_cos = (2 * a_cos - b_cos - c_cos - np.sqrt(3) * (c_sin - b_sin)) / 6
    u1_sin = (2 * a_sin - b_sin - c_sin - np.sqrt(3) * (b_cos - c_cos)) / 6
    return np.sqrt(1.5 * (u1_sin**2 + u1_cos**2)) / np.sqrt(3)


def test_matches_iec_61400_21_annex_c_half_a_cycle_earlier():
    def amplitude(t):
        ramp = 0.2 * np.clip(t - 0.2, 0, 0.1) / 0.1
        return np.sqrt(2) * (1 - ramp + 0.03 * np.sin(6 * np.pi * t))

    def phase(k):
        return lambda x: _three_phase(np.atleast_1d(x), amplitude, negative=0.05)[k][0]

    t = _grid(10000)
    converted = ensure_rms_signals(_curves(t, _three_phase(t, amplitude, negative=0.05)))
    instants = np.array([0.1, 0.2, 0.25, 0.3, 0.42])

    expected = [_iec_61400_21_annex_c([phase(k) for k in range(3)], ti) for ti in instants]

    obtained = np.interp(instants - PERIOD / 2, converted["time"], converted["V"])
    assert np.max(np.abs(obtained - expected)) < 1e-6


def test_phasor_is_stamped_at_the_centre_of_its_cycle():
    t = _grid(10000)
    step = 0.25

    amplitude = np.sqrt(2) * np.where(t < step, 1.0, 0.5)

    converted = ensure_rms_signals(_curves(t, _three_phase(t, amplitude)))

    instants = [step - PERIOD / 2, step, step + PERIOD / 2]
    rms = np.interp(instants, converted["time"], converted["V"])
    assert rms == pytest.approx([1.0, 0.75, 0.5], abs=2e-3)


def test_curves_lose_half_a_cycle_at_each_end_and_keep_their_rms_columns():
    t = _grid(1000)
    curves = _curves(t, _three_phase(t), P=np.arange(len(t), dtype=float))

    converted = ensure_rms_signals(curves)

    assert list(converted.columns) == ["V", "time", "P"]
    assert list(converted.index) == list(range(len(t) - 20))
    assert converted["time"].iloc[0] == pytest.approx(t[0] + PERIOD / 2)
    assert converted["time"].iloc[-1] == pytest.approx(t[-1] - PERIOD / 2)
    assert np.array_equal(converted["P"], curves["P"].to_numpy()[10:-10])


def test_irregular_sampling_keeps_its_own_time_stamps():
    t = np.sort(np.concatenate([_grid(2000), _grid(10000)[1::7] + 1e-5]))
    curves = _curves(t, _three_phase(t), P=t)

    converted = ensure_rms_signals(curves)

    first, last = converted["time"].iloc[[0, -1]]
    assert np.array_equal(converted["time"], t[(t >= first) & (t <= last)])
    assert np.array_equal(converted["P"], converted["time"])
    assert first - t[0] == pytest.approx(PERIOD / 2, abs=PERIOD / 40)
    assert t[-1] - last == pytest.approx(PERIOD / 2, abs=PERIOD / 40)
    assert np.max(np.abs(converted["V"] - 1.0)) < 1e-3


def test_irregular_samples_above_the_resampling_frequency_keep_their_own_time_stamps():
    t = np.sort(np.concatenate([_grid(10000), _grid(10000)[1::7] + 1e-5, [0.25, 0.25]]))
    curves = _curves(t, _three_phase(t), P=t)

    converted = ensure_rms_signals(curves)

    inside = t[(t >= t[0] + PERIOD / 2) & (t <= t[-1] - PERIOD / 2)]
    assert np.array_equal(converted["time"], inside)
    assert np.array_equal(converted["P"], inside)
    assert np.max(np.abs(converted["V"] - 1.0)) < 1e-9


def test_curves_without_three_phase_signals_are_returned_as_they_are():
    curves = pd.DataFrame({"time": [0.0, 0.1, 0.2], "V": [1.0, 1.0, 0.9]})

    assert ensure_rms_signals(curves) is curves


@pytest.mark.parametrize(
    "t",
    [_grid(100), _grid(140), np.arange(83) / 4096],
    ids=["too coarse", "under three samples per cycle", "barely one cycle off the grid"],
)
def test_curves_that_cannot_hold_a_fundamental_phasor_are_rejected(t):
    with pytest.raises(ValueError, match="three samples per cycle"):
        ensure_rms_signals(_curves(t, _three_phase(t)))


@pytest.mark.parametrize("sampling_frequency, warned", [(1000, True), (1980, True), (2000, False)])
def test_curves_sampled_below_the_minimum_of_the_dtr_are_warned(
    mocker, sampling_frequency, warned
):
    logger = mocker.MagicMock()
    mocker.patch("dycov.logging.dycov_logging.get_logger", return_value=logger)
    t = _grid(sampling_frequency)

    ensure_rms_signals(_curves(t, _three_phase(t)))

    assert logger.warning.called is warned


def test_resample_to_fixed_step():
    import numpy as np
    import pandas as pd

    from dycov.sigpro.sigpro import resample_to_fixed_step

    # Non-uniform sampling
    t = np.array([0.0, 0.01, 0.021, 0.031, 0.05])
    y = np.sin(t)

    df = pd.DataFrame({"time": t, "y": y})
    out = resample_to_fixed_step(df)

    # Check monotone equal grid
    dt = np.diff(out["time"])
    assert np.allclose(dt, dt[0])

    # PCHIP preserves shape; values should match interpolation
    assert len(out) > len(df)


def test_resample_to_common_tgrid():
    import numpy as np
    import pandas as pd

    from dycov.sigpro.sigpro import resample_to_common_tgrid

    t1 = np.linspace(0, 1, 300)
    t2 = np.linspace(0.1, 1.1, 400)

    df1 = pd.DataFrame({"time": t1, "v": np.sin(t1)})
    df2 = pd.DataFrame({"time": t2, "v": np.sin(t2)})

    rs1, rs2 = resample_to_common_tgrid(df1, df2)

    # Time grids must match
    assert np.allclose(rs1["time"], rs2["time"])
    assert len(rs1) == len(rs2)


def test_filter_curves_basic():
    import numpy as np
    import pandas as pd

    from dycov.sigpro.sigpro import filter_curves

    t = np.linspace(0, 1, 2000)
    # Mix low freq + high freq to verify filtering
    y = np.sin(2 * np.pi * 5 * t) + 0.2 * np.sin(2 * np.pi * 200 * t)

    df = pd.DataFrame({"time": t, "y": y})

    windows = {
        "before": (0, 0.3),
        "during": (0.3, 0.6),
        "after": (0.6, 1.0),
    }

    out = filter_curves(df, windows, f_cutoff=20)

    # time unchanged
    assert np.allclose(out["time"], df["time"])

    # high freq content reduced (RMS drop)
    assert out["y"].std() < df["y"].std()


def test_apply_time_shift():
    import pandas as pd

    from dycov.sigpro.sigpro import apply_time_shift

    t = np.linspace(0, 10, 101)  # 0 → 10 s
    y = np.sin(t)
    curves = pd.DataFrame({"time": t, "signal": y})

    # ---------------------------
    # Case 1: shift is applied
    # ---------------------------
    t_event_curves = 2.0
    t_event_reference = 5.0
    expected_shift = t_event_reference - t_event_curves  # = 3.0

    shifted = apply_time_shift(curves, t_event_curves, t_event_reference)

    assert np.allclose(shifted["time"], t + expected_shift)
    # Validate that the data is untouched
    assert np.allclose(shifted["signal"], curves["signal"])

    # ---------------------------
    # Case 2: shift = 0 → no change
    # ---------------------------
    shifted2 = apply_time_shift(curves, 3.0, 3.0)
    assert np.allclose(shifted2["time"], curves["time"])
    assert np.allclose(shifted2["signal"], curves["signal"])

    # ---------------------------
    # Case 3: event time outside range → error
    # ---------------------------
    try:
        apply_time_shift(curves, -5.0, 1.0)
        assert False, "Expected ValueError for event out of range"
    except ValueError:
        pass

    try:
        apply_time_shift(curves, 20.0, 1.0)
        assert False, "Expected ValueError for event out of range"
    except ValueError:
        pass
