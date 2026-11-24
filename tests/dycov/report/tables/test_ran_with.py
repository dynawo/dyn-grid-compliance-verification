#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from pathlib import Path

import dycov
from dycov.report.tables import ran_with

_TEMPLATES = Path(dycov.__file__).resolve().parent / "templates"


def test_a_high_impedance_fault_shows_the_impedance_its_search_settled_on():
    results = {
        "ran_with": {
            "pdr_P": 0.6,
            "pdr_Q": 0.0,
            "pdr_U": 1.0,
            "SCR": 3.0,
            "line_RPu": 0.8292,
            "line_XPu": 8.292,
            "grid_lines": 1,
            "fault_RPu": 0.2539,
            "fault_XPu": 2.5391,
            "sim_t_event_start": 30.0,
            "fault_duration": 0.5,
            "hiz_dip": 0.7,
        }
    }

    assert ran_with.create_map(results, "InternalNode1") == [
        ["$P$ at InternalNode1", "60 MW (0.6 pu)"],
        ["$Q$ at InternalNode1", "0 Mvar (0 pu)"],
        ["$U$ at InternalNode1", "1 pu"],
        ["SCR of the grid", "3"],
        ["Resistance of the line of the grid", "0.8292 pu"],
        ["Reactance of the line of the grid", "8.292 pu"],
        ["Resistance of the fault", "0.2539 pu"],
        ["Reactance of the fault", "2.539 pu"],
        ["Start of the event", "30 s"],
        ["Duration of the event", "0.5 s"],
        ["Voltage dip the fault search aims at", "0.7 pu"],
        ["Base of the pu values", "100 MVA, nominal voltage"],
    ]


def test_a_permanent_fault_lasts_to_the_end_of_the_simulation():
    assert ran_with.format_value("fault_duration", {"fault_duration": 9999.0}) == "permanent"


def test_a_dip_of_the_grid_shows_its_short_circuit_impedance_and_the_voltages_of_its_stages():
    results = {
        "ran_with": {
            "Zcc": 0.0476,
            "sim_t_event_start": 30.0,
            "fault_duration": 0.15,
            "u_fault": 0.05,
            "u_clear": 0.05,
            "u_rec2": 0.85,
        }
    }

    rows = dict(ran_with.create_map(results, "the PDR"))

    assert rows["Short-circuit impedance of the grid, not modelled"] == "0.0476 pu"
    assert rows["Grid voltage during the fault"] == "0.05 pu"
    assert rows["Grid voltage when the fault clears"] == "0.05 pu"
    assert rows["Grid voltage at the second stage of recovery"] == "0.85 pu"
    assert rows["Base of the pu values"] == "100 MVA, nominal voltage"


def test_a_setpoint_step_shows_the_setpoint_and_its_step_at_the_bus():
    results = {
        "ran_with": {
            "pdr_P": -0.4,
            "sim_t_event_start": 20.0,
            "connect_event_to": "ActivePowerSetpointPu",
            "setpoint_step_value": 0.16,
        }
    }

    rows = dict(ran_with.create_map(results, "the PDR"))

    assert rows["$P$ at the PDR"] == "-40 MW (-0.4 pu)"
    assert rows["Stepped setpoint"] == r"\texttt{\detokenize{ActivePowerSetpointPu}}"
    assert rows["Step of the setpoint"] == "16 MW (0.16 pu)"


def test_a_voltage_step_is_in_pu_of_the_voltage():
    conditions = {"connect_event_to": "VoltageSetpointPu", "setpoint_step_value": 0.02}

    assert ran_with.format_value("setpoint_step_value", conditions) == "0.02 pu"


def test_the_events_of_the_grid_and_its_lines():
    results = {
        "ran_with": {
            "line_RPu": 0.0,
            "line_XPu": 0.4,
            "grid_lines": 4,
            "switched_SCR": 20.0,
            "switched_line_XPu": 0.1,
            "grid_phase_jump": 0.1047,
            "grid_voltage_step": -0.05,
            "grid_frequency0": 49.5,
            "grid_rocof": 2.0,
        }
    }

    rows = dict(ran_with.create_map(results, "InternalNode1"))

    assert rows["Reactance of each of the 4 lines of the grid"] == "0.4 pu"
    assert rows["SCR with the switched line in service"] == "20"
    assert rows["Reactance of the switched line"] == "0.1 pu"
    assert rows["Phase jump of the grid voltage"] == r"5.999$^\circ$ (0.1047 rad)"
    assert rows["Step of the grid voltage"] == "-0.05 pu"
    assert rows["Grid frequency before the event"] == "49.5 Hz"
    assert rows["Rate of change of the grid frequency"] == "2 Hz/s"


def test_a_test_that_was_not_simulated_has_no_conditions_to_show():
    assert ran_with.create_map({}, "the PDR") == []
    assert ran_with.create_map({"ran_with": {}}, "the PDR") == []


def test_a_value_that_is_not_a_number_is_left_out():
    results = {"ran_with": {"setpoint_step_value": "Pmax", "pdr_U": float("nan")}}

    assert ran_with.create_map(results, "the PDR") == []


def test_every_page_with_the_solver_of_its_simulation_shows_the_conditions_it_ran_with():
    pages = [
        page
        for page in _TEMPLATES.rglob("*.tex")
        if "for row in solver" in page.read_text(encoding="utf-8")
    ]

    assert pages
    assert [
        page for page in pages if "for row in ranwith" not in page.read_text(encoding="utf-8")
    ] == []


def test_a_grid_whose_lines_the_short_circuit_impedance_sizes_shows_it_as_modelled():
    rows = dict(ran_with.create_map({"ran_with": {"Zcc": 0.05, "grid_lines": 1}}, "the PDR"))

    assert rows["Short-circuit impedance of the grid"] == "0.05 pu"


def test_a_ramp_of_the_grid_frequency_shows_its_step_in_hz():
    rows = dict(ran_with.create_map({"ran_with": {"grid_frequency_step": 0.01}}, "the PDR"))

    assert rows["Step of the grid frequency"] == "0.5 Hz (0.01 pu)"
