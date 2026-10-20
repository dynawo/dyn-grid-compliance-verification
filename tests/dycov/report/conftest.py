#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Fixtures shared by the report tests."""

import pytest

from dycov.configuration.cfg import config


class RecordingRenderer:
    """A renderer that keeps the kind and position of every mark it is asked to draw."""

    def __init__(self):
        self.marks = []

    def add_hline(self, y, **kwargs):
        self.marks.append(("hline", y))

    def add_vline(self, x, **kwargs):
        self.marks.append(("vline", x))

    def add_curve(self, x, y, **kwargs):
        self.marks.append(("curve", list(y)))

    def add_scatter(self, x, y, **kwargs):
        self.marks.append(("scatter", (x, y)))

    def add_hrect(self, y0, y1, **kwargs):
        self.marks.append(("hrect", (y0, y1)))

    def add_vrect(self, x0, x1, **kwargs):
        self.marks.append(("vrect", (x0, x1)))

    def add_annotation(self, text, **kwargs):
        self.marks.append(("annotation", text))


@pytest.fixture
def renderer():
    return RecordingRenderer()


@pytest.fixture
def set_user_option():
    """Yields a setter that writes options into the in-memory user config and
    restores the previous state on teardown."""
    parser = config._user_config
    added_sections = []
    backup = {}

    def _set(section, key, value):
        if not parser.has_section(section):
            parser.add_section(section)
            added_sections.append(section)
        if (section, key) not in backup:
            backup[(section, key)] = (
                parser.get(section, key) if parser.has_option(section, key) else None
            )
        parser.set(section, key, str(value))

    yield _set

    for (section, key), old_value in backup.items():
        if old_value is None:
            parser.remove_option(section, key)
        else:
            parser.set(section, key, old_value)
    for section in added_sections:
        parser.remove_section(section)
