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
import os
import signal
import types
from typing import Optional

from dycov.logging.logger import DycovLogger


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


def _end_worker(signum: int, frame: Optional[types.FrameType]) -> None:
    """Ends a worker its pool terminates, with the external processes it launched, which run
    in sessions of their own. A worker running its exit handlers exits at once, as an exception
    raised here would reach them; any other unwinds, which releases the task queue it may be
    waiting on, and the pool that terminates needs that queue."""
    from multiprocessing import util

    from dycov.core.graceful_shutdown import terminate_all_children

    terminate_all_children(timeout=5.0)
    if util._exiting:
        os._exit(128 + signum)
    raise SystemExit(128 + signum)


def worker_initializer(handler_settings: Optional[dict]) -> None:
    """Prepare a process pool worker.

    The main process coordinates the shutdown, so workers ignore SIGINT, and a worker that is
    told to end does not run the shutdown of the main process, which a forked worker inherits.
    A worker started with forkserver or spawn does not inherit the handlers of the run, and
    without them every record it emits is discarded, so they are built again here.

    Parameters
    ----------
    handler_settings: Optional[dict]
        Handler configuration of the run, from get_handler_settings().
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    for name in ("SIGTERM", "SIGHUP", "SIGQUIT"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _end_worker)

    if handler_settings and not dycov_logging.handlers:
        dycov_logging.init_handlers(**handler_settings)


def set_test_context(
    pcs: Optional[str] = None,
    benchmark: Optional[str] = None,
    oc: Optional[str] = None,
    producer: Optional[str] = None,
) -> None:
    """
    Convenience function to set the active test context for the current thread.

    Usage (at the start of each test, in its own thread):
        from dycov.logging import set_test_context
        set_test_context(pcs="PCS_RTE-I16z1", benchmark="ThreePhaseFault", oc="TransientHiZTc800")

    All subsequent log lines from this thread will be prefixed with:
        [Producer PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800]
    """
    dycov_logging.set_test_context(pcs=pcs, benchmark=benchmark, oc=oc, producer=producer)


def clear_test_context() -> None:
    """
    Convenience function to clear the active test context for the current thread.
    Call this when a test finishes to avoid context leaking into the next test
    if threads are reused (e.g., with a thread pool).
    """
    dycov_logging.clear_test_context()


dycov_logging = _get_instance()
