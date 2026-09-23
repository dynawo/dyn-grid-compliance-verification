#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path

import pytest

from dycov.curves.dynawo.runtime import retry_strategy as retry_strategy_module
from dycov.curves.dynawo.runtime.dynawo_simulator import DynawoResult, DynawoSimulator
from dycov.curves.dynawo.runtime.retry_strategy import RetrySettings, SolverRetryStrategy
from dycov.curves.dynawo.runtime.run_types import SolverParams

MAX_SIM_TIME = 10.0
RETRY_HEADINGS = [
    "Retry 1/4: minStep 1e-06 -> 1e-07",
    "Retry 2/4: absAccuracy 1e-06 -> 1e-05",
    "Retry 3/4: added the small network parameters",
    "Retry 4/4: solver IDA -> SIM",
]
TIME_WARNING = f"Simulation time exceeds the maximum allowed ({MAX_SIM_TIME})"


class RecordingLogger:
    def __init__(self):
        self.messages = []

    def warning(self, message):
        self.messages.append(message)


@pytest.fixture
def recorded_warnings(monkeypatch):
    logger = RecordingLogger()
    monkeypatch.setattr(retry_strategy_module.dycov_logging, "get_logger", lambda name: logger)
    return logger.messages


@pytest.fixture
def recorded_writes(monkeypatch):
    writes = []
    for writer in ("modify_par_file", "add_parameters", "modify_jobs_file"):
        monkeypatch.setattr(
            retry_strategy_module.replace_placeholders,
            writer,
            lambda *args, _writer=writer, **kwargs: writes.append((_writer, args)),
        )
    return writes


@pytest.fixture
def failing_attempts(monkeypatch):
    return _patch_run_base(monkeypatch, successful_attempt=None)


def _patch_run_base(monkeypatch, successful_attempt):
    attempts = []

    def fake_run_base(*args, **kwargs):
        attempts.append(1)
        succeeded = len(attempts) == successful_attempt
        return DynawoResult(succeeded, "", False, None, MAX_SIM_TIME + 1.0)

    monkeypatch.setattr(DynawoSimulator, "run_base", staticmethod(fake_run_base))
    return attempts


def _run(strategy, solver):
    return strategy.run(
        run=None,
        solver=solver,
        output_dir=Path("output"),
        working_oc_dir=Path("working"),
        jobs_output_dir=Path("jobs"),
        bm_name="BM",
        oc_name="OC",
        max_sim_time=MAX_SIM_TIME,
    )


def _ida_solver():
    return SolverParams(
        solver_id="IDA",
        solver_lib="dynawo_SolverIDA",
        minimum_time_step=1e-6,
        minimal_acceptable_step=1e-6,
        absAccuracy=1e-6,
        relAccuracy=1e-4,
    )


def _sim_solver():
    return SolverParams(
        solver_id="SIM",
        solver_lib="dynawo_SolverSIM",
        minimum_time_step=1e-6,
        minimal_acceptable_step=1e-6,
        absAccuracy=1e-4,
        relAccuracy=None,
    )


def _modified_parameters(writes):
    return [args[2] for writer, args in writes if writer == "modify_par_file"]


def _added_parameters(writes):
    return [
        parameter["name"]
        for writer, args in writes
        if writer == "add_parameters"
        for parameter in args[3]
    ]


@pytest.mark.parametrize(
    "disable_retry_logs, expected_warnings",
    [(False, len(RETRY_HEADINGS) + 1), (True, 0)],
)
def test_retry_warnings_follow_disable_flag(
    recorded_warnings, recorded_writes, failing_attempts, disable_retry_logs, expected_warnings
):
    strategy = SolverRetryStrategy(RetrySettings(disable_retry_logs=disable_retry_logs))

    result = _run(strategy, _ida_solver())

    assert not result.succeeded
    assert len(failing_attempts) == 5
    assert len(recorded_warnings) == expected_warnings


def test_each_retry_says_which_attempt_it_is_and_what_it_changed(
    recorded_warnings, recorded_writes, failing_attempts
):
    strategy = SolverRetryStrategy(RetrySettings())

    _run(strategy, _ida_solver())

    retries = recorded_warnings[:-1]
    assert len(retries) == len(RETRY_HEADINGS)
    for warning, heading in zip(retries, RETRY_HEADINGS):
        assert warning.startswith(heading)
    assert recorded_warnings[-1] == TIME_WARNING


@pytest.mark.parametrize(
    "result, expected_reason",
    [
        (
            DynawoResult(False, "", False, None, MAX_SIM_TIME + 1.0),
            f"took 11.0s, over the {MAX_SIM_TIME}s limit",
        ),
        (
            DynawoResult(
                False,
                "Simulation Fails: network is not connected, logs in /work/dynawo.log",
                "network is not connected",
                None,
                1.0,
            ),
            "network is not connected",
        ),
        (
            DynawoResult(False, "job failed\nsolver diverged", False, None, 1.0),
            "solver diverged",
        ),
        (DynawoResult(False, "", False, None, 1.0), "Dynawo did not report success"),
    ],
)
def test_a_retry_says_why_the_previous_attempt_failed(
    monkeypatch, recorded_warnings, recorded_writes, result, expected_reason
):
    monkeypatch.setattr(DynawoSimulator, "run_base", staticmethod(lambda *args, **kwargs: result))
    strategy = SolverRetryStrategy(RetrySettings())

    _run(strategy, _ida_solver())

    assert recorded_warnings[0].endswith(f"(previous attempt: {expected_reason})")


@pytest.mark.parametrize("successful_attempt", [1, 2, 3, 4])
def test_retry_stops_at_the_first_successful_attempt(
    monkeypatch, recorded_warnings, recorded_writes, successful_attempt
):
    attempts = _patch_run_base(monkeypatch, successful_attempt=successful_attempt)
    strategy = SolverRetryStrategy(RetrySettings())

    result = _run(strategy, _ida_solver())

    assert result.succeeded
    assert len(attempts) == successful_attempt
    assert len(recorded_warnings) == successful_attempt - 1


def test_the_small_network_parameters_are_declared_once_a_retry_adds_them(
    monkeypatch, recorded_warnings, recorded_writes
):
    _patch_run_base(monkeypatch, successful_attempt=4)
    solver = _ida_solver()

    _run(SolverRetryStrategy(RetrySettings()), solver)

    assert solver.added_parameters["mxiterAlg"] == "30"
    assert solver.added_parameters["maximumNumberSlowStepIncrease"] == "100"


def test_flipping_the_solver_drops_the_parameters_added_to_the_one_left_behind(
    recorded_warnings, recorded_writes, failing_attempts
):
    solver = _ida_solver()

    _run(SolverRetryStrategy(RetrySettings()), solver)

    assert solver.solver_id == "SIM"
    assert solver.added_parameters == {}


def test_ida_retries_tune_the_ida_parameters(recorded_warnings, recorded_writes, failing_attempts):
    solver = _ida_solver()
    strategy = SolverRetryStrategy(RetrySettings())

    _run(strategy, solver)

    assert _modified_parameters(recorded_writes) == [
        "minStep",
        "minimalAcceptableStep",
        "relAccuracy",
        "absAccuracy",
    ]
    assert "mxiterAlg" in _added_parameters(recorded_writes)
    assert solver.solver_id == "SIM"
    assert solver.relAccuracy is None


def test_sim_retries_tune_the_sim_parameters(recorded_warnings, recorded_writes, failing_attempts):
    solver = _sim_solver()
    strategy = SolverRetryStrategy(RetrySettings())

    _run(strategy, solver)

    assert _modified_parameters(recorded_writes) == [
        "hMin",
        "minimalAcceptableStep",
        "fnormtol",
    ]
    assert "maxNewtonTry" in _added_parameters(recorded_writes)
    assert solver.solver_id == "IDA"
    assert solver.relAccuracy is not None


def test_settings_are_read_from_the_configuration(monkeypatch):
    config_type = type(retry_strategy_module.config)
    monkeypatch.setattr(config_type, "get_float", lambda *args: 2.0)
    monkeypatch.setattr(config_type, "get_boolean", lambda *args: False)
    monkeypatch.setattr(config_type, "get_int", lambda *args: 7)

    settings = RetrySettings.from_config(disable_retry_logs=True)

    assert settings.step_divisor == 2.0
    assert settings.accuracy_multiplier == 2.0
    assert not settings.add_parameters_small_network
    assert not settings.enable_solver_flip
    assert settings.allowed_retries == 7
    assert settings.disable_retry_logs
