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

import configparser
import math
import re
from pathlib import Path
from typing import Optional

from lxml import etree

from dycov.configuration.cfg import config
from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.logging.logging import dycov_logging
from dycov.model.parameters import (
    Gen_params,
    Line_params,
    Load_params,
    Pdr_equipments,
    Pdr_params,
    Terminal,
    Xfmr_params,
)

# Numeric values: supports integers, decimals, and leading sign; allows ".5" style.
NUMERIC_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$")

# Multiplier * name OR name only.
# - Optional signed float multiplier followed by optional '*' (requires digits, no bare '+'/'-').
# - Name is an identifier-like token (letters, digits, underscores; must start with a letter
#   or underscore).
MULTIPLIER_PATTERN = re.compile(
    r"^(?:(?P<mul>[+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*\*\s*)?(?P<name>[A-Za-z_]\w*)$"
)


def write_pdr_comment(path: Path, par_file: str, pdr: Pdr_params) -> None:
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
    pdr : Pdr_params
        Parameters at the PDR bus (U, UPhase, S, P, Q).
    """
    par_path = path / par_file
    parser = etree.XMLParser(remove_blank_text=True)
    par_tree = etree.parse(par_path, parser)
    par_root = par_tree.getroot()

    header = "PDR parameters"
    comment_text = f"{header}: U={pdr.U}, UPhase={pdr.UPhase}, S={pdr.S}, P={pdr.P}, Q={pdr.Q}"

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


def find_bbmodel_by_type(producer_dyd_root: etree.Element, model_type: str) -> list:
    """Gets the blackbox models of the producer model by type of equipment.

    Parameters
    ----------
    producer_dyd_root: Element
        Root of the producer model
    model_type: str

    Returns
    -------
    list
        All the blackbox models in the producer model
    """
    bbmodels = []
    nsmap = {"ns": etree.QName(producer_dyd_root).namespace}
    for bbmodel in producer_dyd_root.xpath("//ns:blackBoxModel", namespaces=nsmap):
        if model_type == bbmodel.get("lib"):
            bbmodels.append(bbmodel)

    return bbmodels


def get_connected_to_pdr(producer_dyd: Path) -> list:
    """Gets the list of equipment connected to the PDR bus in the producer DYD model.

    Parameters
    ----------
    producer_dyd: Path
        Path to the producer DYD file

    Returns
    -------
    list
        List of Pdr_equipments objects representing equipment connected to the PDR bus
    """
    producer_dyd_tree = etree.parse(producer_dyd, etree.XMLParser(remove_blank_text=True))
    producer_dyd_root = producer_dyd_tree.getroot()

    connected_to_pdr = []
    nsmap = {"ns": etree.QName(producer_dyd_root).namespace}
    for connect in producer_dyd_root.xpath("//ns:connect", namespaces=nsmap):
        if "BusPDR" in connect.get("id1") and "terminal" in connect.get("var2"):
            connected_to_pdr.append(Pdr_equipments(connect.get("id2"), connect.get("var2")))
        if "BusPDR" in connect.get("id2") and "terminal" in connect.get("var1"):
            connected_to_pdr.append(Pdr_equipments(connect.get("id1"), connect.get("var1")))

    return connected_to_pdr


def get_producer_values(
    producer_dyd: Path,
    producer_par: Path,
    producer_ini: configparser.ConfigParser,
    s_nref: float,
) -> tuple[list, list, Load_params, Xfmr_params, Xfmr_params, Line_params]:
    """Gets the equipment parameters of the producer model.

    Parameters
    ----------
    producer_dyd: Path
        Path to the producer DYD file
    producer_par: Path
        Path to the producer PAR file
    producer_ini: ConfigParser
        producer INI file
    s_nref: float
        Nominal Apparent Power

    Returns
    -------
    list
        Parameters of the generators
    list
        Parameters of the transformers connected to the generators
    Load_params
        Parameters of the load
    Xfmr_params
        Parameters of the transformer connected to the load
    Xfmr_params
        Parameters of the main transformer connecting the power plant to the transmission network
    Line_params
        Internal line parameters of the producer model
    """

    producer_dyd_tree = etree.parse(producer_dyd, etree.XMLParser(remove_blank_text=True))
    producer_dyd_root = producer_dyd_tree.getroot()

    producer_par_tree = etree.parse(producer_par, etree.XMLParser(remove_blank_text=True))
    producer_par_root = producer_par_tree.getroot()

    generators = _get_generator_values(producer_dyd_root, producer_par_root, producer_ini)
    transformers = _get_transformer_values(producer_dyd_root, producer_par_root, s_nref)

    loads = _get_load_values(producer_dyd_root, producer_par_root)
    lines = _get_line_values(producer_dyd_root, producer_par_root, None, None)

    stepup_xfmrs = []
    auxload_xfmr = None
    ppm_xfmr = None
    for transformer in transformers:
        if "StepUp_Xfmr" in transformer.id:
            stepup_xfmrs.append(transformer)
        elif "AuxLoad_Xfmr" in transformer.id:
            auxload_xfmr = transformer
        elif "Main_Xfmr" in transformer.id:
            ppm_xfmr = transformer

    aux_load = None
    if len(loads) > 0:
        aux_load = loads[0]

    intline = None
    if len(lines) > 0:
        intline = lines[0]

    return (
        generators,
        stepup_xfmrs,
        aux_load,
        auxload_xfmr,
        ppm_xfmr,
        intline,
    )


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

    for model_parameter in _get_allowed_models(pcs_dyd_root, all_allowed_models):
        _append_generator(pcs_dyd_root, pcs_par_root, model_parameter, generators, None)
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

    loads = _get_load_values(pcs_dyd_root, pcs_par_root)
    return loads


def get_grid_load(loads: list) -> Load_params:
    """Gets the Equivalent load parameters.

    Parameters
    ----------
    loads: list
        A list of load parameters

    Returns
    -------
    Load_params
        An equivalent load parameters
    """
    if len(loads) == 0:
        return None

    ppu = 0
    qpu = 0
    for load in loads:
        ppu += load.P0
        qpu += load.Q0

    return Load_params(
        id=None,
        lib=None,
        P=ppu,
        Q=qpu,
        U=None,
        UPhase=None,
        Alpha=None,
        Beta=None,
        par_id=None,
        terminals=(Terminal(connectedEquipment=None),),
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

    lines = _get_line_values(pcs_dyd_root, pcs_par_root, line_rpu, line_xpu)

    return lines


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

    # Parse XML
    root = etree_par.getroot()
    ns = etree.QName(root).namespace
    nsmap = {"ns": ns}

    # XPath queries
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


def extract_defined_value(
    value_definition: str, parameter: str, base_value: float, sign: int = 1
) -> float:
    """
    Converts a parameter definition to a numeric value.

    Supported forms:
      - Pure numeric: "1.2", "-0.5", ".75"
      - Parameter only: "PmaxInjection", "-PmaxInjection"  (leading sign allowed)
      - Multiplier * parameter: "2*b", "-0.8*Pmax", "+1.25*PmaxInjection"

    Behavior:
      - The definition's explicit sign/multiplier is parsed to produce a raw value.
      - The 'sign' argument is applied at the end to convert the value to the desired
        downstream sign convention (it does NOT sanitize the input; it just transforms
        the final result).

    Parameters
    ----------
    value_definition : str
        The configuration string that defines the value (may include sign/multiplier).
    parameter : str
        Expected parameter name (case-insensitive).
    base_value : float
        Base value associated with the parameter (e.g., Pmax in pu).
    sign : int
        Final sign conversion to match downstream convention (e.g., -1 to flip).

    Returns
    -------
    float
        The computed value after applying the definition and the final 'sign'.
    """
    if value_definition is None:
        raise ValueError(f"{parameter} parameter not defined.")

    s = value_definition.strip()
    if not s:
        raise ValueError(f"{parameter} parameter not defined (empty).")

    # Step 1: Capture an explicit leading sign if present, then parse the rest.
    explicit_sign = 1
    if s[0] in "+-":
        explicit_sign = -1 if s[0] == "-" else 1
        s = s[1:].strip()

    # Step 2: Pure numeric (including the explicit leading sign).
    num_candidate = ("-" if explicit_sign == -1 else "") + s
    if NUMERIC_PATTERN.fullmatch(num_candidate):
        raw_value = float(num_candidate)
        return sign * raw_value  # Apply final convention

    # Step 3: Multiplier * parameter OR parameter only.
    m = MULTIPLIER_PATTERN.fullmatch(s)
    if m:
        multiplier_str = m.group("mul")
        param_name = m.group("name")

        # Validate parameter name, case-insensitive.
        if param_name.lower() != parameter.lower():
            raise ValueError(
                f"Parameter name mismatch: expected '{parameter}', got '{param_name}'"
            )

        # Multiplier: if present, parse; otherwise default to 1.0.
        multiplier = float(multiplier_str) if multiplier_str is not None else 1.0

        # Compose: explicit sign from the definition × parsed multiplier × base value.
        raw_value = explicit_sign * multiplier * base_value
        return sign * raw_value  # Apply final convention

    # Step 4: No valid form matched.
    raise ValueError(f"Invalid format for {parameter}: '{value_definition}'")


def adjust_producer_init(
    path: Path,
    producer_par: Path,
    generators: list,
    xfmrs: list,
    aux_load: Load_params,
    pdr: Pdr_params,
    generator_control_mode: str,
    force_voltage_droop: bool,
) -> None:
    """Modify the Producer PAR file to add the init values.

    Parameters
    ----------
    path: Path
        Path to store the modified PAR file
    producer_par: Path
        Path to the Producer PAR file
    generators: list
        All the producer's generators
    xfmrs: list
        Parameters for the transformers
    aux_load: Load_params
        Initial values to the producer's auxiliary load
    pdr: Pdr_params
        PDR parameters
    generator_control_mode: str
        Control mode
    force_voltage_droop: bool
        Force the voltage droop to be applied even if the control mode is not VoltageDroop
    """

    producer_par_tree = etree.parse(producer_par, etree.XMLParser(remove_blank_text=True))
    producer_par_root = producer_par_tree.getroot()

    for generator, xfmr in zip(generators, xfmrs):
        _adjust_transformer(
            producer_par_root,
            xfmr,
            xfmr.terminals[0].P0,
            xfmr.terminals[0].Q0,
            xfmr.terminals[0].U0,
            xfmr.terminals[0].UPhase0,
            xfmr.terminals[1].U0,
        )
        _adjust_generator(
            producer_par_root,
            generator,
            generator.terminals[0].P0,
            generator.terminals[0].Q0,
            generator.terminals[0].U0,
            generator.terminals[0].UPhase0,
            pdr,
            generator_control_mode,
            force_voltage_droop,
        )

    if aux_load:
        _adjust_load(
            producer_par_root,
            aux_load.id,
            aux_load.lib,
            aux_load.terminals[0].P0,
            aux_load.terminals[0].Q0,
            aux_load.terminals[0].U0,
            aux_load.terminals[0].UPhase0,
        )

    producer_par_tree.write(path / producer_par.name, pretty_print=True)


def _get_allowed_models(dyd_root: etree.Element, model_list: list) -> list[etree.Element]:
    matched_models = []
    for model_type in model_list:
        matched_models.extend(find_bbmodel_by_type(dyd_root, model_type))
    return matched_models


def _get_generator_values(
    dyd_root: etree.Element, par_root: etree.Element, producer_ini: configparser.ConfigParser
) -> list:
    generators = []
    all_allowed_models = _collect_allowed_generator_models()

    for model_parameter in _get_allowed_models(dyd_root, all_allowed_models):
        _append_generator(dyd_root, par_root, model_parameter, generators, producer_ini)

    _validate_generator_flows(generators)
    return generators


def _collect_allowed_generator_models() -> list:
    allowed_sync_models = dynawo_translator.get_synchronous_machine_models()
    allowed_park_models = dynawo_translator.get_power_park_models()
    allowed_storage_models = dynawo_translator.get_storage_models()
    return allowed_sync_models + allowed_park_models + allowed_storage_models


def _validate_generator_flows(generators: list) -> None:
    if not generators:
        return

    total_p = sum(g.P for g in generators)
    total_q = sum(g.Q for g in generators)

    if not math.isclose(total_p, 1.0, rel_tol=1e-6):
        dycov_logging.get_logger("Model Parameters").error("Generator P flows do not add up to 1")
        raise ValueError("Generator P flows do not add up to 1")

    if not math.isclose(total_q, 1.0, rel_tol=1e-6):
        dycov_logging.get_logger("Model Parameters").error("Generator Q flows do not add up to 1")
        raise ValueError("Generator Q flows do not add up to 1")


def _append_generator(
    dyd_root: etree.Element,
    par_root: etree.Element,
    model_parameter: etree.Element,
    generators: list,
    producer_ini: configparser.ConfigParser = None,
):
    gen_id = model_parameter.get("id")
    par_id = model_parameter.get("parId")
    lib = model_parameter.get("lib")
    nsmap = {"ns": etree.QName(par_root).namespace}

    connected_equipment = _get_connected_equipment(dyd_root, gen_id)
    parset = _get_parset(par_root, par_id, nsmap)

    imax = _get_injected_current(parset, nsmap, lib)
    P, Q = _get_generator_power_values(parset, nsmap, lib, gen_id, producer_ini)
    droop_value, s_nom = _get_generator_droop_and_snom(parset, nsmap, lib)

    generators.append(
        Gen_params(
            id=gen_id,
            lib=lib,
            terminals=(Terminal(connectedEquipment=connected_equipment),),
            SNom=s_nom,
            IMax=imax,
            par_id=par_id,
            P=P,
            Q=Q,
            VoltageDroop=droop_value,
            UseVoltageDroop=False,
        )
    )


def _get_connected_equipment(dyd_root, gen_id):
    nsmap = {"dyn": etree.QName(dyd_root).namespace}
    for connect in dyd_root.xpath("//dyn:connect", namespaces=nsmap):
        if connect.get("id1") == gen_id:
            return connect.get("id2")
        elif connect.get("id2") == gen_id:
            return connect.get("id1")
    return None


def _get_connected_equipment_by_terminal(dyd_root, gen_id, terminal):
    nsmap = {"dyn": etree.QName(dyd_root).namespace}
    for connect in dyd_root.xpath("//dyn:connect", namespaces=nsmap):
        if connect.get("id1") == gen_id and terminal in connect.get("var1"):
            return connect.get("id2")
        elif connect.get("id2") == gen_id and terminal in connect.get("var2"):
            return connect.get("id1")
    return None


def _get_parset(par_root, par_id, nsmap):
    parset = par_root.xpath(f"//ns:set[@id='{par_id}']", namespaces=nsmap)
    if parset is None:
        raise ValueError(f"The parameter set with id='{par_id}' was not found")
    return parset


def _get_injected_current(parset, nsmap, lib):
    sign, imaxpu_element = _get_parameter(parset, nsmap, lib, "InjectedCurrentMax")
    return float(imaxpu_element) * sign if imaxpu_element is not None else None


def _get_generator_power_values(parset, nsmap, lib, gen_id, producer_ini):
    default_section = "DEFAULT"
    if not producer_ini:
        _, P_str = _get_parameter(parset, nsmap, lib, "ActivePower0Pu")
        P = float(P_str) if P_str is not None else 0.0
    elif producer_ini.has_option(default_section, f"P_sharing_{gen_id}"):
        P = float(producer_ini.get(default_section, f"P_sharing_{gen_id}"))
    elif producer_ini.has_option(default_section, "topology") and str(
        producer_ini.get(default_section, "topology")
    ).startswith("S"):
        P = 1.0
        dycov_logging.get_logger("Model Parameters").warning(
            "A P flow of 1.0 has been automatically defined."
        )
    else:
        dycov_logging.get_logger("Model Parameters").error(
            "It is mandatory to define the distribution of P flows for multi-topology generators"
        )
        raise ValueError("Generator P flows not defined")

    if not producer_ini:
        _, Q_str = _get_parameter(parset, nsmap, lib, "ReactivePower0Pu")
        Q = float(Q_str) if Q_str is not None else 0.0
    elif producer_ini.has_option(default_section, f"Q_sharing_{gen_id}"):
        Q = float(producer_ini.get(default_section, f"Q_sharing_{gen_id}"))
    elif producer_ini.has_option(default_section, "topology") and str(
        producer_ini.get(default_section, "topology")
    ).startswith("S"):
        Q = 1.0
        dycov_logging.get_logger("Model Parameters").warning(
            "A Q flow of 1.0 has been automatically defined."
        )
    else:
        dycov_logging.get_logger("Model Parameters").error(
            "It is mandatory to define the distribution of Q flows for multi-topology generators"
        )
        raise ValueError("Generator Q flows not defined")

    return P, Q


def _get_generator_droop_and_snom(parset, nsmap, lib):
    _, VoltageDroop_str = _get_parameter(parset, nsmap, lib, "VoltageDroop")
    droop_value = float(VoltageDroop_str) if VoltageDroop_str is not None else 0.0
    _, s_nom_str = _get_parameter(parset, nsmap, lib, "NominalApparentPower")
    s_nom = float(s_nom_str) if s_nom_str is not None else 0.0
    return droop_value, s_nom


def _get_line_values(
    dyd_root: etree.Element,
    par_root: etree.Element,
    applied_line_rpu: float,
    applied_line_xpu: float,
) -> list:
    lines = []
    nsmap = {"ns": etree.QName(par_root).namespace}
    allowed_line_models = dynawo_translator.get_line_models()

    for model_parameter in _get_allowed_models(dyd_root, allowed_line_models):
        line_id = model_parameter.get("id")
        lib = model_parameter.get("lib")
        par_id = model_parameter.get("parId")
        parset = par_root.xpath(f"//ns:set[@id='{par_id}']", namespaces=nsmap)

        _, r_str = _get_parameter(parset, nsmap, lib, "ResistancePu")
        _, x_str = _get_parameter(parset, nsmap, lib, "ReactancePu")
        _, b_str = _get_parameter(parset, nsmap, lib, "SusceptancePu")
        _, g_str = _get_parameter(parset, nsmap, lib, "ConductancePu")

        line_rpu = float(r_str) if applied_line_rpu is None else applied_line_rpu
        line_xpu = _calculate_line_xpu(x_str, applied_line_xpu)
        line_gpu = float(g_str) if g_str is not None else 0.0
        line_bpu = float(b_str) if b_str is not None else 0.0

        connected_equipment1 = _get_connected_equipment_by_terminal(dyd_root, line_id, "terminal1")
        connected_equipment2 = _get_connected_equipment_by_terminal(dyd_root, line_id, "terminal2")

        lines.append(
            Line_params(
                id=line_id,
                lib=lib,
                R=line_rpu,
                X=line_xpu,
                B=line_bpu,
                G=line_gpu,
                par_id=par_id,
                terminals=(
                    Terminal(connectedEquipment=connected_equipment1),
                    Terminal(connectedEquipment=connected_equipment2),
                ),
            )
        )

    return lines


def _calculate_line_xpu(x_str: Optional[str], applied_line_xpu: float) -> float:
    """
    Compute X from 'line_XPu'.

    Rules:
    - If x_str is None or empty/whitespace: return 0.0
    - If x_str == 'line_XPu' (whitespace tolerated): return applied_line_xpu
    - Any other value: raise ValueError

    This function assumes the input domain has been constrained upstream.
    """
    if not x_str:
        return 0.0

    if x_str.strip() == "line_XPu":
        return applied_line_xpu

    raise ValueError(f"Unsupported x_str format: {x_str!r}")


def _get_transformer_values(
    dyd_root: etree.Element, par_root: etree.Element, s_nref: float
) -> list:
    transformers = []
    nsmap = {"ns": etree.QName(par_root).namespace}
    allowed_transformer_models = dynawo_translator.get_transformer_models()

    for bbmodel in _get_allowed_models(dyd_root, allowed_transformer_models):
        transformer_id, lib, par_id, parset = _parse_transformer_metadata(bbmodel, par_root, nsmap)
        xfmr_rpu, xfmr_xpu, xfmr_gpu, xfmr_bpu = _convert_transformer_units(
            parset, nsmap, lib, s_nref
        )
        xfmr_tapr = _get_tap_ratio(parset, nsmap, lib)
        connected_equipment1 = _get_connected_equipment_by_terminal(
            dyd_root, transformer_id, "terminal1"
        )
        connected_equipment2 = _get_connected_equipment_by_terminal(
            dyd_root, transformer_id, "terminal2"
        )

        transformers.append(
            Xfmr_params(
                id=transformer_id,
                lib=lib,
                R=xfmr_rpu,
                X=xfmr_xpu,
                B=xfmr_bpu,
                G=xfmr_gpu,
                rTfo=xfmr_tapr,
                par_id=par_id,
                terminals=(
                    Terminal(connectedEquipment=connected_equipment1),
                    Terminal(connectedEquipment=connected_equipment2),
                ),
            )
        )

    return transformers


def _parse_transformer_metadata(bbmodel, par_root, nsmap):
    transformer_id = bbmodel.get("id")
    lib = bbmodel.get("lib")
    par_id = bbmodel.get("parId")
    parset = par_root.xpath(f"//ns:set[@id='{par_id}']", namespaces=nsmap)
    return transformer_id, lib, par_id, parset


def _convert_transformer_units(parset, nsmap, lib, s_nref):
    _, r_str = _get_parameter(parset, nsmap, lib, "Resistance")
    _, x_str = _get_parameter(parset, nsmap, lib, "Reactance")
    _, g_str = _get_parameter(parset, nsmap, lib, "Conductance")
    _, b_str = _get_parameter(parset, nsmap, lib, "Susceptance")
    units_inPu = dynawo_translator.get_dynawo_variable(lib, "Resistance")[1].endswith("Pu")

    if not units_inPu:
        _, snom_str = _get_parameter(parset, nsmap, lib, "SNom")
        s_nom = float(snom_str)
        xfmr_rpu = (s_nref / s_nom) * float(r_str) / 100
        xfmr_xpu = (s_nref / s_nom) * float(x_str) / 100
        xfmr_gpu = (s_nom / s_nref) * float(g_str) / 100
        xfmr_bpu = (s_nom / s_nref) * float(b_str) / 100
    else:
        xfmr_rpu = float(r_str)
        xfmr_xpu = float(x_str)
        xfmr_gpu = float(g_str)
        xfmr_bpu = float(b_str)

    return xfmr_rpu, xfmr_xpu, xfmr_gpu, xfmr_bpu


def _get_tap_ratio(parset, nsmap, lib):
    _, rho_str = _get_parameter(parset, nsmap, lib, "Rho")
    return float(rho_str)


def _get_load_values(dyd_root: etree.Element, par_root: etree.Element) -> list:
    loads = []
    nsmap = {"ns": etree.QName(par_root).namespace}
    allowed_load_models = dynawo_translator.get_load_models()

    for bbmodel in _get_allowed_models(dyd_root, allowed_load_models):
        load_id, lib, par_id, connected_equipment, parset = _parse_load_metadata(
            bbmodel, dyd_root, par_root, nsmap
        )
        aux_ppu, aux_qpu, aux_upu, aux_phpu, alpha, beta = _extract_load_parameters(
            parset, nsmap, lib
        )
        connected_equipment = _get_connected_equipment(dyd_root, load_id)

        loads.append(
            Load_params(
                id=load_id,
                lib=lib,
                P=aux_ppu,
                Q=aux_qpu,
                U=aux_upu,
                UPhase=aux_phpu,
                Alpha=alpha,
                Beta=beta,
                par_id=par_id,
                terminals=(Terminal(connectedEquipment=connected_equipment),),
            )
        )

    return loads


def _parse_load_metadata(bbmodel, dyd_root, par_root, nsmap):
    load_id = bbmodel.get("id")
    lib = bbmodel.get("lib")
    par_id = bbmodel.get("parId")
    connected_equipment = _get_connected_equipment(dyd_root, load_id)
    parset = par_root.xpath(f"//ns:set[@id='{par_id}']", namespaces=nsmap)
    return load_id, lib, par_id, connected_equipment, parset


def _extract_load_parameters(parset, nsmap, lib):
    sign_P, p0_value = _get_parameter(parset, nsmap, lib, "ActivePower0")
    sign_Q, q0_value = _get_parameter(parset, nsmap, lib, "ReactivePower0")
    _, u0_value = _get_parameter(parset, nsmap, lib, "Voltage0")
    _, ph0_value = _get_parameter(parset, nsmap, lib, "Phase0")
    _, alpha_value = _get_parameter(parset, nsmap, lib, "Alpha")
    _, beta_value = _get_parameter(parset, nsmap, lib, "Beta")

    aux_ppu = _resolve_value(p0_value, sign_P)
    aux_qpu = _resolve_value(q0_value, sign_Q)
    aux_upu = _resolve_value(u0_value, 1)
    aux_phpu = _resolve_value(ph0_value, 1)

    alpha = None if alpha_value is None else float(alpha_value)
    beta = None if beta_value is None else float(beta_value)

    return aux_ppu, aux_qpu, aux_upu, aux_phpu, alpha, beta


def _resolve_value(raw, sign):
    if raw is None:
        return None
    if isinstance(raw, str) and raw.startswith("{") and raw.endswith("}"):
        return raw.replace("{", "").replace("}", "")
    try:
        return float(raw) * sign
    except (ValueError, TypeError):
        return raw


def _adjust_transformer(
    producer_par_root,
    transformer,
    transformer_p10pu,
    transformer_q10pu,
    transformer_u10pu,
    transformer_uphase10,
    transformer_u20pu,
):
    nsmap = {"ns": etree.QName(producer_par_root).namespace}
    parset = _get_parset(producer_par_root, transformer.par_id, nsmap)
    if parset is None:
        return

    _set_transformer_power(parset, nsmap, transformer.lib, transformer_p10pu, transformer_q10pu)
    _set_transformer_voltage_phase(
        parset, nsmap, transformer.lib, transformer_u10pu, transformer_uphase10
    )
    _set_transformer_voltage(parset, nsmap, transformer.lib, transformer_u20pu)


def _set_transformer_power(parset, nsmap, lib, p0pu, q0pu):
    sign, active_power0 = dynawo_translator.get_dynawo_variable(lib, "ActivePower10")
    _set_parameter(parset, nsmap, active_power0, sign, p0pu)
    sign, reactive_power0 = dynawo_translator.get_dynawo_variable(lib, "ReactivePower10")
    _set_parameter(parset, nsmap, reactive_power0, sign, q0pu)


def _set_transformer_voltage_phase(parset, nsmap, lib, u0pu, uphase0):
    sign = 1
    _, voltage0 = dynawo_translator.get_dynawo_variable(lib, "Voltage10")
    _set_parameter(parset, nsmap, voltage0, sign, u0pu)
    _, phase0 = dynawo_translator.get_dynawo_variable(lib, "Phase10")
    _set_parameter(parset, nsmap, phase0, sign, uphase0)


def _set_transformer_voltage(parset, nsmap, lib, u0pu):
    sign = 1
    _, voltage_setpoint = dynawo_translator.get_dynawo_variable(lib, "Voltage20")
    _set_parameter(parset, nsmap, voltage_setpoint, sign, u0pu)


def _adjust_generator(
    producer_par_root: etree.Element,
    generator: Gen_params,
    generator_p0pu: float,
    generator_q0pu: float,
    generator_u0pu: float,
    generator_uphase0: float,
    pdr: Pdr_params,
    generator_control_mode: str,
    force_voltage_droop: bool,
) -> None:
    nsmap = {"ns": etree.QName(producer_par_root).namespace}
    parset = _get_parset(producer_par_root, generator.par_id, nsmap)
    if parset is None:
        return

    _set_initial_power(parset, nsmap, generator.lib, generator_p0pu, generator_q0pu)
    _set_initial_pcc_power(parset, nsmap, generator.lib, pdr)
    _set_initial_voltage_phase(parset, nsmap, generator.lib, generator_u0pu, generator_uphase0)
    _set_initial_pcc_voltage_phase(parset, nsmap, generator.lib, pdr)

    control_mode_name = _apply_control_mode(generator, parset, nsmap, generator_control_mode)
    _apply_voltage_droop(
        generator, parset, nsmap, generator_control_mode, control_mode_name, force_voltage_droop
    )


def _set_initial_power(parset, nsmap, lib, p0pu, q0pu):
    sign, active_power0 = dynawo_translator.get_dynawo_variable(lib, "ActivePower0Pu")
    _set_parameter(parset, nsmap, active_power0, sign, p0pu)
    sign, reactive_power0 = dynawo_translator.get_dynawo_variable(lib, "ReactivePower0Pu")
    _set_parameter(parset, nsmap, reactive_power0, sign, q0pu)


def _set_initial_pcc_power(parset, nsmap, lib, pdr):
    sign, active_power0 = dynawo_translator.get_dynawo_variable(lib, "ActivePowerPcc0Pu")
    _set_parameter(parset, nsmap, active_power0, sign, pdr.P)
    sign, reactive_power0 = dynawo_translator.get_dynawo_variable(lib, "ReactivePowerPcc0Pu")
    _set_parameter(parset, nsmap, reactive_power0, sign, pdr.Q)


def _set_initial_voltage_phase(parset, nsmap, lib, u0pu, uphase0):
    sign = 1
    _, voltage0 = dynawo_translator.get_dynawo_variable(lib, "Voltage0Pu")
    _set_parameter(parset, nsmap, voltage0, sign, u0pu)
    _, phase0 = dynawo_translator.get_dynawo_variable(lib, "Phase0")
    _set_parameter(parset, nsmap, phase0, sign, uphase0)


def _set_initial_pcc_voltage_phase(parset, nsmap, lib, pdr):
    sign = 1
    _, voltage0 = dynawo_translator.get_dynawo_variable(lib, "VoltagePcc0Pu")
    _set_parameter(parset, nsmap, voltage0, sign, pdr.U)
    _, phase0 = dynawo_translator.get_dynawo_variable(lib, "PhasePcc0")
    _set_parameter(parset, nsmap, phase0, sign, pdr.UPhase)


def _apply_control_mode(generator, parset, nsmap, generator_control_mode):
    control_mode_parameters = _get_control_mode_parameters(generator, parset, nsmap)
    _log_control_mode(generator, control_mode_parameters)

    if not control_mode_parameters:
        return None

    is_valid, control_mode_name = dynawo_translator.is_valid_control_mode(
        generator, generator_control_mode, control_mode_parameters
    )

    if generator_control_mode != "Others" and not is_valid:
        control_mode_name = _handle_invalid_control_mode(
            generator, parset, nsmap, generator_control_mode
        )

    return control_mode_name


def _log_control_mode(generator, control_mode_parameters):
    dycov_logging.get_logger("Model Parameters").debug(
        f"Generator {generator.id} Control Mode: {control_mode_parameters}"
    )


def _handle_invalid_control_mode(generator, parset, nsmap, generator_control_mode):
    dycov_logging.get_logger("Model Parameters").warning(
        f"{generator.lib} control mode will be changed"
    )
    default_control_mode_parameters = _get_default_control_mode_parameters(
        generator, generator_control_mode
    )
    dycov_logging.get_logger("Model Parameters").debug(
        f"Default Control Mode: {default_control_mode_parameters} for {generator_control_mode}"
    )

    is_valid, control_mode_name = dynawo_translator.is_valid_control_mode(
        generator, generator_control_mode, default_control_mode_parameters
    )
    if is_valid:
        _set_parameters(generator, parset, nsmap, default_control_mode_parameters)
    else:
        dycov_logging.get_logger("Model Parameters").error(
            f"{generator.lib} executed with wrong control mode"
        )
        raise ValueError(f"{generator.lib} executed with wrong control mode")

    return control_mode_name


def _apply_voltage_droop(
    generator, parset, nsmap, generator_control_mode, control_mode_name, force_voltage_droop
):
    voltage_droop_parameters = _get_voltage_droop_parameters(generator, parset, nsmap)
    _log_voltage_droop(generator, voltage_droop_parameters)

    force_voltage_droop = _determine_voltage_droop(
        force_voltage_droop, control_mode_name, voltage_droop_parameters, generator
    )

    if force_voltage_droop:
        _validate_or_apply_default_voltage_droop(
            generator, parset, nsmap, generator_control_mode, voltage_droop_parameters
        )

    _recalculate_voltage_ref(generator, voltage_droop_parameters)


def _log_voltage_droop(generator, voltage_droop_parameters):
    dycov_logging.get_logger("Model Parameters").debug(
        f"Generator {generator.id} Voltage Droop Mode: {voltage_droop_parameters}"
    )


def _determine_voltage_droop(
    force_voltage_droop, control_mode_name, voltage_droop_parameters, generator
):
    if not voltage_droop_parameters:
        return False
    if control_mode_name:
        return not dynawo_translator.is_reactive_control_mode(generator, control_mode_name)
    return force_voltage_droop


def _validate_or_apply_default_voltage_droop(
    generator, parset, nsmap, generator_control_mode, voltage_droop_parameters
):
    is_valid, _ = dynawo_translator.is_valid_control_mode(
        generator, "VoltageDroop", voltage_droop_parameters
    )
    if not is_valid:
        dycov_logging.get_logger("Model Parameters").warning(
            f"{generator.lib} voltage droop mode will be changed"
        )
        default_voltage_droop_parameters = _get_default_voltage_droop_parameters(
            generator, "VoltageDroop"
        )
        dycov_logging.get_logger("Model Parameters").debug(
            f"Default Voltage Droop Mode: {default_voltage_droop_parameters} "
            f"for {generator_control_mode}"
        )
        is_valid, _ = dynawo_translator.is_valid_control_mode(
            generator, "VoltageDroop", default_voltage_droop_parameters
        )
        if is_valid:
            _set_parameters(generator, parset, nsmap, default_voltage_droop_parameters)
        else:
            dycov_logging.get_logger("Model Parameters").error(
                f"{generator.lib} executed with wrong voltage droop mode"
            )
            raise ValueError(f"{generator.lib} executed with wrong voltage droop mode")


def _recalculate_voltage_ref(generator, voltage_droop_parameters) -> None:
    if "MwpqMode" in voltage_droop_parameters:
        if voltage_droop_parameters["MwpqMode"] == "3":
            generator.UseVoltageDroop = True

    if all(p in voltage_droop_parameters for p in ["RefFlag", "VCompFlag"]):
        if voltage_droop_parameters["RefFlag"].lower() != "true":
            return
        if voltage_droop_parameters["VCompFlag"].lower() != "false":
            return
        generator.UseVoltageDroop = True


def _get_voltage_droop_parameters(generator, parset, nsmap) -> dict:
    if "IEC" in generator.lib:
        return _get_voltage_droop_parameters_iec(generator, parset, nsmap)
    elif "Wecc" in generator.lib:
        return _get_voltage_droop_parameters_wecc(generator, parset, nsmap)
    else:
        return {}


def _get_voltage_droop_parameters_iec(generator, parset, nsmap) -> dict:
    parameters = {}
    _, MwpqMode = _get_parameter(parset, nsmap, generator.lib, "MwpqMode")
    if MwpqMode is not None:
        parameters["MwpqMode"] = MwpqMode

    _, MqG = _get_parameter(parset, nsmap, generator.lib, "MqG")
    if MqG is not None:
        parameters["MqG"] = MqG

    return parameters


def _get_voltage_droop_parameters_wecc(generator, parset, nsmap) -> dict:
    parameters = {}
    _, RefFlag = _get_parameter(parset, nsmap, generator.lib, "RefFlag")
    if RefFlag is not None:
        parameters["RefFlag"] = RefFlag

    _, VCompFlag = _get_parameter(parset, nsmap, generator.lib, "VCompFlag")
    if VCompFlag is not None:
        parameters["VCompFlag"] = VCompFlag

    return parameters


def _get_control_mode_parameters(generator, parset, nsmap) -> dict:
    if "IEC" in generator.lib:
        return _get_control_mode_parameters_iec(generator, parset, nsmap)
    elif "Wecc" in generator.lib:
        return _get_control_mode_parameters_wecc(generator, parset, nsmap)
    else:
        return {}


def _get_control_mode_parameters_iec(generator, parset, nsmap) -> dict:
    parameters = {}
    _, MwpqMode = _get_parameter(parset, nsmap, generator.lib, "MwpqMode")
    if MwpqMode is not None:
        parameters["MwpqMode"] = MwpqMode

    _, MqG = _get_parameter(parset, nsmap, generator.lib, "MqG")
    if MqG is not None:
        parameters["MqG"] = MqG

    return parameters


def _get_control_mode_parameters_wecc(generator, parset, nsmap) -> dict:
    parameters = {}
    # Use _get_parameter where it helps to centralize lookup
    _, PfFlag = _get_parameter(parset, nsmap, generator.lib, "PfFlag")
    if PfFlag is not None:
        parameters["PfFlag"] = PfFlag

    _, VFlag = _get_parameter(parset, nsmap, generator.lib, "VFlag")
    if VFlag is not None:
        parameters["VFlag"] = VFlag

    _, PFlag = _get_parameter(parset, nsmap, generator.lib, "PFlag")
    if PFlag is not None:
        parameters["PFlag"] = PFlag

    _, QFlag = _get_parameter(parset, nsmap, generator.lib, "QFlag")
    if QFlag is not None:
        parameters["QFlag"] = QFlag

    _, RefFlag = _get_parameter(parset, nsmap, generator.lib, "RefFlag")
    if RefFlag is not None:
        parameters["RefFlag"] = RefFlag

    _, FreqFlag = _get_parameter(parset, nsmap, generator.lib, "FreqFlag")
    if FreqFlag is not None:
        parameters["FreqFlag"] = FreqFlag

    return parameters


def _get_default_voltage_droop_parameters(generator, generator_voltage_droop) -> dict:
    family, level = dynawo_translator.get_generator_family_level(generator)
    parameters = {}
    section = f"{generator_voltage_droop}_{family}_{level}"
    if config.has_option(section, "control_option"):
        control_option = config.get_int(section, "control_option", 1)
        parameters = dynawo_translator.get_control_mode(section, control_option)
    else:
        options = config.get_options(section)
        for option in options:
            parameters[option] = config.get_value(section, option)
    return parameters


def _get_default_control_mode_parameters(generator, generator_control_mode) -> dict:
    family, level = dynawo_translator.get_generator_family_level(generator)
    parameters = {}
    section = f"{generator_control_mode}_{family}_{level}"
    if config.has_option(section, "control_option"):
        control_option = config.get_int(section, "control_option", 1)
        parameters = dynawo_translator.get_control_mode(section, control_option)
    else:
        options = config.get_options(section)
        for option in options:
            parameters[option] = config.get_value(section, option)
    return parameters


def _set_parameters(generator, parset, nsmap, parameters: dict):
    for name, value in parameters.items():
        _, dynawo_name = dynawo_translator.get_dynawo_variable(generator.lib, name)
        _set_parameter(parset, nsmap, dynawo_name, 1, value.lower())


def _adjust_load(
    producer_par_root: etree.Element,
    load_id: str,
    load_lib: str,
    load_p0pu: float,
    load_q0pu: float,
    load_u0pu: float,
    load_uphase0: float,
) -> None:
    nsmap = {"ns": etree.QName(producer_par_root).namespace}
    parset = producer_par_root.xpath(f"//ns:set[@id='{load_id}']", namespaces=nsmap)
    if parset is None:
        return

    sign, active_power0 = dynawo_translator.get_dynawo_variable(load_lib, "ActivePower0")
    _set_parameter(parset, nsmap, active_power0, sign, load_p0pu)

    sign, reactive_power0 = dynawo_translator.get_dynawo_variable(load_lib, "ReactivePower0")
    _set_parameter(parset, nsmap, reactive_power0, sign, load_q0pu)

    sign = 1
    _, voltage0 = dynawo_translator.get_dynawo_variable(load_lib, "Voltage0")
    _set_parameter(parset, nsmap, voltage0, sign, load_u0pu)

    _, phase0 = dynawo_translator.get_dynawo_variable(load_lib, "Phase0")
    _set_parameter(parset, nsmap, phase0, sign, load_uphase0)


def _set_parameter(parset, nsmap, parameter_name, sign, parameter_value):
    # Validate parset contains exactly one element
    if not isinstance(parset, list) or len(parset) != 1 or not parameter_name:
        return
    ps = parset[0]
    parameter = ps.xpath(f"ns:par[@name='{parameter_name}']", namespaces=nsmap)
    if parameter:
        parameter[0].set("value", str(sign * parameter_value))


def _get_parameter(parset, nsmap, lib, parameter_name):
    # Validate parset contains exactly one element
    if not isinstance(parset, list) or len(parset) != 1:
        return None, None
    ps = parset[0]
    sign, variable_name = dynawo_translator.get_dynawo_variable(lib, parameter_name)
    if not variable_name:
        return None, None
    variable = ps.xpath(f"ns:par[@name='{variable_name}']", namespaces=nsmap)
    return (sign, variable[0].get("value")) if variable else (sign, None)
