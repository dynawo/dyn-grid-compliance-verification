#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""PAR set of the auxiliary load."""

from __future__ import annotations

import electrical as el
import parse as P


def aux_par_set(par_id: str, zone3: dict) -> tuple:
    """Build the auxiliary load (``LoadAlphaBeta``).

    Parameters
    ----------
    par_id: str
        Id of the set, matching the load's block in the DYD.
    zone3: dict
        Rows of the ``Zone3`` sheet: ``P_A``/``Q_A`` in MW/MVAr and the voltage exponents.

    Returns
    -------
    tuple
        ``(set id, parameters)``.
    """
    number = P.numbers("Zone3", zone3)
    p_ref, q_ref = el.load_pu(number("aux_p"), number("aux_q"))
    return par_id, [
        {"name": "load_PRefPu", "type": "DOUBLE", "value": p_ref},
        {"name": "load_QRefPu", "type": "DOUBLE", "value": q_ref},
        {"name": "load_alpha", "type": "DOUBLE", "value": number("aux_alpha")},
        {"name": "load_beta", "type": "DOUBLE", "value": number("aux_beta")},
    ]
