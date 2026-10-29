#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The Fiche I16 of a storage installation, in the two versions the revision 20260723 gives it.

The revision splits the fiche into the Fiche I16.1 for type B, the base with what its delta writes
over it, and the Fiche I16.2 for types C and D, which patches the description the revision gives
type B, its delta when it writes one. The version Type C/D drops
the faults and the steps of the grid voltage of type B from Zone 1, whose setpoint steps run with
a grid of short-circuit ratio 2, and simulates there the tests of the Fiche I18 (Grid Forming),
compared at InternalNode1; it drops the fault of the Fiche I5 and the ramp of the grid frequency
from Zone 3, and filters the curves at 30 Hz with a common sampling interval of 1 ms. The base
revision has no Fiche I16.2, because it has no Fiche I18.
"""

from pathlib import Path

import pytest

import dycov
from dycov.configuration.cfg import config
from dycov.model.pcs import _version_for_category
from dycov.validation import compared_curves

REVISION = "20260723"
TEMPLATES = Path(dycov.__file__).resolve().parent / "templates"
_DELTA = TEMPLATES / "revisions" / REVISION
_SETPOINT_STEPS = [
    f"{magnitude}{mode}"
    for mode in ("Injection", "Consumption")
    for magnitude in ("Active", "Reactive", "Voltage")
]
_I18_TESTS = (
    [f"S_VolAngStep{n}" for n in range(1, 13)]
    + [f"S_VolAmpStep{n}" for n in range(1, 7)]
    + ["S_SCRup1", "S_SCRdown1"]
    + [f"S_Rocof{n}" for n in range(1, 13)]
    + ["S_Fault4", "S_Fault5", "S_Fault6"]
)


def _delta_of(pcs: str, name: str) -> Path | None:
    path = _DELTA / "PCS" / "model" / "BESS" / pcs / name
    return path if path.is_file() else None


@pytest.fixture
def version(revision):
    """Loads a storage PCS as the tool loads it under the revision 20260723 for the category of
    an installation: the base, the delta of the revision, and the version for that category."""

    def load(pcs: str, category: str) -> None:
        revision(REVISION)
        config.load_pcs_config(
            TEMPLATES / "PCS" / "model" / "BESS" / pcs / "PCSDescription.ini",
            None,
            _delta_of(pcs, "PCSDescription.ini"),
            _version_for_category(_DELTA / "PCS" / "model" / "BESS" / pcs, category),
        )

    yield load
    config.load_pcs_config(None)


def _operating_conditions(benchmark):
    return config.get_list("PCS-OperatingConditions", f"PCS_RTE-I16z1.{benchmark}")


def test_the_base_revision_has_no_version_of_a_fiche_by_category():
    """Before the revision 20260723 a storage installation of any type takes the Fiche I16."""
    assert not sorted((TEMPLATES / "PCS").glob("*/*/*/Type*.ini"))
    assert _version_for_category(_DELTA / "PCS" / "model" / "BESS" / "PCS_RTE-I16z1", "C")


@pytest.mark.parametrize("category", ["C", "D"])
def test_zone1_of_types_c_and_d_runs_the_setpoint_steps_on_a_weak_grid(version, category):
    version("PCS_RTE-I16z1", category)

    benchmarks = config.get_list("PCS-Benchmarks", "PCS_RTE-I16z1")
    assert benchmarks[0] == "SetPointStep"
    assert "ThreePhaseFault" not in benchmarks
    assert "GridVoltageStep" not in benchmarks
    for oc in _SETPOINT_STEPS:
        assert config.get_float(f"PCS_RTE-I16z1.SetPointStep.{oc}.Model", "SCR", 0) == 2
    assert config.get_value("PCS_RTE-I16z1", "report_name") == "report.RTE-I16z1.TypeCD.tex"


def test_zone1_of_types_c_and_d_simulates_the_tests_of_the_fiche_i18(version):
    version("PCS_RTE-I16z1", "C")

    assert config.get_list("PCS-Benchmarks", "PCS_RTE-I16z1")[1:] == _I18_TESTS
    assert _operating_conditions("S_VolAngStep1") == ["OC1", "OC2", "OC3", "OC4", "OC5"]
    assert _operating_conditions("S_VolAmpStep1")[-2:] == ["OC6", "OC7"]
    assert _operating_conditions("S_Fault4")[:3] == ["OC1_SCR2", "OC1_SCR10", "OC1_SCR20"]


def test_every_test_of_the_fiche_i18_runs_for_oc2_and_oc3_and_the_others_when_recorded(version):
    version("PCS_RTE-I16z1", "C")

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
    version, benchmark, tracked, scr, event
):
    version("PCS_RTE-I16z1", "C")
    section = f"PCS_RTE-I16z1.{benchmark}.OC2"

    assert config.get_value(section, "tracked_magnitude") == tracked
    assert config.get_float(f"{section}.Model", "SCR", 0) == scr
    assert config.get_value(f"{section}.Model", "pdr_P") == "0.5*Snom"
    assert config.get_value(f"{section}.Event", event[0]) == event[1]


def test_a_jump_of_the_short_circuit_ratio_switches_a_line_between_2_and_20(version):
    version("PCS_RTE-I16z1", "C")

    for benchmark, bench in (
        ("S_SCRup1", "SCRStepUp_2Lines_InfBus"),
        ("S_SCRdown1", "SCRStepDown_2Lines_InfBus"),
    ):
        assert config.get_value(f"PCS_RTE-I16z1.{benchmark}", "TSO_model") == bench
        model = f"PCS_RTE-I16z1.{benchmark}.OC3.Model"
        assert config.get_float(model, "SCR", 0) == 2
        assert config.get_float(model, "switched_SCR", 0) == 20


def test_zone1_of_types_c_and_d_compares_the_curves_of_internal_node1(version):
    """The references are the results of the Fiche I18, which the fiche observes at the output
    of the unit, after its transformer."""
    version("PCS_RTE-I16z1", "C")

    assert [curve.selector for curve in compared_curves.for_zone(1)] == [
        "BusPDR_BUS_Voltage",
        "BusPDR_BUS_ActivePower",
        "BusPDR_BUS_ReactivePower",
        "BusPDR_BUS_ActiveCurrent",
        "BusPDR_BUS_ReactiveCurrent",
    ]
    assert config.get_list("ReportCurves", "fig_InternalNode1P") == []


def test_a_ramp_of_the_frequency_draws_the_frequency_the_unit_gives(version):
    """A Grid Forming converter gives its frequency as the network frequency it runs at, which
    is what the figure of the network frequency draws: it has no rotor speed."""
    version("PCS_RTE-I16z1", "C")

    rocof_tests = [f"PCS_RTE-I16z1.S_Rocof{n}" for n in range(1, 13)]
    assert config.get_list("ReportCurves", "fig_WRef") == rocof_tests
    assert config.get_list("ReportCurves", "fig_W") == []


def test_zone1_of_type_b_compares_the_curves_of_the_fiche_i16_1(version):
    version("PCS_RTE-I16z1", "B")

    selectors = [curve.selector for curve in compared_curves.for_zone(1)]
    assert "_GEN_ActiveCurrentNode2" in selectors
    assert "_GEN_ActivePowerControlledNode" in selectors


def test_zone3_of_types_c_and_d_has_neither_the_fault_nor_the_frequency_ramp(version):
    version("PCS_RTE-I16z3", "C")

    assert config.get_list("PCS-Benchmarks", "PCS_RTE-I16z3") == [
        "USetPointStep",
        "PSetPointStep",
        "QSetPointStep",
        "GridVoltageDip",
        "GridVoltageSwell",
        "Islanding",
    ]


def test_zone3_of_types_c_and_d_keeps_what_the_revision_writes_for_type_b(version):
    """The version patches the delta, so the swell at Q = 0 of the revision still applies."""
    version("PCS_RTE-I16z3", "D")

    assert config.get_list("PCS-OperatingConditions", "PCS_RTE-I16z3.GridVoltageSwell") == [
        "QzeroInjection",
        "QzeroConsumption",
    ]


@pytest.mark.parametrize("pcs", ["PCS_RTE-I16z1", "PCS_RTE-I16z3"])
def test_types_c_and_d_filter_at_30_hz_every_millisecond(version, pcs):
    version(pcs, "D")

    assert config.get_float("GridCode", "cutoff", 0) == 30.0
    assert config.get_float("GridCode", "t_com", 0) == 0.001


@pytest.mark.parametrize("pcs", ["PCS_RTE-I16z1", "PCS_RTE-I16z3"])
def test_type_b_keeps_the_fiche_the_revision_writes_for_it(version, pcs):
    version(pcs, "B")

    assert _version_for_category(_DELTA / "PCS" / "model" / "BESS" / pcs, "B") is None
    assert "ThreePhaseFault" in config.get_list("PCS-Benchmarks", pcs)
    assert config.get_float("GridCode", "cutoff", 0) == 15.0
    assert not config.get_boolean("GridCode", "zone1_compared_at_node1", False)


@pytest.mark.parametrize("pcs", ["PCS_RTE-I16z1", "PCS_RTE-I16z3"])
def test_every_test_of_the_version_carries_its_report_template_in_the_delta(version, pcs):
    """The version and the templates of its tests travel together, in the delta: a test whose
    template the version names finds it there, and every other one in the shipped templates."""
    version(pcs, "C")
    shipped = TEMPLATES / "reports" / "model" / "BESS" / pcs
    delta = _DELTA / "reports" / "model" / "BESS" / pcs

    missing = [config.get_value(pcs, "report_name")]
    for benchmark in config.get_list("PCS-Benchmarks", pcs):
        for oc in config.get_list("PCS-OperatingConditions", f"{pcs}.{benchmark}"):
            missing.append(config.get_value(f"{pcs}.{benchmark}.{oc}", "report_name"))

    missing = sorted(
        {
            report
            for report in missing
            if not (delta / report).is_file()
            and ("TypeCD" in report or not (shipped / report).is_file())
        }
    )
    assert not missing
