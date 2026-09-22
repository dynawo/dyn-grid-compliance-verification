#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#

from pathlib import Path

from dycov.configuration.cfg import Config
from dycov.model.producer import Producer

_CONFIG_VALUES = {("Dynawo", "s_nref"): 90.0, ("Dynawo", "f_nom"): 60.0}


def _make_producer(monkeypatch):
    monkeypatch.setattr(
        Config,
        "get_float",
        lambda self, section, key, default: _CONFIG_VALUES.get((section, key), default),
    )

    return Producer(Path("/tmp/model"), Path("/tmp/ini/producer.ini"))


def test_initialize_reads_config_from_the_dynawo_section(monkeypatch):
    producer = _make_producer(monkeypatch)

    assert producer._s_nref == 90.0
    assert producer._f_nom == 60.0
    assert producer._producer_model_path == Path("/tmp/model")
    assert producer._producer_ini_path == Path("/tmp/ini")
    assert producer._sim_type is None


def test_initialize_without_ini(monkeypatch):
    monkeypatch.setattr(Config, "get_float", lambda *args, **kwargs: 50.0)

    producer = Producer(Path("/tmp/model"), None)

    assert producer._producer_ini_path is None


def test_is_gfm_when_sim_type_none(monkeypatch):
    producer = _make_producer(monkeypatch)

    assert producer.is_gfm() is True


def test_is_gfm_when_sim_type_set(monkeypatch):
    producer = _make_producer(monkeypatch)
    producer._sim_type = 1

    assert producer.is_gfm() is False


def test_stub_methods_return_none(monkeypatch):
    producer = _make_producer(monkeypatch)

    assert producer.get_producer_path() is None
    assert producer.get_filenames() is None
    assert producer.get_filenames(zone=1) is None
    assert producer.get_sim_type() is None
    assert producer.get_sim_type_str() is None
