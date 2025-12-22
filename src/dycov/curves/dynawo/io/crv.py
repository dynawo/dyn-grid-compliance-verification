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

from dycov.configuration.cfg import config
from dycov.core.global_variables import ELECTRIC_PERFORMANCE_SM, MODEL_VALIDATION
from dycov.curves.dynawo.dictionary.translator import dynawo_translator


def _add_curves_dict(
    id: str, variable: str, type: str, dynawo_variable: str, sign: int, curves_dict: dict
) -> bool:
    """Adds a curve entry to the curves dictionary.

    Parameters
    ----------
    id : str
        The ID of the model (e.g., generator ID, bus ID).
    variable : str
        The variable name in the tool.
    type : str
        The type of the curve (e.g., "GEN", "BUS", "XFMR").
    dynawo_variable : str
        The corresponding variable name in Dynawo.
    sign : int
        The sign associated with the variable.
    curves_dict : dict
        The dictionary to which the curve entry will be added.

    Returns
    -------
    bool
        True if a new key for the dynawo_variable was created, False otherwise.
    """
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
    sign: int,
    dynawo_variable: str,
    curves_dict: dict,
):
    """Adds a curve element to the XML root and updates the curves dictionary.

    Parameters
    ----------
    curves_root : etree.Element
        The root XML element for curves.
    model : str
        The model ID associated with the curve.
    variable : str
        The variable name in the tool.
    type : str
        The type of the curve (e.g., "GEN", "BUS", "XFMR").
    sign : int
        The sign associated with the variable.
    dynawo_variable : str
        The corresponding variable name in Dynawo.
    curves_dict : dict
        The dictionary to which the curve entry will be added.
    """
    if _add_curves_dict(model, variable, type, dynawo_variable, sign, curves_dict):
        etree.SubElement(
            curves_root,
            "curve",
            model=f"{model}",
            variable=f"{dynawo_variable}",
        )


def _add_bus_curves(curves_root: etree.Element, zone: int, curves_dict: dict) -> None:
    """Adds bus-related curves to the XML root and curves dictionary.

    Parameters
    ----------
    curves_root : etree.Element
        The root XML element for curves.
    zone : int
        The zone ID.
    curves_dict : dict
        The dictionary to which curve entries will be added.
    """
    bus_variables = ["VoltageRe", "VoltageIm"]
    for variable in bus_variables:
        sign, dynawo_variable = dynawo_translator.get_dynawo_variable("Bus", variable)
        if dynawo_variable:  # Check if dynawo_variable is not empty
            _add_curve_to_file(
                curves_root, "BusPDR", variable, "BUS", sign, dynawo_variable, curves_dict
            )
    if zone == 1:
        sign, dynawo_variable = dynawo_translator.get_dynawo_variable(
            "InfiniteBus", "NetworkFrequencyPu"
        )
        if dynawo_variable:  # Check if dynawo_variable is not empty
            _add_curve_to_file(
                curves_root,
                "InfiniteBus",
                "NetworkFrequencyPu",
                "BUS",
                sign,
                dynawo_variable,
                curves_dict,
            )


def _add_pdr_curves(curves_root: etree.Element, connected_to_pdr: list, curves_dict: dict) -> None:
    """Adds PDR-related curves to the XML root and curves dictionary.

    Parameters
    ----------
    curves_root : etree.Element
        The root XML element for curves.
    connected_to_pdr : list
        List of equipment connected to the PDR bus.
    curves_dict : dict
        The dictionary to which curve entries will be added.
    """
    terminal_variables_map = {
        "VoltageRe": "V_re",
        "VoltageIm": "V_im",
        "CurrentRe": "i_re",
        "CurrentIm": "i_im",
    }
    etree.SubElement(
        curves_root,
        "curve",
        model="Measurements",
        variable="measurements_PPu",
    )
    etree.SubElement(
        curves_root,
        "curve",
        model="Measurements",
        variable="measurements_QPu",
    )
    etree.SubElement(
        curves_root,
        "curve",
        model="Measurements",
        variable="measurements_UPu",
    )

    for equipment in connected_to_pdr:
        for variable, terminal_variable in terminal_variables_map.items():
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
    """Adds transformer-related curves to the XML root and curves dictionary.

    Parameters
    ----------
    curves_root : etree.Element
        The root XML element for curves.
    xfmrs : list
        List of transformers.
    curves_dict : dict
        The dictionary to which curve entries will be added.
    """
    xfmr_variables = ["Tap"]
    for xfmr in xfmrs:
        for variable in xfmr_variables:
            sign, dynawo_variable = dynawo_translator.get_dynawo_variable(xfmr.lib, variable)
            if dynawo_variable:  # Check if dynawo_variable is not empty
                _add_curve_to_file(
                    curves_root, xfmr.id, variable, "XFMR", sign, dynawo_variable, curves_dict
                )


def _is_composed_setpoint(
    generator_lib: str, tool_variable: str, dynawo_variable: str, control_mode: str
) -> bool:
    """Checks if a variable is a composed setpoint to avoid showing wrong setpoints.

    Some models use the same variable to assign the setpoint of Q and V. To avoid
    showing the wrong setpoint in the figures, we only use the setpoint according to the
    assigned control mode.

    Parameters
    ----------
    generator_lib : str
        The library name of the generator.
    tool_variable : str
        The variable name used in the tool.
    dynawo_variable : str
        The corresponding variable name in Dynawo.
    control_mode : str
        The control mode of the generator (e.g., "USetpoint", "QSetpoint").

    Returns
    -------
    bool
        True if the variable is a composed setpoint that should be ignored, False otherwise.
    """
    control_variable = ""
    if control_mode == "USetpoint":
        control_variable = "AVRSetpointPu"
    elif control_mode == "QSetpoint":
        control_variable = "ReactivePowerSetpointPu"
    else:
        return False  # If the control mode is not one of those affected, False is returned.

    if tool_variable == control_variable:
        return False  # If the input variable is the complementary variable to the control mode,
        # False is returned.

    # If the model defines different variables for the Q and V setpoints, False is returned.
    # The comparison should be with the dynawo variable obtained from the generator_lib and
    # control_variable
    _, expected_dynawo_variable = dynawo_translator.get_dynawo_variable(
        generator_lib, control_variable
    )
    if dynawo_variable != expected_dynawo_variable:
        return False

    return True


def _add_generators_curves(
    curves_root: etree.Element,
    generators: list,
    generator_variables: list,
    control_mode: str,
    curves_dict: dict,
) -> None:
    """Adds generator-related curves to the XML root and curves dictionary.

    Parameters
    ----------
    curves_root : etree.Element
        The root XML element for curves.
    generators : list
        List of generators.
    generator_variables : list
        List of variables to add for each generator.
    control_mode : str
        The control mode of the generators.
    curves_dict : dict
        The dictionary to which curve entries will be added.
    """
    for generator in generators:
        for variable in generator_variables:
            sign, dynawo_variable = dynawo_translator.get_dynawo_variable(generator.lib, variable)

            if not dynawo_variable:
                # Check needed as long as there are Dynawo models that do not have
                # a variable that corresponds to U + lambda * Q. In these models,
                # the U and Q curves are needed to be able to perform the calculation
                # in the tool.
                if variable == "MagnitudeControlledByAVRPu":
                    # Handle specific case for combined AVR variables
                    for sub_variable in [
                        "MagnitudeControlledByAVRUPu",
                        "MagnitudeControlledByAVRQPu",
                    ]:
                        sign_sub, dynawo_variable_sub = dynawo_translator.get_dynawo_variable(
                            generator.lib, sub_variable
                        )
                        if dynawo_variable_sub:
                            _add_curve_to_file(
                                curves_root,
                                generator.id,
                                sub_variable,
                                "GEN",
                                sign_sub,
                                dynawo_variable_sub,
                                curves_dict,
                            )
                continue

            if _is_composed_setpoint(generator.lib, variable, dynawo_variable, control_mode):
                continue

            _add_curve_to_file(
                curves_root, generator.id, variable, "GEN", sign, dynawo_variable, curves_dict
            )


def create_curves_file(
    path: Path,
    curves_filename: str,
    connected_to_pdr: list,
    xfmrs: list,
    generators: list,
    rte_loads: list,  # This parameter is not used in the current implementation.
    sim_type: int,
    zone: int,
    control_mode: str,
) -> dict:
    """Creates the CRV file for Dynawo.

    Parameters
    ----------
    path: Path
        Path to the directory where the CRV file will be saved.
    curves_filename: str
        Name of the CRV file to be created.
    connected_to_pdr: list
        List of equipment connected to the PDR bus on the Producer side.
    xfmrs: list
        List of transformers on the Producer side.
    generators: list
        List of generators on the Producer side.
    rte_loads: list
        Loads on the TSO side, if the model has loads. (Currently not used)
    sim_type: int
        Type of simulation:
        * 1: Electrical performance for Synchronous Machine Model (ELECTRIC_PERFORMANCE_SM)
        * 2: Electrical performance for Power Park Module Model (PPM - handled by else case)
        * 3: Model validation (MODEL_VALIDATION)
    zone: int
        Relevant for Model Validation:
        * 1: Zone 1 (the individual generating unit)
        * 3: Zone 3 (the whole plant)
    control_mode: str
        The control mode of the generators.

    Returns
    -------
    dict
        Dictionary of the variables for which curves are obtained and their equivalent in Dynawo.
    """
    curves_dict = {}

    curves_root = etree.fromstring(
        """<curvesInput xmlns="http://www.rte-france.com/dynawo"></curvesInput>"""
    )

    _add_bus_curves(curves_root, zone, curves_dict)
    _add_pdr_curves(curves_root, connected_to_pdr, curves_dict)
    _add_xfmrs_curves(curves_root, xfmrs, curves_dict)

    if sim_type == ELECTRIC_PERFORMANCE_SM:
        generator_variables = config.get_list("CurvesVariables", "SM")
    elif (
        sim_type > MODEL_VALIDATION
    ):  # Covers MODEL_VALIDATION (3) and potentially other higher values
        if zone == 3:
            generator_variables = config.get_list("CurvesVariables", "ModelValidationZ3")
        elif zone == 1:
            generator_variables = config.get_list("CurvesVariables", "ModelValidationZ1")
        else:
            generator_variables = []
    else:  # Assumed to be PPM for sim_type == 2
        generator_variables = config.get_list("CurvesVariables", "PPM")

    _add_generators_curves(curves_root, generators, generator_variables, control_mode, curves_dict)

    # This process is done to parse the new Elements and make pretty_print work correctly
    curves_tree = etree.ElementTree(
        etree.fromstring(etree.tostring(curves_root), etree.XMLParser(remove_blank_text=True))
    )
    curves_tree.write(
        path / curves_filename, encoding="utf-8", pretty_print=True, xml_declaration=True
    )
    return curves_dict
