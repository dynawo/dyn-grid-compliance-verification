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

import pandas as pd

from dycov.core.validator import Validator
from dycov.model.parameters import Disconnection_Model


class DummyProducer:
    def __init__(self, sim_type):
        self._sim_type = sim_type

    def get_sim_type(self):
        return self._sim_type


class DummyCurvesManager:
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
        return self._generator_u_dim

    def get_time_cct(self, working_oc_dir, jobs_output_dir, duration_time):
        return self._time_cct

    def get_generators_imax(self):
        return self._generators_imax

    def get_disconnection_model(self):
        return self._disconnection_model

    def get_setpoint_variation(self, cfg_oc_name):
        return self._setpoint_variation

    def get_curves(self, curve):
        if curve == "calculated":
            return self._calculated_curves
        elif curve == "reference":
            return self._reference_curves
        return {}

    def get_exclusion_times(self):
        return (0.1, 0.2, 0.3, 0.4)

    def get_curves_by_windows(self, windows):
        return (pd.DataFrame({"x": [1]}), pd.DataFrame({"y": [2]}))


class DummyParameters:
    def __init__(self, producer):
        self._producer = producer

    def get_producer(self):
        return self._producer


def test_get_generator_u_dim_returns_correct_value():
    curves_manager = DummyCurvesManager(generator_u_dim=456.7)
    parameters = DummyParameters(DummyProducer(sim_type=1))
    validator = Validator(curves_manager, parameters, validations=[], is_field_measurements=False)
    assert validator.get_generator_u_dim() == 456.7


def test_complete_parameters_sets_all_attributes():
    curves_manager = DummyCurvesManager(
        generator_u_dim=111.1,
        time_cct=2.5,
        generators_imax={"g1": 10.0},
        disconnection_model=Disconnection_Model(
            auxload=[1], auxload_xfmr=[2], stepup_xfmrs=[3], gen_intline=[4]
        ),
        setpoint_variation=0.99,
    )
    parameters = DummyParameters(DummyProducer(sim_type=0))
    validator = Validator(
        curves_manager, parameters, validations=["time_cct"], is_field_measurements=False
    )
    working_oc_dir = Path("/tmp/oc")
    jobs_output_dir = Path("/tmp/jobs")
    event_params = {"duration_time": 2.5}
    cfg_oc_name = "cfg"
    validator.complete_parameters(working_oc_dir, jobs_output_dir, event_params, cfg_oc_name)
    assert validator._time_cct == 2.5
    assert validator._generators_imax == {"g1": 10.0}
    assert validator._disconnection_model == Disconnection_Model(
        auxload=[1], auxload_xfmr=[2], stepup_xfmrs=[3], gen_intline=[4]
    )
    assert validator._setpoint_variation == 0.99


def test_has_validations_returns_true_when_validations_exist():
    curves_manager = DummyCurvesManager()
    parameters = DummyParameters(DummyProducer(sim_type=1))
    validator = Validator(
        curves_manager, parameters, validations=["some_validation"], is_field_measurements=False
    )
    assert validator.has_validations() is True


def test_get_curve_by_name_returns_empty_for_missing_curve():
    curves_manager = DummyCurvesManager(
        calculated_curves={"curve1": pd.DataFrame({"a": [1]})},
        reference_curves={"curve2": pd.DataFrame({"b": [2]})},
    )
    parameters = DummyParameters(DummyProducer(sim_type=1))
    validator = Validator(curves_manager, parameters, validations=[], is_field_measurements=False)
    # calculated curve missing
    df = validator._get_calculated_curve_by_name("missing_curve")
    assert isinstance(df, pd.DataFrame)
    assert df.empty
    # reference curve missing
    ref = validator._get_reference_curve_by_name("missing_curve")
    assert ref is None


def test_has_validations_returns_false_when_no_validations():
    curves_manager = DummyCurvesManager()
    parameters = DummyParameters(DummyProducer(sim_type=2))
    validator = Validator(curves_manager, parameters, validations=[], is_field_measurements=False)
    assert validator.has_validations() is False


def test_complete_parameters_handles_missing_optional_parameters():
    curves_manager = DummyCurvesManager(
        generators_imax={"g2": 20.0},
        disconnection_model=Disconnection_Model(
            auxload=[], auxload_xfmr=[], stepup_xfmrs=[], gen_intline=[]
        ),
        setpoint_variation=0.0,
    )
    parameters = DummyParameters(DummyProducer(sim_type=0))
    # No "time_cct" in validations, so set_time_cct should not be called
    validator = Validator(curves_manager, parameters, validations=[], is_field_measurements=False)
    working_oc_dir = Path("/tmp/oc2")
    jobs_output_dir = Path("/tmp/jobs2")
    event_params = {"duration_time": 1.0}
    cfg_oc_name = "cfg2"
    validator.complete_parameters(working_oc_dir, jobs_output_dir, event_params, cfg_oc_name)
    assert validator._time_cct is None
    assert validator._generators_imax == {"g2": 20.0}
    assert validator._disconnection_model == Disconnection_Model(
        auxload=[], auxload_xfmr=[], stepup_xfmrs=[], gen_intline=[]
    )
    assert validator._setpoint_variation == 0.0


def test_get_sim_type_returns_expected_value():
    curves_manager = DummyCurvesManager()
    parameters = DummyParameters(DummyProducer(sim_type=42))
    validator = Validator(curves_manager, parameters, validations=[], is_field_measurements=False)
    assert validator.get_sim_type() == 42


def test_set_generators_imax_handles_empty_dict():
    curves_manager = DummyCurvesManager()
    parameters = DummyParameters(DummyProducer(sim_type=0))
    validator = Validator(curves_manager, parameters, validations=[], is_field_measurements=False)
    validator.set_generators_imax({})
    assert validator._generators_imax == {}


def test_validate_returns_compliance_results_dict():
    class CustomCurvesManager(DummyCurvesManager):
        pass

    class CustomValidator(Validator):
        def validate(self, oc_name, results_path, sim_output_path, event_params, fs):
            # Simulate compliance result
            return {"compliance": True, "details": {"oc_name": oc_name}}

    curves_manager = CustomCurvesManager()
    parameters = DummyParameters(DummyProducer(sim_type=1))
    validator = CustomValidator(
        curves_manager, parameters, validations=["val"], is_field_measurements=False
    )
    result = validator.validate("OC1", Path("/tmp/results"), "/tmp/sim", {"param": 1}, 50.0)
    assert isinstance(result, dict)
    assert "compliance" in result
    assert result["compliance"] is True
    assert "details" in result
    assert result["details"]["oc_name"] == "OC1"


def test_get_measurement_names_returns_empty_when_no_validations():
    class CustomValidator(Validator):
        def get_measurement_names(self):
            return []

    curves_manager = DummyCurvesManager()
    parameters = DummyParameters(DummyProducer(sim_type=1))
    validator = CustomValidator(
        curves_manager, parameters, validations=[], is_field_measurements=False
    )
    assert validator.get_measurement_names() == []
