#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from __future__ import annotations

import signal
import threading
from typing import Callable, Iterable

# --- Termination helpers -----------------------------------------------------


def terminate_dynawo_children(timeout: float = 5.0) -> None:
    """Stop all Dynawo processes launched by DynawoSimulator (best-effort)."""
    try:
        from dycov.curves.dynawo.runtime.dynawo_simulator import DynawoSimulator

        DynawoSimulator.terminate_all_children(timeout=timeout)
    except Exception:
        # Never raise from a termination helper
        pass


def terminate_report_children(timeout: float = 5.0) -> None:
    """Stop all LaTeX (pdflatex) processes launched by report.py (best-effort)."""
    try:
        from dycov.report.report import terminate_all_children as _term

        _term(timeout=timeout)
    except Exception:
        pass


def terminate_all_children(timeout: float = 5.0) -> None:
    """Stop all known external children (Dynawo + LaTeX)."""
    terminate_dynawo_children(timeout=timeout)
    terminate_report_children(timeout=timeout)


# --- Signal handling (main-thread only) -------------------------------------


def install_signal_handlers(
    on_exit: Callable[[int], None],
    extra_signals: Iterable[signal.Signals] = (signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT),
) -> None:
    """Install minimal signal handlers that delegate to `on_exit(exit_code)`.

    Parameters
    ----------
    on_exit : Callable[[int], None]
        Callback executed in the main thread when a handled signal arrives. It receives
        the conventional exit code (130 for SIGINT, 143 for SIGTERM, else 1).
    extra_signals : Iterable[signal.Signals]
        Additional signals to trap besides SIGINT.
    """
    if threading.current_thread() is not threading.main_thread():
        return

    def _handler(signum, frame):
        try:
            if signum == signal.SIGINT:
                code = 130
            elif signum == signal.SIGTERM:
                code = 143
            else:
                code = 1
            on_exit(code)
        except Exception:
            # Never raise from a signal handler
            pass

    try:
        signal.signal(signal.SIGINT, _handler)
    except Exception:
        pass
    for sig in extra_signals:
        try:
            signal.signal(sig, _handler)
        except Exception:
            pass
