#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The generating units of the plant: one per ``Zone1<x>`` sheet, with the model it resolves to
and the names its blocks and files take in each zone."""

from __future__ import annotations

from dataclasses import dataclass

from dycov.excel import names
from dycov.excel import parse as P
from dycov.excel.producer_dyd import GEN_ID_BY_TECH


@dataclass(frozen=True)
class GeneratingUnit:
    """A generating unit, as DyCoV lays it out.

    Attributes
    ----------
    zone1: dict
        Rows of its ``Zone1<x>`` sheet.
    model: dict
        Libs and prefixes of both zones, as ``parse.resolve_models`` returns them.
    zone1_file: str
        Base name of its own Zone1 files: the producer name, or ``<producer>_G<i>`` when the plant
        has several units, each validated on its own in Zone1.
    gen_id: str
        Id of its block in its Zone1 files, which follows the technology.
    plant_id: str
        Id of its block in Zone3, numbered when the plant has several units.
    """

    zone1: dict
    model: dict
    zone1_file: str
    gen_id: str
    plant_id: str

    @property
    def lv_control(self) -> bool:
        """Whether the converter controls on the low-voltage side of its step-up transformer."""
        return P.is_true(self.zone1.get(names.row("Zone1", "converter_lv_control"), "True"))


def is_multiple(topology: str) -> bool:
    """Whether the topology describes several generating units (the ``M`` family)."""
    return topology.startswith("M")


def _checked_sheets(workbook: dict, topology: str) -> list:
    """The ``Zone1<x>`` sheets, as many as the topology describes units."""
    sheets = P.zone1_sheets(workbook)
    if not sheets:
        raise ValueError("the workbook has no Zone1 sheet: it describes no generating unit.")
    if is_multiple(topology) and len(sheets) == 1:
        raise ValueError(
            f"topology {topology!r} describes several generating units, and the workbook has a "
            f"single Zone1 sheet ({sheets[0]}): duplicate it once per unit."
        )
    if not is_multiple(topology) and len(sheets) > 1:
        raise ValueError(
            f"topology {topology!r} describes a single generating unit, and the workbook has "
            f"{len(sheets)} Zone1 sheets ({', '.join(sheets)}): pick an 'M' topology or keep one."
        )
    return sheets


def _check_common_internal_node(units: list) -> None:
    """Every unit connects at the plant's internal node, so they all declare its voltage."""
    voltages = {P.sheet_of(u.zone1): P.numbers("Zone1", u.zone1)("u_nom") for u in units}
    if len(set(voltages.values())) > 1:
        declared = ", ".join(f"{sheet}: {u_nom:g}" for sheet, u_nom in voltages.items())
        raise ValueError(
            f"the generating units connect at the same internal node, and their Zone1 sheets "
            f"declare different nominal voltages for it ({declared})."
        )


def generating_units(workbook: dict, topology: str, producer_name: str) -> list:
    """The generating units the workbook describes, one per ``Zone1<x>`` sheet.

    Parameters
    ----------
    workbook: dict
        The whole workbook, as ``{sheet name -> grid}``.
    topology: str
        Topology name, as ``producer_dyd.checked_topology`` returns it.
    producer_name: str
        Base name of the input files.

    Returns
    -------
    list
        A ``GeneratingUnit`` per sheet, in workbook order.
    """
    sheets = _checked_sheets(workbook, topology)
    models = P.resolve_unit_models(workbook, sheets)
    multiple = is_multiple(topology)
    units = []
    for number, (sheet, model) in enumerate(zip(sheets, models), start=1):
        gen_id = GEN_ID_BY_TECH[P.technology(model["zone3_lib"])]
        units.append(
            GeneratingUnit(
                zone1=P.parse_zone(workbook, sheet),
                model=model,
                zone1_file=f"{producer_name}_G{number}" if multiple else producer_name,
                gen_id=gen_id,
                plant_id=f"{gen_id}{number}" if multiple else gen_id,
            )
        )
    _check_common_internal_node(units)
    return units
