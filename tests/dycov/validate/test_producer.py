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

from dycov.validate.producer import ModelProducer


def test_s_nom_pu_is_snom_over_snref():
    producer = ModelProducer.__new__(ModelProducer)
    producer.s_nom = 180.0
    producer._s_nref = 100.0

    assert producer.s_nom_pu == pytest.approx(1.8)
