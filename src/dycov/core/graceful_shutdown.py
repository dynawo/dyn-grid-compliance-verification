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
from typing import Callable, Iterable, List, Optional

# ---------------------------------------------------------------------------
# Termination helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Signal handling
# ---------------------------------------------------------------------------


def _available_signals(candidates: Iterable[str]) -> List[int]:
    """Return a list of available signal numbers for the given candidate names."""
    sigs: List[int] = []
    for name in candidates:
        sig = getattr(signal, name, None)
        if sig is not None:
            sigs.append(sig)
    return sigs


def install_signal_handlers(
    on_exit: Callable[[int], None],
    extra_signals: Optional[Iterable[int]] = None,
) -> None:
    """Install minimal signal handlers that delegate to `on_exit(exit_code)`.

    Parameters
    ----------
    on_exit : Callable[[int], None]
        Callback executed in the main thread when a handled signal arrives.
        It receives the conventional exit code (130 for SIGINT, 143 for SIGTERM, else 1).
    extra_signals : Iterable[int] | None
        Additional signal numbers to trap besides SIGINT. If None, a cross-platform
        default is used: on Unix-like systems [SIGTERM, SIGHUP, SIGQUIT], on Windows
        typically [SIGTERM].
    """
    # Only register in main thread
    if threading.current_thread() is not threading.main_thread():
        return

    def _handler(signum, frame):  # type: ignore[no-redef]
        try:
            if signum == getattr(signal, "SIGINT", None):
                code = 130
            elif signum == getattr(signal, "SIGTERM", None):
                code = 143
            else:
                code = 1
            on_exit(code)
        except Exception:
            # Never raise from a signal handler
            pass

    # Always trap SIGINT
    try:
        signal.signal(signal.SIGINT, _handler)
    except Exception:
        pass

    # Build a safe set of extra signals if not provided
    if extra_signals is None:
        extra_signals = _available_signals(["SIGTERM", "SIGHUP", "SIGQUIT"])

    for sig in extra_signals:
        try:
            signal.signal(sig, _handler)
        except Exception:
            # Some signals may not be settable in certain environments (e.g., pytest on Windows)
            pass
