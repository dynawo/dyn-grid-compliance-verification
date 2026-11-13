#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import pytest

from dycov.configuration.cfg import config


def _select_revision(name: str) -> None:
    config.set_value("DTR", "current", name)
    config.load_dtr_delta_config(name)


@pytest.fixture
def dtr_revision():
    """Puts the tool on a revision of the DTR, as the configuration of a run does, and gives it
    back the one it had: the shipped configuration names none."""
    selected = config.get_value("DTR", "current", "")
    yield _select_revision
    _select_revision(selected)
