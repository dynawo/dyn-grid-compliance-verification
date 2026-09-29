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
from dycov.core.global_variables import MODEL_VALIDATION_PPM
from dycov.validate.producer import ModelProducer

_PRODUCER_INI = """[DEFAULT]
p_max_injection_at_PDR = 80
u_nom_at_PDR = 225
q_max_at_PDR = 40
q_min_at_PDR = -40
topology = S
"""


def _producer_reading(monkeypatch, ini_text: str) -> ModelProducer:
    producer = ModelProducer.__new__(ModelProducer)
    producer._s_nref = 100.0
    producer._sim_type = MODEL_VALIDATION_PPM
    producer_config = configparser.ConfigParser()
    producer_config.read_string(ini_text)
    monkeypatch.setattr(producer, "_ModelProducer__read_producer_ini", lambda: producer_config)
    producer._ModelProducer__init_parameters()
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
        _PRODUCER_INI + "p_min_injection_at_PDR = 8\np_min_consumption_at_PDR = 4\n",
    )

    assert producer.p_min_injection_pu == pytest.approx(0.08)
    assert producer.p_min_consumption_pu == pytest.approx(0.04)


def test_minimum_active_power_is_zero_when_the_ini_does_not_declare_it(monkeypatch):
    producer = _producer_reading(monkeypatch, _PRODUCER_INI)

    assert producer.p_min_injection_pu == 0.0
    assert producer.p_min_consumption_pu == 0.0


def test_the_operating_mode_selects_the_active_power_limits(monkeypatch):
    producer = _producer_reading(
        monkeypatch,
        _PRODUCER_INI + "p_max_consumption_at_PDR = 60\n"
        "p_min_injection_at_PDR = 8\np_min_consumption_at_PDR = 4\n",
    )

    producer.set_consumption(False)
    injection = (producer.p_max_pu, producer.p_min_pu)
    producer.set_consumption(True)
    consumption = (producer.p_max_pu, producer.p_min_pu)

    assert injection == pytest.approx((0.8, 0.08))
    assert consumption == pytest.approx((-0.6, -0.04))
