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
from dataclasses import dataclass


@dataclass
class Terminal:
    connectedEquipment: str
    U0: float = 1.0
    UPhase0: float = 0.0
    P0: float = 0.0
    Q0: float = 0.0


@dataclass
class Equipment:
    id: str
    lib: str
    par_id: str
    terminals: tuple[Terminal, ...]


@dataclass
class Bus_params(Equipment):
    VMin: float
    VMax: float


@dataclass
class Line_params(Equipment):
    R: float
    X: float
    B: float
    G: float


@dataclass
class Xfmr_params(Equipment):
    R: float
    X: float
    B: float
    G: float
    rTfo: float


@dataclass
class Load_params(Equipment):
    P: float
    Q: float
    U: float
    UPhase: float
    Alpha: float
    Beta: float


@dataclass
class Gen_params(Equipment):
    SNom: float
    IMax: float
    P: float
    Q: float
    VoltageDroop: float
    UseVoltageDroop: bool


Pdr_equipments = namedtuple("Pdr_equipments", ["id", "var"])
Pdr_params = namedtuple("Pdr_params", ["U", "S", "P", "Q"])
Pimodel_params = namedtuple("Pimodel_params", ["Ytr", "Ysh1", "Ysh2"])
Gen_init = namedtuple("Gen_init", ["id", "P0", "Q0", "U0", "UPhase0"])
Load_init = namedtuple("Load_init", ["id", "lib", "P0", "Q0", "U0", "UPhase0"])

Simulation_result = namedtuple(
    "Simulation_result", ["success", "time_exceeds", "has_simulated_curves", "error_message"]
)
Stability = namedtuple("Stability", ["p", "q", "v", "theta", "pi"])
Disconnection_Model = namedtuple(
    "Disconnection_Model", ["auxload", "auxload_xfmr", "stepup_xfmrs", "gen_intline"]
)
ExclusionWindows = namedtuple(
    "ExclusionWindows",
    ["event_start", "event_end", "clear_start", "clear_end"],
)
