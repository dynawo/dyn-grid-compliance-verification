#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#

import pytest


def _patch_config(monkeypatch):
    from dycov.configuration.cfg import Config

    monkeypatch.setattr(Config, "get_float", lambda *args, **kwargs: 100.0)


def _write_ini(path, name="Producer.ini", body="[Section]\nkey = value  # inline\n"):
    ini = path / name
    ini.write_text(body)
    return ini


def test_read_producer_ini_and_get_config(monkeypatch, tmp_path):
    from dycov.gfm.producer import GFMProducer

    _patch_config(monkeypatch)
    ini = _write_ini(tmp_path)

    producer = GFMProducer(ini)

    config = producer.get_config()
    assert config.get("Section", "key") == "value"
    assert producer.get_producer_path() == tmp_path


def test_get_sim_type_str(monkeypatch, tmp_path):
    from dycov.gfm.producer import GFMProducer

    _patch_config(monkeypatch)
    ini = _write_ini(tmp_path)

    assert GFMProducer(ini).get_sim_type_str() == "gfm"


def test_get_filenames_sorted(monkeypatch, tmp_path):
    from dycov.gfm.producer import GFMProducer

    _patch_config(monkeypatch)
    _write_ini(tmp_path, name="Bravo.ini")
    _write_ini(tmp_path, name="Alpha.ini")
    (tmp_path / "ignored.txt").write_text("nope")

    producer = GFMProducer(tmp_path / "Bravo.ini")

    assert producer.get_filenames() == ["Alpha", "Bravo"]


def test_set_zone_is_noop(monkeypatch, tmp_path):
    from dycov.gfm.producer import GFMProducer

    _patch_config(monkeypatch)
    ini = _write_ini(tmp_path)

    producer = GFMProducer(ini)
    assert producer.set_zone(1, "file") is None


def test_missing_ini_raises(monkeypatch, tmp_path):
    from dycov.gfm.producer import GFMProducer

    _patch_config(monkeypatch)
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        GFMProducer(empty_dir / "Producer.ini")
