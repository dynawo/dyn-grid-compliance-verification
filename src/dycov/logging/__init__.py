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
import threading
import time
import types
from typing import Optional

from dycov.logging.logger import DycovLogger

_END_SIGNALS = ("SIGTERM", "SIGHUP", "SIGQUIT")
_ending = False
_watching_in: Optional[int] = None


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


def _in_task_loop(frame: Optional[types.FrameType]) -> bool:
    from multiprocessing import pool

    while frame is not None:
        if frame.f_code is pool.worker.__code__:
            return True
        frame = frame.f_back
    return False


def _end_worker(signum: int, frame: Optional[types.FrameType]) -> None:
    """Ends a worker its pool terminates, with the external processes it launched, which run
    in sessions of their own. A worker still in its task loop unwinds, which releases the task
    queue it may be waiting on, and the pool that terminates needs that queue; one that left it
    is already exiting and exits at once, as an exception raised here would reach the exit
    handlers it runs."""
    from dycov.core.graceful_shutdown import terminate_all_children

    global _ending
    _ending = True
    terminate_all_children(timeout=5.0)
    if not _in_task_loop(frame):
        os._exit(128 + signum)
    raise SystemExit(128 + signum)


def _deliver_again(wakeup: int, end_signals: set[int]) -> None:
    """Delivers an end signal to the worker again until its handler runs: one that reaches the
    worker as it starts to wait, for its next task or for the lock of the queue, leaves that wait
    blocked and the handler pending."""
    signum = None
    while signum not in end_signals:
        received = os.read(wakeup, 1)
        if not received:
            return
        signum = received[0]
    while True:
        time.sleep(0.2)
        if _ending or signal.getsignal(signum) is not _end_worker:
            return
        signal.pthread_kill(threading.main_thread().ident, signum)


def _watch_end_signals(end_signals: set[int]) -> None:
    global _watching_in
    if _watching_in == os.getpid() or not hasattr(signal, "pthread_kill"):
        return
    wakeup, notify = os.pipe()
    os.set_blocking(notify, False)
    signal.set_wakeup_fd(notify, warn_on_full_buffer=False)
    threading.Thread(target=_deliver_again, args=(wakeup, end_signals), daemon=True).start()
    _watching_in = os.getpid()


def worker_initializer(
    handler_settings: Optional[dict], config_layers: Optional[dict] = None
) -> None:
    """Prepare a process pool worker.

    The main process coordinates the shutdown, so workers ignore SIGINT, and a worker that is
    told to end does not run the shutdown of the main process, which a forked worker inherits.
    A worker started with forkserver or spawn does not inherit the handlers of the run, and
    without them every record it emits is discarded, so they are built again here.
    Nor does it inherit the configuration the run set up in memory, the revision of
    the DTR and the file given with --user-config among it, which is put back too.

    Parameters
    ----------
    handler_settings: Optional[dict]
        Handler configuration of the run, from get_handler_settings().
    config_layers: Optional[dict]
        Configuration of the run, from config.run_layers().
    """
    global _ending
    _ending = False
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    end_signals = {getattr(signal, name) for name in _END_SIGNALS if hasattr(signal, name)}
    for signum in end_signals:
        signal.signal(signum, _end_worker)
    _watch_end_signals(end_signals)

    if handler_settings and not dycov_logging.handlers:
        dycov_logging.init_handlers(**handler_settings)

    if config_layers is not None:
        # The configuration logs through this package, so it is imported once it exists
        from dycov.configuration.cfg import config

        config.restore_run_layers(config_layers)


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
