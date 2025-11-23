#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from dycov.core.validator import Validator
from dycov.model.parameters import Disconnection_Model


class DummyProducer:
    """A dummy Producer class for testing purposes."""

    def __init__(self, sim_type):
        """Initializes the DummyProducer.

        Parameters
        ----------
        sim_type : int
            The simulation type.
        """
        self._sim_type = sim_type

    def get_sim_type(self):
        """Returns the simulation type."""
        return self._sim_type


class DummyCurvesManager:
    """A dummy CurvesManager class for testing purposes."""

    def __init__(
        self,
        generator_u_dim=123.4,
        time_cct=0.5,
        generators_imax=None,
        disconnection_model=None,
        setpoint_variation=0.0,
        calculated_curves=None,
        reference_curves=None,
        windows=None,
    ):
        """Initializes the DummyCurvesManager.

        Parameters
        ----------
        generator_u_dim : float, optional
            Dummy generator_u_dim value. Defaults to 123.4.
        time_cct : float, optional
            Dummy time_cct value. Defaults to 0.5.
        generators_imax : dict, optional
            Dummy generators_imax value. Defaults to {"gen1": 100.0}.
        disconnection_model : Disconnection_Model, optional
            Dummy disconnection_model. Defaults to a new Disconnection_Model instance.
        setpoint_variation : float, optional
            Dummy setpoint_variation. Defaults to 0.0.
        calculated_curves : dict, optional
            Dummy calculated_curves. Defaults to None.
        reference_curves : dict, optional
            Dummy reference_curves. Defaults to None.
        windows : dict, optional
            Dummy windows. Defaults to None.
        """
        self._generator_u_dim = generator_u_dim
        self._time_cct = time_cct
        self._generators_imax = generators_imax if generators_imax is not None else {"gen1": 100.0}
        self._disconnection_model = (
            disconnection_model
            if disconnection_model is not None
            else Disconnection_Model(auxload=[], auxload_xfmr=[], stepup_xfmrs=[], gen_intline=[])
        )
        self._setpoint_variation = setpoint_variation
        self._calculated_curves = (
            calculated_curves
            if calculated_curves is not None
            else {"curve1": pd.DataFrame({"a": [1, 2]})}
        )
        self._reference_curves = (
            reference_curves
            if reference_curves is not None
            else {"curve2": pd.DataFrame({"b": [3, 4]})}
        )
        self._windows = (
            windows
            if windows is not None
            else {"before": (0.0, 1.0), "during": (1.0, 2.0), "after": (2.0, 3.0)}
        )

    def get_generator_u_dim(self):
        """Returns dummy generator_u_dim."""
        return self._generator_u_dim

    def get_time_cct(self, working_oc_dir, jobs_output_dir, duration_time, bm_name, oc_name):
        """Returns dummy time_cct."""
        return self._time_cct

    def get_generators_imax(self):
        """Returns dummy generators_imax."""
        return self._generators_imax

    def get_disconnection_model(self):
        """Returns dummy disconnection_model."""
        return self._disconnection_model

    def get_setpoint_variation(self, cfg_oc_name):
        """Returns dummy setpoint_variation."""
        return self._setpoint_variation

    def get_curves(self, curve):
        """Returns dummy curves based on the curve type."""
        if curve == "calculated":
            return self._calculated_curves
        elif curve == "reference":
            return self._reference_curves
        return {}

    def get_exclusion_times(self):
        """Returns dummy exclusion times."""
        return (0.1, 0.2, 0.3, 0.4)

    def get_curves_by_windows(self, windows):
        """Returns dummy curves by windows."""
        return (pd.DataFrame({"x": [1]}), pd.DataFrame({"y": [2]}))


# Define a concrete subclass for testing abstract methods
class CustomValidator(Validator):
    def __init__(
        self,
        curves_manager,
        producer,
        validations,
        is_field_measurements,
        pcs_name,
        bm_name,
    ):
        super().__init__(
            curves_manager,
            producer,
            validations,
            is_field_measurements,
            pcs_name,
            bm_name,
        )

    def validate(self, oc_name, results_path, sim_output_path, event_params) -> dict:
        """Dummy implementation for abstract method."""
        return {"compliance": True, "details": {"oc_name": oc_name}}

    def get_measurement_names(self) -> list:
        """Dummy implementation for abstract method."""
        return []


def test_validator_initialization():
    """Tests the initialization of the Validator class."""
    curves_manager = DummyCurvesManager()
    producer = DummyProducer(sim_type=1)
    validator = CustomValidator(  # Use CustomValidator instead of Validator
        curves_manager,
        producer,
        validations=["val1", "val2"],
        is_field_measurements=True,
        pcs_name="PCS1",
        bm_name="BM1",
    )

    assert validator._curves_manager == curves_manager
    assert validator._producer == producer
    assert validator._validations == ["val1", "val2"]
    assert validator._is_field_measurements is True
    assert validator._pcs_name == "PCS1"
    assert validator._bm_name == "BM1"
    assert validator._time_cct is None
    assert validator._disconnection_model is None


def test_set_time_cct():
    """Tests the setter for time_cct."""
    curves_manager = DummyCurvesManager()
    producer = DummyProducer(sim_type=1)
    validator = CustomValidator(  # Use CustomValidator
        curves_manager,
        producer,
        validations=[],
        is_field_measurements=False,
        pcs_name="PCS",
        bm_name="BM",
    )
    validator.set_time_cct(2.5)
    assert validator._time_cct == 2.5


def test_set_generators_imax():
    """Tests the setter for generators_imax."""
    curves_manager = DummyCurvesManager()
    producer = DummyProducer(sim_type=1)
    validator = CustomValidator(  # Use CustomValidator
        curves_manager,
        producer,
        validations=[],
        is_field_measurements=False,
        pcs_name="PCS",
        bm_name="BM",
    )
    validator.set_generators_imax({"gen2": 200.0})
    assert validator._generators_imax == {"gen2": 200.0}


def test_set_disconnection_model():
    """Tests the setter for disconnection_model."""
    curves_manager = DummyCurvesManager()
    producer = DummyProducer(sim_type=1)
    validator = CustomValidator(  # Use CustomValidator
        curves_manager,
        producer,
        validations=[],
        is_field_measurements=False,
        pcs_name="PCS",
        bm_name="BM",
    )
    dm = Disconnection_Model(
        auxload=["a"], auxload_xfmr=["b"], stepup_xfmrs=["c"], gen_intline=["d"]
    )
    validator.set_disconnection_model(dm)
    assert validator._disconnection_model == dm


def test_set_setpoint_variation():
    """Tests the setter for setpoint_variation."""
    curves_manager = DummyCurvesManager()
    producer = DummyProducer(sim_type=1)
    validator = CustomValidator(  # Use CustomValidator
        curves_manager,
        producer,
        validations=[],
        is_field_measurements=False,
        pcs_name="PCS",
        bm_name="BM",
    )
    validator.set_setpoint_variation(0.1)
    assert validator._setpoint_variation == 0.1


def test_get_generator_u_dim_returns_correct_value():
    curves_manager = DummyCurvesManager(generator_u_dim=456.7)
    producer = DummyProducer(sim_type=1)
    validator = CustomValidator(  # Use CustomValidator
        curves_manager,
        producer,
        validations=[],
        is_field_measurements=False,
        pcs_name="PCS",
        bm_name="BM",
    )
    assert validator.get_generator_u_dim() == 456.7


def test_complete_producer_sets_all_attributes():
    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        curves_manager = DummyCurvesManager(
            generator_u_dim=111.1,
            time_cct=2.5,
            generators_imax={"g1": 10.0},
            disconnection_model=Disconnection_Model(
                auxload=[1], auxload_xfmr=[2], stepup_xfmrs=[3], gen_intline=[4]
            ),
            setpoint_variation=0.99,
        )
        producer = DummyProducer(sim_type=0)
        validator = CustomValidator(  # Use CustomValidator
            curves_manager,
            producer,
            validations=["time_cct"],
            is_field_measurements=False,
            pcs_name="PCS",
            bm_name="BM",
        )
        working_oc_dir = path / "oc"
        jobs_output_dir = path / "jobs"
        event_params = {"duration_time": 2.5}
        cfg_oc_name = "cfg"
        validator.complete_parameters(
            working_oc_dir, jobs_output_dir, event_params, cfg_oc_name, "OC"
        )
        assert validator._time_cct == 2.5
        assert validator._generators_imax == {"g1": 10.0}
        assert validator._disconnection_model == Disconnection_Model(
            auxload=[1], auxload_xfmr=[2], stepup_xfmrs=[3], gen_intline=[4]
        )
        assert validator._setpoint_variation == 0.99


def test_has_validations_returns_true_when_validations_exist():
    curves_manager = DummyCurvesManager()
    producer = DummyProducer(sim_type=1)
    validator = CustomValidator(  # Use CustomValidator
        curves_manager,
        producer,
        validations=["some_validation"],
        is_field_measurements=False,
        pcs_name="PCS",
        bm_name="BM",
    )
    assert validator.has_validations() is True


def test_get_curve_by_name_returns_empty_for_missing_curve():
    curves_manager = DummyCurvesManager(
        calculated_curves={"curve1": pd.DataFrame({"a": [1]})},
        reference_curves={"curve2": pd.DataFrame({"b": [2]})},
    )
    producer = DummyProducer(sim_type=1)
    validator = CustomValidator(  # Use CustomValidator
        curves_manager,
        producer,
        validations=[],
        is_field_measurements=False,
        pcs_name="PCS",
        bm_name="BM",
    )
    # calculated curve missing
    df = validator._get_calculated_curve_by_name("missing_curve")
    assert isinstance(df, pd.DataFrame)
    assert df.empty
    # reference curve missing
    ref = validator._get_reference_curve_by_name("missing_curve")
    assert ref is None


def test_has_validations_returns_false_when_no_validations():
    curves_manager = DummyCurvesManager()
    producer = DummyProducer(sim_type=2)
    validator = CustomValidator(  # Use CustomValidator
        curves_manager,
        producer,
        validations=[],
        is_field_measurements=False,
        pcs_name="PCS",
        bm_name="BM",
    )
    assert validator.has_validations() is False


def test_complete_producer_handles_missing_optional_producer():
    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        curves_manager = DummyCurvesManager(
            generators_imax={"g2": 20.0},
            disconnection_model=Disconnection_Model(
                auxload=[], auxload_xfmr=[], stepup_xfmrs=[], gen_intline=[]
            ),
            setpoint_variation=0.0,
        )
        producer = DummyProducer(sim_type=0)
        # No "time_cct" in validations, so set_time_cct should not be called
        validator = CustomValidator(  # Use CustomValidator
            curves_manager,
            producer,
            validations=[],
            is_field_measurements=False,
            pcs_name="PCS",
            bm_name="BM",
        )
        working_oc_dir = path / "oc2"
        jobs_output_dir = path / "jobs2"
        event_params = {"duration_time": 1.0}
        cfg_oc_name = "cfg2"
        validator.complete_parameters(
            working_oc_dir, jobs_output_dir, event_params, cfg_oc_name, "OC"
        )
        assert validator._time_cct is None
        assert validator._generators_imax == {"g2": 20.0}
        assert validator._disconnection_model == Disconnection_Model(
            auxload=[], auxload_xfmr=[], stepup_xfmrs=[], gen_intline=[]
        )
        assert validator._setpoint_variation == 0.0


def test_get_sim_type_returns_expected_value():
    curves_manager = DummyCurvesManager()
    producer = DummyProducer(sim_type=42)
    validator = CustomValidator(  # Use CustomValidator
        curves_manager,
        producer,
        validations=[],
        is_field_measurements=False,
        pcs_name="PCS",
        bm_name="BM",
    )
    assert validator.get_sim_type() == 42


def test_set_generators_imax_handles_empty_dict():
    curves_manager = DummyCurvesManager()
    producer = DummyProducer(sim_type=0)
    validator = CustomValidator(  # Use CustomValidator
        curves_manager,
        producer,
        validations=[],
        is_field_measurements=False,
        pcs_name="PCS",
        bm_name="BM",
    )
    validator.set_generators_imax({})
    assert validator._generators_imax == {}


def test_validate_returns_compliance_results_dict():
    class CustomCurvesManager(DummyCurvesManager):
        pass

    class CustomValidator(Validator):
        def __init__(
            self,
            curves_manager,
            producer,
            validations,
            is_field_measurements,
            pcs_name,
            bm_name,
        ):
            super().__init__(
                curves_manager,
                producer,
                validations,
                is_field_measurements,
                pcs_name,
                bm_name,
            )

        # Corrected signature to match the abstract method in validator.py
        def validate(self, oc_name, results_path, sim_output_path, event_params) -> dict:
            """Simulates compliance result."""
            return {"compliance": True, "details": {"oc_name": oc_name}}

        def get_measurement_names(self) -> list:
            """Dummy implementation for abstract method."""
            return []

    curves_manager = CustomCurvesManager()
    producer = DummyProducer(sim_type=1)
    validator = CustomValidator(
        curves_manager,
        producer,
        validations=["val"],
        is_field_measurements=False,
        pcs_name="PCS",
        bm_name="BM",
    )
    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        # Remove the extra 'fs' argument when calling validate
        result = validator.validate("OC1", path / "results", "sim", {"param": 1})
        assert isinstance(result, dict)
        assert "compliance" in result
        assert result["compliance"] is True
        assert "details" in result
        assert result["details"]["oc_name"] == "OC1"


def test_get_measurement_names_returns_empty_when_no_validations():
    class CustomValidator(Validator):
        def __init__(
            self,
            curves_manager,
            producer,
            validations,
            is_field_measurements,
            pcs_name,
            bm_name,
        ):
            super().__init__(
                curves_manager,
                producer,
                validations,
                is_field_measurements,
                pcs_name,
                bm_name,
            )

        def get_measurement_names(self):
            return []

        def validate(self, oc_name, results_path, sim_output_path, event_params) -> dict:
            """Dummy implementation for abstract method."""
            return {}

    curves_manager = DummyCurvesManager()
    producer = DummyProducer(sim_type=1)
    validator = CustomValidator(
        curves_manager,
        producer,
        validations=[],
        is_field_measurements=False,
        pcs_name="PCS",
        bm_name="BM",
    )
    assert validator.get_measurement_names() == []
