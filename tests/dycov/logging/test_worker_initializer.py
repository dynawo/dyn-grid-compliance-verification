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

import configparser
import io
import logging
import os
import signal
import subprocess
import sys
import textwrap
from logging.handlers import RotatingFileHandler

import pytest

from dycov.logging import dycov_logging, worker_initializer

FILE_FORMAT = "%(levelname)s|%(name)s|%(message)s"
EXECUTION_LOG = "dycov_run.log"

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

_POOL_START = "    context = multiprocessing.get_context"
assert _POOL_START in FORKSERVER_RUN
FORKSERVER_RUN_WITH_EXECUTION_LOG = FORKSERVER_RUN.replace(
    _POOL_START,
    f"    dycov_logging.add_run_handler(Path(sys.argv[1]))\n\n{_POOL_START}",
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


def test_a_worker_puts_back_the_configuration_of_the_run(tmp_path):
    from dycov.configuration.cfg import config

    layers = config.run_layers()
    user = configparser.ConfigParser(interpolation=None)
    user.optionxform = str
    user.read_string(layers["user"])
    if not user.has_section("DTR"):
        user.add_section("DTR")
    user.set("DTR", "current", "20240215")
    text = io.StringIO()
    user.write(text)
    changed = {**layers, "user": text.getvalue()}

    try:
        worker_initializer(None, changed)

        assert config.get_value("DTR", "current") == "20240215"
    finally:
        config.restore_run_layers(layers)


WORKER_CONFIGURATION_RUN = textwrap.dedent(
    '''
    """A run that sets up its configuration in memory, as the command line does, and reads it
    back from workers started apart."""

    import multiprocessing
    import sys
    from pathlib import Path

    from dycov.configuration.cfg import config
    from dycov.logging import worker_initializer


    def read(_):
        return (
            config.get_value("DTR", "current"),
            config.get_threshold("GridCode", "thr_reaction_time", -1.0),
            config.get_value("Global", "from_the_user_file"),
            config.get_value("Dynawo", "simulation_limit"),
        )


    if __name__ == "__main__":
        user_file = Path(sys.argv[2])
        user_file.write_text("[Global]\\nfrom_the_user_file = yes\\n")
        config.load_user_config(user_file)
        # What --dtr does, and an option set at run time where the default configuration has it
        config.set_value("DTR", "current", sys.argv[4])
        config.load_dtr_delta_config(sys.argv[4])
        config.set_value("Dynawo", "simulation_limit", "77")

        initargs = (None, config.run_layers()) if sys.argv[3] == "with" else (None,)
        context = multiprocessing.get_context(sys.argv[1])
        with context.Pool(1, initializer=worker_initializer, initargs=initargs) as pool:
            print(repr((read(0), pool.apply(read, (0,)))))
    '''
)


def _run_reading_the_configuration(tmp_path, start_method, layers, revision):
    script = tmp_path / "run.py"
    script.write_text(WORKER_CONFIGURATION_RUN, encoding="utf-8")
    env = dict(os.environ, HOME=str(tmp_path / "home"))
    run = subprocess.run(
        [sys.executable, str(script), start_method, str(tmp_path / "user.ini"), layers, revision],
        env=env,
        timeout=120,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    return eval(run.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize(
    "revision, reaction_time_limit", [("20240215", pytest.approx(0.10)), ("20260723", None)]
)
@pytest.mark.parametrize("start_method", ["forkserver", "spawn"])
def test_a_worker_started_apart_runs_with_the_configuration_of_the_run(
    tmp_path, start_method, revision, reaction_time_limit
):
    """#678: the revision of --dtr, its delta, the file of --user-config and what the run set."""
    main, worker = _run_reading_the_configuration(tmp_path, start_method, "with", revision)

    assert main == (revision, reaction_time_limit, "yes", "77")
    assert worker == main


@pytest.mark.parametrize("revision", ["20240215", "20260723"])
def test_a_worker_started_apart_without_the_layers_reads_the_files_alone(tmp_path, revision):
    """What #678 saw: the worker reads the revision of the files and no delta, and neither the
    file of --user-config nor what the run set."""
    main, worker = _run_reading_the_configuration(tmp_path, "forkserver", "without", revision)

    assert worker == ("20260723", pytest.approx(0.10), None, "30")
    assert worker != main


def test_a_forkserver_worker_writes_into_the_log_of_the_run(tmp_path):
    script = tmp_path / "run.py"
    script.write_text(FORKSERVER_RUN, encoding="utf-8")

    subprocess.run(
        [sys.executable, str(script), str(tmp_path)], check=True, timeout=120, capture_output=True
    )

    assert "INFO|DyCoV.Worker|desde el forkserver" in (tmp_path / "dycov.log").read_text(
        encoding="utf-8"
    )


def test_a_forkserver_worker_also_writes_into_the_log_of_the_execution(tmp_path):
    script = tmp_path / "run.py"
    script.write_text(FORKSERVER_RUN_WITH_EXECUTION_LOG, encoding="utf-8")

    subprocess.run(
        [sys.executable, str(script), str(tmp_path)], check=True, timeout=120, capture_output=True
    )

    assert "INFO|DyCoV.Worker|desde el forkserver" in (tmp_path / EXECUTION_LOG).read_text(
        encoding="utf-8"
    )


def test_a_worker_without_handlers_also_writes_into_the_log_of_the_execution(run_log, tmp_path):
    dycov_logging.add_run_handler(tmp_path)
    settings = dycov_logging.get_handler_settings()
    _detach_handlers()

    worker_initializer(settings)
    _log_from_the_worker("desde el worker")

    assert "INFO|DyCoV.Worker|desde el worker" in (tmp_path / EXECUTION_LOG).read_text(
        encoding="utf-8"
    )


def test_the_execution_log_is_not_rotated_while_several_processes_write_it(run_log, tmp_path):
    dycov_logging.add_run_handler(tmp_path)

    execution_handlers = [h for h in dycov_logging.handlers if h.get_name() == "run"]

    assert execution_handlers
    assert not any(isinstance(h, RotatingFileHandler) for h in execution_handlers)


def test_closing_the_execution_log_leaves_the_shared_one(run_log, tmp_path):
    dycov_logging.add_run_handler(tmp_path)

    dycov_logging.close_run_handler()
    _log_from_the_worker("solo en el compartido")

    assert "solo en el compartido" in run_log.read_text(encoding="utf-8")
    assert "run_log_dir" not in dycov_logging.get_handler_settings()
