#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from dycov.electrical.initialization_calcs import init_calcs
from dycov.model.parameters import (
    Gen_params,
    Line_params,
    Pdr_params,
    Pimodel_params,
    Terminal,
    Xfmr_params,
)

REL_ERR = 1.0e-9  # max allowed relative error
ABS_ERR = 1.0e-6  # max allowed absolute error (for magnitudes near zero)


def test_initialization():
    _initialize_topo_s()
    _initialize_topo_s_i()
    print("\nTesting initialization calcs COMPLETED OK.\n")


def _initialize_topo_s():
    gen = Gen_params(
        id=None,
        lib=None,
        par_id=None,
        terminals=(Terminal(connectedEquipment=None),),
        P=1,
        Q=1,
        SNom=90,
        IMax=None,
        VoltageDroop=None,
        UseVoltageDroop=False,
    )
    gen_xfmr = Xfmr_params(
        id=None,
        lib=None,
        par_id=None,
        R=0.0003,
        X=0.0268,
        G=0.0,
        B=0.0,
        rTfo=0.9574,
        terminals=(
            Terminal(connectedEquipment=None),
            Terminal(connectedEquipment=None),
        ),
    )
    pdr = Pdr_params(U=1.04444444444444444444, S=-4.567 + 0.0j, P=-4.567, Q=0.0)
    grid_line = Pimodel_params(Ytr=-12.562245359891353j, Ysh1=0.0j, Ysh2=0.0j)

    print("\n\nTesting initialization calcs for Topology 'S':")
    print("\tInputs:")
    print(f"\t\t{gen_xfmr = }")
    print(f"\t\t{pdr = }")
    print(f"\t\t{grid_line = }")

    grid_init = init_calcs(
        gens=[gen],
        gen_xfmrs=[gen_xfmr],
        aux_load=None,
        auxload_xfmr=None,
        ppm_xfmr=None,
        int_line=None,
        pdr=pdr,
        grid_line=grid_line,
        grid_load=None,
    )

    print("\tOutputs:")
    print(f"\t\t{grid_init = }")
    print(f"\t\t{gen.terminals[0] = }")

    assert _is_equal(grid_init.U0, 1.1009193919758402)
    assert _is_equal(grid_init.UPhase0, 0.0)
    assert _is_equal(grid_init.P0, 4.567)
    assert _is_equal(grid_init.Q0, -1.522032981081081)

    assert _is_equal(gen.terminals[0].U0, 1.0087747269606742)
    assert _is_equal(gen.terminals[0].UPhase0, 0.44332797328537715)
    assert _is_equal(gen.terminals[0].P0, -4.573257858564547)
    assert _is_equal(gen.terminals[0].Q0, -0.5590353650995359)


def _initialize_topo_s_i():
    gen = Gen_params(
        id=None,
        lib=None,
        par_id=None,
        terminals=(Terminal(connectedEquipment=None),),
        P=1,
        Q=1,
        SNom=90,
        IMax=None,
        VoltageDroop=None,
        UseVoltageDroop=False,
    )
    gen_xfmr = Xfmr_params(
        id=None,
        lib=None,
        par_id=None,
        R=0.0003,
        X=0.0268,
        G=0.0,
        B=0.0,
        rTfo=0.9574,
        terminals=(
            Terminal(connectedEquipment=None),
            Terminal(connectedEquipment=None),
        ),
    )
    int_line = Line_params(
        id=None,
        lib=None,
        R=0.0,
        X=0.01,
        G=0.0,
        B=0.0,
        par_id=None,
        terminals=(
            Terminal(connectedEquipment=None),
            Terminal(connectedEquipment=None),
        ),
    )
    pdr = Pdr_params(U=1.04444444444444444444, S=-4.567 + 0.0j, P=-4.567, Q=0.0)
    grid_line = Pimodel_params(Ytr=-12.562245359891353j, Ysh1=0.0j, Ysh2=0.0j)

    print("\n\nTesting initialization calcs for Topology 'S+i':")
    print("\tInputs:")
    print(f"\t\t{gen_xfmr = }")
    print(f"\t\t{int_line = }")
    print(f"\t\t{pdr = }")
    print(f"\t\t{grid_line = }")

    grid_init = init_calcs(
        gens=[gen],
        gen_xfmrs=[gen_xfmr],
        aux_load=None,
        auxload_xfmr=None,
        ppm_xfmr=None,
        int_line=int_line,
        pdr=pdr,
        grid_line=grid_line,
        grid_load=None,
    )

    print("\tOutputs:")
    print(f"\t\t{grid_init = }")
    print(f"\t\t{gen.terminals[0] = }")

    assert _is_equal(grid_init.U0, 1.1009193919758402)
    assert _is_equal(grid_init.UPhase0, 0.0)
    assert _is_equal(grid_init.P0, 4.567)
    assert _is_equal(grid_init.Q0, -1.522032981081081)

    assert _is_equal(gen.terminals[0].U0, 1.0147055890384953)
    assert _is_equal(gen.terminals[0].UPhase0, 0.48429172795433334)
    assert _is_equal(gen.terminals[0].P0, -4.573257858564549)
    assert _is_equal(gen.terminals[0].Q0, -0.7502368826414034)


def _is_equal(a: float, b: float) -> bool:
    scale = 0.5 * (abs(a) + abs(b))
    if scale >= 1.0:
        if abs(a - b) / scale < REL_ERR:
            return True
        else:
            return False
    else:
        if abs(a - b) < ABS_ERR:
            return True
        else:
            return False
