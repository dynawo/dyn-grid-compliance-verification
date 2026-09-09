#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Metadata that the generated curve dictionaries ask for, as read by the curves importer."""

import re
from pathlib import Path

import pytest

import dycov
from dycov.curves.importer.curves import ImportedCurves

_IC = "dycov.curves.importer.curves"

_INPUT_TEMPLATES = Path(dycov.__file__).resolve().parent / "templates" / "inputs"
_METADATA_SECTION = "Curves-Metadata"
_SECTION_HEADER = re.compile(r"^\[(?P<name>[^]]+)\]\s*$")
_GENERATOR_PLACEHOLDER = "[WT_ID]"
_PER_GENERATOR_OPTION = re.compile(r"^(?P<option>\[WT_ID\][^=\s]+)\s*=")

_GENERATOR_ID = "Wind_Turbine"
_GENERATOR_IMAX = 1.3

_PCS = "PCSX"
_BM = "Bm"
_OC = "Oc"
_CFG_OC_NAME = f"{_PCS}.{_BM}.{_OC}"

_METADATA = (
    "[Curves-Metadata]\n"
    "sim_t_event_start = 20.0\n"
    "fault_duration = 1.5\n"
    "is_field_measurements = False\n"
)


def _per_generator_metadata_options(dict_file: Path) -> list[str]:
    """Options that a curve dictionary declares once per generator in its metadata section.

    A template dictionary cannot be read with configparser: the placeholder makes each of these
    declarations look like a section header, and the option name is dropped.

    Parameters
    ----------
    dict_file : Path
        Path to the curve dictionary.

    Returns
    -------
    list
        Option names, with the generator placeholder still in them.
    """
    options = []
    in_metadata = False
    for line in dict_file.read_text(encoding="utf-8").splitlines():
        section_header = _SECTION_HEADER.match(line)
        if section_header:
            in_metadata = section_header.group("name") == _METADATA_SECTION
            continue
        option = _PER_GENERATOR_OPTION.match(line)
        if in_metadata and option:
            options.append(option.group("option"))
    return options


def _declared_per_generator_options() -> list[tuple[Path, str]]:
    return [
        (dict_file, option)
        for dict_file in sorted(_INPUT_TEMPLATES.rglob("*.dict"))
        for option in _per_generator_metadata_options(dict_file)
    ]


_DECLARED_OPTIONS = _declared_per_generator_options()


class DummyProducer:
    """Producer reduced to what the curves importer asks of it.

    Parameters
    ----------
    curves_path : Path
        Directory holding the producer curves.
    """

    def __init__(self, curves_path: Path):
        self._curves_path = curves_path
        self.generators = []
        self.is_field_measurements = None
        self.consumption = None

    def get_zone(self) -> int:
        return 3

    def get_producer_curves_path(self) -> Path:
        return self._curves_path

    def set_generators(self, generators: list) -> None:
        self.generators = generators

    def set_is_field_measurements(self, is_field_measurements: bool) -> None:
        self.is_field_measurements = is_field_measurements

    def set_consumption(self, consumption: bool) -> None:
        self.consumption = consumption


class DummyConfig:
    """Tool configuration reduced to the options the curves importer reads."""

    def get_value(self, section: str, key: str):
        return "Pmax" if key == "pdr_P" else None

    def has_option(self, section: str, key: str) -> bool:
        return False


@pytest.fixture
def tool_config(monkeypatch) -> DummyConfig:
    """Replaces the tool configuration read while importing the curves."""
    config = DummyConfig()
    monkeypatch.setattr(f"{_IC}.config", config)
    return config


def _write_curves(curves_dir: Path, metadata: str) -> None:
    producer_dir = curves_dir / "Producer"
    producer_dir.mkdir(parents=True)
    (producer_dir / "CurvesFiles.ini").write_text(
        "[Curves-Files]\n"
        f"{_CFG_OC_NAME} = {_CFG_OC_NAME}.csv\n"
        "\n"
        "[Curves-Dictionary]\n"
        "time = time\n"
        "BusPDR_BUS_Voltage = BusPDR_BUS_Voltage\n"
        "\n"
        "[Curves-Dictionary-Zone1]\n"
        "\n"
        "[Curves-Dictionary-Zone3]\n"
    )
    (producer_dir / f"{_CFG_OC_NAME}.dict").write_text(
        f"{metadata}\n[Curves-Dictionary]\ntime = time\nBusPDR_BUS_Voltage = BusPDR_BUS_Voltage\n"
    )
    (producer_dir / f"{_CFG_OC_NAME}.csv").write_text(
        "time;BusPDR_BUS_Voltage\n0.0;1.0\n10.0;1.0\n20.0;1.0\n"
    )


def test_generated_curves_dicts_declare_a_per_generator_option():
    declared = _declared_per_generator_options()

    assert declared, f"No per-generator metadata option declared under {_INPUT_TEMPLATES}."


@pytest.mark.parametrize(
    "option",
    [option for _, option in _DECLARED_OPTIONS],
    ids=[dict_file.name for dict_file, _ in _DECLARED_OPTIONS],
)
def test_generated_per_generator_option_is_imported_as_the_generator_imax(
    option: str, tmp_path, tool_config
):
    """Guards issue #484: a generated dictionary asking for a value the importer never reads."""
    curves_dir = tmp_path / "ProducerCurves"
    declared_option = option.replace(_GENERATOR_PLACEHOLDER, _GENERATOR_ID)
    _write_curves(curves_dir, f"{_METADATA}{declared_option} = {_GENERATOR_IMAX}\n")
    working_oc_dir = tmp_path / "working"
    working_oc_dir.mkdir()
    imported_curves = ImportedCurves(DummyProducer(curves_dir))

    imported_curves.obtain_simulated_curve(working_oc_dir, "Producer", _PCS, _BM, _OC, None)

    assert imported_curves.get_generators_imax() == pytest.approx({_GENERATOR_ID: _GENERATOR_IMAX})
