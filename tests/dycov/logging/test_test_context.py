#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the test context a log line carries and for the facts it reports once."""

import logging
from pathlib import Path

import pytest

from dycov.logging import dycov_logging
from dycov.logging.test_context import (
    clear_test_context,
    get_test_context,
    is_first_report,
    set_test_context,
)

FILE_FORMAT = "%(levelname)s|%(message)s"


@pytest.fixture(autouse=True)
def a_test_without_context():
    clear_test_context()
    yield
    clear_test_context()


@pytest.fixture
def run_log(tmp_path: Path):
    dycov_logging.handlers.clear()
    dycov_logging.init_handlers(
        logging.INFO,
        FILE_FORMAT,
        10_000_000,
        logging.INFO,
        FILE_FORMAT,
        tmp_path,
        disable_console=True,
    )
    yield tmp_path / "dycov.log"
    for handler in list(dycov_logging.handlers):
        dycov_logging.removeHandler(handler)
        handler.close()


def test_a_test_without_context_carries_no_prefix():
    assert get_test_context() == ""


def test_the_context_names_the_test():
    set_test_context("PCS_RTE-I16z1", "ThreePhaseFault", "TransientBolted")

    assert get_test_context() == "PCS_RTE-I16z1.ThreePhaseFault.TransientBolted"


def test_the_context_names_the_producer_the_test_runs_against():
    set_test_context("PCS_RTE-I16z1", "ThreePhaseFault", "TransientBolted", producer="Wind_Farm")

    assert get_test_context() == "Wind_Farm PCS_RTE-I16z1.ThreePhaseFault.TransientBolted"


def test_a_producer_alone_is_still_a_context():
    set_test_context(None, None, None, producer="Wind_Farm")

    assert get_test_context() == "Wind_Farm"


def test_a_fact_is_reported_the_first_time_only():
    set_test_context("PCS", "BM", "OC")

    assert is_first_report("no reference values") is True
    assert is_first_report("no reference values") is False


def test_each_fact_is_reported_on_its_own():
    set_test_context("PCS", "BM", "OC")
    is_first_report("no reference values")

    assert is_first_report("another fact") is True


def test_the_next_test_reports_the_same_fact_again():
    set_test_context("PCS", "BM", "OC1")
    is_first_report("no reference values")

    set_test_context("PCS", "BM", "OC2")

    assert is_first_report("no reference values") is True


def test_a_fact_a_check_spots_again_is_logged_once(run_log):
    set_test_context("PCS", "BM", "OC")

    for _ in range(3):
        dycov_logging.warn_once("Common Validation", "No reference values in BusPDR_BUS_Voltage")

    assert run_log.read_text().count("No reference values in BusPDR_BUS_Voltage") == 1


def test_the_warning_carries_the_context_of_its_test(run_log):
    set_test_context("PCS", "BM", "OC", producer="Wind_Farm")

    dycov_logging.warn_once("Common Validation", "No reference values in BusPDR_BUS_Voltage")

    assert "Wind_Farm PCS.BM.OC: No reference values" in run_log.read_text()
