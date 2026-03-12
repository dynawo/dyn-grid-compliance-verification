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
from typing import Optional

from dycov.logging.logger import DycovLogger
import dycov.logging.test_context as _test_context


def _get_instance() -> DycovLogger:
    # Use DycovLogger as the default logging.Logger class
    logging.setLoggerClass(DycovLogger)
    return logging.getLogger("DyCoV")


def enable_warning_capture(force_runtimewarning_visible: bool = True) -> None:
    """
    Convenience function to enable warning capture on the DyCoV root logger.
    Call this AFTER dycov_logging.init_handlers(...).
    """
    if isinstance(dycov_logging, DycovLogger):
        dycov_logging.enable_warning_capture(
            force_runtimewarning_visible=force_runtimewarning_visible
        )


def set_test_context(
    pcs: Optional[str] = None,
    benchmark: Optional[str] = None,
    oc: Optional[str] = None,
) -> None:
    """
    Set the active test context for the current thread/process.
    All subsequent log lines will be prefixed with [PCS.Benchmark.OC].

    Usage:
        from dycov.logging.logging import set_test_context
        set_test_context(pcs="PCS_RTE-I16z1", benchmark="ThreePhaseFault", oc="TransientHiZTc800")
    """
    _test_context.set_test_context(pcs=pcs, benchmark=benchmark, oc=oc)


def clear_test_context() -> None:
    """Clear the active test context for the current thread/process."""
    _test_context.clear_test_context()


# Root logger for DyCoV
dycov_logging = _get_instance()
