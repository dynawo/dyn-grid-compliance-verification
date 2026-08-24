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


class _DummyParameters:
    def __init__(self, tmp_path):
        self._tmp_path = tmp_path

    def get_working_dir(self):
        return self._tmp_path / "working"

    def get_output_dir(self):
        return self._tmp_path / "Results"


def test_initialize_working_environment_exits_on_existing_output_dir(monkeypatch, tmp_path):
    from dycov.gfm import generator

    monkeypatch.setattr(generator.manage_files, "create_dir", lambda *a, **k: None)
    monkeypatch.setattr(generator.manage_files, "check_output_dir", lambda path: True)
    gfm_generation = object.__new__(generator.GFMGeneration)
    gfm_generation._parameters = _DummyParameters(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        gfm_generation._GFMGeneration__initialize_working_environment()

    assert exc_info.value.code == 1
