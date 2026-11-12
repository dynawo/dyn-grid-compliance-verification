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


def test_the_producer_is_the_file_given_whatever_else_its_folder_holds(monkeypatch, tmp_path):
    """#766: another INI of the folder is neither a producer nor where its settings are read."""
    from dycov.gfm.producer import GFMProducer

    _patch_config(monkeypatch)
    _write_ini(tmp_path, name="Alpha.ini", body="[Section]\nkey = alpha\n")
    bravo = _write_ini(tmp_path, name="Bravo.ini", body="[Section]\nkey = bravo\n")

    producer = GFMProducer(bravo)

    assert producer.get_filenames() == ["Bravo"]
    assert producer.get_config().get("Section", "key") == "bravo"


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


def test_a_missing_ini_raises_although_its_folder_holds_another(monkeypatch, tmp_path):
    from dycov.gfm.producer import GFMProducer

    _patch_config(monkeypatch)
    _write_ini(tmp_path)
    missing = tmp_path / "Typo.ini"

    with pytest.raises(FileNotFoundError, match="Typo.ini"):
        GFMProducer(missing)


def test_a_folder_is_not_a_producer_ini(monkeypatch, tmp_path):
    from dycov.gfm.producer import GFMProducer

    _patch_config(monkeypatch)
    _write_ini(tmp_path)
    folder = tmp_path / "Producer"
    folder.mkdir()

    with pytest.raises(FileNotFoundError):
        GFMProducer(folder)
