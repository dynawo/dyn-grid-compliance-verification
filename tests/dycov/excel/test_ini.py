#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the INI side (``dycov/excel/producer_ini.py``): each zone's own limits."""

from __future__ import annotations

import configparser

from dycov.excel import producer_ini as ini


def _read_ini(path):
    """Helper to read the generated INI file and return its DEFAULT section as a dict."""
    parser = configparser.ConfigParser()
    parser.read(path)
    return dict(parser["DEFAULT"])


def _write(tmp_path, zone1, zone3, gen_id="PV_Array", include_consumption=False):
    for zone in ("Zone1", "Zone3"):
        (tmp_path / zone).mkdir(exist_ok=True)

    # Wrap the single test generator into the new list format
    generators = [{"gen_id": gen_id, "zone1_data": zone1}]

    ini.write_ini(
        tmp_path,
        "Producer",
        "S+Aux",
        generators,
        zone3,
        include_consumption=include_consumption,
    )

    # Read and return the generated INI files as dictionaries so tests can subscript them
    return (
        _read_ini(tmp_path / "Zone1" / "Producer.ini"),
        _read_ini(tmp_path / "Zone3" / "Producer.ini"),
    )


def test_each_zone_declares_the_node_it_connects_at(tmp_path, zone1, zone3):
    # Zone1 connects at its internal node (Un1) and Zone3 at the PDR (Un_PDR): never the
    # converter's own Un2.
    z1, z3 = _write(tmp_path, zone1, zone3)

    assert (z1["u_nom_at_pdr"], z3["u_nom_at_pdr"]) == (zone1["Un1"], zone3["Un_PDR"])
    assert z1["p_max_injection_at_pdr"] == zone1["Pmax_injection_z1"]
    assert z3["p_max_injection_at_pdr"] == zone3["Pmax_injection_PDR"]
    assert (z1["q_min_at_pdr"], z3["q_min_at_pdr"]) == (zone1["Qmin_z1"], zone3["Qmin_PDR"])


def test_zone1_describes_its_own_node_and_not_the_pdr(tmp_path, zone1, zone3):
    # Zone 1's node is internal to the plant, so neither the PDR nor its list of levels applies.
    _write(tmp_path, zone1, zone3)

    text = (tmp_path / "Zone1" / "Producer.ini").read_text()

    assert "# u_nom is the nominal voltage of Zone 1's internal node (Node 1), in kV" in text
    assert "Allowed values" not in text


def test_zone1_is_a_single_unit_whatever_the_plant_topology(tmp_path, zone1, zone3):
    z1, z3 = _write(tmp_path, zone1, zone3)

    assert (z1["topology"], z3["topology"]) == ("S", "S+Aux")


def test_the_power_sharing_is_keyed_by_the_generator_block(tmp_path, zone1, zone3):
    z1, _z3 = _write(tmp_path, zone1, zone3, gen_id="Bess")

    assert z1["p_sharing_bess"] == zone1["P_share"]
    assert z1["q_sharing_bess"] == zone1["Q_share"]


def test_storage_declares_its_consumption_in_both_zones(tmp_path, zone1, zone3):
    # DyCoV rejects a BESS INI without the consumption limit, and each zone takes its own row:
    # the Zone1a one is per unit, the Zone3 one is the whole plant.
    zone1["Pmax_soutirage_z1"] = "0.333"
    zone3["Pmax_soutirage_PDR"] = "40"

    z1, z3 = _write(tmp_path, zone1, zone3, gen_id="Bess", include_consumption=True)

    assert z1["p_max_consumption_at_pdr"] == "0.333"
    assert z3["p_max_consumption_at_pdr"] == "40"


def test_a_non_storage_model_declares_no_consumption(tmp_path, zone1, zone3):
    z1, z3 = _write(tmp_path, zone1, zone3)

    assert "p_max_consumption_at_pdr" not in z1
    assert "p_max_consumption_at_pdr" not in z3
