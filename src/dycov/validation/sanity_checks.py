#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import errno
import os
import shutil
from pathlib import Path

from lxml import etree

from dycov.configuration.cfg import config
from dycov.dynawo.translator import dynawo_translator
from dycov.files.producer_curves import create_producer_curves
from dycov.logging.logging import dycov_logging
from dycov.model.parameters import Gen_params, Line_params, Load_params, Xfmr_params
from dycov.validation import common


def _check_topology_s(
    generators: list[Gen_params],
    transformers: list[Xfmr_params],
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:

    expected_elements = len(generators) == 1 and len(transformers) == 1
    unexpected_elements = (
        auxiliary_load is not None
        or auxiliary_transformer is not None
        or transformer is not None
        or internal_line is not None
    )
    valid_elements = _is_valid_generator(generators[0].id) and _is_valid_stepup_xfmr(
        transformers, generators
    )
    valid_topology = expected_elements and not unexpected_elements and valid_elements

    if not valid_topology:
        raise ValueError(
            "The 'S' topology expects the following models:\n"
            "  - A generator with id:\n"
            "      * 'Synch_Gen' if a synchronous generator is modeled\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "      * 'Bess' if a storage or a park of storages is modeled\n"
            "  - A transformer with id 'StepUp_Xfmr' connected between the generator and the PDR "
            "bus\n"
        )


def _check_topology_si(
    generators: list[Gen_params],
    transformers: list[Xfmr_params],
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:

    expected_elements = (
        len(generators) == 1 and len(transformers) == 1 and internal_line is not None
    )
    unexpected_elements = (
        auxiliary_load is not None or auxiliary_transformer is not None or transformer is not None
    )
    valid_elements = (
        _is_valid_generator(generators[0].id)
        and _is_valid_stepup_xfmr(transformers, generators)
        and _is_valid_internal_line(internal_line)
    )
    valid_topology = expected_elements and not unexpected_elements and valid_elements

    if not valid_topology:
        raise ValueError(
            "The 'S+i' topology expects the following models:\n"
            "  - A generator with id:\n"
            "      * 'Synch_Gen' if a synchronous generator is modeled\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "      * 'Bess' if a storage or a park of storages is modeled\n"
            "  - A transformer with id 'StepUp_Xfmr' connected between the generator and the "
            "internal line\n"
            "  - An internal line with id 'IntNetwork_Line' connected between the transformer "
            "and the PDR bus\n"
        )


def _check_topology_saux(
    generators: list[Gen_params],
    transformers: list[Xfmr_params],
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:

    expected_elements = (
        len(generators) == 1
        and len(transformers) == 1
        and auxiliary_load is not None
        and auxiliary_transformer is not None
    )
    unexpected_elements = transformer is not None or internal_line is not None
    valid_elements = (
        _is_valid_generator(generators[0].id)
        and _is_valid_stepup_xfmr(transformers, generators)
        and _is_valid_auxiliary_load(auxiliary_load)
        and _is_valid_auxiliary_transformer(auxiliary_transformer)
    )
    valid_topology = expected_elements and not unexpected_elements and valid_elements

    if not valid_topology:
        raise ValueError(
            "The 'S+Aux' topology expects the following models:\n"
            "  - A generator with id:\n"
            "      * 'Synch_Gen' if a synchronous generator is modeled\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "      * 'Bess' if a storage or a park of storages is modeled\n"
            "  - A transformer with id 'StepUp_Xfmr' connected between the generator and the PDR "
            "bus\n"
            "  - An auxiliary load with id 'Aux_Load'\n"
            "  - A transformer with id 'AuxLoad_Xfmr' connected between the auxiliary "
            "load and the PDR bus\n"
        )


def _check_topology_sauxi(
    generators: list[Gen_params],
    transformers: list[Xfmr_params],
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:

    expected_elements = (
        len(generators) == 1
        and len(transformers) == 1
        and auxiliary_load is not None
        and auxiliary_transformer is not None
        and internal_line is not None
    )
    unexpected_elements = transformer is not None
    valid_elements = (
        _is_valid_generator(generators[0].id)
        and _is_valid_stepup_xfmr(transformers, generators)
        and _is_valid_auxiliary_load(auxiliary_load)
        and _is_valid_auxiliary_transformer(auxiliary_transformer)
        and _is_valid_internal_line(internal_line)
    )
    valid_topology = expected_elements and not unexpected_elements and valid_elements

    if not valid_topology:
        raise ValueError(
            "The 'S+Aux+i' topology expects the following models:\n"
            "  - A generator with id:\n"
            "      * 'Synch_Gen' if a synchronous generator is modeled\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "      * 'Bess' if a storage or a park of storages is modeled\n"
            "  - A transformer with id 'StepUp_Xfmr' connected between the generator and the "
            "internal bus\n"
            "  - An auxiliary load with id 'Aux_Load'\n"
            "  - A transformer with id 'AuxLoad_Xfmr' connected between the auxiliary "
            "load and the internal bus\n"
            "  - An internal line with id 'IntNetwork_Line' connected between the transformer and "
            "the PDR bus\n"
        )


def _check_topology_m(
    generators: list[Gen_params],
    transformers: list[Xfmr_params],
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:

    expected_elements = len(generators) > 1 and len(transformers) > 1 and transformer is not None
    unexpected_elements = (
        auxiliary_load is not None
        or auxiliary_transformer is not None
        or internal_line is not None
    )
    valid_elements = (
        _is_valid_generators(generators)
        and _is_valid_stepup_xfmr(transformers, generators)
        and _is_valid_transformer(transformer)
    )
    valid_topology = expected_elements and not unexpected_elements and valid_elements

    if not valid_topology:
        raise ValueError(
            "The 'M' topology expects the following models:\n"
            "  - Two or more generators, their ids start with:\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "      * 'Bess' if a storage or a park of storages is modeled\n"
            "  - A transformer for each generator, its id starts with 'StepUp_Xfmr' and it is "
            "connected between a generator and the internal bus\n"
            "  - A transformer with id 'Main_Xfmr' connected between the internal bus and the "
            "PDR bus\n"
        )


def _check_topology_mi(
    generators: list[Gen_params],
    transformers: list[Xfmr_params],
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:

    expected_elements = (
        len(generators) > 1
        and len(transformers) > 1
        and transformer is not None
        and internal_line is not None
    )
    unexpected_elements = auxiliary_load is not None or auxiliary_transformer is not None
    valid_elements = (
        _is_valid_generators(generators)
        and _is_valid_stepup_xfmr(transformers, generators)
        and _is_valid_transformer(transformer)
        and _is_valid_internal_line(internal_line)
    )
    valid_topology = expected_elements and not unexpected_elements and valid_elements

    if not valid_topology:
        raise ValueError(
            "The 'M+i' topology expects the following models:\n"
            "  - Two or more generators, their ids start with:\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "      * 'Bess' if a storage or a park of storages is modeled\n"
            "  - A transformer for each generator, its id starts with 'StepUp_Xfmr' and it is "
            "connected between a generator and the internal bus\n"
            "  - A transformer with id 'Main_Xfmr' connected between the internal bus and the "
            "internal line\n"
            "  - An internal line with id 'IntNetwork_Line' connected between the transformer "
            "with id 'transformer' and the PDR bus\n"
        )


def _check_topology_maux(
    generators: list[Gen_params],
    transformers: list[Xfmr_params],
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:

    expected_elements = (
        len(generators) > 1
        and len(transformers) > 1
        and transformer is not None
        and auxiliary_load is not None
        and auxiliary_transformer is not None
    )
    unexpected_elements = internal_line is not None
    valid_elements = (
        _is_valid_generators(generators)
        and _is_valid_stepup_xfmr(transformers, generators)
        and _is_valid_transformer(transformer)
        and _is_valid_auxiliary_load(auxiliary_load)
        and _is_valid_auxiliary_transformer(auxiliary_transformer)
    )
    valid_topology = expected_elements and not unexpected_elements and valid_elements

    if not valid_topology:
        raise ValueError(
            "The 'M+Aux' topology expects the following models:\n"
            "  - Two or more generators, their ids start with:\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "      * 'Bess' if a storage or a park of storages is modeled\n"
            "  - A transformer for each generator, its id starts with 'StepUp_Xfmr' and it is "
            "connected between a generator and the internal bus\n"
            "  - An auxiliary load with id 'Aux_Load'\n"
            "  - A transformer with id 'AuxLoad_Xfmr' connected between the auxiliary "
            "load and the internal bus\n"
            "  - A transformer with id 'Main_Xfmr' connected between the internal bus and the "
            "PDR bus\n"
        )


def _check_topology_mauxi(
    generators: list[Gen_params],
    transformers: list[Xfmr_params],
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:

    expected_elements = (
        len(generators) > 1
        and len(transformers) > 1
        and transformer is not None
        and auxiliary_load is not None
        and auxiliary_transformer is not None
        and internal_line is not None
    )
    unexpected_elements = False
    valid_elements = (
        _is_valid_generators(generators)
        and _is_valid_stepup_xfmr(transformers, generators)
        and _is_valid_transformer(transformer)
        and _is_valid_auxiliary_load(auxiliary_load)
        and _is_valid_auxiliary_transformer(auxiliary_transformer)
        and _is_valid_internal_line(internal_line)
    )
    valid_topology = expected_elements and not unexpected_elements and valid_elements

    if not valid_topology:
        raise ValueError(
            "The 'M+Aux+i' topology expects the following models:\n"
            "  - Two or more generators, their ids start with:\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "      * 'Bess' if a storage or a park of storages is modeled\n"
            "  - A transformer for each generator, its id starts with 'StepUp_Xfmr' and it is "
            "connected between a generator and the internal bus\n"
            "  - An auxiliary load with id 'Aux_Load'\n"
            "  - A transformer with id 'AuxLoad_Xfmr' connected between the auxiliary "
            "load and the internal bus\n"
            "  - A transformer with id 'Main_Xfmr' connected between the internal bus and the "
            "internal line\n"
            "  - An internal line with id 'IntNetwork_Line' connected between the transformer "
            "with id 'transformer' and the PDR bus\n"
        )


def _is_valid_generators(generators) -> bool:
    for generator in generators:
        if not _is_valid_generator(generator.id, False):
            return False

    return True


def _is_valid_generator(gen_id, add_sm=True) -> bool:
    # The generator id may contain numbered suffixes, for this reason it must be checked if the
    #  substring exists in the identifier
    gen_types = ["Wind_Turbine", "PV_Array", "Bess"]
    if add_sm:
        gen_types.append("Synch_Gen")
    if any(gen_type in gen_id for gen_type in gen_types):
        return True
    return False


def _is_valid_stepup_xfmr(transformers: list[Xfmr_params], generators: list) -> bool:
    ids = [
        stepup_xfmr.id for stepup_xfmr in transformers if stepup_xfmr.id.startswith("StepUp_Xfmr")
    ]
    return len(generators) == len(ids)


def _is_valid_auxiliary_transformer(auxiliary_transformer: Xfmr_params) -> bool:
    if auxiliary_transformer is not None and auxiliary_transformer.id == "AuxLoad_Xfmr":
        return True
    return False


def _is_valid_transformer(transformer: Xfmr_params) -> bool:
    if transformer is not None and transformer.id == "Main_Xfmr":
        return True
    return False


def _is_valid_auxiliary_load(auxiliary_load: Load_params) -> bool:
    if auxiliary_load is not None and auxiliary_load.id == "Aux_Load":
        return True
    return False


def _is_valid_internal_line(internal_line: Line_params) -> bool:
    if internal_line is not None and internal_line.id == "IntNetwork_Line":
        return True
    return False


def check_t_fault(start_time: float, event_time: float, range_len: float) -> None:
    """Check that the difference between the curve start time and the event trigger time is
    greater than or equal to the range length.

    Parameters
    ----------
    start_time: float
        The curve start time.
    event_time: float
        The event trigger time.
    range_len: float
        The range length.
    """
    if event_time - start_time < range_len:
        dycov_logging.get_logger("Sanity Checks").warning(
            f"The event is triggered before {range_len} seconds have elapsed since the start"
            f" of the curve."
        )


def check_pre_stable(time: list, curve: list) -> None:
    """Check that the curve is stable.

    Parameters
    ----------
    curve: float
        Pre window curve.
    """
    stable, _ = common.is_stable(time, curve, time[-1] - time[0])
    if not stable:
        dycov_logging.get_logger("Sanity Checks").warning(
            "Unstable curve before the event is triggered."
        )


def check_sampling_interval(sampling_interval: float, cutoff: float) -> None:
    """Check that the sampling interval and cut-off values do not exceed the maximum allowed value.
    The maximum value for the sampling interval is determined by 2 times the filter Cut-off
    frequency.

    Parameters
    ----------
    sampling_interval: float
        Sampling interval.
    cutoff: float
        Filter Cut-off frequency.
    """
    if sampling_interval >= 1 / (2 * cutoff):
        raise ValueError(
            "Unexpected sampling interval, its maximum is determined by 2 times the filter "
            "Cut-off frequency."
        )


def check_well_formed_xml(xml_file: Path) -> None:
    """Check if the supplied file is a well-formed xml file.

    Parameters
    ----------
    xml_file: Path
        File in XML format.
    """
    etree.parse(open(xml_file))


def check_producer_params(
    p_max_injection_pu: float, p_max_consumption_pu: float, u_nom: float
) -> None:
    """Check whether the user-supplied model values are consistent:
    * The value of maximum active power generation must be greater or equal than 0.
    * The value of maximum active power consumption must be greater or equal than 0.
    * The nominal voltage value is defined in the configuration file.

    Parameters
    ----------
    p_max_injection_pu: float
        Maximum active power generation.
    p_max_consumption_pu: float
        Maximum active power consumption.
    u_nom: float
        Nominal voltage.
    """
    if p_max_injection_pu < 0:
        raise ValueError(
            "The value of maximum active power generation must be greater or equal than 0."
        )
    if p_max_consumption_pu < 0:
        raise ValueError(
            "The value of maximum active power consumption must be greater or equal than 0."
        )
    Udims = (
        config.get_list("GridCode", "HTB1_Udims")
        + config.get_list("GridCode", "HTB2_Udims")
        + config.get_list("GridCode", "HTB3_Udims")
        + config.get_list("GridCode", "HTB1_External_Udims")
        + config.get_list("GridCode", "HTB2_External_Udims")
        + config.get_list("GridCode", "HTB3_External_Udims")
    )
    if str(u_nom) not in Udims:
        raise ValueError("Unexpected nominal voltage in the PDR Bus.")


def check_generators(generators: list) -> tuple[int, int, int]:
    """Check whether the user-supplied generators parameters are consistent:
    * All generators are SM, PPM or BESS, mixing is not allowed.

    Parameters
    ----------
    generators: list
        Generators parameters list.

    Returns
    -------
    int
        Number of Synchronous Machines
    int
        Number of Power Park Modules
    """
    sm_models = 0
    ppm_models = 0
    bess_models = 0
    for generator in generators:
        if generator.lib in dynawo_translator.get_synchronous_machine_models():
            sm_models += 1
        if generator.lib in dynawo_translator.get_power_park_models():
            ppm_models += 1
        if generator.lib in dynawo_translator.get_storage_models():
            bess_models += 1

    total = len(generators)
    if sm_models < total and ppm_models < total and bess_models < total:
        raise ValueError(
            "The supplied network contains two or more different generator model types."
        )
    return sm_models, ppm_models, bess_models


def check_trafos(xfmrs: list) -> None:
    """Check whether the user-supplied transformers parameters are consistent:
    * The admittance of each transformer must be greater than 0.

    Parameters
    ----------
    xfmrs: list
        Transformers parameters list.
    """
    for xfmr in xfmrs:
        check_trafo(xfmr)


def check_trafo(xfmr: Xfmr_params) -> None:
    """Check whether the user-supplied tranformer parameters are consistent:
    * The admittance of the transformer must be greater than 0.

    Parameters
    ----------
    xfmr: Xfmr_params
        Transformer parameters.
    """
    if xfmr and xfmr.X <= 0:
        raise ValueError(f"The admittance of the transformer {xfmr.id} must be greater than zero.")


def check_auxiliary_load(load: Load_params) -> None:
    """Check whether the user-supplied auxiliary load parameters are consistent:
    * The active flow of the auxiliary load must be greater than zero.

    Parameters
    ----------
    load: Load_params
        Auxiliary load parameters.
    """
    if load is None:
        return
    if load.P <= 0:
        raise ValueError("The active flow of the auxiliary load must be greater than zero.")
    if load.Alpha is not None and load.Alpha == 0 and load.Beta is not None and load.Beta == 0:
        dycov_logging.get_logger("Sanity Checks").warning(
            "The auxiliary load is defined with alpha = 0 and beta = 0, "
            "this configuration can cause unexpected results in bolted fault tests."
        )


def check_internal_line(line: Line_params) -> None:
    """Check whether the user-supplied internal line parameters are consistent:
    * The reactance and admittance of the internal line must be greater than zero.

    Parameters
    ----------
    line: Line_params
        Internal line parameters.
    """
    if line and (line.R <= 0 or line.X <= 0):
        raise ValueError(
            "The reactance and admittance of the internal line must be greater than zero."
        )


def check_simulation_duration(time: float) -> None:
    """Check if the simulation time is greater than 60 seconds, the minimum time to guarantee that
    all compliance tests can be completed.

    Parameters
    ----------
    time: float
        Total simulation time in seconds.
    """
    if time < 60:
        dycov_logging.get_logger("Sanity Checks").warning(
            "The time for the simulation is very short, it is recommended to use a minimum of 60s"
        )


def check_solver(id: str, lib: str):
    """Check if a solver allowed by the tool has been configured.

    Parameters
    ----------
    id: str
        Solver id.
    lib: str
        Solver library.
    """
    if lib not in ["dynawo_SolverIDA", "dynawo_SolverSIM"]:
        raise ValueError("The solver library is not available.")

    if id not in lib:
        raise ValueError("The solver id is incorrect.")


def check_topology(
    topology: str,
    generators: list[Gen_params],
    transformers: list[Xfmr_params],
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:
    """Check if one of the 8 allowed topologies has been selected, and if the correct devices
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
    """
    if "S".casefold() == topology.casefold():
        _check_topology_s(
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    elif "S+i".casefold() == topology.casefold():
        _check_topology_si(
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    elif "S+Aux".casefold() == topology.casefold():
        _check_topology_saux(
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    elif "S+Aux+i".casefold() == topology.casefold():
        _check_topology_sauxi(
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    elif "M".casefold() == topology.casefold():
        _check_topology_m(
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    elif "M+i".casefold() == topology.casefold():
        _check_topology_mi(
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    elif "M+Aux".casefold() == topology.casefold():
        _check_topology_maux(
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    elif "M+Aux+i".casefold() == topology.casefold():
        _check_topology_mauxi(
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    else:
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


def check_launchers(launcher_dwo: Path) -> None:
    error_txt = ""
    if not shutil.which(launcher_dwo):
        error_txt += "Dynawo not found.\n"
    if not shutil.which("pdflatex"):
        error_txt += "PdfLatex not found.\n"
    if not shutil.which("cmake"):
        error_txt += "CMake not found.\n"
    # TODO: for Windows, add an analogous check for the presence of the VS2019 compiler.
    if os.name == "posix" and not shutil.which("g++"):
        error_txt += "G++ not found.\n"

    if len(error_txt) > 0:
        raise OSError(error_txt)

    if os.name == "posix" and not shutil.which("open"):
        dycov_logging.get_logger("Sanity Checks").warning("Open not found")


def check_curves_files(model_path: Path, curves_path: Path, template: str) -> None:
    if not curves_path:
        return

    if not (curves_path / "CurvesFiles.ini").exists():
        message = ""
        if model_path:
            template_name = "model"
            if template.startswith("performance"):
                template_name = template.replace("/", "_")
            create_producer_curves(model_path, curves_path, template_name)
            message = " Edit the generated file to complete it."

        dycov_logging.get_logger("Sanity Checks").error(f"CurvesFiles.ini not found.{message}")
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), "CurvesFiles.ini")
