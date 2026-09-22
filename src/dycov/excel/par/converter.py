#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""PAR set of the generating unit (the WECC/IEC converter model)."""

from __future__ import annotations

from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.excel import electrical as el
from dycov.excel import names
from dycov.excel import parse as P

# The impedance between the converter and its transformer, as the series pair and the shunt one.
# Which parameter each model keeps them in — and whether it has a shunt at all — is what the
# Dynawo dictionary says, so a family that spells them differently is an entry there.
_TRANSFORMER_CONCEPTS = (
    "TransformerResistance",
    "TransformerReactance",
    "TransformerConductance",
    "TransformerSusceptance",
)


def _transformer_params(lib: str, zone1: dict, lv_control: bool, plant: bool) -> list:
    """The impedance between the converter and its transformer, where this model keeps it.

    The unit reads it only when the converter controls on the MV side; with LV control its own
    transformer is the external block instead, so the branch is zeroed. No model gives these a
    default value, so they are written either way. The workbook describes no shunt, so a model
    that has one takes it as zero.
    """
    number = P.numbers("Zone1", zone1)
    series = el.short_circuit_rx(number("group_impedance"), number("group_rx_ratio"))
    if not plant and lv_control:
        series = (0, 0)
    values = list(series) + [0, 0]

    params = []
    for concept, value in zip(_TRANSFORMER_CONCEPTS, values):
        _sign, name = dynawo_translator.get_dynawo_variable(lib, concept)
        if name:
            params.append({"name": name, "type": "DOUBLE", "value": value})
    if not params:
        raise ValueError(
            f"the Dynawo dictionary does not say where '{lib}' keeps the transformer between the "
            f"converter and its terminal: add its {_TRANSFORMER_CONCEPTS[0]} entry."
        )
    return params


def par_set(
    par_id: str,
    prefix: str,
    control_params: list,
    zone1: dict,
    s_nom,
    lib: str,
    plant_model: bool = False,
) -> tuple:
    """Build the converter's parameter set.

    The group transformer is the only one the workbook describes for the unit, and the model reads
    it on its own ``SNom``, so ``Z_cc_TG`` (base ``SnZone1``) needs no rebase: it is already the
    right pu in Zone1, and in Zone3 aggregating N of them onto ``SnZone3 = N x SnZone1`` gives the
    same number. In Zone1 with ``ConverterLVControl = true`` the model zeroes this branch and the
    external block carries the transformer instead.

    Parameters
    ----------
    par_id: str
        Id of the set, matching the generator's block in the DYD.
    prefix: str
        Model prefix every parameter name takes (e.g. ``photovoltaics_``).
    control_params: list
        Control parameters of the blocks that declare this zone, in workbook order.
    zone1: dict
        Rows of the ``Zone1a`` sheet, which describe the unit whichever zone is emitted.
    s_nom: str or float
        Nominal apparent power of the model: ``SnZone1`` in Zone1, ``SnZone3`` in Zone3.
    lib: str
        Resolved model class, which decides the names the transformer parameters take.
    plant_model: bool
        True for the Zone3 plant model, which adds ``PPCLocal``; the turbine models lack it.

    Returns
    -------
    tuple
        ``(set id, parameters)``, the parameters as dicts of name/type/value/comments.
    """
    params = [{**p, "name": f"{prefix}{p['name']}"} for p in control_params]
    if plant_model:
        params.append(
            {
                "name": f"{prefix}PPCLocal",
                "type": "BOOL",
                "value": "false",
                "comments": ["Plant control"],
            }
        )
    lv_control = P.is_true(zone1.get(names.row("Zone1", "converter_lv_control"), "True"))
    params.append(
        {
            "name": f"{prefix}ConverterLVControl",
            "type": "BOOL",
            "value": str(lv_control).lower(),
            "comments": ["LV Transformer"],
        }
    )
    params += _transformer_params(lib, zone1, lv_control, plant_model)
    params.append(
        {"name": f"{prefix}SNom", "type": "DOUBLE", "value": float(s_nom), "comments": ["General"]}
    )
    return par_id, params
