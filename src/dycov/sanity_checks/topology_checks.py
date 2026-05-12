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

from dycov.logging.logging import dycov_logging
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


def _find_stepup_xfmr(gen: GenParams, transformers: list[XfmrParams]) -> XfmrParams | None:
    """Return the StepUp_Xfmr whose terminals reference the given generator, or None."""
    return next(
        (
            xfmr
            for xfmr in transformers
            if xfmr.id.startswith("StepUp_Xfmr")
            and any(terminal.connected_equipment == gen.id for terminal in xfmr.terminals)
        ),
        None,
    )


def _check_converter_lv_control(
    generators: list[GenParams],
    transformers: list[XfmrParams],
) -> None:
    """Warn when a generator has converter_lv_control=False and is connected to a StepUp_Xfmr.

    In that configuration the converter's internal transformer and the StepUp_Xfmr are in
    series, which is likely unintentional.
    """
    problematic = []
    for gen in generators:
        if gen.converter_lv_control:
            continue
        xfmr = _find_stepup_xfmr(gen, transformers)
        if xfmr:
            problematic.append((gen.id, xfmr.id))

    if problematic:
        dycov_logging.get_logger("Sanity Checks").warning(
            "The following generators have ConverterLVControl=False and are connected to StepUp "
            "transformers:"
        )
        for gid, tid in problematic:
            dycov_logging.get_logger("Sanity Checks").warning(f"  - {gid} → {tid}")

        dycov_logging.get_logger("Sanity Checks").warning(
            "This results in two transformers in series (the converter's internal transformer "
            "and the StepUp_Xfmr), which is usually unintended. Consider enabling "
            "ConverterLVControl or removing the external StepUp_Xfmr if not required."
        )


def _check_topology_components(
    topology_name: str,
    generators: list[GenParams],
    transformers: list[XfmrParams],
    auxiliary_load: LoadParams | None,
    auxiliary_transformer: XfmrParams | None,
    main_transformer: XfmrParams | None,
    internal_line: LineParams | None,
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

    # Validate step-up transformers
    if expected_xfmr_count == "single":
        if len(transformers) != 1:
            add_error("A transformer with id 'StepUp_Xfmr' is expected.")
        elif not _is_valid_stepup_xfmr(transformers, generators):
            add_error("Invalid step-up transformer configuration.")
    elif expected_xfmr_count == "multiple":
        if len(transformers) <= 1:
            add_error("Multiple step-up transformers are expected.")
        elif not _is_valid_stepup_xfmr(transformers, generators):
            add_error("Invalid step-up transformers configuration.")

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

    # Warn about potentially unintended double-transformer configurations.
    # Runs regardless of structural errors above so the user sees all issues at once.
    _check_converter_lv_control(generators, transformers)

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


def _is_valid_stepup_xfmr(transformers: list[XfmrParams], generators: list[GenParams]) -> bool:
    ids = [t.id for t in transformers if t.id.startswith("StepUp_Xfmr")]
    return len(generators) == len(ids)


def _is_valid_auxiliary_transformer(auxiliary_transformer: XfmrParams) -> bool:
    return auxiliary_transformer is not None and auxiliary_transformer.id == "AuxLoad_Xfmr"


def _is_valid_transformer(transformer: XfmrParams) -> bool:
    return transformer is not None and transformer.id == "Main_Xfmr"


def _is_valid_auxiliary_load(auxiliary_load: LoadParams) -> bool:
    return auxiliary_load is not None and auxiliary_load.id == "Aux_Load"


def _is_valid_internal_line(internal_line: LineParams) -> bool:
    return internal_line is not None and internal_line.id == "IntNetwork_Line"


def check_topology(
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

    cfg = topology_configs[topology_lower]
    _check_topology_components(
        topology,
        generators,
        transformers,
        auxiliary_load,
        auxiliary_transformer,
        transformer,
        internal_line,
        cfg["expected_gen_count"],
        cfg["expected_xfmr_count"],
        cfg["expect_aux_load"],
        cfg["expect_aux_xfmr"],
        cfg["expect_main_xfmr"],
        cfg["expect_internal_line"],
        cfg["generator_bus_connection"],
        cfg["aux_load_bus_connection"],
        cfg["main_xfmr_bus_connection"],
        cfg["internal_line_bus_connection"],
    )
