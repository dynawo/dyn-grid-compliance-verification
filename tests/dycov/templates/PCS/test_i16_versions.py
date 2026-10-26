#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The DTR gives the Fiche I16 of a storage installation in two versions: Fiche I16.1 for type B,
which the PCS descriptions carry, and Fiche I16.2 for types C and D, which patches them. The
version Type C/D drops the faults and the steps of the grid voltage of type B from Zone 1, whose
setpoint steps run with a grid of short-circuit ratio 2, and simulates there the tests of the
Fiche I18 (Grid Forming); it drops the fault of the Fiche I5 from Zone 3, and filters the curves
at 30 Hz with a common sampling interval of 1 ms."""

from pathlib import Path

import pytest

import dycov
from dycov.configuration.cfg import config
from dycov.model.pcs import _version_for_type

_BESS = Path(dycov.__file__).resolve().parent / "templates" / "PCS" / "model" / "BESS"
_SETPOINT_STEPS = [
    f"{magnitude}{mode}"
    for mode in ("Injection", "Consumption")
    for magnitude in ("Active", "Reactive", "Voltage")
]


@pytest.fixture
def load_version():
    def load(pcs: str, installation_type: str) -> None:
        version = _version_for_type(_BESS / pcs, installation_type)
        config.load_pcs_config(_BESS / pcs / "PCSDescription.ini", None, version)

    yield load
    config.load_pcs_config(None)


_I18_TESTS = (
    [f"S_VolAngStep{n}" for n in range(1, 13)]
    + [f"S_VolAmpStep{n}" for n in range(1, 7)]
    + ["S_SCRup1", "S_SCRdown1"]
    + [f"S_Rocof{n}" for n in range(1, 13)]
    + ["S_Fault4", "S_Fault5", "S_Fault6"]
)


def _operating_conditions(benchmark):
    return config.get_list("PCS-OperatingConditions", f"PCS_RTE-I16z1.{benchmark}")


@pytest.mark.parametrize("installation_type", ["C", "D"])
def test_zone1_of_types_c_and_d_runs_the_setpoint_steps_on_a_weak_grid(
    load_version, installation_type
):
    load_version("PCS_RTE-I16z1", installation_type)

    benchmarks = config.get_list("PCS-Benchmarks", "PCS_RTE-I16z1")
    assert benchmarks[0] == "SetPointStep"
    assert "ThreePhaseFault" not in benchmarks
    assert "GridVoltageStep" not in benchmarks
    for oc in _SETPOINT_STEPS:
        assert config.get_float(f"PCS_RTE-I16z1.SetPointStep.{oc}.Model", "SCR", 0) == 2
    assert config.get_value("PCS_RTE-I16z1", "report_name") == "report.RTE-I16z1.TypeCD.tex"


def test_zone1_of_types_c_and_d_simulates_the_tests_of_the_fiche_i18(load_version):
    load_version("PCS_RTE-I16z1", "C")

    assert config.get_list("PCS-Benchmarks", "PCS_RTE-I16z1")[1:] == _I18_TESTS
    assert _operating_conditions("S_VolAngStep1") == ["OC1", "OC2", "OC3", "OC4", "OC5"]
    assert _operating_conditions("S_VolAmpStep1")[-2:] == ["OC6", "OC7"]
    assert _operating_conditions("S_Fault4")[:3] == ["OC1_SCR2", "OC1_SCR10", "OC1_SCR20"]


def test_every_test_of_the_fiche_i18_runs_for_oc2_and_oc3_and_the_others_when_recorded(
    load_version,
):
    load_version("PCS_RTE-I16z1", "C")

    for benchmark in _I18_TESTS:
        for oc in _operating_conditions(benchmark):
            recorded_only = config.get_boolean(
                f"PCS_RTE-I16z1.{benchmark}.{oc}", "only_with_reference", False
            )
            assert recorded_only is not oc.startswith(("OC2", "OC3")), f"{benchmark}.{oc}"


@pytest.mark.parametrize(
    "benchmark, tracked, scr, event",
    [
        ("S_VolAngStep1", "active_current", 10, ("grid_phase_jump", "0.3*(Xeff+Xgrid)")),
        ("S_VolAngStep8", "active_current", 2, ("grid_phase_jump", "-0.6*(Xeff+Xgrid)")),
        ("S_VolAmpStep6", "reactive_current", 20, ("grid_voltage_step", "-0.15*(Xeff+Xgrid)")),
        ("S_Rocof7", "active_current", 10, ("grid_rocof", "2.0")),
    ],
)
def test_a_test_of_the_fiche_i18_is_set_up_as_its_tables_define_it(
    load_version, benchmark, tracked, scr, event
):
    load_version("PCS_RTE-I16z1", "C")
    section = f"PCS_RTE-I16z1.{benchmark}.OC2"

    assert config.get_value(section, "tracked_magnitude") == tracked
    assert config.get_float(f"{section}.Model", "SCR", 0) == scr
    assert config.get_value(f"{section}.Model", "pdr_P") == "0.5*Snom"
    assert config.get_value(f"{section}.Event", event[0]) == event[1]


def test_a_jump_of_the_short_circuit_ratio_switches_a_line_between_2_and_20(load_version):
    load_version("PCS_RTE-I16z1", "C")

    for benchmark, bench in (
        ("S_SCRup1", "SCRStepUp_2Lines_InfBus"),
        ("S_SCRdown1", "SCRStepDown_2Lines_InfBus"),
    ):
        assert config.get_value(f"PCS_RTE-I16z1.{benchmark}", "TSO_model") == bench
        model = f"PCS_RTE-I16z1.{benchmark}.OC3.Model"
        assert config.get_float(model, "SCR", 0) == 2
        assert config.get_float(model, "switched_SCR", 0) == 20


def test_zone3_of_types_c_and_d_has_neither_the_fault_nor_the_frequency_ramp(load_version):
    load_version("PCS_RTE-I16z3", "C")

    assert config.get_list("PCS-Benchmarks", "PCS_RTE-I16z3") == [
        "USetPointStep",
        "PSetPointStep",
        "QSetPointStep",
        "GridVoltageDip",
        "GridVoltageSwell",
        "Islanding",
    ]


@pytest.mark.parametrize("pcs", ["PCS_RTE-I16z1", "PCS_RTE-I16z3"])
def test_types_c_and_d_filter_at_30_hz_every_millisecond(load_version, pcs):
    load_version(pcs, "D")

    assert config.get_float("GridCode", "cutoff", 0) == 30.0
    assert config.get_float("GridCode", "t_com", 0) == 0.001


@pytest.mark.parametrize("pcs", ["PCS_RTE-I16z1", "PCS_RTE-I16z3"])
def test_type_b_keeps_the_fiche_the_descriptions_carry(load_version, pcs):
    load_version(pcs, "B")

    assert _version_for_type(_BESS / pcs, "B") is None
    assert "ThreePhaseFault" in config.get_list("PCS-Benchmarks", pcs)
    assert config.get_float("GridCode", "cutoff", 0) == 15.0
