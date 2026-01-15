#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import signal
import sys
import types

# Import the module under test
from dycov.core.graceful_shutdown import (
    install_signal_handlers,
    terminate_all_children,
    terminate_dynawo_children,
    terminate_report_children,
)


def test_module_imports_and_api():
    # Basic API presence
    assert callable(install_signal_handlers)
    assert callable(terminate_all_children)
    assert callable(terminate_dynawo_children)
    assert callable(terminate_report_children)


def test_install_signal_handlers_no_extra_signals_does_not_raise():
    # Save current SIGINT handler to restore later
    prev = signal.getsignal(signal.SIGINT)

    calls = []

    def _on_exit(code: int):
        # We won't actually send signals; just ensure registration does not raise
        calls.append(code)

    try:
        # Should not raise on any platform
        install_signal_handlers(_on_exit)
    finally:
        # Restore previous handler
        try:
            signal.signal(signal.SIGINT, prev)
        except Exception:
            pass


def test_terminate_all_children_invokes_dynawo_and_report(monkeypatch):
    """Simulate presence of DynawoSimulator and report.terminate_all_children
    via sys.modules and ensure our helpers call them without raising.
    """
    # Create fake dynawo_simulator module
    dynawo_mod = types.ModuleType("dycov.curves.dynawo.runtime.dynawo_simulator")

    class _DynawoSimulator:
        called = []

        @staticmethod
        def terminate_all_children(timeout: float = 5.0):
            _DynawoSimulator.called.append(timeout)

    dynawo_mod.DynawoSimulator = _DynawoSimulator

    # Create fake report module
    report_mod = types.ModuleType("dycov.report.report")
    report_called = []

    def _report_term(timeout: float = 5.0):
        report_called.append(timeout)

    report_mod.terminate_all_children = _report_term

    # Register fakes in sys.modules
    sys.modules["dycov.curves.dynawo.runtime.dynawo_simulator"] = dynawo_mod
    sys.modules["dycov.report.report"] = report_mod

    try:
        # Individual helpers
        terminate_dynawo_children(timeout=3.0)
        terminate_report_children(timeout=4.0)
        # Aggregate helper
        terminate_all_children(timeout=2.5)

        assert _DynawoSimulator.called == [3.0, 2.5]
        assert report_called == [4.0, 2.5]
    finally:
        # Clean up fakes
        sys.modules.pop("dycov.curves.dynawo.runtime.dynawo_simulator", None)
        sys.modules.pop("dycov.report.report", None)
