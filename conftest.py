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
