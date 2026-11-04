#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023-2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import shutil

import pytest

from dycov.sanity_checks import system_checks


@pytest.mark.skipif(shutil.which("dynawo.sh") is not None, reason="Dynawo installed")
def test_launchers():
    with pytest.raises(OSError) as pytest_wrapped_e:
        system_checks.check_launchers("dynawo.sh")
    assert pytest_wrapped_e.type is OSError
    assert "Dynawo not found." in pytest_wrapped_e.value.args[0]


def _installed(monkeypatch, *commands):
    """Only the given commands are on the PATH."""
    monkeypatch.setattr(
        system_checks.shutil,
        "which",
        lambda command: f"/usr/bin/{command}" if str(command) in commands else None,
    )


def test_the_dynawo_check_does_not_ask_for_pdflatex(monkeypatch):
    _installed(monkeypatch, "dynawo.sh")

    system_checks.check_launchers("dynawo.sh")


def test_the_dynawo_check_names_dynawo_alone(monkeypatch):
    _installed(monkeypatch, "pdflatex", "open")

    with pytest.raises(OSError) as error:
        system_checks.check_launchers("dynawo.sh")

    assert error.value.args[0] == "Dynawo not found."


def test_the_report_needs_pdflatex(monkeypatch):
    _installed(monkeypatch, "dynawo.sh", "open")

    with pytest.raises(OSError) as error:
        system_checks.check_report_tools()

    assert "PdfLatex not found." in error.value.args[0]
    assert "Dynawo" not in error.value.args[0]


def test_the_report_tools_are_there(monkeypatch):
    _installed(monkeypatch, "pdflatex", "open")

    system_checks.check_report_tools()
