#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import math
from pathlib import Path

from lxml import etree

from dycov.model.parameters import PdrParams


def write_pdr_comment(path: Path, par_file: str, pdr: PdrParams) -> None:
    """
    Insert (or update) an XML comment at the top of the PAR file
    with the PDR parameters (U, UPhase, S, P, Q).

    The comment is marked with a stable header so that repeated calls
    update the existing comment instead of duplicating it.

    Parameters
    ----------
    path : Path
        Directory where the PAR file is located.
    par_file : str
        PAR filename (e.g., "network.par").
    pdr : PdrParams
        Parameters at the PDR bus (U, UPhase, S, P, Q).
    """
    par_path = path / par_file
    parser = etree.XMLParser(remove_blank_text=True)
    par_tree = etree.parse(par_path, parser)
    par_root = par_tree.getroot()

    header = "PDR parameters"
    comment_text = f"{header}: U={pdr.u}, UPhase={pdr.u_phase}, S={pdr.s}, P={pdr.p}, Q={pdr.q}"

    # Buscar comentarios existentes en todo el documento
    existing = None
    for c in par_root.xpath("//comment()"):
        if c.text and c.text.startswith(header):
            existing = c
            break

    if existing is not None:
        # Actualizar el comentario existente
        existing.text = comment_text
    else:
        # Insertar un nuevo comentario como primer hijo del <root>
        comment = etree.Comment(comment_text)
        if len(par_root):
            par_root.insert(0, comment)
        else:
            par_root.append(comment)

    # Guardar cambios con declaración XML y codificación explícita
    par_tree.write(par_path, pretty_print=True, xml_declaration=True, encoding="UTF-8")


def get_event_times(
    results_case_dir: Path, filename: str, fault_duration: float, simulation_duration: float
) -> tuple[float, float]:
    """Gets the start time of an event and the end time.

    Parameters
    ----------
    results_case_dir: Path
        Path to the pcs PAR file
    filename: str
        PAR filename
    fault_duration: float
        Duration of the event
    simulation_duration: float
        Duration of the simulation

    Returns
    -------
    float
        Start time of an event
    float
        End time of an event
    """
    etree_par = etree.parse(
        results_case_dir / (filename + ".par"),
        etree.XMLParser(remove_blank_text=True),
    )

    root = etree_par.getroot()
    ns = etree.QName(root).namespace
    nsmap = {"ns": ns}

    tbegin_parameters = root.xpath("//ns:par[@name='fault_tBegin']", namespaces=nsmap)
    tevent_parameters = root.xpath("//ns:par[@name='event_tEvent']", namespaces=nsmap)
    tstep_parameters = root.xpath("//ns:par[@name='step_tStep']", namespaces=nsmap)

    # Extract values
    if tbegin_parameters:
        tevent1 = float(tbegin_parameters[0].get("value"))
    else:
        tevent1 = float("NaN")

    if tevent_parameters and not tevent_parameters[0].get("value").startswith("{"):
        tevent2 = float(tevent_parameters[0].get("value"))
    elif tstep_parameters and not tstep_parameters[0].get("value").startswith("{"):
        tevent2 = float(tstep_parameters[0].get("value"))
    else:
        tevent2 = float("NaN")

    if math.isnan(tevent2) and not math.isnan(tevent1):
        if fault_duration > simulation_duration:
            tevent2 = tevent1
        else:
            tevent2 = tevent1 + fault_duration

    return tevent1, tevent2


def find_output_dir(results_case_dir: Path, filename: str) -> str:
    """Gets the Dynawo simulation output directory.

    Parameters
    ----------
    results_case_dir: Path
        Path to the pcs JOBS file
    filename: str
        JOBS filename

    Returns
    -------
    str
        Dynawo simulation output directory
    """
    etree_par = etree.parse(
        results_case_dir / (filename + ".jobs"),
        etree.XMLParser(remove_blank_text=True),
    )

    root = etree_par.getroot()
    nsmap = {"ns": etree.QName(root).namespace}
    output_dir = None
    for model_output in root.xpath("//ns:outputs", namespaces=nsmap):
        output_dir = model_output.get("directory")
    return output_dir
