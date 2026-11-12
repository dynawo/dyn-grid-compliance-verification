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
import time
from logging.handlers import RotatingFileHandler

import pytest

from dycov.logging import _end_worker, dycov_logging, worker_initializer

FILE_FORMAT = "%(levelname)s|%(name)s|%(message)s"
EXECUTION_LOG = "dycov_run.log"


@pytest.fixture(autouse=True)
def end_signals_of_the_test_process(monkeypatch):
    """A worker prepared in the process of the tests leaves its end signals as they were, and
    starts no thread to deliver them again."""
    monkeypatch.setattr("dycov.logging._watch_end_signals", lambda end_signals: None)
    monkeypatch.setattr("dycov.logging._ending", False)
    trapped = [getattr(signal, name) for name in ("SIGINT", "SIGTERM", "SIGHUP", "SIGQUIT")]
    previous = {sig: signal.getsignal(sig) for sig in trapped}
    yield
    for sig, handler in previous.items():
        signal.signal(sig, handler)


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
        # The revision the run follows, and an option set at run time where the default
        # configuration has it
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
    """#678: the revision of the run, its delta, the file of --user-config and what the run
    set."""
    main, worker = _run_reading_the_configuration(tmp_path, start_method, "with", revision)

    assert main == (revision, reaction_time_limit, "yes", "77")
    assert worker == main


@pytest.mark.parametrize("revision", ["20240215", "20260723"])
def test_a_worker_started_apart_without_the_layers_reads_the_files_alone(tmp_path, revision):
    """What #678 saw: the worker reads the files alone, which give no revision, so it reads no
    delta, and neither the file of --user-config nor what the run set."""
    main, worker = _run_reading_the_configuration(tmp_path, "forkserver", "without", revision)

    assert worker == (None, pytest.approx(0.10), None, "30")
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


# The run traps the end signals in the main process, and a forked worker inherits that trap,
# whose exit must not reach the exit handlers the worker may be running
TERMINATED_POOL_RUN = textwrap.dedent(
    '''
    """A run whose pool is terminated: a worker is told to end while it runs its exit handlers,
    another as it starts them, and another while a process it launched, as it launches Dynawo,
    is still running."""

    import atexit
    import multiprocessing
    import os
    import signal
    import subprocess
    import sys
    import time
    from multiprocessing import util

    from dycov.core.graceful_shutdown import install_signal_handlers, terminate_all_children
    from dycov.curves.dynawo.runtime._process import _proc_registry
    from dycov.logging import worker_initializer


    def on_exit(exit_code):
        terminate_all_children(timeout=5.0)
        raise SystemExit(exit_code)


    def finish_slowly(_):
        util.Finalize(None, time.sleep, args=(3,), exitpriority=0)
        return os.getpid()


    def be_told_to_end_on_exit(_):
        atexit.register(os.kill, os.getpid(), signal.SIGTERM)


    def launch_and_wait(_):
        child = subprocess.Popen(
            ["sleep", "60"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )
        _proc_registry.add(child)
        with open(sys.argv[2], "w") as pids:
            pids.write(f"{os.getpid()} {child.pid}")
        time.sleep(60)


    if __name__ == "__main__":
        install_signal_handlers(on_exit=on_exit)
        context = multiprocessing.get_context(sys.argv[1])

        pool = context.Pool(
            1, initializer=worker_initializer, initargs=(None,), maxtasksperchild=1
        )
        pool.apply(be_told_to_end_on_exit, (0,))
        time.sleep(1)
        pool.terminate()
        pool.join()

        pool = context.Pool(
            1, initializer=worker_initializer, initargs=(None,), maxtasksperchild=1
        )
        worker = pool.apply(finish_slowly, (0,))
        time.sleep(1)
        os.kill(worker, signal.SIGTERM)
        time.sleep(1)
        pool.terminate()
        pool.join()

        pool = context.Pool(1, initializer=worker_initializer, initargs=(None,))
        pool.apply_async(launch_and_wait, (0,))
        while not os.path.exists(sys.argv[2]) or not open(sys.argv[2]).read():
            time.sleep(0.1)
        pool.terminate()
        pool.join()
    '''
)


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    with open(f"/proc/{pid}/stat") as stat:
        return stat.read().split(")")[-1].split()[0] != "Z"


@pytest.mark.parametrize("start_method", ["fork", "forkserver"])
def test_a_terminated_pool_ends_its_workers_quietly_and_their_processes_with_them(
    tmp_path, start_method
):
    script = tmp_path / "run.py"
    script.write_text(TERMINATED_POOL_RUN, encoding="utf-8")
    pids = tmp_path / "pids.txt"

    run = subprocess.run(
        [sys.executable, str(script), start_method, str(pids)],
        timeout=120,
        capture_output=True,
        text=True,
    )
    _, child = (int(pid) for pid in pids.read_text().split())
    time.sleep(0.5)
    orphaned = _is_running(child)
    if orphaned:
        os.kill(child, signal.SIGKILL)

    assert run.returncode == 0, run.stderr
    assert "Traceback" not in run.stderr and "SystemExit" not in run.stderr, run.stderr
    assert not orphaned


GROUP_SIGNALLED_RUN = textwrap.dedent(
    '''
    """A run whose whole process group is told to end, as a closed terminal or a timeout does,
    while a worker of its pool waits for a task and another runs a process it launched. Like a
    run of the tool, it has loaded the modules whose processes its end stops."""

    import multiprocessing
    import os
    import subprocess
    import sys
    import time

    import dycov.curves.dynawo.runtime.dynawo_simulator
    import dycov.report.report
    from dycov.core.graceful_shutdown import install_signal_handlers, terminate_all_children
    from dycov.curves.dynawo.runtime._process import _proc_registry
    from dycov.logging import worker_initializer


    def on_exit(exit_code):
        terminate_all_children(timeout=5.0)
        raise SystemExit(exit_code)


    def launch_and_wait(_):
        child = subprocess.Popen(
            ["sleep", "60"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )
        _proc_registry.add(child)
        with open(sys.argv[2], "w") as pids:
            pids.write(f"{os.getpid()} {child.pid}")
        time.sleep(60)


    if __name__ == "__main__":
        install_signal_handlers(on_exit=on_exit)
        context = multiprocessing.get_context(sys.argv[1])
        with context.Pool(2, initializer=worker_initializer, initargs=(None,)) as pool:
            pool.map(launch_and_wait, [0])
    '''
)


@pytest.mark.parametrize(
    "end_signal, exit_code", [(signal.SIGTERM, 143), (signal.SIGHUP, 1)], ids=["TERM", "HUP"]
)
@pytest.mark.parametrize("start_method", ["fork", "forkserver"])
def test_a_run_whose_process_group_is_told_to_end_ends(
    tmp_path, start_method, end_signal, exit_code
):
    script = tmp_path / "run.py"
    script.write_text(GROUP_SIGNALLED_RUN, encoding="utf-8")
    pids = tmp_path / "pids.txt"
    run = subprocess.Popen(
        [sys.executable, str(script), start_method, str(pids)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    deadline = time.monotonic() + 60
    while not (pids.exists() and pids.read_text()) and time.monotonic() < deadline:
        time.sleep(0.1)

    os.killpg(run.pid, end_signal)
    try:
        _, stderr = run.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        os.killpg(run.pid, signal.SIGKILL)
        run.communicate()
        pytest.fail("the run did not end once its process group was told to")
    _, child = (int(pid) for pid in pids.read_text().split())
    time.sleep(0.5)
    orphaned = _is_running(child)
    if orphaned:
        os.kill(child, signal.SIGKILL)

    assert run.returncode == exit_code, stderr
    assert not orphaned


# The end signal of a worker that starts to wait just after it arrives is received, and its
# handler left pending, without the wait being interrupted; another thread receiving it does the
# same, deterministically
WAITING_WORKER_RUN = textwrap.dedent(
    '''
    """A worker waiting for a lock whose end signal another of its threads receives."""

    import multiprocessing
    import signal
    import threading
    import time

    from dycov.logging import worker_initializer


    def receive_the_end_signal():
        time.sleep(0.5)
        signal.pthread_kill(threading.get_ident(), signal.SIGTERM)


    if __name__ == "__main__":
        worker_initializer(None)
        lock = multiprocessing.Lock()
        lock.acquire()
        threading.Thread(target=receive_the_end_signal).start()
        lock.acquire()
    '''
)


def test_a_worker_its_end_signal_reaches_while_it_starts_to_wait_ends(tmp_path):
    script = tmp_path / "run.py"
    script.write_text(WAITING_WORKER_RUN, encoding="utf-8")

    try:
        run = subprocess.run(
            [sys.executable, str(script)], timeout=30, capture_output=True, text=True
        )
    except subprocess.TimeoutExpired:
        pytest.fail("the worker kept waiting once told to end")

    assert run.returncode == 128 + signal.SIGTERM, run.stderr


def test_the_worker_does_not_keep_the_end_signals_of_the_main_process():
    trapped = [getattr(signal, name) for name in ("SIGTERM", "SIGHUP", "SIGQUIT")]
    previous = {sig: signal.getsignal(sig) for sig in trapped + [signal.SIGINT]}

    def main_process_trap(signum, frame):
        raise SystemExit(128 + signum)

    try:
        for sig in trapped:
            signal.signal(sig, main_process_trap)

        worker_initializer(None)

        assert all(signal.getsignal(sig) is not main_process_trap for sig in trapped)
        assert all(callable(signal.getsignal(sig)) for sig in trapped)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


@pytest.fixture
def ending_calls(monkeypatch):
    class Exited(BaseException):
        pass

    calls = []

    def exit_at_once(code):
        calls.append(code)
        raise Exited

    monkeypatch.setattr(
        "dycov.core.graceful_shutdown.terminate_all_children", lambda timeout: None
    )
    monkeypatch.setattr(os, "_exit", exit_at_once)
    return calls, Exited


def test_a_worker_out_of_its_task_loop_exits_at_once(ending_calls):
    calls, exited = ending_calls

    with pytest.raises(exited):
        _end_worker(signal.SIGTERM, sys._getframe())

    assert calls == [128 + signal.SIGTERM]


def test_a_worker_in_its_task_loop_unwinds_it(ending_calls):
    import multiprocessing.pool
    import queue

    calls, _ = ending_calls
    tasks, results = queue.Queue(), queue.Queue()
    tasks.put((0, 0, lambda: _end_worker(signal.SIGTERM, sys._getframe()), (), {}))

    with pytest.raises(SystemExit) as ended:
        multiprocessing.pool.worker(tasks, results)

    assert ended.value.code == 128 + signal.SIGTERM
    assert calls == []
