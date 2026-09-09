#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""PAR set of the internal network line (the aggregated collector)."""

from __future__ import annotations

import electrical as el
import parse as P


def collector_par_set(par_id: str, zone3: dict) -> tuple:
    """Build the aggregated collector of the ``+i`` topologies (``Line``).

    Its rows carry no voltage of their own, and the block connects to the PDR with no transformer
    in between, so the per-unit base is ``Un_PDR``.

    Parameters
    ----------
    par_id: str
        Id of the set, matching the line's block in the DYD.
    zone3: dict
        Rows of the ``Zone3`` sheet: ``R_rc``/``X_rc`` in ohms and ``B_rc``/``G_rc`` in siemens.

    Returns
    -------
    tuple
        ``(set id, parameters)``.
    """
    number = P.numbers("Zone3", zone3)
    line = el.line_impedance(
        number("collector_r"),
        number("collector_x"),
        number("collector_b"),
        number("collector_g"),
        number("u_nom"),
    )
    return par_id, [
        {"name": "line_RPu", "type": "DOUBLE", "value": line["RPu"]},
        {"name": "line_XPu", "type": "DOUBLE", "value": line["XPu"]},
        {"name": "line_BPu", "type": "DOUBLE", "value": line["BPu"]},
        {"name": "line_GPu", "type": "DOUBLE", "value": line["GPu"]},
    ]
