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
from math import sqrt

from dycov.electrical.pimodel_parameters import line_pimodel, xfmr_pimodel
from dycov.model import parameters as mp


def init_calcs(
    gens: tuple[mp.GenParams, ...],
    gen_xfmrs: tuple[mp.XfmrParams, ...],
    aux_load: mp.LoadParams,
    auxload_xfmr: mp.XfmrParams,
    ppm_xfmr: mp.XfmrParams,
    int_line: mp.LineParams,
    pdr: mp.PdrParams,
    grid_line: mp.PimodelParams,
    grid_load: mp.LoadParams,
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
    ppm_xfmr: XfmrParams
        Params of the plant transformer (if present)
    int_line: LineParams
        Params of the "internal network" line (if present)
    pdr: PdrParams
        Params at the PDR bus (U, S)
    grid_line: PimodelParams
        Params of the equiv line on the grid side (zero-impedance if not used)
    grid_load: LoadParams
        Params of the equiv load on the grid side (if not Inf Bus, as in Pcs I8)

    Returns
    -------
    GenInit
        Params for the initialization of TSO's bus side (P, Q, U, angle)
    """

    #####################################################################
    # First loadflow: calculate voltage and current at the grid bus
    # [THIS STEP IS COMMON TO ALL TOPOLOGIES]
    #####################################################################
    v_pdr = cmath.rect(abs(pdr.u), 0)
    # Sign convention: we expect Pdr to be negative; therefore we need
    # to flip its sign here in this call. All other loadflows below do
    # not need this, as they are looking in the opposite direction.
    if _zero_imp_line(grid_line):
        v_grid = v_pdr
        s_grid = -pdr.s
    else:
        v_grid, _, s_grid = _calc_pimodel(
            grid_line.y_tr, grid_line.y_sh1, grid_line.y_sh2, v_pdr, None, -pdr.s
        )
        # Re-set phase angle globally. The grid sets the reference now:
        pdr.u_phase = -cmath.phase(v_grid)
        v_pdr = cmath.rect(abs(pdr.u), pdr.u_phase)
        v_grid = cmath.rect(abs(v_grid), 0)
    # If the grid bus is not Inf (as in Pcs I8), calc also the PQ init params of the equiv gen
    if grid_load is not None:
        s_grid = s_grid - complex(grid_load.p, grid_load.q)
    # We return both the grid bus voltage and PQ init params in one single object
    grid_init = mp.GenInit(id=None, p0=s_grid.real, q0=s_grid.imag, u0=abs(v_grid), u_phase0=0)

    ##########################################################################
    # Second loadflow: calculate voltage and current at the other side of the
    # internal network representation (if there is one).
    # [THIS STEP IS COMMON TO ALL TOPOLOGIES]
    ##########################################################################
    int_id = ("Measurements", "BusPDR")
    if int_line is None:
        v_int = v_pdr
        s_int = pdr.s
    else:
        int_id = (int_line.id,)
        line = line_pimodel(int_line)
        v_int, _, s_int = _calc_pimodel(line.y_tr, line.y_sh1, line.y_sh2, v_pdr, None, pdr.s)
        if int_line.terminals[0].connected_equipment in ("Measurements", "BusPDR"):
            int_line.terminals[0].u0 = abs(v_pdr)
            int_line.terminals[0].u_phase0 = cmath.phase(v_pdr)
            int_line.terminals[0].p0 = pdr.s.real
            int_line.terminals[0].q0 = pdr.s.imag
            int_line.terminals[1].u0 = abs(v_int)
            int_line.terminals[1].u_phase0 = cmath.phase(v_int)
            int_line.terminals[1].p0 = -s_int.real
            int_line.terminals[1].q0 = -s_int.imag
        else:
            int_line.terminals[1].u0 = abs(v_pdr)
            int_line.terminals[1].u_phase0 = cmath.phase(v_pdr)
            int_line.terminals[1].p0 = pdr.s.real
            int_line.terminals[1].q0 = pdr.s.imag
            int_line.terminals[0].u0 = abs(v_int)
            int_line.terminals[0].u_phase0 = cmath.phase(v_int)
            int_line.terminals[0].p0 = -s_int.real
            int_line.terminals[0].q0 = -s_int.imag
    # Next comes the plant-level transformer, if present
    if ppm_xfmr is not None:
        xfmr = line_pimodel(ppm_xfmr)
        v_int_ = v_int
        s_int_ = s_int
        v_int, _, s_int = _calc_pimodel(xfmr.y_tr, xfmr.y_sh1, xfmr.y_sh2, v_int, None, s_int)
        if ppm_xfmr.terminals[0].connected_equipment in int_id:
            ppm_xfmr.terminals[0].u0 = abs(v_int_)
            ppm_xfmr.terminals[0].u_phase0 = cmath.phase(v_int_)
            ppm_xfmr.terminals[0].p0 = s_int_.real
            ppm_xfmr.terminals[0].q0 = s_int_.imag
            ppm_xfmr.terminals[1].u0 = abs(v_int)
            ppm_xfmr.terminals[1].u_phase0 = cmath.phase(v_int)
            ppm_xfmr.terminals[1].p0 = -s_int.real
            ppm_xfmr.terminals[1].q0 = -s_int.imag
        else:
            ppm_xfmr.terminals[1].u0 = abs(v_int_)
            ppm_xfmr.terminals[1].u_phase0 = cmath.phase(v_int_)
            ppm_xfmr.terminals[1].p0 = s_int_.real
            ppm_xfmr.terminals[1].q0 = s_int_.imag
            ppm_xfmr.terminals[0].u0 = abs(v_int)
            ppm_xfmr.terminals[0].u_phase0 = cmath.phase(v_int)
            ppm_xfmr.terminals[0].p0 = -s_int.real
            ppm_xfmr.terminals[0].q0 = -s_int.imag

    ##########################################################################
    # Now things are different depending on the topology:
    #
    #   * Topologies S, S+i, M, M+i: perform a Third loadflow simply calculating
    #     volt and current behind the step-up transformers.
    #
    #   * Topologies S+Aux, S+Aux+i, M+Aux, M+Aux+i:
    #       - first calculate a Third loadflow for solving the Aux Load circuit
    #       - then calculate a Fourth loadflow for the volt & current behind the
    #         step-up transformers
    #
    ##########################################################################
    if aux_load is None:
        _solve_gen_circuits(gens, gen_xfmrs, v_int, s_int)
    else:
        # solve first the powerflow for the aux load circuit
        xfmr = xfmr_pimodel(auxload_xfmr)
        pq = complex(aux_load.p, aux_load.q)
        i1_aux, v2_aux, _ = _calc_twobus_pf(xfmr.y_tr, xfmr.y_sh1, xfmr.y_sh2, v_int, pq)
        aux_load.terminals[0].u0 = abs(v2_aux)
        aux_load.terminals[0].u_phase0 = cmath.phase(v2_aux)
        aux_load.terminals[0].p0 = aux_load.p
        aux_load.terminals[0].q0 = aux_load.q
        # Now we can solve the generators' circuits
        i_gens = s_int.conjugate() / v_int.conjugate() - i1_aux
        s_int_gens = v_int * i_gens.conjugate()
        _solve_gen_circuits(gens, gen_xfmrs, v_int, s_int_gens)

    return grid_init


def _zero_imp_line(conn_line: mp.PimodelParams) -> bool:
    return cmath.isinf(conn_line.y_tr) and conn_line.y_sh1 == 0 and conn_line.y_sh2 == 0


def _solve_gen_circuits(
    gens: tuple[mp.GenParams, ...],
    gen_xfmrs: tuple[mp.XfmrParams, ...],
    v_int: complex,
    s_int: complex,
) -> None:
    tot_P = 0
    tot_Q = 0
    for gen in gens:
        tot_P += gen.p
        tot_Q += gen.q

    for gen, gen_xfmr in zip(gens, gen_xfmrs):
        s_int_share = complex(s_int.real * gen.p / tot_P, s_int.imag * gen.q / tot_Q)
        xfmr = xfmr_pimodel(gen_xfmr)
        v_gen, _, s_gen = _calc_pimodel(
            xfmr.y_tr, xfmr.y_sh1, xfmr.y_sh2, v_int, None, s_int_share
        )
        gen.terminals[0].u0 = abs(v_gen)
        gen.terminals[0].u_phase0 = cmath.phase(v_gen)
        gen.terminals[0].p0 = s_gen.real
        gen.terminals[0].q0 = s_gen.imag
        if gen_xfmr.terminals[0].connected_equipment == gen.id:
            gen_xfmr.terminals[1].u0 = abs(v_int)
            gen_xfmr.terminals[1].u_phase0 = cmath.phase(v_int)
            gen_xfmr.terminals[1].p0 = s_int.real
            gen_xfmr.terminals[1].q0 = s_int.imag
            gen_xfmr.terminals[0].u0 = abs(v_gen)
            gen_xfmr.terminals[0].u_phase0 = cmath.phase(v_gen)
            gen_xfmr.terminals[0].p0 = -s_gen.real
            gen_xfmr.terminals[0].q0 = -s_gen.imag
        else:
            gen_xfmr.terminals[0].u0 = abs(v_int)
            gen_xfmr.terminals[0].u_phase0 = cmath.phase(v_int)
            gen_xfmr.terminals[0].p0 = s_int.real
            gen_xfmr.terminals[0].q0 = s_int.imag
            gen_xfmr.terminals[1].u0 = abs(v_gen)
            gen_xfmr.terminals[1].u_phase0 = cmath.phase(v_gen)
            gen_xfmr.terminals[1].p0 = -s_gen.real
            gen_xfmr.terminals[1].q0 = -s_gen.imag


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
