#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the ModelProducer helpers."""

import configparser
from pathlib import Path

import pytest
from tests.dycov.utils import listed_in_order

from dycov.configuration.cfg import Config
from dycov.core.global_variables import (
    ELECTRIC_PERFORMANCE_BESS,
    ELECTRIC_PERFORMANCE_PPM,
    MODEL_VALIDATION_BESS,
    MODEL_VALIDATION_PPM,
)
from dycov.model.parameters import GenParams, Terminal
from dycov.validate import producer as producer_module
from dycov.validate.producer import ModelProducer

_PRODUCER_INI = """[DEFAULT]
p_max_injection = 80
u_nom = 225
q_max = 40
q_min = -40
topology = S
"""


def _producer_reading(
    monkeypatch, ini_text: str, sim_type: int = MODEL_VALIDATION_PPM
) -> ModelProducer:
    producer = ModelProducer.__new__(ModelProducer)
    producer._s_nref = 100.0
    producer._sim_type = sim_type
    producer_config = configparser.ConfigParser()
    producer_config.read_string(ini_text)
    monkeypatch.setattr(producer, "_ModelProducer__read_producer_ini", lambda: producer_config)
    producer._ModelProducer__init_parameters()
    return producer


def _make_generator(converter_lv_control: bool) -> GenParams:
    return GenParams(
        id="PV_Array",
        lib="",
        terminals=(Terminal(connected_equipment=""),),
        par_id="",
        s_nom=100.0,
        i_max=1.0,
        p=0.0,
        q=0.0,
        voltage_droop=0.0,
        use_voltage_droop=False,
        converter_lv_control=converter_lv_control,
    )


def _producer_with_curves(curves_path: Path) -> ModelProducer:
    producer = ModelProducer.__new__(ModelProducer)
    producer._producer_model_path = None
    producer._producer_curves_path = curves_path
    return producer


def _curves_tree(root: Path) -> Path:
    curves_path = root / "ProducerCurves"
    for folder in ("Producer", "Zone1", "Zone3"):
        (curves_path / folder).mkdir(parents=True)
    (curves_path / "Zone3" / "Producer.ini").write_text("[DEFAULT]\n")
    return curves_path


def _producer_with_model(*generators: GenParams) -> ModelProducer:
    producer = ModelProducer.__new__(ModelProducer)
    producer._is_dynawo_model = True
    producer.generators = list(generators)
    return producer


def test_the_producer_gives_the_category_of_its_unit(monkeypatch):
    """The DTR of 15/02/2024 makes every unit above 110 kV a type D."""
    producer = _producer_reading(monkeypatch, _PRODUCER_INI)

    assert producer.get_category() == "D"


def test_the_category_of_a_unit_below_110_kv_follows_its_power(monkeypatch):
    ini = _PRODUCER_INI.replace("u_nom = 225", "u_nom = 90")

    assert _producer_reading(monkeypatch, ini).get_category() == "D"
    assert (
        _producer_reading(
            monkeypatch, ini.replace("p_max_injection = 80", "p_max_injection = 20")
        ).get_category()
        == "C"
    )


def test_s_nom_pu_is_snom_over_snref():
    producer = ModelProducer.__new__(ModelProducer)
    producer.s_nom = 180.0
    producer._s_nref = 100.0

    assert producer.s_nom_pu == pytest.approx(1.8)


def test_init_reads_s_nref_from_the_dynawo_section(monkeypatch):
    monkeypatch.setattr(
        Config,
        "get_float",
        lambda self, section, key, default: (
            90.0 if (section, key) == ("Dynawo", "s_nref") else default
        ),
    )

    producer = ModelProducer(None, None, None, -1)

    assert producer._s_nref == pytest.approx(90.0)


def test_minimum_active_power_is_read_in_pu_of_s_nref(monkeypatch):
    producer = _producer_reading(
        monkeypatch,
        _PRODUCER_INI + "p_min_injection = 8\np_min_consumption = 4\n",
    )

    assert producer.p_min_injection_pu == pytest.approx(0.08)
    assert producer.p_min_consumption_pu == pytest.approx(0.04)


def test_minimum_active_power_is_zero_when_the_ini_does_not_declare_it(monkeypatch):
    producer = _producer_reading(monkeypatch, _PRODUCER_INI)

    assert producer.p_min_injection_pu == 0.0
    assert producer.p_min_consumption_pu == 0.0


def test_a_key_of_the_retired_naming_is_rejected_by_the_name_to_use(monkeypatch):
    ini_text = _PRODUCER_INI.replace("u_nom = 225", "u_nom_at_PDR = 225")

    with pytest.raises(ValueError, match="migrate_inputs.*rename it to u_nom"):
        _producer_reading(monkeypatch, ini_text)


def test_a_missing_magnitude_is_reported_by_its_name(monkeypatch):
    ini_text = _PRODUCER_INI.replace("q_max = 40\n", "")

    with pytest.raises(ValueError, match="must specify the q_max"):
        _producer_reading(monkeypatch, ini_text)


def test_storage_must_declare_the_consumption_limit(monkeypatch):
    with pytest.raises(ValueError, match="must specify the p_max_consumption"):
        _producer_reading(monkeypatch, _PRODUCER_INI, MODEL_VALIDATION_BESS)


def _performance_producer(monkeypatch, ini_text: str, model: bool, kinds: tuple) -> ModelProducer:
    """A producer whose kind of unit a performance verification is about to read, from its
    model (the generators of its DYD) or from the INI beside its curves."""
    producer = ModelProducer.__new__(ModelProducer)
    producer._s_nref = 100.0
    producer._sim_type = None
    producer._is_dynawo_model = model
    producer._producer_model_path = Path("Model") if model else None
    producer._producer_curves_path = None if model else Path("ProducerCurves")
    producer_config = configparser.ConfigParser()
    producer_config.read_string(ini_text)
    monkeypatch.setattr(producer, "_ModelProducer__read_producer_ini", lambda: producer_config)
    monkeypatch.setattr(producer, "get_producer_dyd", lambda: Path("Producer.dyd"))
    monkeypatch.setattr(producer, "get_producer_par", lambda: Path("Producer.par"))
    monkeypatch.setattr(producer_module.file_checks, "check_performance_model", lambda path: None)
    monkeypatch.setattr(producer_module.file_checks, "check_performance_curves", lambda path: None)
    monkeypatch.setattr(
        producer_module.model_parameters, "get_producer_values", lambda *args: ([],) * 6
    )
    monkeypatch.setattr(
        producer_module.parameter_checks, "check_producer_params_consistency", lambda *a, **k: None
    )
    monkeypatch.setattr(producer_module.parameter_checks, "check_generators", lambda gens: kinds)
    return producer


_STORAGE = (0, 0, 1)
_POWER_PARK = (0, 1, 0)


@pytest.mark.parametrize("model", [True, False], ids=["model", "curves"])
def test_storage_performance_must_declare_the_consumption_limit(monkeypatch, model):
    producer = _performance_producer(
        monkeypatch, _PRODUCER_INI + "generator_type = BESS\n", model, _STORAGE
    )

    with pytest.raises(ValueError, match="must specify the p_max_consumption"):
        producer._ModelProducer__set_electric_performance_type()


@pytest.mark.parametrize("model", [True, False], ids=["model", "curves"])
def test_storage_performance_with_the_retired_name_points_to_the_migration(monkeypatch, model):
    producer = _performance_producer(
        monkeypatch,
        _PRODUCER_INI + "generator_type = BESS\np_max_consumption_at_PDR = 60\n",
        model,
        _STORAGE,
    )

    with pytest.raises(ValueError, match="p_max_consumption_at_PDR.*migrate_inputs"):
        producer._ModelProducer__set_electric_performance_type()


@pytest.mark.parametrize("model", [True, False], ids=["model", "curves"])
def test_storage_performance_runs_with_the_consumption_limit(monkeypatch, model):
    producer = _performance_producer(
        monkeypatch,
        _PRODUCER_INI + "generator_type = BESS\np_max_consumption = 60\n",
        model,
        _STORAGE,
    )

    producer._ModelProducer__set_electric_performance_type()

    assert producer.get_sim_type() == ELECTRIC_PERFORMANCE_BESS


@pytest.mark.parametrize("model", [True, False], ids=["model", "curves"])
def test_power_park_performance_needs_no_consumption_limit(monkeypatch, model):
    producer = _performance_producer(
        monkeypatch, _PRODUCER_INI + "generator_type = PPM\n", model, _POWER_PARK
    )

    producer._ModelProducer__set_electric_performance_type()

    assert producer.get_sim_type() == ELECTRIC_PERFORMANCE_PPM


def test_the_operating_mode_selects_the_active_power_limits(monkeypatch):
    producer = _producer_reading(
        monkeypatch,
        _PRODUCER_INI + "p_max_consumption = 60\np_min_injection = 8\np_min_consumption = 4\n",
    )

    producer.set_consumption(False)
    injection = (producer.p_max_pu, producer.p_min_pu)
    producer.set_consumption(True)
    consumption = (producer.p_max_pu, producer.p_min_pu)

    assert injection == pytest.approx((0.8, 0.08))
    assert consumption == pytest.approx((-0.6, -0.04))


@pytest.mark.parametrize("converter_lv_control", [True, False])
def test_the_controlled_node_is_the_converter_lv_control_flag_of_the_model(converter_lv_control):
    producer = _producer_with_model(_make_generator(converter_lv_control))

    assert producer.controls_internal_node2() is converter_lv_control


def test_the_controlled_node_is_internal_node1_when_a_unit_controls_it():
    producer = _producer_with_model(_make_generator(True), _make_generator(False))

    assert producer.controls_internal_node2() is False


def test_the_controlled_node_keeps_the_flag_default_for_curves_without_a_model():
    producer = ModelProducer.__new__(ModelProducer)
    producer._is_dynawo_model = False

    assert producer.controls_internal_node2() is True


def _model_in(model_path: Path, zone: int = 0, filename=None) -> ModelProducer:
    producer = ModelProducer.__new__(ModelProducer)
    producer._producer_model_path = model_path
    producer._producer_curves_path = None
    producer._zone = zone
    producer._filename = filename
    return producer


@pytest.mark.parametrize("reverse", [False, True], ids=["dyd listed first", "par listed first"])
@pytest.mark.parametrize("folder", ["WindPark", "IECPark", "partage", "Model_dyd"])
def test_the_model_files_are_found_whatever_the_folder_is_called(
    tmp_path, monkeypatch, folder, reverse
):
    model_path = tmp_path / folder
    model_path.mkdir()
    for extension in ("dyd", "par", "ini"):
        (model_path / f"Producer.{extension}").write_text("[DEFAULT]\n")
    (model_path / "LHVRT.txt").write_text("")
    listed_in_order(monkeypatch, reverse)
    producer = _model_in(model_path)

    assert producer.get_producer_dyd().name == "Producer.dyd"
    assert producer.get_producer_par().name == "Producer.par"
    assert producer.get_filenames() == ["Producer"]


@pytest.mark.parametrize("reverse", [False, True], ids=["listed first", "listed last"])
def test_a_unit_is_not_taken_for_one_whose_name_ends_with_it(tmp_path, monkeypatch, reverse):
    zone1 = tmp_path / "Dynawo" / "Zone1"
    zone1.mkdir(parents=True)
    for unit, p_max in (("G1", 10), ("WG1", 20)):
        for extension in ("dyd", "par", "ini"):
            (zone1 / f"{unit}.{extension}").write_text(f"[DEFAULT]\np_max_injection = {p_max}\n")
    listed_in_order(monkeypatch, reverse)
    producer = _model_in(tmp_path / "Dynawo", zone=1, filename="G1")

    assert producer.get_producer_dyd().name == "G1.dyd"
    assert producer.get_producer_par().name == "G1.par"
    assert producer._ModelProducer__read_producer_ini().get("DEFAULT", "p_max_injection") == "10"


def test_get_filenames_of_a_zone_not_delivered_is_empty(tmp_path):
    (tmp_path / "Zone3").mkdir()
    (tmp_path / "Zone3" / "Producer.dyd").write_text("")
    producer = ModelProducer.__new__(ModelProducer)
    producer._producer_model_path = tmp_path
    producer._producer_curves_path = None

    assert producer.get_filenames(zone=1) == []
    assert producer.get_filenames(zone=3) == ["Producer"]


def test_get_filenames_skips_the_zone_folders_of_the_curves_directory(tmp_path):
    producer = _producer_with_curves(_curves_tree(tmp_path))

    assert producer.get_filenames() == ["Producer"]


@pytest.mark.parametrize("enclosing_folder", ["Zone1_validation_file", "Zone3_case"])
def test_get_filenames_ignores_a_zone_name_above_the_curves_directory(tmp_path, enclosing_folder):
    producer = _producer_with_curves(_curves_tree(tmp_path / enclosing_folder))

    assert producer.get_filenames() == ["Producer"]


def test_get_filenames_skips_a_folder_of_the_curves_that_no_ini_describes(tmp_path, caplog):
    """#687: the Results a run leaves next to the INI is no producer, and stops nothing."""
    (tmp_path / "Producer").mkdir()
    (tmp_path / "Producer.ini").write_text("[DEFAULT]\n")
    (tmp_path / "Results").mkdir()
    producer = _producer_with_curves(tmp_path)

    assert producer.get_filenames() == ["Producer"]
    assert producer.get_filenames() == ["Producer"]
    assert caplog.text.count(f"{tmp_path / 'Results'} is skipped") == 1


def test_get_filenames_of_the_curves_reads_the_ini_of_the_zone(tmp_path, caplog):
    curves_path = tmp_path / "ProducerCurves"
    for folder in ("Producer", "Zone3"):
        (curves_path / folder).mkdir(parents=True)
    (curves_path / "Zone3" / "Producer.INI").write_text("[DEFAULT]\n")
    producer = _producer_with_curves(curves_path)

    assert producer.get_filenames(zone=1) == []
    assert producer.get_filenames(zone=3) == ["Producer"]
    assert "is skipped" not in caplog.text
