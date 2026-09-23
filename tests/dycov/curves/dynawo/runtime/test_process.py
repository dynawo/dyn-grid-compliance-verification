#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for what the Dynawo log is asked about after a simulation."""

from pathlib import Path

from dycov.curves.dynawo.runtime._process import find_timeline_error

LOG_WITH_ERROR = """\
2026-09-23 10:02:16 | INFO  | model was built successfully
2026-09-23 10:02:17 | ERROR | network is not connected at t = 0.5
2026-09-23 10:02:17 | ERROR | simulation stopped
"""


def test_the_first_error_is_reported_without_its_timestamp_and_level(tmp_path: Path):
    log = tmp_path / "dynawo.log"
    log.write_text(LOG_WITH_ERROR)

    assert find_timeline_error(log) == "network is not connected at t = 0.5"


def test_a_log_without_errors_reports_none(tmp_path: Path):
    log = tmp_path / "dynawo.log"
    log.write_text("2026-09-23 10:02:16 | INFO  | end of job 'PCS'\n")

    assert find_timeline_error(log) is None


def test_a_log_that_was_never_written_reports_none(tmp_path: Path):
    assert find_timeline_error(tmp_path / "dynawo.log") is None


def test_an_error_logged_without_the_usual_prefix_comes_back_whole(tmp_path: Path):
    log = tmp_path / "dynawo.log"
    log.write_text("  ERROR: solver failed to converge  \n")

    assert find_timeline_error(log) == "ERROR: solver failed to converge"
