#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from collections import namedtuple

Line_params = namedtuple("Line_params", ["id", "lib", "connectedPdr", "R", "X", "B", "G"])
Xfmr_params = namedtuple("Xfmr_params", ["id", "lib", "R", "X", "B", "G", "rTfo", "par_id"])
Load_params = namedtuple("Load_params", ["id", "lib", "connectedXmfr", "P", "Q", "U", "UPhase"])
Gen_params = namedtuple(
    "Gen_params", ["id", "lib", "connectedXmfr", "IMax", "par_id", "P", "Q", "VoltageDrop"]
)
Pdr_equipments = namedtuple("Pdr_equipments", ["id", "var"])
Pdr_params = namedtuple("Pdr_params", ["U", "S", "P", "Q"])
Pimodel_params = namedtuple("Pimodel_params", ["Ytr", "Ysh1", "Ysh2"])
Gen_init = namedtuple("Gen_init", ["id", "P0", "Q0", "U0", "UPhase0"])
Load_init = namedtuple("Load_init", ["id", "lib", "P0", "Q0", "U0", "UPhase0"])

Stability = namedtuple("Stability", ["p", "q", "v", "theta", "pi"])
Disconnection_Model = namedtuple(
    "Disconnection_Model", ["auxload", "auxload_xfmr", "stepup_xfmrs", "gen_intline"]
)
