#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the PAR set builders (``tools/dynawo_inputs/par/``), one per kind of equipment.

Every builder is pure, so they are exercised with the zone-sheet dicts from ``conftest``."""

from __future__ import annotations

import par
import pytest


def test_converter_par_set_prefix_control_snom(zone1, named):
    control = [{"name": "Kqp", "type": "DOUBLE", "value": "1"}]

    par_id, params = par.converter_par_set("PV_Array", "photovoltaics_", control, zone1, "100")

    values = named(params)
    assert par_id == "PV_Array"
    assert values["photovoltaics_Kqp"] == "1"  # control param, prefixed, value verbatim
    assert values["photovoltaics_ConverterLVControl"] == "true"
    assert values["photovoltaics_SNom"] == pytest.approx(100.0)
    # The model's own transformer is always emitted, from the group transformer's Z_cc_TG.
    assert values["photovoltaics_XLvTrPu"] == pytest.approx(0.1)
    assert values["photovoltaics_RLvTrPu"] == pytest.approx(0.0)


def test_converter_par_set_writes_ppclocal_only_for_the_plant_model(zone1, named):
    # PPCLocal has no template row: the plant (Zone3) models define it, the turbine ones do not.
    _id, turbine = par.converter_par_set("PV_Array", "photovoltaics_", [], zone1, "100")
    _id, plant = par.converter_par_set(
        "PV_Array", "photovoltaics_", [], zone1, "100", plant_model=True
    )

    assert "photovoltaics_PPCLocal" not in named(turbine)
    assert named(plant)["photovoltaics_PPCLocal"] == "false"
    assert next(p for p in plant if p["name"].endswith("PPCLocal"))["type"] == "BOOL"


def test_converter_par_set_lvtr_is_on_the_model_base_not_snref(zone1, named):
    # Z_cc_TG is pu on SnZone1 and the model reads RLvTrPu on its own SNom, so the value is never
    # rebased to SnRef and comes out the same for the turbine and the plant.
    zone1.update({"SnZone1": "4", "Z_cc_TG": "0.06185", "R_cc_TG / X_cc_TG": "0.25"})

    _id, turbine = par.converter_par_set("Wind_Turbine", "WT4B_", [], zone1, zone1["SnZone1"])
    _id, plant = par.converter_par_set("Wind_Turbine", "WTG4B_", [], zone1, "90", plant_model=True)

    assert named(turbine)["WT4B_XLvTrPu"] == pytest.approx(0.06, abs=1e-4)
    assert named(turbine)["WT4B_RLvTrPu"] == pytest.approx(0.015, abs=1e-4)
    assert named(plant)["WTG4B_XLvTrPu"] == named(turbine)["WT4B_XLvTrPu"]
    assert named(plant)["WTG4B_SNom"] == pytest.approx(90.0)


def test_converter_par_set_writes_the_model_transformer_whatever_the_flag(zone1, named):
    # The parameters have no Dynawo default, so they are written even when the model zeroes the
    # branch and the external block carries the transformer (ConverterLVControl=True).
    zone1.update({"ConverterLVControl": "False", "Z_cc_TG": "0.05"})

    _id, params = par.converter_par_set("PV_Array", "photovoltaics_", [], zone1, "100")

    values = named(params)
    assert values["photovoltaics_ConverterLVControl"] == "false"
    assert values["photovoltaics_XLvTrPu"] == pytest.approx(0.05)  # Z_cc_TG, on the model's base
    assert values["photovoltaics_RLvTrPu"] == pytest.approx(0.0)


def test_main_transformer_par_set(zone3, named):
    _par_id, params = par.main_transformer_par_set("Main_Xfmr", zone3)

    values = named(params)
    assert values["transformer_XPu"] == pytest.approx(0.18)
    assert values["transformer_RPu"] == pytest.approx(0.0)
    assert values["transformer_SNom"] == pytest.approx(100.0)
    assert values["transformer_NbTap"] == 21
    assert values["transformer_Tap0"] == 10
    assert values["transformer_RatioTfoMinPu"] == pytest.approx(0.9)


def test_group_transformer_par_set_fixed_ratio(zone1, named):
    # Z_cc_TG=0.1 on base SnZone1=100 -> XPu=0.1; from Zone1a in both zones (base = s_nom).
    _par_id, params = par.group_transformer_par_set("Group_Xfmr", zone1, zone1["SnZone1"])

    values = named(params)
    assert values["transformer_XPu"] == pytest.approx(0.1)
    assert values["transformer_rTfoPu"] == pytest.approx(1.0)
    assert "transformer_NbTap" not in values  # fixed ratio -> no taps


def test_aux_transformer_par_set_is_on_the_auxiliary_base(zone3, named):
    # Z_cc_TA is pu on Sn_A (2 MVA) and the block is written on SnRef = 100, so it scales up.
    _par_id, params = par.aux_transformer_par_set("AuxLoad_Xfmr", zone3)

    values = named(params)
    assert values["transformer_XPu"] == pytest.approx(0.1 * 100 / 2)
    assert values["transformer_rTfoPu"] == pytest.approx(1.0)


def test_aux_load_par_set(zone3, named):
    _par_id, load = par.aux_load_par_set("Aux_Load", zone3)

    values = named(load)
    assert values["load_PRefPu"] == pytest.approx(0.01)  # P_A=1 MW / 100
    assert values["load_QRefPu"] == pytest.approx(0.005)
    assert values["load_alpha"] == pytest.approx(1.5)


def test_collector_line_par_set_uses_the_pdr_voltage_as_base(zone3, named):
    # The collector rows are in ohms and siemens; its base is Un_PDR, the node it connects to.
    _par_id, line = par.collector_line_par_set("IntNetwork_Line", zone3)

    z_base = float(zone3["Un_PDR"]) ** 2 / 100.0
    assert named(line)["line_XPu"] == pytest.approx(1.0 / z_base)
    assert named(line)["line_BPu"] == pytest.approx(0.0)
