#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the curves a zone asks a producer for."""

from dycov.curves import requested_curves

GENERATORS = ["Wind_Turbine"]
TRANSFORMERS = ["StepUp_Xfmr"]


def _generator_curves(zone):
    return [
        name.split("_GEN_", 1)[1]
        for name in requested_curves.for_zone(zone, GENERATORS, TRANSFORMERS)
        if "_GEN_" in name
    ]


def test_zone_1_asks_for_the_curves_it_compares():
    requested = requested_curves.for_zone(1, GENERATORS)

    assert requested == [
        "InternalNode1_BUS_Voltage",
        "Wind_Turbine_GEN_VoltageInjTerminal",
        "Wind_Turbine_GEN_ActivePowerControlledPu",
        "Wind_Turbine_GEN_ReactivePowerControlledPu",
        "Wind_Turbine_GEN_ActiveCurrentInjTerminal",
        "Wind_Turbine_GEN_ReactiveCurrentInjTerminal",
    ]


def test_zone_3_asks_for_the_bus_the_taps_and_the_injector_terminal():
    requested = requested_curves.for_zone(3, GENERATORS, TRANSFORMERS)

    assert requested == [
        "BusPDR_BUS_Voltage",
        "BusPDR_BUS_ActivePower",
        "BusPDR_BUS_ReactivePower",
        "BusPDR_BUS_ActiveCurrent",
        "BusPDR_BUS_ReactiveCurrent",
        "StepUp_Xfmr_XFMR_Tap",
        "Wind_Turbine_GEN_VoltageInjTerminal",
        "Wind_Turbine_GEN_ActiveCurrentInjTerminal",
        "Wind_Turbine_GEN_ReactiveCurrentInjTerminal",
        "Wind_Turbine_GEN_MagnitudeControlledByAVRPu",
        "Wind_Turbine_GEN_VoltageSetpointPu",
    ]


def test_every_zone_asks_for_the_voltage_the_terminal_figure_draws():
    """fig_UIt draws the generator VoltageInjTerminal, in Zone 1 and in three Zone 3
    benchmarks."""
    for zone in (1, 3):
        assert "VoltageInjTerminal" in _generator_curves(zone)


def test_the_common_curves_precede_the_ones_of_the_zone():
    every = requested_curves.every_name(3, GENERATORS, TRANSFORMERS)

    assert every[: len(requested_curves.COMMON)] == list(requested_curves.COMMON)
    assert every[len(requested_curves.COMMON) :] == requested_curves.for_zone(
        3, GENERATORS, TRANSFORMERS
    )
