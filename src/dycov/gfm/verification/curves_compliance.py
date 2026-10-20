#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Compliance of the producer curves of a Grid Forming test, as the DTR Fiche I18 defines it.

The producer delivers the RMS active and reactive currents, and the voltage, at the PGU
terminals. Once filtered, the current the envelope bounds must stay inside it, and no oscillation
of the currents or of the voltage between ``damping_f_min`` and ``damping_f_max`` may be damped
less than ``thr_damping_ratio``.
"""

from collections import namedtuple
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from dycov.configuration.cfg import config
from dycov.curves.importer.importer import CurvesImporter
from dycov.files import manage_files
from dycov.logging import dycov_logging
from dycov.model.compliance import Compliance
from dycov.sigpro import matrix_pencil, signal_windows, sigpro

# The producer curve of each magnitude: the envelope bounds one of the currents and the damping
# of all of them is checked, the voltage only when the producer delivers it
_CURVES = {
    "Ip": "BusPDR_BUS_ActiveCurrent",
    "Iq": "BusPDR_BUS_ReactiveCurrent",
    "U": "BusPDR_BUS_Voltage",
}
_REQUIRED_MAGNITUDES = ("Ip", "Iq")
# The PGU terminals are the Node 1 of the Zone 1 of the DTR, so the curves may also be named
# after the Zone 1 bus (InternalNode1_BUS_*), which the importer translates for this zone
_PGU_ZONE = 1
# The windows between the event discontinuities that may show oscillations
_DAMPED_WINDOWS = ("during", "after")

EnvelopeCheck = namedtuple("EnvelopeCheck", ["within", "max_excess", "t_from", "t_to"])
DampedMode = namedtuple(
    "DampedMode", ["curve", "window", "frequency", "damping_ratio", "amplitude"]
)
CurvesCheck = namedtuple("CurvesCheck", ["compliance", "signal", "envelope", "modes"])


def check(
    curves_path: Path,
    working_path: Path,
    test_name: str,
    magnitude: str,
    time_array: np.ndarray,
    event_time: float,
    event_duration: float,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
) -> CurvesCheck:
    """Checks the producer curves of a test against its envelope and the damping criterion.

    Parameters
    ----------
    curves_path: Path
        Directory of the producer curves, holding a CurvesFiles.ini and, for each test, a curve
        file named after the test with its DICT file.
    working_path: Path
        Working directory of the test, where the curve files are copied to be read.
    test_name: str
        Name of the test, '<PCS>.<benchmark>.<operating condition>'.
    magnitude: str
        Magnitude the envelope bounds, 'Ip' or 'Iq'.
    time_array: np.ndarray
        Time values of the envelope.
    event_time: float
        Time of the event in the envelope.
    event_duration: float
        Duration of the event, 0 for an event made of a single step.
    lower_envelope: np.ndarray
        Lower envelope.
    upper_envelope: np.ndarray
        Upper envelope.

    Returns
    -------
    CurvesCheck
        The compliance of the test, the filtered producer curve on the time values of the
        envelope (NaN where the curve does not reach), the envelope check and every oscillating
        mode found.

    Raises
    ------
    ValueError
        If the event time declared by the producer lies outside its curves.
    """
    logger = dycov_logging.get_logger("GFMCompliance")
    curves = _read_producer_curves(curves_path, working_path, test_name, event_time)
    if curves is None:
        logger.warning(f"No producer curves for the test in '{curves_path}'")
        return CurvesCheck(Compliance.WithoutProducerCurves, None, None, [])

    missing = [_CURVES[name] for name in _REQUIRED_MAGNITUDES if _CURVES[name] not in curves]
    if missing:
        logger.warning(f"The producer curves of the test miss {', '.join(missing)}")
        return CurvesCheck(Compliance.WithoutProducerCurves, None, None, [])

    curves = sigpro.resample_to_fixed_step(curves)
    windows = signal_windows.filter_windows(list(curves["time"]), event_time, event_duration)
    curves = sigpro.filter_curves(curves, windows, config.get_float("GFM", "cutoff", 30.0))

    signal = _on_envelope_time(curves, _CURVES[magnitude], time_array)
    envelope = _check_envelope(time_array, signal, lower_envelope, upper_envelope)
    modes = _damped_modes(curves, windows)

    thr_damping_ratio = config.get_float("GFM", "thr_damping_ratio", 0.40)
    is_damped = all(mode.damping_ratio >= thr_damping_ratio for mode in modes)
    compliance = Compliance.Compliant if envelope.within and is_damped else Compliance.NonCompliant
    return CurvesCheck(compliance, signal, envelope, modes)


def _read_producer_curves(
    curves_path: Path, working_path: Path, test_name: str, event_time: float
) -> Optional[pd.DataFrame]:
    """The producer curves of the test, shifted so that the event they declare happens at the
    event time of the envelope; None when the producer delivers none for the test."""
    if not manage_files.copy_base_curves_files(curves_path, working_path, test_name):
        return None

    importer = CurvesImporter(working_path, test_name)
    curves = importer.get_curves_dataframe(_PGU_ZONE)
    if curves.empty:
        return None
    return sigpro.apply_time_shift(
        curves,
        t_event_curves=importer.metadata.get_float("sim_t_event_start"),
        t_event_reference=event_time,
    )


def _on_envelope_time(curves: pd.DataFrame, curve: str, time_array: np.ndarray) -> np.ndarray:
    """The curve at the time values of the envelope, NaN outside the time the curve covers."""
    time = curves["time"].to_numpy()
    return np.interp(time_array, time, curves[curve].to_numpy(), left=np.nan, right=np.nan)


def _check_envelope(
    time_array: np.ndarray,
    signal: np.ndarray,
    lower_envelope: np.ndarray,
    upper_envelope: np.ndarray,
) -> EnvelopeCheck:
    """Whether the curve stays inside the envelope over the time both cover."""
    covered = ~np.isnan(signal)
    if not covered.any():
        return EnvelopeCheck(False, None, None, None)

    # Depending on the direction of the event the calculators deliver the two bounds in either
    # order, the envelope being what lies between them
    lower = np.minimum(lower_envelope, upper_envelope)[covered]
    upper = np.maximum(lower_envelope, upper_envelope)[covered]
    excess = np.maximum(lower - signal[covered], signal[covered] - upper)
    max_excess = max(float(np.max(excess)), 0.0)
    tolerance = config.get_float("GFM", "envelope_tolerance", 0.005)
    return EnvelopeCheck(
        within=max_excess <= tolerance,
        max_excess=max_excess,
        t_from=float(time_array[covered][0]),
        t_to=float(time_array[covered][-1]),
    )


def _damped_modes(curves: pd.DataFrame, windows: dict) -> list[DampedMode]:
    """The oscillating modes of every checked curve, window by window after the event."""
    f_min = config.get_float("GFM", "damping_f_min", 0.1)
    f_max = config.get_float("GFM", "damping_f_max", 10.0)
    min_amplitude = config.get_float("GFM", "damping_min_amplitude", 0.001)
    time = curves["time"].to_numpy()

    modes = []
    for magnitude, curve in _CURVES.items():
        if curve not in curves:
            continue
        for window in _DAMPED_WINDOWS:
            t_from, t_to = windows[window]
            selected = (time >= t_from) & (time <= t_to)
            modes += [
                DampedMode(magnitude, window, mode.frequency, mode.damping_ratio, mode.amplitude)
                for mode in matrix_pencil.oscillation_modes(
                    time[selected], curves[curve].to_numpy()[selected], f_min, f_max, min_amplitude
                )
            ]
    return modes
