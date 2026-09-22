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
