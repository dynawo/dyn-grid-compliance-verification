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
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader, Template, meta
from lxml import etree

from dycov.logging.logging import dycov_logging


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


def modify_jobs_file(
    path: Path,
    filename: str,
    solver_id: str,
    solver_lib: str,
) -> None:
    """Modify the value of a parameter in the PAR file.

    Parameters
    ----------
    path: Path
        Path where the PAR file is stored
    filename: str
        PAR filename
    solver_id: str
        Solver ID
    solver_lib: str
        Solver library
    """
    jobs_tree = etree.parse(path / filename, etree.XMLParser(remove_blank_text=True))
    jobs_root = jobs_tree.getroot()
    ns = etree.QName(jobs_root).namespace
    solver = jobs_root.find(f".//{{{ns}}}solver")
    if solver is not None:
        solver.set("parId", solver_id)
        solver.set("lib", solver_lib)

    jobs_tree.write(
        path / filename,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )


def modify_par_file(
    path: Path,
    filename: str,
    parameter_name: str,
    value: float,
) -> None:
    """Modify the value of a parameter in the PAR file.

    Parameters
    ----------
    path: Path
        Path where the PAR file is stored
    filename: str
        PAR filename
    parameter_name: str
        Parameter name to modify
    value: float
        New value
    """
    par_tree = etree.parse(path / filename, etree.XMLParser(remove_blank_text=True))
    par_root = par_tree.getroot()
    ns = etree.QName(par_root).namespace
    par_file_parameter = par_root.find(f".//{{{ns}}}par[@name='{parameter_name}']")
    if par_file_parameter is not None:
        par_file_parameter.set("value", str(value))

    par_tree.write(
        path / filename,
        pretty_print=True,
        xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="UTF-8",
    )


def add_parameters(
    path: Path,
    filename: str,
    solver_id: str,
    parameters: List[Dict[str, str]],
) -> None:
    """Add or update parameters in a solver <set> within a PAR XML file.

    Parameters
    ----------
    path : Path
        Path where the PAR file is stored.
    filename : str
        PAR filename.
    solver_id : str
        Identifier of the <set> element to modify.
    parameters : list[dict[str, str]]
        List of parameter specs. Each item must contain:
            - "type": str, parameter type (e.g., "double", "string", "INT").
            - "name": str, parameter name.
            - "value": str, parameter value.
    """
    par_tree = etree.parse(path / filename, etree.XMLParser(remove_blank_text=True))
    par_root = par_tree.getroot()

    nsmap = {"ns": etree.QName(par_root).namespace}
    parset = par_root.xpath(f"//ns:set[@id='{solver_id}']", namespaces=nsmap)
    ps = parset[0]

    # Add or update each parameter from the list
    for spec in parameters:
        parameter_type = str(spec.get("type", ""))
        parameter_name = str(spec.get("name", ""))
        value = str(spec.get("value", ""))

        # Find existing <par name="..."> under the target <set>
        existing = ps.xpath(
            f"./ns:par[@name='{parameter_name}']",
            namespaces=nsmap,
        )

        if existing:
            existing[0].set("type", parameter_type)
            existing[0].set("value", value)
        else:
            etree.SubElement(
                ps,
                f"{{{nsmap['ns']}}}par" if nsmap["ns"] else "par",
                type=parameter_type,
                name=parameter_name,
                value=value,
            )

    par_tree.write(
        str(path / filename),
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )


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
        dycov_logging.get_logger("Files").info("No event to disconnect")
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
