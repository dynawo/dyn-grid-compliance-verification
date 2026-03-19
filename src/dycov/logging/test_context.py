#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import threading
from typing import Optional

_local = threading.local()


def set_test_context(pcs: Optional[str], benchmark: Optional[str], oc: Optional[str]) -> None:
    """Set the active test context for the current thread."""
    _local.pcs = pcs
    _local.benchmark = benchmark
    _local.oc = oc


def clear_test_context() -> None:
    """Clear the active test context for the current thread."""
    _local.pcs = None
    _local.benchmark = None
    _local.oc = None


def get_test_context() -> str:
    """
    Return the active test context for the current thread as a formatted string.
    Returns an empty string if no context is set.
    """
    pcs = getattr(_local, "pcs", None)
    benchmark = getattr(_local, "benchmark", None)
    oc = getattr(_local, "oc", None)

    if pcs or benchmark or oc:
        parts = [p for p in (pcs, benchmark, oc) if p]
        return ".".join(parts)
    return ""
