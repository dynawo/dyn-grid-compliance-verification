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

"""Low-level access to the parameter sets of a Dynawo PAR file."""


def get_parset(par_root, par_id, nsmap):
    parset = par_root.xpath(f"//ns:set[@id='{par_id}']", namespaces=nsmap)
    if not parset:
        raise ValueError(f"The parameter set with id='{par_id}' was not found")
    if len(parset) > 1:
        raise ValueError(f"Multiple parameter sets with id='{par_id}' were found")
    return parset


def get_parameter(parset, nsmap, lib, parameter_name):
    ps = parset[0]
    sign, variable_name = dynawo_translator.get_dynawo_variable(lib, parameter_name)
    if not variable_name:
        return None, None
    variable = ps.xpath(f"ns:par[@name='{variable_name}']", namespaces=nsmap)
    return (sign, variable[0].get("value")) if variable else (sign, None)
