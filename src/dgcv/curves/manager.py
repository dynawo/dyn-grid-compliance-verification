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
        self._before_filters_curves = {"calculated": pd.DataFrame(), "reference": pd.DataFrame()}
        self._curves = {"calculated": pd.DataFrame(), "reference": pd.DataFrame()}
        self._windows = {"calculated": dict(), "reference": dict()}

        self._producer_curves_generator = curves_factory.get_producer(
            parameters, pcs_benchmark_name, stable_time, lib_path, templates_path, pcs_name
        )
        self._reference_curves_generator = curves_factory.get_reference(parameters)

    def __copy_curves_to_before_filters(self):
        self._before_filters_curves["calculated"] = self._curves["calculated"].copy()
        self._before_filters_curves["reference"] = self._curves["reference"].copy()

    def __get_before_filters_curves(self, curve: str) -> pd.DataFrame:
        if curve not in self._before_filters_curves:
            return pd.DataFrame()

        if self._before_filters_curves[curve].empty:
            return pd.DataFrame()

        return self._before_filters_curves[curve]

    def __get_producer_curves_generator(self):
        return self._producer_curves_generator

    def __get_reference_curves_generator(self):
        return self._reference_curves_generator

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
            ) = self.__get_reference_curves_generator().obtain_reference_curve(
                working_oc_dir, pcs_bm_name, oc_name, self.__get_reference_curves_path()
            )

        (
            jobs_output_dir,
            event_params,
            fs,
            success,
            has_simulated_curves,
            self._curves["calculated"],
        ) = self.__get_producer_curves_generator().obtain_simulated_curve(
            working_oc_dir,
            pcs_bm_name,
            bm_name,
            oc_name,
            reference_event_start_time,
        )

        self.__copy_curves_to_before_filters()

        return (
            working_oc_dir,
            jobs_output_dir,
            event_params,
            fs,
            success,
            has_simulated_curves,
        )

    def __check_curves(
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

    def __save_curves(self, working_oc_dir: Path):
        if not self.get_curves("calculated").empty:
            self.get_curves("calculated").to_csv(working_oc_dir / "curves_calculated.csv", sep=";")
        if not self.get_curves("reference").empty:
            self.get_curves("reference").to_csv(working_oc_dir / "curves_reference.csv", sep=";")

    def __get_signal_processing_windows(self, curve: str, windows: str) -> tuple[float, float]:
        return self._windows[curve]["sigpro"][windows]

    def __get_validation_windows(self, curve: str, windows: str) -> tuple[float, float]:
        return self._windows[curve]["validate"][windows]

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
        measurement_names: list
            Measurement names
        pcs_bm_name: str
            Composite name, pcs + Benchmark name
        bm_name: str
            Benchmark name
        oc_name: str
            Operating Condition name

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
        sim_curves = self.__check_curves(
            measurement_names,
            self.get_curves("calculated"),
            "producer",
            not self._producer.is_dynawo_model(),
        )
        ref_curves = self.__check_curves(
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

        self.__save_curves(working_oc_dir)

        return (
            working_oc_dir,
            jobs_output_dir,
            event_params,
            fs,
            success,
            has_simulated_curves,
            has_curves,
        )

    def apply_signal_processing(
        self,
        working_path: Path,
        event_params: dict,
        fs: float,
        setpoint_tracking_controlled_magnitude: bool,
    ):
        """Apply signal processing.

        Parameters
        ----------
        working_path: Path
            Working path.
        event_params: dict
            Event parameters.
        fs: float
            Frequency sampling.
        setpoint_tracking_controlled_magnitude: bool
            Setpoint tracking controlled magnitude.

        Method
        ------
        This class method centralizes the overall procedure for the signal processing of all
        curves. It follows these steps (their order is important):
            * When needed, convert the signal from EMT (abc) to RMS (positive sequence).
            * First resampling: for ensuring a constant time-step (uses monotone interp.).
              Note that each set of signals is interpolated to its own minimum observed step,
              in order to preserve their original time-resolution.
            * Windowing: calculate curve metadata about the validation windows specified by the
              test and the exclusion zones at the boundaries of each of those windows.
            * Filtering: apply a low-pass filter to the signal (normally performed separately
              per window)
            * Second resampling: for ensuring a common time-grid for both sets. Note this is
              actually a _downsampling_ for most signals (since most signals are expected to
              have a samplig rate higher than 2fc), therefore this step needs to be done
              _after_ low-pass filtering, to ensure there's no aliasing.
        """
        # TODO: refactor this function so that it really adheres to the Method described above.

        csv_calculated_curves = self.__get_before_filters_curves("calculated")
        csv_reference_curves = self.__get_before_filters_curves("reference")

        # Activate this code to use the curve calculated as a reference curve,
        # only for debug cases without reference curves.
        # if reference_curves is None:
        #     csv_reference_curves = csv_calculated_curves

        t_com = config.get_float("GridCode", "t_com", 0.002)
        cutoff = config.get_float("GridCode", "cutoff", 15.0)
        sanity_checks.check_sampling_interval(t_com, cutoff)

        resampling_fs = 1 / t_com

        # First resampling: ensure a constant time-step signal
        # TODO: preserve the finest time-resolution instead of using a fixed t_com here
        calculated_curves = sigpro.resampling_signal(csv_calculated_curves, resampling_fs)

        reference_curves = sigpro.ensure_rms_signals(csv_reference_curves, fs)
        # TODO: preserve the finest time-resolution instead of using a fixed t_com here
        reference_curves = sigpro.resampling_signal(reference_curves, resampling_fs)

        calc_time_values = list(calculated_curves["time"])
        self._windows["calculated"] = signal_windows.calculate(
            calc_time_values,
            event_params["start_time"],
            event_params["duration_time"],
            setpoint_tracking_controlled_magnitude,
        )
        self._windows["reference"] = signal_windows.calculate(
            list(reference_curves["time"]),
            event_params["start_time"],
            event_params["duration_time"],
            setpoint_tracking_controlled_magnitude,
        )

        # After their respective resampling and after windowing, we can apply the filters
        calculated_curves = sigpro.filter_signal(calculated_curves, cutoff, resampling_fs)
        reference_curves = sigpro.filter_signal(reference_curves, cutoff, resampling_fs)

        # Second resampling: ensure both signals are on the same time grid
        # Note it doesn't matter if this is a downsampling for any of the two sets, because the
        # low-pass filter has already been applied (therefore, no aliasing is produced).
        calculated_curves, reference_curves = sigpro.interpolate_same_time_grid(
            calculated_curves, reference_curves
        )
        self._curves["calculated"] = calculated_curves
        self._curves["reference"] = reference_curves

        # Sanity check: the "pre" window should be in the steady-state
        t_from, t_to = self.__get_validation_windows("calculated", "before")
        before_calculated = signal_windows.get(self.get_curves("calculated"), t_from, t_to)
        sanity_checks.check_pre_stable(
            list(before_calculated["time"]),
            list(before_calculated["BusPDR_BUS_Voltage"]),
        )

        if dgcv_logging.getEffectiveLevel() == logging.DEBUG:
            calculated_curves.to_csv(working_path / "signal.csv", sep=";")
            reference_curves.to_csv(working_path / "reference.csv", sep=";")

    def get_curves(self, curve: str) -> pd.DataFrame:
        """Get the curves.

        Parameters
        ----------
        curve: str
            calculated or reference curves.

        Returns
        -------
        pd.DataFrame
            Dataframe with the selected curves.
        """
        if curve not in self._curves:
            return pd.DataFrame()

        if self._curves[curve].empty:
            return pd.DataFrame()

        return self._curves[curve]

    def get_exclusion_times(self) -> tuple[float, float, float, float]:
        """Get the exclusion times.

        Returns
        -------
        float
            Exclusion time before the event is triggered.
        float
            Exclusion time after the event is triggered.
        float
            Exclusion time before the event is cleared, if the event is cleared.
        float
            Exclusion time after the event is cleared, if the event is cleared.
        """
        _, t_to_b = self.__get_validation_windows("calculated", "before")
        t_from_a, _ = self.__get_validation_windows("calculated", "after")
        t_from_d, t_to_d = self.__get_validation_windows("calculated", "during")
        excl1_t0 = t_to_b
        if t_from_d < t_to_d:
            excl1_t = t_from_d
            excl2_t0 = t_to_d
            excl2_t = t_from_a
        else:
            excl1_t = t_from_a
            excl2_t0 = 0.0
            excl2_t = 0.0

        return excl1_t0, excl1_t, excl2_t0, excl2_t

    def get_curves_by_windows(self, windows: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Get the curves by windows.

        Parameters
        ----------
        windows: str
            before, during or after window.

        Returns
        -------
        pd.DataFrame
            A dataframe with the selected window of calculated curves.
        pd.DataFrame
            A dataframe with the selected window of reference curves.
        """
        t_from_calc, t_to_calc = self.__get_validation_windows("calculated", windows)
        t_from_ref, t_to_ref = self.__get_validation_windows("reference", windows)
        return signal_windows.get(
            self.get_curves("calculated"), t_from_calc, t_to_calc
        ), signal_windows.get(self.get_curves("reference"), t_from_ref, t_to_ref)

    def get_generator_u_dim(self) -> float:
        """Get the generator Udim.

        Returns
        -------
        float
            Generator Udim.
        """
        return self.__get_producer_curves_generator().get_generator_u_dim()

    def get_time_cct(
        self,
        working_oc_dir: Path,
        jobs_output_dir: Path,
        fault_duration: float,
    ) -> float:
        """Get the time CCT.

        Parameters
        ----------
        working_oc_dir: Path
            Working path.
        jobs_output_dir: Path
            Jobs output path.
        fault_duration: float
            Fault duration.

        Returns
        -------
        float
            Time CCT.
        """
        return self.__get_producer_curves_generator().get_time_cct(
            working_oc_dir,
            jobs_output_dir,
            fault_duration,
        )

    def get_generators_imax(self) -> dict:
        """Get maximum continuous current.

        Returns
        -------
        dict
            Get maximum continuous current by generator.
        """
        return self.__get_producer_curves_generator().get_generators_imax()

    def get_disconnection_model(self) -> Disconnection_Model:
        """Get all equipment in the model that can be disconnected in the simulation.
        When there is no model to simulate, it is not possible to detect the equipment
        that has been disconnected.

        Returns
        -------
        Disconnection_Model
            Equipment that can be disconnected.
        """
        return self.__get_producer_curves_generator().get_disconnection_model()

    def get_setpoint_variation(self, pcs_bm_oc_name: str) -> float:
        """Get the setpoint variation.

        Parameters
        ----------
        pcs_bm_oc_name: str
            Composite name, pcs + Benchmark name + Operating Condition name.

        Returns
        -------
        float
            Setpoint variation.
        """
        return self.__get_producer_curves_generator().get_setpoint_variation(pcs_bm_oc_name)

    def is_field_measurements(self) -> bool:
        """Check if the reference curves are field measurements.

        Returns
        -------
        bool
            True if the reference signals are field measurements.
        """
        return self.__get_reference_curves_generator().is_field_measurements()
