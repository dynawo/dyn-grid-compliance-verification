#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from pathlib import Path

from lxml import etree

from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.logging.logging import dycov_logging

PERFORMANCE_SM = 1
PERFORMANCE_PPM = 2
PERFORMANCE_BESS = 3

VALIDATION_PPM = 11
VALIDATION_BESS = 12

BUS_DYNAMIC_MODEL = "BUS_DYNAMIC_MODEL"
SM_DYNAMIC_MODEL = "SM_DYNAMIC_MODEL"
PPM_DYNAMIC_MODEL = "PPM_DYNAMIC_MODEL"
BESS_DYNAMIC_MODEL = "BESS_DYNAMIC_MODEL"
LINE_DYNAMIC_MODEL = "LINE_DYNAMIC_MODEL"
LOAD_DYNAMIC_MODEL = "LOAD_DYNAMIC_MODEL"
XFMR_DYNAMIC_MODEL = "XFMR_DYNAMIC_MODEL"

PDR_ID = "BusPDR"
INT_LINE_ID = "IntNetwork_Line"
MAIN_XFMR_ID = "Main_Xfmr"
INT_BUS_ID = "Int_Bus"
XFMR_AUX_ID = "AuxLoad_Xfmr"
AUX_ID = "Aux_Load"
XFMR_ID = "StepUp_Xfmr"
SM_ID = "Synch_Gen"
PPM_ID = "Power_Park"
XFMR1_ID = "StepUp_Xfmr_1"
PPM1_ID = "Power_Park_1"
XFMR2_ID = "StepUp_Xfmr_2"
PPM2_ID = "Power_Park_2"
BESS_ID = "Storage"
BESS1_ID = "Storage_1"
BESS2_ID = "Storage_2"
MEASUREMENTS_ID = "Measurements"

SM_TERMINAL = "generator_terminal"
PPM_TERMINAL = "PPM_TERMINAL"
BESS_TERMINAL = "BESS_terminal"
BUS_TERMINAL = "bus_terminal"
LOAD_TERMINAL = "load_terminal"
XFMR_TERMINAL1 = "transformer_terminal1"
XFMR_TERMINAL2 = "transformer_terminal2"
LINE_TERMINAL1 = "line_terminal1"
LINE_TERMINAL2 = "line_terminal2"
MEASUREMENTS_TERMINAL1 = "Measurements_terminal1"
MEASUREMENTS_TERMINAL2 = "Measurements_terminal2"

PLACEHOLDER_MODELS = [
    BUS_DYNAMIC_MODEL,
    SM_DYNAMIC_MODEL,
    PPM_DYNAMIC_MODEL,
    BESS_DYNAMIC_MODEL,
    LINE_DYNAMIC_MODEL,
    LOAD_DYNAMIC_MODEL,
    XFMR_DYNAMIC_MODEL,
]

PLACEHOLDER_TERMINALS = [PPM_TERMINAL]


def _add_terminal_options(dyd_root: etree.Element, terminal: str):
    if terminal != PPM_TERMINAL:
        return

    available_models = [
        "WPP_terminal",
        "WT_terminal",
        "WTG4A_terminal",
        "WTG4B_terminal",
        "WT4A_terminal",
        "WT4B_terminal",
        "photovoltaics_terminal",
    ]
    dyd_root.append(
        etree.Comment(
            f"Replace the placeholder: '{PPM_TERMINAL}', available_options: {available_models}"
        )
    )


def _add_lib_options(dyd_root: etree.Element, lib: str, is_model_validation: bool = False):
    if lib == BUS_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_bus_models()
    elif lib == SM_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_synchronous_machine_models()
    elif lib == PPM_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_power_park_models()
    elif lib == BESS_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_storage_models()
    elif lib == LINE_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_line_models()
    elif lib == LOAD_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_load_models()
    elif lib == XFMR_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_transformer_models()
    dyd_root.append(
        etree.Comment(f"Replace the placeholder: '{lib}', available_options: {available_models}")
    )
    if is_model_validation:
        dyd_root.append(
            etree.Comment(
                "For model validation it is essential to use the same dynamic model family in "
                "zone1 and Zone3"
            )
        )


def _add_blackbox(
    dyd_root: etree.Element,
    ns: str,
    id: str,
    lib: str,
    par_filename: str,
    par_id: str,
    show_comment: bool = False,
):
    if show_comment and lib in PLACEHOLDER_MODELS:
        _add_lib_options(dyd_root, lib)

    etree.SubElement(
        dyd_root,
        f"{{{ns}}}blackBoxModel",
        id=id,
        lib=lib,
        parFile=par_filename,
        parId=par_id,
    )


def _add_measurements_blackbox(dyd_root, ns):

    dyd_root.append(
        etree.Comment(
            '"Measurements" is a pseudo-model acting as an ammeter (allows extracting measures of '
            "currents and PQ flows traversing it). \n"
            "       Here it is needed in order to channel the flows coming from all branches to "
            "the BusPDR into a single element,\n"
            "       thus allowing the connection of PQ flow values taken at the external PCC to "
            "those generating units that control P or Q at the PCC point."
        )
    )

    etree.SubElement(
        dyd_root,
        f"{{{ns}}}blackBoxModel",
        id=MEASUREMENTS_ID,
        lib="Measurements",
    )


def _add_connection(
    dyd_root: etree.Element,
    ns: str,
    id_from: str,
    var_from: str,
    id_to: str,
    var_to: str,
    show_comment: bool = False,
):
    if show_comment:
        if var_from in PLACEHOLDER_TERMINALS:
            _add_terminal_options(dyd_root, var_from)
        elif var_to in PLACEHOLDER_TERMINALS:
            _add_terminal_options(dyd_root, var_to)

    print(f"etree.SubElement connection {id_from=}, {var_from=}, {id_to=}, {var_to=}")
    new_elem = etree.SubElement(
        dyd_root,
        f"{{{ns}}}connect",
        id1=id_from,
        var1=var_from,
        id2=id_to,
        var2=var_to,
    )
    xml_str = etree.tostring(new_elem, pretty_print=True).decode()
    print(xml_str)


def _add_measurements_connection_comment(dyd_root: etree.Element):
    dyd_root.append(
        etree.Comment(
            "Variables measurements_PPu & measurements_QPu (which are the controlled magnitudes "
            "when the Plant controls at the PCC point) \n"
            "       are on terminal1, so it is necessary to connect terminal1 to the BusPDR"
        )
    )


def _create_s_topology(dyd_root: etree.Element, ns: str, validation_type: int, par_filename: str):
    if validation_type == PERFORMANCE_SM:
        gen_id = SM_ID
        gen_lib = SM_DYNAMIC_MODEL
        gen_terminal = SM_TERMINAL
    elif validation_type == PERFORMANCE_PPM or validation_type == VALIDATION_PPM:
        gen_id = PPM_ID
        gen_lib = PPM_DYNAMIC_MODEL
        gen_terminal = PPM_TERMINAL
    else:
        gen_id = BESS_ID
        gen_lib = BESS_DYNAMIC_MODEL
        gen_terminal = BESS_TERMINAL
    _add_blackbox(dyd_root, ns, XFMR_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_ID, True)
    _add_blackbox(dyd_root, ns, gen_id, gen_lib, par_filename, gen_id, True)
    _add_measurements_blackbox(dyd_root, ns)
    _add_measurements_connection_comment(dyd_root)
    _add_connection(dyd_root, ns, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR_ID, XFMR_TERMINAL2, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL2)
    _add_connection(dyd_root, ns, gen_id, gen_terminal, XFMR_ID, XFMR_TERMINAL1, True)


def _create_saux_topology(
    dyd_root: etree.Element, ns: str, validation_type: int, par_filename: str
):
    if validation_type == PERFORMANCE_SM:
        gen_id = SM_ID
        gen_lib = SM_DYNAMIC_MODEL
        gen_terminal = SM_TERMINAL
    elif validation_type == PERFORMANCE_PPM or validation_type == VALIDATION_PPM:
        gen_id = PPM_ID
        gen_lib = PPM_DYNAMIC_MODEL
        gen_terminal = PPM_TERMINAL
    else:
        gen_id = BESS_ID
        gen_lib = BESS_DYNAMIC_MODEL
        gen_terminal = BESS_TERMINAL
    _add_blackbox(dyd_root, ns, XFMR_AUX_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_AUX_ID, True)
    _add_blackbox(dyd_root, ns, AUX_ID, LOAD_DYNAMIC_MODEL, par_filename, AUX_ID, True)
    _add_blackbox(dyd_root, ns, XFMR_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_ID)
    _add_blackbox(dyd_root, ns, gen_id, gen_lib, par_filename, gen_id, True)
    _add_measurements_blackbox(dyd_root, ns)
    _add_measurements_connection_comment(dyd_root)
    _add_connection(dyd_root, ns, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(
        dyd_root, ns, XFMR_AUX_ID, XFMR_TERMINAL2, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL2
    )
    _add_connection(dyd_root, ns, XFMR_ID, XFMR_TERMINAL2, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL2)
    _add_connection(dyd_root, ns, AUX_ID, LOAD_TERMINAL, XFMR_AUX_ID, XFMR_TERMINAL1)
    _add_connection(dyd_root, ns, gen_id, gen_terminal, XFMR_ID, XFMR_TERMINAL1, True)


def _create_si_topology(dyd_root: etree.Element, ns: str, validation_type: int, par_filename: str):
    if validation_type == PERFORMANCE_SM:
        gen_id = SM_ID
        gen_lib = SM_DYNAMIC_MODEL
        gen_terminal = SM_TERMINAL
    elif validation_type == PERFORMANCE_PPM or validation_type == VALIDATION_PPM:
        gen_id = PPM_ID
        gen_lib = PPM_DYNAMIC_MODEL
        gen_terminal = PPM_TERMINAL
    else:
        gen_id = BESS_ID
        gen_lib = BESS_DYNAMIC_MODEL
        gen_terminal = BESS_TERMINAL
    _add_blackbox(dyd_root, ns, INT_LINE_ID, LINE_DYNAMIC_MODEL, par_filename, INT_LINE_ID, True)
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, par_filename, INT_BUS_ID, True)
    _add_blackbox(dyd_root, ns, XFMR_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_ID, True)
    _add_blackbox(dyd_root, ns, gen_id, gen_lib, par_filename, gen_id, True)
    _add_measurements_blackbox(dyd_root, ns)
    _add_measurements_connection_comment(dyd_root)
    _add_connection(dyd_root, ns, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(
        dyd_root, ns, INT_LINE_ID, LINE_TERMINAL2, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL2
    )
    _add_connection(dyd_root, ns, INT_BUS_ID, BUS_TERMINAL, INT_LINE_ID, LINE_TERMINAL1)
    _add_connection(dyd_root, ns, XFMR_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, gen_id, gen_terminal, XFMR_ID, XFMR_TERMINAL1, True)


def _create_sauxi_topology(
    dyd_root: etree.Element, ns: str, validation_type: int, par_filename: str
):
    if validation_type == PERFORMANCE_SM:
        gen_id = SM_ID
        gen_lib = SM_DYNAMIC_MODEL
        gen_terminal = SM_TERMINAL
    elif validation_type == PERFORMANCE_PPM or validation_type == VALIDATION_PPM:
        gen_id = PPM_ID
        gen_lib = PPM_DYNAMIC_MODEL
        gen_terminal = PPM_TERMINAL
    else:
        gen_id = BESS_ID
        gen_lib = BESS_DYNAMIC_MODEL
        gen_terminal = BESS_TERMINAL
    _add_blackbox(dyd_root, ns, INT_LINE_ID, LINE_DYNAMIC_MODEL, par_filename, INT_LINE_ID, True)
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, par_filename, INT_BUS_ID, True)
    _add_blackbox(dyd_root, ns, XFMR_AUX_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_AUX_ID, True)
    _add_blackbox(dyd_root, ns, AUX_ID, LOAD_DYNAMIC_MODEL, par_filename, AUX_ID, True)
    _add_blackbox(dyd_root, ns, XFMR_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_ID)
    _add_blackbox(dyd_root, ns, gen_id, gen_lib, par_filename, gen_id, True)
    _add_measurements_blackbox(dyd_root, ns)
    _add_measurements_connection_comment(dyd_root)
    _add_connection(dyd_root, ns, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(
        dyd_root, ns, INT_LINE_ID, LINE_TERMINAL2, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL2
    )
    _add_connection(dyd_root, ns, INT_BUS_ID, BUS_TERMINAL, INT_LINE_ID, LINE_TERMINAL1)
    _add_connection(dyd_root, ns, XFMR_AUX_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, AUX_ID, LOAD_TERMINAL, XFMR_AUX_ID, XFMR_TERMINAL1)
    _add_connection(dyd_root, ns, gen_id, gen_terminal, XFMR_ID, XFMR_TERMINAL1, True)


def _create_m_topology(dyd_root: etree.Element, ns: str, validation_type: int, par_filename: str):
    if validation_type == PERFORMANCE_PPM or validation_type == VALIDATION_PPM:
        gen1_id = PPM1_ID
        gen2_id = PPM2_ID
        gen_lib = PPM_DYNAMIC_MODEL
        gen_terminal = PPM_TERMINAL
    else:
        gen1_id = BESS1_ID
        gen2_id = BESS2_ID
        gen_lib = BESS_DYNAMIC_MODEL
        gen_terminal = BESS_TERMINAL
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, par_filename, INT_BUS_ID, True)
    _add_blackbox(dyd_root, ns, MAIN_XFMR_ID, XFMR_DYNAMIC_MODEL, par_filename, MAIN_XFMR_ID, True)
    _add_blackbox(dyd_root, ns, XFMR1_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR1_ID)
    _add_blackbox(dyd_root, ns, gen1_id, gen_lib, par_filename, gen1_id, True)
    _add_blackbox(dyd_root, ns, XFMR2_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR2_ID)
    _add_blackbox(dyd_root, ns, gen2_id, gen_lib, par_filename, gen2_id)
    _add_measurements_blackbox(dyd_root, ns)
    _add_measurements_connection_comment(dyd_root)
    _add_connection(dyd_root, ns, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(
        dyd_root, ns, MAIN_XFMR_ID, XFMR_TERMINAL2, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL2
    )
    _add_connection(dyd_root, ns, INT_BUS_ID, BUS_TERMINAL, MAIN_XFMR_ID, XFMR_TERMINAL1)
    _add_connection(dyd_root, ns, XFMR1_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR2_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, gen1_id, gen_terminal, XFMR1_ID, XFMR_TERMINAL1, True)
    _add_connection(dyd_root, ns, gen2_id, gen_terminal, XFMR2_ID, XFMR_TERMINAL1)


def _create_maux_topology(
    dyd_root: etree.Element, ns: str, validation_type: int, par_filename: str
):
    if validation_type == PERFORMANCE_PPM or validation_type == VALIDATION_PPM:
        gen1_id = PPM1_ID
        gen2_id = PPM2_ID
        gen_lib = PPM_DYNAMIC_MODEL
        gen_terminal = PPM_TERMINAL
    else:
        gen1_id = BESS1_ID
        gen2_id = BESS2_ID
        gen_lib = BESS_DYNAMIC_MODEL
        gen_terminal = BESS_TERMINAL
    _add_blackbox(dyd_root, ns, MAIN_XFMR_ID, XFMR_DYNAMIC_MODEL, par_filename, MAIN_XFMR_ID, True)
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, par_filename, INT_BUS_ID, True)
    _add_blackbox(dyd_root, ns, XFMR_AUX_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_AUX_ID)
    _add_blackbox(dyd_root, ns, AUX_ID, LOAD_DYNAMIC_MODEL, par_filename, AUX_ID, True)
    _add_blackbox(dyd_root, ns, XFMR1_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR1_ID)
    _add_blackbox(dyd_root, ns, gen1_id, gen_lib, par_filename, gen1_id, True)
    _add_blackbox(dyd_root, ns, XFMR2_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR2_ID)
    _add_blackbox(dyd_root, ns, gen2_id, gen_lib, par_filename, gen2_id)
    _add_measurements_blackbox(dyd_root, ns)
    _add_measurements_connection_comment(dyd_root)
    _add_connection(dyd_root, ns, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(
        dyd_root, ns, MAIN_XFMR_ID, XFMR_TERMINAL2, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL2
    )
    _add_connection(dyd_root, ns, INT_BUS_ID, BUS_TERMINAL, MAIN_XFMR_ID, XFMR_TERMINAL1)
    _add_connection(dyd_root, ns, XFMR_AUX_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR1_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR2_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, AUX_ID, LOAD_TERMINAL, XFMR_AUX_ID, XFMR_TERMINAL1)
    _add_connection(dyd_root, ns, gen1_id, gen_terminal, XFMR1_ID, XFMR_TERMINAL1, True)
    _add_connection(dyd_root, ns, gen2_id, gen_terminal, XFMR2_ID, XFMR_TERMINAL1)


def _create_mi_topology(dyd_root: etree.Element, ns: str, validation_type: int, par_filename: str):
    if validation_type == PERFORMANCE_PPM or validation_type == VALIDATION_PPM:
        gen1_id = PPM1_ID
        gen2_id = PPM2_ID
        gen_lib = PPM_DYNAMIC_MODEL
        gen_terminal = PPM_TERMINAL
    else:
        gen1_id = BESS1_ID
        gen2_id = BESS2_ID
        gen_lib = BESS_DYNAMIC_MODEL
        gen_terminal = BESS_TERMINAL
    _add_blackbox(dyd_root, ns, INT_LINE_ID, LINE_DYNAMIC_MODEL, par_filename, INT_LINE_ID, True)
    _add_blackbox(dyd_root, ns, MAIN_XFMR_ID, XFMR_DYNAMIC_MODEL, par_filename, MAIN_XFMR_ID, True)
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, par_filename, INT_BUS_ID, True)
    _add_blackbox(dyd_root, ns, XFMR1_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR1_ID)
    _add_blackbox(dyd_root, ns, gen1_id, gen_lib, par_filename, gen1_id, True)
    _add_blackbox(dyd_root, ns, XFMR2_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR2_ID)
    _add_blackbox(dyd_root, ns, gen2_id, gen_lib, par_filename, gen2_id)
    _add_measurements_blackbox(dyd_root, ns)
    _add_measurements_connection_comment(dyd_root)
    _add_connection(dyd_root, ns, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(
        dyd_root, ns, INT_LINE_ID, LINE_TERMINAL2, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL2
    )
    _add_connection(dyd_root, ns, MAIN_XFMR_ID, XFMR_TERMINAL2, INT_LINE_ID, LINE_TERMINAL1)
    _add_connection(dyd_root, ns, INT_BUS_ID, BUS_TERMINAL, MAIN_XFMR_ID, XFMR_TERMINAL1)
    _add_connection(dyd_root, ns, XFMR1_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR2_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, gen1_id, gen_terminal, XFMR1_ID, XFMR_TERMINAL1, True)
    _add_connection(dyd_root, ns, gen2_id, gen_terminal, XFMR2_ID, XFMR_TERMINAL1)


def _create_mauxi_topology(
    dyd_root: etree.Element, ns: str, validation_type: int, par_filename: str
):
    if validation_type == PERFORMANCE_PPM or validation_type == VALIDATION_PPM:
        gen1_id = PPM1_ID
        gen2_id = PPM2_ID
        gen_lib = PPM_DYNAMIC_MODEL
        gen_terminal = PPM_TERMINAL
    else:
        gen1_id = BESS1_ID
        gen2_id = BESS2_ID
        gen_lib = BESS_DYNAMIC_MODEL
        gen_terminal = BESS_TERMINAL
    _add_blackbox(dyd_root, ns, INT_LINE_ID, LINE_DYNAMIC_MODEL, par_filename, INT_LINE_ID, True)
    _add_blackbox(dyd_root, ns, MAIN_XFMR_ID, XFMR_DYNAMIC_MODEL, par_filename, MAIN_XFMR_ID, True)
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, par_filename, INT_BUS_ID, True)
    _add_blackbox(dyd_root, ns, XFMR_AUX_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR_AUX_ID)
    _add_blackbox(dyd_root, ns, AUX_ID, LOAD_DYNAMIC_MODEL, par_filename, AUX_ID, True)
    _add_blackbox(dyd_root, ns, XFMR1_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR1_ID)
    _add_blackbox(dyd_root, ns, gen1_id, gen_lib, par_filename, gen1_id, True)
    _add_blackbox(dyd_root, ns, XFMR2_ID, XFMR_DYNAMIC_MODEL, par_filename, XFMR2_ID)
    _add_blackbox(dyd_root, ns, gen2_id, gen_lib, par_filename, gen2_id)
    _add_measurements_blackbox(dyd_root, ns)
    _add_measurements_connection_comment(dyd_root)
    _add_connection(dyd_root, ns, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(
        dyd_root, ns, INT_LINE_ID, LINE_TERMINAL2, MEASUREMENTS_ID, MEASUREMENTS_TERMINAL2
    )
    _add_connection(dyd_root, ns, MAIN_XFMR_ID, XFMR_TERMINAL2, INT_LINE_ID, LINE_TERMINAL1)
    _add_connection(dyd_root, ns, INT_BUS_ID, BUS_TERMINAL, MAIN_XFMR_ID, XFMR_TERMINAL1)
    _add_connection(dyd_root, ns, XFMR_AUX_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR1_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR2_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, AUX_ID, LOAD_TERMINAL, XFMR_AUX_ID, XFMR_TERMINAL1)
    _add_connection(dyd_root, ns, gen1_id, gen_terminal, XFMR1_ID, XFMR_TERMINAL1, True)
    _add_connection(dyd_root, ns, gen2_id, gen_terminal, XFMR2_ID, XFMR_TERMINAL1)


def _check_dynamic_models(target: Path, filename: str) -> bool:
    placeholders = (
        dynawo_translator.get_bus_models()
        + dynawo_translator.get_synchronous_machine_models()
        + dynawo_translator.get_power_park_models()
        + dynawo_translator.get_storage_models()
        + dynawo_translator.get_line_models()
        + dynawo_translator.get_load_models()
        + dynawo_translator.get_transformer_models()
        + ["Measurements"]
    )

    producer_dyd_tree = etree.parse(target / filename, etree.XMLParser(remove_blank_text=True))
    producer_dyd_root = producer_dyd_tree.getroot()

    success = True
    dyn_models = []
    ns = etree.QName(producer_dyd_root).namespace
    for bbmodel in producer_dyd_root.iterfind(f"{{{ns}}}blackBoxModel"):
        if bbmodel.get("lib") not in placeholders:
            dyn_models.append(bbmodel.get("lib"))
            success = False

    if not success:
        dycov_logging.get_logger("Create DYD input").error(
            f"The DYD file contains dynamic models that are not supported by the tool.\n"
            f"Please fix {dyn_models}."
        )
    return success


def _create_producer_dyd_file(
    target: Path,
    filename: str,
    topology: str,
    validation_type: int,
) -> None:
    if (target / "Producer.dyd").exists():
        (target / "Producer.dyd").unlink()

    ns = "http://www.rte-france.com/dynawo"
    etree.register_namespace("dyn", "http://www.rte-france.com/dynawo")
    dyd_root = etree.Element(f"{{{ns}}}dynamicModelsArchitecture")
    comment = etree.Comment(f"Topology: {topology}")
    dyd_root.append(comment)

    par_filename = filename.replace(".dyd", ".par")
    if "S".casefold() == topology.casefold():
        _create_s_topology(dyd_root, ns, validation_type, par_filename)
    elif "S+i".casefold() == topology.casefold():
        _create_si_topology(dyd_root, ns, validation_type, par_filename)
    elif "S+Aux".casefold() == topology.casefold():
        _create_saux_topology(dyd_root, ns, validation_type, par_filename)
    elif "S+Aux+i".casefold() == topology.casefold():
        _create_sauxi_topology(dyd_root, ns, validation_type, par_filename)
    elif "M".casefold() == topology.casefold():
        _create_m_topology(dyd_root, ns, validation_type, par_filename)
    elif "M+i".casefold() == topology.casefold():
        _create_mi_topology(dyd_root, ns, validation_type, par_filename)
    elif "M+Aux".casefold() == topology.casefold():
        _create_maux_topology(dyd_root, ns, validation_type, par_filename)
    elif "M+Aux+i".casefold() == topology.casefold():
        _create_mauxi_topology(dyd_root, ns, validation_type, par_filename)
    else:
        raise ValueError(
            "Select one of the 8 available topologies:\n"
            "  - S\n"
            "  - S+i\n"
            "  - S+Aux\n"
            "  - S+Aux+i\n"
            "  - M\n"
            "  - M+i\n"
            "  - M+Aux\n"
            "  - M+Aux+i\n"
        )

    dyd_tree = etree.ElementTree(
        etree.fromstring(etree.tostring(dyd_root), etree.XMLParser(remove_blank_text=True))
    )
    xml_str = etree.tostring(dyd_tree, pretty_print=True).decode()
    print(xml_str)
    dyd_tree.write(target / filename, encoding="utf-8", pretty_print=True, xml_declaration=True)


def create_producer_dyd_file(
    target: Path,
    topology: str,
    template: str,
) -> None:
    """Create a DYD file in target path with the selected topology.

    Parameters
    ----------
    target: Path
        Target path
    topology: str
        Topology to the DYD file
    template: str
        Input template name:
        * 'performance_SM' if it is electrical performance for Synchronous Machine Model
        * 'performance_PPM' if it is electrical performance for Power Park Module Model
        * 'performance_BESS' if it is electrical performance for Storage Model
        * 'model_PPM' if it is model validation for Power Park Module Model
        * 'model_BESS' if it is model validation for Storage Model
    """
    if template.startswith("performance"):
        validation_type = PERFORMANCE_SM
        if template == "performance_PPM":
            validation_type = PERFORMANCE_PPM
        elif template == "performance_BESS":
            validation_type = PERFORMANCE_BESS
        _create_producer_dyd_file(target, "Producer.dyd", topology, validation_type)

    elif template.startswith("model"):
        validation_type = VALIDATION_PPM
        if template == "model_BESS":
            validation_type = VALIDATION_BESS
        if topology.casefold().startswith("m"):
            _create_producer_dyd_file(target / "Zone1", "Producer_G1.dyd", "S", validation_type)
            _create_producer_dyd_file(target / "Zone1", "Producer_G2.dyd", "S", validation_type)
        else:
            _create_producer_dyd_file(target / "Zone1", "Producer.dyd", "S", validation_type)
        _create_producer_dyd_file(target / "Zone3", "Producer.dyd", topology, validation_type)

    else:
        raise ValueError("Unsupported template name")


def check_dynamic_models(target: Path, template: str) -> bool:
    """Find placeholders in the DYD file .

    Parameters
    ----------
    target: Path
        Target path
    template: str
        Input template name:
        * 'performance_SM' if it is electrical performance for Synchronous Machine Model
        * 'performance_PPM' if it is electrical performance for Power Park Module Model
        * 'performance_BESS' if it is electrical performance for Storage Model
        * 'model_PPM' if it is model validation for Power Park Module Model
        * 'model_BESS' if it is model validation for Storage Model

    Returns
    -------
    bool
        True if there are placeholders in the DYD file
    """

    if template.startswith("model"):
        dyd_files = list((target / "Zone1").glob("*.[dD][yY][dD]"))
        for dyd_file in dyd_files:
            if not _check_dynamic_models(target / "Zone1", dyd_file.name):
                return False
        check_zone3 = _check_dynamic_models(target / "Zone3", "Producer.dyd")
        return check_zone3
    else:
        return _check_dynamic_models(target, "Producer.dyd")
