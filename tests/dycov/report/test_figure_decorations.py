#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the figure decoration helpers."""

import pytest

from dycov.configuration.cfg import Config
from dycov.report import figure_decorations
from dycov.report.types import FrequencyBand


class RecordingRenderer:
    """Renderer stand-in that records every horizontal line drawn."""

    def __init__(self):
        self.hlines = []

    def add_hline(self, y, color):
        self.hlines.append((y, color))


def test_draw_frequency_band_reads_f_nom_from_the_dynawo_section(monkeypatch):
    calls = []

    def get_float(self, section, key, default):
        calls.append((section, key))
        return 100.0 if (section, key) == ("Dynawo", "f_nom") else default

    monkeypatch.setattr(Config, "get_float", get_float)
    renderer = RecordingRenderer()

    ymin, ymax = figure_decorations.draw_frequency_band(
        renderer, FrequencyBand(upper=1.0, lower=1.0), 0.9, 1.1
    )

    assert ("Dynawo", "f_nom") in calls
    assert renderer.hlines[0][0] == pytest.approx((100.0 + 1.0) / 100.0)
    assert renderer.hlines[1][0] == pytest.approx((100.0 - 1.0) / 100.0)
    assert ymin == pytest.approx(0.9)
    assert ymax == pytest.approx(1.1)
