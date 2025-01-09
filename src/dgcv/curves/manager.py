import logging
from pathlib import Path

import pandas as pd

from dgcv.configuration.cfg import config
from dgcv.core.execution_parameters import Parameters
from dgcv.curves import curves_factory
from dgcv.files import manage_files
from dgcv.logging.logging import dgcv_logging
from dgcv.model.parameters import Disconnection_Model
from dgcv.sigpro import signal_windows, sigpro
from dgcv.validation import sanity_checks


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
        self._curves = {"calculated": pd.DataFrame(), "reference": pd.DataFrame()}

        self._producer_curves = curves_factory.get_producer(
            parameters, pcs_benchmark_name, stable_time, lib_path, templates_path, pcs_name
        )
        self._reference_curves = curves_factory.get_reference(parameters)

    def __has_reference_curves(self) -> bool:
        return self._producer.has_reference_curves_path()

    def _get_reference_curves_path(self) -> Path:
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
                working_oc_dir, pcs_bm_name, oc_name, self._get_reference_curves_path()
            )

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

    def _save_curves(self, working_oc_dir: Path):
        if not self.get_curves("calculated").empty:
            self.get_curves("calculated").to_csv(working_oc_dir / "curves_calculated.csv", sep=";")
        if not self.get_curves("reference").empty:
            self.get_curves("reference").to_csv(working_oc_dir / "curves_reference.csv", sep=";")

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
            self.get_curves("calculated"),
            "producer",
            not self._producer.is_dynawo_model(),
        )
        ref_curves = self._check_curves(
            measurement_names,
            self.get_curves("reference"),
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

        self._save_curves(working_oc_dir)

        return (
            working_oc_dir,
            jobs_output_dir,
            event_params,
            fs,
            success,
            has_simulated_curves,
            has_curves,
        )

    def prepare_curves(
        self,
        working_path: Path,
        event_params: dict,
        fs: float,
        setpoint_tracking_controlled_magnitude: bool,
    ):
        # Activate this code to use the curve calculated as a reference curve,
        # only for debug cases without reference curves.
        # if reference_curves is None:
        #     reference_curves = calculated_curves

        csv_calculated_curves = self.get_curves("calculated")
        csv_reference_curves = self.get_curves("reference")

        t_com = config.get_float("GridCode", "t_com", 0.002)
        cutoff = config.get_float("GridCode", "cutoff", 15.0)
        sanity_checks.check_sampling_interval(t_com, cutoff)

        resampling_fs = 1 / t_com

        # First resampling: Ensure constant time step signal.
        calculated_curves = sigpro.resampling_signal(csv_calculated_curves, resampling_fs)
        calculated_curves = sigpro.lowpass_signal(calculated_curves, cutoff, resampling_fs)

        reference_curves = sigpro.ensure_rms_signals(csv_reference_curves, fs)
        reference_curves = sigpro.resampling_signal(reference_curves, resampling_fs)
        reference_curves = sigpro.lowpass_signal(reference_curves, cutoff, resampling_fs)

        # Second resampling: Ensure same time grid for both signals.
        calculated_curves, reference_curves = sigpro.interpolate_same_time_grid(
            calculated_curves, reference_curves
        )

        t_integrator_tol = config.get_float("GridCode", "t_integrator_tol", 0.000001)
        if setpoint_tracking_controlled_magnitude:
            t_faultQS_excl = 0.0
            t_clearQS_excl = 0.0
        else:
            t_faultQS_excl = config.get_float("GridCode", "t_faultQS_excl", 0.020)
            t_clearQS_excl = config.get_float("GridCode", "t_clearQS_excl", 0.060)

        t_faultLP_excl = config.get_float("GridCode", "t_faultLP_excl", 0.050)
        self._before_calculated, self._during_calculated, self._after_calculated = (
            signal_windows.get(
                calculated_curves,
                signal_windows.calculate(
                    list(calculated_curves["time"]),
                    event_params["start_time"],
                    event_params["duration_time"],
                    t_integrator_tol,
                    t_faultLP_excl,
                    t_faultQS_excl,
                    t_clearQS_excl,
                ),
            )
        )
        sanity_checks.check_pre_stable(
            list(self._before_calculated["time"]),
            list(self._before_calculated["BusPDR_BUS_Voltage"]),
        )

        self._before_reference, self._during_reference, self._after_reference = signal_windows.get(
            reference_curves,
            signal_windows.calculate(
                list(reference_curves["time"]),
                event_params["start_time"],
                event_params["duration_time"],
                t_integrator_tol,
                t_faultLP_excl,
                t_faultQS_excl,
                t_clearQS_excl,
            ),
        )

        if dgcv_logging.getEffectiveLevel() == logging.DEBUG:
            calculated_curves.to_csv(working_path / "signal.csv", sep=";")
            reference_curves.to_csv(working_path / "reference.csv", sep=";")

    def get_producer_curves(self) -> curves_factory.ProducerCurves:
        """Get the producer curves."""
        return self._producer_curves

    def get_reference_curves(self) -> curves_factory.ProducerCurves:
        """Get the reference curves."""
        return self._reference_curves

    def get_curves(self, curve: str) -> pd.DataFrame:
        """Get the curves."""
        if curve not in self._curves:
            return pd.DataFrame()

        if self._curves[curve].empty:
            return pd.DataFrame()

        return self._curves[curve]

    def get_exclusion_times(self) -> tuple[float, float, float, float]:
        """Get the exclusion times."""
        excl1_t0 = self._before_calculated["time"].iloc[-1]
        if len(self._during_calculated["time"]):
            excl1_t = self._during_calculated["time"].iloc[0]
            excl2_t0 = self._during_calculated["time"].iloc[-1]
            excl2_t = self._after_calculated["time"].iloc[0]
        else:
            excl1_t = self._after_calculated["time"].iloc[0]
            excl2_t0 = 0.0
            excl2_t = 0.0

        return excl1_t0, excl1_t, excl2_t0, excl2_t

    def get_curves_by_windows(self, windows: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Get the curves by windows."""
        if windows == "before":
            return self._before_calculated, self._before_reference
        elif windows == "during":
            return self._during_calculated, self._during_reference
        elif windows == "after":
            return self._after_calculated, self._after_reference

        raise ValueError(f"Invalid windows: {windows}")

    def get_generator_u_dim(self) -> float:
        """Get the generator U dimension."""
        return self.get_producer_curves().get_generator_u_dim()

    def get_time_cct(
        self,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        fault_duration: float,
    ) -> float:
        """Get the time CCT."""
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
