#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from unittest.mock import MagicMock

import pytest

from dycov.curves.dynawo.runtime.dynawo_simulator import DynawoResult
from dycov.curves.dynawo.runtime.retry_strategy import RetrySettings, SolverRetryStrategy

MODULE = "dycov.curves.dynawo.runtime.retry_strategy"


@pytest.fixture
def retry_environment(mocker):
    logger = MagicMock()
    mocker.patch(f"{MODULE}.dycov_logging.get_logger", return_value=logger)
    mocker.patch(f"{MODULE}.replace_placeholders.modify_par_file")
    mocker.patch(f"{MODULE}.replace_placeholders.modify_jobs_file")
    return logger


@pytest.mark.parametrize("disable_retry_logs", [True, False])
def test_retry_warnings_follow_disable_flag(mocker, retry_environment, disable_retry_logs):
    attempts = []

    def fake_run_base(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            return DynawoResult(False, "", False, None, 1.0)
        return DynawoResult(True, "", False, None, 1.0)

    mocker.patch(f"{MODULE}.DynawoSimulator.run_base", side_effect=fake_run_base)

    settings = RetrySettings(disable_retry_logs=disable_retry_logs)
    strategy = SolverRetryStrategy(settings)
    strategy.run(
        run=MagicMock(),
        solver=MagicMock(solver_id="IDA", solver_lib="lib", minimum_time_step=1.0,
                         minimal_acceptable_step=1e-6, absAccuracy=1e-6, relAccuracy=1e-4),
        output_dir=MagicMock(),
        working_oc_dir=MagicMock(),
        jobs_output_dir=MagicMock(),
        bm_name="BM",
        oc_name="OC",
        max_sim_time=10.0,
    )

    warning_messages = [
        call.args[0] for call in retry_environment.warning.call_args_list
    ]
    if disable_retry_logs:
        assert warning_messages == []
    else:
        assert "Retry: reducing minimum time step" in warning_messages
