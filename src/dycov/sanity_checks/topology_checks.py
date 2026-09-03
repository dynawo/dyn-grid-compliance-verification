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

from dycov.model.parameters import GenParams, LineParams, LoadParams, XfmrParams

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


def _check_group_xfmr(
    generators: list[GenParams],
    transformers: list[XfmrParams],
    add_error,
) -> None:
    """Checks the Zone-1 group transformer against the unit's ConverterLVControl flag.

    The converter reaches the internal node through its own transformer when the flag is
    false, so modelling an external one as well would put two transformers in series.
    """
    expected = bool(generators) and generators[0].converter_lv_control
    if expected and len(transformers) != 1:
        add_error(
            "A transformer with id 'Group_Xfmr' is expected between the generating unit and "
            "the internal node, because the unit has ConverterLVControl = true."
        )
    elif not expected and transformers:
        add_error(
            "No transformer is expected between the generating unit and the internal node, "
            "because the unit has ConverterLVControl = false: its own transformer already "
            "reaches the internal node."
        )


def _check_topology_components(
    zone: int,
    topology_name: str,
    generators: list[GenParams],
    transformers: list[XfmrParams],
    auxiliary_load: LoadParams | None,
    auxiliary_transformer: XfmrParams | None,
    main_transformer: XfmrParams | None,
    internal_line: LineParams | None,
    expected_gen_count: str,  # "single" or "multiple"
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

    # Normalize for the startswith check regardless of how the caller spelled it.
    is_single_topology = topology_name.upper().startswith("S")

    # Validate generators
    if expected_gen_count == "single":
        if len(generators) != 1:
            add_error("A single generator is expected.")
        elif not _is_valid_generator(generators[0].id, add_sm=is_single_topology):
            add_error("Invalid generator configuration.")
    elif expected_gen_count == "multiple":
        if len(generators) <= 1:
            add_error("Multiple generators are expected.")
        elif not _is_valid_generators(generators):
            add_error("Invalid generators configuration.")

    # Validate the unit transformers: only Zone 1 may model one
    if zone == 1:
        _check_group_xfmr(generators, transformers, add_error)
    elif transformers:
        add_error(
            "No transformer is expected between the generating units and the internal bus: "
            "the group transformer of each unit is part of its dynamic model."
        )

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

    if not error_messages:
        return

    full_message = f"The '{topology_name}' topology expects the following models:\n" + "\n".join(
        error_messages
    )

    # Add connection hints only when the relevant component is present and valid,
    # so the hint is meaningful in context.
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


def _is_valid_generators(generators: list[GenParams]) -> bool:
    return all(_is_valid_generator(g.id, add_sm=False) for g in generators)


def _is_valid_generator(gen_id: str, add_sm: bool = True) -> bool:
    gen_types = ["Wind_Turbine", "PV_Array", "Bess"]
    if add_sm:
        gen_types.append("Synch_Gen")
    return any(gen_type in gen_id for gen_type in gen_types)


def _is_valid_auxiliary_transformer(auxiliary_transformer: XfmrParams) -> bool:
    return auxiliary_transformer is not None and auxiliary_transformer.id == "AuxLoad_Xfmr"


def _is_valid_transformer(transformer: XfmrParams) -> bool:
    return transformer is not None and transformer.id == "Main_Xfmr"


def _is_valid_auxiliary_load(auxiliary_load: LoadParams) -> bool:
    return auxiliary_load is not None and auxiliary_load.id == "Aux_Load"


def _is_valid_internal_line(internal_line: LineParams) -> bool:
    return internal_line is not None and internal_line.id == "IntNetwork_Line"


ZONE1_CONFIG = {
    "expected_gen_count": "single",
    "expect_aux_load": False,
    "expect_aux_xfmr": False,
    "expect_main_xfmr": False,
    "expect_internal_line": False,
    "generator_bus_connection": "internal node",
    "aux_load_bus_connection": "",
    "main_xfmr_bus_connection": "",
    "internal_line_bus_connection": "",
}


def check_topology(
    zone: int,
    topology: str,
    generators: list[GenParams],
    transformers: list[XfmrParams],
    auxiliary_load: LoadParams | None,
    auxiliary_transformer: XfmrParams | None,
    transformer: XfmrParams | None,
    internal_line: LineParams | None,
) -> None:
    """Checks if one of the 8 allowed topologies has been selected, and if the correct devices
    have been defined for the selected topology.

    Parameters
    ----------
    zone: int
        Zone under test; only Zone 1 models the group transformer of the generating unit.
    topology: str
        Selected topology.
    generators: list
        Producer model generators.
    transformers: list
        Transformers connected to the generators of the producer model.
    auxiliary_load: LoadParams | None
        Auxiliary load connected to the generators of the producer model.
    auxiliary_transformer: XfmrParams | None
        Transformer connected to the auxiliary load of the producer model.
    transformer: XfmrParams | None
        Transformer that groups all the transformer of the producer model.
    internal_line: LineParams | None
        Internal line of the producer model.

    Raises
    ------
    ValueError
        If an invalid topology is selected or if the required devices for the
        selected topology are not correctly defined.
    """
    topology_configs = {
        "s": {
            "expected_gen_count": "single",
            "expect_aux_load": False,
            "expect_aux_xfmr": False,
            "expect_main_xfmr": True,
            "expect_internal_line": False,
            "generator_bus_connection": "internal bus",
            "aux_load_bus_connection": "",
            "main_xfmr_bus_connection": "internal network and the PDR bus",
            "internal_line_bus_connection": "",
        },
        "s+i": {
            "expected_gen_count": "single",
            "expect_aux_load": False,
            "expect_aux_xfmr": False,
            "expect_main_xfmr": True,
            "expect_internal_line": True,
            "generator_bus_connection": "internal bus",
            "aux_load_bus_connection": "",
            "main_xfmr_bus_connection": "internal network and the PDR bus",
            "internal_line_bus_connection": "internal bus and the main transformer",
        },
        "s+aux": {
            "expected_gen_count": "single",
            "expect_aux_load": True,
            "expect_aux_xfmr": True,
            "expect_main_xfmr": True,
            "expect_internal_line": False,
            "generator_bus_connection": "internal bus",
            "aux_load_bus_connection": "internal bus",
            "main_xfmr_bus_connection": "internal network and the PDR bus",
            "internal_line_bus_connection": "",
        },
        "s+aux+i": {
            "expected_gen_count": "single",
            "expect_aux_load": True,
            "expect_aux_xfmr": True,
            "expect_main_xfmr": True,
            "expect_internal_line": True,
            "generator_bus_connection": "internal bus",
            "aux_load_bus_connection": "internal bus",
            "main_xfmr_bus_connection": "internal network and the PDR bus",
            "internal_line_bus_connection": "internal bus and the main transformer",
        },
        "m": {
            "expected_gen_count": "multiple",
            "expect_aux_load": False,
            "expect_aux_xfmr": False,
            "expect_main_xfmr": True,
            "expect_internal_line": False,
            "generator_bus_connection": "internal bus",
            "aux_load_bus_connection": "",
            "main_xfmr_bus_connection": "internal network and the PDR bus",
            "internal_line_bus_connection": "",
        },
        "m+i": {
            "expected_gen_count": "multiple",
            "expect_aux_load": False,
            "expect_aux_xfmr": False,
            "expect_main_xfmr": True,
            "expect_internal_line": True,
            "generator_bus_connection": "internal bus",
            "aux_load_bus_connection": "",
            "main_xfmr_bus_connection": "internal network and the PDR bus",
            "internal_line_bus_connection": "transformer with id 'transformer' and the PDR bus",
        },
        "m+aux": {
            "expected_gen_count": "multiple",
            "expect_aux_load": True,
            "expect_aux_xfmr": True,
            "expect_main_xfmr": True,
            "expect_internal_line": False,
            "generator_bus_connection": "internal bus",
            "aux_load_bus_connection": "internal bus",
            "main_xfmr_bus_connection": "internal network and the PDR bus",
            "internal_line_bus_connection": "",
        },
        "m+aux+i": {
            "expected_gen_count": "multiple",
            "expect_aux_load": True,
            "expect_aux_xfmr": True,
            "expect_main_xfmr": True,
            "expect_internal_line": True,
            "generator_bus_connection": "internal bus",
            "aux_load_bus_connection": "internal bus",
            "main_xfmr_bus_connection": "internal network and the PDR bus",
            "internal_line_bus_connection": "transformer with id 'transformer' and the PDR bus",
        },
    }

    topology_lower = topology.casefold()
    if topology_lower not in topology_configs:
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

    cfg = ZONE1_CONFIG if zone == 1 else topology_configs[topology_lower]
    _check_topology_components(
        zone,
        topology,
        generators,
        transformers,
        auxiliary_load,
        auxiliary_transformer,
        transformer,
        internal_line,
        cfg["expected_gen_count"],
        cfg["expect_aux_load"],
        cfg["expect_aux_xfmr"],
        cfg["expect_main_xfmr"],
        cfg["expect_internal_line"],
        cfg["generator_bus_connection"],
        cfg["aux_load_bus_connection"],
        cfg["main_xfmr_bus_connection"],
        cfg["internal_line_bus_connection"],
    )
