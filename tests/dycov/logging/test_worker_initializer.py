#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the preparation of a process pool worker."""

import logging
import signal
import subprocess
import sys
import textwrap

import pytest

from dycov.logging import dycov_logging, worker_initializer

FILE_FORMAT = "%(levelname)s|%(name)s|%(message)s"

FORKSERVER_RUN = textwrap.dedent(
    '''
    """A run whose pool starts its workers the way Python 3.14 does by default."""

    import logging
    import multiprocessing
    import sys
    from pathlib import Path

    from dycov.logging import dycov_logging, worker_initializer


    def work(message):
        dycov_logging.get_logger("Worker").info(message)


    if __name__ == "__main__":
        dycov_logging.init_handlers(
            logging.INFO,
            "%(levelname)s|%(name)s|%(message)s",
            10_000_000,
            logging.INFO,
            "%(levelname)s|%(message)s",
            Path(sys.argv[1]),
            disable_console=True,
        )

        context = multiprocessing.get_context("forkserver")
        with context.Pool(
            processes=1,
            initializer=worker_initializer,
            initargs=(dycov_logging.get_handler_settings(),),
        ) as pool:
            pool.map(work, ["desde el forkserver"])
    '''
)


def _detach_handlers():
    """Leaves the logger as a worker that did not inherit the configuration of the run finds it."""
    detached = list(dycov_logging.handlers)
    for handler in detached:
        dycov_logging.removeHandler(handler)
    dycov_logging.setLevel(logging.NOTSET)
    return detached


def _log_from_the_worker(message):
    dycov_logging.get_logger("Worker").info(message)


@pytest.fixture
def run_log(tmp_path):
    """The logger is process-wide, so the handlers of the session are restored afterwards."""
    previous_handlers = _detach_handlers()
    previous_level = dycov_logging.level

    dycov_logging.init_handlers(
        logging.INFO,
        FILE_FORMAT,
        10_000_000,
        logging.INFO,
        "%(levelname)s|%(message)s",
        tmp_path,
        disable_console=True,
    )

    yield tmp_path / "dycov.log"

    for handler in _detach_handlers():
        handler.close()
    for handler in previous_handlers:
        dycov_logging.addHandler(handler)
    dycov_logging.setLevel(previous_level)


def test_a_worker_without_handlers_writes_into_the_log_of_the_run(run_log):
    settings = dycov_logging.get_handler_settings()
    _detach_handlers()

    worker_initializer(settings)
    _log_from_the_worker("desde el worker")

    assert "INFO|DyCoV.Worker|desde el worker" in run_log.read_text(encoding="utf-8")


def test_a_worker_that_inherited_the_handlers_does_not_duplicate_them(run_log):
    settings = dycov_logging.get_handler_settings()
    inherited = len(dycov_logging.handlers)

    worker_initializer(settings)
    _log_from_the_worker("una sola vez")

    assert len(dycov_logging.handlers) == inherited
    assert run_log.read_text(encoding="utf-8").count("una sola vez") == 1


def test_a_run_without_handlers_leaves_the_worker_without_them():
    previous_handlers = _detach_handlers()

    try:
        worker_initializer(None)

        assert dycov_logging.handlers == []
    finally:
        for handler in previous_handlers:
            dycov_logging.addHandler(handler)


def test_the_worker_leaves_the_interrupt_to_the_main_process(run_log):
    previous = signal.getsignal(signal.SIGINT)

    try:
        worker_initializer(dycov_logging.get_handler_settings())

        assert signal.getsignal(signal.SIGINT) is signal.SIG_IGN
    finally:
        signal.signal(signal.SIGINT, previous)


def test_a_forkserver_worker_writes_into_the_log_of_the_run(tmp_path):
    script = tmp_path / "run.py"
    script.write_text(FORKSERVER_RUN, encoding="utf-8")

    subprocess.run(
        [sys.executable, str(script), str(tmp_path)], check=True, timeout=120, capture_output=True
    )

    assert "INFO|DyCoV.Worker|desde el forkserver" in (tmp_path / "dycov.log").read_text(
        encoding="utf-8"
    )
