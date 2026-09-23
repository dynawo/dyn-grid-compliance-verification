#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The curves a zone asks a producer for, declared once.

Two places need the same list: the dictionary the tool scaffolds for the user to fill in, and
the one the anonymizer writes beside a curve file it produces. They read it here, so a curve
added to a zone reaches both.
"""

from __future__ import annotations

from typing import Iterable

from dycov.curves import naming
from dycov.validation import compared_curves

# Asked for whatever the zone is, and declared apart from the curves of the zone itself.
COMMON = ("time", "NetworkFrequencyPu")

_ZONE_3_BUS = (
    "BusPDR_BUS_Voltage",
    "BusPDR_BUS_ActivePower",
    "BusPDR_BUS_ReactivePower",
    "BusPDR_BUS_ActiveCurrent",
    "BusPDR_BUS_ReactiveCurrent",
)

_ZONE_3_GENERATOR = (
    "VoltageInjTerminal",
    "ActiveCurrentInjTerminal",
    "ReactiveCurrentInjTerminal",
    "MagnitudeControlledByAVRPu",
    "VoltageSetpointPu",
)


def for_zone(
    zone: int,
    generator_ids: Iterable[str],
    transformer_ids: Iterable[str] = (),
) -> list[str]:
    """The curves a zone asks for, named as the producer's own files name them.

    Parameters
    ----------
    zone : int
        The zone the curves are asked for, 1 or 3.
    generator_ids : Iterable[str]
        The generating units the producer declares.
    transformer_ids : Iterable[str]
        The transformers whose tap is recorded; only Zone 3 asks for any.

    Returns
    -------
    list of str
        The curve names, in the order the dictionary declares them.
    """
    if zone == 1:
        return [
            naming.to_output_name(name, 1)
            for name in compared_curves.curve_names(1, generator_ids)
        ]

    requested = list(_ZONE_3_BUS)
    requested += [f"{transformer_id}_XFMR_Tap" for transformer_id in transformer_ids]
    for generator_id in generator_ids:
        requested += [f"{generator_id}_GEN_{name}" for name in _ZONE_3_GENERATOR]
    return requested


def every_name(
    zone: int,
    generator_ids: Iterable[str],
    transformer_ids: Iterable[str] = (),
) -> list[str]:
    """Every curve a zone asks for, the common ones included, for a single-section dictionary."""
    return list(COMMON) + for_zone(zone, generator_ids, transformer_ids)


def _generator_suffixes(zone: int) -> tuple[str, ...]:
    if zone == 1:
        return tuple(
            curve.selector for curve in compared_curves.for_zone(1) if "_GEN_" in curve.selector
        )
    return tuple(f"_GEN_{name}" for name in _ZONE_3_GENERATOR)


def _prefixes(columns: Iterable[str], suffixes: Iterable[str]) -> list[str]:
    """The equipment a curve set names, in the order it first names them."""
    found = []
    for column in columns:
        for suffix in suffixes:
            if column.endswith(suffix):
                prefix = column[: -len(suffix)]
                if prefix and prefix not in found:
                    found.append(prefix)
    return found


def compared_for_columns(zone: int, columns: Iterable[str]) -> list[str]:
    """The curves a zone compares against the reference, of everything it asks for.

    These are the ones whose absence costs something: the rest are asked for so the user can
    supply them, but no check reads them.
    """
    generator_ids = _prefixes(list(columns), _generator_suffixes(zone))
    return [
        naming.to_output_name(name, zone)
        for name in compared_curves.curve_names(zone, generator_ids)
    ]


def for_columns(zone: int, columns: Iterable[str]) -> list[str]:
    """Every curve a zone asks of the equipment a curve set already shows.

    A generating unit is recognised by carrying one of the curves the zone asks of it, so a
    synchronous compensator, which shares the ``_GEN_`` infix but none of those curves, is not
    mistaken for one.
    """
    columns = list(columns)
    return every_name(
        zone,
        _prefixes(columns, _generator_suffixes(zone)),
        _prefixes(columns, ("_XFMR_Tap",)),
    )
