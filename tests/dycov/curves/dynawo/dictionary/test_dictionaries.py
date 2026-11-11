#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The entries of the Dynawo dictionaries, and the parameters the TSO and Omega templates set,
against the models of the Dynawo the tool runs.

Dynawo accepts a parameter its model does not have, ignores a read-only parameter a PAR sets, and
drops the request of a curve its model does not have, all without failing: an entry that names
none of what a PAR or a curve can reach goes unnoticed. These tests read the model descriptors of
the installation DYNAWOPATH or the PATH points to, and are skipped without one.
"""

import configparser
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from tests.dycov.utils import _resolve_dynawo_sh

import dycov
from dycov.curves.dynawo import dictionary

_DICTIONARIES = Path(dictionary.__file__).parent
_TEMPLATES = Path(dycov.__file__).parent / "model_lib"
# The control modes name the parameter sets of a mode, not a model.
_NOT_MODELS = {"Control_Modes.ini"}
_DYNAWO_NS = "{http://www.rte-france.com/dynawo}"
# A flag that no parameter of the model holds is stated in the dictionary itself.
_STATED_FLAGS = {"true", "false"}


def _models():
    models = []
    for path in sorted(_DICTIONARIES.glob("*.ini")):
        if path.name in _NOT_MODELS:
            continue
        parser = configparser.ConfigParser(inline_comment_prefixes=("#",), strict=False)
        parser.optionxform = str
        parser.read(path)
        for lib in parser.sections():
            entries = {
                key: value.lstrip("-")
                for key, value in parser.items(lib)
                if key != "family" and value.lower() not in _STATED_FLAGS
            }
            models.append(pytest.param(lib, entries, id=lib))
    return models


def _reachable_names_of(descriptor: Path) -> set[str]:
    root = ET.parse(descriptor).getroot()
    parameters = {
        element.get("name")
        for element in root.iter(f"{_DYNAWO_NS}parameter")
        if element.get("readOnly") != "true"
    }
    return parameters | {element.get("name") for element in root.iter(f"{_DYNAWO_NS}variable")}


@pytest.fixture(scope="module")
def descriptors() -> Path:
    dynawo_sh = _resolve_dynawo_sh()
    if dynawo_sh is None or not (dynawo_sh.parent / "ddb").is_dir():
        pytest.skip("No Dynawo installation: set DYNAWOPATH or put dynawo.sh on the PATH")
    return dynawo_sh.parent / "ddb"


@pytest.mark.parametrize("lib, entries", _models())
def test_every_entry_names_a_settable_parameter_or_a_variable_of_its_model(
    descriptors, lib, entries
):
    descriptor = descriptors / f"{lib}.desc.xml"
    assert descriptor.exists(), f"Dynawo has no model {lib}"

    names = _reachable_names_of(descriptor)

    assert {key: name for key, name in entries.items() if name not in names} == {}


def _template_sets():
    """Every parameter set a TSO or Omega template gives a model, with the model it is for."""
    sets = []
    for dyd in sorted(_TEMPLATES.rglob("*.dyd")):
        for model in ET.parse(dyd).getroot().iter(f"{_DYNAWO_NS}blackBoxModel"):
            if model.get("parId") is None:
                continue
            par = ET.parse(dyd.parent / model.get("parFile")).getroot()
            for parameter_set in par.iter(f"{_DYNAWO_NS}set"):
                if parameter_set.get("id") == model.get("parId"):
                    names = [element.get("name") for element in parameter_set]
                    sets.append(
                        pytest.param(
                            model.get("lib"),
                            names,
                            id=f"{dyd.parent.name}-{model.get('id')}",
                        )
                    )
    return sets


def _settable_parameters_of(descriptor: Path) -> tuple[set[str], set[str]]:
    """The parameters a PAR may set: the names of the single ones, and those of the arrays,
    which a PAR sets one element at a time, suffixed with its index."""
    singles, arrays = set(), set()
    for element in ET.parse(descriptor).getroot().iter(f"{_DYNAWO_NS}parameter"):
        if element.get("readOnly") == "true":
            continue
        (arrays if element.get("cardinality") == "*" else singles).add(element.get("name"))
    return singles, arrays


def test_the_templates_give_their_models_parameter_sets():
    assert _template_sets()


@pytest.mark.parametrize("lib, names", _template_sets())
def test_every_parameter_a_template_sets_is_a_settable_parameter_of_its_model(
    descriptors, lib, names
):
    descriptor = descriptors / f"{lib}.desc.xml"
    assert descriptor.exists(), f"Dynawo has no model {lib}"

    singles, arrays = _settable_parameters_of(descriptor)

    def is_settable(name: str) -> bool:
        array, _, index = name.rpartition("_")
        return name in singles or (array in arrays and index.isdigit())

    assert [name for name in names if not is_settable(name)] == []
