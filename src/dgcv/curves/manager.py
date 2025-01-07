from pathlib import Path

import pandas as pd

from dgcv.core.execution_parameters import Parameters
from dgcv.curves import curves_factory
from dgcv.files import manage_files
from dgcv.logging.logging import dgcv_logging
from dgcv.model.parameters import Disconnection_Model


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
        self._curves = dict()

        self._producer_curves = curves_factory.get_producer(
            parameters, pcs_benchmark_name, stable_time, lib_path, templates_path, pcs_name
        )
        self._reference_curves = curves_factory.get_reference(parameters)

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

        reference_event_start_time = None
        if self.__has_reference_curves():
            (
                reference_event_start_time,
                self._curves["reference"],
            ) = self.get_reference_curves().obtain_reference_curve(
                working_oc_dir, pcs_bm_name, oc_name, self.__get_reference_curves_path()
            )
        else:
            self._curves["reference"] = pd.DataFrame()

        (
            jobs_output_dir,
            event_params,
            fs,
            success,
            has_simulated_curves,
            self._curves["calculated"],
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
    ) -> tuple[Path, Path, dict, float, bool, bool, int]:
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
        """
        (
            working_oc_dir,
            jobs_output_dir,
            event_params,
            fs,
            success,
            has_simulated_curves,
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
            self._curves["calculated"],
            "producer",
            not self._producer.is_dynawo_model(),
        )
        ref_curves = self._check_curves(
            measurement_names,
            self._curves["reference"],
            "reference",
            self.__has_reference_curves(),
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
        )

    def get_producer_curves(self):
        return self._producer_curves

    def get_reference_curves(self):
        return self._reference_curves

    def get_curves(self, key: str):
        if key in self._curves and not self._curves[key].empty:
            return self._curves[key]

        return None

    def get_generator_u_dim(self) -> float:
        return self.get_producer_curves().get_generator_u_dim()

    def get_time_cct(
        self,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        fault_duration: float,
    ) -> float:
        return self.get_producer_curves().get_time_cct(
            working_oc_dir,
            jobs_output_dir,
            fault_duration,
        )

    def get_generators_imax(self) -> dict:
        return self.get_producer_curves().get_generators_imax()

    def get_disconnection_model(self) -> Disconnection_Model:
        return self.get_producer_curves().get_disconnection_model()

    def get_setpoint_variation(self, pcs_bm_oc_name: str) -> float:
        return self.get_producer_curves().get_setpoint_variation(pcs_bm_oc_name)
