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

import pandas as pd

from dgcv.configuration.cfg import config
from dgcv.core.execution_parameters import Parameters
from dgcv.core.global_variables import CASE_SEPARATOR
from dgcv.core.validator import Validator
from dgcv.curves.manager import CurvesManager
from dgcv.files import manage_files
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
    model_path: Path
        Model library directory
    omega_path: Path
        Omega library directory
    pcs_path: Path
        PCS configuration directory
    job_name: str
        Dynawo job name
    """

    def __init__(
        self,
        curves_manager: CurvesManager,
        validator: Validator,
        parameters: Parameters,
        pcs_name: str,
        oc_name: str,
    ):
        self._curves_manager = curves_manager
        self._validator = validator
        self._working_dir = parameters.get_working_dir()
        self._producer = parameters.get_producer()
        self._pcs_name = pcs_name
        self._name = oc_name

        # Read default values
        self._thr_ss_tol = config.get_float("GridCode", "thr_ss_tol", 0.002)

    def __has_reference_curves(self) -> bool:
        return self._producer.has_reference_curves_path()

    def __get_reference_curves_path(self) -> Path:
        if not hasattr(self, "_reference_curves_path"):
            self._reference_curves_path = self._producer.get_reference_curves_path()
        return self._reference_curves_path

    def __obtain_curve(
        self,
        pcs_bm_name: str,
        bm_name: str,
    ):
        # Create a specific folder by operational point
        working_oc_dir = self._working_dir / self._pcs_name / bm_name / self._name
        manage_files.create_dir(working_oc_dir)

        curves = dict()
        reference_event_start_time = None
        if self.__has_reference_curves():
            (
                reference_event_start_time,
                curves["reference"],
            ) = self._curves_manager.get_reference_curves().obtain_reference_curve(
                working_oc_dir, pcs_bm_name, self._name, self.__get_reference_curves_path()
            )
        else:
            curves["reference"] = pd.DataFrame()

        (
            jobs_output_dir,
            event_params,
            fs,
            success,
            has_simulated_curves,
            curves["calculated"],
        ) = self._curves_manager.get_producer_curves().obtain_simulated_curve(
            working_oc_dir,
            pcs_bm_name,
            bm_name,
            self._name,
            reference_event_start_time,
        )

        return (
            working_oc_dir,
            jobs_output_dir,
            event_params,
            fs,
            success,
            has_simulated_curves,
            curves,
        )

    def __validate(
        self,
        pcs_bm_name: str,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        event_params: dict,
        fs: float,
        curves: dict,
    ) -> dict:

        if self._validator.is_defined_cct():
            self._validator.set_time_cct(
                self._curves_manager.get_producer_curves().get_time_cct(
                    working_oc_dir,
                    jobs_output_dir,
                    event_params["duration_time"],
                )
            )
        self._validator.set_generators_imax(
            self._curves_manager.get_producer_curves().get_generators_imax()
        )
        self._validator.set_disconnection_model(
            self._curves_manager.get_producer_curves().get_disconnection_model()
        )
        self._validator.set_setpoint_variation(
            self._curves_manager.get_producer_curves().get_setpoint_variation(
                get_cfg_oc_name(pcs_bm_name, self._name)
            )
        )

        results = self._validator.validate(
            self._name,
            working_oc_dir,
            jobs_output_dir,
            event_params,
            fs,
            curves,
        )

        # Operational point without defining its validations
        if not self._validator.has_validations():
            results["compliance"] = None

        if dgcv_logging.getEffectiveLevel() != logging.DEBUG:
            with open(working_oc_dir / "results.json", "w") as outfile:
                outfile.write(str(results))

        return results

    def _check_curves(
        self, curves: pd.DataFrame, curves_name: str, review_curves_set: bool
    ) -> bool:
        measurement_names = self._validator.get_measurement_names()
        has_curves = True
        if review_curves_set:
            if curves.empty:
                dgcv_logging.get_logger("Operating Condition").warning(
                    f"Test without {curves_name} curves file"
                )
                has_curves = False
            else:
                missed_curves = []
                for key in measurement_names:
                    if key not in curves:
                        missed_curves.append(key)
                        has_curves = False
                if not has_curves:
                    dgcv_logging.get_logger("Operating Condition").warning(
                        f"Test without {curves_name} curve for keys {missed_curves}"
                    )
        return has_curves

    def validate(
        self,
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
                pcs_bm_name,
                working_path,
                jobs_output_dir,
                event_params,
                fs,
                curves,
            )
        else:
            results = {"compliance": False, "curves": None}

        results["udim"] = self._curves_manager.get_producer_curves().get_generator_u_dim()
        return success, results

    def has_required_curves(
        self,
        pcs_bm_name: str,
        bm_name: str,
    ) -> tuple[Path, Path, dict, float, bool, bool, int, dict]:
        """Check if all curves are present.

        Parameters
        ----------
        pcs_bm_name: str
            Composite name, pcs + Benchmark name
        bm_name: str
            Benchmark name

        Returns
        -------
        Path
            Working path.
        Path
            Simulator output path.
        dict
            Event parameters
        float
            Frequency sampling
        bool
            True if simulation is success
        bool
            True if simulation calculated curves
        int
            0 all curves are present
            1 producer's curves are missing
            2 reference curves are missing
            3 all curves are missing
        dict
            Calculated and reference curves
        """
        dgcv_logging.get_logger("Operating Condition").info(
            "RUNNING BENCHMARK: " + pcs_bm_name + ", OPER. COND.: " + self._name
        )

        (
            working_oc_dir,
            jobs_output_dir,
            event_params,
            fs,
            success,
            has_simulated_curves,
            curves,
        ) = self.__obtain_curve(
            pcs_bm_name,
            bm_name,
        )

        # If the tool has the model, it is assumed that the simulated curves are always available,
        #  if they are not available it is due to a failure in the simulation, this event is
        #  handled differently.
        sim_curves = self._check_curves(
            curves["calculated"], "producer", not self._producer.is_dynawo_model()
        )
        ref_curves = self._check_curves(
            curves["reference"], "reference", self.__has_reference_curves()
        )

        if sim_curves and ref_curves:
            has_curves = 0
        elif not sim_curves and ref_curves:
            has_curves = 1
        elif sim_curves and not ref_curves:
            has_curves = 2
        else:
            dgcv_logging.get_logger("Operating Condition").warning("Test without curves")
            has_curves = 3

        return (
            working_oc_dir,
            jobs_output_dir,
            event_params,
            fs,
            success,
            has_simulated_curves,
            has_curves,
            curves,
        )

    def get_name(self) -> str:
        """Get the OperatingCondition name.

        Returns
        -------
        str
            OperatingCondition name
        """
        return self._name
