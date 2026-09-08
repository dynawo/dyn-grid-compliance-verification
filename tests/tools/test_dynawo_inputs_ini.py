#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the INI side (``tools/dynawo_inputs/producer_ini.py``): each zone's own limits."""

from __future__ import annotations

import configparser

import producer_ini as ini


def _read(path):
    parser = configparser.ConfigParser(inline_comment_prefixes=("#",))
    parser.read(path)
    return {key: value.strip() for key, value in parser["DEFAULT"].items()}


def _write(tmp_path, zone1, zone3, gen_id="PV_Array", include_consumption=False):
    for zone in ("Zone1", "Zone3"):
        (tmp_path / zone).mkdir(exist_ok=True)
    ini.write_ini(
        tmp_path, "Producer", "S+Aux", zone1, zone3, gen_id,
        include_consumption=include_consumption,
    )
    return _read(tmp_path / "Zone1" / "Producer.ini"), _read(tmp_path / "Zone3" / "Producer.ini")


def test_each_zone_declares_the_node_it_connects_at(tmp_path, zone1, zone3):
    # Zone1 connects at its internal node (Un1) and Zone3 at the PDR (Un_PDR): never the
    # converter's own Un2.
    z1, z3 = _write(tmp_path, zone1, zone3)

    assert (z1["u_nom_at_pdr"], z3["u_nom_at_pdr"]) == (zone1["Un1"], zone3["Un_PDR"])
    assert z1["p_max_injection_at_pdr"] == zone1["Pmax_injection_z1"]
    assert z3["p_max_injection_at_pdr"] == zone3["Pmax_injection_PDR"]
    assert (z1["q_min_at_pdr"], z3["q_min_at_pdr"]) == (zone1["Qmin_z1"], zone3["Qmin_PDR"])


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
