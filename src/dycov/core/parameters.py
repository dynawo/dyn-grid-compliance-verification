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
import getpass
import logging
import os
import signal
import tempfile
import threading
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.files import manage_files
from dycov.logging.logging import dycov_logging
from dycov.model.producer import Producer


class Parameters:
    """Parent class to define the common parameters.

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

        tmp_path = config.get_value("Global", "temporal_path")
        username = getpass.getuser()
        base_dir = output_dir.parent if output_dir.parent.exists() else Path.cwd()
        self._working_dir = Path(tempfile.mkdtemp(prefix=f"{tmp_path}_{username}_", dir=base_dir))

        # The parameter is initialized in the child class
        self._producer = None

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
        wd: Path | None = getattr(self, "_working_dir", None)
        if not wd:
            return

        try:
            logger = dycov_logging.get_logger("Parameters")
            is_debug = logger.getEffectiveLevel() == logging.DEBUG
            if is_debug and preserve_on_debug:
                # Keep artifacts: move into final output for inspection
                manage_files.rename_path(wd, self._output_dir)
            else:
                manage_files.remove_dir(wd)
        except Exception:
            # Best-effort hard delete if rename failed
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

        # Run at normal interpreter exit
        atexit.register(self.cleanup_working_dir)

        # Trap SIGINT/SIGTERM so Ctrl+C / docker stop also cleans
        def _sig_handler(signum, frame):
            try:
                self.cleanup_working_dir(preserve_on_debug=True)
            finally:
                # Restore default and re-signal so the process exits with the right code
                try:
                    signal.signal(signum, signal.SIG_DFL)
                except Exception:
                    pass
                try:
                    os.kill(os.getpid(), signum)
                except Exception:
                    # On Windows or restricted envs, fall back to sys.exit with non-zero
                    import sys

                    sys.exit(130 if signum == signal.SIGINT else 143)

        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    signal.signal(sig, _sig_handler)
                except Exception:
                    # Not always possible (Windows services, non-main thread, etc.)
                    pass

        self._cleanup_registered = True
