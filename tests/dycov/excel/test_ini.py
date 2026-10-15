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


def _read(path):
    parser = configparser.ConfigParser(inline_comment_prefixes=("#",))
    parser.read(path)
    return {key: value.strip() for key, value in parser["DEFAULT"].items()}


def _write(tmp_path, zone1, zone3, gen_id="PV_Array", include_consumption=False):
    for zone in ("Zone1", "Zone3"):
        (tmp_path / zone).mkdir(exist_ok=True)
    ini.write_ini(
        tmp_path,
        "Producer",
        "S+Aux",
        zone1,
        zone3,
        gen_id,
        include_consumption=include_consumption,
    )
    return _read(tmp_path / "Zone1" / "Producer.ini"), _read(tmp_path / "Zone3" / "Producer.ini")


def test_each_zone_declares_the_node_it_connects_at(tmp_path, zone1, zone3):
    # Zone1 connects at its internal node (Un1) and Zone3 at the PDR (Un_PDR): never the
    # converter's own Un2.
    z1, z3 = _write(tmp_path, zone1, zone3)

    assert (z1["u_nom"], z3["u_nom"]) == (zone1["Un1"], zone3["Un_PDR"])
    assert z1["p_max_injection"] == zone1["Pmax_injection_z1"]
    assert z3["p_max_injection"] == zone3["Pmax_injection_PDR"]
    assert (z1["q_min"], z3["q_min"]) == (zone1["Qmin_z1"], zone3["Qmin_PDR"])


def test_zone1_describes_its_own_node_and_not_the_pdr(tmp_path, zone1, zone3):
    # Zone 1's node is internal to the plant, so neither the PDR nor its list of levels applies.
    _write(tmp_path, zone1, zone3)

    text = (tmp_path / "Zone1" / "Producer.ini").read_text()

    assert "declared at InternalNode1" in text
    assert "declared at the PDR" not in text
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

    assert z1["p_max_consumption"] == "0.333"
    assert z3["p_max_consumption"] == "40"


def test_a_non_storage_model_declares_no_consumption(tmp_path, zone1, zone3):
    z1, z3 = _write(tmp_path, zone1, zone3)

    assert "p_max_consumption" not in z1
    assert "p_max_consumption" not in z3


def test_zone3_declares_the_minimum_injection_the_f16_tests_start_from(tmp_path, zone1, zone3):
    zone3["Pmin_injection_PDR"] = "7.5"

    z1, z3 = _write(tmp_path, zone1, zone3)

    assert z3["p_min_injection"] == "7.5"
    assert "p_min_injection" not in z1


def test_an_empty_minimum_injection_stays_commented_out(tmp_path, zone1, zone3):
    zone3["Pmin_injection_PDR"] = None

    _z1, z3 = _write(tmp_path, zone1, zone3)

    assert "p_min_injection" not in z3
    assert "# p_min_injection =" in (tmp_path / "Zone3" / "Producer.ini").read_text()


def test_storage_declares_its_minimum_consumption_in_zone3(tmp_path, zone1, zone3):
    zone1["Pmax_soutirage_z1"] = "0.333"
    zone3["Pmax_soutirage_PDR"] = "40"
    zone3["Pmin_soutirage_PDR"] = "4"

    z1, z3 = _write(tmp_path, zone1, zone3, gen_id="Bess", include_consumption=True)

    assert z3["p_min_consumption"] == "4"
    assert "p_min_consumption" not in z1


def test_a_non_storage_model_ignores_the_minimum_consumption(tmp_path, zone1, zone3):
    zone3["Pmin_soutirage_PDR"] = "4"

    _z1, z3 = _write(tmp_path, zone1, zone3)

    assert "p_min_consumption" not in z3
