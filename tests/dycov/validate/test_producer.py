#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the ModelProducer helpers."""

import pytest

from dycov.configuration.cfg import Config
from dycov.validate.producer import ModelProducer


def test_s_nom_pu_is_snom_over_snref():
    producer = ModelProducer.__new__(ModelProducer)
    producer.s_nom = 180.0
    producer._s_nref = 100.0

    assert producer.s_nom_pu == pytest.approx(1.8)


def test_init_reads_s_nref_from_the_dynawo_section(monkeypatch):
    monkeypatch.setattr(
        Config,
        "get_float",
        lambda self, section, key, default: (
            90.0 if (section, key) == ("Dynawo", "s_nref") else default
        ),
    )

    producer = ModelProducer(None, None, None, -1)

    assert producer._s_nref == pytest.approx(90.0)
