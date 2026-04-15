#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# pytest configuration providing isolated working directories for each test.
# Creates a shared .pytest_temp/ folder at session start (wiped clean on start and finish)
# and an autouse fixture that gives every test its own temporary subdirectory as cwd,
# restoring the original cwd and deleting the tempdir after the test completes.
#
# (c) 2025/26 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import shutil
import tempfile
from pathlib import Path

import pytest

BASE_TEMP_DIR = Path.cwd() / ".pytest_temp"


def pytest_sessionstart(session):
    if BASE_TEMP_DIR.exists():
        shutil.rmtree(BASE_TEMP_DIR, ignore_errors=True)
    BASE_TEMP_DIR.mkdir(parents=True, exist_ok=True)


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(BASE_TEMP_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def temp_workdir():
    tmpdir = Path(tempfile.mkdtemp(prefix="test_", dir=str(BASE_TEMP_DIR)))
    old_cwd = Path.cwd()
    tmpdir.mkdir(exist_ok=True)
    import os

    os.chdir(tmpdir)
    try:
        yield tmpdir
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(tmpdir, ignore_errors=True)
