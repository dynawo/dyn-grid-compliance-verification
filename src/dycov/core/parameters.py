#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import atexit
import fcntl
import getpass
import logging
import os
import shutil
import tempfile
import threading
import time
from datetime import timedelta
from pathlib import Path
from typing import Optional

from dycov.configuration.cfg import config
from dycov.core.graceful_shutdown import install_signal_handlers, terminate_all_children
from dycov.files import manage_files
from dycov.logging import dycov_logging
from dycov.model.producer import Producer


def _purge_stale_temp_dirs(base_dir: Path, prefix: str, older_than: timedelta):
    """
    Removes temporary directories that are older than the specified time limit
    and are not currently locked by an active process.
    """
    now = time.time()
    for p in base_dir.glob(f"{prefix}*"):
        if p.is_dir():
            mtime = p.stat().st_mtime

            # Check if the directory is older than the allowed limit
            if now - mtime > older_than.total_seconds():
                try:
                    # Open the directory to obtain a file descriptor
                    fd = os.open(str(p), os.O_RDONLY)
                    try:
                        # Attempt to acquire an exclusive, non-blocking lock
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

                        # If the lock is acquired, the process that created
                        # the directory is no longer alive. It is safe to purge.
                        shutil.rmtree(p, ignore_errors=True)

                    except BlockingIOError:
                        # If a BlockingIOError is raised, the directory is currently
                        # locked by a live run. We skip it.
                        pass
                    finally:
                        # Always close the file descriptor
                        os.close(fd)
                except OSError:
                    # This can happen if the directory disappears or due to permissions
                    pass


# Global abort flag to coordinate graceful shutdown across threads
ABORT_EVENT = threading.Event()


class Parameters:
    """
    Parent class to define the common parameters.
    Args
    ----
    launcher_dwo: Path
        Dynawo launcher
    selected_pcs: str
        Individual PCS to validate
    output_dir: Path
        User output directory
    """

    def __init__(
        self,
        launcher_dwo: Path,
        selected_pcs: str,
        output_dir: Path,
        only_dtr: bool,
    ):
        # Inputs parameters
        self._launcher_dwo = launcher_dwo
        self._selected_pcs = selected_pcs
        self._output_dir = output_dir
        self._only_dtr = only_dtr
        self._producer_workbook = None

        tmp_path = config.get_value("Global", "temporal_path")
        username = getpass.getuser()
        base_dir = Path.cwd()
        prefix = f"{tmp_path}_{username}_"
        _purge_stale_temp_dirs(base_dir=base_dir, prefix=prefix, older_than=timedelta(minutes=30))
        self._working_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=base_dir))

        # Lock the working directory. We keep the file descriptor (self._lock_fd)
        # open for the lifetime of the run so the OS maintains the lock.
        self._lock_fd = os.open(str(self._working_dir), os.O_RDONLY)
        fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        # The parameter is initialized in the child class
        self._producer: Optional[Producer] = None

        # --- Robust atexit cleanup bound to concrete path (not to object state) ---
        wd = self._working_dir

        def _cleanup_on_exit():
            try:
                # Preserve in DEBUG, remove otherwise (no logs emitted)
                if dycov_logging.get_logger("Parameters").getEffectiveLevel() != logging.DEBUG:
                    manage_files.remove_dir(wd)
            except Exception:
                try:
                    manage_files.remove_dir(wd)
                except Exception:
                    pass

        atexit.register(_cleanup_on_exit)

        # Cleanup bookkeeping
        self._cleanup_registered = False
        self._register_cleanup_hooks()

    def get_launcher_dwo(self) -> Path:
        """Get the Dynawo launcher.

        Returns
        -------
        Path
            Dynawo launcher
        """
        return self._launcher_dwo

    def get_selected_pcs(self) -> str:
        """Get the selected PCS

        Returns
        -------
        str
            PCS name
        """
        return self._selected_pcs

    def get_output_dir(self) -> Path:
        """Get the user output directory.

        Returns
        -------
        Path
            User output directory
        """
        return self._output_dir

    def get_only_dtr(self) -> bool:
        """Use only the PCS of the DTR:

        Returns
        -------
        bool
            True if use only the PCS of the DTR
        """
        return self._only_dtr

    def get_working_dir(self) -> Path:
        """Get the temporal working directory.

        Returns
        -------
        Path
            Temporal working directory
        """
        return self._working_dir

    def get_producer(self) -> Producer:
        """Get the producer model

        Returns
        -------
        Producer
            Producer
        """
        return self._producer

    def get_producer_workbook(self) -> Path:
        """Get the workbook the producer inputs were generated from, when there is one.

        Returns
        -------
        Path
            Workbook the inputs come from, or None when they were given as files.
        """
        return self._producer_workbook

    def is_valid(self) -> bool:
        """Checks if the execution of the tool is valid.

        Returns
        -------
        bool
            True if it is a valid execution, False otherwise
        """
        pass

    def cleanup_working_dir(self, preserve_on_debug: bool = True) -> None:
        """
        Deletes the working directory, or renames it to output_dir when running in DEBUG
        and preserve_on_debug=True (to keep artifacts for inspection).
        Idempotent and safe to call multiple times.
        """
        wd: Optional[Path] = getattr(self, "_working_dir", None)
        if not wd:
            return
        try:
            if (
                not preserve_on_debug
                or dycov_logging.get_logger("Parameters").getEffectiveLevel() != logging.DEBUG
            ):
                manage_files.remove_dir(wd)
        except Exception:
            try:
                manage_files.remove_dir(wd)
            except Exception:
                pass
        finally:
            self._working_dir = None

    def __exit__(self, exc_type, exc, tb):
        # On normal exit or exception, remove tmp unless you're debugging and want to keep it
        self.cleanup_working_dir(preserve_on_debug=True)

    # --- INTERNAL: hook registration ---
    def _register_cleanup_hooks(self):
        if self._cleanup_registered:
            return

        # Install centralized signal handlers via graceful_shutdown.install_signal_handlers
        def _on_exit(exit_code: int) -> None:
            """Minimal exit callback for signal handlers.
            - Mark global abort
            - Terminate external children (Dynawo + LaTeX)
            - Exit from main thread using Pythonic exceptions so finally/atexit run
            """
            # 1) Mark global abort so long-running loops can break promptly
            ABORT_EVENT.set()
            # 2) Terminate external children (best-effort & idempotent)
            terminate_all_children(timeout=5.0)
            # 3) Exit only from the main thread
            if threading.current_thread() is threading.main_thread():
                if exit_code == 130:  # SIGINT
                    raise KeyboardInterrupt()
                else:  # SIGTERM/SIGHUP/SIGQUIT -> conventional code
                    raise SystemExit(exit_code)
            # Non-main threads: do nothing else; main will exit cleanly.

        # Register handlers (SIGINT + SIGTERM/SIGHUP/SIGQUIT) only from main thread
        install_signal_handlers(on_exit=_on_exit)
        self._cleanup_registered = True
