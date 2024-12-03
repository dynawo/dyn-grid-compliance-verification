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

from dgcv.configuration.cfg import config
from dgcv.dynawo.translator import dynawo_translator
from dgcv.files.producer_curves import create_producer_curves
from dgcv.logging.logging import dgcv_logging
from dgcv.model.parameters import Line_params, Load_params, Xfmr_params


def _check_topology_s(
    generators: list,
    transformers: list,
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:
    has_error = False
    if len(generators) != 1 or len(transformers) != 1:
        has_error |= True

    if (
        auxiliary_load is not None
        or auxiliary_transformer is not None
        or transformer is not None
        or internal_line is not None
    ):
        has_error |= True

    has_error |= not (_is_valid_generator(generators[0].id))
    has_error |= not (_is_valid_stepup_xfmr(transformers, generators))

    if has_error:
        raise ValueError(
            "The 'S' topology expects the following models:\n"
            "  - A generator with id:\n"
            "      * 'Synch_Gen' if a synchronous generator is modeled\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "  - A transformer with id 'StepUp_Xfmr' connected between the generator and the PDR "
            "bus\n"
        )


def _check_topology_si(
    generators: list,
    transformers: list,
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:
    has_error = False
    if len(generators) != 1 or len(transformers) != 1 or internal_line is None:
        has_error |= True

    if auxiliary_load is not None or auxiliary_transformer is not None or transformer is not None:
        has_error |= True

    has_error |= not (_is_valid_generator(generators[0].id))
    has_error |= not (_is_valid_stepup_xfmr(transformers, generators))
    has_error |= not (internal_line.id == "IntNetwork_Line")

    if has_error:
        raise ValueError(
            "The 'S+i' topology expects the following models:\n"
            "  - A generator with id:\n"
            "      * 'Synch_Gen' if a synchronous generator is modeled\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "  - A transformer with id 'StepUp_Xfmr' connected between the generator and the "
            "internal line\n"
            "  - An internal line with id 'IntNetwork_Line' connected between the transformer "
            "and the PDR bus\n"
        )


def _check_topology_saux(
    generators: list,
    transformers: list,
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:
    has_error = False
    if (
        len(generators) != 1
        or len(transformers) != 1
        or auxiliary_load is None
        or auxiliary_transformer is None
    ):
        has_error |= True

    if transformer is not None or internal_line is not None:
        has_error |= True

    has_error |= not (_is_valid_generator(generators[0].id))
    has_error |= not (_is_valid_stepup_xfmr(transformers, generators))
    has_error |= not (auxiliary_load.id == "Aux_Load")
    has_error |= not (_is_valid_auxiliary_transformer(auxiliary_transformer))

    if has_error:
        raise ValueError(
            "The 'S+Aux' topology expects the following models:\n"
            "  - A generator with id:\n"
            "      * 'Synch_Gen' if a synchronous generator is modeled\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "  - A transformer with id 'StepUp_Xfmr' connected between the generator and the PDR "
            "bus\n"
            "  - An auxiliary load with id 'auxiliary_load'\n"
            "  - A transformer with id 'auxiliary_transformer' connected between the auxiliary "
            "load and the PDR bus\n"
        )


def _check_topology_sauxi(
    generators: list,
    transformers: list,
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:
    has_error = False
    if (
        len(generators) != 1
        or len(transformers) != 1
        or auxiliary_load is None
        or auxiliary_transformer is None
        or internal_line is None
    ):
        has_error |= True

    if transformer is not None:
        has_error |= True

    has_error |= not (_is_valid_generator(generators[0].id))
    has_error |= not (_is_valid_stepup_xfmr(transformers, generators))
    has_error |= not (auxiliary_load.id == "Aux_Load")
    has_error |= not (_is_valid_auxiliary_transformer(auxiliary_transformer))
    has_error |= not (internal_line.id == "IntNetwork_Line")

    if has_error:
        raise ValueError(
            "The 'S+Aux+i' topology expects the following models:\n"
            "  - A generator with id:\n"
            "      * 'Synch_Gen' if a synchronous generator is modeled\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "  - A transformer with id 'StepUp_Xfmr' connected between the generator and the "
            "internal bus\n"
            "  - An auxiliary load with id 'auxiliary_load'\n"
            "  - A transformer with id 'auxiliary_transformer' connected between the auxiliary "
            "load and the internal bus\n"
            "  - An internal line with id 'IntNetwork_Line' connected between the transformer and "
            "the PDR bus\n"
        )


def _check_topology_m(
    generators: list,
    transformers: list,
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:
    has_error = False
    if len(generators) < 2 or len(transformers) < 2 or transformer is None:
        has_error |= True

    if (
        auxiliary_load is not None
        or auxiliary_transformer is not None
        or internal_line is not None
    ):
        has_error |= True

    for generator in generators:
        has_error |= not (_is_valid_generator(generator.id, False))
    has_error |= not (_is_valid_stepup_xfmr(transformers, generators))
    has_error |= not (_is_valid_transformer(transformer))

    if has_error:
        raise ValueError(
            "The 'M' topology expects the following models:\n"
            "  - Two or more generators, their ids start with:\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "  - A transformer for each generator, its id starts with 'StepUp_Xfmr' and it is "
            "connected between a generator and the internal bus\n"
            "  - A transformer with id 'transformer' connected between the internal bus and the "
            "PDR bus\n"
        )


def _check_topology_mi(
    generators: list,
    transformers: list,
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:
    has_error = False
    if (
        len(generators) < 2
        or len(transformers) < 2
        or transformer is None
        or internal_line is None
    ):
        has_error |= True

    if auxiliary_load is not None or auxiliary_transformer is not None:
        has_error |= True

    for generator in generators:
        has_error |= not (_is_valid_generator(generator.id, False))
    has_error |= not (_is_valid_stepup_xfmr(transformers, generators))
    has_error |= not (_is_valid_transformer(transformer))
    has_error |= not (internal_line.id == "IntNetwork_Line")

    if has_error:
        raise ValueError(
            "The 'M+i' topology expects the following models:\n"
            "  - Two or more generators, their ids start with:\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "  - A transformer for each generator, its id starts with 'StepUp_Xfmr' and it is "
            "connected between a generator and the internal bus\n"
            "  - A transformer with id 'transformer' connected between the internal bus and the "
            "internal line\n"
            "  - An internal line with id 'IntNetwork_Line' connected between the transformer "
            "with id 'transformer' and the PDR bus\n"
        )


def _check_topology_maux(
    generators: list,
    transformers: list,
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:
    has_error = False
    if (
        len(generators) < 2
        or len(transformers) < 2
        or auxiliary_load is None
        or auxiliary_transformer is None
        or transformer is None
    ):
        has_error |= True

    if internal_line is not None:
        has_error |= True

    for generator in generators:
        has_error |= not (_is_valid_generator(generator.id, False))
    has_error |= not (_is_valid_stepup_xfmr(transformers, generators))
    has_error |= not (auxiliary_load.id == "Aux_Load")
    has_error |= not (_is_valid_auxiliary_transformer(auxiliary_transformer))
    has_error |= not (_is_valid_transformer(transformer))

    if has_error:
        raise ValueError(
            "The 'M+Aux' topology expects the following models:\n"
            "  - Two or more generators, their ids start with:\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "  - A transformer for each generator, its id starts with 'StepUp_Xfmr' and it is "
            "connected between a generator and the internal bus\n"
            "  - An auxiliary load with id 'auxiliary_load'\n"
            "  - A transformer with id 'auxiliary_transformer' connected between the auxiliary "
            "load and the internal bus\n"
            "  - A transformer with id 'transformer' connected between the internal bus and the "
            "PDR bus\n"
        )


def _check_topology_mauxi(
    generators: list,
    transformers: list,
    auxiliary_load: Load_params,
    auxiliary_transformer: Xfmr_params,
    transformer: Xfmr_params,
    internal_line: Line_params,
) -> None:
    has_error = False
    if (
        len(generators) < 2
        or len(transformers) < 2
        or auxiliary_load is None
        or auxiliary_transformer is None
        or transformer is None
        or internal_line is None
    ):
        has_error |= True

    for generator in generators:
        has_error |= not (_is_valid_generator(generator.id, False))
    has_error |= not (_is_valid_stepup_xfmr(transformers, generators))
    has_error |= not (auxiliary_load.id == "Aux_Load")
    has_error |= not (_is_valid_auxiliary_transformer(auxiliary_transformer))
    has_error |= not (_is_valid_transformer(transformer))
    has_error |= not (internal_line.id == "IntNetwork_Line")

    if has_error:
        raise ValueError(
            "The 'M+Aux+i' topology expects the following models:\n"
            "  - Two or more generators, their ids start with:\n"
            "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
            "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
            "  - A transformer for each generator, its id starts with 'StepUp_Xfmr' and it is "
            "connected between a generator and the internal bus\n"
            "  - An auxiliary load with id 'auxiliary_load'\n"
            "  - A transformer with id 'auxiliary_transformer' connected between the auxiliary "
            "load and the internal bus\n"
            "  - A transformer with id 'transformer' connected between the internal bus and the "
            "internal line\n"
            "  - An internal line with id 'IntNetwork_Line' connected between the transformer "
            "with id 'transformer' and the PDR bus\n"
        )


def _is_valid_generator(gen_id, add_sm=True) -> None:
    # The generator id may contain numbered suffixes, for this reason it must be checked if the
    #  substring exists in the identifier
    gen_types = ["Wind_Turbine", "PV_Array"]
    if add_sm:
        gen_types.append("Synch_Gen")
    if any(gen_type in gen_id for gen_type in gen_types):
        return True
    return False


def _is_valid_stepup_xfmr(transformers: list, generators: list) -> None:
    ids = [
        stepup_xfmr.id for stepup_xfmr in transformers if stepup_xfmr.id.startswith("StepUp_Xfmr")
    ]
    if len(generators) == len(ids):
        return True
    return False


def _is_valid_auxiliary_transformer(auxiliary_transformer: Xfmr_params) -> None:
    if auxiliary_transformer is not None and auxiliary_transformer.id == "AuxLoad_Xfmr":
        return True
    return False


def _is_valid_transformer(transformer: Xfmr_params) -> None:
    if transformer is not None and transformer.id == "Main_Xfmr":
        return True
    return False


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


def check_producer_params(p_max_pu: float, u_nom: float) -> None:
    """Check whether the user-supplied model values are consistent:
    * The value of maximum active power generation must be greater than 0.
    * The nominal voltage value is defined in the configuration file.

    Parameters
    ----------
    p_max_pu: float
        Maximum active power generation.
    u_nom: float
        Nominal voltage.
    """
    if p_max_pu < 0:
        raise ValueError("Unexpected maximum generation of active flow.")
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
    if load is not None and load.P <= 0:
        raise ValueError("The active flow of the auxiliary load must be greater than zero.")


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
        dgcv_logging.get_logger("Sanity Checks").warning(
            "The time for the simulation is very short, it is recommended to use a minimum of 60s"
        )


def check_topology(
    topology: str,
    generators: list,
    transformers: list,
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
        dgcv_logging.get_logger("Sanity Checks").warning("Open not found")


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

        dgcv_logging.get_logger("Sanity Checks").error(f"CurvesFiles.ini not found.{message}")
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), "CurvesFiles.ini")
