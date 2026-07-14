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

from dycov.electrical.initialization_calcs import (
    _calc_pimodel,
    _calc_twobus_pf,
    _zero_imp_line,
    init_calcs,
)
from dycov.electrical.pimodel_parameters import line_pimodel
from dycov.model.parameters import GenParams, LineParams, PdrParams, Terminal, XfmrParams

REL_ERR = 1.0e-9  # max allowed relative error
ABS_ERR = 1.0e-6  # max allowed absolute error (for magnitudes near zero)


def test_pimodel():
    ln = LineParams(
        id=None,
        lib=None,
        r=0.04444444444444444,
        x=0.4444444444444444,
        g=0.0,
        b=0.0,
        par_id=None,
        terminals=(
            Terminal(connected_equipment=None),
            Terminal(connected_equipment=None),
        ),
    )
    pdr = PdrParams(u=1.0444444444444445, u_phase=0.0, s=complex(-0.75, 0.0), p=-0.75, q=0.0)
    v_pdr = cmath.rect(abs(pdr.u), 0)
    line = line_pimodel(ln)
    v2, i2, s2 = _calc_pimodel(
        ytr=line.y_tr, ysh1=line.y_sh1, ysh2=line.y_sh2, v1=v_pdr, i1=None, s1=-pdr.s
    )
    expected_v = 1.0616365360882047
    expected_phase = -0.3053424207483087
    expected_i2 = complex(0.7180851063829787, 1.3877787807814457e-17)
    expected_s2 = complex(0.7270823902218199, -0.22917609778180173)
    assert _is_equal(abs(v2), expected_v)
    assert _is_equal(cmath.phase(v2), expected_phase)
    assert _is_equal(i2.real, expected_i2.real)
    assert _is_equal(i2.imag, expected_i2.imag)
    assert _is_equal(s2.real, expected_s2.real)
    assert _is_equal(s2.imag, expected_s2.imag)


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
    pdr = PdrParams(u=1.04444444444444444444, u_phase=0.0, s=-4.567 + 0.0j, p=-4.567, q=0.0)
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
    pdr = PdrParams(u=1.04444444444444444444, u_phase=0.0, s=-4.567 + 0.0j, p=-4.567, q=0.0)
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


def test_initialize_topo_s_with_main_xfmr():
    """Topology 'S' plus a plant transformer (Main_Xfmr) with r_tfo != 1.

    Regression test for issue #353 (point 1): the plant transformer must be
    converted with xfmr_pimodel, so its transformer ratio is honoured.
    """
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
    ppm_xfmr = XfmrParams(
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
            Terminal(connected_equipment="Measurements"),
            Terminal(connected_equipment=None),
        ),
    )
    pdr = PdrParams(u=1.04444444444444444444, u_phase=0.0, s=-4.567 + 0.0j, p=-4.567, q=0.0)
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

    grid_init = init_calcs(
        gens=[gen],
        gen_xfmrs=[gen_xfmr],
        aux_load=None,
        auxload_xfmr=None,
        ppm_xfmr=ppm_xfmr,
        int_line=None,
        pdr=pdr,
        grid_line=grid_line,
        grid_load=None,
    )

    # The grid side is solved before the plant transformer, so it must match
    # the plain topology 'S' case
    assert _is_equal(grid_init.u0, 1.1009193919758402)
    assert _is_equal(grid_init.u_phase0, 0.0)
    assert _is_equal(grid_init.p0, 4.567)
    assert _is_equal(grid_init.q0, -1.522032981081081)

    # Main_Xfmr terminals: PDR side and internal side
    assert _is_equal(ppm_xfmr.terminals[0].u0, 1.0444444444444445)
    assert _is_equal(ppm_xfmr.terminals[0].u_phase0, 0.3216913640397123)
    assert _is_equal(ppm_xfmr.terminals[0].p0, -4.567)
    assert _is_equal(ppm_xfmr.terminals[0].q0, 0.0)
    assert _is_equal(ppm_xfmr.terminals[1].u0, 1.0087747269606742)
    assert _is_equal(ppm_xfmr.terminals[1].u_phase0, 0.44332797328537715)
    assert _is_equal(ppm_xfmr.terminals[1].p0, 4.573257858564547)
    assert _is_equal(ppm_xfmr.terminals[1].q0, 0.5590353650995359)

    # Generator, behind Main_Xfmr + step-up transformer
    assert _is_equal(gen.terminals[0].u0, 0.99087174205643)
    assert _is_equal(gen.terminals[0].u_phase0, 0.5715763627421826)
    assert _is_equal(gen.terminals[0].p0, -4.58008499995222)
    assert _is_equal(gen.terminals[0].q0, -1.1689266623982368)


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


# =========================
# _zero_imp_line
# =========================

def test_zero_imp_line():
    class DummyLine:
        y_tr = complex(float("inf"))
        y_sh1 = 0
        y_sh2 = 0

    assert _zero_imp_line(DummyLine()) is True


def test_non_zero_imp_line():
    class DummyLine:
        y_tr = complex(1.0)
        y_sh1 = 0
        y_sh2 = 0

    assert _zero_imp_line(DummyLine()) is False


# =========================
# _calc_pimodel (branch i1 != None)
# =========================

def test_calc_pimodel_with_current():
    from dycov.electrical.initialization_calcs import _calc_pimodel

    v1 = complex(1, 0)
    i1 = complex(1, 0)

    v2, i2, s2 = _calc_pimodel(
        ytr=1 + 0j,
        ysh1=0,
        ysh2=0,
        v1=v1,
        i1=i1,
        s1=None,
    )

    # rama trivial: copia valores
    assert v2 == v1
    assert i2 == i1
    assert s2 == v1 * i1.conjugate()


# =========================
# _calc_twobus_pf
# =========================


def test_calc_twobus_pf():
    ytr = 1 + 0j
    ysh1 = 0 + 0j
    ysh2 = 0 + 0j
    v1 = complex(1, 0)
    s2 = complex(0.1, 0)  # 👈 más pequeño

    i1, v2, i2 = _calc_twobus_pf(ytr, ysh1, ysh2, v1, s2)

    assert isinstance(v2, complex)
    assert isinstance(i1, complex)
    assert isinstance(i2, complex)



# =========================
# init_calcs (zero imp branch)
# =========================

def test_init_calcs_zero_imp_grid_line(monkeypatch):
    from dycov.model.parameters import GenParams, PdrParams, Terminal

    # dummy gen
    gen = GenParams(
        id=None,
        lib=None,
        par_id=None,
        terminals=(Terminal(None),),
        p=1,
        q=1,
        s_nom=1,
        i_max=None,
        voltage_droop=None,
        use_voltage_droop=False,
    )

    pdr = PdrParams(u=1, u_phase=0, s=complex(-1, 0), p=-1, q=0)

    class DummyLine:
        y_tr = complex(float("inf"))
        y_sh1 = 0
        y_sh2 = 0

    # parchear solve para evitar lógica interna compleja
    monkeypatch.setattr(
        "dycov.electrical.initialization_calcs._solve_gen_circuits",
        lambda *a, **k: None,
    )

    res = init_calcs(
        gens=(gen,),
        gen_xfmrs=(),
        aux_load=None,
        auxload_xfmr=None,
        ppm_xfmr=None,
        int_line=None,
        pdr=pdr,
        grid_line=DummyLine(),
        grid_load=None,
    )

    assert res.u0 == 1
