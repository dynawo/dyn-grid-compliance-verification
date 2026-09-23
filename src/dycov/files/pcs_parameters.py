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

from pathlib import Path

from lxml import etree

from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.files import model_parameters
from dycov.model.parameters import (
    LoadParams,
    Terminal,
)

"""Reading of the equipment the PCS itself declares in its DYD/PAR."""


def get_pcs_generators_params(pcs_dyd: Path, pcs_par: Path) -> list:
    """Gets the generators parameters of the pcs model.

    Parameters
    ----------
    pcs_dyd: Path
        Path to the pcs DYD file
    pcs_par: Path
        Path to the pcs PAR file

    Returns
    -------
    list
        Generators parameters of the pcs model
    """
    pcs_dyd_tree = etree.parse(pcs_dyd, etree.XMLParser(remove_blank_text=True))
    pcs_dyd_root = pcs_dyd_tree.getroot()

    pcs_par_tree = etree.parse(pcs_par, etree.XMLParser(remove_blank_text=True))
    pcs_par_root = pcs_par_tree.getroot()

    generators = []
    allowed_sync_models = dynawo_translator.get_synchronous_machine_models()
    allowed_park_models = dynawo_translator.get_power_park_models()
    allowed_storage_models = dynawo_translator.get_storage_models()

    all_allowed_models = allowed_sync_models + allowed_park_models + allowed_storage_models

    for model_parameter in model_parameters.get_allowed_models(pcs_dyd_root, all_allowed_models):
        model_parameters.append_generator(
            pcs_dyd_root, pcs_par_root, model_parameter, generators, None
        )
    return generators


def get_pcs_load_params(pcs_dyd: Path, pcs_par: Path) -> list:
    """Gets the load parameters of the pcs model.

    Parameters
    ----------
    pcs_dyd: Path
        Path to the pcs DYD file
    pcs_par: Path
        Path to the pcs PAR file

    Returns
    -------
    list
        Load parameters of the pcs model
    """
    pcs_dyd_tree = etree.parse(pcs_dyd, etree.XMLParser(remove_blank_text=True))
    pcs_dyd_root = pcs_dyd_tree.getroot()

    pcs_par_tree = etree.parse(pcs_par, etree.XMLParser(remove_blank_text=True))
    pcs_par_root = pcs_par_tree.getroot()

    loads = model_parameters.get_load_values(pcs_dyd_root, pcs_par_root)
    return loads


def get_grid_load(loads: list) -> LoadParams:
    """Gets the Equivalent load parameters.

    Parameters
    ----------
    loads: list
        A list of load parameters

    Returns
    -------
    LoadParams
        An equivalent load parameters
    """
    if len(loads) == 0:
        return None

    ppu = 0
    qpu = 0
    for load in loads:
        ppu += load.p0
        qpu += load.q0

    return LoadParams(
        id=None,
        lib=None,
        p=ppu,
        q=qpu,
        u=None,
        u_phase=None,
        alpha=None,
        beta=None,
        par_id=None,
        terminals=(Terminal(connected_equipment=None),),
    )


def get_pcs_lines_params(pcs_dyd: Path, pcs_par: Path, line_rpu: float, line_xpu: float) -> list:
    """Gets the line parameters of the pcs model.

    Parameters
    ----------
    pcs_dyd: Path
        Path to the pcs DYD file
    pcs_par: Path
        Path to the pcs PAR file
    line_rpu: float
        Line resistance value
    line_xpu: float
        Line reactance value

    Returns
    -------
    list
        Line parameters of the pcs model
    """
    pcs_dyd_tree = etree.parse(pcs_dyd, etree.XMLParser(remove_blank_text=True))
    pcs_dyd_root = pcs_dyd_tree.getroot()

    pcs_par_tree = etree.parse(pcs_par, etree.XMLParser(remove_blank_text=True))
    pcs_par_root = pcs_par_tree.getroot()

    lines = model_parameters.get_line_values(pcs_dyd_root, pcs_par_root, line_rpu, line_xpu)

    return lines
