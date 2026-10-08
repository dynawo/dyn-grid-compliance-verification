#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import pytest

from dycov.configuration.cfg import Config
from dycov.curves.curves import ProducerCurves
from dycov.curves.dynawo.io import file_variables
from dycov.curves.dynawo.io.file_variables import FileVariables


class DummyProducer:
    def __init__(self, u_nom):
        self.u_nom = u_nom


class DummyProducerCurves(ProducerCurves):
    def __init__(self, producer):
        self._producer = producer

    def obtain_value(self, value_definition, origin=None):
        # For test, just return the value_definition as float if possible, else as is
        try:
            return float(value_definition)
        except Exception:
            return value_definition

    def get_producer(self):
        return self._producer


class DummyGeneratorVariables:
    def __init__(self, generator_type):
        self._generator_type = generator_type

    def get_generator_type(self, u_nom):
        return self._generator_type


class DummyConfig:
    def __init__(self, keys, values):
        self._keys = keys  # dict: section -> set(keys)
        self._values = values  # dict: (section, key) -> value

    def has_key(self, section, key):
        return section in self._keys and key in self._keys[section]

    def get_value(self, section, key):
        return self._values.get((section, key), None)


@pytest.fixture(autouse=True)
def patch_org_modules(monkeypatch):
    yield


def test_tool_variables_are_not_updated(monkeypatch):
    bm_section = "BM"
    oc_section = "OC"
    keys = {bm_section: {"alpha"}}
    values = {(bm_section, "alpha"): "1.0"}
    monkeypatch.setattr("dycov.configuration.cfg.config", DummyConfig(keys, values))
    monkeypatch.setattr(
        "dycov.electrical.generator_variables.generator_variables", DummyGeneratorVariables("HTB1")
    )
    producer = DummyProducer(u_nom=225.0)
    dynawo_curves = DummyProducerCurves(producer)
    fv = FileVariables(["alpha"], dynawo_curves, bm_section, oc_section)
    variables_dict = {"alpha": "original"}
    event_params = {"start_time": 0.0}
    fv.complete_parameters(variables_dict, event_params)
    assert variables_dict["alpha"] == "original"


def test_key_not_found_leaves_value_unchanged(monkeypatch):
    bm_section = "BM"
    oc_section = "OC"
    keys = {}  # No keys in any section
    values = {}
    monkeypatch.setattr("dycov.configuration.cfg.config", DummyConfig(keys, values))
    monkeypatch.setattr(
        "dycov.electrical.generator_variables.generator_variables", DummyGeneratorVariables("HTB1")
    )
    producer = DummyProducer(u_nom=225.0)
    dynawo_curves = DummyProducerCurves(producer)
    fv = FileVariables([], dynawo_curves, bm_section, oc_section)
    variables_dict = {"missing_key": "unchanged"}
    event_params = {"start_time": 0.0}
    fv.complete_parameters(variables_dict, event_params)
    assert variables_dict["missing_key"] == "unchanged"


def test_key_of_the_voltage_level_wins_over_the_plain_key(monkeypatch):
    values = {("BM", "delay"): "1.0", ("BM", "delay_HTB1"): "2.0"}
    monkeypatch.setattr(Config, "has_option", lambda self, section, key: (section, key) in values)
    monkeypatch.setattr(
        Config, "get_value", lambda self, section, key, default=None: values[(section, key)]
    )
    monkeypatch.setattr(file_variables, "generator_variables", DummyGeneratorVariables("HTB1"))
    fv = FileVariables([], DummyProducerCurves(DummyProducer(u_nom=225.0)), "BM", "OC")
    variables_dict = {"delay": "unset"}

    fv.complete_parameters(variables_dict, {"start_time": 0.0})

    assert variables_dict["delay"] == "2.0"
