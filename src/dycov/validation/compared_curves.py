#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The curves each zone compares against the reference, declared once, and the ones it only draws.

The set was spelled out in six places — the error calculation, the compliance checks, the
threshold lookup, the report table, the required-curve check and the setpoint-tracking target —
and every one of them had to agree. They all read this registry instead.

The curves a zone draws without comparing them are declared apart, so that none of those readers
ever sees them: they are neither required of the reference nor part of the verdict.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

_GENERATOR_SELECTOR = "_GEN_"


@dataclass(frozen=True)
class ComparedCurve:
    """A curve a zone compares, and everything the tool needs to say about it.

    Attributes
    ----------
    selector : str
        The curve's column name, or the suffix that identifies it when the column carries the
        id of the generating unit that produced it.
    label : str
        The name the results are stored under, unique within a zone.
    display : str
        The name the report gives it.
    threshold : str | None
        The ``thr_<threshold>_*`` family that bounds its error, or None when the DTR sets no
        limit on the magnitude.
    """

    selector: str
    label: str
    display: str
    threshold: str | None

    def matches(self, column: str) -> bool:
        """Whether a curve column is this compared curve."""
        if self.selector.startswith(_GENERATOR_SELECTOR):
            return column.endswith(self.selector)
        return column == self.selector


_ZONE_1 = (
    ComparedCurve("BusPDR_BUS_Voltage", "voltage", "V", None),
    ComparedCurve("_GEN_VoltageInjTerminal", "injector_voltage", "V InternalNode2", None),
    ComparedCurve("_GEN_ActivePowerControlledPu", "active_power", "P", "P"),
    ComparedCurve("_GEN_ReactivePowerControlledPu", "reactive_power", "Q", "Q"),
    ComparedCurve("_GEN_ActiveCurrentInjTerminal", "active_current", "$I_p$", "Ip"),
    ComparedCurve("_GEN_ReactiveCurrentInjTerminal", "reactive_current", "$I_q$", "Iq"),
)

_ZONE_3 = (
    ComparedCurve("BusPDR_BUS_Voltage", "voltage", "V", None),
    ComparedCurve("BusPDR_BUS_ActivePower", "active_power", "P", "P"),
    ComparedCurve("BusPDR_BUS_ReactivePower", "reactive_power", "Q", "Q"),
    ComparedCurve("BusPDR_BUS_ActiveCurrent", "active_current", "$I_p$", "Ip"),
    ComparedCurve("BusPDR_BUS_ReactiveCurrent", "reactive_current", "$I_q$", "Iq"),
    ComparedCurve("NetworkFrequencyPu", "frequency", r"$\omega$", None),
)

_BY_ZONE = {1: _ZONE_1, 3: _ZONE_3}


@dataclass(frozen=True)
class DrawnCurve:
    """A curve a zone draws in the report without comparing it against the reference.

    Attributes
    ----------
    selector : str
        The curve's column name, or the suffix that identifies it when the column carries the
        id of the generating unit that produced it.
    label : str
        The name a figure asks for it by, unique within a zone.
    """

    selector: str
    label: str


_ZONE_1_DRAWN = (
    DrawnCurve("BusPDR_BUS_ActivePower", "internal_node1_active_power"),
    DrawnCurve("BusPDR_BUS_ReactivePower", "internal_node1_reactive_power"),
)

_DRAWN_BY_ZONE = {1: _ZONE_1_DRAWN}


@dataclass(frozen=True)
class DrawnSetpoint:
    """A setpoint a zone draws over the magnitude it drives, in the test that steps it.

    Attributes
    ----------
    name : str
        The setpoint's variable, which its column names after the id of the generating unit.
    test_type : str
        The ``setpoint_change_test_type`` of the test that steps it.
    drives : str
        The label of the curve it drives when the converter controls InternalNode1.
    drives_at_internal_node2 : str
        The label of the curve it drives when the converter controls InternalNode2.
    asked : bool
        Whether the zone asks the producer for it. The workbook of the TSO asks for no voltage
        setpoint in Zone 1, and the curves of a producer name their generating units by theirs.
    """

    name: str
    test_type: str
    drives: str
    drives_at_internal_node2: str
    asked: bool

    def driven_label(self, controls_internal_node2: bool) -> str:
        """The label of the curve the setpoint drives, given the node the converter controls."""
        return self.drives_at_internal_node2 if controls_internal_node2 else self.drives


_ZONE_1_SETPOINTS = (
    DrawnSetpoint("ActivePowerSetpointPu", "PSetpoint", "active_power", "active_power", True),
    DrawnSetpoint(
        "ReactivePowerSetpointPu", "QSetpoint", "reactive_power", "reactive_power", True
    ),
    DrawnSetpoint("VoltageSetpointPu", "USetpoint", "voltage", "injector_voltage", False),
)

_DRAWN_SETPOINTS_BY_ZONE = {1: _ZONE_1_SETPOINTS}


def for_zone(zone: int) -> tuple[ComparedCurve, ...]:
    """The curves a zone compares, in report order."""
    return _BY_ZONE.get(zone, _ZONE_3)


def every_curve() -> tuple[ComparedCurve, ...]:
    """Every compared curve of every zone, each label once, in report order."""
    seen, curves = set(), []
    for curve in _ZONE_1 + _ZONE_3:
        if curve.label not in seen:
            seen.add(curve.label)
            curves.append(curve)
    return tuple(curves)


def resolve(zone: int, columns: Iterable[str]) -> list[tuple[ComparedCurve, str]]:
    """Pair each compared curve of a zone with the columns that carry it."""
    available = list(columns)
    return [
        (curve, column)
        for curve in for_zone(zone)
        for column in available
        if curve.matches(column)
    ]


_SETPOINT_LABELS = {
    "ActivePowerSetpointPu": "active_power",
    "ReactivePowerSetpointPu": "reactive_power",
    "VoltageSetpointPu": "voltage",
    "NetworkFrequencyPu": "frequency",
}


def in_zone(zone: int, label: str) -> ComparedCurve | None:
    """The curve a zone compares under a label."""
    return next((curve for curve in for_zone(zone) if curve.label == label), None)


def in_column(zone: int, column: str) -> ComparedCurve | None:
    """The curve a zone compares in a column, or None when the column carries none of them."""
    return next((curve for curve in for_zone(zone) if curve.matches(column)), None)


def column_of(zone: int, label: str, columns: Iterable[str]) -> str | None:
    """The column that carries a zone's compared curve, or None when no column does."""
    curve = in_zone(zone, label)
    if curve is None:
        return None
    return next((column for column in columns if curve.matches(column)), None)


def setpoint_label(modified_setpoint: str) -> str:
    """The label of the magnitude a setpoint drives, the reactive power for an unknown one, as
    the tool has always done."""
    return _SETPOINT_LABELS.get(modified_setpoint, "reactive_power")


def asked_setpoints(zone: int) -> tuple[str, ...]:
    """The setpoints a zone asks the producer for, which it draws without comparing them."""
    return tuple(
        setpoint.name for setpoint in _DRAWN_SETPOINTS_BY_ZONE.get(zone, ()) if setpoint.asked
    )


def setpoint_driving(zone: int, label: str, controls_internal_node2: bool) -> str | None:
    """The setpoint a zone draws over the curve it compares under a label, given the node the
    converter controls, or None when it draws none there."""
    return next(
        (
            setpoint.name
            for setpoint in _DRAWN_SETPOINTS_BY_ZONE.get(zone, ())
            if setpoint.driven_label(controls_internal_node2) == label
        ),
        None,
    )


def setpoint_stepped_by(zone: int, test_type: str | None) -> str | None:
    """The setpoint a zone draws that a test of a ``setpoint_change_test_type`` steps, or None
    when the test steps none of them."""
    return next(
        (
            setpoint.name
            for setpoint in _DRAWN_SETPOINTS_BY_ZONE.get(zone, ())
            if setpoint.test_type == test_type
        ),
        None,
    )


def for_setpoint(zone: int, modified_setpoint: str, columns: Iterable[str]) -> str:
    """The column a setpoint step is tracked on: the magnitude the setpoint drives, in this zone.

    Falls back to the selector itself when no column carries it, so the caller reports it as not
    computable.
    """
    label = setpoint_label(modified_setpoint)
    curve = in_zone(zone, label)
    if curve is None:
        return modified_setpoint
    return column_of(zone, label, columns) or curve.selector


def resolve_all(zone: int, columns: Iterable[str]) -> list[tuple[ComparedCurve, str]]:
    """Every compared curve of a zone, paired with the column that carries it.

    A curve no column carries is paired with its own selector, so the checks still report it as
    not computable instead of leaving its results out altogether.
    """
    available = list(columns)
    resolved = []
    for curve in for_zone(zone):
        carried = [column for column in available if curve.matches(column)]
        resolved.extend((curve, column) for column in carried or [curve.selector])
    return resolved


def matches_column(selector: str, column: str) -> bool:
    """Whether a curve column is the one a selector identifies."""
    if selector.startswith(_GENERATOR_SELECTOR):
        return column.endswith(selector)
    return column == selector


def curve_names(zone: int, generator_ids: Iterable[str]) -> list[str]:
    """The name of every curve a zone compares, one per generating unit where it belongs.

    These are the internal names; the reference dictionaries the user fills spell the bus the
    way the zone's outputs do, so the caller renames them with ``curves.naming``.
    """
    names = []
    for curve in for_zone(zone):
        if curve.selector.startswith(_GENERATOR_SELECTOR):
            names.extend(f"{generator_id}{curve.selector}" for generator_id in generator_ids)
        else:
            names.append(curve.selector)
    return names


def _drawn_in_zone(zone: int, label: str) -> DrawnCurve | None:
    return next((curve for curve in _DRAWN_BY_ZONE.get(zone, ()) if curve.label == label), None)


def plot_variables(zone: int, label: str):
    """The ``variables`` a report figure needs to draw the curve a zone compares or only draws
    under a label, or None when the zone has no curve under it.

    A curve of the generating unit is drawn for every unit the curves carry, so it is named by
    its suffix; one of the bus is a single column, named in full.
    """
    curve = in_zone(zone, label) or _drawn_in_zone(zone, label)
    if curve is None:
        return None
    if curve.selector.startswith(_GENERATOR_SELECTOR):
        return [{"type": "generator", "variable": curve.selector[len(_GENERATOR_SELECTOR) :]}]
    return curve.selector


def by_label(label: str) -> ComparedCurve | None:
    """The compared curve stored under a label, from any zone."""
    for curve in every_curve():
        if curve.label == label:
            return curve
    return None


def threshold_of(column: str) -> str | None:
    """The ``thr_<name>_*`` family that bounds a curve's error, or None when it has no limit.

    Every zone is searched, because a curve's limit does not depend on the zone that compares it.
    """
    for curve in _ZONE_1 + _ZONE_3:
        if curve.matches(column):
            return curve.threshold
    return None
