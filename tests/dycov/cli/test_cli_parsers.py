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


def test_print_completion_writes_the_script_and_exits(parser, capsys):
    with pytest.raises(SystemExit) as exit_info:
        parser.parse_args(["--print-completion", "bash"])

    assert exit_info.value.code == 0
    assert "complete -F _shtab_dycov dycov" in capsys.readouterr().out
