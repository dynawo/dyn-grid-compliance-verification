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

from jinja2 import Environment, FileSystemLoader, Template, meta
from lxml import etree

from dgcv.logging.logging import dgcv_logging


def _get_template(path: Path, template_file: str) -> Template:
    file_loader = FileSystemLoader(path)
    env = Environment(loader=file_loader)
    template = env.get_template(template_file)

    return template


def get_all_variables(path: Path, template_file: str) -> dict:
    if not (path / template_file).exists():
        return {}

    file_loader = FileSystemLoader(path)
    env = Environment(loader=file_loader)
    template = env.loader.get_source(env, template_file)[0]
    content = env.parse(template)
    variables = meta.find_undeclared_variables(content)
    return dict.fromkeys(variables, 0)


def dump_file(
    path: Path,
    filename: str,
    stream_dict: dict,
) -> None:
    """Replace file placeholders with values.

    Parameters
    ----------
    path: Path
        Path where the  file is stored
    filename: str
        filename
    stream_dict: dict
        Dictionary with all variables in the file
    """

    template = _get_template(path, filename)
    template.stream(stream_dict).dump(str(path / filename))


def fault_par_file(
    path: Path,
    filename: str,
    fault_tend: float,
    fault_xpu: float,
    fault_rpu: float,
) -> None:
    """Replace PAR file placeholders with values.

    Parameters
    ----------
    path: Path
        Path where the PAR file is stored
    filename: str
        PAR filename
    fault_tend: float
        End time for event
    fault_xpu: float
        Node fault resistance
    fault_rpu: float
        Node fault reactance
    """
    par_tree = etree.parse(path / filename, etree.XMLParser(remove_blank_text=True))
    par_root = par_tree.getroot()
    ns = etree.QName(par_root).namespace
    tend_parameters = par_root.find(f".//{{{ns}}}par[@name='fault_tEnd']")
    if tend_parameters is not None:
        tend_parameters.set("value", str(fault_tend))
    rpu_parameters = par_root.find(f".//{{{ns}}}par[@name='fault_RPu']")
    if rpu_parameters is not None:
        rpu_parameters.set("value", str(fault_rpu))
    xpu_parameters = par_root.find(f".//{{{ns}}}par[@name='fault_XPu']")
    if xpu_parameters is not None:
        xpu_parameters.set("value", str(fault_xpu))

    par_tree.write(
        path / filename,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )


def fault_time(path: Path, time: float) -> None:
    """Replaces the end time event placeholder with its value.

    Parameters
    ----------
    path: Path
        Path where the PAR file is stored
    time: float
        End time value
    """
    etree_par = etree.parse(path, etree.XMLParser(remove_blank_text=True))
    root = etree_par.getroot()
    ns = etree.QName(root).namespace

    fault_tbegin = None
    for model_output in root.iter("{%s}par" % ns):
        if (
            model_output.get("name") == "fault_tBegin"
            and model_output.getparent().get("id") == "NodeFault"
        ):
            fault_tbegin = model_output.get("value")

    if fault_tbegin is None:
        dgcv_logging.get_logger("Files").info("No event to disconnect")
        return

    fault_tend = str(float(fault_tbegin) + time)

    for model_output in root.iter("{%s}par" % ns):
        if (
            model_output.get("name") == "event_tEvent"
            and model_output.getparent().get("id") == "DisconnectLine"
        ):
            model_output.set("value", fault_tend)

        if (
            model_output.get("name") == "fault_tEnd"
            and model_output.getparent().get("id") == "NodeFault"
        ):
            model_output.set("value", fault_tend)

    etree_par.write(
        path,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )
