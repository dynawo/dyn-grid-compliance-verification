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

from dgcv.configuration.cfg import config
from dgcv.core.execution_parameters import Parameters
from dgcv.core.global_variables import CASE_SEPARATOR
from dgcv.core.validator import Validator
from dgcv.curves.manager import CurvesManager
from dgcv.logging.logging import dgcv_logging


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
    pcs_name: str
        Name of the current pcs
    oc_name: str
        Name of the current OperatingCondition
    """

    def __init__(
        self,
        parameters: Parameters,
        pcs_name: str,
        oc_name: str,
    ):
        self._working_dir = parameters.get_working_dir()
        self._producer = parameters.get_producer()
        self._pcs_name = pcs_name
        self._name = oc_name

        # Read default values
        self._thr_ss_tol = config.get_float("GridCode", "thr_ss_tol", 0.002)

    def __validate(
        self,
        curves_manager: CurvesManager,
        validator: Validator,
        pcs_bm_name: str,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        event_params: dict,
        fs: float,
        curves: dict,
    ) -> dict:

        if validator.is_defined_cct():
            validator.set_time_cct(
                curves_manager.get_producer_curves().get_time_cct(
                    working_oc_dir,
                    jobs_output_dir,
                    event_params["duration_time"],
                )
            )
        validator.set_generators_imax(curves_manager.get_producer_curves().get_generators_imax())
        validator.set_disconnection_model(
            curves_manager.get_producer_curves().get_disconnection_model()
        )
        validator.set_setpoint_variation(
            curves_manager.get_producer_curves().get_setpoint_variation(
                get_cfg_oc_name(pcs_bm_name, self._name)
            )
        )

        results = validator.validate(
            self._name,
            working_oc_dir,
            jobs_output_dir,
            event_params,
            fs,
            curves,
        )

        # Operational point without defining its validations
        if not validator.has_validations():
            results["compliance"] = None

        if dgcv_logging.getEffectiveLevel() != logging.DEBUG:
            with open(working_oc_dir / "results.json", "w") as outfile:
                outfile.write(str(results))

        return results

    def validate(
        self,
        curves_manager: CurvesManager,
        validator: Validator,
        pcs_bm_name: str,
        working_path: Path,
        jobs_output_dir: Path,
        event_params: dict,
        fs: float,
        success: bool,
        has_simulated_curves: bool,
        curves: dict,
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
        fs: float
            Frequency sampling
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
                curves_manager,
                validator,
                pcs_bm_name,
                working_path,
                jobs_output_dir,
                event_params,
                fs,
                curves,
            )
        else:
            results = {"compliance": False, "curves": None}

        results["udim"] = curves_manager.get_producer_curves().get_generator_u_dim()
        return success, results

    def get_name(self) -> str:
        """Get the OperatingCondition name.

        Returns
        -------
        str
            OperatingCondition name
        """
        return self._name
