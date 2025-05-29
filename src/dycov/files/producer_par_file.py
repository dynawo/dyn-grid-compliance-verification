#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import shutil
from pathlib import Path

from lxml import etree

from dycov.configuration.cfg import config
from dycov.files import manage_files
from dycov.logging.logging import dycov_logging


def _get_bbmodels_info(dyd_file: Path) -> dict:
    producer_dyd_tree = etree.parse(dyd_file, etree.XMLParser(remove_blank_text=True))
    producer_dyd_root = producer_dyd_tree.getroot()

    bbmodels = {}
    ns = etree.QName(producer_dyd_root).namespace
    for bbmodel in producer_dyd_root.iterfind(f"{{{ns}}}blackBoxModel"):
        bbmodels[bbmodel.get("id")] = {
            "lib": bbmodel.get("lib"),
            "parId": bbmodel.get("parId"),
        }

    return bbmodels


def _get_ddb_model_path(dynawo_command: str):
    return Path(shutil.which(dynawo_command)).parent / "ddb"


def _search_ddb_model_file(name: str, path: Path):
    file_path = path / (name + ".desc.xml")
    if file_path.exists():
        return file_path
    return None


def _get_desc_xml_params(model_desc: Path):
    desc_xml_tree = etree.parse(model_desc, etree.XMLParser(remove_blank_text=True))
    desc_xml_root = desc_xml_tree.getroot()

    params_list = []
    ns = etree.QName(desc_xml_root).namespace

    for parameter in desc_xml_root.iter(f"{{{ns}}}parameter"):
        if parameter.get("readOnly") == "false":
            params_list.append(
                {
                    "name": parameter.get("name"),
                    "type": parameter.get("valueType"),
                    "value": (
                        parameter.get("defaultValue") if "defaultValue" in parameter.attrib else ""
                    ),
                }
            )

    return sorted(
        params_list, key=lambda d: (True, d["name"]) if d["value"] != "" else (False, d["name"])
    )


def _write_params_par_file(producer_par_root: etree.Element, params_list: list, parId: str):

    xml_set = etree.SubElement(producer_par_root, "set", id=f"{parId}")
    for param in params_list:
        etree.SubElement(
            xml_set,
            "par",
            type=f"{param['type']}",
            name=f"{param['name']}",
            value=f"{param['value']}",
        )


def _create_producer_par_file(
    launcher_dwo: Path,
    target: Path,
    filename: str,
) -> None:

    ddb_dynawo_path = _get_ddb_model_path(launcher_dwo)
    ddb_local_config_path = config.get_config_dir() / "ddb"
    producer_par_root = etree.fromstring(
        """<parametersSet xmlns="http://www.rte-france.com/dynawo"></parametersSet>"""
    )

    models_dict = _get_bbmodels_info(target / filename.replace(".par", ".dyd"))
    for key, value in models_dict.items():
        if value["parId"] is None:
            continue

        model_desc = _search_ddb_model_file(value["lib"], ddb_local_config_path)
        if not model_desc:
            model_desc = _search_ddb_model_file(value["lib"], ddb_dynawo_path)
            if not model_desc:
                print("Error: " + value["lib"] + ".desc.xml file not found")
                continue

        params_list = _get_desc_xml_params(model_desc)
        _write_params_par_file(producer_par_root, params_list, value["parId"])

    producer_par_tree = etree.ElementTree(
        etree.fromstring(
            etree.tostring(producer_par_root), etree.XMLParser(remove_blank_text=True)
        )
    )
    producer_par_tree.write(
        target / filename, encoding="utf-8", pretty_print=True, xml_declaration=True
    )


def _check_parameters(target: Path, filename: str) -> bool:
    producer_par_tree = etree.parse(target / filename, etree.XMLParser(remove_blank_text=True))
    producer_par_root = producer_par_tree.getroot()

    success = True
    empty_values = []
    ns = etree.QName(producer_par_root).namespace
    for parameters_set in producer_par_root.iterfind(f"{{{ns}}}set"):
        for parameter in parameters_set.iterfind(f"{{{ns}}}par"):
            if parameter.get("value") == "":
                empty_values.append(parameter.get("name"))
                success = False

    if not success:
        dycov_logging.get_logger("Create PAR input").error(
            f"The PAR file contains parameters without value.\n" f"Please fix {empty_values}."
        )
    return success


def create_producer_par_file(
    launcher_dwo: Path,
    target: Path,
    topology: str,
    template: str,
) -> None:
    """Create a PAR file in target path

    Parameters
    ----------
    launcher_dwo: Path
        Dynawo launcher
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
    if template.startswith("model"):
        if topology.casefold().startswith("m"):
            manage_files.copy_file(
                target / "Zone1" / "Producer.par", target / "Zone1" / "Producer_G1.par"
            )
            manage_files.copy_file(
                target / "Zone1" / "Producer.par", target / "Zone1" / "Producer_G2.par"
            )
            (target / "Zone1" / "Producer.par").unlink()

            _create_producer_par_file(launcher_dwo, target / "Zone1", "Producer_G1.par")
            _create_producer_par_file(launcher_dwo, target / "Zone1", "Producer_G2.par")
        else:
            _create_producer_par_file(launcher_dwo, target / "Zone1", "Producer.par")
        _create_producer_par_file(launcher_dwo, target / "Zone3", "Producer.par")
    else:
        _create_producer_par_file(launcher_dwo, target, "Producer.par")


def check_parameters(target: Path, template: str) -> bool:
    """Checks if all parameters in the PAR file have a value defined.

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
        False if there are empty values in the PAR file
    """
    if template.startswith("model"):
        par_files = list((target / "Zone1").glob("*.[pP][aA][rR]"))
        for par_file in par_files:
            if not _check_parameters(target / "Zone1", par_file.name):
                return False
        check_zone3 = _check_parameters(target / "Zone3", "Producer.par")
        return check_zone3
    else:
        return _check_parameters(target, "Producer.par")
