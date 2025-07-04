#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import configparser

import pytest

from dycov.configuration.cfg import Config


@pytest.fixture
def config_with_priority(tmp_path):
    # Create three config parsers with different priorities
    default_config = configparser.ConfigParser()
    user_config = configparser.ConfigParser()
    pcs_config = configparser.ConfigParser()

    # Add sections and keys
    default_config.add_section("section")
    default_config.set("section", "key", "default_value")
    pcs_config.add_section("section")
    pcs_config.set("section", "key", "pcs_value")
    user_config.add_section("section")
    user_config.set("section", "key", "user_value")

    # Add a key only in pcs_config
    pcs_config.set("section", "pcs_only", "pcs_only_value")
    # Add a key only in default_config
    default_config.set("section", "default_only", "default_only_value")

    return Config(tmp_path, default_config, user_config, pcs_config)


def test_get_value_priority_order(config_with_priority):
    # Should return user_config value
    assert config_with_priority.get_value("section", "key") == "user_value"
    # Should return pcs_config value if not in user_config
    assert config_with_priority.get_value("section", "pcs_only") == "pcs_only_value"
    # Should return default_config value if not in user_config or pcs_config
    assert config_with_priority.get_value("section", "default_only") == "default_only_value"


def test_load_pcs_config_updates_parser(tmp_path):
    pcs_config = configparser.ConfigParser()
    user_config = configparser.ConfigParser()
    default_config = configparser.ConfigParser()
    config_dir = tmp_path

    # Write a pcs config file
    pcs_file = tmp_path / "pcs.ini"
    with pcs_file.open("w") as f:
        f.write("[pcs_section]\nfoo=bar\n")

    cfg = Config(config_dir, default_config, user_config, pcs_config)
    assert not pcs_config.has_section("pcs_section")
    cfg.load_pcs_config(pcs_file)
    assert pcs_config.has_section("pcs_section")
    assert pcs_config.get("pcs_section", "foo") == "bar"


def test_get_list_returns_split_values(tmp_path):
    default_config = configparser.ConfigParser()
    user_config = configparser.ConfigParser()
    pcs_config = configparser.ConfigParser()
    user_config.add_section("list_section")
    user_config.set("list_section", "mylist", "a,b,c")
    cfg = Config(tmp_path, default_config, user_config, pcs_config)
    assert cfg.get_list("list_section", "mylist") == ["a", "b", "c"]


def test_get_value_nonexistent_returns_none_or_default(tmp_path):
    default_config = configparser.ConfigParser()
    user_config = configparser.ConfigParser()
    pcs_config = configparser.ConfigParser()
    cfg = Config(tmp_path, default_config, user_config, pcs_config)
    # get_value returns None for missing key
    assert cfg.get_value("no_section", "no_key") is None
    # get_int returns default for missing key
    assert cfg.get_int("no_section", "no_key", 42) == 42
    # get_float returns default for missing key
    assert cfg.get_float("no_section", "no_key", 3.14) == 3.14
    # get_boolean returns default for missing key
    assert cfg.get_boolean("no_section", "no_key", True) is True


def test_get_int_float_with_invalid_value(tmp_path):
    default_config = configparser.ConfigParser()
    user_config = configparser.ConfigParser()
    pcs_config = configparser.ConfigParser()
    user_config.add_section("bad_section")
    user_config.set("bad_section", "not_an_int", "abc")
    user_config.set("bad_section", "not_a_float", "xyz")
    cfg = Config(tmp_path, default_config, user_config, pcs_config)
    assert cfg.get_int("bad_section", "not_an_int", 0) == 0
    assert cfg.get_float("bad_section", "not_a_float", 0.0) == 0.0


def test_get_options_returns_keys_with_priority(tmp_path):
    default_config = configparser.ConfigParser()
    user_config = configparser.ConfigParser()
    pcs_config = configparser.ConfigParser()
    # Only user_config has the section
    user_config.add_section("opt_section")
    user_config.set("opt_section", "foo", "1")
    user_config.set("opt_section", "bar", "2")
    # pcs_config has the section, but should not be used
    pcs_config.add_section("opt_section")
    pcs_config.set("opt_section", "baz", "3")
    # default_config has the section, but should not be used
    default_config.add_section("opt_section")
    default_config.set("opt_section", "qux", "4")
    cfg = Config(tmp_path, default_config, user_config, pcs_config)
    options = cfg.get_options("opt_section")
    assert set(options) == {"foo", "bar"}


def test_get_list_empty_or_missing_returns_empty_list(tmp_path):
    default_config = configparser.ConfigParser()
    user_config = configparser.ConfigParser()
    pcs_config = configparser.ConfigParser()
    user_config.add_section("empty_section")
    user_config.set("empty_section", "emptylist", "")
    cfg = Config(tmp_path, default_config, user_config, pcs_config)
    # Empty string returns empty list
    assert cfg.get_list("empty_section", "emptylist") == []
    # Missing key returns empty list
    assert cfg.get_list("empty_section", "missing") == []
    # Missing section returns empty list
    assert cfg.get_list("no_section", "no_key") == []
