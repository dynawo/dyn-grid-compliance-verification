#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import pytest

from dycov.logging import dycov_logging


@pytest.fixture
def capture_error_logs(monkeypatch):
    """Patches dycov_logging.get_logger and returns the list of captured error messages."""
    logs = []

    class _ErrorCollector:
        def error(self, msg):
            logs.append(msg)

    monkeypatch.setattr(dycov_logging, "get_logger", lambda name: _ErrorCollector())
    return logs
