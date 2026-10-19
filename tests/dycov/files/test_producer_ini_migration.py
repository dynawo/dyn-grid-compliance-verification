#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the migration of a producer's INI files to the current magnitude names."""

from pathlib import Path

import pytest

from dycov.files.producer_ini_migration import migrate

_LEGACY_INI = """[DEFAULT]
# p_{max_unite} injection as defined by the DTR in MW
p_max_injection_at_PDR = 75
# p_{min_unite} injection in MW (optional, 0 when absent)
# p_min_injection_at_PDR =
# u_nom is the nominal voltage at the PDR bus (in kV)
u_nom_at_PDR = 225
# q_max is the maximum reactive power at the PDR bus (in MVar)
q_max_at_PDR = 40
# q_min is the minimum reactive power at the PDR bus (in MVar)
q_min_at_PDR = -40
# topology
topology = M+Aux
P_sharing_Wind_Turbine = 1.0
"""
_RETIRED_KEYS = [
    "p_max_injection_at_PDR",
    "p_min_injection_at_PDR",
    "u_nom_at_PDR",
    "q_max_at_PDR",
    "q_min_at_PDR",
]


@pytest.fixture
def legacy_ini(tmp_path: Path) -> Path:
    ini_file = tmp_path / "Producer.ini"
    ini_file.write_text(_LEGACY_INI)
    return ini_file


def test_every_retired_key_is_renamed_keeping_its_value(legacy_ini):
    migrate(legacy_ini.parent)

    content = legacy_ini.read_text()
    assert "p_max_injection = 75" in content
    assert "u_nom = 225" in content
    assert "q_max = 40" in content
    assert "q_min = -40" in content
    assert "_at_PDR" not in content


def test_a_commented_out_key_is_renamed_too(legacy_ini):
    migrate(legacy_ini.parent)

    assert "# p_min_injection =" in legacy_ini.read_text()


def test_what_is_not_a_magnitude_is_left_as_it_is(legacy_ini):
    migrate(legacy_ini.parent)

    content = legacy_ini.read_text()
    assert "topology = M+Aux" in content
    assert "P_sharing_Wind_Turbine = 1.0" in content
    assert "# q_max is the maximum reactive power at the PDR bus (in MVar)" in content


def test_the_report_names_the_retired_keys_of_each_file(legacy_ini):
    renamed = migrate(legacy_ini.parent)

    assert renamed == {legacy_ini: _RETIRED_KEYS}


def test_a_dry_run_reports_the_same_without_writing(legacy_ini):
    renamed = migrate(legacy_ini.parent, dry_run=True)

    assert renamed == {legacy_ini: _RETIRED_KEYS}
    assert legacy_ini.read_text() == _LEGACY_INI


def test_a_file_already_using_the_current_names_is_not_touched(tmp_path):
    ini_file = tmp_path / "Producer.ini"
    ini_file.write_text(_LEGACY_INI.replace("_at_PDR", ""))

    assert migrate(tmp_path) == {}


def test_both_zones_of_a_model_are_migrated(tmp_path):
    for zone in ("Zone1", "Zone3"):
        (tmp_path / zone).mkdir()
        (tmp_path / zone / "Producer.ini").write_text(_LEGACY_INI)

    renamed = migrate(tmp_path)

    assert sorted(renamed) == [
        tmp_path / "Zone1" / "Producer.ini",
        tmp_path / "Zone3" / "Producer.ini",
    ]


def test_a_single_ini_file_is_migrated(legacy_ini):
    renamed = migrate(legacy_ini)

    assert list(renamed) == [legacy_ini]


def test_prose_naming_a_retired_key_is_not_rewritten(tmp_path):
    ini_file = tmp_path / "Producer.ini"
    ini_file.write_text("[DEFAULT]\n# u_nom_at_PDR was its old name\nu_nom_at_PDR = 225\n")

    migrate(tmp_path)

    content = ini_file.read_text()
    assert "# u_nom_at_PDR was its old name" in content
    assert "u_nom = 225" in content
