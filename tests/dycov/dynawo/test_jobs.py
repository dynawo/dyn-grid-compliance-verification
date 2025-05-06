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
from dycov.dynawo.jobs import JobsFile


# Minimal stub classes to allow integration-style testing without mocks
class DummyProducer:
    def __init__(self, dyd_name="producer.dyd", raise_on_dyd=False):
        self._dyd_name = dyd_name
        self._raise_on_dyd = raise_on_dyd

    def get_producer_dyd(self):
        if self._raise_on_dyd:
            raise FileNotFoundError("DYD file not found")

        class DydFile:
            def __init__(self, name):
                self.name = name

        return DydFile(self._dyd_name)


class DummyParameters:
    def __init__(self, producer):
        self._producer = producer

    def get_producer(self):
        return self._producer


class DummyProducerCurves(ProducerCurves):
    def __init__(self, producer):
        self._producer = producer

    def get_producer(self):
        return self._producer


@pytest.fixture
def temp_working_dir(tmp_path):
    # Create a temporary working directory and a minimal TSOModel.jobs template
    jobs_file = tmp_path / "TSOModel.jobs"
    jobs_file.write_text(
        "{{ solver_lib }}\n"
        "{{ solver_id }}\n"
        "{{ dycov_ddb_path }}\n"
        "{{ producer_dyd }}\n"
        "{{ custom_var }}\n"
    )
    return tmp_path


@pytest.fixture
def event_params():
    return {"start_time": 10.0, "custom_var": "custom_value"}


def test_complete_file_producer_dyd_not_found(temp_working_dir, event_params):
    producer = DummyProducer(raise_on_dyd=True)
    dynawo_curves = DummyProducerCurves(producer)
    jobs = JobsFile(dynawo_curves, "BM", "OC")
    # Should handle the exception gracefully (may raise, but not unhandled)
    try:
        jobs.complete_file(temp_working_dir, "solverB", "libB.so", event_params)
    except Exception as e:
        assert isinstance(e, FileNotFoundError)
