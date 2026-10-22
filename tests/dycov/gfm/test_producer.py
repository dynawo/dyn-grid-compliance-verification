#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#

import configparser

import pytest


def _patch_config(monkeypatch):
    from dycov.configuration.cfg import Config

    monkeypatch.setattr(Config, "get_float", lambda *args, **kwargs: 100.0)


def _write_ini(
    path,
    name="Producer.ini",
    body="[DEFAULT]\ngenerator_type = PPM\n\n[Section]\nkey = value  # inline\n",
):
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


@pytest.mark.parametrize("generator_type", ["PPM", "BESS"])
def test_get_sim_type_str_follows_the_generator_type(monkeypatch, tmp_path, generator_type):
    from dycov.gfm.producer import GFMProducer

    _patch_config(monkeypatch)
    ini = _write_ini(tmp_path, body=f"[DEFAULT]\ngenerator_type = {generator_type}\n")

    assert GFMProducer(ini).get_sim_type_str() == f"gfm/{generator_type}"


@pytest.mark.parametrize(
    "body", ["[DEFAULT]\np_max_injection = 100\n", "[DEFAULT]\ngenerator_type = SM\n"]
)
def test_unsupported_generator_type_raises(monkeypatch, tmp_path, body):
    from dycov.gfm.producer import GFMProducer

    _patch_config(monkeypatch)
    ini = _write_ini(tmp_path, body=body)

    with pytest.raises(ValueError, match="generator_type"):
        GFMProducer(ini)


def test_the_unit_is_the_ini_file_given_whatever_lies_next_to_it(monkeypatch, tmp_path):
    from dycov.gfm.producer import GFMProducer

    _patch_config(monkeypatch)
    _write_ini(tmp_path, name="Bravo.ini", body="[DEFAULT]\ngenerator_type = BESS\n")
    _write_ini(tmp_path, name="Alpha.ini", body="[DEFAULT]\ngenerator_type = PPM\n")

    producer = GFMProducer(tmp_path / "Bravo.ini")

    assert producer.get_filenames() == ["Bravo"]
    assert producer.get_sim_type_str() == "gfm/BESS"


def test_a_generator_type_given_needs_none_in_the_ini_file(monkeypatch, tmp_path):
    from dycov.gfm.producer import GFMProducer

    _patch_config(monkeypatch)
    ini = _write_ini(tmp_path, body="[DEFAULT]\np_max_injection = 100\n")

    assert GFMProducer(ini, generator_type="BESS").get_sim_type_str() == "gfm/BESS"


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


def _parameters(ini_text: str, emt: bool = False):
    from dycov.gfm.parameters import GFMParameters

    producer_config = configparser.ConfigParser()
    producer_config.read_string(ini_text)
    producer = type(
        "Producer", (), {"_config": producer_config, "get_config": lambda self: producer_config}
    )()
    return GFMParameters(None, producer, emt=emt)


@pytest.mark.parametrize("declared, expected", [("Imax = 1.1\n", 1.1), ("", None)])
def test_maximum_current_bounds_the_envelopes_only_when_declared(declared, expected):
    parameters = _parameters(f"[GFM Parameters]\nXeff = 0.27\n{declared}")

    assert parameters.get_max_current() == expected


@pytest.mark.parametrize(
    "declared, expected",
    [
        # The INI file of an envelope generation
        ("p_min_injection = -90\n", -0.9),
        # The INI file of the Zone 1 unit of a model validation
        ("p_min_injection = 10\np_max_consumption = 80\n", -0.8),
    ],
)
def test_minimum_active_power_of_a_storage_unit_is_its_maximum_consumption(declared, expected):
    parameters = _parameters(f"[DEFAULT]\n{declared}\n[GFM Parameters]\nSnom = 100\n")

    assert parameters.get_min_active_power() == pytest.approx(expected)


@pytest.mark.parametrize(
    "asked, declared, expected",
    [(False, "", False), (True, "", True), (False, "emt = true\n", True)],
)
def test_envelopes_are_for_emt_when_asked_or_when_the_unit_declares_it(asked, declared, expected):
    parameters = _parameters(f"[GFM Parameters]\nXeff = 0.27\n{declared}", emt=asked)

    assert parameters.is_emt() == expected


@pytest.mark.parametrize(
    "ini_text, expected", [("[GFM Parameters]\nXeff = 0.27\n", True), ("", False)]
)
def test_envelopes_are_generated_only_for_a_unit_that_declares_its_parameters(ini_text, expected):
    assert _parameters(ini_text).declares_unit_parameters() == expected
