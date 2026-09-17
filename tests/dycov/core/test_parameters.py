import os
import time
import fcntl
import pytest
from datetime import timedelta
from pathlib import Path

# Adjust the import path based on where the function is located
from dycov.core.parameters import _purge_stale_temp_dirs


def test_purge_stale_temp_dirs(tmp_path: Path):
    """
    Tests that the temporary directory purge logic only removes old folders
    that are not currently locked by a live process.
    """
    prefix = "dycov_run_"
    older_than = timedelta(minutes=30)

    # Scenario 1: Old, orphaned directory (should be deleted)
    stale_dir = tmp_path / f"{prefix}stale"
    stale_dir.mkdir()
    old_time = time.time() - 3600  # Set modification time to 1 hour ago
    os.utime(stale_dir, (old_time, old_time))

    # Scenario 2: Freshly created directory (should NOT be deleted)
    fresh_dir = tmp_path / f"{prefix}fresh"
    fresh_dir.mkdir()
    # We leave the default utime, simulating a directory created just now

    # Scenario 3: Old directory, but currently locked by an active process (should NOT be deleted)
    locked_dir = tmp_path / f"{prefix}locked"
    locked_dir.mkdir()
    os.utime(locked_dir, (old_time, old_time))

    # Acquire a lock manually in the test to simulate an active Dynawo run
    fd = os.open(str(locked_dir), os.O_RDONLY)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    try:
        # Execute the purge function
        _purge_stale_temp_dirs(tmp_path, prefix, older_than)

        # Validate the results
        assert not stale_dir.exists(), (
            "Purge failed: the old orphaned directory should have been removed."
        )
        assert fresh_dir.exists(), (
            "Purge failed: the fresh directory should not have been removed."
        )
        assert locked_dir.exists(), (
            "Purge failed: the locked directory should not have been removed."
        )

    finally:
        # Clean up the lock properly so it doesn't affect other pytest runs
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
