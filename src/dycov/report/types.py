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
    """Description of a figure to be rendered in reports."""

    name: str
    variables: str | list[dict]
    ylabel: str
    tolerance_band: ToleranceBand | None = None
    frequency_band: FrequencyBand | None = None
    dynamic_band: DynamicBand | None = None
    event_markers: list[EventMarker] = field(default_factory=list)


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
