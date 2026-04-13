#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SimulationError(IntEnum):
    FAULT_SIMULATION_FAILS = 1
    FAULT_DIP_UNACHIEVABLE = 2


class CurvesAvailability(IntEnum):
    ALL = 0
    NO_PRODUCER = 1
    NO_REFERENCE = 2
    NONE = 3


# ---------------------------------------------------------------------------
# Network model dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Terminal:
    connected_equipment: str
    u0: float = 1.0
    u_phase0: float = 0.0
    p0: float = 0.0
    q0: float = 0.0


@dataclass
class Equipment:
    id: str
    lib: str
    par_id: str
    terminals: tuple[Terminal, ...]


@dataclass
class BusParams(Equipment):
    v_min: float
    v_max: float


@dataclass
class LineParams(Equipment):
    r: float
    x: float
    b: float
    g: float


@dataclass
class XfmrParams(Equipment):
    r: float
    x: float
    b: float
    g: float
    r_tfo: float
    alpha_tfo: float


@dataclass
class LoadParams(Equipment):
    p: float
    q: float
    u: float
    u_phase: float
    alpha: float
    beta: float


@dataclass
class GenParams(Equipment):
    s_nom: float
    i_max: float
    p: float
    q: float
    voltage_droop: float
    use_voltage_droop: bool
    ppc_local: bool = True
    p_min: Optional[float] = None
    p_max: Optional[float] = None
    q_min: Optional[float] = None
    q_max: Optional[float] = None


# ---------------------------------------------------------------------------
# Simulation / validation result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PdrEquipments:
    id: str
    var: str


@dataclass
class PdrParams:
    u: float
    u_phase: float
    s: float
    p: float
    q: float


@dataclass(frozen=True)
class PimodelParams:
    y_tr: float
    y_sh1: float
    y_sh2: float


@dataclass(frozen=True)
class GenInit:
    id: str
    p0: float
    q0: float
    u0: float
    u_phase0: float


@dataclass(frozen=True)
class LoadInit:
    id: str
    lib: str
    p0: float
    q0: float
    u0: float
    u_phase0: float


@dataclass(frozen=True)
class SimulationResult:
    success: bool
    time_exceeds: bool
    has_simulated_curves: bool
    error: Optional[SimulationError] = None


@dataclass(frozen=True)
class Stability:
    p: float
    q: float
    v: float
    theta: float
    pi: float


@dataclass(frozen=True)
class DisconnectionModel:
    auxload: object
    auxload_xfmr: object
    stepup_xfmrs: object
    gen_intline: object


@dataclass(frozen=True)
class ExclusionWindows:
    event_start: float
    event_end: float
    clear_start: float
    clear_end: float


@dataclass(frozen=True)
class CurvesCheckResult:
    working_oc_dir: Path
    jobs_output_dir: Path
    event_params: dict
    simulation_result: SimulationResult
    availability: CurvesAvailability
