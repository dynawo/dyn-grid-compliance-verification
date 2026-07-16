#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from __future__ import annotations

import os
import signal
import subprocess
import time
from collections import namedtuple
from pathlib import Path

from dycov.logging import dycov_logging

ProcessOutcome = namedtuple("ProcessOutcome", "completed_successfully stderr elapsed_seconds")


class _ProcRegistry:
    """Simple process registry for DynawoSimulator child processes."""

    def __init__(self) -> None:
        self._procs: list[subprocess.Popen] = []

    def add(self, p: subprocess.Popen) -> None:
        self._procs.append(p)

    def discard(self, p: subprocess.Popen) -> None:
        try:
            self._procs.remove(p)
        except ValueError:
            pass

    def active(self) -> list[subprocess.Popen]:
        return [p for p in list(self._procs) if p and p.poll() is None]


_proc_registry = _ProcRegistry()


def kill_process(proc: subprocess.Popen) -> None:
    """Kill a process and all its children.

    Parameters
    ----------
    proc : subprocess.Popen
        The process to kill.
    """
    if os.name == "nt":
        subprocess.run(
            f"taskkill /F /T /PID {proc.pid}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    else:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)


def run_dynawo_process(
    launcher_dwo: Path,
    jobs_filename: str,
    inputs_path: Path,
    simulation_limit: float | None,
) -> ProcessOutcome:
    """Run a Dynawo process with a timeout.

    Parameters
    ----------
    launcher_dwo : Path
        Path to the Dynawo launcher executable.
    jobs_filename : str
        Name of the .jobs file to execute (without extension).
    inputs_path : Path
        Path to the directory containing the .jobs file.
    simulation_limit : float | None
        Maximum allowed simulation time in seconds. If None, no timeout is applied.

    Returns
    -------
    ProcessOutcome
        A named tuple containing:
        - completed_successfully: True if the process completed successfully, False otherwise.
        - stderr: The standard error output from the process.
        - elapsed_seconds: The total time taken by the process in seconds.
    """
    dycov_logging.get_logger("DynawoSimulator").debug(
        f"Simulation limit: {simulation_limit} seconds."
    )
    proc = subprocess.Popen(
        [launcher_dwo, "jobs", f"{jobs_filename}.jobs"],
        cwd=inputs_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid if os.name != "nt" else None,
    )
    _proc_registry.add(proc)
    start_time = time.time()

    while (
        simulation_limit is None or (time.time() - start_time) < simulation_limit
    ) and proc.poll() is None:
        time.sleep(0.1)

    completed_successfully = False
    stderr_output = ""
    try:
        if proc.poll() is None:
            stderr_output = "Execution terminated due to timeout."
            kill_process(proc)
            proc.wait()
        else:
            stderr_output = proc.stderr.read().decode("utf-8")
            completed_successfully = "succeeded" in stderr_output
    finally:
        _proc_registry.discard(proc)

    return ProcessOutcome(
        completed_successfully=completed_successfully,
        stderr=stderr_output,
        elapsed_seconds=time.time() - start_time,
    )


def has_error_timeline(pcs_name: str, bm_name: str, oc_name: str, log_path: Path) -> bool:
    """Check if the Dynawo log file contains any error messages.

    Parameters
    ----------
    pcs_name : str
        Name of the PCS.
    bm_name : str
        Name of the benchmark.
    oc_name : str
        Name of the operating condition.
    log_path : Path
        Path to the Dynawo log file.

    Returns
    -------
    bool
        True if an error message is found in the log file, False otherwise.
    """
    if not log_path.is_file():
        dycov_logging.get_logger("DynawoSimulator").warning(f"Log file not found at {log_path}")
        return False
    with open(log_path, "r") as log:
        for line in log:
            if "ERROR" in line:
                dycov_logging.get_logger("DynawoSimulator").debug(
                    f"{pcs_name}.{bm_name}.{oc_name}: Error found in: {line.strip()}"
                )
                return True
    return False


def _sigterm_all(procs: list[subprocess.Popen]) -> None:
    for p in procs:
        try:
            if os.name == "nt":
                p.terminate()
            else:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except Exception:
            try:
                p.terminate()
            except Exception:
                pass


def _wait_with_deadline(procs: list[subprocess.Popen], timeout: float) -> None:
    deadline = time.time() + max(0.0, timeout)
    for p in procs:
        rem = deadline - time.time()
        if rem <= 0:
            break
        try:
            p.wait(timeout=rem)
        except Exception:
            pass


def _sigkill_survivors(procs: list[subprocess.Popen]) -> None:
    for p in procs:
        if p.poll() is not None:
            continue
        try:
            kill_process(p)
        except Exception:
            pass


def terminate_all_children(timeout: float = 5.0) -> None:
    """Gracefully stop all child processes started by DynawoSimulator.
    Idempotent and best-effort: never raises.

    Parameters
    ----------
    timeout : float, optional
        Time in seconds to wait for processes to terminate after sending SIGTERM before sending
        SIGKILL, by default 5.0
    """
    procs = _proc_registry.active()
    if not procs:
        return
    _sigterm_all(procs)
    _wait_with_deadline(procs, timeout)
    _sigkill_survivors(procs)
