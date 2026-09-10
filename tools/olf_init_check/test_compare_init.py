#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#
"""Unit tests for the branch pi-model that compare_init.py feeds to OpenLoadFlow."""

import math
import os
import sys

import pytest

pytest.importorskip("pypowsybl")
import pypowsybl.loadflow as lf  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compare_init import LF_PARAMS, _branch_pimodel  # noqa: E402
from network_builder import PypowsyblNetworkBuilder  # noqa: E402

R, X = 0.00001, 0.0001  # Main_Xfmr of the bundled quasi-ideal plant transformer
RHO = 1.05  # its off-nominal tap
UNOM, SNREF = 225.0, 100.0
ZBASE = UNOM**2 / SNREF


def _solve_two_bus(load_mw, load_mvar, branch):
    """Terminal-2 voltage and t1->t2 angle of a two-bus net fed from a slack on terminal 1."""
    builder = PypowsyblNetworkBuilder("pimodel_case")
    builder.add_substation(id="S1", country="ES")
    for node in ("N1", "N2"):
        builder.add_voltage_level(
            id="VL_" + node, substation_id="S1", nominal_v=UNOM, topology_kind="BUS_BREAKER"
        )
        builder.add_bus(id="B_" + node, voltage_level_id="VL_" + node)
    builder.add_generator(
        id="G_SRC",
        voltage_level_id="VL_N1",
        bus_id="B_N1",
        min_p=-1e5,
        max_p=1e5,
        target_p=0.0,
        target_v=UNOM,
        voltage_regulator_on=True,
    )
    builder.add_load(id="L2", voltage_level_id="VL_N2", bus_id="B_N2", p0=load_mw, q0=load_mvar)
    branch(builder)

    network = builder.build()
    buses = network.get_buses()
    slack = buses.index[buses["voltage_level_id"] == "VL_N1"][0]
    result = lf.run_ac(
        network,
        parameters=lf.Parameters(
            distributed_slack=False,
            provider_parameters={
                "slackBusSelectionMode": "NAME",
                "slackBusesIds": slack,
                **LF_PARAMS,
            },
        ),
    )
    assert result[0].status.name == "CONVERGED", result[0].status_text

    buses = network.get_buses()
    bus1 = buses.index[buses["voltage_level_id"] == "VL_N1"][0]
    bus2 = buses.index[buses["voltage_level_id"] == "VL_N2"][0]
    return (
        buses.loc[bus2, "v_mag"] / UNOM,
        math.radians(buses.loc[bus2, "v_angle"] - buses.loc[bus1, "v_angle"]),
    )


def _as_line(builder, rho):
    z, ysh1, ysh2 = _branch_pimodel(R, X, rho)
    builder.add_line(
        id="BR",
        voltage_level1_id="VL_N1",
        bus1_id="B_N1",
        voltage_level2_id="VL_N2",
        bus2_id="B_N2",
        r=z.real * ZBASE,
        x=z.imag * ZBASE,
        g1=ysh1.real / ZBASE,
        b1=ysh1.imag / ZBASE,
        g2=ysh2.real / ZBASE,
        b2=ysh2.imag / ZBASE,
    )


def _as_transformer(builder, rho):
    builder.add_two_windings_transformer(
        id="BR",
        voltage_level1_id="VL_N1",
        bus1_id="B_N1",
        voltage_level2_id="VL_N2",
        bus2_id="B_N2",
        rated_u1=UNOM,
        rated_u2=UNOM * rho,
        rated_s=SNREF,
        r=R * ZBASE,
        x=X * ZBASE,
        g=0.0,
        b=0.0,
    )


def test_nominal_tap_leaves_a_plain_series_branch():
    z, ysh1, ysh2 = _branch_pimodel(R, X, 1.0)

    assert z == complex(R, X)
    assert ysh1 == 0
    assert ysh2 == 0


def test_pimodel_admittances_are_those_of_an_ideal_ratio_at_terminal_1():
    z, ysh1, ysh2 = _branch_pimodel(R, X, RHO)

    y_series = 1 / z
    y = 1 / complex(R, X)
    assert y_series + ysh1 == pytest.approx(RHO**2 * y)  # self admittance at terminal 1
    assert -y_series == pytest.approx(-RHO * y)  # mutual admittance
    assert y_series + ysh2 == pytest.approx(y)  # self admittance at terminal 2


def test_off_nominal_tap_raises_terminal_2_by_the_ratio_at_no_load():
    v2, phase = _solve_two_bus(0.0, 0.0, lambda b: _as_line(b, RHO))

    assert v2 == pytest.approx(RHO, abs=1e-9)
    assert phase == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("load_mw, load_mvar", [(60.0, 20.0), (-40.0, 15.0)])
def test_pimodel_branch_solves_like_a_powsybl_transformer(load_mw, load_mvar):
    v2_pi, phase_pi = _solve_two_bus(load_mw, load_mvar, lambda b: _as_line(b, RHO))
    v2_tfo, phase_tfo = _solve_two_bus(load_mw, load_mvar, lambda b: _as_transformer(b, RHO))

    assert v2_pi == pytest.approx(v2_tfo, abs=1e-9)
    assert phase_pi == pytest.approx(phase_tfo, abs=1e-9)
