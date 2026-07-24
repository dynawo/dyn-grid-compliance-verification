#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Unit tests for dycov.electrical.initialization_calcs (pi-model solvers and init_calcs)."""
import cmath

from dycov.electrical.initialization_calcs import (
    _calc_pimodel,
    _calc_twobus_pf,
    _zero_imp_line,
    init_calcs,
)
from dycov.electrical.pimodel_parameters import line_pimodel
from dycov.model.parameters import (
    GenParams,
    LineParams,
    LoadParams,
    PdrParams,
    Terminal,
    XfmrParams,
)

REL_ERR = 1.0e-9  # max allowed relative error
ABS_ERR = 1.0e-6  # max allowed absolute error (for magnitudes near zero)


def _is_equal(a: float, b: float) -> bool:
    scale = 0.5 * (abs(a) + abs(b))
    if scale < 1.0:
        return abs(a - b) < ABS_ERR
    return abs(a - b) / scale < REL_ERR


class DummyLine:
    def __init__(self, y_tr: complex):
        self.y_tr = y_tr
        self.y_sh1 = 0
        self.y_sh2 = 0


def _make_load(p: float, q: float) -> LoadParams:
    return LoadParams(
        id=None,
        lib=None,
        p=p,
        q=q,
        u=None,
        u_phase=None,
        alpha=None,
        beta=None,
        par_id=None,
        terminals=(Terminal(connected_equipment=None),),
    )


def _make_gen_and_xfmr() -> tuple[GenParams, XfmrParams]:
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
    return gen, gen_xfmr


def _make_grid_line() -> LineParams:
    return LineParams(
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


# ---------------------------------------------------------------------------
# _calc_pimodel
# ---------------------------------------------------------------------------


def test_calc_pimodel_with_power():
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

    assert _is_equal(abs(v2), 1.0616365360882047)
    assert _is_equal(cmath.phase(v2), -0.3053424207483087)
    assert _is_equal(i2.real, 0.7180851063829787)
    assert _is_equal(i2.imag, 1.3877787807814457e-17)
    assert _is_equal(s2.real, 0.7270823902218199)
    assert _is_equal(s2.imag, -0.22917609778180173)


def test_calc_pimodel_with_current():
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

    assert v2 == v1
    assert i2 == i1
    assert s2 == v1 * i1.conjugate()


# ---------------------------------------------------------------------------
# _calc_twobus_pf
# ---------------------------------------------------------------------------


def test_calc_twobus_pf():
    ytr = 1 + 0j
    ysh1 = 0 + 0j
    ysh2 = 0 + 0j
    v1 = complex(1, 0)
    s2 = complex(0.1, 0)

    i1, v2, i2 = _calc_twobus_pf(ytr, ysh1, ysh2, v1, s2)

    # Analytic solution of v2^2 - v2 + 0.1 = 0: v2 = (1 + sqrt(0.6)) / 2
    assert _is_equal(v2.real, 0.8872983346207417)
    assert _is_equal(v2.imag, 0.0)
    # With no shunts the same current flows through both terminals: i = 1 - v2
    assert _is_equal(i1.real, 0.1127016653792583)
    assert _is_equal(i1.imag, 0.0)
    assert _is_equal(i2.real, 0.1127016653792583)
    assert _is_equal(i2.imag, 0.0)


# ---------------------------------------------------------------------------
# _zero_imp_line
# ---------------------------------------------------------------------------


def test_zero_imp_line():
    assert _zero_imp_line(DummyLine(y_tr=complex(float("inf")))) is True


def test_non_zero_imp_line():
    assert _zero_imp_line(DummyLine(y_tr=complex(1.0))) is False


# ---------------------------------------------------------------------------
# init_calcs
# ---------------------------------------------------------------------------


def test_initialize_topo_s():
    """Topology 'S': a single generator behind its step-up transformer."""
    gen, gen_xfmr = _make_gen_and_xfmr()
    pdr = PdrParams(u=1.04444444444444444444, u_phase=0.0, s=-4.567 + 0.0j, p=-4.567, q=0.0)
    grid_line = line_pimodel(_make_grid_line())

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

    assert _is_equal(grid_init.u0, 1.1009193919758402)
    assert _is_equal(grid_init.u_phase0, 0.0)
    assert _is_equal(grid_init.p0, 4.567)
    assert _is_equal(grid_init.q0, -1.522032981081081)

    assert _is_equal(gen.terminals[0].u0, 1.0991244531721)
    assert _is_equal(gen.terminals[0].u_phase0, 0.43328564582460044)
    assert _is_equal(gen.terminals[0].p0, -4.572736045526256)
    assert _is_equal(gen.terminals[0].q0, -0.5124200670122216)


def test_initialize_topo_s_i():
    """Topology 'S+i': topology 'S' plus an internal network line."""
    gen, gen_xfmr = _make_gen_and_xfmr()
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
    grid_line = line_pimodel(_make_grid_line())

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

    # The grid side is not affected by the internal line
    assert _is_equal(grid_init.u0, 1.1009193919758402)
    assert _is_equal(grid_init.u_phase0, 0.0)
    assert _is_equal(grid_init.p0, 4.567)
    assert _is_equal(grid_init.q0, -1.522032981081081)

    assert _is_equal(gen.terminals[0].u0, 1.1051430783919824)
    assert _is_equal(gen.terminals[0].u_phase0, 0.4743671252012512)
    assert _is_equal(gen.terminals[0].p0, -4.572736045526256)
    assert _is_equal(gen.terminals[0].q0, -0.7036215845540932)


def test_initialize_topo_s_with_main_xfmr():
    """Topology 'S' plus a plant transformer (Main_Xfmr) with r_tfo != 1.

    Regression test for issue #353 (point 1): the plant transformer must be
    converted with xfmr_pimodel, so its transformer ratio is honoured.
    Expected values satisfy the Dynawo transformer equations with the declared
    terminal orientation (issue #355).
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
    assert _is_equal(gen.terminals[0].u0, 1.0780685014941822)
    assert _is_equal(gen.terminals[0].u_phase0, 0.5611528954914154)
    assert _is_equal(gen.terminals[0].p0, -4.5795157171290946)
    assert _is_equal(gen.terminals[0].q0, -1.118070730199069)


def test_initialize_topo_m_power_share():
    """Topology 'M': two generators with different P/Q shares.

    Regression test for issue #353 (point 2): the network-side terminal of
    each step-up transformer must carry its per-generator share of the plant
    flow (s_int_share), not the plant total. Covers both terminal
    orientations (generator on terminal 1 and on terminal 2), whose pi models
    are solved from the declared known side (issue #355).
    """
    gen1 = GenParams(
        id="G1",
        lib=None,
        par_id=None,
        terminals=(Terminal(connected_equipment=None),),
        p=0.6,
        q=0.7,
        s_nom=45,
        i_max=None,
        voltage_droop=None,
        use_voltage_droop=False,
    )
    gen2 = GenParams(
        id="G2",
        lib=None,
        par_id=None,
        terminals=(Terminal(connected_equipment=None),),
        p=0.4,
        q=0.3,
        s_nom=45,
        i_max=None,
        voltage_droop=None,
        use_voltage_droop=False,
    )
    # Usual orientation: terminal 1 on the generator side
    xfmr1 = XfmrParams(
        id="X1",
        lib=None,
        par_id=None,
        r=0.0003,
        x=0.0268,
        g=0.0,
        b=0.0,
        r_tfo=0.9574,
        alpha_tfo=0.0,
        terminals=(
            Terminal(connected_equipment="G1"),
            Terminal(connected_equipment="Int"),
        ),
    )
    # Reversed orientation: terminal 2 on the generator side
    xfmr2 = XfmrParams(
        id="X2",
        lib=None,
        par_id=None,
        r=0.0004,
        x=0.0300,
        g=0.0,
        b=0.0,
        r_tfo=0.98,
        alpha_tfo=0.0,
        terminals=(
            Terminal(connected_equipment="Int"),
            Terminal(connected_equipment="G2"),
        ),
    )
    pdr = PdrParams(
        u=1.04444444444444444444, u_phase=0.0, s=complex(-4.567, -1.0), p=-4.567, q=-1.0
    )
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
        gens=[gen1, gen2],
        gen_xfmrs=[xfmr1, xfmr2],
        aux_load=None,
        auxload_xfmr=None,
        ppm_xfmr=None,
        int_line=None,
        pdr=pdr,
        grid_line=grid_line,
        grid_load=None,
    )

    assert _is_equal(grid_init.u0, 1.0288951414189706)
    assert _is_equal(grid_init.u_phase0, 0.0)
    assert _is_equal(grid_init.p0, 4.567)
    assert _is_equal(grid_init.q0, -0.5950059540540541)

    # Network-side terminal of each step-up transformer: its own share
    assert _is_equal(xfmr1.terminals[1].u0, 1.0444444444444445)
    assert _is_equal(xfmr1.terminals[1].p0, -2.7402)
    assert _is_equal(xfmr1.terminals[1].q0, -0.7)
    assert _is_equal(xfmr2.terminals[0].u0, 1.0444444444444445)
    assert _is_equal(xfmr2.terminals[0].p0, -1.8268000000000002)
    assert _is_equal(xfmr2.terminals[0].q0, -0.3)

    # Shares must add up to the plant total at the internal bus
    assert _is_equal(xfmr1.terminals[1].p0 + xfmr2.terminals[0].p0, -4.567)
    assert _is_equal(xfmr1.terminals[1].q0 + xfmr2.terminals[0].q0, -1.0)

    # Generator-side values, consistent with each unit's flow
    assert _is_equal(gen1.terminals[0].u0, 1.1129125029368876)
    assert _is_equal(gen1.terminals[0].u_phase0, 0.4109629092433011)
    assert _is_equal(gen1.terminals[0].p0, -2.7423997319349467)
    assert _is_equal(gen1.terminals[0].q0, -0.8965093861886826)
    assert _is_equal(xfmr1.terminals[0].p0, 2.7423997319349467)
    assert _is_equal(xfmr1.terminals[0].q0, 0.8965093861886826)
    assert _is_equal(gen2.terminals[0].u0, 1.0344428846880473)
    assert _is_equal(gen2.terminals[0].u_phase0, 0.3967838257659877)
    assert _is_equal(gen2.terminals[0].p0, -1.828108507986619)
    assert _is_equal(gen2.terminals[0].q0, -0.3981380989964001)
    assert _is_equal(xfmr2.terminals[1].p0, 1.828108507986619)
    assert _is_equal(xfmr2.terminals[1].q0, 0.3981380989964001)


def test_initialize_islanding_pdr_side_load():
    """Islanding topology: the Main_Load hangs directly from the PDR bus.

    The load consumes the whole producer delivery, so the grid line must carry
    no flow: the grid-side equivalent generator initializes at ~0 PQ and the
    PDR bus keeps the grid phase reference (u_phase ~ 0). Regression test for
    the bug where the full delivery was sent through the line, producing a
    spurious phase shift at the PDR bus.
    """
    gen, gen_xfmr = _make_gen_and_xfmr()
    pdr = PdrParams(u=1.0, u_phase=0.0, s=complex(-0.32, 0.0), p=-0.32, q=0.0)
    line = LineParams(
        id=None,
        lib=None,
        r=0.0,
        x=0.05,
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
        ppm_xfmr=None,
        int_line=None,
        pdr=pdr,
        grid_line=grid_line,
        grid_load=None,
        pdr_load=_make_load(0.32, 0.0),
    )

    assert _is_equal(grid_init.p0, 0.0)
    assert _is_equal(grid_init.q0, 0.0)
    assert _is_equal(grid_init.u0, 1.0)
    assert _is_equal(pdr.u_phase, 0.0)


def test_initialize_grid_side_load_keeps_line_flow():
    """Topology with the load behind the line, on the grid side (as in Pcs I8).

    The grid-side load must be subtracted only from the equivalent generator's
    PQ init params; the line still carries the full producer delivery, so the
    voltages and the PDR phase must match the plain topology 'S' case.
    """
    gen, gen_xfmr = _make_gen_and_xfmr()
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
        ppm_xfmr=None,
        int_line=None,
        pdr=pdr,
        grid_line=grid_line,
        grid_load=_make_load(0.5, 0.1),
        pdr_load=None,
    )

    # Voltages match the plain topology 'S' case (same line flow)
    assert _is_equal(grid_init.u0, 1.1009193919758402)
    assert _is_equal(grid_init.u_phase0, 0.0)
    # The equiv generator PQ is reduced by the grid-side load consumption
    assert _is_equal(grid_init.p0, 4.567 - 0.5)
    assert _is_equal(grid_init.q0, -1.522032981081081 - 0.1)
    # Generator-side values unaffected by the grid-side load
    assert _is_equal(gen.terminals[0].u0, 1.0991244531721)
    assert _is_equal(gen.terminals[0].u_phase0, 0.43328564582460044)


def test_init_calcs_zero_imp_grid_line(monkeypatch):
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
    # Stub the generator-side solve: only the grid-side result is under test
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
        grid_line=DummyLine(y_tr=complex(float("inf"))),
        grid_load=None,
    )

    # With a zero-impedance line the PDR bus values pass through unchanged
    assert res.u0 == 1
    assert res.u_phase0 == 0
    assert res.p0 == 1
    assert res.q0 == 0
