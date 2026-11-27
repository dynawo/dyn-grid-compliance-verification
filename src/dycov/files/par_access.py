#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from __future__ import annotations

from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.logging import dycov_logging

"""Low-level access to the parameter sets of a Dynawo PAR file."""


def get_parset(par_root, par_id, nsmap):
    parset = par_root.xpath(f"//ns:set[@id='{par_id}']", namespaces=nsmap)
    if not parset:
        raise ValueError(f"The parameter set with id='{par_id}' was not found")
    if len(parset) > 1:
        raise ValueError(f"Multiple parameter sets with id='{par_id}' were found")
    return parset


def _find(parset, nsmap, lib, parameter_name):
    """The sign of a parameter, its name in the PAR and its element, None when it is absent."""
    sign, variable_name = dynawo_translator.get_dynawo_variable(lib, parameter_name)
    if not variable_name:
        return None, None, None
    found = parset[0].xpath(f"ns:par[@name='{variable_name}']", namespaces=nsmap)
    return sign, variable_name, found[0] if found else None


def get_parameter(parset, nsmap, lib, parameter_name):
    sign, _, element = _find(parset, nsmap, lib, parameter_name)
    return sign, element.get("value") if element is not None else None


def dynawo_boolean(value: str, variable_name: str, set_id: str) -> bool:
    """A boolean of the PAR as Dynawo reads it, true only when written ``true``. Any other
    spelling, ``TRUE`` or ``1`` among them, runs as false, which the user is told."""
    if value not in ("true", "false"):
        dycov_logging.warn_once(
            "Model Parameters",
            f"{variable_name} = {value!r} in the set {set_id} of the producer's PAR: Dynawo "
            f"reads it as false, write true or false.",
        )
    return value == "true"


def get_boolean(parset, nsmap, lib, parameter_name, default: bool) -> bool:
    """A boolean parameter of the PAR as Dynawo reads it, *default* when it is absent."""
    _, variable_name, element = _find(parset, nsmap, lib, parameter_name)
    if element is None:
        return default
    return dynawo_boolean(element.get("value"), variable_name, parset[0].get("id"))


def get_parameter_as_read(parset, nsmap, lib, parameter_name):
    """The sign and the value of a parameter as Dynawo reads it: a ``BOOL`` one is ``true`` or
    ``false``, however it is written."""
    sign, variable_name, element = _find(parset, nsmap, lib, parameter_name)
    if element is None:
        return sign, None
    value = element.get("value")
    if element.get("type") == "BOOL":
        value = str(dynawo_boolean(value, variable_name, parset[0].get("id"))).lower()
    return sign, value
