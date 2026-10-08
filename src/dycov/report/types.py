#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from dataclasses import dataclass, field
from enum import Enum

from dycov.report.curve_classification import is_setpoint


class BandUnit(Enum):
    PERCENT = "percent"
    ABSOLUTE = "absolute"


@dataclass
class ToleranceBand:
    """Base class defining an upper and lower tolerance band."""

    upper: float | None
    lower: float | None


@dataclass
class FinalValueBand(ToleranceBand):
    """Band relative to the last value of the curve (10P, 5P, imax_reac...)"""

    unit: BandUnit = BandUnit.PERCENT
    color: str = "#55a868"


@dataclass
class FrequencyBand(ToleranceBand):
    """Band relative to f_nom, deviation expressed in Hz."""

    pass


@dataclass
class DynamicBand(ToleranceBand):
    """Band relative to each point of an external reference curve (AVR5...)"""

    source_key: str = ""


@dataclass
class EventMarker:
    """Vertical marker at a specific event time."""

    source_key: str


@dataclass
class FigureDescription:
    """Description of a figure to be rendered in reports.

    Every figure goes to the HTML report; ``in_pdf`` says whether it also goes to the PDF.
    ``setpoint`` is the setpoint that drives the magnitude the figure draws, which a test that
    steps it draws over that magnitude. ``in_hz`` says the figure draws a frequency, which the
    tool keeps in pu of f_nom, in Hz.
    """

    name: str
    variables: str | list[dict]
    ylabel: str
    tolerance_band: ToleranceBand | None = None
    frequency_bands: list[FrequencyBand] = field(default_factory=list)
    dynamic_band: DynamicBand | None = None
    event_markers: list[EventMarker] = field(default_factory=list)
    in_pdf: bool = True
    setpoint: str | None = None
    in_hz: bool = False

    def draws_one_magnitude(self) -> bool:
        """Whether the figure draws a single magnitude, the setpoint that drives it aside. Only
        such a figure marks the MXE of its curves: one that draws several repeats the figures of
        each."""
        if isinstance(self.variables, str):
            return True
        return len([v for v in self.variables if not is_setpoint(v["variable"])]) == 1


def band_limits(
    ref_val: float, upper_pct: float | None, lower_pct: float | None
) -> tuple[float | None, float | None]:
    """Calculate the upper and lower limits of a tolerance band based on a reference value and
    percentage values.

    Parameters
    ----------
    ref_val: float
        The reference value.
    upper_pct: float | None
        The upper percentage value.
    lower_pct: float | None
        The lower percentage value.

    Returns
    -------
    tuple[float | None, float | None]
        A tuple containing the upper and lower limits.
    """
    upper = None
    lower = None
    if upper_pct is not None:
        delta = upper_pct / 100.0 if abs(ref_val) <= 1 else abs(upper_pct / 100.0 * ref_val)
        upper = ref_val + delta
    if lower_pct is not None:
        delta = lower_pct / 100.0 if abs(ref_val) <= 1 else abs(lower_pct / 100.0 * ref_val)
        lower = ref_val - delta
    return upper, lower
