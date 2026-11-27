#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import argparse
import re
from pathlib import Path

import pytest
import shtab

from dycov.cli.cli_parsers import setup_cli_parsers


def _commands(parser: argparse.ArgumentParser) -> dict:
    subparsers = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    return subparsers.choices


def _action(parser: argparse.ArgumentParser, command: str, option: str) -> argparse.Action:
    return next(
        action for action in _commands(parser)[command]._actions if option in action.option_strings
    )


@pytest.fixture
def parser():
    return setup_cli_parsers()


def test_completion_script_covers_every_command(parser):
    script = shtab.complete(parser, "bash")

    for command in _commands(parser):
        assert command in script


@pytest.mark.parametrize(
    "command, option, completion",
    [
        ("validate", "--model", shtab.DIRECTORY),
        ("validate", "--curves", shtab.DIRECTORY),
        ("validate", "--excel", shtab.FILE),
        ("validate", "--output", shtab.DIRECTORY),
        ("performance", "--launcher", shtab.FILE),
        ("generate_gfm_envelopes", "--producer_ini", shtab.FILE),
        ("anonymize", "--results", shtab.DIRECTORY),
    ],
)
def test_path_arguments_complete_paths(parser, command, option, completion):
    assert _action(parser, command, option).complete == completion


def test_positional_arguments_complete_paths(parser):
    reference = next(
        action for action in _commands(parser)["validate"]._actions if action.dest == "reference"
    )
    excel = next(
        action for action in _commands(parser)["excel2inputs"]._actions if action.dest == "excel"
    )

    assert reference.complete == shtab.DIRECTORY
    assert excel.complete == shtab.FILE


@pytest.mark.parametrize(
    "arguments",
    [
        ["validate", "-m", "Dynawo", "ReferenceCurves"],
        ["performance", "-m", "Dynawo"],
    ],
)
def test_curves_only_is_off_unless_asked_for(parser, arguments):
    assert parser.parse_args(arguments).curves_only is False
    assert parser.parse_args([*arguments, "--curves-only"]).curves_only is True


_COMMANDS = [
    ["validate", "-e", "Producer.xlsx"],
    ["performance", "-m", "Model"],
    ["excel2inputs", "Producer.xlsx"],
    ["anonymize", "-c", "curves", "-o", "out"],
    ["generate_gfm_envelopes", "-i", "Producer.ini"],
    ["migrate_inputs", "inputs"],
]


@pytest.mark.parametrize("command", _COMMANDS, ids=lambda command: command[0])
@pytest.mark.parametrize("after_the_command", [False, True], ids=["before", "after"])
def test_the_global_options_go_before_or_after_the_command(parser, command, after_the_command):
    """#854: after the command, --user-config, and --debug and --diagnostic too, were refused."""
    options = ["--user-config", "user.ini", "--debug", "--diagnostic"]
    arguments = [*command, *options] if after_the_command else [*options, *command]

    args = parser.parse_args(arguments)

    assert args.user_config == Path("user.ini")
    assert args.debug is True
    assert args.diagnostic is True


@pytest.mark.parametrize("command", _COMMANDS, ids=lambda command: command[0])
def test_a_global_option_left_out_after_the_command_keeps_its_value(parser, command):
    args = parser.parse_args(["--user-config", "user.ini", "-d", *command])

    assert args.user_config == Path("user.ini")
    assert args.debug is True
    assert args.diagnostic is False
    assert parser.parse_args(command).user_config is None


@pytest.mark.parametrize(
    "arguments",
    [
        ["anonymize", "-c", "curves", "-o", "out", "-dr3"],
        ["validate", "-e", "Producer.xlsx", "-dod"],
        ["validate", "-e", "Producer.xlsx", "-d"],
    ],
)
def test_a_short_debug_after_the_command_reads_no_glued_letters(parser, arguments):
    """Only the long names follow the command: a -d there would read -dr3 as -d -r 3."""
    with pytest.raises(SystemExit):
        parser.parse_args(arguments)


def test_anonymize_asks_for_its_output_directory(parser, capsys):
    """#836: the curves are written there, and read from there without --curves."""
    with pytest.raises(SystemExit):
        parser.parse_args(["anonymize"])

    assert "the following arguments are required: -o/--output" in capsys.readouterr().err


def test_print_completion_writes_the_script_and_exits(parser, capsys):
    with pytest.raises(SystemExit) as exit_info:
        parser.parse_args(["--print-completion", "bash"])

    assert exit_info.value.code == 0
    script = capsys.readouterr().out
    assert re.search(r"^complete (-o \S+ )*-F _shtab_dycov dycov$", script, re.MULTILINE)


def test_the_revision_of_the_dtr_is_no_option_of_the_command_line(parser):
    """#753: the configuration declares it, where the files of a run keep it."""
    with pytest.raises(SystemExit):
        parser.parse_args(["--dtr", "20240215", "performance"])
