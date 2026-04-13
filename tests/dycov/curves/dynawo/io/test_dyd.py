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
from dycov.curves.dynawo.io.dyd import DydFile
from dycov.files import replace_placeholders

# --- Dummy domain objects -----------------------------------------------------


class DummyGenerator:
    def __init__(self, id: str, lib: str):
        self.id = id
        self.lib = lib


class DummyProducer:
    def __init__(self, generators):
        self.generators = generators
        self.u_nom = 1.0


class DummyProducerCurves(ProducerCurves):
    """Minimal stub to satisfy the DydFile constructor."""

    def __init__(self, producer: DummyProducer):
        self._producer = producer

    def get_producer(self) -> DummyProducer:
        return self._producer

    def obtain_value(self, value_definition: str):
        # FileVariables may call this; keep simple passthrough
        return value_definition


# --- Fixtures ----------------------------------------------------------------


@pytest.fixture
def working_oc_dir(tmp_path):
    """
    Create a dummy TSOModel.dyd file so DydFile finds the template.
    The content isn't parsed by the test—only existence matters for
    replace_placeholders.get_all_variables mock.
    """
    (tmp_path / "TSOModel.dyd").write_text("{{ generator_id }} {{ connection_event }}")
    return tmp_path


@pytest.fixture
def dummy_event_params():
    # 'connect_to' no longer affects DydFile; kept to ensure it doesn't break anything
    return {"connect_to": "connect_event", "start_time": 10.0}


@pytest.fixture
def dummy_producer_curves():
    gen = DummyGenerator(id="GEN1", lib="LIB1")
    producer = DummyProducer(generators=[gen])
    return DummyProducerCurves(producer)


# --- Tests -------------------------------------------------------------------


def test_complete_file_passes_variables_and_dumps(
    monkeypatch, working_oc_dir, dummy_event_params, dummy_producer_curves
):
    """
    DydFile.complete_file should:
      1) Read placeholders from TSOModel.dyd (mocked).
      2) Call FileVariables.complete_parameters (indirect).
      3) Dump the resulting dict as-is (since no config-driven change is
         simulated here).
    """
    original = {"generator_id": 0, "connection_event": 0, "other": 123}

    def fake_get_all_variables(path, template_file):
        # Simulate template variable extraction
        assert str(path) == str(working_oc_dir)
        assert template_file == "TSOModel.dyd"
        return dict(original)

    def fake_dump_file(path, filename, stream_dict):
        # Expect a passthrough dump (no changes simulated)
        assert str(path) == str(working_oc_dir)
        assert filename == "TSOModel.dyd"
        assert stream_dict == original

    monkeypatch.setattr(replace_placeholders, "get_all_variables", fake_get_all_variables)
    monkeypatch.setattr(replace_placeholders, "dump_file", fake_dump_file)

    dyd = DydFile(dummy_producer_curves, "BM", "OC")
    dyd.complete_file(working_oc_dir, dummy_event_params)


def test_complete_file_without_connect_to_behaves_the_same(
    monkeypatch, working_oc_dir, dummy_producer_curves
):
    """
    Without 'connect_to' in event params, behavior is identical:
    placeholders are read and dumped; DydFile doesn't alter generator_id/connection_event.
    """
    original = {"generator_id": 0, "connection_event": 0, "other": 1}

    def fake_get_all_variables(path, template_file):
        return dict(original)

    def fake_dump_file(path, filename, stream_dict):
        assert stream_dict == original

    monkeypatch.setattr(replace_placeholders, "get_all_variables", fake_get_all_variables)
    monkeypatch.setattr(replace_placeholders, "dump_file", fake_dump_file)

    dyd = DydFile(dummy_producer_curves, "BM", "OC")
    dyd.complete_file(working_oc_dir, {"start_time": 5.0})
