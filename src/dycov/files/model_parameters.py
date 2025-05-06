#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

# TODO: remove generator types ("GeneratorSynchronous", "IECWPP", "WTG4", etc. ==> we'll need
#       entries in the master dictionary).
#       The same goes for generator families ("IEC", "Wecc").
#

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

from lxml import etree

from dycov.configuration.cfg import config
from dycov.dynawo.translator import dynawo_translator, get_generator_family_level
from dycov.logging.logging import dycov_logging
from dycov.model.parameters import (
    EquivIntLine_params,
    Gen_params,
    Line_params,
    Load_init,
    Load_params,
    Pdr_equipments,
    Pdr_params,
    Xfmr_params,
)


def _get_generator_values(dyd_root: etree.Element, par_root: etree.Element) -> list:
    generators = []
    # Generators
    for model_parameter in find_bbmodel_by_type(dyd_root, "GeneratorSynchronous"):
        _append_generator(dyd_root, par_root, model_parameter, generators)

    # WindTurbine Parks
    for model_parameter in find_bbmodel_by_type(dyd_root, "IECWPP"):
        _append_generator(dyd_root, par_root, model_parameter, generators)
    for model_parameter in find_bbmodel_by_type(dyd_root, "WTG4"):
        _append_generator(dyd_root, par_root, model_parameter, generators)

    # WindTurbines
    for model_parameter in find_bbmodel_by_type(dyd_root, "IECWT"):
        _append_generator(dyd_root, par_root, model_parameter, generators)
    for model_parameter in find_bbmodel_by_type(dyd_root, "WT4"):
        if "IECWT" in model_parameter.get("lib"):
            continue
        _append_generator(dyd_root, par_root, model_parameter, generators)

    # Photovoltaics
    for model_parameter in find_bbmodel_by_type(dyd_root, "PhotovoltaicsWecc"):
        _append_generator(dyd_root, par_root, model_parameter, generators)

    # BESS
    for model_parameter in find_bbmodel_by_type(dyd_root, "BESS"):
        _append_generator(dyd_root, par_root, model_parameter, generators)

    return generators


def _append_generator(
    dyd_root: etree.Element,
    par_root: etree.Element,
    model_parameter: etree.Element,
    generators: list,
):
    gen_id = model_parameter.get("id")
    par_id = model_parameter.get("parId")
    lib = model_parameter.get("lib")
    dyn = etree.QName(dyd_root).namespace
    ns = etree.QName(par_root).namespace

    dydset1 = dyd_root.find(f".//{{{dyn}}}connect[@id1='{gen_id}']")
    dydset2 = dyd_root.find(f".//{{{dyn}}}connect[@id2='{gen_id}']")
    if dydset1 is not None:
        connectedXmfr = dydset1.get("id2")
    elif dydset2 is not None:
        connectedXmfr = dydset2.get("id1")
    else:
        connectedXmfr = None

    # Parameter Set from which to extract the generator parameters we need
    parset = par_root.find(f"{{{ns}}}set[@id='{par_id}']")

    sign, generator_imax = dynawo_translator.get_dynawo_variable(lib, "InjectedCurrentMax")
    imaxpu = parset.find(f"{{{ns}}}par[@name='{generator_imax}']")
    if imaxpu is not None:
        imax = float(imaxpu.get("value")) * sign
    else:
        imax = None

    sign, generator_P = dynawo_translator.get_dynawo_variable(lib, "ActivePower0Pu")
    p0pu = parset.find(f"{{{ns}}}par[@name='{generator_P}']")
    P = float(p0pu.get("value")) * sign
    sign, generator_Q = dynawo_translator.get_dynawo_variable(lib, "ReactivePower0Pu")
    q0pu = parset.find(f"{{{ns}}}par[@name='{generator_Q}']")
    Q = float(q0pu.get("value")) * sign

    _, generator_VoltageDrop = dynawo_translator.get_dynawo_variable(lib, "VoltageDrop")
    if generator_VoltageDrop is not None:
        gVoltageDrop = parset.find(f"{{{ns}}}par[@name='{generator_VoltageDrop}']")
        VoltageDrop = float(gVoltageDrop.get("value"))
    else:
        VoltageDrop = 0.0

    _, generator_SNom = dynawo_translator.get_dynawo_variable(lib, "NominalApparentPower")
    snom_par = parset.find(f"{{{ns}}}par[@name='{generator_SNom}']")
    s_nom = float(snom_par.get("value"))

    _, equiv_int_line_RPu = dynawo_translator.get_dynawo_variable(lib, "EquivIntLineRPu")
    if equiv_int_line_RPu is not None:
        rpu_par = parset.find(f"{{{ns}}}par[@name='{equiv_int_line_RPu}']")
        rpu = float(rpu_par.get("value"))
    else:
        rpu = 0.0

    _, equiv_int_line_RSourcePu = dynawo_translator.get_dynawo_variable(
        lib, "EquivIntLineRSourcePu"
    )
    if equiv_int_line_RSourcePu is not None:
        rsourcepu_par = parset.find(f"{{{ns}}}par[@name='{equiv_int_line_RSourcePu}']")
        rsourcepu = float(rsourcepu_par.get("value"))
    else:
        rsourcepu = 0.0

    _, equiv_int_line_XPu = dynawo_translator.get_dynawo_variable(lib, "EquivIntLineXPu")
    if equiv_int_line_XPu is not None:
        xpu_par = parset.find(f"{{{ns}}}par[@name='{equiv_int_line_XPu}']")
        xpu = float(xpu_par.get("value"))
    else:
        xpu = 0.0

    _, equiv_int_line_XSourcePu = dynawo_translator.get_dynawo_variable(
        lib, "EquivIntLineXSourcePu"
    )
    if equiv_int_line_XSourcePu is not None:
        xsourcepu_par = parset.find(f"{{{ns}}}par[@name='{equiv_int_line_XSourcePu}']")
        xsourcepu = float(xsourcepu_par.get("value"))
    else:
        xsourcepu = 0.0

    _, equiv_int_line_BPu = dynawo_translator.get_dynawo_variable(lib, "EquivIntLineBPu")
    if equiv_int_line_BPu is not None:
        bpu_par = parset.find(f"{{{ns}}}par[@name='{equiv_int_line_BPu}']")
        bpu = float(bpu_par.get("value"))
    else:
        bpu = 0.0

    _, equiv_int_line_GPu = dynawo_translator.get_dynawo_variable(lib, "EquivIntLineGPu")
    if equiv_int_line_GPu is not None:
        gpu_par = parset.find(f"{{{ns}}}par[@name='{equiv_int_line_GPu}']")
        gpu = float(gpu_par.get("value"))
    else:
        gpu = 0.0

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
            VoltageDrop=VoltageDrop,
            UseVoltageDrop=False,
            equiv_int_line=EquivIntLine_params(rpu, xpu, rsourcepu, xsourcepu, bpu, gpu),
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

        _, line_R = dynawo_translator.get_dynawo_variable(lib, "ResistancePu")
        _, line_X = dynawo_translator.get_dynawo_variable(lib, "ReactancePu")
        _, line_B = dynawo_translator.get_dynawo_variable(lib, "SusceptancePu")
        _, line_G = dynawo_translator.get_dynawo_variable(lib, "ConductancePu")
        r_par = parset.find(f"{{{ns}}}par[@name='{line_R}']")
        x_par = parset.find(f"{{{ns}}}par[@name='{line_X}']")
        b_par = parset.find(f"{{{ns}}}par[@name='{line_B}']")
        g_par = parset.find(f"{{{ns}}}par[@name='{line_G}']")

        if applied_line_rpu is None:
            line_rpu = float(r_par.get("value"))
        else:
            line_rpu = applied_line_rpu

        if applied_line_xpu is None:
            line_xpu = float(x_par.get("value"))
        else:
            if "{{line_XPu}}" in x_par.get("value"):
                line_xpu = applied_line_xpu
            elif "{{line1_XPu}}" in x_par.get("value"):
                line_xpu = applied_line_xpu * 0.01
            elif "{{line99_XPu}}" in x_par.get("value"):
                line_xpu = applied_line_xpu * 0.99

        line_gpu = float(g_par.get("value"))
        line_bpu = float(b_par.get("value"))
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
        _, transformer_R = dynawo_translator.get_dynawo_variable(lib, "Resistance")
        _, transformer_X = dynawo_translator.get_dynawo_variable(lib, "Reactance")
        _, transformer_B = dynawo_translator.get_dynawo_variable(lib, "Susceptance")
        _, transformer_G = dynawo_translator.get_dynawo_variable(lib, "Conductance")
        r_par = parset.find(f"{{{ns}}}par[@name='{transformer_R}']")
        x_par = parset.find(f"{{{ns}}}par[@name='{transformer_X}']")
        g_par = parset.find(f"{{{ns}}}par[@name='{transformer_G}']")
        b_par = parset.find(f"{{{ns}}}par[@name='{transformer_B}']")
        units_inPu = transformer_R.endswith("Pu")
        if not units_inPu:
            _, transformer_SNom = dynawo_translator.get_dynawo_variable(lib, "SNom")
            snom_par = parset.find(f"{{{ns}}}par[@name='{transformer_SNom}']")
            s_nom = float(snom_par.get("value"))
            xfmr_rpu = (s_nref / s_nom) * float(r_par.get("value")) / 100
            xfmr_xpu = (s_nref / s_nom) * float(x_par.get("value")) / 100
            xfmr_gpu = (s_nom / s_nref) * float(g_par.get("value")) / 100
            xfmr_bpu = (s_nom / s_nref) * float(b_par.get("value")) / 100
        else:
            xfmr_rpu = float(r_par.get("value"))
            xfmr_xpu = float(x_par.get("value"))
            xfmr_gpu = float(g_par.get("value"))
            xfmr_bpu = float(b_par.get("value"))

        # If there's a regulating tap, get rTfo0Pu; otherwise get rTfoPu
        _, transformer_rTfoPu = dynawo_translator.get_dynawo_variable(lib, "Rho")
        tap_par = parset.find(f"{{{ns}}}par[@name='{transformer_rTfoPu}']")
        xfmr_tapr = float(tap_par.get("value"))

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

        sign_P, load_P0 = dynawo_translator.get_dynawo_variable(lib, "ActivePower0")
        sign_Q, load_Q0 = dynawo_translator.get_dynawo_variable(lib, "ReactivePower0")
        _, load_U0 = dynawo_translator.get_dynawo_variable(lib, "Voltage0")
        _, load_Ph0 = dynawo_translator.get_dynawo_variable(lib, "Phase0")
        _, load_alpha = dynawo_translator.get_dynawo_variable(lib, "Alpha")
        _, load_beta = dynawo_translator.get_dynawo_variable(lib, "Beta")
        p0_par = parset.find(f"{{{ns}}}par[@name='{load_P0}']")
        q0_par = parset.find(f"{{{ns}}}par[@name='{load_Q0}']")
        u0_par = parset.find(f"{{{ns}}}par[@name='{load_U0}']")
        ph0_par = parset.find(f"{{{ns}}}par[@name='{load_Ph0}']")
        alpha_value = None
        if load_alpha is not None:
            alpha_par = parset.find(f"{{{ns}}}par[@name='{load_alpha}']")
            alpha_value = float(alpha_par.get("value"))
        beta_value = None
        if load_beta is not None:
            beta_par = parset.find(f"{{{ns}}}par[@name='{load_beta}']")
            beta_value = float(beta_par.get("value"))

        # Check if value contains a float or a placeholder
        if "{" in p0_par.get("value"):
            aux_ppu = p0_par.get("value").replace("{", "").replace("}", "") * sign_P
            aux_qpu = q0_par.get("value").replace("{", "").replace("}", "") * sign_Q
            aux_upu = u0_par.get("value").replace("{", "").replace("}", "")
            aux_phpu = ph0_par.get("value").replace("{", "").replace("}", "")
        else:
            aux_ppu = float(p0_par.get("value")) * sign_P
            aux_qpu = float(q0_par.get("value")) * sign_Q
            aux_upu = float(u0_par.get("value"))
            aux_phpu = float(ph0_par.get("value"))

        loads.append(
            Load_params(
                load_id,
                lib,
                connectedXmfr,
                aux_ppu,
                aux_qpu,
                aux_upu,
                aux_phpu,
                alpha_value,
                beta_value,
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

    _set_control_mode(generator, parset, ns, generator_control_mode)


def _recalculate_voltage_ref(generator, parset, ns, control_mode_parameters) -> None:
    if "RefFlag" in control_mode_parameters:
        _, VCompFlag = dynawo_translator.get_dynawo_variable(generator.lib, "VCompFlag")
        par = parset.find(f"{{{ns}}}par[@name='{VCompFlag}']")
        if par is not None and par.get("value").lower() == "false":
            generator.UseVoltageDrop = True


def _set_control_mode(generator, parset, ns, generator_control_mode) -> None:
    if generator_control_mode == "USetpoint" or generator_control_mode == "QSetpoint":
        # Get the generator control mode parameters from the producer PAR file.
        control_mode_parameters = _get_control_mode_parameters(generator, parset, ns)
        dycov_logging.get_logger("Model Parameters").debug(
            f"Generator {generator.id} Control Mode: {control_mode_parameters}"
        )
        # If the generator has not control mode parameters return.
        if not control_mode_parameters:
            return

        # Check if the configured control mode is valid
        if dynawo_translator.is_valid_control_mode(
            generator, generator_control_mode, control_mode_parameters
        ):
            _recalculate_voltage_ref(generator, parset, ns, control_mode_parameters)

        else:
            dycov_logging.get_logger("Model Parameters").warning(
                f"{generator.lib} control mode will be changed"
            )
            default_control_mode_parameters = _get_default_control_mode_parameters(
                generator, generator_control_mode
            )
            dycov_logging.get_logger("Model Parameters").debug(
                f"Default Control Mode: {control_mode_parameters} for {generator_control_mode}"
            )
            if dynawo_translator.is_valid_control_mode(
                generator, generator_control_mode, default_control_mode_parameters
            ):
                _set_control_mode_parameters(
                    generator, parset, ns, default_control_mode_parameters
                )
                _recalculate_voltage_ref(generator, parset, ns, default_control_mode_parameters)
            else:
                dycov_logging.get_logger("Model Parameters").error(
                    f"{generator.lib} executed with wrong control mode"
                )
                raise ValueError(f"{generator.lib} executed with wrong control mode")

    return


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
    _, dynawo_variable = dynawo_translator.get_dynawo_variable(generator.lib, "PfFlag")
    par = parset.find(f"{{{ns}}}par[@name='{dynawo_variable}']")
    if par is not None:
        parameters["PfFlag"] = par.get("value")

    _, dynawo_variable = dynawo_translator.get_dynawo_variable(generator.lib, "VFlag")
    par = parset.find(f"{{{ns}}}par[@name='{dynawo_variable}']")
    if par is not None:
        parameters["VFlag"] = par.get("value")

    _, dynawo_variable = dynawo_translator.get_dynawo_variable(generator.lib, "QFlag")
    par = parset.find(f"{{{ns}}}par[@name='{dynawo_variable}']")
    if par is not None:
        parameters["QFlag"] = par.get("value")

    _, dynawo_variable = dynawo_translator.get_dynawo_variable(generator.lib, "RefFlag")
    par = parset.find(f"{{{ns}}}par[@name='{dynawo_variable}']")
    if par is not None:
        parameters["RefFlag"] = par.get("value")

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


def _set_control_mode_parameters(generator, parset, ns, control_mode_parameters: dict):
    for name, value in control_mode_parameters.items():
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
    s_nref: float,
) -> tuple[list, list, Load_params, Xfmr_params, Xfmr_params, Line_params]:
    """Gets the equipment parameters of the producer model.

    Parameters
    ----------
    producer_dyd: Path
        Path to the producer DYD file
    producer_par: Path
        Path to the producer PAR file
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

    generators = _get_generator_values(producer_dyd_root, producer_par_root)
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
