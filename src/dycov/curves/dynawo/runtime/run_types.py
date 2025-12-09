#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Literal, Optional


@dataclass
class DynawoRunInputs:
    pcs_name: str
    launcher_dwo: Path
    curves_dict: dict[str, Any]
    generators: List[Any]
    s_nom: float
    s_nref: float


@dataclass
class SolverParams:
    solver_id: Literal["IDA", "SIM"]
    solver_lib: str
    minimum_time_step: float
    minimal_acceptable_step: float
    absAccuracy: float
    relAccuracy: Optional[float]  # None for SIM
