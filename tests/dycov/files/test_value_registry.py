#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the registry of base magnitudes and the value-definition resolver."""

from types import SimpleNamespace

import pytest

from dycov.files import value_registry


def test_extract_defined_value_with_placeholders():
    assert value_registry.extract_defined_value("2*b", "b", 0.2) == pytest.approx(0.4)
    assert value_registry.extract_defined_value("pmax", "pmax", 90) == pytest.approx(90)
    assert value_registry.extract_defined_value("3*pmax", "pmax", 10) == pytest.approx(30)


def test_extract_defined_value_numeric():
    val = value_registry.extract_defined_value("2.5", "p", 1)

    assert val == pytest.approx(2.5)


def test_extract_defined_value_errors():
    for invalid in (None, "", "abc", "2*x"):
        with pytest.raises(ValueError):
            value_registry.extract_defined_value(invalid, "p", 1)


def _producer(p_max_pu=0.8, q_max_pu=0.5, q_min_pu=-0.5, s_nom_pu=1.8, u_nom=20.0):
    return SimpleNamespace(
        p_max_pu=p_max_pu,
        q_max_pu=q_max_pu,
        q_min_pu=q_min_pu,
        s_nom_pu=s_nom_pu,
        u_nom=u_nom,
    )


_OPTION_LOCATION = "'pdr_P' in section [PCS.Model] of '/etc/PCSDescription.ini', line 7"


def _config_stub():
    return SimpleNamespace(describe_option=lambda section, key: _OPTION_LOCATION)


def test_unit_characteristics_exposes_power_and_voltage_bases():
    chars = value_registry.unit_characteristics(_producer(), u_dim=21.0, line_Xpu=0.05)

    assert chars["Pmax"] == pytest.approx(0.8)
    assert chars["Snom"] == pytest.approx(1.8)
    assert chars["Qmax"] == pytest.approx(0.5)
    assert chars["Qmin"] == pytest.approx(-0.5)
    assert chars["Udim"] == pytest.approx(21.0 / 20.0)
    assert chars["Unom"] == pytest.approx(1.0)
    assert chars["line_XPu"] == pytest.approx(0.05)


def test_unit_characteristics_pmax_aliases_track_active_mode():
    chars = value_registry.unit_characteristics(_producer(p_max_pu=-0.3), u_dim=20.0)

    assert chars["PmaxInjection"] == pytest.approx(-0.3)
    assert chars["PmaxConsumption"] == pytest.approx(-0.3)


def test_resolve_value_definition_numeric():
    chars = value_registry.unit_characteristics(_producer(), u_dim=20.0)

    assert value_registry.resolve_value_definition("1.25", chars) == pytest.approx(1.25)
    assert value_registry.resolve_value_definition("-0.5", chars) == pytest.approx(-0.5)
    assert value_registry.resolve_value_definition(".75", chars) == pytest.approx(0.75)


def test_resolve_value_definition_named_and_multiplier():
    chars = value_registry.unit_characteristics(_producer(s_nom_pu=1.8), u_dim=20.0)

    assert value_registry.resolve_value_definition("Snom", chars) == pytest.approx(1.8)
    assert value_registry.resolve_value_definition("0.5*Snom", chars) == pytest.approx(0.9)
    assert value_registry.resolve_value_definition("-Snom", chars) == pytest.approx(-1.8)


def test_resolve_value_definition_applies_final_sign():
    chars = value_registry.unit_characteristics(_producer(s_nom_pu=1.8), u_dim=20.0)

    value = value_registry.resolve_value_definition("0.5*Snom", chars, sign=-1)

    assert value == pytest.approx(-0.9)


def test_resolve_value_definition_unknown_name_raises():
    chars = value_registry.unit_characteristics(_producer(), u_dim=20.0)

    with pytest.raises(ValueError):
        value_registry.resolve_value_definition("0.5*Foobar", chars)


def test_resolve_value_definition_invalid_forms_raise():
    chars = value_registry.unit_characteristics(_producer(), u_dim=20.0)

    for invalid in (None, "", "  ", "-", "2*", "*Snom", "2*3", "Snom*2", "Snom+Unom"):
        with pytest.raises(ValueError):
            value_registry.resolve_value_definition(invalid, chars)


def test_resolve_value_definition_unknown_name_lists_the_available_magnitudes():
    chars = value_registry.unit_characteristics(_producer(), u_dim=20.0)

    with pytest.raises(ValueError) as error:
        value_registry.resolve_value_definition("0.5*snom", chars)

    message = str(error.value)
    assert "Unknown magnitude 'snom'" in message
    assert "case-sensitive" in message
    assert "Defined by" not in message
    for magnitude in chars:
        assert magnitude in message


def test_resolve_value_definition_errors_point_to_the_configuration_option(monkeypatch):
    monkeypatch.setattr(value_registry, "config", _config_stub())
    chars = value_registry.unit_characteristics(_producer(), u_dim=20.0)

    for invalid in (None, "0.5*Foobar", "Snom*2"):
        with pytest.raises(ValueError) as error:
            value_registry.resolve_value_definition(invalid, chars, origin=("PCS.Model", "pdr_P"))

        assert _OPTION_LOCATION in str(error.value)
