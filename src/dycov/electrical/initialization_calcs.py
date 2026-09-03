#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import cmath
from itertools import zip_longest
from math import sqrt

from dycov.electrical.pimodel_parameters import line_pimodel, xfmr_pimodel
from dycov.model import parameters as mp

PDR_IDS = ("Measurements", "BusPDR")


def init_calcs(
    gens: tuple[mp.GenParams, ...],
    gen_xfmrs: tuple[mp.XfmrParams, ...],
    aux_load: mp.LoadParams,
    auxload_xfmr: mp.XfmrParams,
    main_xfmr: mp.XfmrParams,
    int_line: mp.LineParams,
    pdr: mp.PdrParams,
    grid_line: mp.PimodelParams,
    grid_load: mp.LoadParams,
    pdr_load: mp.LoadParams = None,
) -> mp.GenInit:
    """Calculates initialization parameters for generators.

    Calculates initialization parameters for the producer's
    generators, and also for the generator on the network side when it
    is not modeled as an infinite bus.

    Calculations explained in: doc/initialization/generator_initialization.pdf

    Parameters
    ----------
    gens: tuple
        Params of the producer's generating units
    gen_xfmrs: tuple
        Params of their step-up transformers (a tuple)
    aux_load: LoadParams
        Params of the auxiliary load (if present)
    auxload_xfmr: XfmrParams
        Params of the auxiliary load transformer (if present)
    main_xfmr: XfmrParams
        Params of the plant transformer (if present)
    int_line: LineParams
        Params of the "internal network" line (if present)
    pdr: PdrParams
        Params at the PDR bus (U, S)
    grid_line: PimodelParams
        Params of the equiv line on the grid side (zero-impedance if not used)
    grid_load: LoadParams
        Params of the equiv load on the grid side (if not Inf Bus, as in Pcs I8)
    pdr_load: LoadParams
        Params of the equiv load hanging directly from the PDR bus (as in the
        Islanding PCS); it consumes part of the producer's delivery before it
        enters the grid line

    Returns
    -------
    GenInit
        Params for the initialization of TSO's bus side (P, Q, U, angle)
    """

    v_pdr, grid_init = _solve_grid_side(pdr, grid_line, grid_load, pdr_load)

    v_node, s_node, node_ids = _solve_int_line(int_line, v_pdr, pdr.s, PDR_IDS)
    v_node, s_node, node_ids = _solve_main_xfmr(main_xfmr, v_node, s_node, node_ids)
    s_node = _solve_aux_branch(aux_load, auxload_xfmr, v_node, s_node)
    _solve_gen_circuits(gens, gen_xfmrs, v_node, s_node)

    return grid_init


def _solve_grid_side(
    pdr: mp.PdrParams,
    grid_line: mp.PimodelParams,
    grid_load: mp.LoadParams,
    pdr_load: mp.LoadParams,
) -> tuple[complex, mp.GenInit]:
    """Solves the grid side of the PDR bus and returns the PDR voltage and grid init.

    Loads hanging directly from the PDR bus consume part of the producer's delivery
    before it enters the grid line. When the grid line has impedance, the grid bus
    becomes the angle reference and the PDR angle is re-set globally.
    """
    v_pdr = cmath.rect(abs(pdr.u), 0)
    # Sign convention: we expect Pdr to be negative; therefore we need to flip its
    # sign here. All other loadflows below do not need this, as they are looking in
    # the opposite direction.
    s_line = -pdr.s
    if pdr_load is not None:
        s_line = s_line - complex(pdr_load.p, pdr_load.q)

    if _zero_imp_line(grid_line):
        v_grid = v_pdr
        s_grid = s_line
    else:
        v_grid, _, s_grid = _calc_pimodel(
            grid_line.y_tr, grid_line.y_sh1, grid_line.y_sh2, v_pdr, None, s_line
        )
        pdr.u_phase = -cmath.phase(v_grid)
        v_pdr = cmath.rect(abs(pdr.u), pdr.u_phase)
        v_grid = cmath.rect(abs(v_grid), 0)

    if grid_load is not None:
        s_grid = s_grid - complex(grid_load.p, grid_load.q)

    grid_init = mp.GenInit(id=None, p0=s_grid.real, q0=s_grid.imag, u0=abs(v_grid), u_phase0=0)
    return v_pdr, grid_init


def _solve_int_line(
    int_line: mp.LineParams,
    v_in: complex,
    s_in: complex,
    upstream_ids: tuple[str, ...],
) -> tuple[complex, complex, tuple[str, ...]]:
    """Pushes the flow through the internal network line, if there is one."""
    if int_line is None:
        return v_in, s_in, upstream_ids

    near = _near_index_from_upstream(int_line, upstream_ids)
    v_out, s_out = _push_through(int_line, line_pimodel(int_line), v_in, s_in, near)
    return v_out, s_out, (int_line.id,)


def _solve_main_xfmr(
    main_xfmr: mp.XfmrParams,
    v_in: complex,
    s_in: complex,
    upstream_ids: tuple[str, ...],
) -> tuple[complex, complex, tuple[str, ...]]:
    """Pushes the flow through the plant-level transformer, if there is one."""
    if main_xfmr is None:
        return v_in, s_in, upstream_ids

    near = _near_index_from_upstream(main_xfmr, upstream_ids)
    v_out, s_out = _push_through(main_xfmr, xfmr_pimodel(main_xfmr), v_in, s_in, near)
    return v_out, s_out, (main_xfmr.id,)


def _solve_aux_branch(
    aux_load: mp.LoadParams,
    auxload_xfmr: mp.XfmrParams,
    v_node: complex,
    s_node: complex,
) -> complex:
    """Solves the auxiliary load circuit and returns the flow left for the generators."""
    if aux_load is None:
        return s_node

    pq = complex(aux_load.p, aux_load.q)
    near = _near_index_from_downstream(auxload_xfmr, aux_load.id)
    ytr, ysh_near, ysh_far = _oriented(xfmr_pimodel(auxload_xfmr), near)
    i_aux, v_aux, _ = _calc_twobus_pf(ytr, ysh_near, ysh_far, v_node, pq)
    _record(aux_load.terminals[0], v_aux, pq)

    i_gens = s_node.conjugate() / v_node.conjugate() - i_aux
    return v_node * i_gens.conjugate()


def _solve_gen_circuits(
    gens: tuple[mp.GenParams, ...],
    gen_xfmrs: tuple[mp.XfmrParams, ...],
    v_node: complex,
    s_node: complex,
) -> None:
    """Shares the node flow among the units and solves each unit's circuit."""
    shares = _share_among_units(gens, s_node)
    for gen, gen_xfmr, s_share in zip_longest(gens, gen_xfmrs, shares):
        _solve_gen_circuit(gen, gen_xfmr, v_node, s_share)


def _share_among_units(gens: tuple[mp.GenParams, ...], s_node: complex) -> list[complex]:
    """Splits the node flow among the units, in proportion to their declared P and Q."""
    tot_p = 0
    tot_q = 0
    for gen in gens:
        tot_p += gen.p
        tot_q += gen.q

    return [complex(s_node.real * gen.p / tot_p, s_node.imag * gen.q / tot_q) for gen in gens]


def _solve_gen_circuit(
    gen: mp.GenParams,
    gen_xfmr: mp.XfmrParams,
    v_node: complex,
    s_share: complex,
) -> None:
    """Initializes one unit behind its transformer, or at the node when it has none."""
    if gen_xfmr is None:
        _record(gen.terminals[0], v_node, s_share)
        return

    near = _near_index_from_downstream(gen_xfmr, gen.id)
    v_gen, s_gen = _push_through(gen_xfmr, xfmr_pimodel(gen_xfmr), v_node, s_share, near)
    _record(gen.terminals[0], v_gen, s_gen)


def _push_through(
    equipment: mp.Equipment,
    pimodel: mp.PimodelParams,
    v_near: complex,
    s_near: complex,
    near_index: int,
) -> tuple[complex, complex]:
    """Solves a two-terminal pi model from its `near_index` side and records both ends.

    The transformer pi model is asymmetric: its ratio lives on the declared terminal 1
    side, so when the known bus faces terminal 2 the pi must be solved with its shunts
    swapped.
    """
    ytr, ysh_near, ysh_far = _oriented(pimodel, near_index)
    v_far, _, s_far = _calc_pimodel(ytr, ysh_near, ysh_far, v_near, None, s_near)
    _record(equipment.terminals[near_index], v_near, s_near)
    _record(equipment.terminals[1 - near_index], v_far, -s_far)
    return v_far, s_far


def _oriented(pimodel: mp.PimodelParams, near_index: int) -> tuple[complex, complex, complex]:
    if near_index == 0:
        return pimodel.y_tr, pimodel.y_sh1, pimodel.y_sh2
    return pimodel.y_tr, pimodel.y_sh2, pimodel.y_sh1


def _near_index_from_upstream(equipment: mp.Equipment, upstream_ids: tuple[str, ...]) -> int:
    return 0 if equipment.terminals[0].connected_equipment in upstream_ids else 1


def _near_index_from_downstream(equipment: mp.Equipment, downstream_id: str) -> int:
    return 1 if equipment.terminals[0].connected_equipment == downstream_id else 0


def _record(terminal: mp.Terminal, v: complex, s: complex) -> None:
    terminal.u0 = abs(v)
    terminal.u_phase0 = cmath.phase(v)
    terminal.p0 = s.real
    terminal.q0 = s.imag


def _zero_imp_line(conn_line: mp.PimodelParams) -> bool:
    return cmath.isinf(conn_line.y_tr) and conn_line.y_sh1 == 0 and conn_line.y_sh2 == 0


def _calc_pimodel(
    ytr: complex, ysh1: complex, ysh2: complex, v1: complex, i1: complex, s1: complex
) -> tuple[complex, complex, complex]:
    """Solves a pi-model circuit.

    Solves a simple pi-model circuit. In our calculations, Terminal 1 always
    represents the bus where both voltage and current (or, equivalently, P & Q)
    are known, modulo a global shift in angles. The voltage and current on
    terminal 2 are here calculated directly through simple algebra. Notation:
    (tr) stands for transmission branch; (sh) stands for shunt admittance.

    On input:
      ytr, ysh1, ysh2: the three admittance parameters of the pi model
      v1: complex voltage at terminal 1
      i1: complex current entering terminal 1
      s1: complex power flow entering terminal 1

    (If both i1 and s1 are specified, i1 is used and s1 is ignored.)

    On output:
      v2: complex voltage at terminal 2
      i2: complex current leaving terminal 2
      s2: complex power flow leaving terminal 2
    """

    if i1 is not None:
        s1 = v1 * i1.conjugate()
        v2 = v1
        i2 = i1
        s2 = s1
    else:
        v2 = v1 * (1 + ysh1 / ytr) - s1.conjugate() / (v1.conjugate() * ytr)
        i2 = (v1 - v2) * ytr - v2 * ysh2
        s2 = v2 * i2.conjugate()

    return v2, i2, s2


def _calc_twobus_pf(
    ytr: complex, ysh1: complex, ysh2: complex, v1: complex, s2: complex
) -> tuple[complex, complex, complex]:
    """Solves the two-bus load flow problem for a pi-model network.

    Solves the powerflow for a simple pi-model circuit. Terminal 1 here
    represents the bus where voltage is known. The voltage and current on
    terminal 2 are calculated by the analytic solution formulas. Notation: (tr)
    stands for 'transmission' branch; (sh) stands for 'shunt' admittance.

    On input:
      ytr, ysh1, ysh2: the three admittance parameters of the pi model
      v1: complex voltage at terminal 1
      s2: complex power load at terminal 2

    On output:
      i1: complex current at terminal 1
      v2: complex voltage at terminal 2
      i2: complex current leaving terminal 2

    """
    # calculate the sigma constant in the reduced-voltage equation:
    sigma = ((ysh2 + ytr) * s2).conjugate() / abs(ytr * v1) ** 2

    # solution to the reduced-voltage equation:
    v = complex(0.5 + sqrt(0.25 - sigma.real - sigma.imag**2), -sigma.imag)

    # undo the reduced-voltage transformation:
    v2 = v * v1 * ytr / (ytr + ysh2)

    # current flowing out of terminal 2:
    i2 = s2.conjugate() / v2.conjugate()

    # current flowing into terminal 1:
    i1 = (v1 - v2) * ytr + v1 * ysh1

    return i1, v2, i2
