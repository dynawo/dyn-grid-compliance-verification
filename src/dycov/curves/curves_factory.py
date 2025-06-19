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

from dycov.configuration.cfg import config
from dycov.core.execution_parameters import Parameters
from dycov.curves.curves import ProducerCurves
from dycov.curves.dynawo.curves import DynawoCurves
from dycov.curves.importer.curves import ImportedCurves
from dycov.model.producer import Producer


def get_producer(
    parameters: Parameters,
    producer: Producer,
    pcs_benchmark_name: str,
    stable_time: float,
    lib_path: Path,
    templates_path: Path,
    pcs_name: str,
) -> ProducerCurves:
    """Gets the producer curve generator.

    Parameters
    ----------
    parameters: Parameters
        Tool parameters
    producer: Producer
        The producer object containing configuration and producer information.
    pcs_benchmark_name : str
        Composite name, pcs + Benchmark name.
    stable_time: float
        Minimum duration required to consider stability reached (measured from the tail)
    lib_path : Path
        Path where the TSO models are saved within the package.
    templates_path : Path
        Path where the pcs templates are saved within the package
    pcs_name : str
        Pcs name.

    Returns
    -------
    ProducerCurves
        Object for obtaining the producer curves, these can be generated using the Dynawo
        simulator, or they can be imported from files.
    """
    if producer.is_dynawo_model():
        job_name = config.get_value(pcs_benchmark_name, "job_name")
        rte_model = config.get_value(pcs_benchmark_name, "TSO_model")
        omega_model = config.get_value(pcs_benchmark_name, "Omega_model")

        file_path = Path(__file__).resolve().parent.parent
        sim_type_path = producer.get_sim_type_str()
        model_path = file_path / lib_path / "TSO_model" / rte_model
        omega_path = file_path / lib_path / "Omega" / omega_model
        pcs_path = file_path / templates_path / sim_type_path / pcs_name
        if not pcs_path.exists():
            pcs_path = config.get_config_dir() / templates_path / sim_type_path / pcs_name

        return DynawoCurves(
            parameters,
            producer,
            pcs_name,
            model_path,
            omega_path,
            pcs_path,
            job_name,
            stable_time,
        )
    elif producer.is_user_curves():
        return ImportedCurves(producer)

    raise ValueError("Unsupported producer curves")


def get_reference(
    producer: Producer,
) -> ImportedCurves:
    """Gets the reference curve generator.

    Parameters
    ----------
    producer: Producer
        The producer object containing configuration and producer information.

    Returns
    -------
    ImportedCurves
        Object for obtaining reference curves, these must be imported from files.
    """
    return ImportedCurves(producer)
