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


def _make_producer(monkeypatch):
    from dycov.configuration.cfg import Config
    from dycov.model.producer import Producer

    monkeypatch.setattr(Config, "get_float", lambda *args, **kwargs: 100.0)

    return Producer(Path("/tmp/model"), Path("/tmp/ini/producer.ini"))


def test_initialize_reads_config(monkeypatch):
    producer = _make_producer(monkeypatch)

    assert producer._s_nref == 100.0
    assert producer._f_nom == 100.0
    assert producer._producer_model_path == Path("/tmp/model")
    assert producer._producer_ini_path == Path("/tmp/ini")
    assert producer._sim_type is None


def test_initialize_without_ini(monkeypatch):
    from dycov.configuration.cfg import Config
    from dycov.model.producer import Producer

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
