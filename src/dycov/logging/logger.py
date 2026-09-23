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
from dycov.logging.test_context import (
    clear_test_context,
    get_test_context,
    is_first_report,
    set_test_context,
)

colorama.init()

_RUN_LOG_NAME = "dycov_run.log"
_RUN_HANDLER_NAME = "run"


class _ContextAdapter(logging.LoggerAdapter):
    """
    LoggerAdapter that injects the active test context (Producer PCS.Benchmark.OC)
    from the current thread into every log record.
    """

    def process(self, msg, kwargs):
        context = get_test_context()
        if context:
            msg = f"{context}: {msg}"
        return msg, kwargs


class DycovLogger(logging.getLoggerClass()):
    def __init__(self, name: str, level: int = logging.NOTSET):
        super().__init__(name, level)
        self._handler_settings = None

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
            log_file,
            mode="a",
            maxBytes=file_max_bytes,
            backupCount=5,
            encoding=None,
            delay=0,
        )
        file_handler.setLevel(file_log_level)
        file_handler.setFormatter(logging.Formatter(file_formatter))

        if not disable_file:
            self.addHandler(file_handler)

    def _add_run_handler(self, run_log_dir: Path) -> None:
        settings = self._handler_settings
        run_handler = logging.FileHandler(run_log_dir / _RUN_LOG_NAME, mode="a", delay=True)
        run_handler.setLevel(settings["file_log_level"])
        run_handler.setFormatter(logging.Formatter(settings["file_formatter"]))
        run_handler.set_name(_RUN_HANDLER_NAME)
        self.addHandler(run_handler)

    def add_run_handler(self, run_log_dir: Path) -> None:
        """Also write the log of this run where its results are produced.

        The shared log mixes every run ever made by this user; this one belongs to a
        single execution and travels with its results.

        Parameters
        ----------
        run_log_dir: Path
            Directory the log of this run is written to.
        """
        if self._handler_settings is None:
            return
        self._handler_settings["run_log_dir"] = run_log_dir
        self._add_run_handler(run_log_dir)

    def close_run_handler(self) -> None:
        """Stop writing the log of this run, so its file can be moved with the results."""
        for handler in list(self.handlers):
            if handler.get_name() == _RUN_HANDLER_NAME:
                self.removeHandler(handler)
                handler.close()
        if self._handler_settings is not None:
            self._handler_settings.pop("run_log_dir", None)

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
        run_log_dir: Optional[Path] = None,
    ) -> None:
        """Initialize console and file handlers with the given configurations.
        The effective log level of the logger is set to the lowest of the console and file log
        levels to ensure all messages are captured by the appropriate handlers.

        Parameters
        ----------
        file_log_level: int
            Log level for the file handler (e.g., logging.DEBUG, logging.INFO).
        file_formatter: str
            Log message format for the file handler.
        file_max_bytes: int
            Maximum size in bytes for the log file before rotation occurs.
        console_log_level: int
            Log level for the console handler (e.g., logging.DEBUG, logging.INFO).
        console_formatter: str
            Log message format for the console handler.
        log_dir: Path
            Directory where log files should be stored.
        disable_console: bool, optional
            If True, the console handler will not be added. Default is False.
        disable_file: bool, optional
            If True, the file handler will not be added. Default is False.
        run_log_dir: Path, optional
            Directory the log of this run is also written to. Default is None, which
            writes only the shared log.
        """
        # Set the effective level to the lowest of console/file levels
        self.setLevel(console_log_level)
        if file_log_level < console_log_level:
            self.setLevel(file_log_level)

        self._add_console_handler(console_log_level, console_formatter, disable_console)
        self._add_file_handler(
            file_log_level, file_formatter, file_max_bytes, log_dir, disable_file
        )
        self._handler_settings = {
            "file_log_level": file_log_level,
            "file_formatter": file_formatter,
            "file_max_bytes": file_max_bytes,
            "console_log_level": console_log_level,
            "console_formatter": console_formatter,
            "log_dir": log_dir,
            "disable_console": disable_console,
            "disable_file": disable_file,
        }
        if run_log_dir is not None:
            self.add_run_handler(run_log_dir)

    def get_handler_settings(self) -> Optional[dict]:
        """The arguments init_handlers was called with, so a process that does not
        inherit the handlers can build the same ones.

        Returns
        -------
        Optional[dict]
            Keyword arguments for init_handlers, or None if it was never called.
        """
        return self._handler_settings

    def enable_warning_capture(self, force_runtimewarning_visible: bool = True) -> None:
        """
        Redirect Python warnings (e.g., SciPy/NumPy RuntimeWarning) into logging
        and use the same handlers/formatters configured on this DycovLogger.
        This uses Python's built-in logging.captureWarnings(True), which sends
        warnings to the 'py.warnings' logger. We attach our handlers to that
        logger so the output looks identical to the rest of DyCoV logs.

        Parameters
        ----------
        force_runtimewarning_visible: bool, optional
            If True, forces RuntimeWarnings to be visible in the logs by setting their filter to
            "always". Default is True, which is recommended since many libraries use RuntimeWarning
            for important messages (e.g., NaN in results, convergence issues). Set to False if you
            want to respect the default warning filters and potentially hide some warnings.
        """

        def _formatwarning(
            message: str, category: type[Warning], filename: str, lineno: int, line: str = None
        ) -> str:
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
        producer: Optional[str] = None,
    ) -> None:
        """
        Set the active test context for the current thread.
        All subsequent log calls from this thread will include
        [Producer PCS.Benchmark.OC].
        Safe to use with parallel threads — each thread has its own context.

        Parameters
        ----------
        pcs: str, optional
            Power conversion system identifier (e.g., "GEN", "PDR", "STOR").
        benchmark: str, optional
            Benchmark name (e.g., "Benchmark1").
        oc: str, optional
            Operating condition name (e.g., "OC1").
        producer: str, optional
            Producer the test runs against (e.g., "Producer", "Wind_Farm").
        """
        set_test_context(pcs, benchmark, oc, producer)

    def clear_test_context(self) -> None:
        """Clear the active test context for the current thread."""
        clear_test_context()

    def warn_once(self, name: str, message: str) -> None:
        """
        Warn about something that holds for the whole test, however many times the check
        that spots it runs.

        Parameters
        ----------
        name: str
            Name of the child logger (e.g., "curves", "report", "simulation").
        message: str
            Warning message, reported only the first time it comes up in the active test.
        """
        if is_first_report(message):
            self.get_logger(name).warning(message)

    def get_logger(self, name: str) -> _ContextAdapter:
        """
        Return a context-aware child logger for the given name.
        The returned adapter automatically prepends [PCS.Benchmark.OC]
        to every message based on the calling thread's active context.

        Parameters
        ----------
        name: str
            Name of the child logger (e.g., "curves", "report", "simulation").

        Returns
        -------
        _ContextAdapter
            A LoggerAdapter that injects the test context into log messages.
        """
        child = self.getChild(name)
        return _ContextAdapter(child, {})
