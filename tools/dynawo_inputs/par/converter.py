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

import electrical as el
import parse as P

from .common import number_of


def par_set(
    par_id: str,
    prefix: str,
    control_params: list,
    zone1: dict,
    s_nom,
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
            {"name": f"{prefix}PPCLocal", "type": "BOOL", "value": "false",
             "comments": ["Plant control"]}
        )
    lv_control = P.is_true(zone1.get("ConverterLVControl", "True"))
    params.append(
        {"name": f"{prefix}ConverterLVControl", "type": "BOOL",
         "value": str(lv_control).lower(), "comments": ["LV Transformer"]}
    )
    number = number_of(zone1)
    r_pu, x_pu = el.short_circuit_rx(number("Z_cc_TG"), number("R_cc_TG / X_cc_TG"))
    params += [
        {"name": f"{prefix}RLvTrPu", "type": "DOUBLE", "value": r_pu},
        {"name": f"{prefix}XLvTrPu", "type": "DOUBLE", "value": x_pu},
    ]
    params.append(
        {"name": f"{prefix}SNom", "type": "DOUBLE", "value": float(s_nom),
         "comments": ["General"]}
    )
    return par_id, params
