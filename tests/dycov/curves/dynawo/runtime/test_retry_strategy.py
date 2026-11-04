#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import shutil
from pathlib import Path

import pandas as pd
import pytest
from lxml import etree

import dycov
from dycov.curves.dynawo.runtime import retry_strategy as retry_strategy_module
from dycov.curves.dynawo.runtime._curves import SimulatedCurves
from dycov.curves.dynawo.runtime.dynawo_simulator import DynawoResult, DynawoSimulator
from dycov.curves.dynawo.runtime.retry_strategy import RetrySettings, SolverRetryStrategy
from dycov.curves.dynawo.runtime.run_types import DynawoRunInputs, SolverParams

MAX_SIM_TIME = 10.0
RETRY_HEADINGS = [
    "Retry 1/4: minStep 1e-06 -> 1e-07",
    "Retry 2/4: absAccuracy 1e-06 -> 1e-05",
    "Retry 3/4: added the small network parameters",
    "Retry 4/4: solver IDA -> SIM",
]
TIME_WARNING = f"Simulation time exceeds the maximum allowed ({MAX_SIM_TIME})"
CURVES_FILE = Path("working/jobs/curves/curves.csv")
DIVERGENCE = "BusPDR_BUS_Voltage reached 4.2e+06 pu, beyond 10 pu"
RUN = DynawoRunInputs(
    pcs_name="PCS",
    launcher_dwo=Path("dynawo.sh"),
    curves_dict={},
    generators=[],
    s_nom=100.0,
    s_nref=100.0,
)


class RecordingLogger:
    def __init__(self):
        self.messages = []
        self.debug_messages = []

    def warning(self, message):
        self.messages.append(message)

    def debug(self, message):
        self.debug_messages.append(message)


@pytest.fixture
def recording_logger(monkeypatch):
    logger = RecordingLogger()
    monkeypatch.setattr(retry_strategy_module.dycov_logging, "get_logger", lambda name: logger)
    return logger


@pytest.fixture
def recorded_warnings(recording_logger):
    return recording_logger.messages


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


def _run(strategy, solver, run=None):
    return strategy.run(
        run=run,
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
    return [args[3] for writer, args in writes if writer == "modify_par_file"]


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

    assert not result.usable
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


def test_every_attempt_reports_how_long_dynawo_ran(monkeypatch, recording_logger, recorded_writes):
    _patch_run_base(monkeypatch, successful_attempt=2)
    strategy = SolverRetryStrategy(RetrySettings())

    _run(strategy, _ida_solver())

    assert recording_logger.debug_messages == [
        "Attempt 1 ran in 11.0s (failed)",
        "Attempt 2 ran in 11.0s (succeeded)",
    ]


def _dynawo_ends_well(monkeypatch):
    attempts = []

    def run_base(*args, **kwargs):
        attempts.append(1)
        return DynawoResult(True, None, None, CURVES_FILE, 1.0)

    monkeypatch.setattr(DynawoSimulator, "run_base", staticmethod(run_base))
    return attempts


def _curves_read_as(monkeypatch, *simulated):
    """The curves each attempt reads, in turn; the last one stands for any later attempt."""
    read = []

    def read_simulated_curves(run, curves_file):
        read.append((run, curves_file))
        return simulated[min(len(read), len(simulated)) - 1]

    monkeypatch.setattr(retry_strategy_module, "read_simulated_curves", read_simulated_curves)
    return read


_DIVERGED = SimulatedCurves(
    pd.DataFrame({"time": [0.0, 1.0], "BusPDR_BUS_Voltage": [1.0, 4.2e6]}), DIVERGENCE
)
_SOUND = SimulatedCurves(
    pd.DataFrame({"time": [0.0, 1.0], "BusPDR_BUS_Voltage": [1.0, 0.9]}), None
)


def test_a_diverged_attempt_is_retried_and_quoted(monkeypatch, recording_logger, recorded_writes):
    """#675: a run Dynawo ended well after diverging is not a usable one, which a retry may
    cure."""
    attempts = _dynawo_ends_well(monkeypatch)
    _curves_read_as(monkeypatch, _DIVERGED, _SOUND)

    attempt = _run(SolverRetryStrategy(RetrySettings()), _ida_solver(), RUN)

    assert len(attempts) == 2
    assert attempt.usable
    assert attempt.curves is _SOUND.curves
    [retry] = recording_logger.messages
    assert retry.startswith(RETRY_HEADINGS[0])
    assert retry.endswith(f"(previous attempt: diverged, {DIVERGENCE})")
    assert recording_logger.debug_messages == [
        "Attempt 1 ran in 1.0s (diverged)",
        "Attempt 2 ran in 1.0s (succeeded)",
    ]


def test_a_divergence_leaves_what_dynawo_reported_as_it_was(
    monkeypatch, recorded_warnings, recorded_writes
):
    """Dynawo ended the run well; that the curves diverged is said apart from it."""
    _dynawo_ends_well(monkeypatch)
    _curves_read_as(monkeypatch, _DIVERGED)

    attempt = _run(SolverRetryStrategy(RetrySettings()), _ida_solver(), RUN)

    assert attempt.dynawo.succeeded is True
    assert attempt.divergence == DIVERGENCE
    assert attempt.curves.empty
    assert not attempt.usable


def test_the_curves_are_read_from_the_file_of_the_run_with_its_inputs(
    monkeypatch, recorded_warnings, recorded_writes
):
    _dynawo_ends_well(monkeypatch)
    read = _curves_read_as(monkeypatch, _SOUND)

    _run(SolverRetryStrategy(RetrySettings()), _ida_solver(), RUN)

    assert read == [(RUN, CURVES_FILE)]


@pytest.mark.parametrize(
    "result",
    [
        DynawoResult(False, "job failed", None, CURVES_FILE, 1.0),
        DynawoResult(True, None, None, None, 1.0),
    ],
    ids=["Dynawo failed", "no curves file"],
)
def test_no_curves_are_read_when_dynawo_left_none_to_read(
    monkeypatch, recorded_warnings, recorded_writes, result
):
    monkeypatch.setattr(DynawoSimulator, "run_base", staticmethod(lambda *args, **kwargs: result))
    read = _curves_read_as(monkeypatch, _SOUND)

    attempt = _run(SolverRetryStrategy(RetrySettings()), _ida_solver(), RUN)

    assert read == []
    assert attempt.curves.empty
    assert attempt.divergence is None


@pytest.mark.parametrize("successful_attempt", [1, 2, 3, 4])
def test_retry_stops_at_the_first_successful_attempt(
    monkeypatch, recorded_warnings, recorded_writes, successful_attempt
):
    attempts = _patch_run_base(monkeypatch, successful_attempt=successful_attempt)
    strategy = SolverRetryStrategy(RetrySettings())

    result = _run(strategy, _ida_solver())

    assert result.usable
    assert len(attempts) == successful_attempt
    assert len(recorded_warnings) == successful_attempt - 1


def _failing_with(monkeypatch, timeline_error):
    attempts = []

    def fake_run_base(*args, **kwargs):
        attempts.append(1)
        return DynawoResult(False, "", timeline_error, None, 1.0)

    monkeypatch.setattr(DynawoSimulator, "run_base", staticmethod(fake_run_base))
    return attempts


@pytest.mark.parametrize(
    "timeline_error",
    [
        "parameter WPP_tLagM not found in set merged_Wind_Turbine ( PARParametersSet.cpp:156 )",
        "error while parsing file Producer.par : error while parsing stream bad lexical cast: "
        "source type value could not be interpreted as target ( PARXmlImporter.cpp:63 ) "
        "( PARXmlImporter.cpp:45 )",
        "error while parsing file Producer.dyd : unexpected element ( DYDXmlImporter.cpp:88 )",
        "parameter voltageSetPointChange has no value ( DYNParameter.hpp:58 )",
        "failed to retrieve parameter weight_gen cardinality (nbGen) ( DYNSubModel.cpp:458 )",
        "failed to retrieve multiple variable's cardinality for weight_gen : the nbGen "
        "cardinality parameter is not set ( DYNSubModel.cpp:512 )",
        "unable to find lib DYNModelUnknown ( DYNCompiler.cpp:284 )",
        "invalid dynamic connect between Gen_terminal and Bus_ACPIN : ACPIN is unknown "
        "( DYNCompiler.cpp:1009 )",
        "element WT_terminalX not found in subModel Wind_Turbine (type "
        "IECWT4BCurrentSource2020) ( DYNSubModel.cpp:262 )",
        "missing 'parFile' attribute for model Wind_Turbine in the dyd file (whereas 'parId' "
        "is defined) ( DYNDynamicData.cpp:258 )",
        'boost::filesystem::canonical: No such file or directory: "/work/Nope.par"',
    ],
    ids=[
        "missing parameter",
        "unreadable PAR",
        "unreadable DYD",
        "parameter without value",
        "missing cardinality",
        "cardinality not set",
        "unknown library",
        "unknown connection",
        "unknown variable",
        "PAR not named",
        "missing PAR",
    ],
)
def test_an_error_in_the_inputs_of_the_model_is_not_retried(
    monkeypatch, recorded_warnings, recorded_writes, timeline_error
):
    attempts = _failing_with(monkeypatch, timeline_error)

    attempt = _run(SolverRetryStrategy(RetrySettings()), _ida_solver())

    assert attempt.usable is False
    assert attempt.dynawo.timeline_error == timeline_error
    assert len(attempts) == 1
    assert recorded_writes == []
    assert not [message for message in recorded_warnings if message.startswith("Retry")]
    assert "Not retried: Dynawo rejected the inputs of the model" in recorded_warnings


@pytest.mark.parametrize(
    "timeline_error",
    [
        "KINSOL fails to solve the problem ( DYNSolverKINAlgRestoration.cpp:432 )",
        "no value found for mandatory solver parameter 'hMin' (parameter set 'SIM', "
        "parameter file 'solvers.par') ( DYNSolverImpl.cpp:443 )",
    ],
    ids=["numerical", "solver setting"],
)
def test_an_error_a_solver_setting_may_settle_is_retried(
    monkeypatch, recorded_warnings, recorded_writes, timeline_error
):
    attempts = _failing_with(monkeypatch, timeline_error)

    _run(SolverRetryStrategy(RetrySettings()), _ida_solver())

    assert len(attempts) == 5


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


# A run writes solvers.par and builds its solver from the same configuration, so the file holds
# the settings of _ida_solver() and _sim_solver()
_SOLVER_SETTINGS = {
    "ida_order": "2",
    "ida_initStep": "1e-07",
    "ida_minStep": "1e-06",
    "ida_maxStep": "10",
    "ida_absAccuracy": "1e-06",
    "ida_relAccuracy": "0.0001",
    "ida_minimalAcceptableStep": "1e-06",
    "sim_hMin": "1e-06",
    "sim_hMax": "0.001",
    "sim_kReduceStep": "0.5",
    "sim_maxNewtonTry": "10",
    "sim_linearSolverName": "KLU",
    "sim_fnormtol": "0.0001",
    "sim_minimalAcceptableStep": "1e-06",
}


def _solvers_par(working_oc_dir: Path) -> None:
    shutil.copy(Path(dycov.__file__).parent / "model_lib" / "solvers.par", working_oc_dir)
    retry_strategy_module.replace_placeholders.dump_file(
        working_oc_dir, "solvers.par", _SOLVER_SETTINGS
    )


def _solver_sets(working_oc_dir: Path) -> dict[str, dict[str, str]]:
    root = etree.parse(working_oc_dir / "solvers.par").getroot()
    return {
        parameter_set.get("id"): {
            par.get("name"): par.get("value") for par in parameter_set if par.get("name")
        }
        for parameter_set in root.iter("{*}set")
    }


@pytest.fixture
def written_solvers(monkeypatch, tmp_path):
    """The solvers.par of a test, written by the real writers; the job file is left aside."""
    _solvers_par(tmp_path)
    monkeypatch.setattr(
        retry_strategy_module.replace_placeholders, "modify_jobs_file", lambda *args: None
    )
    return tmp_path


def _run_in(strategy, solver, working_oc_dir):
    return strategy.run(
        run=None,
        solver=solver,
        output_dir=Path("output"),
        working_oc_dir=working_oc_dir,
        jobs_output_dir=Path("jobs"),
        bm_name="BM",
        oc_name="OC",
        max_sim_time=MAX_SIM_TIME,
    )


def test_sim_retries_tune_the_sim_set_and_leave_the_ida_one_as_configured(
    recorded_warnings, failing_attempts, written_solvers
):
    configured = _solver_sets(written_solvers)

    _run_in(SolverRetryStrategy(RetrySettings()), _sim_solver(), written_solvers)

    tuned = _solver_sets(written_solvers)
    assert tuned["IDA"] == configured["IDA"]
    assert float(tuned["SIM"]["hMin"]) == pytest.approx(1e-7)
    assert float(tuned["SIM"]["minimalAcceptableStep"]) == pytest.approx(1e-7)
    assert float(tuned["SIM"]["fnormtol"]) == pytest.approx(1e-3)


def test_ida_retries_tune_the_ida_set_and_leave_the_sim_one_as_configured(
    recorded_warnings, failing_attempts, written_solvers
):
    configured = _solver_sets(written_solvers)

    _run_in(SolverRetryStrategy(RetrySettings()), _ida_solver(), written_solvers)

    tuned = _solver_sets(written_solvers)
    assert tuned["SIM"] == configured["SIM"]
    assert float(tuned["IDA"]["minStep"]) == pytest.approx(1e-7)
    assert float(tuned["IDA"]["minimalAcceptableStep"]) == pytest.approx(1e-7)
    assert float(tuned["IDA"]["absAccuracy"]) == pytest.approx(1e-5)
    assert float(tuned["IDA"]["relAccuracy"]) == pytest.approx(1e-3)


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
