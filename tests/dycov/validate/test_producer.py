#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the ModelProducer helpers."""

import configparser

import pytest

from dycov.configuration.cfg import Config
from dycov.core.global_variables import MODEL_VALIDATION_BESS, MODEL_VALIDATION_PPM
from dycov.model.parameters import GenParams, Terminal
from dycov.validate.producer import ModelProducer

_PRODUCER_INI = """[DEFAULT]
p_max_injection = 80
u_nom = 225
q_max = 40
q_min = -40
topology = S
"""


def _producer_reading(
    monkeypatch, ini_text: str, sim_type: int = MODEL_VALIDATION_PPM
) -> ModelProducer:
    producer = ModelProducer.__new__(ModelProducer)
    producer._s_nref = 100.0
    producer._sim_type = sim_type
    producer_config = configparser.ConfigParser()
    producer_config.read_string(ini_text)
    monkeypatch.setattr(producer, "_ModelProducer__read_producer_ini", lambda: producer_config)
    producer._ModelProducer__init_parameters()
    return producer


def _make_generator(converter_lv_control: bool) -> GenParams:
    return GenParams(
        id="PV_Array",
        lib="",
        terminals=(Terminal(connected_equipment=""),),
        par_id="",
        s_nom=100.0,
        i_max=1.0,
        p=0.0,
        q=0.0,
        voltage_droop=0.0,
        use_voltage_droop=False,
        converter_lv_control=converter_lv_control,
    )


def _producer_with_model(*generators: GenParams) -> ModelProducer:
    producer = ModelProducer.__new__(ModelProducer)
    producer._is_dynawo_model = True
    producer.generators = list(generators)
    return producer


def test_s_nom_pu_is_snom_over_snref():
    producer = ModelProducer.__new__(ModelProducer)
    producer.s_nom = 180.0
    producer._s_nref = 100.0

    assert producer.s_nom_pu == pytest.approx(1.8)


def test_init_reads_s_nref_from_the_dynawo_section(monkeypatch):
    monkeypatch.setattr(
        Config,
        "get_float",
        lambda self, section, key, default: (
            90.0 if (section, key) == ("Dynawo", "s_nref") else default
        ),
    )

    producer = ModelProducer(None, None, None, -1)

    assert producer._s_nref == pytest.approx(90.0)


def test_minimum_active_power_is_read_in_pu_of_s_nref(monkeypatch):
    producer = _producer_reading(
        monkeypatch,
        _PRODUCER_INI + "p_min_injection = 8\np_min_consumption = 4\n",
    )

    assert producer.p_min_injection_pu == pytest.approx(0.08)
    assert producer.p_min_consumption_pu == pytest.approx(0.04)


def test_minimum_active_power_is_zero_when_the_ini_does_not_declare_it(monkeypatch):
    producer = _producer_reading(monkeypatch, _PRODUCER_INI)

    assert producer.p_min_injection_pu == 0.0
    assert producer.p_min_consumption_pu == 0.0


def test_a_key_of_the_retired_naming_is_rejected_by_the_name_to_use(monkeypatch):
    ini_text = _PRODUCER_INI.replace("u_nom = 225", "u_nom_at_PDR = 225")

    with pytest.raises(ValueError, match="migrate_inputs.*rename it to u_nom"):
        _producer_reading(monkeypatch, ini_text)


def test_a_missing_magnitude_is_reported_by_its_name(monkeypatch):
    ini_text = _PRODUCER_INI.replace("q_max = 40\n", "")

    with pytest.raises(ValueError, match="must specify the q_max"):
        _producer_reading(monkeypatch, ini_text)


def test_storage_must_declare_the_consumption_limit(monkeypatch):
    with pytest.raises(ValueError, match="must specify the p_max_consumption"):
        _producer_reading(monkeypatch, _PRODUCER_INI, MODEL_VALIDATION_BESS)


def test_the_operating_mode_selects_the_active_power_limits(monkeypatch):
    producer = _producer_reading(
        monkeypatch,
        _PRODUCER_INI + "p_max_consumption = 60\np_min_injection = 8\np_min_consumption = 4\n",
    )

    producer.set_consumption(False)
    injection = (producer.p_max_pu, producer.p_min_pu)
    producer.set_consumption(True)
    consumption = (producer.p_max_pu, producer.p_min_pu)

    assert injection == pytest.approx((0.8, 0.08))
    assert consumption == pytest.approx((-0.6, -0.04))


@pytest.mark.parametrize("converter_lv_control", [True, False])
def test_the_controlled_node_is_the_converter_lv_control_flag_of_the_model(converter_lv_control):
    producer = _producer_with_model(_make_generator(converter_lv_control))

    assert producer.controls_internal_node2() is converter_lv_control


def test_the_controlled_node_is_internal_node1_when_a_unit_controls_it():
    producer = _producer_with_model(_make_generator(True), _make_generator(False))

    assert producer.controls_internal_node2() is False


def test_the_controlled_node_keeps_the_flag_default_for_curves_without_a_model():
    producer = ModelProducer.__new__(ModelProducer)
    producer._is_dynawo_model = False

    assert producer.controls_internal_node2() is True


def test_get_filenames_of_a_zone_not_delivered_is_empty(tmp_path):
    (tmp_path / "Zone3").mkdir()
    (tmp_path / "Zone3" / "Producer.dyd").write_text("")
    producer = ModelProducer.__new__(ModelProducer)
    producer._producer_model_path = tmp_path
    producer._producer_curves_path = None

    assert producer.get_filenames(zone=1) == []
    assert producer.get_filenames(zone=3) == ["Producer"]
