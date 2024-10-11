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

from dgcv.dynawo.translator import dynawo_translator
from dgcv.logging.logging import dgcv_logging

PAR_FILE = "Producer.par"

BUS_DYNAMIC_MODEL = "BUS_DYNAMIC_MODEL"
SM_DYNAMIC_MODEL = "SM_DYNAMIC_MODEL"
PPM_DYNAMIC_MODEL = "PPM_DYNAMIC_MODEL"
LINE_DYNAMIC_MODEL = "LINE_DYNAMIC_MODEL"
LOAD_DYNAMIC_MODEL = "LOAD_DYNAMIC_MODEL"
XFMR_DYNAMIC_MODEL = "XFMR_DYNAMIC_MODEL"

PDR_ID = "BusPDR"
INT_LINE_ID = "IntNetwork_Line"
PPM_XFMR_ID = "PPM_Xfmr"
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

BUS_TERMINAL = "bus_terminal"
LOAD_TERMINAL = "load_terminal"
GENERATOR_TERMINAL = "generator_terminal"
XFMR_TERMINAL1 = "transformer_terminal1"
XFMR_TERMINAL2 = "transformer_terminal2"
LINE_TERMINAL1 = "line_terminal1"
LINE_TERMINAL2 = "line_terminal2"


def _add_lib_options(dyd_root: etree.Element, lib: str, is_model_validation: bool = False):
    if lib == BUS_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_bus_models()
    elif lib == SM_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_synchronous_machine_models()
    elif lib == PPM_DYNAMIC_MODEL:
        available_models = dynawo_translator.get_power_park_models()
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


def _add_placeholders_comments(
    dyd_root: etree.Element, topology: str, is_performance_sm: bool, is_model_validation: bool
):
    _add_lib_options(dyd_root, XFMR_DYNAMIC_MODEL)
    if is_performance_sm:
        _add_lib_options(dyd_root, SM_DYNAMIC_MODEL)
    else:
        _add_lib_options(dyd_root, PPM_DYNAMIC_MODEL, is_model_validation)
    if topology.startswith("M") or topology.endswith("+i"):
        _add_lib_options(dyd_root, BUS_DYNAMIC_MODEL)
    if topology.endswith("+i"):
        _add_lib_options(dyd_root, LINE_DYNAMIC_MODEL)
    if "+Aux" in topology:
        _add_lib_options(dyd_root, LOAD_DYNAMIC_MODEL)


def _add_blackbox(dyd_root: etree.Element, ns: str, id: str, lib: str, par_file: str, par_id: str):
    etree.SubElement(
        dyd_root,
        f"{{{ns}}}blackBoxModel",
        id=id,
        lib=lib,
        parFile=par_file,
        parId=par_id,
    )


def _add_connection(dyd_root: etree.Element, ns: str, id1: str, var1: str, id2: str, var2: str):
    etree.SubElement(
        dyd_root,
        f"{{{ns}}}connect",
        id1=id1,
        var1=var1,
        id2=id2,
        var2=var2,
    )


def _create_s_topology(dyd_root: etree.Element, ns: str, is_performance_sm: bool):
    if is_performance_sm:
        gen_id = SM_ID
        gen_lib = SM_DYNAMIC_MODEL
    else:
        gen_id = PPM_ID
        gen_lib = PPM_DYNAMIC_MODEL
    _add_blackbox(dyd_root, ns, XFMR_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR_ID)
    _add_blackbox(dyd_root, ns, gen_id, gen_lib, PAR_FILE, gen_id)
    _add_connection(dyd_root, ns, XFMR_ID, XFMR_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, gen_id, GENERATOR_TERMINAL, XFMR_ID, XFMR_TERMINAL2)


def _create_saux_topology(dyd_root: etree.Element, ns: str, is_performance_sm: bool):
    if is_performance_sm:
        gen_id = SM_ID
        gen_lib = SM_DYNAMIC_MODEL
    else:
        gen_id = PPM_ID
        gen_lib = PPM_DYNAMIC_MODEL
    _add_blackbox(dyd_root, ns, XFMR_AUX_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR_AUX_ID)
    _add_blackbox(dyd_root, ns, AUX_ID, LOAD_DYNAMIC_MODEL, PAR_FILE, AUX_ID)
    _add_blackbox(dyd_root, ns, XFMR_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR_ID)
    _add_blackbox(dyd_root, ns, gen_id, gen_lib, PAR_FILE, gen_id)
    _add_connection(dyd_root, ns, XFMR_AUX_ID, XFMR_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR_ID, XFMR_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, AUX_ID, LOAD_TERMINAL, XFMR_AUX_ID, XFMR_TERMINAL2)
    _add_connection(dyd_root, ns, gen_id, GENERATOR_TERMINAL, XFMR_ID, XFMR_TERMINAL2)


def _create_si_topology(dyd_root: etree.Element, ns: str, is_performance_sm: bool):
    if is_performance_sm:
        gen_id = SM_ID
        gen_lib = SM_DYNAMIC_MODEL
    else:
        gen_id = PPM_ID
        gen_lib = PPM_DYNAMIC_MODEL
    _add_blackbox(dyd_root, ns, INT_LINE_ID, LINE_DYNAMIC_MODEL, PAR_FILE, INT_LINE_ID)
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, PAR_FILE, INT_BUS_ID)
    _add_blackbox(dyd_root, ns, XFMR_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR_ID)
    _add_blackbox(dyd_root, ns, gen_id, gen_lib, PAR_FILE, gen_id)
    _add_connection(dyd_root, ns, INT_LINE_ID, LINE_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, INT_LINE_ID, LINE_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR_ID, XFMR_TERMINAL1, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, gen_id, GENERATOR_TERMINAL, XFMR_ID, XFMR_TERMINAL2)


def _create_sauxi_topology(dyd_root: etree.Element, ns: str, is_performance_sm: bool):
    if is_performance_sm:
        gen_id = SM_ID
        gen_lib = SM_DYNAMIC_MODEL
    else:
        gen_id = PPM_ID
        gen_lib = PPM_DYNAMIC_MODEL
    _add_blackbox(dyd_root, ns, INT_LINE_ID, LINE_DYNAMIC_MODEL, PAR_FILE, INT_LINE_ID)
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, PAR_FILE, INT_BUS_ID)
    _add_blackbox(dyd_root, ns, XFMR_AUX_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR_AUX_ID)
    _add_blackbox(dyd_root, ns, AUX_ID, LOAD_DYNAMIC_MODEL, PAR_FILE, AUX_ID)
    _add_blackbox(dyd_root, ns, XFMR_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR_ID)
    _add_blackbox(dyd_root, ns, gen_id, gen_lib, PAR_FILE, gen_id)
    _add_connection(dyd_root, ns, INT_LINE_ID, LINE_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, INT_LINE_ID, LINE_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR_AUX_ID, XFMR_TERMINAL1, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR_ID, XFMR_TERMINAL1, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, AUX_ID, LOAD_TERMINAL, XFMR_AUX_ID, XFMR_TERMINAL2)
    _add_connection(dyd_root, ns, gen_id, GENERATOR_TERMINAL, XFMR_ID, XFMR_TERMINAL2)


def _create_m_topology(dyd_root: etree.Element, ns: str):
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, PAR_FILE, INT_BUS_ID)
    _add_blackbox(dyd_root, ns, PPM_XFMR_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, PPM_XFMR_ID)
    _add_blackbox(dyd_root, ns, XFMR1_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR1_ID)
    _add_blackbox(dyd_root, ns, PPM1_ID, PPM_DYNAMIC_MODEL, PAR_FILE, PPM1_ID)
    _add_blackbox(dyd_root, ns, XFMR2_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR2_ID)
    _add_blackbox(dyd_root, ns, PPM2_ID, PPM_DYNAMIC_MODEL, PAR_FILE, PPM2_ID)
    _add_connection(dyd_root, ns, PPM_XFMR_ID, XFMR_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, PPM_XFMR_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR1_ID, XFMR_TERMINAL1, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR2_ID, XFMR_TERMINAL1, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, PPM1_ID, GENERATOR_TERMINAL, XFMR1_ID, XFMR_TERMINAL2)
    _add_connection(dyd_root, ns, PPM2_ID, GENERATOR_TERMINAL, XFMR2_ID, XFMR_TERMINAL2)


def _create_maux_topology(dyd_root: etree.Element, ns: str):
    _add_blackbox(dyd_root, ns, PPM_XFMR_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, PPM_XFMR_ID)
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, PAR_FILE, INT_BUS_ID)
    _add_blackbox(dyd_root, ns, XFMR_AUX_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR_AUX_ID)
    _add_blackbox(dyd_root, ns, AUX_ID, LOAD_DYNAMIC_MODEL, PAR_FILE, AUX_ID)
    _add_blackbox(dyd_root, ns, XFMR1_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR1_ID)
    _add_blackbox(dyd_root, ns, PPM1_ID, PPM_DYNAMIC_MODEL, PAR_FILE, PPM1_ID)
    _add_blackbox(dyd_root, ns, XFMR2_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR2_ID)
    _add_blackbox(dyd_root, ns, PPM2_ID, PPM_DYNAMIC_MODEL, PAR_FILE, PPM2_ID)
    _add_connection(dyd_root, ns, PPM_XFMR_ID, XFMR_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, PPM_XFMR_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR_AUX_ID, XFMR_TERMINAL1, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR1_ID, XFMR_TERMINAL1, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR2_ID, XFMR_TERMINAL1, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, AUX_ID, LOAD_TERMINAL, XFMR_AUX_ID, XFMR_TERMINAL2)
    _add_connection(dyd_root, ns, PPM1_ID, GENERATOR_TERMINAL, XFMR1_ID, XFMR_TERMINAL2)
    _add_connection(dyd_root, ns, PPM2_ID, GENERATOR_TERMINAL, XFMR2_ID, XFMR_TERMINAL2)


def _create_mi_topology(dyd_root: etree.Element, ns: str):
    _add_blackbox(dyd_root, ns, INT_LINE_ID, LINE_DYNAMIC_MODEL, PAR_FILE, INT_LINE_ID)
    _add_blackbox(dyd_root, ns, PPM_XFMR_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, PPM_XFMR_ID)
    _add_blackbox(dyd_root, ns, INT_BUS_ID, BUS_DYNAMIC_MODEL, PAR_FILE, INT_BUS_ID)
    _add_blackbox(dyd_root, ns, XFMR1_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR1_ID)
    _add_blackbox(dyd_root, ns, PPM1_ID, PPM_DYNAMIC_MODEL, PAR_FILE, PPM1_ID)
    _add_blackbox(dyd_root, ns, XFMR2_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR2_ID)
    _add_blackbox(dyd_root, ns, PPM2_ID, PPM_DYNAMIC_MODEL, PAR_FILE, PPM2_ID)
    _add_connection(dyd_root, ns, INT_LINE_ID, LINE_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, INT_LINE_ID, LINE_TERMINAL2, PPM_XFMR_ID, XFMR_TERMINAL1)
    _add_connection(dyd_root, ns, PPM_XFMR_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR1_ID, XFMR_TERMINAL1, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR2_ID, XFMR_TERMINAL1, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, PPM1_ID, GENERATOR_TERMINAL, XFMR1_ID, XFMR_TERMINAL2)
    _add_connection(dyd_root, ns, PPM2_ID, GENERATOR_TERMINAL, XFMR2_ID, XFMR_TERMINAL2)


def _create_mauxi_topology(dyd_root: etree.Element, ns: str):
    _add_blackbox(dyd_root, ns, INT_LINE_ID, LINE_DYNAMIC_MODEL, PAR_FILE, INT_LINE_ID)
    _add_blackbox(dyd_root, ns, PPM_XFMR_ID, PPM_DYNAMIC_MODEL, PAR_FILE, PPM_XFMR_ID)
    _add_blackbox(dyd_root, ns, INT_BUS_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, INT_BUS_ID)
    _add_blackbox(dyd_root, ns, XFMR_AUX_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR_AUX_ID)
    _add_blackbox(dyd_root, ns, AUX_ID, LOAD_DYNAMIC_MODEL, PAR_FILE, AUX_ID)
    _add_blackbox(dyd_root, ns, XFMR1_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR1_ID)
    _add_blackbox(dyd_root, ns, PPM1_ID, PPM_DYNAMIC_MODEL, PAR_FILE, PPM1_ID)
    _add_blackbox(dyd_root, ns, XFMR2_ID, XFMR_DYNAMIC_MODEL, PAR_FILE, XFMR2_ID)
    _add_blackbox(dyd_root, ns, PPM2_ID, PPM_DYNAMIC_MODEL, PAR_FILE, PPM2_ID)
    _add_connection(dyd_root, ns, INT_LINE_ID, LINE_TERMINAL1, PDR_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, INT_LINE_ID, LINE_TERMINAL2, PPM_XFMR_ID, XFMR_TERMINAL1)
    _add_connection(dyd_root, ns, PPM_XFMR_ID, XFMR_TERMINAL2, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR_AUX_ID, XFMR_TERMINAL1, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR1_ID, XFMR_TERMINAL1, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, XFMR2_ID, XFMR_TERMINAL1, INT_BUS_ID, BUS_TERMINAL)
    _add_connection(dyd_root, ns, AUX_ID, LOAD_TERMINAL, XFMR_AUX_ID, XFMR_TERMINAL2)
    _add_connection(dyd_root, ns, PPM1_ID, GENERATOR_TERMINAL, XFMR1_ID, XFMR_TERMINAL2)
    _add_connection(dyd_root, ns, PPM2_ID, GENERATOR_TERMINAL, XFMR2_ID, XFMR_TERMINAL2)


def _check_dynamic_models(target: Path) -> bool:
    placeholders = (
        dynawo_translator.get_bus_models()
        + dynawo_translator.get_synchronous_machine_models()
        + dynawo_translator.get_power_park_models()
        + dynawo_translator.get_line_models()
        + dynawo_translator.get_load_models()
        + dynawo_translator.get_transformer_models()
    )

    producer_dyd_tree = etree.parse(
        target / "Producer.dyd", etree.XMLParser(remove_blank_text=True)
    )
    producer_dyd_root = producer_dyd_tree.getroot()

    success = True
    dyn_models = []
    ns = etree.QName(producer_dyd_root).namespace
    for bbmodel in producer_dyd_root.iterfind(f"{{{ns}}}blackBoxModel"):
        if bbmodel.get("lib") not in placeholders:
            dyn_models.append(bbmodel.get("lib"))
            success = False

    if not success:
        dgcv_logging.get_logger("Create DYD input").error(
            f"The DYD file contains dynamic models that are not supported by the tool.\n"
            f"Please fix {dyn_models}."
        )
    return success


def _create_producer_dyd_file(
    target: Path,
    topology: str,
    is_performance_sm: bool,
    is_model_validation: bool,
) -> None:
    ns = "http://www.rte-france.com/dynawo"
    etree.register_namespace("dyn", "http://www.rte-france.com/dynawo")
    dyd_root = etree.Element(f"{{{ns}}}dynamicModelsArchitecture")
    comment = etree.Comment(f"Topology: {topology}")
    dyd_root.append(comment)

    if "S".casefold() == topology.casefold():
        _create_s_topology(dyd_root, ns, is_performance_sm)
    elif "S+i".casefold() == topology.casefold():
        _create_si_topology(dyd_root, ns, is_performance_sm)
    elif "S+Aux".casefold() == topology.casefold():
        _create_saux_topology(dyd_root, ns, is_performance_sm)
    elif "S+Aux+i".casefold() == topology.casefold():
        _create_sauxi_topology(dyd_root, ns, is_performance_sm)
    elif "M".casefold() == topology.casefold():
        _create_m_topology(dyd_root, ns)
    elif "M+i".casefold() == topology.casefold():
        _create_mi_topology(dyd_root, ns)
    elif "M+Aux".casefold() == topology.casefold():
        _create_maux_topology(dyd_root, ns)
    elif "M+Aux+i".casefold() == topology.casefold():
        _create_mauxi_topology(dyd_root, ns)
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
    _add_placeholders_comments(dyd_root, topology, is_performance_sm, is_model_validation)

    dyd_tree = etree.ElementTree(
        etree.fromstring(etree.tostring(dyd_root), etree.XMLParser(remove_blank_text=True))
    )
    dyd_tree.write(
        target / "Producer.dyd", encoding="utf-8", pretty_print=True, xml_declaration=True
    )


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
        * 'model' if it is model validation
    """
    if template == "performance_SM":
        _create_producer_dyd_file(target, topology, True, False)
    elif template == "model":
        _create_producer_dyd_file(target / "Zone1", "S", False, True)
        _create_producer_dyd_file(target / "Zone3", topology, False, True)
    else:
        _create_producer_dyd_file(target, topology, False, False)


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
        * 'model' if it is model validation

    Returns
    -------
    bool
        True if there are placeholders in the DYD file
    """

    if template == "model":
        check_zone1 = _check_dynamic_models(target / "Zone1")
        check_zone3 = _check_dynamic_models(target / "Zone3")
        return check_zone1 and check_zone3
    else:
        return _check_dynamic_models(target)
