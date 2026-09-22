#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The PAR: one module per kind of equipment, plus the control sheets it also carries.

Every equipment builder is pure: it reads the rows of a zone sheet and returns
``(set id, parameters)``, leaving the writing to ``dycov.files.producer_par_file``.
"""

from .control import control_params, empty_zone1_reason
from .control import for_zone as control_params_for_zone
from .converter import par_set as converter_par_set
from .lines import collector_par_set as collector_line_par_set
from .loads import aux_par_set as aux_load_par_set
from .transformers import aux_par_set as aux_transformer_par_set
from .transformers import group_par_set as group_transformer_par_set
from .transformers import main_par_set as main_transformer_par_set

__all__ = [
    "control_params",
    "control_params_for_zone",
    "empty_zone1_reason",
    "converter_par_set",
    "group_transformer_par_set",
    "main_transformer_par_set",
    "aux_transformer_par_set",
    "aux_load_par_set",
    "collector_line_par_set",
]
