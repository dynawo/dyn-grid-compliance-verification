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

from typing import List, Optional

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
    auxiliary_load: Optional[Load_params],
    auxiliary_transformer: Optional[Xfmr_params],
    main_transformer: Optional[Xfmr_params],
    internal_line: Optional[Line_params],
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
    """
    Validate the topology configuration by checking expected components, their count,
    and connections.

    Raises:
        ValueError: If the topology does not meet expected requirements.
    """

    error_messages = []

    def add_error(msg: str):
        error_messages.append(f"  - {msg}")

    # Declarative expectations
    expectations = [
        {
            "name": "Generators",
            "count": expected_gen_count,
            "items": generators,
            "validators": {
                "single": lambda: _is_valid_generator(
                    generators[0].id, add_sm=topology_name.startswith("S")
                ),
                "multiple": lambda: _is_valid_generators(generators),
            },
            "messages": {
                "single": "A single generator is expected.",
                "multiple": "Multiple generators are expected.",
                "invalid_single": "Invalid generator configuration.",
                "invalid_multiple": "Invalid generators configuration.",
            },
        },
        {
            "name": "Step-up Transformers",
            "count": expected_xfmr_count,
            "items": transformers,
            "validators": {
                "single": lambda: _is_valid_stepup_xfmr(transformers, generators),
                "multiple": lambda: _is_valid_stepup_xfmr(transformers, generators),
            },
            "messages": {
                "single": "A transformer with id 'StepUp_Xfmr' is expected.",
                "multiple": "Multiple step-up transformers are expected.",
                "invalid_single": "Invalid step-up transformer configuration.",
                "invalid_multiple": "Invalid step-up transformers configuration.",
            },
        },
    ]

    # Validate generators and transformers
    for exp in expectations:
        if exp["count"] == "single":
            if len(exp["items"]) != 1:
                add_error(exp["messages"]["single"])
            elif not exp["validators"]["single"]:
                add_error(exp["messages"]["invalid_single"])
        elif exp["count"] == "multiple":
            if len(exp["items"]) <= 1:
                add_error(exp["messages"]["multiple"])
            elif not exp["validators"]["multiple"]:
                add_error(exp["messages"]["invalid_multiple"])

    # Validate optional components
    def validate_optional(expect: bool, component, name: str, validator, expected_msg: str):
        if expect:
            if component is None:
                add_error(expected_msg)
            elif not validator(component):
                add_error(f"Invalid {name} configuration.")
        elif component is not None:
            add_error(f"Unexpected {name} found.")

    validate_optional(
        expect_aux_load,
        auxiliary_load,
        "Aux_Load",
        _is_valid_auxiliary_load,
        "An auxiliary load with id 'Aux_Load' is expected.",
    )
    validate_optional(
        expect_aux_xfmr,
        auxiliary_transformer,
        "AuxLoad_Xfmr",
        _is_valid_auxiliary_transformer,
        "A transformer with id 'AuxLoad_Xfmr' is expected.",
    )
    validate_optional(
        expect_main_xfmr,
        main_transformer,
        "Main_Xfmr",
        _is_valid_transformer,
        "A transformer with id 'Main_Xfmr' is expected.",
    )
    validate_optional(
        expect_internal_line,
        internal_line,
        "IntNetwork_Line",
        _is_valid_internal_line,
        "An internal line with id 'IntNetwork_Line' is expected.",
    )

    # Build final message if invalid
    if error_messages:
        full_message = (
            f"The '{topology_name}' topology expects the following models:\n"
            + "\n".join(error_messages)
        )

        # Add connection details
        if expected_gen_count == "single" and len(generators) == 1:
            full_message += (
                f"\n  - 'StepUp_Xfmr' connected between the generator and the "
                f"{generator_bus_connection}"
            )

        if expect_aux_load and auxiliary_load:
            full_message += (
                f"\n  - 'AuxLoad_Xfmr' connected between the auxiliary load and the "
                f"{aux_load_bus_connection}"
            )

        if expect_main_xfmr and main_transformer:
            full_message += f"\n  - 'Main_Xfmr' connected between the {main_xfmr_bus_connection}"

        if expect_internal_line and internal_line:
            full_message += (
                f"\n  - 'IntNetwork_Line' connected between the {internal_line_bus_connection}"
            )

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
