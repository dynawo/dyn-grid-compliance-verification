#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the purge of the temporary working directories left by previous runs."""

import os
import subprocess
import sys
import textwrap
import time
from datetime import timedelta

from dycov.core.parameters import _purge_stale_temp_dirs

PREFIX = "Dynawo_user_"
OLDER_THAN = timedelta(minutes=30)

_OWNER = textwrap.dedent(
    """
    import fcntl
    import os
    import sys
    import time

    fd = os.open(sys.argv[1], os.O_RDONLY)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    print("locked", flush=True)
    time.sleep(60)
    """
)


def _make_dir(base_dir, name, age_minutes=0):
    path = base_dir / name
    path.mkdir()
    when = time.time() - age_minutes * 60
    os.utime(path, (when, when))
    return path


def _start_owner(path):
    owner = subprocess.Popen(
        [sys.executable, "-c", _OWNER, str(path)], stdout=subprocess.PIPE, text=True
    )
    assert owner.stdout.readline().strip() == "locked"
    return owner


def test_purge_removes_a_stale_directory_no_run_owns(tmp_path):
    stale = _make_dir(tmp_path, PREFIX + "stale", age_minutes=60)

    _purge_stale_temp_dirs(base_dir=tmp_path, prefix=PREFIX, older_than=OLDER_THAN)

    assert not stale.exists()


def test_purge_keeps_the_directory_a_running_process_holds(tmp_path):
    owned = _make_dir(tmp_path, PREFIX + "owned", age_minutes=60)
    owner = _start_owner(owned)

    try:
        _purge_stale_temp_dirs(base_dir=tmp_path, prefix=PREFIX, older_than=OLDER_THAN)
    finally:
        owner.kill()
        owner.wait()

    assert owned.exists()


def test_purge_removes_the_directory_of_a_run_that_died(tmp_path):
    crashed = _make_dir(tmp_path, PREFIX + "crashed", age_minutes=60)
    owner = _start_owner(crashed)
    owner.kill()
    owner.wait()

    _purge_stale_temp_dirs(base_dir=tmp_path, prefix=PREFIX, older_than=OLDER_THAN)

    assert not crashed.exists()


def test_purge_keeps_a_directory_younger_than_the_threshold(tmp_path):
    recent = _make_dir(tmp_path, PREFIX + "recent")

    _purge_stale_temp_dirs(base_dir=tmp_path, prefix=PREFIX, older_than=OLDER_THAN)

    assert recent.exists()


def test_purge_keeps_the_excluded_directory(tmp_path):
    excluded = _make_dir(tmp_path, PREFIX + "excluded", age_minutes=60)

    _purge_stale_temp_dirs(
        base_dir=tmp_path, prefix=PREFIX, older_than=OLDER_THAN, exclude=excluded
    )

    assert excluded.exists()


def test_purge_keeps_a_stale_directory_of_another_tool(tmp_path):
    foreign = _make_dir(tmp_path, "other_tool_stale", age_minutes=60)

    _purge_stale_temp_dirs(base_dir=tmp_path, prefix=PREFIX, older_than=OLDER_THAN)

    assert foreign.exists()
