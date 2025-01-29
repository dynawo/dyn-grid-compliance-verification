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

from dgcv.configuration.cfg import config
from dgcv.core.global_variables import ELECTRIC_PERFORMANCE_SM, MODEL_VALIDATION_PPM
from dgcv.dynawo.translator import dynawo_translator


def _add_curves_dict(
    id: str, variable: str, type: str, dynawo_variable: str, sign: int, curves_dict: dict
) -> bool:
    key = f"{id}_{dynawo_variable}"
    curve = f"{id}_{type}_{variable}"
    curves_dict[curve] = sign

    if key not in curves_dict:
        curves_dict[key] = [curve]
        return True
    else:
        curves_dict[key].append(curve)

    return False


def _add_curve_to_file(
    curves_root: etree.Element,
    model: str,
    variable: str,
    type: str,
    dynawo_variable: str,
    curves_dict: dict,
):
    sign = 1
    if dynawo_variable.startswith("-"):
        sign = -1
        dynawo_variable = dynawo_variable[1:]

    if _add_curves_dict(model, variable, type, dynawo_variable, sign, curves_dict):
        etree.SubElement(
            curves_root,
            "curve",
            model=f"{model}",
            variable=f"{dynawo_variable}",
        )


def _add_bus_curves(curves_root: etree.Element, zone: int, curves_dict: dict) -> None:
    bus_variables = ["VoltageRe", "VoltageIm"]
    for variable in bus_variables:
        dynawo_variable = dynawo_translator.get_dynawo_variable("Bus", variable)
        if not dynawo_variable:
            continue

        _add_curve_to_file(curves_root, "BusPDR", variable, "BUS", dynawo_variable, curves_dict)
    if zone == 1:
        dynawo_variable = dynawo_translator.get_dynawo_variable(
            "InfiniteBus", "NetworkFrequencyPu"
        )
        _add_curve_to_file(
            curves_root, "InfiniteBus", "NetworkFrequencyPu", "BUS", dynawo_variable, curves_dict
        )


def _add_pdr_curves(curves_root: etree.Element, connected_to_pdr: list, curves_dict: dict) -> None:
    equipment_variables = ["VoltageRe", "VoltageIm", "CurrentRe", "CurrentIm"]
    terminal_variables = ["V_re", "V_im", "i_re", "i_im"]
    for equipment in connected_to_pdr:
        for variable, terminal_variable in zip(equipment_variables, terminal_variables):
            dynawo_variable = equipment.var + "_" + terminal_variable
            etree.SubElement(
                curves_root,
                "curve",
                model=f"{equipment.id}",
                variable=f"{dynawo_variable}",
            )
            key = f"{equipment.id}_{dynawo_variable}"
            curves_dict[key] = [f"BusPDR_TE_{equipment.id}_{variable}"]
            curves_dict[f"BusPDR_TE_{equipment.id}_{variable}"] = 1


def _add_xfmrs_curves(curves_root: etree.Element, xfmrs: list, curves_dict: dict) -> None:
    xfmr_variables = ["Tap"]
    for xfmr in xfmrs:
        for variable in xfmr_variables:
            dynawo_variable = dynawo_translator.get_dynawo_variable(xfmr.lib, variable)
            if not dynawo_variable:
                continue

            _add_curve_to_file(
                curves_root, xfmr.id, variable, "XFMR", dynawo_variable, curves_dict
            )


def _is_composed_setpoint(
    generator_lib: str, tool_variable: str, dynawo_variable: str, control_mode: str
) -> bool:
    # Some models use the same variable to assign the setpoint of Q and V, to avoid
    # showing the wrong setpoint in the figures, we only use the setpoint according to the
    # assigned control mode.

    # If the control mode is not one of those affected, False is returned.
    if control_mode == "USetpoint":
        control_variable = "AVRSetpointPu"
    elif control_mode == "QSetpoint":
        control_variable = "ReactivePowerSetpointPu"
    else:
        return False

    # If the input variable is the complementary variable to the control mode, False is returned.
    if tool_variable == control_variable:
        return False

    # If the model defines different variables for the Q and V setpoints, False is returned.
    if dynawo_variable != dynawo_translator.get_dynawo_variable(generator_lib, control_variable):
        return False

    return True


def _add_generators_curves(
    curves_root: etree.Element,
    generators: list,
    generator_variables: list,
    control_mode: str,
    curves_dict: dict,
) -> None:

    for generator in generators:
        for variable in generator_variables:
            dynawo_variable = dynawo_translator.get_dynawo_variable(generator.lib, variable)
            if not dynawo_variable:
                continue

            if _is_composed_setpoint(generator.lib, variable, dynawo_variable, control_mode):
                continue

            _add_curve_to_file(
                curves_root, generator.id, variable, "GEN", dynawo_variable, curves_dict
            )


def _add_sm_curves(
    curves_root: etree.Element,
    generators: list,
    control_mode: str,
    curves_dict: dict,
) -> None:
    generator_variables = config.get_list("CurvesVariables", "SM")
    _add_generators_curves(curves_root, generators, generator_variables, control_mode, curves_dict)


def _add_ppm_curves(
    curves_root: etree.Element,
    generators: list,
    control_mode: str,
    curves_dict: dict,
) -> None:
    generator_variables = config.get_list("CurvesVariables", "PPM")
    _add_generators_curves(curves_root, generators, generator_variables, control_mode, curves_dict)


def _add_model_validation_curves(
    curves_root: etree.Element,
    generators: list,
    zone: int,
    control_mode: str,
    curves_dict: dict,
) -> None:
    if zone == 3:
        generator_variables = config.get_list("CurvesVariables", "ModelValidationZ3")
    elif zone == 1:
        generator_variables = config.get_list("CurvesVariables", "ModelValidationZ1")
    else:
        generator_variables = []
    _add_generators_curves(curves_root, generators, generator_variables, control_mode, curves_dict)


def create_curves_file(
    path: Path,
    curves_filename: str,
    connected_to_pdr: list,
    xfmrs: list,
    generators: list,
    rte_loads: list,
    sim_type: int,
    zone: int,
    control_mode: str,
) -> dict:
    """Creates the CRV file to Dynawo.

    Parameters
    ----------
    path: Path
        Path to the CRV file
    curves_filename: str
        Name of the CRV file
    connected_to_pdr: list
        Equipments connected to the bus PDR in Producer side
    xfmrs: list
        Transformer in the Producer side
    generators: list
        Generators in the Producer side
    rte_loads: list
        Loads in the TSO side, if the model have loads
    sim_type: int
        0 if it is an electrical performance for Synchronous Machine Model
        1 if it is an electrical performance for Power Park Module Model
        2 if it is a model validation
    zone: int
        If it is running the Model Validation:
        * 1: Zone1 (the individual generating unit)
        * 3: Zone3 (the whole plant)
    control_mode: str
        Control mode

    Returns
    -------
    dict
        Dictionary of the variables that the curves are obtained and their equivalent in Dynawo
    """
    curves_dict = {}

    curves_root = etree.fromstring(
        """<curvesInput xmlns="http://www.rte-france.com/dynawo"></curvesInput>"""
    )

    _add_bus_curves(curves_root, zone, curves_dict)
    _add_pdr_curves(curves_root, connected_to_pdr, curves_dict)
    _add_xfmrs_curves(curves_root, xfmrs, curves_dict)
    if sim_type == ELECTRIC_PERFORMANCE_SM:
        _add_sm_curves(curves_root, generators, control_mode, curves_dict)
    elif sim_type >= MODEL_VALIDATION_PPM:
        _add_model_validation_curves(curves_root, generators, zone, control_mode, curves_dict)
    else:
        _add_ppm_curves(curves_root, generators, control_mode, curves_dict)

    # This process is done to parse the news Elements and make the pretty_print work correctly
    curves_tree = etree.ElementTree(
        etree.fromstring(etree.tostring(curves_root), etree.XMLParser(remove_blank_text=True))
    )
    curves_tree.write(
        path / curves_filename, encoding="utf-8", pretty_print=True, xml_declaration=True
    )
    return curves_dict
