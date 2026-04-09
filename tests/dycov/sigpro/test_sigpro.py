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

from dycov.sigpro.sigpro import _abc_to_psrms, _shortfft

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
        f, t, Zxx = _shortfft(x, fs)
        assert f is not None
        assert t is not None
        assert Zxx is not None

        idx = np.argmin(np.abs(f - 50))
        assert idx is not None


def test_abc_to_psrms():
    abc, fs, _ = gen_abc(300)
    ps_rms = _abc_to_psrms(abc, fs)
    assert ps_rms is not None


def test_ensure_rms_signals():
    import numpy as np
    import pandas as pd

    from dycov.sigpro.sigpro import ensure_rms_signals

    t = np.linspace(0, 0.02, 200)
    wt = 2 * np.pi * 50 * t
    Va = np.sin(wt)
    Vb = np.sin(wt - 2 * np.pi / 3)
    Vc = np.sin(wt + 2 * np.pi / 3)

    df = pd.DataFrame({"time": t, "Va_a": Va, "Va_b": Vb, "Va_c": Vc})

    out = ensure_rms_signals(df)

    assert "Va" in out.columns
    assert len(out["Va"]) == len(t)

    # Ensure RMS is positive and in a reasonable STFT‑based range
    val = np.max(out["Va"])
    assert 0.05 < val < 0.2


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

    # Create simple synthetic curve
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

    # Validate shift
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
