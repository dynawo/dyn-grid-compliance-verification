#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the CRV file DyCoV writes to ask Dynawo for the curves of a simulation."""

from pathlib import Path

import pytest
from lxml import etree

from dycov.core.global_variables import (
    ELECTRIC_PERFORMANCE_PPM,
    ELECTRIC_PERFORMANCE_SM,
    MODEL_VALIDATION_PPM,
)
from dycov.curves.dynawo.io.crv import create_curves_file

_CURVE_TAG = ".//{http://www.rte-france.com/dynawo}curve"

_ALL_GENERATOR_CURVE_LISTS = [
    (ELECTRIC_PERFORMANCE_PPM, 1),
    (MODEL_VALIDATION_PPM, 1),
    (MODEL_VALIDATION_PPM, 3),
]


class DummyEquipment:
    def __init__(self, id, lib=None, var=None):
        self.id = id
        self.lib = lib
        self.var = var


def parse_curves_file(path):
    parser = etree.XMLParser(remove_blank_text=True)
    return etree.parse(str(path), parser).getroot()


def _requested_models(path: Path) -> list:
    return [curve.attrib["model"] for curve in parse_curves_file(path).findall(_CURVE_TAG)]


# ---------------------------------------------------------------------------
# Equipment asked for curves
# ---------------------------------------------------------------------------


def test_create_curves_file_asks_a_synchronous_machine_for_its_curves(tmp_path):
    curves_dict = create_curves_file(
        tmp_path,
        "curves_sm.xml",
        [DummyEquipment("Xfmr", lib="TransformerFixedRatio")],
        [DummyEquipment("Gen", lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a")],
        [],
        [],
        ELECTRIC_PERFORMANCE_SM,
        1,
        "USetpoint",
    )

    models = _requested_models(tmp_path / "curves_sm.xml")
    assert "Measurements" in models
    assert "Gen" in models
    assert "Gen_GEN_RotorSpeedPu" in curves_dict["Gen_generator_omegaPu"]
    assert curves_dict["Gen_generator_thetaInternal"] == ["Gen_GEN_InternalAngle"]


def test_create_curves_file_asks_a_tso_load_for_its_powers(tmp_path):
    curves_dict = create_curves_file(
        tmp_path,
        "curves_all.xml",
        [DummyEquipment("Xfmr", lib="TransformerFixedRatio")],
        [DummyEquipment("Gen", lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a")],
        [DummyEquipment("Load", lib="LoadAlphaBeta")],
        [],
        ELECTRIC_PERFORMANCE_SM,
        1,
        "USetpoint",
    )

    assert "Load" in _requested_models(tmp_path / "curves_all.xml")
    assert curves_dict["Load_load_PPu"] == ["Load_LOAD_ActivePower"]
    assert curves_dict["Load_load_QPu"] == ["Load_LOAD_ReactivePower"]


def test_zone_1_asks_the_infinite_bus_for_no_curve(tmp_path):
    curves_dict = create_curves_file(
        tmp_path,
        "curves_z1.xml",
        [DummyEquipment("Xfmr", lib="TransformerFixedRatio")],
        [DummyEquipment("Gen", lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a")],
        [],
        [],
        ELECTRIC_PERFORMANCE_SM,
        1,
        "USetpoint",
    )

    assert "InfiniteBus" not in _requested_models(tmp_path / "curves_z1.xml")
    assert not any("InfiniteBus" in key for key in curves_dict)


def test_create_curves_file_asks_a_unit_for_nothing_in_an_unknown_zone(tmp_path):
    curves_dict = create_curves_file(
        tmp_path,
        "curves_invalid.xml",
        [],
        [DummyEquipment("WT", lib="WT4BWeccCurrentSource")],
        [],
        [],
        MODEL_VALIDATION_PPM,
        2,
        "USetpoint",
    )

    assert _requested_models(tmp_path / "curves_invalid.xml") == ["Measurements"] * 3
    assert curves_dict == {
        "Measurements_measurements_UPu": ["Measurements_BUS_Voltage"],
        "Measurements_BUS_Voltage": 1,
        "Measurements_measurements_PPu": ["Measurements_BUS_ActivePower"],
        "Measurements_BUS_ActivePower": -1,
        "Measurements_measurements_QPu": ["Measurements_BUS_ReactivePower"],
        "Measurements_BUS_ReactivePower": -1,
    }


# ---------------------------------------------------------------------------
# Zone 1 setpoints
# ---------------------------------------------------------------------------


def _zone_1_setpoints(tmp_path: Path, control_mode: str) -> set:
    """The setpoints Zone 1 asks the simulation of a unit whose model carries the reactive power
    and the voltage setpoints in a single variable."""
    curves_dict = create_curves_file(
        tmp_path,
        "curves_z1.xml",
        [],
        [DummyEquipment("WT", lib="WT4BWeccCurrentSource")],
        [],
        [],
        MODEL_VALIDATION_PPM,
        1,
        control_mode,
    )
    return {key for key in curves_dict if key.startswith("WT_GEN_") and key.endswith("SetpointPu")}


def test_zone_1_asks_for_the_voltage_setpoint_in_the_test_that_steps_it(tmp_path):
    """#554: in a voltage setpoint step the shared variable is the voltage setpoint."""
    assert _zone_1_setpoints(tmp_path, "USetpoint") == {
        "WT_GEN_ActivePowerSetpointPu",
        "WT_GEN_VoltageSetpointPu",
    }


@pytest.mark.parametrize("control_mode", ["PSetpoint", "QSetpoint", "Others", None])
def test_zone_1_asks_no_other_test_for_the_voltage_setpoint(tmp_path, control_mode):
    """#554: anywhere else the shared variable would be published under both names."""
    assert _zone_1_setpoints(tmp_path, control_mode) == {
        "WT_GEN_ActivePowerSetpointPu",
        "WT_GEN_ReactivePowerSetpointPu",
    }


# ---------------------------------------------------------------------------
# Voltage at InternalNode2
# ---------------------------------------------------------------------------


def _terminal_voltage_requests(
    tmp_path: Path, generator_lib: str, sim_type: int, zone: int
) -> dict:
    """What the curves file asks a unit for to obtain its voltage at InternalNode2, mapped to the
    voltage curves each request feeds."""
    curves_dict = create_curves_file(
        tmp_path,
        "curves.xml",
        [],
        [DummyEquipment("Gen", lib=generator_lib)],
        [],
        [],
        sim_type,
        zone,
        None,
    )

    requested = [
        curve.attrib["variable"]
        for curve in parse_curves_file(tmp_path / "curves.xml").findall(_CURVE_TAG)
        if curve.attrib["model"] == "Gen"
    ]
    voltage_curves = {
        variable: [
            curve for curve in curves_dict[f"Gen_{variable}"] if "_GEN_VoltageInjTerminal" in curve
        ]
        for variable in requested
    }
    return {variable: curves for variable, curves in voltage_curves.items() if curves}


@pytest.mark.parametrize("sim_type, zone", _ALL_GENERATOR_CURVE_LISTS)
@pytest.mark.parametrize(
    "generator_lib, amplitude",
    [
        ("PhotovoltaicsWeccVoltageSource1NoPlantControl", "photovoltaics_SourceMeasurements_UPu"),
        ("WT4BWeccCurrentSource", "WT4B_injector_UPu"),
        ("BESSWeccCurrentSource", "BESS_injector_UPu"),
    ],
)
def test_a_unit_that_publishes_its_terminal_voltage_amplitude_is_asked_for_it(
    tmp_path, sim_type, zone, generator_lib, amplitude
):
    """#555: Dynawo already computes the amplitude, so there is nothing to rebuild."""
    requests = _terminal_voltage_requests(tmp_path, generator_lib, sim_type, zone)

    assert requests == {amplitude: ["Gen_GEN_VoltageInjTerminal"]}


@pytest.mark.parametrize("sim_type, zone", _ALL_GENERATOR_CURVE_LISTS)
@pytest.mark.parametrize(
    "generator_lib, terminal",
    [
        ("PhotovoltaicsWeccVoltageSource1", "photovoltaics_injector_terminal"),
        ("IECWT4BCurrentSource2020", "WT_wT4Injector_terminal"),
    ],
)
def test_a_unit_declaring_its_terminal_voltage_by_components_is_asked_for_them(
    tmp_path, sim_type, zone, generator_lib, terminal
):
    requests = _terminal_voltage_requests(tmp_path, generator_lib, sim_type, zone)

    assert requests == {
        f"{terminal}_V_re": ["Gen_GEN_VoltageInjTerminalRe"],
        f"{terminal}_V_im": ["Gen_GEN_VoltageInjTerminalIm"],
    }
