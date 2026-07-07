#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#


def test_get_effective_value_with_source():
    from dycov.configuration.dump import _get_effective_value_with_source

    class DummyCfg:
        def __init__(self):
            import configparser

            self._user_config = configparser.ConfigParser()
            self._pcs_config = configparser.ConfigParser()
            self._default_config = configparser.ConfigParser()

            self._user_config.add_section("A")
            self._user_config.set("A", "k", "user_val")

            self._pcs_config.add_section("A")
            self._pcs_config.set("A", "k", "pcs_val")

            self._default_config.add_section("A")
            self._default_config.set("A", "k", "default_val")

        def _is_valid_value(self, v):
            return True

    cfg = DummyCfg()

    val, src = _get_effective_value_with_source(cfg, "A", "k")

    assert val == "user_val"
    assert src == "user"


def test_get_effective_value_fallback_to_pcs():
    from dycov.configuration.dump import _get_effective_value_with_source

    class DummyCfg:
        def __init__(self):
            import configparser
            self._user_config = configparser.ConfigParser()
            self._pcs_config = configparser.ConfigParser()
            self._default_config = configparser.ConfigParser()

            self._pcs_config.add_section("A")
            self._pcs_config.set("A", "k", "pcs_val")

        def _is_valid_value(self, v):
            return True

    val, src = _get_effective_value_with_source(DummyCfg(), "A", "k")

    assert src == "pcs"


def test_get_effective_value_fallback_to_pcs():
    from dycov.configuration.dump import _get_effective_value_with_source

    class DummyCfg:
        def __init__(self):
            import configparser
            self._user_config = configparser.ConfigParser()
            self._pcs_config = configparser.ConfigParser()
            self._default_config = configparser.ConfigParser()

            self._pcs_config.add_section("A")
            self._pcs_config.set("A", "k", "pcs_val")

        def _is_valid_value(self, v):
            return True

    val, src = _get_effective_value_with_source(DummyCfg(), "A", "k")

    assert src == "pcs"


def test_dump_effective_config_no_non_default(monkeypatch):
    from dycov.configuration.dump import dump_effective_config

    logs = []

    class DummyLogger:
        def debug(self, msg, *args):
            logs.append(msg)

    class DummyCfg:
        def __init__(self):
            import configparser
            self._user_config = configparser.ConfigParser()
            self._pcs_config = configparser.ConfigParser()
            self._default_config = configparser.ConfigParser()

        def _is_valid_value(self, v):
            return True

    monkeypatch.setattr(
        "dycov.configuration.dump.dycov_logging.get_logger",
        lambda name: DummyLogger(),
    )

    dump_effective_config(DummyCfg())

    assert any("No non-default" in log for log in logs)


def test_dump_effective_pcs_description(monkeypatch):
    from dycov.configuration.dump import dump_effective_pcs_description

    logs = []

    class DummyLogger:
        def debug(self, msg, *args):
            logs.append(msg % args if args else msg)

    class DummyCfg:
        def __init__(self):
            import configparser
            self._pcs_config = configparser.ConfigParser()
            self._pcs_config.add_section("PCS")
            self._pcs_config.set("PCS", "a", "1")

    monkeypatch.setattr(
        "dycov.configuration.dump.dycov_logging.get_logger",
        lambda name: DummyLogger(),
    )

    dump_effective_pcs_description(DummyCfg(), "PCS")

    assert any("PCS       : PCS" in log for log in logs)


def test_dump_effective_pcs_description_nested(monkeypatch):
    from dycov.configuration.dump import dump_effective_pcs_description

    logs = []

    class DummyLogger:
        def debug(self, msg, *args):
            logs.append(msg % args if args else msg)

    class DummyCfg:
        def __init__(self):
            import configparser
            self._pcs_config = configparser.ConfigParser()
            self._pcs_config.add_section("PCS.BM.OC")
            self._pcs_config.set("PCS.BM.OC", "x", "1")

    monkeypatch.setattr(
        "dycov.configuration.dump.dycov_logging.get_logger",
        lambda name: DummyLogger(),
    )

    dump_effective_pcs_description(DummyCfg(), "PCS", "BM", "OC")

    assert any("PCS.BM.OC" in log for log in logs)
