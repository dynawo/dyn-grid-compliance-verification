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
from pathlib import Path

import pytest

import dycov
from dycov.configuration.cfg import (
    Config,
    _default_config_path,
    _new_parser,
    _user_config_path,
)

_PACKAGE_ROOT = Path(dycov.__file__).resolve().parent
_ZONE_1_DESCRIPTION = (
    _PACKAGE_ROOT / "templates" / "PCS" / "model" / "PPM" / "PCS_RTE-I16z1" / "PCSDescription.ini"
)
_ZONE_3_DESCRIPTION = (
    _PACKAGE_ROOT / "templates" / "PCS" / "model" / "PPM" / "PCS_RTE-I16z3" / "PCSDescription.ini"
)


@pytest.fixture
def empty_parsers():
    """The six configuration layers, in the order the Config constructor takes them."""
    return tuple(_new_parser() for _ in range(6))


@pytest.fixture
def config_with_priority(tmp_path):
    default_config = configparser.ConfigParser()
    user_config = configparser.ConfigParser()
    pcs_user_config = configparser.ConfigParser()
    pcs_dtr_delta_config = configparser.ConfigParser()
    pcs_config = configparser.ConfigParser()
    dtr_delta_config = configparser.ConfigParser()

    default_config.add_section("section")
    default_config.set("section", "key", "default_value")
    pcs_config.add_section("section")
    pcs_config.set("section", "key", "pcs_value")
    user_config.add_section("section")
    user_config.set("section", "key", "user_value")

    pcs_config.set("section", "pcs_only", "pcs_only_value")
    default_config.set("section", "default_only", "default_only_value")

    return Config(
        tmp_path,
        default_config,
        user_config,
        pcs_user_config,
        pcs_dtr_delta_config,
        pcs_config,
        dtr_delta_config,
    )


def test_get_value_priority_order(config_with_priority):
    # Should return user_config value
    assert config_with_priority.get_value("section", "key") == "user_value"
    # Should return pcs_config value if not in user_config
    assert config_with_priority.get_value("section", "pcs_only") == "pcs_only_value"
    # Should return default_config value if not in user_config or pcs_config
    assert config_with_priority.get_value("section", "default_only") == "default_only_value"


def test_load_pcs_config_updates_parser(tmp_path, empty_parsers):
    (
        default_config,
        user_config,
        pcs_user_config,
        pcs_dtr_delta_config,
        pcs_config,
        dtr_delta_config,
    ) = empty_parsers

    pcs_file = tmp_path / "pcs.ini"
    with pcs_file.open("w") as f:
        f.write("[pcs_section]\nfoo=bar\n")

    cfg = Config(tmp_path, *empty_parsers)
    assert not pcs_config.has_section("pcs_section")
    cfg.load_pcs_config(pcs_file)
    assert pcs_config.has_section("pcs_section")
    assert pcs_config.get("pcs_section", "foo") == "bar"


def test_get_list_returns_split_values(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    user_config.add_section("list_section")
    user_config.set("list_section", "mylist", "a,b,c")
    cfg = Config(tmp_path, *empty_parsers)
    assert cfg.get_list("list_section", "mylist") == ["a", "b", "c"]


def test_get_value_nonexistent_returns_none_or_default(tmp_path, empty_parsers):
    cfg = Config(tmp_path, *empty_parsers)
    # get_value returns None for missing key
    assert cfg.get_value("no_section", "no_key") is None
    # get_int returns default for missing key
    assert cfg.get_int("no_section", "no_key", 42) == 42
    # get_float returns default for missing key
    assert cfg.get_float("no_section", "no_key", 3.14) == 3.14
    # get_boolean returns default for missing key
    assert cfg.get_boolean("no_section", "no_key", True) is True


def test_get_int_float_with_invalid_value(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    user_config.add_section("bad_section")
    user_config.set("bad_section", "not_an_int", "abc")
    user_config.set("bad_section", "not_a_float", "xyz")
    cfg = Config(tmp_path, *empty_parsers)
    assert cfg.get_int("bad_section", "not_an_int", 0) == 0
    assert cfg.get_float("bad_section", "not_a_float", 0.0) == 0.0


def test_get_threshold_reads_the_limit_of_a_check(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    user_config.add_section("GridCode")
    user_config.set("GridCode", "thr_given", "2.5")
    user_config.set("GridCode", "thr_informative", "none")
    cfg = Config(tmp_path, *empty_parsers)

    assert cfg.get_threshold("GridCode", "thr_given", 5.0) == 2.5
    assert cfg.get_threshold("GridCode", "thr_informative", 5.0) is None
    assert cfg.get_threshold("GridCode", "thr_absent", 5.0) == 5.0


def test_find_option_prefers_the_first_suffix_the_section_defines(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    user_config.add_section("test_section")
    user_config.set("test_section", "u_fault", "0.05")
    user_config.set("test_section", "u_fault_D", "1e-3")
    user_config.set("test_section", "fault_duration_HTB1", "0.150")
    cfg = Config(tmp_path, *empty_parsers)

    assert cfg.find_option("test_section", "u_fault", "D", "HTB1") == "u_fault_D"
    assert cfg.find_option("test_section", "u_fault", "B", "HTB1") == "u_fault"
    assert cfg.find_option("test_section", "fault_duration", "D", "HTB1") == "fault_duration_HTB1"
    assert cfg.find_option("test_section", "u_clear", "D", "HTB3") is None


def test_get_options_gathers_the_keys_of_every_layer(tmp_path, empty_parsers):
    default_config, user_config, _, _, pcs_config, _ = empty_parsers
    user_config.add_section("opt_section")
    user_config.set("opt_section", "foo", "1")
    user_config.set("opt_section", "bar", "2")
    pcs_config.add_section("opt_section")
    pcs_config.set("opt_section", "foo", "3")
    pcs_config.set("opt_section", "baz", "3")
    default_config.add_section("opt_section")
    default_config.set("opt_section", "qux", "4")
    cfg = Config(tmp_path, *empty_parsers)

    options = cfg.get_options("opt_section")

    assert set(options) == {"foo", "bar", "baz", "qux"}
    assert options.count("foo") == 1
    assert cfg.get_value("opt_section", "foo") == "1"


def test_get_options_sees_the_keys_a_user_pcs_description_does_not_override(
    tmp_path, empty_parsers
):
    tool_file = tmp_path / "tool" / "PCSDescription.ini"
    tool_file.parent.mkdir()
    tool_file.write_text("[PCS.Model]\npdr_Q = 0.0\nu_10 = 0.9\n")
    user_file = tmp_path / "user" / "PCSDescription.ini"
    user_file.parent.mkdir()
    user_file.write_text("[PCS.Model]\npdr_Q = Qmin\n")
    cfg = Config(tmp_path, *empty_parsers)

    cfg.load_pcs_config(tool_file, user_file)

    assert set(cfg.get_options("PCS.Model")) == {"pdr_Q", "u_10"}


def test_get_list_empty_or_missing_returns_empty_list(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    user_config.add_section("empty_section")
    user_config.set("empty_section", "emptylist", "")
    cfg = Config(tmp_path, *empty_parsers)
    # Empty string returns empty list
    assert cfg.get_list("empty_section", "emptylist") == []
    # Missing key returns empty list
    assert cfg.get_list("empty_section", "missing") == []
    # Missing section returns empty list
    assert cfg.get_list("no_section", "no_key") == []


def test_user_config_path_does_not_depend_on_the_platform(tmp_path):
    assert _user_config_path(tmp_path) == tmp_path / "config.ini"


def test_describe_option_reports_user_config_file_and_line(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    user_file = tmp_path / "config.ini"
    user_file.write_text("[Global]\nfoo = 1\n\n[GridCode]\npdr_P = 0.5*Pmax\n")
    user_config.read(user_file)
    cfg = Config(tmp_path, *empty_parsers)

    description = cfg.describe_option("GridCode", "pdr_P")

    assert description == f"'pdr_P' in section [GridCode] of '{user_file}', line 5"


def test_describe_option_reports_pcs_file_and_line(tmp_path, empty_parsers):
    pcs_file = tmp_path / "PCSDescription.ini"
    pcs_file.write_text("[PCS.Model]\npdr_U = Udim\npdr_Q = 0.0\n")
    cfg = Config(tmp_path, *empty_parsers)
    cfg.load_pcs_config(pcs_file)

    description = cfg.describe_option("PCS.Model", "pdr_Q")

    assert description == f"'pdr_Q' in section [PCS.Model] of '{pcs_file}', line 3"


def test_describe_option_prefers_the_user_config_over_the_shipped_pcs_file(
    tmp_path, empty_parsers
):
    user_config = empty_parsers[1]
    user_file = tmp_path / "config.ini"
    user_file.write_text("[PCS.Model]\npdr_Q = 0.1\n")
    user_config.read(user_file)
    pcs_file = tmp_path / "PCSDescription.ini"
    pcs_file.write_text("[PCS.Model]\npdr_Q = 0.0\n")
    cfg = Config(tmp_path, *empty_parsers)
    cfg.load_pcs_config(pcs_file)

    description = cfg.describe_option("PCS.Model", "pdr_Q")

    assert str(user_file) in description
    assert str(pcs_file) not in description


def test_describe_option_names_the_user_pcs_file_over_the_shipped_one(tmp_path, empty_parsers):
    tool_file = tmp_path / "tool" / "PCSDescription.ini"
    tool_file.parent.mkdir()
    tool_file.write_text("[PCS.Model]\npdr_Q = 0.0\n")
    user_file = tmp_path / "user" / "PCSDescription.ini"
    user_file.parent.mkdir()
    user_file.write_text("[PCS.Model]\npdr_U = Udim\npdr_Q = 0.1\n")
    cfg = Config(tmp_path, *empty_parsers)
    cfg.load_pcs_config(tool_file, user_file)

    description = cfg.describe_option("PCS.Model", "pdr_Q")

    assert description == f"'pdr_Q' in section [PCS.Model] of '{user_file}', line 3"


def test_describe_option_ignores_the_same_key_in_another_section(tmp_path, empty_parsers):
    pcs_file = tmp_path / "PCSDescription.ini"
    pcs_file.write_text("[Other]\npdr_Q = 0.0\n\n[PCS.Model]\npdr_Q = 0.5\n")
    cfg = Config(tmp_path, *empty_parsers)
    cfg.load_pcs_config(pcs_file)

    description = cfg.describe_option("PCS.Model", "pdr_Q")

    assert description.endswith("line 5")


def test_describe_option_without_a_source_file_names_section_and_key(tmp_path, empty_parsers):
    cfg = Config(tmp_path, *empty_parsers)

    description = cfg.describe_option("PCS.Model", "pdr_Q")

    assert description == "'pdr_Q' in section [PCS.Model]"


def test_load_pcs_config_forgets_the_files_of_the_previous_pcs(tmp_path, empty_parsers):
    pcs_dir = tmp_path / "PCS" / "model"
    pcs_dir.mkdir(parents=True)
    (tmp_path / "PCS" / "PCS_aliases.ini").write_text(
        "[MyAlias]\ntest_key = alias_default_value\nalias_only = alias_value\n"
    )
    first_file = pcs_dir / "first_pcs.ini"
    first_file.write_text("[TestSection]\ntest_key = original_value\n")
    second_file = pcs_dir / "second_pcs.ini"
    second_file.write_text("[TestSection]\ninherit = MyAlias\n")
    cfg = Config(tmp_path, *empty_parsers)

    cfg.load_pcs_config(first_file)
    cfg.load_pcs_config(second_file)

    assert cfg.get_value("TestSection", "test_key") == "alias_default_value"
    assert cfg.get_value("TestSection", "alias_only") == "alias_value"


def test_load_pcs_config_forgets_the_user_file_of_the_previous_pcs(tmp_path, empty_parsers):
    tool_file = tmp_path / "tool" / "PCSDescription.ini"
    tool_file.parent.mkdir()
    tool_file.write_text("[TestSection]\ntest_key = tool_value\n")
    user_file = tmp_path / "user" / "PCSDescription.ini"
    user_file.parent.mkdir()
    user_file.write_text("[TestSection]\ntest_key = user_value\n")
    cfg = Config(tmp_path, *empty_parsers)

    cfg.load_pcs_config(tool_file, user_file)
    cfg.load_pcs_config(tool_file)

    assert cfg.get_value("TestSection", "test_key") == "tool_value"


def test_the_user_pcs_description_overrides_the_shipped_one(tmp_path, empty_parsers):
    tool_file = tmp_path / "tool" / "PCSDescription.ini"
    tool_file.parent.mkdir()
    tool_file.write_text("[TestSection]\ntest_key = tool_value\ntool_only = tool_value\n")
    user_file = tmp_path / "user" / "PCSDescription.ini"
    user_file.parent.mkdir()
    user_file.write_text("[TestSection]\ntest_key = user_value\n")
    cfg = Config(tmp_path, *empty_parsers)

    cfg.load_pcs_config(tool_file, user_file)

    assert cfg.get_value("TestSection", "test_key") == "user_value"
    assert cfg.get_value("TestSection", "tool_only") == "tool_value"


def test_the_user_pcs_description_overrides_the_user_config(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    user_config.read_string("[TestSection]\ntest_key = config_ini_value\n")
    user_file = tmp_path / "user" / "PCSDescription.ini"
    user_file.parent.mkdir()
    user_file.write_text("[TestSection]\ntest_key = user_pcs_value\n")
    cfg = Config(tmp_path, *empty_parsers)

    cfg.load_pcs_config(None, user_file)

    assert cfg.get_value("TestSection", "test_key") == "user_pcs_value"


def test_a_pcs_does_not_see_the_figures_of_the_previously_loaded_pcs(tmp_path, empty_parsers):
    default_config = empty_parsers[0]
    default_config.read(_default_config_path(), encoding="utf-8")
    cfg = Config(tmp_path, *empty_parsers)

    cfg.load_pcs_config(_ZONE_3_DESCRIPTION)
    zone_3_ustator = cfg.get_value("ReportCurves", "fig_Ustator")
    cfg.load_pcs_config(_ZONE_1_DESCRIPTION)
    zone_1_ustator = cfg.get_value("ReportCurves", "fig_Ustator")

    assert zone_3_ustator
    assert zone_1_ustator is None


def test_the_dtr_revision_overrides_the_shipped_pcs_description(tmp_path, empty_parsers):
    tool_file = tmp_path / "tool" / "PCSDescription.ini"
    tool_file.parent.mkdir()
    tool_file.write_text("[PCS.Model]\npdr_U = Udim\npdr_Q = 0.0\n")
    dtr_delta_file = tmp_path / "revision" / "PCSDescription.ini"
    dtr_delta_file.parent.mkdir()
    dtr_delta_file.write_text("[PCS.Model]\npdr_Q = 0.1\n")
    cfg = Config(tmp_path, *empty_parsers)

    cfg.load_pcs_config(tool_file, None, dtr_delta_file)

    assert cfg.get_value("PCS.Model", "pdr_Q") == "0.1"
    assert cfg.get_value("PCS.Model", "pdr_U") == "Udim"
    assert str(dtr_delta_file) in cfg.describe_option("PCS.Model", "pdr_Q")


def test_the_user_config_overrides_the_dtr_revision(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    user_config.read_string("[PCS.Model]\npdr_Q = 0.3\n")
    dtr_delta_file = tmp_path / "revision" / "PCSDescription.ini"
    dtr_delta_file.parent.mkdir()
    dtr_delta_file.write_text("[PCS.Model]\npdr_Q = 0.1\n")
    cfg = Config(tmp_path, *empty_parsers)

    cfg.load_pcs_config(None, None, dtr_delta_file)

    assert cfg.get_value("PCS.Model", "pdr_Q") == "0.3"


def test_set_value_overrides_a_dtr_revision_value_in_the_user_config(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    pcs_dtr_delta_config = empty_parsers[3]
    dtr_delta_file = tmp_path / "revision" / "PCSDescription.ini"
    dtr_delta_file.parent.mkdir()
    dtr_delta_file.write_text("[PCS.Model]\npdr_Q = 0.1\n")
    cfg = Config(tmp_path, *empty_parsers)
    cfg.load_pcs_config(None, None, dtr_delta_file)

    cfg.set_value("PCS.Model", "pdr_Q", "0.2")

    assert cfg.get_value("PCS.Model", "pdr_Q") == "0.2"
    assert user_config.get("PCS.Model", "pdr_Q") == "0.2"
    assert pcs_dtr_delta_config.get("PCS.Model", "pdr_Q") == "0.1"


def test_set_value_overrides_a_shipped_pcs_value_in_its_own_layer(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    tool_file = tmp_path / "tool" / "PCSDescription.ini"
    tool_file.parent.mkdir()
    tool_file.write_text("[PCS.Model]\npdr_Q = 0.0\n")
    cfg = Config(tmp_path, *empty_parsers)
    cfg.load_pcs_config(tool_file)

    cfg.set_value("PCS.Model", "pdr_Q", "0.2")

    assert cfg.get_value("PCS.Model", "pdr_Q") == "0.2"
    assert not user_config.has_option("PCS.Model", "pdr_Q")


def test_set_value_overrides_a_user_pcs_value_in_its_own_layer(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    pcs_user_config = empty_parsers[2]
    user_file = tmp_path / "user" / "PCSDescription.ini"
    user_file.parent.mkdir()
    user_file.write_text("[PCS.Model]\npdr_Q = 0.0\n")
    cfg = Config(tmp_path, *empty_parsers)
    cfg.load_pcs_config(None, user_file)

    cfg.set_value("PCS.Model", "pdr_Q", "0.2")

    assert pcs_user_config.get("PCS.Model", "pdr_Q") == "0.2"
    assert not user_config.has_option("PCS.Model", "pdr_Q")


def test_the_word_none_withdraws_a_list(tmp_path, empty_parsers):
    """An empty value lets the layer below answer; a revision writes "none" instead."""
    pcs_dtr_delta_config = empty_parsers[3]
    pcs_default_config = empty_parsers[4]
    pcs_default_config.add_section("PCS-Benchmarks")
    pcs_default_config.set("PCS-Benchmarks", "PCS_RTE-I5", "ThreePhaseFault")
    pcs_dtr_delta_config.add_section("PCS-Benchmarks")
    pcs_dtr_delta_config.set("PCS-Benchmarks", "PCS_RTE-I5", "none")
    cfg = Config(tmp_path, *empty_parsers)

    assert cfg.get_list("PCS-Benchmarks", "PCS_RTE-I5") == []


def test_an_empty_list_in_a_delta_leaves_the_shipped_one_answering(tmp_path, empty_parsers):
    pcs_dtr_delta_config = empty_parsers[3]
    pcs_default_config = empty_parsers[4]
    pcs_default_config.add_section("PCS-Benchmarks")
    pcs_default_config.set("PCS-Benchmarks", "PCS_RTE-I5", "ThreePhaseFault")
    pcs_dtr_delta_config.add_section("PCS-Benchmarks")
    pcs_dtr_delta_config.set("PCS-Benchmarks", "PCS_RTE-I5", "")
    cfg = Config(tmp_path, *empty_parsers)

    assert cfg.get_list("PCS-Benchmarks", "PCS_RTE-I5") == ["ThreePhaseFault"]


def test_a_threshold_of_the_norm_the_user_changed_is_named(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    default_config = empty_parsers[0]
    default_config.add_section("GridCode")
    default_config.set("GridCode", "thr_P_mxe_before", "0.05")
    user_config.add_section("GridCode")
    user_config.set("GridCode", "thr_P_mxe_before", "0.5")
    cfg = Config(tmp_path, *empty_parsers)

    assert cfg.overridden_norm_options() == [("GridCode", "thr_P_mxe_before")]


def test_a_value_of_a_pcs_the_user_changed_is_named(tmp_path, empty_parsers):
    pcs_user_config = empty_parsers[2]
    pcs_default_config = empty_parsers[4]
    pcs_default_config.add_section("PCS_RTE-I6.GridVoltageDip.Qzero.Model")
    pcs_default_config.set("PCS_RTE-I6.GridVoltageDip.Qzero.Model", "u_fault", "0.05")
    pcs_user_config.add_section("PCS_RTE-I6.GridVoltageDip.Qzero.Model")
    pcs_user_config.set("PCS_RTE-I6.GridVoltageDip.Qzero.Model", "u_fault", "0.2")
    cfg = Config(tmp_path, *empty_parsers)

    assert cfg.overridden_norm_options() == [("PCS_RTE-I6.GridVoltageDip.Qzero.Model", "u_fault")]


def test_how_the_tool_runs_is_not_a_criterion_of_the_norm(tmp_path, empty_parsers):
    """A log level or a solver setting is the user's business, and marks no verdict."""
    default_config = empty_parsers[0]
    user_config = empty_parsers[1]
    for section, key, value in (
        ("Global", "console_log_level", "20"),
        ("Dynawo", "simulation_limit", "30"),
    ):
        default_config.add_section(section)
        default_config.set(section, key, value)
        user_config.add_section(section)
        user_config.set(section, key, "99")
    cfg = Config(tmp_path, *empty_parsers)

    assert cfg.overridden_norm_options() == []


def test_an_option_only_the_user_defines_overrides_nothing(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    user_config.add_section("GridCode")
    user_config.set("GridCode", "thr_of_its_own", "1.0")
    cfg = Config(tmp_path, *empty_parsers)

    assert cfg.overridden_norm_options() == []


def test_an_option_the_delta_of_the_revision_fixes_is_of_the_norm(tmp_path, empty_parsers):
    user_config = empty_parsers[1]
    dtr_delta_config = empty_parsers[5]
    dtr_delta_config.add_section("GridCode")
    dtr_delta_config.set("GridCode", "category_thresholds_high_voltage", "1,18,30")
    user_config.add_section("GridCode")
    user_config.set("GridCode", "category_thresholds_high_voltage", "1,18,99")
    cfg = Config(tmp_path, *empty_parsers)

    assert cfg.overridden_norm_options() == [("GridCode", "category_thresholds_high_voltage")]
