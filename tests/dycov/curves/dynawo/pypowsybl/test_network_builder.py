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


def test_minimal_bus_breaker_network():
    network = nw.create_empty("test_case")

    network.create_substations(id="S1", country="ES")

    network.create_voltage_levels(
        id="VL1", substation_id="S1", nominal_v=110, topology_kind="BUS_BREAKER"
    )

    network.create_buses(id="BUS1", voltage_level_id="VL1")

    network.create_generators(
        id="G1",
        voltage_level_id="VL1",
        bus_id="BUS1",
        target_p=50,
        min_p=0.0,
        max_p=100.0,
        target_v=110.0,
        voltage_regulator_on=True,
    )

    network.create_loads(id="L1", voltage_level_id="VL1", bus_id="BUS1", p0=30.0, q0=10.0)

    # Smoke checks (no solver, no dynawo)
    gens = network.get_generators()
    loads = network.get_loads()

    assert "G1" in gens.index
    assert "L1" in loads.index
