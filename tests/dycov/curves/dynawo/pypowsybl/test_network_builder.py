#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import pytest

pypowsybl = pytest.importorskip("pypowsybl")
import pypowsybl.network as nw

from dycov.curves.dynawo.pypowsybl.network_builder import PypowsyblNetworkBuilder


def test_minimal_bus_breaker_network():
    builder = PypowsyblNetworkBuilder("test_case")

    builder.add_substation(id="S1", country="ES")
    builder.add_voltage_level(
        id="VL1", substation_id="S1", nominal_v=110, topology_kind="BUS_BREAKER"
    )
    builder.add_bus(id="BUS1", voltage_level_id="VL1")
    builder.add_generator(
        id="G1",
        voltage_level_id="VL1",
        bus_id="BUS1",
        target_p=50,
        min_p=0.0,
        max_p=100.0,
        target_v=110.0,
        voltage_regulator_on=True,
    )
    builder.add_load(id="L1", voltage_level_id="VL1", bus_id="BUS1", p0=30.0, q0=10.0)

    network = builder.build()

    assert "S1" in network.get_substations().index
    assert "VL1" in network.get_voltage_levels().index
    assert "BUS1" in network.get_bus_breaker_view_buses().index
    assert "G1" in network.get_generators().index
    assert "L1" in network.get_loads().index


def test_add_line_bus_breaker():
    """
    Test creation of a line between two buses using BUS_BREAKER topology.
    """

    builder = PypowsyblNetworkBuilder("test_case")

    # Substation
    builder.add_substation(id="S1", country="ES")

    # Voltage levels
    builder.add_voltage_level(
        id="VL1",
        substation_id="S1",
        nominal_v=110,
        topology_kind="BUS_BREAKER",
    )
    builder.add_voltage_level(
        id="VL2",
        substation_id="S1",
        nominal_v=110,
        topology_kind="BUS_BREAKER",
    )

    # Buses
    builder.add_bus(id="BUS1", voltage_level_id="VL1")
    builder.add_bus(id="BUS2", voltage_level_id="VL2")

    # Line
    builder.add_line(
        id="LINE1",
        voltage_level1_id="VL1",
        bus1_id="BUS1",
        voltage_level2_id="VL2",
        bus2_id="BUS2",
        r=0.5,
        x=10.0,
        b1=1e-6,
        b2=1e-6,
        g1=0.0,
        g2=0.0,
    )

    network = builder.build()

    lines = network.get_lines()
    assert "LINE1" in lines.index


def test_add_two_windings_transformer_bus_breaker():
    """
    Test creation of a two-windings transformer between two buses
    using BUS_BREAKER topology.
    """

    builder = PypowsyblNetworkBuilder("test_case")

    # Substation
    builder.add_substation(id="S1", country="ES")

    # Voltage levels (different nominal voltages)
    builder.add_voltage_level(
        id="VL_HV",
        substation_id="S1",
        nominal_v=225,
        topology_kind="BUS_BREAKER",
    )
    builder.add_voltage_level(
        id="VL_LV",
        substation_id="S1",
        nominal_v=110,
        topology_kind="BUS_BREAKER",
    )

    # Buses
    builder.add_bus(id="BUS_HV", voltage_level_id="VL_HV")
    builder.add_bus(id="BUS_LV", voltage_level_id="VL_LV")

    # Two-windings transformer
    builder.add_two_windings_transformer(
        id="T1",
        voltage_level1_id="VL_HV",
        bus1_id="BUS_HV",
        voltage_level2_id="VL_LV",
        bus2_id="BUS_LV",
        rated_u1=225,
        rated_u2=110,
        rated_s=100,
        r=0.5,
        x=10.0,
        b=1e-6,
        g=0.0,
    )

    network = builder.build()

    transformers = network.get_2_windings_transformers()
    assert "T1" in transformers.index


def test_add_boundary_lines_bus_breaker():
    """
    Test creation of a boundary line using BUS_BREAKER topology.
    """

    builder = PypowsyblNetworkBuilder("test_case")

    # Substation
    builder.add_substation(id="S1", country="ES")

    # Voltage level
    builder.add_voltage_level(
        id="VL1",
        substation_id="S1",
        nominal_v=110,
        topology_kind="BUS_BREAKER",
    )

    # Bus
    builder.add_bus(id="BUS1", voltage_level_id="VL1")

    # Boundary line
    builder.add_boundary_line(
        id="BL1",
        voltage_level_id="VL1",
        bus_id="BUS1",
        p0=10.0,
        q0=3.0,
        r=0.0,
        x=5.0,
        g=0.0,
        b=1e-6,
    )

    network = builder.build()

    # Pypowsybl 1.14 works with dangling lines, boundary lines will appear in next release.
    # When boundary lines are supported, this test should be updated to check the presence of
    # the boundary line instead of dangling lines.
    dangling_lines = network.get_dangling_lines()
    assert "BL1" in dangling_lines.index
