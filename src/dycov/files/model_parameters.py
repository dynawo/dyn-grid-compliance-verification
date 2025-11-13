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

from dycov.configuration.cfg import config
from dycov.curves.dynawo.translator import dynawo_translator, get_generator_family_level
from dycov.logging.logging import dycov_logging
from dycov.model.parameters import (
    Gen_params,
    Line_params,
    Load_init,
    Load_params,
    Pdr_equipments,
    Pdr_params,
    Xfmr_params,
)


def _get_generator_values(
    dyd_root: etree.Element,
    par_root: etree.Element,
    producer_ini: configparser.ConfigParser,
) -> list:
    generators = []
    # Generators
    for model_parameter in find_bbmodel_by_type(dyd_root, "GeneratorSynchronous"):
        _append_generator(dyd_root, par_root, model_parameter, generators, producer_ini)

    # WindTurbine Parks
    for model_parameter in find_bbmodel_by_type(dyd_root, "IECWPP"):
        _append_generator(dyd_root, par_root, model_parameter, generators, producer_ini)
    for model_parameter in find_bbmodel_by_type(dyd_root, "WTG4"):
        _append_generator(dyd_root, par_root, model_parameter, generators, producer_ini)

    # WindTurbines
    for model_parameter in find_bbmodel_by_type(dyd_root, "IECWT"):
        _append_generator(dyd_root, par_root, model_parameter, generators, producer_ini)
    for model_parameter in find_bbmodel_by_type(dyd_root, "WT4"):
        if "IECWT" in model_parameter.get("lib"):
            continue
        _append_generator(dyd_root, par_root, model_parameter, generators, producer_ini)

    # Photovoltaics
    for model_parameter in find_bbmodel_by_type(dyd_root, "PhotovoltaicsWecc"):
        _append_generator(dyd_root, par_root, model_parameter, generators, producer_ini)

    # BESS
    for model_parameter in find_bbmodel_by_type(dyd_root, "BESS"):
        _append_generator(dyd_root, par_root, model_parameter, generators, producer_ini)

    if generators:
        total_p = sum(g.P for g in generators)
        total_q = sum(g.Q for g in generators)

        if not math.isclose(total_p, 1.0):
            dycov_logging.get_logger("Model Parameters").error(
                "Generator P flows do not add up to 1"
            )
            raise ValueError("Generator P flows do not add up to 1")

        if not math.isclose(total_q, 1.0):
            dycov_logging.get_logger("Model Parameters").error(
                "Generator Q flows do not add up to 1"
            )
            raise ValueError("Generator Q flows do not add up to 1")

    return generators


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
    dyn = etree.QName(dyd_root).namespace
    ns = etree.QName(par_root).namespace

    connectedXmfr = None

    for connect in dyd_root.findall(f".//{{{dyn}}}connect"):
        if connect.get("id1") == gen_id:
            connectedXmfr = connect.get("id2")
            break
        elif connect.get("id2") == gen_id:
            connectedXmfr = connect.get("id1")
            break

    parset = par_root.find(f"{{{ns}}}set[@id='{par_id}']")
    if parset is None:
        raise ValueError(f"No se encontró el conjunto de parámetros con id='{par_id}'")

    # Use _get_parameter where applicable (it already centralizes variable lookup via the translator)
    sign, imaxpu_element = _get_parameter(parset, ns, lib, "InjectedCurrentMax")
    imax = float(imaxpu_element) * sign if imaxpu_element is not None else None

    default_section = "DEFAULT"

    if not producer_ini:
        _, P_str = _get_parameter(parset, ns, lib, "ActivePower0Pu")
        P = float(P_str) if P_str is not None else 0.0
    elif producer_ini.has_option(default_section, f"P_sharing_{gen_id}"):
        P_sharing = producer_ini.get(default_section, f"P_sharing_{gen_id}")
        P = float(P_sharing)
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
        _, Q_str = _get_parameter(parset, ns, lib, "ReactivePower0Pu")
        Q = float(Q_str) if Q_str is not None else 0.0
    elif producer_ini.has_option(default_section, f"Q_sharing_{gen_id}"):
        Q_sharing = producer_ini.get(default_section, f"Q_sharing_{gen_id}")
        Q = float(Q_sharing)
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

    _, VoltageDroop_str = _get_parameter(parset, ns, lib, "VoltageDroop")
    droop_value = float(VoltageDroop_str) if VoltageDroop_str is not None else 0.0

    _, s_nom_str = _get_parameter(parset, ns, lib, "NominalApparentPower")
    s_nom = float(s_nom_str) if s_nom_str is not None else 0.0

    generators.append(
        Gen_params(
            id=gen_id,
            lib=lib,
            connectedXmfr=connectedXmfr,
            SNom=s_nom,
            IMax=imax,
            par_id=par_id,
            P=P,
            Q=Q,
            VoltageDroop=droop_value,
            UseVoltageDroop=False,
        )
    )


def _get_line_values(
    dyd_root: etree.Element,
    par_root: etree.Element,
    applied_line_rpu: float,
    applied_line_xpu: float,
) -> list:
    lines = []
    ns = etree.QName(par_root).namespace
    for model_parameter in find_bbmodel_by_type(dyd_root, "Line"):
        line_id = model_parameter.get("id")
        lib = model_parameter.get("lib")
        par_id = model_parameter.get("parId")
        # Parameter Set from which to extract the line parameters
        parset = par_root.find(f"{{{ns}}}set[@id='{par_id}']")

        # Use _get_parameter for all line parameters
        _, r_str = _get_parameter(parset, ns, lib, "ResistancePu")
        _, x_str = _get_parameter(parset, ns, lib, "ReactancePu")
        _, b_str = _get_parameter(parset, ns, lib, "SusceptancePu")
        _, g_str = _get_parameter(parset, ns, lib, "ConductancePu")

        if applied_line_rpu is None:
            line_rpu = float(r_str)
        else:
            line_rpu = applied_line_rpu

        if applied_line_xpu is None:
            line_xpu = float(x_str)
        else:
            if x_str and "{{line_XPu}}" in x_str:
                line_xpu = applied_line_xpu
            elif x_str and "{{line1_XPu}}" in x_str:
                line_xpu = applied_line_xpu * 0.01
            elif x_str and "{{line99_XPu}}" in x_str:
                line_xpu = applied_line_xpu * 0.99

        line_gpu = float(g_str) if g_str is not None else 0.0
        line_bpu = float(b_str) if b_str is not None else 0.0
        connected = _are_connected(dyd_root, line_id, "BusPDR")

        lines.append(Line_params(line_id, lib, connected, line_rpu, line_xpu, line_bpu, line_gpu))

    return lines


def _get_transformer_values(
    dyd_root: etree.Element,
    par_root: etree.Element,
    s_nref: float,
) -> list:
    transformers = []
    ns = etree.QName(par_root).namespace
    for bbmodel in find_bbmodel_by_type(dyd_root, "Transformer"):
        transformer_id = bbmodel.get("id")
        lib = bbmodel.get("lib")
        par_id = bbmodel.get("parId")
        # Parameter Set from which to extract the transformer parameters
        parset = par_root.find(f"{{{ns}}}set[@id='{par_id}']")

        # Not all Transformer models provide their params in pu
        _, r_str = _get_parameter(parset, ns, lib, "Resistance")
        _, x_str = _get_parameter(parset, ns, lib, "Reactance")
        _, g_str = _get_parameter(parset, ns, lib, "Conductance")
        _, b_str = _get_parameter(parset, ns, lib, "Susceptance")
        units_inPu = dynawo_translator.get_dynawo_variable(lib, "Resistance")[1].endswith("Pu")

        if not units_inPu:
            _, snom_str = _get_parameter(parset, ns, lib, "SNom")
            s_nom = float(snom_str)  # Asume que SNom no será None o fallará

            # Conversión con valores obtenidos
            xfmr_rpu = (s_nref / s_nom) * float(r_str) / 100
            xfmr_xpu = (s_nref / s_nom) * float(x_str) / 100
            xfmr_gpu = (s_nom / s_nref) * float(g_str) / 100
            xfmr_bpu = (s_nom / s_nref) * float(b_str) / 100
        else:
            xfmr_rpu = float(r_str)
            xfmr_xpu = float(x_str)
            xfmr_gpu = float(g_str)
            xfmr_bpu = float(b_str)

        # If there's a regulating tap, get rTfo0Pu; otherwise get rTfoPu
        _, rho_str = _get_parameter(parset, ns, lib, "Rho")
        xfmr_tapr = float(rho_str)

        transformers.append(
            Xfmr_params(
                transformer_id,
                lib,
                xfmr_rpu,
                xfmr_xpu,
                xfmr_bpu,
                xfmr_gpu,
                xfmr_tapr,
                par_id,
            )
        )

    return transformers


def _get_load_values(dyd_root: etree.Element, par_root: etree.Element) -> list:
    loads = []
    ns = etree.QName(par_root).namespace
    for bbmodel in find_bbmodel_by_type(dyd_root, "Load"):
        load_id = bbmodel.get("id")
        lib = bbmodel.get("lib")
        par_id = bbmodel.get("parId")
        connectedXmfr = _find_connect_by_id(dyd_root, load_id)

        # Parameter Set from which to extract the transformer parameters
        parset = par_root.find(f"{{{ns}}}set[@id='{par_id}']")

        sign_P, p0_value = _get_parameter(parset, ns, lib, "ActivePower0")
        sign_Q, q0_value = _get_parameter(parset, ns, lib, "ReactivePower0")
        _, u0_value = _get_parameter(parset, ns, lib, "Voltage0")
        _, ph0_value = _get_parameter(parset, ns, lib, "Phase0")
        _, alpha_value = _get_parameter(parset, ns, lib, "Alpha")
        _, beta_value = _get_parameter(parset, ns, lib, "Beta")

        # Check if value contains a float or a placeholder
        # preserve original behavior: if string contains '{' then treat as placeholder
        def _resolve_value(raw, sign):
            if raw is None:
                return None
            if isinstance(raw, str) and raw.startswith("{") and raw.endswith("}"):
                return raw.replace("{", "").replace("}", "")
            try:
                return float(raw) * sign
            except (ValueError, TypeError):
                # if cannot convert, return raw
                return raw

        aux_ppu = _resolve_value(p0_value, sign_P)
        aux_qpu = _resolve_value(q0_value, sign_Q)
        aux_upu = _resolve_value(u0_value, 1)
        aux_phpu = _resolve_value(ph0_value, 1)

        loads.append(
            Load_params(
                load_id,
                lib,
                connectedXmfr,
                aux_ppu,
                aux_qpu,
                aux_upu,
                aux_phpu,
                None if alpha_value is None else float(alpha_value),
                None if beta_value is None else float(beta_value),
            )
        )

    return loads


def _find_connect_by_id(producer_dyd_root: etree.Element, model_id: str) -> Optional[str]:
    ns = etree.QName(producer_dyd_root).namespace
    for connect in producer_dyd_root.iterfind(f"{{{ns}}}connect"):
        if model_id in connect.get("id1"):
            return connect.get("id2")
        if model_id in connect.get("id2"):
            return connect.get("id1")

    return None


def _are_connected(producer_dyd_root: etree.Element, model_id1: str, model_id2: str) -> bool:
    ns = etree.QName(producer_dyd_root).namespace
    for connect in producer_dyd_root.iterfind(f"{{{ns}}}connect"):
        if model_id1 in connect.get("id1") and model_id2 in connect.get("id2"):
            return True
        if model_id1 in connect.get("id2") and model_id2 in connect.get("id1"):
            return True

    return False


def _adjust_transformer(
    producer_par_root: etree.Element,
    transformer: Xfmr_params,
    generator_p0pu: float,
    generator_q0pu: float,
    generator_u0pu: float,
    generator_uphase0: float,
    pdr: Pdr_params,
) -> None:
    ns = etree.QName(producer_par_root).namespace
    parset = producer_par_root.find(f"{{{ns}}}set[@id='{transformer.par_id}']")
    if parset is None:
        return

    sign, active_power0 = dynawo_translator.get_dynawo_variable(transformer.lib, "ActivePower0")
    _set_parameter(parset, ns, active_power0, sign, generator_p0pu)

    sign, reactive_power0 = dynawo_translator.get_dynawo_variable(
        transformer.lib, "ReactivePower0"
    )
    _set_parameter(parset, ns, reactive_power0, sign, generator_q0pu)

    sign = 1
    _, voltage0 = dynawo_translator.get_dynawo_variable(transformer.lib, "Voltage0")
    _set_parameter(parset, ns, voltage0, sign, generator_u0pu)

    _, phase0 = dynawo_translator.get_dynawo_variable(transformer.lib, "Phase0")
    _set_parameter(parset, ns, phase0, sign, generator_uphase0)

    _, voltage_setpoint = dynawo_translator.get_dynawo_variable(transformer.lib, "VoltageSetpoint")
    _set_parameter(parset, ns, voltage_setpoint, sign, pdr.U)


def _adjust_generator(
    producer_par_root: etree.Element,
    generator: Gen_params,
    generator_p0pu: float,
    generator_q0pu: float,
    generator_u0pu: float,
    generator_uphase0: float,
    generator_control_mode: str,
    force_voltage_droop: bool,
) -> None:
    """Modify the Producer generator to add the init values.
    MODEL_DEPENDENT_CODE
    """
    ns = etree.QName(producer_par_root).namespace
    parset = producer_par_root.find(f"{{{ns}}}set[@id='{generator.par_id}']")
    if parset is None:
        return

    sign, active_power0 = dynawo_translator.get_dynawo_variable(generator.lib, "ActivePower0Pu")
    _set_parameter(parset, ns, active_power0, sign, generator_p0pu)

    sign, reactive_power0 = dynawo_translator.get_dynawo_variable(
        generator.lib, "ReactivePower0Pu"
    )
    _set_parameter(parset, ns, reactive_power0, sign, generator_q0pu)

    sign = 1
    _, voltage0 = dynawo_translator.get_dynawo_variable(generator.lib, "Voltage0Pu")
    _set_parameter(parset, ns, voltage0, sign, generator_u0pu)

    _, phase0 = dynawo_translator.get_dynawo_variable(generator.lib, "Phase0")
    _set_parameter(parset, ns, phase0, sign, generator_uphase0)

    control_mode_name = _set_control_mode(
        generator, parset, ns, generator_control_mode, force_voltage_droop
    )

    _set_voltage_droop(
        generator, parset, ns, generator_control_mode, control_mode_name, force_voltage_droop
    )


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


def _set_voltage_droop(
    generator, parset, ns, generator_control_mode, control_mode_name, force_voltage_droop
) -> None:
    # Get the generator voltage droop parameters from the producer PAR file.
    voltage_droop_parameters = _get_voltage_droop_parameters(generator, parset, ns)
    dycov_logging.get_logger("Model Parameters").debug(
        f"Generator {generator.id} Voltage Droop Mode: {voltage_droop_parameters}"
    )
    # If the generator has not voltage droop parameters return, like NonPlant Controller units.
    if not voltage_droop_parameters:
        force_voltage_droop = False

    # If the control mode is reactive, disable voltage droop
    if control_mode_name:
        force_voltage_droop = not dynawo_translator.is_reactive_control_mode(
            generator, control_mode_name
        )

    if force_voltage_droop:
        # Check if the configured voltage droop is valid
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
                _set_parameters(generator, parset, ns, default_voltage_droop_parameters)
            else:
                dycov_logging.get_logger("Model Parameters").error(
                    f"{generator.lib} executed with wrong voltage droop mode"
                )
                raise ValueError(f"{generator.lib} executed with wrong voltage droop mode")

    _recalculate_voltage_ref(generator, voltage_droop_parameters)


def _set_control_mode(generator, parset, ns, generator_control_mode, force_voltage_droop) -> str:
    # Get the generator control mode parameters from the producer PAR file.
    control_mode_parameters = _get_control_mode_parameters(generator, parset, ns)
    dycov_logging.get_logger("Model Parameters").debug(
        f"Generator {generator.id} Control Mode: {control_mode_parameters}"
    )
    # If the generator has not control mode parameters return.
    if not control_mode_parameters:
        return

    # Check if the configured control mode is valid
    is_valid, control_mode_name = dynawo_translator.is_valid_control_mode(
        generator, generator_control_mode, control_mode_parameters
    )
    if generator_control_mode != "Others" and not is_valid:
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
            _set_parameters(generator, parset, ns, default_control_mode_parameters)
        else:
            dycov_logging.get_logger("Model Parameters").error(
                f"{generator.lib} executed with wrong control mode"
            )
            raise ValueError(f"{generator.lib} executed with wrong control mode")

    return control_mode_name


def _get_voltage_droop_parameters(generator, parset, ns) -> dict:
    if "IEC" in generator.lib:
        return _get_voltage_droop_parameters_iec(generator, parset, ns)
    elif "Wecc" in generator.lib:
        return _get_voltage_droop_parameters_wecc(generator, parset, ns)
    else:
        return {}


def _get_voltage_droop_parameters_iec(generator, parset, ns) -> dict:
    parameters = {}
    _, dynawo_variable = dynawo_translator.get_dynawo_variable(generator.lib, "MwpqMode")
    par = parset.find(f"{{{ns}}}par[@name='{dynawo_variable}']")
    if par is not None:
        parameters["MwpqMode"] = par.get("value")

    _, dynawo_variable = dynawo_translator.get_dynawo_variable(generator.lib, "MqG")
    par = parset.find(f"{{{ns}}}par[@name='{dynawo_variable}']")
    if par is not None:
        parameters["MqG"] = par.get("value")

    return parameters


def _get_voltage_droop_parameters_wecc(generator, parset, ns) -> dict:
    parameters = {}
    _, dynawo_variable = dynawo_translator.get_dynawo_variable(generator.lib, "RefFlag")
    par = parset.find(f"{{{ns}}}par[@name='{dynawo_variable}']")
    if par is not None:
        parameters["RefFlag"] = par.get("value")

    _, dynawo_variable = dynawo_translator.get_dynawo_variable(generator.lib, "VCompFlag")
    par = parset.find(f"{{{ns}}}par[@name='{dynawo_variable}']")
    if par is not None:
        parameters["VCompFlag"] = par.get("value")
    return parameters


def _get_control_mode_parameters(generator, parset, ns) -> dict:
    if "IEC" in generator.lib:
        return _get_control_mode_parameters_iec(generator, parset, ns)
    elif "Wecc" in generator.lib:
        return _get_control_mode_parameters_wecc(generator, parset, ns)
    else:
        return {}


def _get_control_mode_parameters_iec(generator, parset, ns) -> dict:
    parameters = {}
    _, dynawo_variable = dynawo_translator.get_dynawo_variable(generator.lib, "MwpqMode")
    par = parset.find(f"{{{ns}}}par[@name='{dynawo_variable}']")
    if par is not None:
        parameters["MwpqMode"] = par.get("value")

    _, dynawo_variable = dynawo_translator.get_dynawo_variable(generator.lib, "MqG")
    par = parset.find(f"{{{ns}}}par[@name='{dynawo_variable}']")
    if par is not None:
        parameters["MqG"] = par.get("value")

    return parameters


def _get_control_mode_parameters_wecc(generator, parset, ns) -> dict:
    parameters = {}
    # Use _get_parameter where it helps to centralize lookup
    _, PfFlag = _get_parameter(parset, ns, generator.lib, "PfFlag")
    if PfFlag is not None:
        parameters["PfFlag"] = PfFlag

    _, VFlag = _get_parameter(parset, ns, generator.lib, "VFlag")
    if VFlag is not None:
        parameters["VFlag"] = VFlag

    _, PFlag = _get_parameter(parset, ns, generator.lib, "PFlag")
    if PFlag is not None:
        parameters["PFlag"] = PFlag

    _, QFlag = _get_parameter(parset, ns, generator.lib, "QFlag")
    if QFlag is not None:
        parameters["QFlag"] = QFlag

    _, RefFlag = _get_parameter(parset, ns, generator.lib, "RefFlag")
    if RefFlag is not None:
        parameters["RefFlag"] = RefFlag

    _, FreqFlag = _get_parameter(parset, ns, generator.lib, "FreqFlag")
    if FreqFlag is not None:
        parameters["FreqFlag"] = FreqFlag

    return parameters


def _get_default_voltage_droop_parameters(generator, generator_voltage_droop) -> dict:
    family, level = get_generator_family_level(generator)
    parameters = {}
    section = f"{generator_voltage_droop}_{family}_{level}"
    if config.has_key(section, "control_option"):
        control_option = config.get_int(section, "control_option", 1)
        parameters = dynawo_translator.get_control_mode(section, control_option)
    else:
        options = config.get_options(section)
        for option in options:
            parameters[option] = config.get_value(section, option)
    return parameters


def _get_default_control_mode_parameters(generator, generator_control_mode) -> dict:
    family, level = get_generator_family_level(generator)
    parameters = {}
    section = f"{generator_control_mode}_{family}_{level}"
    if config.has_key(section, "control_option"):
        control_option = config.get_int(section, "control_option", 1)
        parameters = dynawo_translator.get_control_mode(section, control_option)
    else:
        options = config.get_options(section)
        for option in options:
            parameters[option] = config.get_value(section, option)
    return parameters


def _set_parameters(generator, parset, ns, parameters: dict):
    for name, value in parameters.items():
        _, dynawo_name = dynawo_translator.get_dynawo_variable(generator.lib, name)
        _set_parameter(parset, ns, dynawo_name, 1, value.lower())


def _adjust_load(
    producer_par_root: etree.Element,
    load: Load_init,
    load_p0pu: float,
    load_q0pu: float,
    load_u0pu: float,
    load_uphase0: float,
) -> None:
    ns = etree.QName(producer_par_root).namespace
    parset = producer_par_root.find(f"{{{ns}}}set[@id='{load.id}']")
    if parset is None:
        return

    sign, active_power0 = dynawo_translator.get_dynawo_variable(load.lib, "ActivePower0")
    _set_parameter(parset, ns, active_power0, sign, load_p0pu)

    sign, reactive_power0 = dynawo_translator.get_dynawo_variable(load.lib, "ReactivePower0")
    _set_parameter(parset, ns, reactive_power0, sign, load_q0pu)

    sign = 1
    _, voltage0 = dynawo_translator.get_dynawo_variable(load.lib, "Voltage0")
    _set_parameter(parset, ns, voltage0, sign, load_u0pu)

    _, phase0 = dynawo_translator.get_dynawo_variable(load.lib, "Phase0")
    _set_parameter(parset, ns, phase0, sign, load_uphase0)


def _set_parameter(parset, ns, parameter_name, sign, parameter_value):
    if parameter_name is None:
        return

    parameter = parset.find(f"{{{ns}}}par[@name='{parameter_name}']")
    if parameter is not None:
        parameter.set("value", str(sign * parameter_value))


def _get_parameter(parset, ns, lib, parameter_name):
    sign, variable_name = dynawo_translator.get_dynawo_variable(lib, parameter_name)
    if variable_name is not None:
        variable = parset.find(f"{{{ns}}}par[@name='{variable_name}']")
        return sign, variable.get("value")
    else:
        return None, None


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
    ns = etree.QName(producer_dyd_root).namespace
    for bbmodel in producer_dyd_root.iterfind(f"{{{ns}}}blackBoxModel"):
        if model_type in bbmodel.get("lib"):
            bbmodels.append(bbmodel)

    return bbmodels


def get_connected_to_pdr(producer_dyd: Path) -> list:
    producer_dyd_tree = etree.parse(producer_dyd, etree.XMLParser(remove_blank_text=True))
    producer_dyd_root = producer_dyd_tree.getroot()

    connected_to_pdr = []
    ns = etree.QName(producer_dyd_root).namespace
    for connect in producer_dyd_root.iterfind(f"{{{ns}}}connect"):
        if "BusPDR" in connect.get("id1"):
            connected_to_pdr.append(Pdr_equipments(connect.get("id2"), connect.get("var2")))
        if "BusPDR" in connect.get("id2"):
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
    for model_parameter in find_bbmodel_by_type(pcs_dyd_root, "GeneratorSynchronous"):
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

    return Load_params(None, None, None, ppu, qpu, None, None, None, None)


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

    root = etree_par.getroot()
    ns = etree.QName(root).namespace
    tbegin_parameters = root.find(f".//{{{ns}}}par[@name='fault_tBegin']")
    if tbegin_parameters is not None:
        tevent1 = float(tbegin_parameters.get("value"))
    else:
        tevent1 = float("NaN")

    tevent_parameters = root.find(f".//{{{ns}}}par[@name='event_tEvent']")
    tstep_parameters = root.find(f".//{{{ns}}}par[@name='step_tStep']")
    if tevent_parameters is not None and not tevent_parameters.get("value").startswith("{"):
        tevent2 = float(tevent_parameters.get("value"))
    elif tstep_parameters is not None and not tstep_parameters.get("value").startswith("{"):
        tevent2 = float(tstep_parameters.get("value"))
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
    ns = etree.QName(root).namespace
    output_dir = None
    for model_output in root.iter("{%s}outputs" % ns):
        output_dir = model_output.get("directory")
    return output_dir


def extract_defined_value(
    value_definition: str, parameter: str, base_value: float, sign: int = 1
) -> float:
    """Converts a parameter definition to a value.
    Examples:
        - P = P_max -> value_definition: 'pmax', parameter: 'pmax', base_value: 90, return 90
        - X = 2*b -> value_definition: '2*b', parameter: 'b', base_value: 0.2, return 0.4

    Parameters
    ----------
    value_definition: str
        Parameter value definition
    parameter: str
        Parameter name
    base_value: float
        Base value
    sign: int
        Sign of the value

    Returns
    -------
    float
        The value of the operation defined with the given base value
    """
    multiplier = 1
    if value_definition is None:
        raise ValueError(f"{parameter} parameter not defined.")

    if "*" in value_definition:
        parts = value_definition.split("*")
        multiplier = float(parts[0])
        value = parts[1]
    else:
        value = value_definition

    if parameter.lower() in value.lower():
        value = base_value

    return sign * float(value) * multiplier


def adjust_producer_init(
    path: Path,
    producer_par: Path,
    generators: list,
    xfmrs: list,
    gens: list,
    aux_load: Load_init,
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
    gens: float
        Initial values to the producer's generators
    aux_load: Load_init
        Initial values to the producer's auxiliary load
    pdr: Pdr_params
        Initial values for the transformer on the PDR side
    generator_control_mode: str
        Control mode
    force_voltage_droop: bool
        Force the voltage droop to be applied even if the control mode is not VoltageDroop
    """

    producer_par_tree = etree.parse(producer_par, etree.XMLParser(remove_blank_text=True))
    producer_par_root = producer_par_tree.getroot()

    for generator, xfmr, gen in zip(generators, xfmrs, gens):
        _adjust_transformer(
            producer_par_root,
            xfmr,
            -gen.P0,
            -gen.Q0,
            gen.U0,
            gen.UPhase0,
            pdr,
        )
        _adjust_generator(
            producer_par_root,
            generator,
            gen.P0,
            gen.Q0,
            gen.U0,
            gen.UPhase0,
            generator_control_mode,
            force_voltage_droop,
        )

    if aux_load:
        _adjust_load(
            producer_par_root,
            aux_load,
            aux_load.P0,
            aux_load.Q0,
            aux_load.U0,
            aux_load.UPhase0,
        )

    producer_par_tree.write(path / producer_par.name, pretty_print=True)
