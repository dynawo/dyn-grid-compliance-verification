#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import logging
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.core.execution_parameters import Parameters
from dycov.core.global_variables import CASE_SEPARATOR
from dycov.core.validator import Validator
from dycov.logging.logging import dycov_logging
from dycov.model.producer import Producer


def get_cfg_oc_name(pcs_bm_name: str, oc_name: str) -> str:
    if pcs_bm_name == oc_name:
        return oc_name
    return pcs_bm_name + CASE_SEPARATOR + oc_name


class OperatingCondition:
    """Thrid-level representation of the pcs described in the DTR.
    A Grid Topology can contain several Operating Conditions, in each Operating Condition
    a set of initial parameters is defined for the simulation of the Benchmark.

    Args
    ----
    parameters: Parameters
        Tool parameters
    producer: Producer
        The producer object containing configuration and producer information.
    pcs_name: str
        Name of the current pcs
    oc_name: str
        Name of the current OperatingCondition
    """

    def __init__(
        self,
        parameters: Parameters,
        producer: Producer,
        pcs_name: str,
        oc_name: str,
    ):
        self._working_dir = parameters.get_working_dir()
        self._producer = producer
        self._pcs_name = pcs_name
        self._name = oc_name

        # Read default values
        self._thr_ss_tol = config.get_float("GridCode", "thr_ss_tol", 0.002)

    def __validate(
        self,
        validator: Validator,
        pcs_bm_name: str,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        event_params: dict,
    ) -> dict:

        validator.complete_parameters(
            working_oc_dir, jobs_output_dir, event_params, get_cfg_oc_name(pcs_bm_name, self._name)
        )
        results = validator.validate(
            self._name,
            working_oc_dir,
            jobs_output_dir,
            event_params,
        )

        # Operational point without defining its validations
        if not validator.has_validations():
            results["compliance"] = None

        if dycov_logging.getEffectiveLevel() != logging.DEBUG:
            with open(working_oc_dir / "results.json", "w") as outfile:
                outfile.write(str(results))

        return results

    def validate(
        self,
        validator: Validator,
        pcs_bm_name: str,
        working_path: Path,
        jobs_output_dir: Path,
        event_params: dict,
        success: bool,
        has_simulated_curves: bool,
    ) -> tuple[bool, dict]:
        """Validate the Benchmark.

        Parameters
        ----------
        pcs_bm_name: str
            Composite name, pcs + Benchmark name
        working_path: Path
            Working path.
        jobs_output_dir: Path
            Simulator output path.
        event_params: dict
            Event parameters
        success: bool
            True if simulation is success
        has_simulated_curves: bool
            True if simulation calculated curves
        curves: dict
            Calculated and reference curves

        Returns
        -------
        bool
            True if OperatingCondition can be validated, False otherwise
        dict
            Validation results of the OperatingCondition
        """
        if has_simulated_curves:
            # Validate results
            results = self.__validate(
                validator,
                pcs_bm_name,
                working_path,
                jobs_output_dir,
                event_params,
            )
        else:
            results = {"compliance": False, "curves": None}

        results["udim"] = validator.get_generator_u_dim()
        return success, results

    def get_name(self) -> str:
        """Get the OperatingCondition name.

        Returns
        -------
        str
            OperatingCondition name
        """
        return self._name
