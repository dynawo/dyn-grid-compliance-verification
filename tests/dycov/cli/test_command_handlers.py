#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path
from unittest.mock import MagicMock

from dycov.cli.command_handlers import handle_performance_command, handle_validate_command
from dycov.core.global_variables import ELECTRIC_PERFORMANCE, MODEL_VALIDATION

_LAUNCHER = Path("dynawo.sh")


def _performance_args(model=None, curves=None):
    args = MagicMock()
    args.model = model
    args.curves = curves
    args.output = "output_dir"
    args.pcs = None
    args.only_dtr = True
    args.testing = False
    return args


def _validate_args(model=None, curves=None, reference=None):
    args = _performance_args(model=model, curves=curves)
    args.reference = reference
    return args


def test_performance_with_model_and_curves_plots_curves_as_reference(mocker):
    run_verification = mocker.patch("dycov.cli.command_handlers._run_verification", return_value=0)
    parser = MagicMock()
    args = _performance_args(model="Dynawo", curves="ProducerCurves/PPM")

    result = handle_performance_command(parser, args, _LAUNCHER)

    assert result == 0
    kwargs = run_verification.call_args.kwargs
    assert kwargs["producer_model"] == Path("Dynawo")
    assert kwargs["producer_curves"] is None
    assert kwargs["reference_curves"] == Path("ProducerCurves/PPM")
    assert kwargs["verification_type"] == ELECTRIC_PERFORMANCE


def test_performance_with_model_only_has_no_reference(mocker):
    run_verification = mocker.patch("dycov.cli.command_handlers._run_verification", return_value=0)
    parser = MagicMock()
    args = _performance_args(model="Dynawo")

    result = handle_performance_command(parser, args, _LAUNCHER)

    assert result == 0
    kwargs = run_verification.call_args.kwargs
    assert kwargs["producer_model"] == Path("Dynawo")
    assert kwargs["producer_curves"] is None
    assert kwargs["reference_curves"] is None


def test_performance_with_curves_only_validates_the_curves(mocker):
    run_verification = mocker.patch("dycov.cli.command_handlers._run_verification", return_value=0)
    parser = MagicMock()
    args = _performance_args(curves="ProducerCurves/PPM")

    result = handle_performance_command(parser, args, _LAUNCHER)

    assert result == 0
    kwargs = run_verification.call_args.kwargs
    assert kwargs["producer_model"] is None
    assert kwargs["producer_curves"] == Path("ProducerCurves/PPM")
    assert kwargs["reference_curves"] is None


def test_performance_without_inputs_reports_a_parser_error(mocker):
    run_verification = mocker.patch("dycov.cli.command_handlers._run_verification")
    parser = MagicMock()
    args = _performance_args()

    handle_performance_command(parser, args, _LAUNCHER)

    parser.error.assert_called_once()
    run_verification.assert_not_called()


def test_validate_with_model_and_reference_passes_both(mocker):
    run_verification = mocker.patch("dycov.cli.command_handlers._run_verification", return_value=0)
    parser = MagicMock()
    args = _validate_args(model="Dynawo", reference="ReferenceCurves")

    result = handle_validate_command(parser, args, _LAUNCHER)

    assert result == 0
    kwargs = run_verification.call_args.kwargs
    assert kwargs["producer_model"] == Path("Dynawo")
    assert kwargs["reference_curves"] == Path("ReferenceCurves")
    assert kwargs["verification_type"] == MODEL_VALIDATION


def test_validate_without_reference_reports_a_parser_error(mocker):
    run_verification = mocker.patch("dycov.cli.command_handlers._run_verification")
    parser = MagicMock()
    args = _validate_args(model="Dynawo")

    handle_validate_command(parser, args, _LAUNCHER)

    parser.error.assert_called_once()
    run_verification.assert_not_called()
