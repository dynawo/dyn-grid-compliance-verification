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

from dycov.curves.curves import ProducerCurves
from dycov.dynawo.dyd import DydFile
from dycov.files import replace_placeholders


class DummyGenerator:
    def __init__(self, id, lib):
        self.id = id
        self.lib = lib


class DummyProducer:
    def __init__(self, generators):
        self.generators = generators
        self.u_nom = 1.0


class DummyProducerCurves(ProducerCurves):
    def __init__(self, producer):
        self._producer = producer

    def get_producer(self):
        return self._producer

    def obtain_value(self, value_definition):
        return value_definition

    def complete_parameters(self, variables_dict, event_params):
        # Simulate adding a value
        variables_dict["completed"] = "yes"


@pytest.fixture
def working_oc_dir(tmp_path):
    # Create a dummy TSOModel.dyd file for template existence
    (tmp_path / "TSOModel.dyd").write_text("{{ generator_id }} {{ connection_event }}")
    return tmp_path


@pytest.fixture
def dummy_event_params():
    return {"connect_to": "connect_event", "start_time": 10.0}


@pytest.fixture
def dummy_producer_curves():
    gen = DummyGenerator(id="GEN1", lib="LIB1")
    producer = DummyProducer(generators=[gen])
    return DummyProducerCurves(producer)


def test_complete_file_sets_generator_id_and_connection_event(
    monkeypatch, working_oc_dir, dummy_event_params, dummy_producer_curves
):
    # Setup
    variables_dict = {"generator_id": 0, "connection_event": 0}

    def fake_get_all_variables(path, template_file):
        return dict(variables_dict)

    def fake_dump_file(path, filename, stream_dict):
        # Check that generator_id and connection_event are set
        assert stream_dict["generator_id"] == "GEN1"

    monkeypatch.setattr(replace_placeholders, "get_all_variables", fake_get_all_variables)
    monkeypatch.setattr(replace_placeholders, "dump_file", fake_dump_file)
    dyd = DydFile(dummy_producer_curves, "BM", "OC")
    dyd.complete_file(working_oc_dir, dummy_event_params)


def test_complete_file_without_connect_to_does_not_set_generator_id_or_connection_event(
    monkeypatch, working_oc_dir, dummy_producer_curves
):
    # Setup
    variables_dict = {"generator_id": 0, "connection_event": 0, "other": 1}

    def fake_get_all_variables(path, template_file):
        return dict(variables_dict)

    def fake_dump_file(path, filename, stream_dict):
        # Should not change generator_id or connection_event
        assert stream_dict["generator_id"] == 0
        assert stream_dict["connection_event"] == 0

    monkeypatch.setattr(replace_placeholders, "get_all_variables", fake_get_all_variables)
    monkeypatch.setattr(replace_placeholders, "dump_file", fake_dump_file)
    dyd = DydFile(dummy_producer_curves, "BM", "OC")
    dyd.complete_file(working_oc_dir, {"start_time": 5.0})


def test_complete_file_handles_dynawo_translator_errors(
    monkeypatch, working_oc_dir, dummy_event_params, dummy_producer_curves
):
    # Setup
    def fake_get_all_variables(path, template_file):
        return {"generator_id": 0, "connection_event": 0}

    def fake_get_dynawo_variable(lib, name):
        # Simulate error: returns None for translated name
        return (1, None)

    def fake_dump_file(path, filename, stream_dict):
        # connection_event should be None
        assert stream_dict["connection_event"] is None

    monkeypatch.setattr(replace_placeholders, "get_all_variables", fake_get_all_variables)
    monkeypatch.setattr(replace_placeholders, "dump_file", fake_dump_file)
    dyd = DydFile(dummy_producer_curves, "BM", "OC")
    dyd.complete_file(working_oc_dir, dummy_event_params)
