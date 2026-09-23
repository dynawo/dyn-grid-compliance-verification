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


def set_test_context(
    pcs: Optional[str],
    benchmark: Optional[str],
    oc: Optional[str],
    producer: Optional[str] = None,
) -> None:
    """Set the active test context for the current thread."""
    _local.producer = producer
    _local.pcs = pcs
    _local.benchmark = benchmark
    _local.oc = oc
    _local.reported = set()


def clear_test_context() -> None:
    """Clear the active test context for the current thread."""
    _local.producer = None
    _local.pcs = None
    _local.benchmark = None
    _local.oc = None
    _local.reported = set()


def get_test_context() -> str:
    """
    Return the active test context for the current thread as a formatted string.
    Returns an empty string if no context is set.
    """
    producer = getattr(_local, "producer", None)
    pcs = getattr(_local, "pcs", None)
    benchmark = getattr(_local, "benchmark", None)
    oc = getattr(_local, "oc", None)

    test = ".".join(p for p in (pcs, benchmark, oc) if p)
    if producer and test:
        return f"{producer} {test}"
    return producer or test


def is_first_report(message: str) -> bool:
    """
    Tell whether a message has still to be reported for the active test, and take note
    that it has been. Messages are forgotten whenever the test context changes.
    """
    reported = getattr(_local, "reported", None)
    if reported is None:
        reported = _local.reported = set()
    if message in reported:
        return False
    reported.add(message)
    return True
