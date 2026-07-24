#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the effective configuration / PCS description dump helpers."""

import configparser

import pytest

from dycov.configuration.dump import (
    _get_effective_value_with_source,
    dump_effective_config,
    dump_effective_pcs_description,
)


class DummyCfg:
    """Minimal stand-in for Config exposing the three layered parsers.

    Each layer is given as a ``{(section, key): value}`` mapping.
    """

    def __init__(self, user=None, pcs=None, default=None):
        self._user_config = self._build_parser(user)
        self._pcs_config = self._build_parser(pcs)
        self._default_config = self._build_parser(default)

    @staticmethod
    def _build_parser(values):
        parser = configparser.ConfigParser()
        for (section, key), value in (values or {}).items():
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section, key, value)
        return parser

    def _is_valid_value(self, value):
        return True


@pytest.fixture
def debug_logs(monkeypatch):
    """Capture every logger.debug() message emitted by the dump module."""
    logs = []

    class DummyLogger:
        def debug(self, msg, *args):
            logs.append(msg % args if args else msg)

    monkeypatch.setattr(
        "dycov.configuration.dump.dycov_logging.get_logger",
        lambda name: DummyLogger(),
    )
    return logs


def test_get_effective_value_prefers_user():
    cfg = DummyCfg(
        user={("A", "k"): "user_val"},
        pcs={("A", "k"): "pcs_val"},
        default={("A", "k"): "default_val"},
    )

    val, src = _get_effective_value_with_source(cfg, "A", "k")

    assert val == "user_val"
    assert src == "user"


def test_get_effective_value_fallback_to_pcs():
    cfg = DummyCfg(pcs={("A", "k"): "pcs_val"})

    val, src = _get_effective_value_with_source(cfg, "A", "k")

    assert val == "pcs_val"
    assert src == "pcs"


def test_dump_effective_config_no_non_default(debug_logs):
    dump_effective_config(DummyCfg())

    assert any("No non-default" in log for log in debug_logs)


def test_dump_effective_pcs_description(debug_logs):
    cfg = DummyCfg(pcs={("PCS", "a"): "1"})

    dump_effective_pcs_description(cfg, "PCS")

    assert any("PCS       : PCS" in log for log in debug_logs)


def test_dump_effective_pcs_description_nested(debug_logs):
    cfg = DummyCfg(pcs={("PCS.BM.OC", "x"): "1"})

    dump_effective_pcs_description(cfg, "PCS", "BM", "OC")

    assert any("PCS.BM.OC" in log for log in debug_logs)
