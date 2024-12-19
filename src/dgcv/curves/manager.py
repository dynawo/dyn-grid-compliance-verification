from pathlib import Path

import pandas as pd

from dgcv.core.execution_parameters import Parameters
from dgcv.curves.curves import ImportedCurves
from dgcv.curves.producer_factory import get_producer_curves
from dgcv.files import manage_files
from dgcv.logging.logging import dgcv_logging


class CurvesManager:
    def __init__(
        self,
        parameters: Parameters,
        pcs_benchmark_name: str,
        stable_time: float,
        lib_path: Path,
        templates_path: Path,
        pcs_name: str,
    ):
        self._working_dir = parameters.get_working_dir()
        self._producer = parameters.get_producer()
        self._pcs_name = pcs_name

        self._producer_curves = get_producer_curves(
            parameters, pcs_benchmark_name, stable_time, lib_path, templates_path, pcs_name
        )
        self._reference_curves = ImportedCurves(parameters)

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
        oc_name: str,
    ):
        # Create a specific folder by operational point
        working_oc_dir = self._working_dir / self._pcs_name / bm_name / oc_name
        manage_files.create_dir(working_oc_dir)

        curves = dict()
        reference_event_start_time = None
        if self.__has_reference_curves():
            (
                reference_event_start_time,
                curves["reference"],
            ) = self.get_reference_curves().obtain_reference_curve(
                working_oc_dir, pcs_bm_name, oc_name, self.__get_reference_curves_path()
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
        ) = self.get_producer_curves().obtain_simulated_curve(
            working_oc_dir,
            pcs_bm_name,
            bm_name,
            oc_name,
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

    def _check_curves(
        self,
        measurement_names: list,
        curves: pd.DataFrame,
        curves_name: str,
        review_curves_set: bool,
    ) -> bool:
        has_curves = True
        if review_curves_set:
            if curves.empty:
                dgcv_logging.get_logger("Curves Manager").warning(
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
                    dgcv_logging.get_logger("Curves Manager").warning(
                        f"Test without {curves_name} curve for keys {missed_curves}"
                    )
        return has_curves

    def has_required_curves(
        self,
        measurement_names: list,
        pcs_bm_name: str,
        bm_name: str,
        oc_name: str,
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
            oc_name,
        )

        # If the tool has the model, it is assumed that the simulated curves are always available,
        #  if they are not available it is due to a failure in the simulation, this event is
        #  handled differently.
        sim_curves = self._check_curves(
            measurement_names,
            curves["calculated"],
            "producer",
            not self._producer.is_dynawo_model(),
        )
        ref_curves = self._check_curves(
            measurement_names, curves["reference"], "reference", self.__has_reference_curves()
        )

        if sim_curves and ref_curves:
            has_curves = 0
        elif not sim_curves and ref_curves:
            has_curves = 1
        elif sim_curves and not ref_curves:
            has_curves = 2
        else:
            dgcv_logging.get_logger("Curves Manager").warning("Test without curves")
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

    def get_producer_curves(self):
        return self._producer_curves

    def get_reference_curves(self):
        return self._reference_curves
