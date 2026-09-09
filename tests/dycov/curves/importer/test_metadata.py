#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#
"""Reading of the `[Curves-Metadata]` section of a curves dictionary."""

import configparser
from pathlib import Path

import pytest

from dycov.curves.importer.metadata import SECTION, CurvesMetadata

_DICT_NAME = "PCSX.Bm.Oc.dict"

_FILLED_METADATA = (
    "[Curves-Metadata]\n"
    "is_field_measurements = True\n"
    "sim_t_event_start = 20.0\n"
    "fault_duration = 0.15\n"
    "frequency_sampling = 15\n"
    "Wind_Turbine_GEN_MaxInjectedCurrentPu = 1.3\n"
)

_UNFILLED_METADATA = (
    "[Curves-Metadata]\n"
    "is_field_measurements =\n"
    "sim_t_event_start =\n"
    "fault_duration =\n"
    "frequency_sampling =\n"
    "Wind_Turbine_GEN_MaxInjectedCurrentPu =\n"
)

_METADATA_WITH_PLACEHOLDERS = (
    "[Curves-Metadata]\n"
    "is_field_measurements =\n"
    "sim_t_event_start =\n"
    "\n"
    "[Curves-Dictionary]\n"
    "[WT_ID]_GEN_IpInjTerminal =\n"
    "[WT_ID]_GEN_IqInjTerminal =\n"
)


def _make_metadata(tmp_path: Path, content: str) -> CurvesMetadata:
    dict_file = tmp_path / _DICT_NAME
    dict_file.write_text(content)
    return CurvesMetadata.from_dict_file(dict_file)


# ---------------------------------------------------------------------------
# Declared, absent and unfilled options
# ---------------------------------------------------------------------------


def test_get_float_declared_option_returns_its_value(tmp_path):
    metadata = _make_metadata(tmp_path, _FILLED_METADATA)

    value = metadata.get_float("sim_t_event_start")

    assert value == pytest.approx(20.0)


def test_get_float_absent_option_returns_the_default(tmp_path):
    metadata = _make_metadata(tmp_path, "[Curves-Metadata]\nfrequency_sampling = 15\n")

    value = metadata.get_float("fault_duration", 0.85)

    assert value == pytest.approx(0.85)


def test_get_float_unfilled_option_names_the_dictionary_and_the_option(tmp_path):
    """Guards against issue #481: an unfilled option must not fail as float('')."""
    metadata = _make_metadata(tmp_path, _UNFILLED_METADATA)

    with pytest.raises(ValueError) as unfilled_error:
        metadata.get_float("sim_t_event_start")

    assert "sim_t_event_start" in str(unfilled_error.value)
    assert _DICT_NAME in str(unfilled_error.value)
    assert SECTION in str(unfilled_error.value)


def test_get_boolean_declared_option_returns_its_value(tmp_path):
    metadata = _make_metadata(tmp_path, _FILLED_METADATA)

    value = metadata.get_boolean("is_field_measurements")

    assert value is True


def test_get_boolean_absent_option_returns_the_default(tmp_path):
    metadata = _make_metadata(tmp_path, "[Curves-Metadata]\nsim_t_event_start = 20.0\n")

    value = metadata.get_boolean("is_field_measurements", True)

    assert value is True


def test_get_boolean_unfilled_option_names_the_dictionary_and_the_option(tmp_path):
    """Guards against issue #481: an unfilled flag must not silently become False."""
    metadata = _make_metadata(tmp_path, _UNFILLED_METADATA)

    with pytest.raises(ValueError) as unfilled_error:
        metadata.get_boolean("is_field_measurements")

    assert "is_field_measurements" in str(unfilled_error.value)
    assert _DICT_NAME in str(unfilled_error.value)


# ---------------------------------------------------------------------------
# Maximum injected current by generator
# ---------------------------------------------------------------------------


def test_get_generators_imax_returns_the_current_of_each_generator(tmp_path):
    metadata = _make_metadata(tmp_path, _FILLED_METADATA)

    generators_imax = metadata.get_generators_imax()

    assert generators_imax == {"Wind_Turbine": pytest.approx(1.3)}


def test_get_generators_imax_unfilled_option_names_the_dictionary_and_the_option(tmp_path):
    metadata = _make_metadata(tmp_path, _UNFILLED_METADATA)

    with pytest.raises(ValueError) as unfilled_error:
        metadata.get_generators_imax()

    assert "Wind_Turbine_GEN_MaxInjectedCurrentPu" in str(unfilled_error.value)
    assert _DICT_NAME in str(unfilled_error.value)


def test_get_generators_imax_without_metadata_section_raises_key_error(tmp_path):
    metadata = _make_metadata(tmp_path, "[Curves-Dictionary]\ntime = time\n")

    with pytest.raises(KeyError):
        metadata.get_generators_imax()


# ---------------------------------------------------------------------------
# Mandatory options left without a value
# ---------------------------------------------------------------------------


def test_get_unfilled_options_reports_every_mandatory_option(tmp_path):
    metadata = _make_metadata(tmp_path, _UNFILLED_METADATA)

    unfilled_options = metadata.get_unfilled_options()

    assert unfilled_options == [
        "is_field_measurements",
        "sim_t_event_start",
        "fault_duration",
        "Wind_Turbine_GEN_MaxInjectedCurrentPu",
    ]


def test_get_unfilled_options_ignores_the_sampling_frequency(tmp_path):
    """The sampling frequency of a CSV file is not read from the dictionary."""
    metadata = _make_metadata(tmp_path, _UNFILLED_METADATA)

    unfilled_options = metadata.get_unfilled_options()

    assert "frequency_sampling" not in unfilled_options


def test_get_unfilled_options_of_a_filled_dictionary_is_empty(tmp_path):
    metadata = _make_metadata(tmp_path, _FILLED_METADATA)

    unfilled_options = metadata.get_unfilled_options()

    assert unfilled_options == []


def test_get_unfilled_options_without_metadata_section_is_empty(tmp_path):
    metadata = _make_metadata(tmp_path, "[Curves-Dictionary]\ntime = time\n")

    unfilled_options = metadata.get_unfilled_options()

    assert unfilled_options == []


# ---------------------------------------------------------------------------
# Reading a dictionary from disk
# ---------------------------------------------------------------------------


def test_from_dict_file_reads_metadata_of_a_dictionary_with_placeholders(tmp_path):
    """A generated dictionary keeps its `[WT_ID]` placeholders, read as repeated sections."""
    metadata = _make_metadata(tmp_path, _METADATA_WITH_PLACEHOLDERS)

    unfilled_options = metadata.get_unfilled_options()

    assert unfilled_options == ["is_field_measurements", "sim_t_event_start"]


def test_from_dict_file_of_a_file_without_sections_raises_a_config_error(tmp_path):
    dict_file = tmp_path / _DICT_NAME
    dict_file.write_text("sim_t_event_start = 20.0\n")

    with pytest.raises(configparser.Error):
        CurvesMetadata.from_dict_file(dict_file)
