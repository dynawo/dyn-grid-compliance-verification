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
from pathlib import Path
from typing import Optional

from lxml import etree

from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.files import par_access
from dycov.logging import dycov_logging
from dycov.model.parameters import (
    GenParams,
    LineParams,
    LoadParams,
    PdrEquipments,
    Terminal,
    XfmrParams,
)


def find_bbmodels(producer_dyd_root: etree.Element) -> list:
    """Gets every blackbox model declared in the producer model.

    Parameters
    ----------
    producer_dyd_root: Element
        Root of the producer model

    Returns
    -------
    list
        All the blackbox models in the producer model
    """
    nsmap = {"ns": etree.QName(producer_dyd_root).namespace}
    return producer_dyd_root.xpath("//ns:blackBoxModel", namespaces=nsmap)


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
    return [b for b in find_bbmodels(producer_dyd_root) if model_type == b.get("lib")]


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
            connected_to_pdr.append(PdrEquipments(connect.get("id2"), connect.get("var2")))
        if "BusPDR" in connect.get("id2") and "terminal" in connect.get("var1"):
            connected_to_pdr.append(PdrEquipments(connect.get("id1"), connect.get("var1")))

    return connected_to_pdr


GROUP_XFMR_ROLE = "Group_Xfmr"
AUXLOAD_XFMR_ROLE = "AuxLoad_Xfmr"
MAIN_XFMR_ROLE = "Main_Xfmr"
XFMR_ROLES = (GROUP_XFMR_ROLE, AUXLOAD_XFMR_ROLE, MAIN_XFMR_ROLE)


def _classify_transformers(transformers: list) -> dict[str, list]:
    """Groups the producer transformers by the role their id declares.

    Parameters
    ----------
    transformers: list
        Transformers read from the producer model

    Returns
    -------
    dict
        Transformers of the producer model, keyed by role

    Raises
    ------
    ValueError
        If a transformer id matches no known role
    """
    by_role = {role: [] for role in XFMR_ROLES}
    for transformer in transformers:
        role = role_of(transformer.id)
        if role is None:
            raise ValueError(
                f"Unexpected transformer id '{transformer.id}': the producer's transformers "
                f"must be named after their role in the topology ({', '.join(XFMR_ROLES)})."
            )
        by_role[role].append(transformer)

    return by_role


def role_of(transformer_id: str) -> Optional[str]:
    """Returns the topology role the given transformer id declares, or None if unknown."""
    return next((role for role in XFMR_ROLES if role in transformer_id), None)


def _single(transformers: list):
    return transformers[0] if transformers else None


def get_producer_values(
    producer_dyd: Path,
    producer_par: Path,
    producer_ini: configparser.ConfigParser,
    s_nref: float,
) -> tuple[list, list, LoadParams, XfmrParams, XfmrParams, LineParams]:
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
    LoadParams
        Parameters of the load
    XfmrParams
        Parameters of the transformer connected to the load
    XfmrParams
        Parameters of the main transformer connecting the power plant to the transmission network
    LineParams
        Internal line parameters of the producer model
    """

    producer_dyd_tree = etree.parse(producer_dyd, etree.XMLParser(remove_blank_text=True))
    producer_dyd_root = producer_dyd_tree.getroot()

    producer_par_tree = etree.parse(producer_par, etree.XMLParser(remove_blank_text=True))
    producer_par_root = producer_par_tree.getroot()

    generators = _get_generator_values(producer_dyd_root, producer_par_root, producer_ini)
    transformers = _get_transformer_values(producer_dyd_root, producer_par_root, s_nref)

    loads = get_load_values(producer_dyd_root, producer_par_root)
    lines = get_line_values(producer_dyd_root, producer_par_root, None, None)

    by_role = _classify_transformers(transformers)
    group_xfmrs = by_role[GROUP_XFMR_ROLE]
    auxload_xfmr = _single(by_role[AUXLOAD_XFMR_ROLE])
    main_xfmr = _single(by_role[MAIN_XFMR_ROLE])

    aux_load = None
    if len(loads) > 0:
        aux_load = loads[0]

    intline = None
    if len(lines) > 0:
        intline = lines[0]

    return (
        generators,
        group_xfmrs,
        aux_load,
        auxload_xfmr,
        main_xfmr,
        intline,
    )


def get_allowed_models(dyd_root: etree.Element, model_list: list) -> list[etree.Element]:
    matched_models = []
    for model_type in model_list:
        matched_models.extend(find_bbmodel_by_type(dyd_root, model_type))
    return matched_models


def _get_generator_values(
    dyd_root: etree.Element, par_root: etree.Element, producer_ini: configparser.ConfigParser
) -> list:
    generators = []
    all_allowed_models = _collect_allowed_generator_models()

    for model_parameter in get_allowed_models(dyd_root, all_allowed_models):
        append_generator(dyd_root, par_root, model_parameter, generators, producer_ini)

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

    total_p = sum(g.p for g in generators)
    total_q = sum(g.q for g in generators)

    if not math.isclose(total_p, 1.0, rel_tol=1e-6):
        dycov_logging.get_logger("Model Parameters").error("Generator P flows do not add up to 1")
        raise ValueError("Generator P flows do not add up to 1")

    if not math.isclose(total_q, 1.0, rel_tol=1e-6):
        dycov_logging.get_logger("Model Parameters").error("Generator Q flows do not add up to 1")
        raise ValueError("Generator Q flows do not add up to 1")


def append_generator(
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
    parset = par_access.get_parset(par_root, par_id, nsmap)

    imax = _get_maximum_current(parset, nsmap, lib)
    P, Q = _get_generator_power_values(parset, nsmap, lib, gen_id, producer_ini)
    p_max, p_min, q_max, q_min = _get_generator_power_limits(
        parset, nsmap, lib, gen_id, producer_ini
    )
    droop_value, s_nom = _get_generator_droop_and_snom(parset, nsmap, lib)
    ppc_local = _get_generator_ppc_local(parset, nsmap, lib)

    converter_lv_control = _get_generator_converter_lv_control(parset, nsmap, lib)

    generators.append(
        GenParams(
            id=gen_id,
            lib=lib,
            terminals=(Terminal(connected_equipment=connected_equipment),),
            s_nom=s_nom,
            i_max=imax,
            par_id=par_id,
            p=P,
            p_max=p_max,
            p_min=p_min,
            q=Q,
            q_max=q_max,
            q_min=q_min,
            voltage_droop=droop_value,
            use_voltage_droop=False,
            ppc_local=ppc_local,
            converter_lv_control=converter_lv_control,
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


def _get_maximum_current(parset, nsmap, lib):
    sign, imaxpu_element = par_access.get_parameter(parset, nsmap, lib, "MaxCurrentAtConverter")
    return float(imaxpu_element) * sign if imaxpu_element is not None else None


def _get_generator_power_values(parset, nsmap, lib, gen_id, producer_ini):
    default_section = "DEFAULT"
    if not producer_ini:
        _, P_str = par_access.get_parameter(parset, nsmap, lib, "ActivePower0Pu")
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
        _, Q_str = par_access.get_parameter(parset, nsmap, lib, "ReactivePower0Pu")
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


def _get_generator_power_limits(parset, nsmap, lib, gen_id, producer_ini):
    _, P_max_str = par_access.get_parameter(parset, nsmap, lib, "MaxActivePowerPu")
    _, P_min_str = par_access.get_parameter(parset, nsmap, lib, "MinActivePowerPu")
    _, Q_max_str = par_access.get_parameter(parset, nsmap, lib, "MaxReactivePowerPu")
    _, Q_min_str = par_access.get_parameter(parset, nsmap, lib, "MinReactivePowerPu")

    p_max = float(P_max_str) if P_max_str is not None else 0.0
    p_min = float(P_min_str) if P_min_str is not None else 0.0
    q_max = float(Q_max_str) if Q_max_str is not None else 0.0
    q_min = float(Q_min_str) if Q_min_str is not None else 0.0

    return p_max, p_min, q_max, q_min


def _get_generator_droop_and_snom(parset, nsmap, lib):
    _, VoltageDroop_str = par_access.get_parameter(parset, nsmap, lib, "VoltageDroop")
    droop_value = float(VoltageDroop_str) if VoltageDroop_str is not None else 0.0
    _, s_nom_str = par_access.get_parameter(parset, nsmap, lib, "NominalApparentPower")
    s_nom = float(s_nom_str) if s_nom_str is not None else 0.0
    return droop_value, s_nom


def _get_generator_ppc_local(parset, nsmap, lib):
    _, ppc_local = par_access.get_parameter(parset, nsmap, lib, "PPCLocal")
    return ppc_local.lower() == "true" if ppc_local is not None else True


def _get_generator_converter_lv_control(parset, nsmap, lib):
    _, converter_lv_control_str = par_access.get_parameter(
        parset, nsmap, lib, "ConverterLVControl"
    )
    return (
        converter_lv_control_str.lower() == "true"
        if converter_lv_control_str is not None
        else True
    )


def get_line_values(
    dyd_root: etree.Element,
    par_root: etree.Element,
    applied_line_rpu: float,
    applied_line_xpu: float,
) -> list:
    lines = []
    nsmap = {"ns": etree.QName(par_root).namespace}
    allowed_line_models = dynawo_translator.get_line_models()

    for model_parameter in get_allowed_models(dyd_root, allowed_line_models):
        line_id = model_parameter.get("id")
        lib = model_parameter.get("lib")
        par_id = model_parameter.get("parId")
        parset = par_access.get_parset(par_root, par_id, nsmap)

        _, r_str = par_access.get_parameter(parset, nsmap, lib, "ResistancePu")
        _, x_str = par_access.get_parameter(parset, nsmap, lib, "ReactancePu")
        _, b_str = par_access.get_parameter(parset, nsmap, lib, "SusceptancePu")
        _, g_str = par_access.get_parameter(parset, nsmap, lib, "ConductancePu")

        line_rpu = float(r_str) if applied_line_rpu is None else applied_line_rpu
        line_xpu = _calculate_line_xpu(x_str, applied_line_xpu)
        line_gpu = float(g_str) if g_str is not None else 0.0
        line_bpu = float(b_str) if b_str is not None else 0.0

        connected_equipment1 = _get_connected_equipment_by_terminal(dyd_root, line_id, "terminal1")
        connected_equipment2 = _get_connected_equipment_by_terminal(dyd_root, line_id, "terminal2")

        lines.append(
            LineParams(
                id=line_id,
                lib=lib,
                r=line_rpu,
                x=line_xpu,
                b=line_bpu,
                g=line_gpu,
                par_id=par_id,
                terminals=(
                    Terminal(connected_equipment=connected_equipment1),
                    Terminal(connected_equipment=connected_equipment2),
                ),
            )
        )

    return lines


def _calculate_line_xpu(x_str: Optional[str], applied_line_xpu: float) -> float:
    if applied_line_xpu is None:
        return float(x_str)
    if x_str and "{{line_XPu}}" in x_str:
        return applied_line_xpu
    return float(x_str) if x_str else 0.0


def _get_transformer_values(
    dyd_root: etree.Element, par_root: etree.Element, s_nref: float
) -> list:
    transformers = []
    nsmap = {"ns": etree.QName(par_root).namespace}
    allowed_transformer_models = dynawo_translator.get_transformer_models()

    for bbmodel in get_allowed_models(dyd_root, allowed_transformer_models):
        transformer_id, lib, par_id, parset = _parse_transformer_metadata(bbmodel, par_root, nsmap)
        xfmr_rpu, xfmr_xpu, xfmr_gpu, xfmr_bpu = _convert_transformer_units(
            parset, nsmap, lib, s_nref
        )
        xfmr_tapr = _get_tap_rho(parset, nsmap, lib)
        xfmr_tapa = _get_tap_alpha(parset, nsmap, lib)
        connected_equipment1 = _get_connected_equipment_by_terminal(
            dyd_root, transformer_id, "terminal1"
        )
        connected_equipment2 = _get_connected_equipment_by_terminal(
            dyd_root, transformer_id, "terminal2"
        )

        transformers.append(
            XfmrParams(
                id=transformer_id,
                lib=lib,
                r=xfmr_rpu,
                x=xfmr_xpu,
                b=xfmr_bpu,
                g=xfmr_gpu,
                r_tfo=xfmr_tapr,
                alpha_tfo=xfmr_tapa,
                par_id=par_id,
                terminals=(
                    Terminal(connected_equipment=connected_equipment1),
                    Terminal(connected_equipment=connected_equipment2),
                ),
            )
        )

    return transformers


def _parse_transformer_metadata(bbmodel, par_root, nsmap):
    transformer_id = bbmodel.get("id")
    lib = bbmodel.get("lib")
    par_id = bbmodel.get("parId")
    parset = par_access.get_parset(par_root, par_id, nsmap)
    return transformer_id, lib, par_id, parset


def _convert_transformer_units(parset, nsmap, lib, s_nref):
    _, r_str = par_access.get_parameter(parset, nsmap, lib, "Resistance")
    _, x_str = par_access.get_parameter(parset, nsmap, lib, "Reactance")
    _, g_str = par_access.get_parameter(parset, nsmap, lib, "Conductance")
    _, b_str = par_access.get_parameter(parset, nsmap, lib, "Susceptance")
    units_inPu = dynawo_translator.get_dynawo_variable(lib, "Resistance")[1].endswith("Pu")

    if not units_inPu:
        _, snom_str = par_access.get_parameter(parset, nsmap, lib, "SNom")
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


def _get_tap_rho(parset, nsmap, lib):
    _, rho_str = par_access.get_parameter(parset, nsmap, lib, "Rho")
    if rho_str is None:
        return 1.0
    return float(rho_str)


def _get_tap_alpha(parset, nsmap, lib):
    _, alpha_str = par_access.get_parameter(parset, nsmap, lib, "Alpha")
    if alpha_str is None:
        return 0.0
    return float(alpha_str)


def get_load_values(dyd_root: etree.Element, par_root: etree.Element) -> list:
    loads = []
    nsmap = {"ns": etree.QName(par_root).namespace}
    allowed_load_models = dynawo_translator.get_load_models()

    for bbmodel in get_allowed_models(dyd_root, allowed_load_models):
        load_id, lib, par_id, connected_equipment, parset = _parse_load_metadata(
            bbmodel, dyd_root, par_root, nsmap
        )
        aux_ppu, aux_qpu, aux_upu, aux_phpu, alpha, beta = _extract_load_parameters(
            parset, nsmap, lib
        )
        connected_equipment = _get_connected_equipment(dyd_root, load_id)

        loads.append(
            LoadParams(
                id=load_id,
                lib=lib,
                p=aux_ppu,
                q=aux_qpu,
                u=aux_upu,
                u_phase=aux_phpu,
                alpha=alpha,
                beta=beta,
                par_id=par_id,
                terminals=(Terminal(connected_equipment=connected_equipment),),
            )
        )

    return loads


def _parse_load_metadata(bbmodel, dyd_root, par_root, nsmap):
    load_id = bbmodel.get("id")
    lib = bbmodel.get("lib")
    par_id = bbmodel.get("parId")
    connected_equipment = _get_connected_equipment(dyd_root, load_id)
    parset = par_access.get_parset(par_root, par_id, nsmap)
    return load_id, lib, par_id, connected_equipment, parset


def _extract_load_parameters(parset, nsmap, lib):
    sign_Pref, pref_value = par_access.get_parameter(parset, nsmap, lib, "ActiveRefPu")
    sign_Qref, qref_value = par_access.get_parameter(parset, nsmap, lib, "ReactiveRefPu")
    sign_P, p0_value = par_access.get_parameter(parset, nsmap, lib, "ActivePower0")
    sign_Q, q0_value = par_access.get_parameter(parset, nsmap, lib, "ReactivePower0")
    _, u0_value = par_access.get_parameter(parset, nsmap, lib, "Voltage0")
    _, ph0_value = par_access.get_parameter(parset, nsmap, lib, "Phase0")
    _, alpha_value = par_access.get_parameter(parset, nsmap, lib, "Alpha")
    _, beta_value = par_access.get_parameter(parset, nsmap, lib, "Beta")

    aux_ppu = _resolve_value(pref_value, sign_Pref)
    if aux_ppu is None:
        aux_ppu = _resolve_value(p0_value, sign_P)
    aux_qpu = _resolve_value(qref_value, sign_Qref)
    if aux_qpu is None:
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
