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
from dycov.electrical.pimodel_parameters import line_pimodel
from dycov.model.parameters import GenParams, LineParams, PdrParams, Terminal, XfmrParams

REL_ERR = 1.0e-9  # max allowed relative error
ABS_ERR = 1.0e-6  # max allowed absolute error (for magnitudes near zero)


def test_initialization():
    _initialize_topo_s()
    _initialize_topo_s_i()
    print("\nTesting initialization calcs COMPLETED OK.\n")


def _initialize_topo_s():
    gen = GenParams(
        id=None,
        lib=None,
        par_id=None,
        terminals=(Terminal(connected_equipment=None),),
        p=1,
        q=1,
        s_nom=90,
        i_max=None,
        voltage_droop=None,
        use_voltage_droop=False,
    )
    gen_xfmr = XfmrParams(
        id=None,
        lib=None,
        par_id=None,
        r=0.0003,
        x=0.0268,
        g=0.0,
        b=0.0,
        r_tfo=0.9574,
        alpha_tfo=0.0,
        terminals=(
            Terminal(connected_equipment=None),
            Terminal(connected_equipment=None),
        ),
    )
    pdr = PdrParams(u=1.04444444444444444444, s=-4.567 + 0.0j, p=-4.567, q=0.0)
    line = LineParams(
        id=None,
        lib=None,
        r=0.0,
        x=1 / 12.562245359891353,
        g=0.0,
        b=0.0,
        par_id=None,
        terminals=(
            Terminal(connected_equipment=None),
            Terminal(connected_equipment=None),
        ),
    )
    grid_line = line_pimodel(line)

    print("\n\nTesting initialization calcs for Topology 'S':")
    print("\tInputs:")
    print(f"\t\t{gen_xfmr=}")
    print(f"\t\t{pdr=}")
    print(f"\t\t{grid_line=}")

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
    print(f"\t\t{grid_init=}")
    print(f"\t\t{gen.terminals[0]=}")

    assert _is_equal(grid_init.u0, 1.1009193919758402)
    assert _is_equal(grid_init.u_phase0, 0.0)
    assert _is_equal(grid_init.p0, 4.567)
    assert _is_equal(grid_init.q0, -1.522032981081081)

    assert _is_equal(gen.terminals[0].u0, 1.0087747269606742)
    assert _is_equal(gen.terminals[0].u_phase0, 0.44332797328537715)
    assert _is_equal(gen.terminals[0].p0, -4.573257858564547)
    assert _is_equal(gen.terminals[0].q0, -0.5590353650995359)


def _initialize_topo_s_i():
    gen = GenParams(
        id=None,
        lib=None,
        par_id=None,
        terminals=(Terminal(connected_equipment=None),),
        p=1,
        q=1,
        s_nom=90,
        i_max=None,
        voltage_droop=None,
        use_voltage_droop=False,
    )
    gen_xfmr = XfmrParams(
        id=None,
        lib=None,
        par_id=None,
        r=0.0003,
        x=0.0268,
        g=0.0,
        b=0.0,
        r_tfo=0.9574,
        alpha_tfo=0.0,
        terminals=(
            Terminal(connected_equipment=None),
            Terminal(connected_equipment=None),
        ),
    )
    int_line = LineParams(
        id=None,
        lib=None,
        r=0.0,
        x=0.01,
        g=0.0,
        b=0.0,
        par_id=None,
        terminals=(
            Terminal(connected_equipment=None),
            Terminal(connected_equipment=None),
        ),
    )
    pdr = PdrParams(u=1.04444444444444444444, s=-4.567 + 0.0j, p=-4.567, q=0.0)
    line = LineParams(
        id=None,
        lib=None,
        r=0.0,
        x=1 / 12.562245359891353,
        g=0.0,
        b=0.0,
        par_id=None,
        terminals=(
            Terminal(connected_equipment=None),
            Terminal(connected_equipment=None),
        ),
    )
    grid_line = line_pimodel(line)

    print("\n\nTesting initialization calcs for Topology 'S+i':")
    print("\tInputs:")
    print(f"\t\t{gen_xfmr=}")
    print(f"\t\t{int_line=}")
    print(f"\t\t{pdr=}")
    print(f"\t\t{grid_line=}")

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
    print(f"\t\t{grid_init=}")
    print(f"\t\t{gen.terminals[0]=}")

    assert _is_equal(grid_init.u0, 1.1009193919758402)
    assert _is_equal(grid_init.u_phase0, 0.0)
    assert _is_equal(grid_init.p0, 4.567)
    assert _is_equal(grid_init.q0, -1.522032981081081)

    assert _is_equal(gen.terminals[0].u0, 1.0147055890384953)
    assert _is_equal(gen.terminals[0].u_phase0, 0.48429172795433334)
    assert _is_equal(gen.terminals[0].p0, -4.573257858564549)
    assert _is_equal(gen.terminals[0].q0, -0.7502368826414034)


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
