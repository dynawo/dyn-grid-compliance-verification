#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023-2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Checks run on the files supplied as tool inputs."""

import logging
from pathlib import Path

import pytest
from lxml import etree

from dycov.sanity_checks import file_checks

_MODEL_EXTENSIONS = ("dyd", "par", "ini")

_FILLED_METADATA = (
    "[Curves-Metadata]\n"
    "is_field_measurements = False\n"
    "sim_t_event_start = 30.0\n"
    "fault_duration = 0.085\n"
    "frequency_sampling = 15\n"
)

_UNFILLED_METADATA = (
    "[Curves-Metadata]\n"
    "is_field_measurements =\n"
    "sim_t_event_start =\n"
    "fault_duration =\n"
    "frequency_sampling =\n"
)


def _get_resources_path() -> Path:
    return Path(__file__).resolve().parent / "resources"


def _write_model_files(model_path: Path, filename: str = "Producer", **stems: str) -> Path:
    """Writes the .dyd, .par and .ini files of a Dynawo model.

    Parameters
    ----------
    model_path : Path
        Directory to write the model files into.
    filename : str, optional
        Base name shared by the three files. By default, "Producer".
    **stems : str
        Base name to use for a single extension, overriding `filename`.

    Returns
    -------
    Path
        The directory holding the model files.
    """
    model_path.mkdir(parents=True, exist_ok=True)
    for extension in _MODEL_EXTENSIONS:
        (model_path / f"{stems.get(extension, filename)}.{extension}").write_text("")
    return model_path


def _write_curves_dict(curves_path: Path, name: str, metadata: str) -> Path:
    curves_path.mkdir(parents=True, exist_ok=True)
    dict_file = curves_path / f"{name}.dict"
    dict_file.write_text(f"{metadata}\n[Curves-Dictionary]\ntime = time\n")
    return dict_file


@pytest.fixture
def sanity_logs(monkeypatch, caplog):
    """Captures what the sanity checks log."""
    monkeypatch.setattr("dycov.logging.dycov_logging.get_logger", logging.getLogger)
    caplog.set_level(logging.WARNING)
    return caplog


# ---------------------------------------------------------------------------
# XML syntax
# ---------------------------------------------------------------------------


def test_validate_xml_syntax_accepts_a_wellformed_file():
    xml_file = _get_resources_path() / "wellformed.xml"

    assert file_checks.validate_xml_syntax(xml_file) is None


def test_validate_xml_syntax_rejects_a_badformed_file():
    xml_file = _get_resources_path() / "badformed.xml"

    with pytest.raises(etree.XMLSyntaxError) as syntax_error:
        file_checks.validate_xml_syntax(xml_file)

    assert syntax_error.value.code == 76
    assert (
        syntax_error.value.args[0]
        == "Opening and ending tag mismatch: elementwithoutend line 3 and root, line 4, column 8"
    )


# ---------------------------------------------------------------------------
# Dynawo model files
# ---------------------------------------------------------------------------


def test_check_dynawo_model_files_accepts_a_complete_model(tmp_path):
    model_path = _write_model_files(tmp_path / "Dynawo")

    assert file_checks.check_dynawo_model_files(model_path) is None


@pytest.mark.parametrize("missing_extension", _MODEL_EXTENSIONS)
def test_check_dynawo_model_files_rejects_a_model_without_one_file(tmp_path, missing_extension):
    model_path = _write_model_files(tmp_path / "Dynawo")
    (model_path / f"Producer.{missing_extension}").unlink()

    with pytest.raises(FileNotFoundError) as not_found_error:
        file_checks.check_dynawo_model_files(model_path)

    assert missing_extension in str(not_found_error.value)


def test_check_dynawo_model_files_rejects_files_with_different_names(tmp_path):
    model_path = _write_model_files(tmp_path / "Dynawo", par="AnotherProducer")

    with pytest.raises(FileNotFoundError) as not_found_error:
        file_checks.check_dynawo_model_files(model_path)

    assert "do not have the same name" in str(not_found_error.value)


def test_check_performance_model_accepts_a_complete_model(tmp_path):
    model_path = _write_model_files(tmp_path / "Dynawo")

    assert file_checks.check_performance_model(model_path) is None


# ---------------------------------------------------------------------------
# Curves configuration file
# ---------------------------------------------------------------------------


def test_check_curves_files_accepts_a_path_with_the_configuration():
    curves_path = _get_resources_path() / "Curves"

    assert file_checks.check_curves_files(None, curves_path, "") is None


def test_check_curves_files_without_curves_path_checks_nothing():
    assert file_checks.check_curves_files(None, None, "") is None


def test_check_curves_files_rejects_a_path_without_the_configuration():
    curves_path = _get_resources_path() / "Non-Curves"

    with pytest.raises(FileNotFoundError) as not_found_error:
        file_checks.check_curves_files(None, curves_path, "")

    assert "CurvesFiles.ini" in str(not_found_error.value)


def test_check_curves_files_generates_the_configuration_from_the_model(tmp_path, monkeypatch):
    created_curves = []
    monkeypatch.setattr(
        file_checks,
        "create_producer_curves",
        lambda model_path, curves_path, template: created_curves.append(template),
    )
    model_path = _write_model_files(tmp_path / "Dynawo")

    with pytest.raises(FileNotFoundError):
        file_checks.check_curves_files(model_path, tmp_path / "Curves", "performance/SM")

    assert created_curves == ["performance_SM"]


# ---------------------------------------------------------------------------
# Performance curves
# ---------------------------------------------------------------------------


def test_check_performance_curves_accepts_a_configuration_with_its_directory(tmp_path):
    curves_path = tmp_path / "ProducerCurves"
    curves_path.mkdir()
    (curves_path / "Producer.ini").write_text("")
    (curves_path / "Producer").mkdir()

    assert file_checks.check_performance_curves(curves_path) is None


def test_check_performance_curves_rejects_a_path_without_configuration(tmp_path):
    curves_path = tmp_path / "ProducerCurves"
    curves_path.mkdir()

    with pytest.raises(FileNotFoundError) as not_found_error:
        file_checks.check_performance_curves(curves_path)

    assert "Configuration file is not present" in str(not_found_error.value)


def test_check_performance_curves_rejects_a_configuration_without_its_directory(tmp_path):
    curves_path = tmp_path / "ProducerCurves"
    curves_path.mkdir()
    (curves_path / "Producer.ini").write_text("")

    with pytest.raises(FileNotFoundError) as not_found_error:
        file_checks.check_performance_curves(curves_path)

    assert "Curves files for Producer" in str(not_found_error.value)


# ---------------------------------------------------------------------------
# Model validation curves
# ---------------------------------------------------------------------------


def _write_zone_curves(curves_path: Path, zone_name: str) -> None:
    zone_path = curves_path / zone_name
    zone_path.mkdir(parents=True)
    (zone_path / "Producer.ini").write_text("")
    (curves_path / "Producer").mkdir(exist_ok=True)


def test_check_zone_curves_and_references_accepts_a_complete_zone(tmp_path):
    curves_path = tmp_path / "ProducerCurves"
    _write_zone_curves(curves_path, "Zone1")
    reference_path = tmp_path / "ReferenceCurves"
    (reference_path / "Producer").mkdir(parents=True)

    assert (
        file_checks.check_zone_curves_and_references("Zone1", curves_path, reference_path) is None
    )


def test_check_zone_curves_and_references_rejects_a_missing_zone(tmp_path):
    curves_path = tmp_path / "ProducerCurves"
    curves_path.mkdir()

    with pytest.raises(FileNotFoundError) as not_found_error:
        file_checks.check_zone_curves_and_references("Zone1", curves_path, tmp_path / "Reference")

    assert "Zone1 configuration files not found" in str(not_found_error.value)


def test_check_zone_curves_and_references_rejects_a_zone_without_configuration(tmp_path):
    curves_path = tmp_path / "ProducerCurves"
    (curves_path / "Zone1").mkdir(parents=True)

    with pytest.raises(FileNotFoundError) as not_found_error:
        file_checks.check_zone_curves_and_references("Zone1", curves_path, tmp_path / "Reference")

    assert "Zone1 configuration files not found" in str(not_found_error.value)


def test_check_zone_curves_and_references_rejects_a_configuration_without_its_directory(tmp_path):
    curves_path = tmp_path / "ProducerCurves"
    (curves_path / "Zone1").mkdir(parents=True)
    (curves_path / "Zone1" / "Producer.ini").write_text("")

    with pytest.raises(FileNotFoundError) as not_found_error:
        file_checks.check_zone_curves_and_references("Zone1", curves_path, tmp_path / "Reference")

    assert "Curves files for Producer" in str(not_found_error.value)


def test_check_zone_curves_and_references_warns_about_missing_references(tmp_path, sanity_logs):
    curves_path = tmp_path / "ProducerCurves"
    _write_zone_curves(curves_path, "Zone1")
    reference_path = tmp_path / "ReferenceCurves"
    reference_path.mkdir()

    file_checks.check_zone_curves_and_references("Zone1", curves_path, reference_path)

    assert any("Reference curves for Producer" in log.message for log in sanity_logs.records)


def test_check_validation_curves_checks_both_zones(tmp_path):
    curves_path = tmp_path / "ProducerCurves"
    _write_zone_curves(curves_path, "Zone1")
    reference_path = tmp_path / "ReferenceCurves"
    (reference_path / "Producer").mkdir(parents=True)

    with pytest.raises(FileNotFoundError) as not_found_error:
        file_checks.check_validation_curves(curves_path, reference_path)

    assert "Zone3 configuration files not found" in str(not_found_error.value)


# ---------------------------------------------------------------------------
# Model validation model
# ---------------------------------------------------------------------------


def _write_validation_model(model_path: Path) -> Path:
    _write_model_files(model_path / "Zone3")
    _write_model_files(model_path / "Zone1", "Producer_G1")
    return model_path


def test_check_validation_model_accepts_a_model_with_one_generator_per_zone(tmp_path):
    model_path = _write_validation_model(tmp_path / "Dynawo")
    reference_path = tmp_path / "ReferenceCurves"
    (reference_path / "Producer").mkdir(parents=True)
    (reference_path / "Producer_G1").mkdir()

    assert (
        file_checks.check_validation_model(
            model_path, reference_path, 1, ["Producer"], ["Producer_G1"]
        )
        is None
    )


def test_check_validation_model_rejects_a_generator_count_mismatch(tmp_path):
    model_path = _write_validation_model(tmp_path / "Dynawo")
    reference_path = tmp_path / "ReferenceCurves"
    reference_path.mkdir()

    with pytest.raises(ValueError) as count_error:
        file_checks.check_validation_model(
            model_path, reference_path, 2, ["Producer"], ["Producer_G1"]
        )

    assert "count mismatch" in str(count_error.value)


def test_check_validation_model_warns_about_unexpected_reference_curves(tmp_path, sanity_logs):
    model_path = _write_validation_model(tmp_path / "Dynawo")
    reference_path = tmp_path / "ReferenceCurves"
    (reference_path / "Producer_G2").mkdir(parents=True)

    file_checks.check_validation_model(
        model_path, reference_path, 1, ["Producer"], ["Producer_G1"]
    )

    assert any("Producer_G2 has not Reference" in log.message for log in sanity_logs.records)


def test_check_validation_model_ignores_loose_files_in_the_reference_path(tmp_path, sanity_logs):
    model_path = _write_validation_model(tmp_path / "Dynawo")
    reference_path = tmp_path / "ReferenceCurves"
    reference_path.mkdir(parents=True)
    (reference_path / "README.txt").write_text("")

    file_checks.check_validation_model(
        model_path, reference_path, 1, ["Producer"], ["Producer_G1"]
    )

    assert sanity_logs.records == []


# ---------------------------------------------------------------------------
# Curves metadata
# ---------------------------------------------------------------------------


def test_check_curves_metadata_accepts_filled_dictionaries(tmp_path):
    curves_path = tmp_path / "ReferenceCurves"
    _write_curves_dict(curves_path / "Producer", "PCS_RTE-I16z3.Bm.Oc", _FILLED_METADATA)

    assert file_checks.check_curves_metadata(curves_path) is None


def test_check_curves_metadata_without_paths_checks_nothing():
    assert file_checks.check_curves_metadata(None, None) is None


def test_check_curves_metadata_names_the_dictionary_and_the_options(tmp_path, sanity_logs):
    """Guards against issue #481: the run aborted without naming file nor option."""
    curves_path = tmp_path / "ReferenceCurves"
    dict_file = _write_curves_dict(
        curves_path / "Producer", "PCS_RTE-I16z3.Bm.Oc", _UNFILLED_METADATA
    )

    with pytest.raises(ValueError):
        file_checks.check_curves_metadata(curves_path)

    reported = "\n".join(log.message for log in sanity_logs.records)
    assert str(dict_file) in reported
    assert "is_field_measurements, sim_t_event_start, fault_duration" in reported


def test_check_curves_metadata_ignores_the_sampling_frequency(tmp_path):
    """The sampling frequency of a CSV file is not read from the dictionary."""
    curves_path = tmp_path / "ReferenceCurves"
    _write_curves_dict(
        curves_path / "Producer",
        "PCS_RTE-I16z3.Bm.Oc",
        _FILLED_METADATA.replace("frequency_sampling = 15", "frequency_sampling ="),
    )

    assert file_checks.check_curves_metadata(curves_path) is None


def test_check_curves_metadata_reports_every_unfilled_dictionary(tmp_path, sanity_logs):
    producer_curves_path = tmp_path / "ProducerCurves"
    reference_curves_path = tmp_path / "ReferenceCurves"
    _write_curves_dict(producer_curves_path / "Producer", "PCS_RTE-I2.Bm.Oc", _UNFILLED_METADATA)
    _write_curves_dict(
        reference_curves_path / "Producer_G1", "PCS_RTE-I16z1.Bm.Oc", _UNFILLED_METADATA
    )
    _write_curves_dict(
        reference_curves_path / "Producer_G2", "PCS_RTE-I16z1.Bm.Oc", _FILLED_METADATA
    )

    with pytest.raises(ValueError):
        file_checks.check_curves_metadata(producer_curves_path, reference_curves_path)

    reported = "\n".join(log.message for log in sanity_logs.records)
    assert "PCS_RTE-I2.Bm.Oc.dict" in reported
    assert "Producer_G1/PCS_RTE-I16z1.Bm.Oc.dict" in reported
    assert "Producer_G2" not in reported


def test_check_curves_metadata_skips_an_unreadable_dictionary(tmp_path):
    """An unreadable dictionary is reported by the importer, for each operating condition."""
    curves_path = tmp_path / "ReferenceCurves" / "Producer"
    curves_path.mkdir(parents=True)
    (curves_path / "PCS_RTE-I16z3.Bm.Oc.dict").write_text("sim_t_event_start =\n")

    assert file_checks.check_curves_metadata(tmp_path / "ReferenceCurves") is None
