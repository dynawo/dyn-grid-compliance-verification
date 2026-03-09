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
This module contains functions for validating various numerical and configuration
parameters of Dynawo models, including generator, transformer, load, and simulation settings.
"""

from typing import List

from dycov.configuration.cfg import config
from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.logging.logging import dycov_logging
from dycov.model.parameters import Gen_params, Line_params, Load_params, Xfmr_params
from dycov.validation import common


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


def check_pre_stable(time: List[float], curve: List[float]) -> None:
    """Check that the curve is stable.

    Parameters
    ----------
    curve: list
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
        raise ValueError("Unexpected nominal voltage at the PDR bus.")


def check_producer_params_consistency(
    generators: List[Gen_params],
    p_max_pu: float = 0.0,
    q_max_pu: float = 0.0,
    q_min_pu: float = 0.0,
    rel_tol: float = 1e-6,
    abs_tol: float = 1e-9,
) -> None:
    """
    Check whether parameters from Producer.INI are consistent with those from Producer.PAR,
    using RTE's rule: INI values may differ as long as they are more restrictive.

    More restrictive rules:
      - Pmax_ini <= Sum(Pmax_par)
      - Qmax_ini <= Sum(Qmax_par)
      - Qmin_ini >= Sum(Qmin_par)

    Parameters
    ----------
    generators: list
        Generator parameters list.
    p_max_pu: float
        Maximum active power in PDR (INI) in per unit.
    q_max_pu: float
        Maximum reactive power in PDR (INI) in per unit.
    q_min_pu: float
        Minimum reactive power in PDR (INI) in per unit.
    rel_tol: float
        Relative tolerance.
    abs_tol: float
        Absolute tolerance.
    """

    # Aggregate PAR values
    gen_p_max = sum(g.PMax for g in generators if g.PMax is not None)
    gen_q_max = sum(g.QMax for g in generators if g.QMax is not None)
    gen_q_min = sum(g.QMin for g in generators if g.QMin is not None)

    log = dycov_logging.get_logger("Sanity Checks")
    has_error = False

    # --- Pmax check ---
    if gen_p_max != 0:
        # INI must be <= PAR (more restrictive)
        if p_max_pu > gen_p_max + max(abs_tol, rel_tol * abs(gen_p_max)):
            log.error(
                f"Inconsistency in Pmax: INI={p_max_pu} is less restrictive than PAR={gen_p_max}"
            )
            has_error = True

    # --- Qmax check ---
    if gen_q_max != 0:
        if q_max_pu > gen_q_max + max(abs_tol, rel_tol * abs(gen_q_max)):
            log.error(
                f"Inconsistency in Qmax: INI={q_max_pu} is less restrictive than PAR={gen_q_max}"
            )
            has_error = True

    # --- Qmin check ---
    if gen_q_min != 0:
        # For Qmin, "more restrictive" means INI >= PAR
        if q_min_pu < gen_q_min - max(abs_tol, rel_tol * abs(gen_q_min)):
            log.error(
                f"Inconsistency in Qmin: INI={q_min_pu} is less restrictive than PAR={gen_q_min}"
            )
            has_error = True

    if has_error:
        raise ValueError(
            "Inconsistency detected: INI values are less restrictive than PAR values."
        )


def check_generators(
    generators_z1: List[Gen_params], generators_z3: List[Gen_params] = None
) -> tuple[int, int, int]:
    """Check whether the user-supplied generators parameters are consistent:
    * The number of generators in each zone must be the same.
    * All generators are SM, PPM or BESS, mixing is not allowed.

    Parameters
    ----------
    generators_z1: list
        Generators parameters list for Zone1.
    generators_z3: list, optional
        Generators parameters list for Zone3.

    Returns
    -------
    tuple[int, int, int]
        Number of Synchronous Machines, Power Park Modules, and Battery Energy Storage Systems.
    """
    generators = generators_z1
    if generators_z3:
        generators = generators_z1 + generators_z3
        if len(generators_z1) != len(generators_z3):
            raise ValueError(
                "The model validation must contain the same number of generators in both zones."
            )

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


def check_trafos(xfmrs: List[Xfmr_params]) -> None:
    """Check whether the user-supplied transformers parameters are consistent:
    * The admittance of each transformer must be greater than 0.

    Parameters
    ----------
    xfmrs: list
        Transformers parameters list.
    """
    for xfmr in xfmrs:
        check_trafo(xfmr)


def check_trafo(xfmrs: Xfmr_params) -> None:
    """Check whether the user-supplied tranformer parameters are consistent:
    * The admittance of the transformer must be greater than 0.

    Parameters
    ----------
    xfmr: Xfmr_params
        Transformer parameters.
    """
    if xfmrs and xfmrs.X <= 0:
        raise ValueError(
            f"The admittance of the transformer {xfmrs.id} must be greater than zero."
        )

    if xfmrs and xfmrs.alphaTfo != 0.0:
        raise ValueError(
            f"The alphaTfo parameter of the transformer {xfmrs.id} must be equal to zero."
        )


def check_auxiliary_load(load: Load_params) -> None:
    """Check whether the user-supplied auxiliary load parameters are consistent:
    * The active flow of the auxiliary load must be greater than zero.
    * Auxiliary load expected to be defined with non-zero alpha and beta values.

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
