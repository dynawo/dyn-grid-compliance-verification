#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Fixtures for the Excel -> DyCoV input generator tests.

The tool lives under tools/ (outside the dycov package), so workbooks puts it on the
path and holds the synthetic workbook the tests read.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workbooks import ZONE1_ROWS, ZONE3_ROWS  # noqa: E402


@pytest.fixture
def zone1() -> dict:
    return dict(ZONE1_ROWS)


@pytest.fixture
def zone3() -> dict:
    return dict(ZONE3_ROWS)


@pytest.fixture
def named():
    """Extract {parameter name -> value} from a builder's parameter list."""
    return lambda params: {p["name"]: p["value"] for p in params}
