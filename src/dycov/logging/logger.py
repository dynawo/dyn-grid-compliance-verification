#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import logging
import warnings
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import colorama

from dycov.logging.custom_formatter import CustomFormatter
from dycov.logging.test_context import clear_test_context, get_test_context, set_test_context

colorama.init()


class _ContextAdapter(logging.LoggerAdapter):
    """
    LoggerAdapter that injects the active test context (PCS.Benchmark.OC)
    from the current thread into every log record.
    """

    def process(self, msg, kwargs):
        context = get_test_context()
        if context:
            msg = f"{context}: {msg}"
        return msg, kwargs


class DycovLogger(logging.getLoggerClass()):
    def __init__(self, name: str) -> None:
        super(DycovLogger, self).__init__(name)
        self.setLevel(logging.INFO)

    def _add_console_handler(
        self,
        console_log_level: int,
        console_formatter: str,
        disable_console: bool = False,
    ) -> None:
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(console_log_level)

        if colorama:
            stdout_handler.setFormatter(CustomFormatter(console_formatter))
        else:
            stdout_handler.setFormatter(logging.Formatter(console_formatter))

        if not disable_console:
            self.addHandler(stdout_handler)

    def _add_file_handler(
        self,
        file_log_level: int,
        file_formatter: str,
        file_max_bytes: int,
        log_dir: Path,
        disable_file: bool = False,
    ) -> None:
        log_name = "dycov.log"
        log_file = log_dir / log_name
        file_handler = RotatingFileHandler(
            log_file, mode="a", maxBytes=file_max_bytes, backupCount=5, encoding=None, delay=0
        )
        file_handler.setLevel(file_log_level)
        file_handler.setFormatter(logging.Formatter(file_formatter))

        if not disable_file:
            self.addHandler(file_handler)

    def init_handlers(
        self,
        file_log_level: int,
        file_formatter: str,
        file_max_bytes: int,
        console_log_level: int,
        console_formatter: str,
        log_dir: Path,
        disable_console: bool = False,
        disable_file: bool = False,
    ) -> None:
        # Set the effective level to the lowest of console/file levels
        self.setLevel(console_log_level)
        if file_log_level < console_log_level:
            self.setLevel(file_log_level)

        self._add_console_handler(console_log_level, console_formatter, disable_console)
        self._add_file_handler(
            file_log_level, file_formatter, file_max_bytes, log_dir, disable_file
        )

    def enable_warning_capture(self, force_runtimewarning_visible: bool = True) -> None:
        """
        Redirect Python warnings (e.g., SciPy/NumPy RuntimeWarning) into logging
        and use the same handlers/formatters configured on this DycovLogger.
        This uses Python's built-in logging.captureWarnings(True), which sends
        warnings to the 'py.warnings' logger. We attach our handlers to that
        logger so the output looks identical to the rest of DyCoV logs.
        """

        def _formatwarning(message, category, filename, lineno, line=None):
            return f"{category.__name__}: {message}"

        warnings.formatwarning = _formatwarning
        logging.captureWarnings(True)
        pywarn = logging.getLogger("py.warnings")

        pywarn.setLevel(logging.WARNING)

        pywarn.handlers.clear()
        for h in self.handlers:
            pywarn.addHandler(h)

        if force_runtimewarning_visible:
            warnings.simplefilter("always", category=RuntimeWarning)

    def set_test_context(
        self,
        pcs: Optional[str] = None,
        benchmark: Optional[str] = None,
        oc: Optional[str] = None,
    ) -> None:
        """
        Set the active test context for the current thread.
        All subsequent log calls from this thread will include [PCS.Benchmark.OC].
        Safe to use with parallel threads — each thread has its own context.
        """
        set_test_context(pcs, benchmark, oc)

    def clear_test_context(self) -> None:
        """Clear the active test context for the current thread."""
        clear_test_context()

    def get_logger(self, name: str) -> _ContextAdapter:
        """
        Return a context-aware child logger for the given name.
        The returned adapter automatically prepends [PCS.Benchmark.OC]
        to every message based on the calling thread's active context.
        """
        child = self.getChild(name)
        child.setLevel(self.getEffectiveLevel())
        return _ContextAdapter(child, {})
