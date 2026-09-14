#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

"""Tests for the names file: the package copy, the user's own, and what happens between them."""

from __future__ import annotations

import pytest

from dycov.excel import names


@pytest.fixture
def user_dictionary(tmp_path, monkeypatch):
    """A user copy of the names file, with the cache cleared around it."""
    path = tmp_path / names.NAMES_FILENAME
    monkeypatch.setattr(names, "user_names_file", lambda: path)
    names._parsed.cache_clear()
    yield path
    names._parsed.cache_clear()


def test_without_a_user_copy_the_names_are_the_ones_shipped(user_dictionary):
    assert not user_dictionary.exists()

    assert names.sheet("zone1") == "Zone1a"


def test_a_user_copy_overrides_one_name_and_leaves_the_rest(user_dictionary):
    user_dictionary.write_text("[Sheets]\nzone1 = HojaZona1\n", encoding="utf-8")

    assert names.sheet("zone1") == "HojaZona1"
    assert names.sheet("zone3") == "Zone3"  # untouched: it still comes from the package


def test_a_name_the_tool_no_longer_reads_is_reported(user_dictionary, caplog):
    user_dictionary.write_text("[Sheets]\nzone9 = HojaZona9\n", encoding="utf-8")

    names.sheet("zone1")

    assert "zone9" in caplog.text


def test_a_whole_section_the_tool_no_longer_reads_is_reported(user_dictionary, caplog):
    user_dictionary.write_text("[Feuilles]\nzone1 = HojaZona1\n", encoding="utf-8")

    names.sheet("zone1")

    assert "Feuilles" in caplog.text


def test_a_curve_the_user_adds_is_not_reported_as_unknown(user_dictionary, caplog):
    # The curve and test sections hold the user's own rows, so a key the package does not
    # ship is a legitimate addition, not a name gone stale.
    user_dictionary.write_text(
        "[Zone1-Curves]\nUne nouvelle grandeur = InternalNode1_BUS_Voltage\n", encoding="utf-8"
    )

    mapped = names.curves("Zone1", "Wind_Turbine")

    assert mapped["une nouvelle grandeur"] == "InternalNode1_BUS_Voltage"
    assert "nouvelle" not in caplog.text


def test_a_name_the_generator_needs_says_where_to_define_it(user_dictionary):
    with pytest.raises(ValueError, match=names.NAMES_FILENAME):
        names.sheet("there_is_no_such_sheet")
