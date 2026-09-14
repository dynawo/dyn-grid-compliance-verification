#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import zipfile
from pathlib import Path
from unittest.mock import MagicMock

from dycov.cli.command_handlers import (
    handle_excel2inputs_command,
    handle_performance_command,
    handle_validate_command,
)
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


def _validate_args(model=None, curves=None, reference=None, excel=None):
    args = _performance_args(model=model, curves=curves)
    args.reference = reference
    args.excel = excel
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


def _excel2inputs_args(excel="Producer.xlsx", output="output_dir"):
    args = MagicMock()
    args.excel = excel
    args.output = output
    return args


def test_excel2inputs_generates_from_the_workbook(mocker, tmp_path):
    workbook = tmp_path / "Producer.xlsx"
    workbook.touch()
    generate = mocker.patch(
        "dycov.cli.command_handlers.excel_generator.generate", return_value="report"
    )
    parser = MagicMock()

    result = handle_excel2inputs_command(parser, _excel2inputs_args(excel=str(workbook)))

    assert result == 0
    assert generate.call_args.args == (workbook, Path("output_dir"))


def test_excel2inputs_writes_next_to_the_workbook_by_default(mocker, tmp_path):
    workbook = tmp_path / "Producer.xlsx"
    workbook.touch()
    generate = mocker.patch(
        "dycov.cli.command_handlers.excel_generator.generate", return_value="report"
    )
    parser = MagicMock()

    handle_excel2inputs_command(parser, _excel2inputs_args(excel=str(workbook), output=None))

    assert generate.call_args.args == (workbook, tmp_path)


def test_excel2inputs_without_a_workbook_reports_a_parser_error(mocker, tmp_path):
    generate = mocker.patch("dycov.cli.command_handlers.excel_generator.generate")
    parser = MagicMock()

    handle_excel2inputs_command(parser, _excel2inputs_args(excel=str(tmp_path / "absent.xlsx")))

    parser.error.assert_called_once()
    generate.assert_not_called()


def test_excel2inputs_reports_what_the_workbook_cannot_express(mocker, tmp_path):
    workbook = tmp_path / "Producer.xlsx"
    workbook.touch()
    mocker.patch(
        "dycov.cli.command_handlers.excel_generator.generate",
        side_effect=ValueError("'Z_cc_TP' is empty in sheet 'Zone3'"),
    )
    parser = MagicMock()

    handle_excel2inputs_command(parser, _excel2inputs_args(excel=str(workbook)))

    assert "Z_cc_TP" in parser.error.call_args.args[0]


def test_excel2inputs_reports_a_workbook_that_is_not_an_xlsx(mocker, tmp_path):
    workbook = tmp_path / "Producer.xlsx"
    workbook.touch()
    mocker.patch(
        "dycov.cli.command_handlers.excel_generator.generate",
        side_effect=zipfile.BadZipFile("not a zip"),
    )
    parser = MagicMock()

    handle_excel2inputs_command(parser, _excel2inputs_args(excel=str(workbook)))

    assert ".xlsx" in parser.error.call_args.args[0]


def test_validate_from_a_workbook_converts_and_validates_what_came_out(mocker, tmp_path):
    workbook = tmp_path / "Producer.xlsx"
    workbook.touch()
    run_verification = mocker.patch("dycov.cli.command_handlers._run_verification", return_value=0)
    generate = mocker.patch(
        "dycov.cli.command_handlers.excel_generator.generate", return_value="report"
    )
    mocker.patch(
        "dycov.cli.command_handlers.excel_generator.tests_without_metadata", return_value=[]
    )
    parser = MagicMock()

    result = handle_validate_command(parser, _validate_args(excel=str(workbook)), _LAUNCHER)

    assert result == 0
    kwargs = run_verification.call_args.kwargs
    generated = generate.call_args.args[1]
    assert kwargs["producer_model"] == generated / "Dynawo"
    assert kwargs["reference_curves"] == generated / "ReferenceCurves"
    assert kwargs["verification_type"] == MODEL_VALIDATION
    # The report names the workbook, not the directory that is about to disappear.
    assert kwargs["producer_workbook"] == workbook


def test_validate_from_a_workbook_leaves_no_temporary_directory(mocker, tmp_path):
    workbook = tmp_path / "Producer.xlsx"
    workbook.touch()
    generate = mocker.patch(
        "dycov.cli.command_handlers.excel_generator.generate", return_value="report"
    )
    mocker.patch(
        "dycov.cli.command_handlers.excel_generator.tests_without_metadata", return_value=[]
    )
    mocker.patch("dycov.cli.command_handlers._run_verification", return_value=0)
    parser = MagicMock()

    handle_validate_command(parser, _validate_args(excel=str(workbook)), _LAUNCHER)

    assert not generate.call_args.args[1].exists()


def test_validate_from_a_workbook_stops_when_the_metadata_is_blank(mocker, tmp_path):
    workbook = tmp_path / "Producer.xlsx"
    workbook.touch()
    mocker.patch("dycov.cli.command_handlers.excel_generator.generate", return_value="report")
    mocker.patch(
        "dycov.cli.command_handlers.excel_generator.tests_without_metadata",
        return_value=["PCS_RTE-I16z1.SetPointStep.Active"],
    )
    run_verification = mocker.patch("dycov.cli.command_handlers._run_verification")
    parser = MagicMock()

    handle_validate_command(parser, _validate_args(excel=str(workbook)), _LAUNCHER)

    assert "SetPointStep.Active" in parser.error.call_args.args[0]
    run_verification.assert_not_called()


def test_validate_from_a_workbook_refuses_reference_curves_as_well(mocker, tmp_path):
    workbook = tmp_path / "Producer.xlsx"
    workbook.touch()
    generate = mocker.patch("dycov.cli.command_handlers.excel_generator.generate")
    parser = MagicMock()

    handle_validate_command(
        parser, _validate_args(excel=str(workbook), reference="ReferenceCurves"), _LAUNCHER
    )

    parser.error.assert_called_once()
    generate.assert_not_called()
