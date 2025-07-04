#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023-2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""
This module provides functions for validating Dynawo model topologies based on
expected and actual components and their connections.
"""
from typing import List

from dycov.model.parameters import Gen_params, Line_params, Load_params, Xfmr_params

_GENERATOR_ERROR_MESSAGE = (
    "  - A generator with id:\n"
    "      * 'Synch_Gen' if a synchronous generator is modeled\n"
    "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
    "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
    "      * 'Bess' if a storage or a park of storages is modeled\n"
)

_MULTIPLE_GENERATOR_ERROR_MESSAGE = (
    "  - Two or more generators, their ids start with:\n"
    "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
    "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
    "      * 'Bess' if a storage or a park of storages is modeled\n"
)


def _check_topology_components(
    topology_name: str,
    generators: List[Gen_params],
    transformers: List[Xfmr_params],
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
    expected_gen_count: str,  # "single" or "multiple"
    expected_xfmr_count: str,  # "single" or "multiple"
    expect_aux_load: bool,
    expect_aux_xfmr: bool,
    expect_main_xfmr: bool,
    expect_internal_line: bool,
    generator_bus_connection: str,  # "PDR bus" or "internal line" or "internal bus"
    aux_load_bus_connection: str,  # "PDR bus" or "internal bus"
    main_xfmr_bus_connection: str,
    # "internal bus and the PDR bus" or "internal bus and the internal line"
    internal_line_bus_connection: str,
    # "transformer and the PDR bus" or "transformer with id 'transformer' and the PDR bus"
) -> None:
    expected_elements = True
    unexpected_elements = False
    valid_elements = True
    error_messages = []

    # Check expected generator count
    if expected_gen_count == "single":
        if len(generators) != 1:
            expected_elements = False
            error_messages.append(_GENERATOR_ERROR_MESSAGE)
        else:
            # Validate the single generator based on topology name (S for Synch_Gen)
            valid_elements = valid_elements and _is_valid_generator(
                generators[0].id, add_sm=(topology_name[0] == "S")
            )
    elif expected_gen_count == "multiple":
        if len(generators) <= 1:
            expected_elements = False
            error_messages.append(_MULTIPLE_GENERATOR_ERROR_MESSAGE)
        else:
            # Validate multiple generators
            valid_elements = valid_elements and _is_valid_generators(generators)

    # Check expected transformer count
    if expected_xfmr_count == "single":
        if len(transformers) != 1:
            expected_elements = False
            error_messages.append("  - A transformer with id 'StepUp_Xfmr'\n")
        else:
            # Validate the single step-up transformer
            valid_elements = valid_elements and _is_valid_stepup_xfmr(transformers, generators)
    elif expected_xfmr_count == "multiple":
        if len(transformers) <= 1:
            expected_elements = False
            error_messages.append(
                "  - A transformer for each generator, its id starts with 'StepUp_Xfmr'\n"
            )
        else:
            # Validate multiple step-up transformers
            valid_elements = valid_elements and _is_valid_stepup_xfmr(transformers, generators)

    # Check for auxiliary load presence and validity
    if expect_aux_load:
        if auxiliary_load is None:
            expected_elements = False
            error_messages.append("  - An auxiliary load with id 'Aux_Load'\n")
        else:
            valid_elements = valid_elements and _is_valid_auxiliary_load(auxiliary_load)
    elif auxiliary_load is not None:
        # If aux load is not expected but present, flag as unexpected
        unexpected_elements = True

    # Check for auxiliary transformer presence and validity
    if expect_aux_xfmr:
        if auxiliary_transformer is None:
            expected_elements = False
            error_messages.append("  - A transformer with id 'AuxLoad_Xfmr'\n")
        else:
            valid_elements = valid_elements and _is_valid_auxiliary_transformer(
                auxiliary_transformer
            )
    elif auxiliary_transformer is not None:
        # If aux transformer is not expected but present, flag as unexpected
        unexpected_elements = True

    # Check for main transformer presence and validity
    if expect_main_xfmr:
        if transformer is None:
            expected_elements = False
            error_messages.append("  - A transformer with id 'Main_Xfmr'\n")
        else:
            valid_elements = valid_elements and _is_valid_transformer(transformer)
    elif transformer is not None:
        # If main transformer is not expected but present, flag as unexpected
        unexpected_elements = True

    # Check for internal line presence and validity
    if expect_internal_line:
        if internal_line is None:
            expected_elements = False
            error_messages.append("  - An internal line with id 'IntNetwork_Line'\n")
        else:
            valid_elements = valid_elements and _is_valid_internal_line(internal_line)
    elif internal_line is not None:
        # If internal line is not expected but present, flag as unexpected
        unexpected_elements = True

    # Determine overall topology validity
    valid_topology = expected_elements and not unexpected_elements and valid_elements

    # If topology is not valid, construct and raise a ValueError with detailed messages
    if not valid_topology:
        base_message = f"The '{topology_name}' topology expects the following models:\n"
        full_message = base_message + "".join(error_messages)

        # Add specific connection messages if elements are expected and valid
        if (
            expected_gen_count == "single"
            and len(generators) == 1
            and _is_valid_generator(generators[0].id, add_sm=(topology_name[0] == "S"))
        ):
            full_message += "  - A transformer with id 'StepUp_Xfmr' connected between "
            full_message += f"the generator and the {generator_bus_connection}\n"
        if (
            expect_aux_load
            and auxiliary_load is not None
            and _is_valid_auxiliary_load(auxiliary_load)
        ):
            full_message += "  - A transformer with id 'AuxLoad_Xfmr' connected between the "
            full_message += f"auxiliary load and the {aux_load_bus_connection}\n"
        if expect_main_xfmr and transformer is not None and _is_valid_transformer(transformer):
            full_message += "  - A transformer with id 'Main_Xfmr' connected between the "
            full_message += f"{main_xfmr_bus_connection}\n"
        if (
            expect_internal_line
            and internal_line is not None
            and _is_valid_internal_line(internal_line)
        ):
            full_message += "  - An internal line with id 'IntNetwork_Line' connected between "
            full_message += f"the {internal_line_bus_connection}\n"

        raise ValueError(full_message)


def _is_valid_generators(generators: List[Gen_params]) -> bool:
    # Iterate through each generator
    for generator in generators:
        # For multiple generators, 'Synch_Gen' is not allowed as per original messages.
        if not _is_valid_generator(generator.id, add_sm=False):
            return False  # Return False if any generator is invalid
    return True  # All generators are valid


def _is_valid_generator(gen_id: str, add_sm: bool = True) -> bool:
    # Define valid generator types
    gen_types = ["Wind_Turbine", "PV_Array", "Bess"]
    # Add 'Synch_Gen' to valid types if add_sm is True (for 'S' topologies)
    if add_sm:
        gen_types.append("Synch_Gen")
    # Check if the generator ID contains any of the valid generator type substrings
    if any(gen_type in gen_id for gen_type in gen_types):
        return True  # Generator ID is valid
    return False  # Generator ID is not valid


def _is_valid_stepup_xfmr(transformers: List[Xfmr_params], generators: List[Gen_params]) -> bool:
    # Extract IDs of transformers that start with 'StepUp_Xfmr'
    ids = [
        stepup_xfmr.id for stepup_xfmr in transformers if stepup_xfmr.id.startswith("StepUp_Xfmr")
    ]
    # Check if the count of valid step-up transformers matches the number of generators
    return len(generators) == len(ids)


def _is_valid_auxiliary_transformer(auxiliary_transformer: Xfmr_params) -> bool:
    # Check if the auxiliary transformer exists and its ID is 'AuxLoad_Xfmr'
    if auxiliary_transformer is not None and auxiliary_transformer.id == "AuxLoad_Xfmr":
        return True  # Auxiliary transformer is valid
    return False  # Auxiliary transformer is not valid


def _is_valid_transformer(transformer: Xfmr_params) -> bool:
    # Check if the main transformer exists and its ID is 'Main_Xfmr'
    if transformer is not None and transformer.id == "Main_Xfmr":
        return True  # Main transformer is valid
    return False  # Main transformer is not valid


def _is_valid_auxiliary_load(auxiliary_load: Load_params) -> bool:
    # Check if the auxiliary load exists and its ID is 'Aux_Load'
    if auxiliary_load is not None and auxiliary_load.id == "Aux_Load":
        return True  # Auxiliary load is valid
    return False  # Auxiliary load is not valid


def _is_valid_internal_line(internal_line: Line_params) -> bool:
    # Check if the internal line exists and its ID is 'IntNetwork_Line'
    if internal_line is not None and internal_line.id == "IntNetwork_Line":
        return True  # Internal line is valid
    return False  # Internal line is not valid


def check_topology(
    topology: str,
    generators: List[Gen_params],
    transformers: List[Xfmr_params],
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:
    """
    Checks if one of the 8 allowed topologies has been selected, and if the correct devices
    have been defined for the selected topology.

    Parameters
    ----------
    topology: str
        Selected topology.
    generators: list
        Producer model generators.
    transformers: list
        Transformers connected to the generators of the producer model.
    auxiliary_load: Load_params
        Auxiliary load connected to the generators of the producer model.
    auxiliary_transformer: Xfmr_params
        Transformer connected to the auxiliary load of the producer model.
    transformer: Xfmr_params
        Transformer that groups all the transformer of the producer model.
    internal_line: Line_params
        Internal line of the producer model.

    Raises
    ------
    ValueError
        If an invalid topology is selected or if the required devices for the
        selected topology are not correctly defined.
    """
    # Define configurations for each allowed topology
    topology_configs = {
        "s": {
            "expected_gen_count": "single",
            "expected_xfmr_count": "single",
            "expect_aux_load": False,
            "expect_aux_xfmr": False,
            "expect_main_xfmr": False,
            "expect_internal_line": False,
            "generator_bus_connection": "PDR bus",
            "aux_load_bus_connection": "",
            "main_xfmr_bus_connection": "",
            "internal_line_bus_connection": "",
        },
        "s+i": {
            "expected_gen_count": "single",
            "expected_xfmr_count": "single",
            "expect_aux_load": False,
            "expect_aux_xfmr": False,
            "expect_main_xfmr": False,
            "expect_internal_line": True,
            "generator_bus_connection": "internal line",
            "aux_load_bus_connection": "",
            "main_xfmr_bus_connection": "",
            "internal_line_bus_connection": "transformer and the PDR bus",
        },
        "s+aux": {
            "expected_gen_count": "single",
            "expected_xfmr_count": "single",
            "expect_aux_load": True,
            "expect_aux_xfmr": True,
            "expect_main_xfmr": False,
            "expect_internal_line": False,
            "generator_bus_connection": "PDR bus",
            "aux_load_bus_connection": "PDR bus",
            "main_xfmr_bus_connection": "",
            "internal_line_bus_connection": "",
        },
        "s+aux+i": {
            "expected_gen_count": "single",
            "expected_xfmr_count": "single",
            "expect_aux_load": True,
            "expect_aux_xfmr": True,
            "expect_main_xfmr": False,
            "expect_internal_line": True,
            "generator_bus_connection": "internal bus",
            "aux_load_bus_connection": "internal bus",
            "main_xfmr_bus_connection": "",
            "internal_line_bus_connection": "transformer and the PDR bus",
        },
        "m": {
            "expected_gen_count": "multiple",
            "expected_xfmr_count": "multiple",
            "expect_aux_load": False,
            "expect_aux_xfmr": False,
            "expect_main_xfmr": True,
            "expect_internal_line": False,
            "generator_bus_connection": "internal bus",
            "aux_load_bus_connection": "",
            "main_xfmr_bus_connection": "internal bus and the PDR bus",
            "internal_line_bus_connection": "",
        },
        "m+i": {
            "expected_gen_count": "multiple",
            "expected_xfmr_count": "multiple",
            "expect_aux_load": False,
            "expect_aux_xfmr": False,
            "expect_main_xfmr": True,
            "expect_internal_line": True,
            "generator_bus_connection": "internal bus",
            "aux_load_bus_connection": "",
            "main_xfmr_bus_connection": "internal bus and the internal line",
            "internal_line_bus_connection": "transformer with id 'transformer' and the PDR bus",
        },
        "m+aux": {
            "expected_gen_count": "multiple",
            "expected_xfmr_count": "multiple",
            "expect_aux_load": True,
            "expect_aux_xfmr": True,
            "expect_main_xfmr": True,
            "expect_internal_line": False,
            "generator_bus_connection": "internal bus",
            "aux_load_bus_connection": "internal bus",
            "main_xfmr_bus_connection": "internal bus and the PDR bus",
            "internal_line_bus_connection": "",
        },
        "m+aux+i": {
            "expected_gen_count": "multiple",
            "expected_xfmr_count": "multiple",
            "expect_aux_load": True,
            "expect_aux_xfmr": True,
            "expect_main_xfmr": True,
            "expect_internal_line": True,
            "generator_bus_connection": "internal bus",
            "aux_load_bus_connection": "internal bus",
            "main_xfmr_bus_connection": "internal bus and the internal line",
            "internal_line_bus_connection": "transformer with id 'transformer' and the PDR bus",
        },
    }

    topology_lower = (
        topology.casefold()
    )  # Convert topology name to lowercase for case-insensitive matching
    if topology_lower in topology_configs:
        config = topology_configs[
            topology_lower
        ]  # Get the configuration for the selected topology
        # Call the base topology check function with the determined configuration
        _check_topology_components(
            topology,
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
            config["expected_gen_count"],
            config["expected_xfmr_count"],
            config["expect_aux_load"],
            config["expect_aux_xfmr"],
            config["expect_main_xfmr"],
            config["expect_internal_line"],
            config["generator_bus_connection"],
            config["aux_load_bus_connection"],
            config["main_xfmr_bus_connection"],
            config["internal_line_bus_connection"],
        )
    else:
        # Raise an error if the selected topology is not one of the 8 allowed options
        raise ValueError(
            "Select one of the 8 available topologies:\n"
            "  - S\n"
            "  - S+i\n"
            "  - S+Aux\n"
            "  - S+Aux+i\n"
            "  - M\n"
            "  - M+i\n"
            "  - M+Aux\n"
            "  - M+Aux+i\n"
        )
