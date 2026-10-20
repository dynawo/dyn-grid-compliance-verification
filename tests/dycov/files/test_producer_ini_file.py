#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the Producer INI writer."""

import configparser
from pathlib import Path

import pytest

from dycov.files.producer_ini_file import (
    MAGNITUDE_KEYS,
    check_ini_parameters,
    create_producer_ini_file,
    write_producer_ini_file,
)

_FILLED_INI = (
    "[DEFAULT]\n"
    "# p_{max_unite} injection as defined by the DTR in MW\n"
    "p_max_injection = 100\n"
    "# u_nom is the nominal voltage of that bus (in kV)\n"
    "u_nom = 225\n"
    "# q_max is the maximum reactive power (in MVar)\n"
    "q_max = 50\n"
    "# q_min is the minimum reactive power (in MVar)\n"
    "q_min = -50\n"
    "# topology\n"
    "topology = S\n"
)


@pytest.fixture
def model_target(tmp_path: Path) -> Path:
    (tmp_path / "Zone1").mkdir()
    (tmp_path / "Zone3").mkdir()
    return tmp_path


def test_every_ini_explains_why_the_file_exists(model_target):
    create_producer_ini_file(model_target, "S", "model_PPM")
    write_producer_ini_file(
        model_target, "Filled.ini", "S", {"u_nom": "33"}, {"Wind_Turbine": ("1", "1")}
    )

    for ini_file in (model_target / "Zone1" / "Producer.ini", model_target / "Filled.ini"):
        content = ini_file.read_text()
        assert "The raison d'être for this INI file" in content
        assert "**both** input files" in content
        assert "more restrictive than PAR" in content


def test_the_template_names_the_magnitudes_without_naming_a_point(tmp_path):
    create_producer_ini_file(tmp_path, "S", "performance_SM")

    content = (tmp_path / "Producer.ini").read_text()
    assert "topology = S" in content
    for key in ("p_max_injection", "p_max_consumption", "u_nom", "q_max", "q_min"):
        assert f"{key} =" in content
    assert "_at_PDR" not in content


def test_the_registry_names_exactly_the_magnitudes_the_template_declares(tmp_path):
    create_producer_ini_file(tmp_path, "S", "performance_BESS")

    declared = {
        line.lstrip("# ").split("=")[0].strip()
        for line in (tmp_path / "Producer.ini").read_text().splitlines()
        if "=" in line
    }

    sharing = {"topology", "P_sharing_[GEN_ID]", "Q_sharing_[GEN_ID]"}
    assert declared - sharing == set(MAGNITUDE_KEYS)


def test_each_zone_says_the_point_its_magnitudes_are_declared_at(model_target):
    create_producer_ini_file(model_target, "S", "model_PPM")

    zone1_content = (model_target / "Zone1" / "Producer.ini").read_text()
    zone3_content = (model_target / "Zone3" / "Producer.ini").read_text()

    assert "declared at InternalNode1" in zone1_content
    assert "Allowed values" not in zone1_content
    assert "declared at the PDR" in zone3_content
    assert "Allowed values" in zone3_content


def test_a_performance_model_declares_its_magnitudes_at_the_pdr(tmp_path):
    create_producer_ini_file(tmp_path, "S", "performance_SM")

    assert "declared at the PDR" in (tmp_path / "Producer.ini").read_text()


def test_check_ini_parameters_accepts_an_ini_without_empty_values(tmp_path):
    (tmp_path / "Producer.ini").write_text(_FILLED_INI)

    assert check_ini_parameters(tmp_path, "performance_SM") is True


def test_check_ini_parameters_rejects_an_ini_with_an_empty_value(tmp_path):
    (tmp_path / "Producer.ini").write_text(
        _FILLED_INI.replace("p_max_injection = 100", "p_max_injection =")
    )

    assert check_ini_parameters(tmp_path, "performance_SM") is False


def test_write_producer_ini_file_fills_values(tmp_path):
    write_producer_ini_file(
        tmp_path,
        "Producer.ini",
        "S+Aux",
        values={"p_max_injection": 50, "u_nom": 63, "q_max": 16, "q_min": -16},
        gen_sharing={"Power_Park": (1.0, 1.0)},
    )

    producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    producer_config.read(tmp_path / "Producer.ini")
    assert producer_config.get("DEFAULT", "topology").strip() == "S+Aux"
    assert producer_config.get("DEFAULT", "p_max_injection").strip() == "50"
    assert producer_config.get("DEFAULT", "u_nom").strip() == "63"
    assert producer_config.get("DEFAULT", "P_sharing_Power_Park").strip() == "1.0"
    assert producer_config.get("DEFAULT", "Q_sharing_Power_Park").strip() == "1.0"
    assert check_ini_parameters(tmp_path, "performance_SM") is True


def test_write_producer_ini_file_bess_consumption(tmp_path):
    write_producer_ini_file(
        tmp_path,
        "Producer.ini",
        "S",
        values={
            "p_max_injection": 50,
            "p_max_consumption": 40,
            "u_nom": 63,
            "q_max": 16,
            "q_min": -16,
        },
        gen_sharing={"Storage": (1.0, 1.0)},
        include_consumption=True,
    )

    assert "p_max_consumption = 40" in (tmp_path / "Producer.ini").read_text()


def test_create_producer_ini_file_nonexistent_target(tmp_path):
    with pytest.raises(FileNotFoundError):
        create_producer_ini_file(tmp_path / "missing", "S", "performance_SM")


def test_a_multiple_model_has_a_zone1_ini_per_generator(model_target):
    create_producer_ini_file(model_target, "M+i", "model_PPM", n_generators=3)

    assert sorted(p.name for p in (model_target / "Zone1").iterdir()) == [
        "Producer_G1.ini",
        "Producer_G2.ini",
        "Producer_G3.ini",
    ]
    assert "topology = S" in (model_target / "Zone1" / "Producer_G3.ini").read_text()
    assert "topology = M+i" in (model_target / "Zone3" / "Producer.ini").read_text()
