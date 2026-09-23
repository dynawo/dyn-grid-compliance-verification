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

from itertools import zip_longest
from pathlib import Path

from lxml import etree

from dycov.configuration.cfg import config
from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.files import par_access
from dycov.logging import dycov_logging
from dycov.model.parameters import (
    GenParams,
    LoadParams,
    PdrParams,
    XfmrParams,
)

"""Writing of the initial values back into the producer PAR file."""


def adjust_producer_init(
    path: Path,
    producer_par: Path,
    generators: list,
    xfmrs: list,
    aux_load: LoadParams,
    main_xfmr: XfmrParams,
    pdr: PdrParams,
    generator_control_mode: str,
    force_voltage_droop: bool,
    zone: int,
) -> bool:
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
    aux_load: LoadParams
        Initial values to the producer's auxiliary load
    main_xfmr: XfmrParams
        Initial values to the producer's main transformer
    pdr: PdrParams
        PDR parameters
    generator_control_mode: str
        Control mode
    force_voltage_droop: bool
        Force the voltage droop to be applied even if the control mode is not VoltageDroop
    zone: int
        Zone number, used to determine the control mode and voltage droop parameters

    Returns
    -------
    bool
        True if the control mode is valid for all generators, False otherwise
    """

    producer_par_tree = etree.parse(producer_par, etree.XMLParser(remove_blank_text=True))
    producer_par_root = producer_par_tree.getroot()

    _adjust_series_transformer(producer_par_root, main_xfmr)

    is_test_applicable = True
    for generator, xfmr in zip_longest(generators, xfmrs):
        if xfmr is not None:
            _adjust_transformer(
                producer_par_root,
                xfmr,
                xfmr.terminals[0].p0,
                xfmr.terminals[0].q0,
                xfmr.terminals[0].u0,
                xfmr.terminals[0].u_phase0,
                xfmr.terminals[1].u0,
            )
        is_control_mode_valid = _adjust_generator(
            producer_par_root,
            generator,
            generator.terminals[0].p0,
            generator.terminals[0].q0,
            generator.terminals[0].u0,
            generator.terminals[0].u_phase0,
            pdr,
            generator_control_mode,
            force_voltage_droop,
            zone,
        )
        is_test_applicable = is_test_applicable and is_control_mode_valid

    if aux_load:
        _adjust_load(
            producer_par_root,
            aux_load.id,
            aux_load.lib,
            aux_load.terminals[0].p0,
            aux_load.terminals[0].q0,
            aux_load.terminals[0].u0,
            aux_load.terminals[0].u_phase0,
        )

    producer_par_tree.write(path / producer_par.name, pretty_print=True)
    return is_test_applicable


def _adjust_series_transformer(producer_par_root, xfmr: XfmrParams) -> None:
    """Writes the init values of a transformer in series with the PDR, if there is one.

    A ratio tap changer needs the flow and both terminal voltages it starts from, and
    init_calcs has already recorded them on the transformer's terminals.
    """
    if xfmr is None:
        return

    _adjust_transformer(
        producer_par_root,
        xfmr,
        xfmr.terminals[0].p0,
        xfmr.terminals[0].q0,
        xfmr.terminals[0].u0,
        xfmr.terminals[0].u_phase0,
        xfmr.terminals[1].u0,
    )


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
    parset = par_access.get_parset(producer_par_root, transformer.par_id, nsmap)

    _set_transformer_power(parset, nsmap, transformer.lib, transformer_p10pu, transformer_q10pu)
    _set_transformer_voltage_phase(
        parset, nsmap, transformer.lib, transformer_u10pu, transformer_uphase10
    )
    _set_transformer_voltage(parset, nsmap, transformer.lib, transformer_u20pu)


def _set_transformer_power(parset, nsmap, lib, p0pu, q0pu):
    sign, active_power0 = dynawo_translator.get_dynawo_variable(lib, "ActivePower10")
    _set_parameter(parset, nsmap, active_power0, sign, p0pu, create_if_missing=True)
    sign, reactive_power0 = dynawo_translator.get_dynawo_variable(lib, "ReactivePower10")
    _set_parameter(parset, nsmap, reactive_power0, sign, q0pu, create_if_missing=True)


def _set_transformer_voltage_phase(parset, nsmap, lib, u0pu, uphase0):
    sign = 1
    _, voltage0 = dynawo_translator.get_dynawo_variable(lib, "Voltage10")
    _set_parameter(parset, nsmap, voltage0, sign, u0pu, create_if_missing=True)
    _, phase0 = dynawo_translator.get_dynawo_variable(lib, "Phase10")
    _set_parameter(parset, nsmap, phase0, sign, uphase0, create_if_missing=True)


def _set_transformer_voltage(parset, nsmap, lib, u0pu):
    sign = 1
    _, voltage_setpoint = dynawo_translator.get_dynawo_variable(lib, "Voltage20")
    _set_parameter(parset, nsmap, voltage_setpoint, sign, u0pu, create_if_missing=True)


def _adjust_generator(
    producer_par_root: etree.Element,
    generator: GenParams,
    generator_p0pu: float,
    generator_q0pu: float,
    generator_u0pu: float,
    generator_uphase0: float,
    pdr: PdrParams,
    generator_control_mode: str,
    force_voltage_droop: bool,
    zone: int,
) -> int:
    nsmap = {"ns": etree.QName(producer_par_root).namespace}
    parset = par_access.get_parset(producer_par_root, generator.par_id, nsmap)

    _set_initial_power(parset, nsmap, generator.lib, generator_p0pu, generator_q0pu)
    _set_initial_pcc_power(parset, nsmap, generator.lib, pdr)
    _set_initial_voltage_phase(parset, nsmap, generator.lib, generator_u0pu, generator_uphase0)
    _set_initial_pcc_voltage_phase(parset, nsmap, generator.lib, pdr)

    # For synchronous machine models, control mode and voltage droop adjustments are not
    # applicable.
    if dynawo_translator.is_synchronous_machine_model(generator):
        return True

    # Control mode and voltage droop are configured based on the zone.
    if zone != 1:
        zone = 3

    is_valid, control_mode_name = _apply_control_mode(
        generator, parset, nsmap, generator_control_mode, zone
    )
    if not config.get_boolean("General", "skip_voltage_droop_adjustment", default=False):
        _apply_voltage_droop(
            generator,
            parset,
            nsmap,
            generator_control_mode,
            control_mode_name,
            force_voltage_droop,
            zone,
        )

    return is_valid


def _set_initial_power(parset, nsmap, lib, p0pu, q0pu):
    sign, active_power0 = dynawo_translator.get_dynawo_variable(lib, "ActivePower0Pu")
    _set_parameter(parset, nsmap, active_power0, sign, p0pu, create_if_missing=True)
    sign, reactive_power0 = dynawo_translator.get_dynawo_variable(lib, "ReactivePower0Pu")
    _set_parameter(parset, nsmap, reactive_power0, sign, q0pu, create_if_missing=True)


def _set_initial_pcc_power(parset, nsmap, lib, pdr):
    sign, active_power0 = dynawo_translator.get_dynawo_variable(lib, "ActivePowerPcc0Pu")
    _set_parameter(parset, nsmap, active_power0, sign, -pdr.p, create_if_missing=True)
    sign, reactive_power0 = dynawo_translator.get_dynawo_variable(lib, "ReactivePowerPcc0Pu")
    _set_parameter(parset, nsmap, reactive_power0, sign, -pdr.q, create_if_missing=True)


def _set_initial_voltage_phase(parset, nsmap, lib, u0pu, uphase0):
    sign = 1
    _, voltage0 = dynawo_translator.get_dynawo_variable(lib, "Voltage0Pu")
    _set_parameter(parset, nsmap, voltage0, sign, u0pu, create_if_missing=True)
    _, phase0 = dynawo_translator.get_dynawo_variable(lib, "Phase0")
    _set_parameter(parset, nsmap, phase0, sign, uphase0, create_if_missing=True)


def _set_initial_pcc_voltage_phase(parset, nsmap, lib, pdr):
    sign = 1
    _, voltage0 = dynawo_translator.get_dynawo_variable(lib, "VoltagePcc0Pu")
    _set_parameter(parset, nsmap, voltage0, sign, pdr.u, create_if_missing=True)
    _, phase0 = dynawo_translator.get_dynawo_variable(lib, "PhasePcc0")
    _set_parameter(parset, nsmap, phase0, sign, pdr.u_phase, create_if_missing=True)


def _apply_control_mode(generator, parset, nsmap, generator_control_mode, zone):
    control_mode_parameters = _get_control_mode_parameters(generator, parset, nsmap, zone)
    _log_control_mode(generator, control_mode_parameters)

    if not control_mode_parameters:
        return False, None

    is_valid, control_mode_name = dynawo_translator.is_valid_control_mode(
        generator, generator_control_mode, control_mode_parameters, zone
    )

    return is_valid, control_mode_name


def _log_control_mode(generator, control_mode_parameters):
    dycov_logging.get_logger("Model Parameters").debug(
        f"Generator {generator.id} Control Mode: {control_mode_parameters}"
    )


def _apply_voltage_droop(
    generator, parset, nsmap, generator_control_mode, control_mode_name, force_voltage_droop, zone
):
    voltage_droop_parameters = _get_voltage_droop_parameters(generator, parset, nsmap, zone)
    _log_voltage_droop(generator, voltage_droop_parameters)

    force_voltage_droop = _determine_voltage_droop(
        force_voltage_droop, control_mode_name, voltage_droop_parameters, generator, zone
    )

    if force_voltage_droop:
        _validate_or_apply_default_voltage_droop(
            generator, parset, nsmap, generator_control_mode, voltage_droop_parameters, zone
        )

    _recalculate_voltage_ref(generator, voltage_droop_parameters)


def _log_voltage_droop(generator, voltage_droop_parameters):
    dycov_logging.get_logger("Model Parameters").debug(
        f"Generator {generator.id} Voltage Droop Mode: {voltage_droop_parameters}"
    )


def _determine_voltage_droop(
    force_voltage_droop, control_mode_name, voltage_droop_parameters, generator, zone
):
    if not voltage_droop_parameters:
        return False
    if control_mode_name:
        return not dynawo_translator.is_reactive_control_mode(generator, control_mode_name, zone)
    return force_voltage_droop


def _validate_or_apply_default_voltage_droop(
    generator, parset, nsmap, generator_control_mode, voltage_droop_parameters, zone
):
    is_valid, _ = dynawo_translator.is_valid_control_mode(
        generator, "VoltageDroop", voltage_droop_parameters, zone
    )
    if not is_valid and zone != 1:
        dycov_logging.get_logger("Model Parameters").warning(
            f"{generator.lib} voltage droop mode will be changed"
        )
        default_voltage_droop_parameters = _get_default_voltage_droop_parameters(
            generator, "VoltageDroop", zone
        )
        dycov_logging.get_logger("Model Parameters").debug(
            f"Default Voltage Droop Mode: {default_voltage_droop_parameters} "
            f"for {generator_control_mode}"
        )
        is_valid, _ = dynawo_translator.is_valid_control_mode(
            generator, "VoltageDroop", default_voltage_droop_parameters, zone
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
            generator.use_voltage_droop = True

    if all(p in voltage_droop_parameters for p in ["RefFlag", "VCompFlag"]):
        if voltage_droop_parameters["RefFlag"].lower() != "true":
            return
        if voltage_droop_parameters["VCompFlag"].lower() != "false":
            return
        generator.use_voltage_droop = True


def _get_voltage_droop_parameters(generator, parset, nsmap, zone) -> dict:
    parameters = {}
    parameter_names = dynawo_translator.get_generator_parameters(generator, "VoltageDroop", zone)
    for name in parameter_names:
        sign, value = par_access.get_parameter(parset, nsmap, generator.lib, name)
        if value is not None:
            parameters[name] = value

    return parameters


def _get_control_mode_parameters(generator, parset, nsmap, zone) -> dict:
    parameters = {}
    parameter_names = dynawo_translator.get_generator_parameters(generator, "ControlMode", zone)
    for name in parameter_names:
        sign, value = par_access.get_parameter(parset, nsmap, generator.lib, name)
        if value is not None:
            parameters[name] = value

    return parameters


def _get_default_voltage_droop_parameters(generator, generator_voltage_droop, zone) -> dict:
    family = dynawo_translator.get_generator_family(generator)
    parameters = {}
    section = f"{generator_voltage_droop}_{family}_Zone{zone}"
    if config.has_option(section, "control_option"):
        control_option = config.get_int(section, "control_option", 1)
        parameters = dynawo_translator.get_control_mode(section, control_option)
    else:
        options = config.get_options(section)
        for option in options:
            parameters[option] = config.get_value(section, option)
    return parameters


def _get_default_control_mode_parameters(generator, generator_control_mode, zone) -> dict:
    family = dynawo_translator.get_generator_family(generator)
    parameters = {}
    section = f"{generator_control_mode}_{family}_Zone{zone}"
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
    parset = par_access.get_parset(producer_par_root, load_id, nsmap)

    sign, active_power0 = dynawo_translator.get_dynawo_variable(load_lib, "ActivePower0")
    _set_parameter(parset, nsmap, active_power0, sign, load_p0pu, create_if_missing=True)

    sign, reactive_power0 = dynawo_translator.get_dynawo_variable(load_lib, "ReactivePower0")
    _set_parameter(parset, nsmap, reactive_power0, sign, load_q0pu, create_if_missing=True)

    sign = 1
    _, voltage0 = dynawo_translator.get_dynawo_variable(load_lib, "Voltage0")
    _set_parameter(parset, nsmap, voltage0, sign, load_u0pu, create_if_missing=True)

    _, phase0 = dynawo_translator.get_dynawo_variable(load_lib, "Phase0")
    _set_parameter(parset, nsmap, phase0, sign, load_uphase0, create_if_missing=True)


def _set_parameter(parset, nsmap, parameter_name, sign, parameter_value, create_if_missing=False):
    if not parameter_name:
        return
    ps = parset[0]
    parameter = ps.xpath(f"ns:par[@name='{parameter_name}']", namespaces=nsmap)
    if parameter:
        parameter[0].set("value", str(sign * parameter_value))
        return

    if not create_if_missing:
        return

    etree.SubElement(
        ps,
        etree.QName(nsmap["ns"], "par"),
        attrib={
            "name": parameter_name,
            "type": "DOUBLE",
            "value": str(sign * parameter_value),
        },
    )
