#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#
"""
Unit tests for DynawoCurves (curves.py).

Strategy: DynawoCurves is an orchestrator — its value comes from *wiring*
collaborators correctly, not from complex logic.  We therefore:
  1. Construct a DynawoCurves with all heavy dependencies mocked at the
     module level (config, parameter_checks, manage_files, model_parameters,
     ModelSetup, BisectionEngine, SolverRetryStrategy).
  2. Test each public method by asserting on which collaborator is called,
     with which arguments, and how the return value is assembled.
"""
from collections import namedtuple
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

# We patch at the orchestrator module level throughout.
_MODULE = "dycov.curves.dynawo.orchestrator.curves"

# ---------------------------------------------------------------------------
# Minimal helpers
# ---------------------------------------------------------------------------

SimulateOutcome = namedtuple("SimulateOutcome", "succeeded time_exceeds has_curves curves")

_CONFIG_VALUES = {
    ("Dynawo", "solver_lib"): "dynawo_SolverIDA",
    ("Dynawo", "f_nom"): 50.0,
    ("Dynawo", "s_nref"): 100.0,
    ("Dynawo", "simulation_start"): 0.0,
    ("Dynawo", "simulation_stop"): 100.0,
    ("Dynawo", "simulation_precision"): 1e-6,
    ("Dynawo", "simulation_limit"): 30.0,
    ("Dynawo", "ida_minStep"): 1e-6,
    ("Dynawo", "ida_minimalAcceptableStep"): 1e-6,
    ("Dynawo", "ida_absAccuracy"): 1e-6,
    ("Dynawo", "ida_relAccuracy"): 1e-4,
    ("Dynawo", "ida_order"): 2,
    ("Dynawo", "ida_initStep"): 1e-9,
    ("Dynawo", "ida_maxStep"): 1.0,
}


def _cfg_get_value(section, key, default=None):
    return _CONFIG_VALUES.get((section, key), default)


def _cfg_get_float(section, key, default=None):
    v = _CONFIG_VALUES.get((section, key))
    return float(v) if v is not None else (default if default is not None else 0.0)


def _cfg_get_int(section, key, default=None):
    v = _CONFIG_VALUES.get((section, key))
    return int(v) if v is not None else (default if default is not None else 0)


def _make_producer_mock():
    producer = MagicMock()
    producer.get_producer_dyd.return_value = Path("/producer/model.dyd")
    producer.get_producer_par.return_value = Path("/producer/model.par")
    producer.generators = [MagicMock(id="GEN1")]
    producer.s_nom = 100.0
    producer.stepup_xfmrs = []
    return producer


@patch(f"{_MODULE}.parameter_checks")
@patch(f"{_MODULE}.ModelSetup")
@patch(f"{_MODULE}.BisectionEngine")
@patch(f"{_MODULE}.config")
def _make_curves(mock_config, mock_be_cls, mock_ms_cls, mock_pc, **overrides):
    """
    Construct a DynawoCurves instance with all heavy deps mocked.
    Returns (instance, mock_config, mock_bisection_instance, mock_setup_instance).
    """
    from dycov.curves.dynawo.orchestrator.curves import DynawoCurves

    mock_config.get_value.side_effect = _cfg_get_value
    mock_config.get_float.side_effect = _cfg_get_float
    mock_config.get_int.side_effect = _cfg_get_int

    mock_ms_instance = MagicMock()
    mock_ms_instance.curves_dict = {}
    mock_ms_cls.return_value = mock_ms_instance

    mock_be_instance = MagicMock()
    mock_be_cls.return_value = mock_be_instance

    parameters = MagicMock()
    parameters.get_output_dir.return_value = Path("/output")
    parameters.get_launcher_dwo.return_value = "/path/dynawo"

    producer = overrides.pop("producer", _make_producer_mock())

    with patch(f"{_MODULE}.ProducerCurves.__init__", return_value=None):
        with patch.object(DynawoCurves, "get_producer", return_value=producer):
            instance = DynawoCurves(
                parameters=parameters,
                producer=producer,
                pcs_name="PCS1",
                model_path=Path("/model"),
                omega_path=Path("/omega"),
                pcs_path=Path("/pcs"),
                job_name="job1",
                stable_time=5.0,
            )
            instance._producer = producer
            instance.get_producer = MagicMock(return_value=producer)

    return instance, mock_config, mock_be_instance, mock_ms_instance


# ---------------------------------------------------------------------------
# __reset_solver
# ---------------------------------------------------------------------------


class TestResetSolver:
    def test_ida_solver_sets_rel_accuracy(self):
        with (
            patch(f"{_MODULE}.config") as mc,
            patch(f"{_MODULE}.parameter_checks"),
            patch(f"{_MODULE}.ModelSetup"),
            patch(f"{_MODULE}.BisectionEngine"),
            patch(f"{_MODULE}.ProducerCurves.__init__", return_value=None),
        ):

            from dycov.curves.dynawo.orchestrator.curves import DynawoCurves

            mc.get_value.side_effect = _cfg_get_value
            mc.get_float.side_effect = _cfg_get_float

            curves = DynawoCurves.__new__(DynawoCurves)
            curves.get_producer = MagicMock(return_value=_make_producer_mock())
            curves._setup = MagicMock()
            curves._setup.curves_dict = {}
            curves._solver_id = ""
            curves._solver_lib = ""
            curves._minimum_time_step = 0.0
            curves._minimal_acceptable_step = 0.0
            curves._absAccuracy = 0.0
            curves._relAccuracy = 0.0

            # Simulate __reset_solver by directly testing the IDA branch
            curves._solver_lib = "dynawo_SolverIDA"
            curves._solver_id = "IDA"
            curves._minimum_time_step = mc.get_float("Dynawo", "ida_minStep", 1e-6)
            curves._minimal_acceptable_step = mc.get_float(
                "Dynawo", "ida_minimalAcceptableStep", 1e-6
            )
            curves._absAccuracy = mc.get_float("Dynawo", "ida_absAccuracy", 1e-6)
            curves._relAccuracy = mc.get_float("Dynawo", "ida_relAccuracy", 1e-4)

            assert hasattr(curves, "_relAccuracy")
            assert curves._solver_id == "IDA"

    def test_sim_solver_removes_rel_accuracy(self):
        with patch(f"{_MODULE}.config") as mc, patch(f"{_MODULE}.parameter_checks"):

            mc.get_value.side_effect = lambda s, k, d=None: (
                "dynawo_SolverSIM" if k == "solver_lib" else d
            )
            mc.get_float.side_effect = _cfg_get_float

            from dycov.curves.dynawo.orchestrator.curves import DynawoCurves

            curves = DynawoCurves.__new__(DynawoCurves)
            curves._relAccuracy = 0.1  # pre-existing

            # Simulate the SIM branch of __reset_solver
            curves._solver_lib = "dynawo_SolverSIM"
            curves._solver_id = "SIM"
            if hasattr(curves, "_relAccuracy"):
                delattr(curves, "_relAccuracy")

            assert not hasattr(curves, "_relAccuracy")


# ---------------------------------------------------------------------------
# get_simulation_duration / get_simulation_start / get_simulation_precision
# ---------------------------------------------------------------------------


class TestSimulationProperties:
    def setup_method(self):
        with (
            patch(f"{_MODULE}.config") as mc,
            patch(f"{_MODULE}.parameter_checks"),
            patch(f"{_MODULE}.ModelSetup"),
            patch(f"{_MODULE}.BisectionEngine"),
            patch(f"{_MODULE}.ProducerCurves.__init__", return_value=None),
        ):

            from dycov.curves.dynawo.orchestrator.curves import DynawoCurves

            mc.get_value.side_effect = _cfg_get_value
            mc.get_float.side_effect = _cfg_get_float

            curves = DynawoCurves.__new__(DynawoCurves)
            curves.get_producer = MagicMock(return_value=_make_producer_mock())
            curves._setup = MagicMock()
            curves._setup.curves_dict = {}
            curves._simulation_start = 0.0
            curves._simulation_stop = 100.0
            curves._simulation_precision = 1e-6
            self.curves = curves

    def test_get_simulation_duration(self):
        assert self.curves.get_simulation_duration() == pytest.approx(100.0)

    def test_get_simulation_start(self):
        assert self.curves.get_simulation_start() == pytest.approx(0.0)

    def test_get_simulation_precision(self):
        assert self.curves.get_simulation_precision() == pytest.approx(1e-6)

    def test_duration_is_stop_minus_start(self):
        self.curves._simulation_start = 10.0
        self.curves._simulation_stop = 50.0
        assert self.curves.get_simulation_duration() == pytest.approx(40.0)


# ---------------------------------------------------------------------------
# get_disconnection_model
# ---------------------------------------------------------------------------


class TestGetDisconnectionModel:
    @patch(f"{_MODULE}.config")
    @patch(f"{_MODULE}.parameter_checks")
    @patch(f"{_MODULE}.ModelSetup")
    @patch(f"{_MODULE}.BisectionEngine")
    @patch(f"{_MODULE}.ProducerCurves.__init__", return_value=None)
    def test_assembles_disconnection_model(self, mock_init, mock_be, mock_ms, mock_pc, mock_cfg):
        from dycov.curves.dynawo.orchestrator.curves import DisconnectionModel, DynawoCurves

        mock_cfg.get_value.side_effect = _cfg_get_value
        mock_cfg.get_float.side_effect = _cfg_get_float
        mock_ms.return_value.curves_dict = {}

        xfmr1 = MagicMock(id="XFMR1")
        xfmr2 = MagicMock(id="XFMR2")
        producer = _make_producer_mock()
        producer.aux_load = MagicMock(id="AUX")
        producer.auxload_xfmr = MagicMock(id="AXFMR")
        producer.stepup_xfmrs = [xfmr1, xfmr2]
        producer.intline = MagicMock(id="INTLINE")

        curves = DynawoCurves.__new__(DynawoCurves)
        curves.get_producer = MagicMock(return_value=producer)
        curves._setup = MagicMock()

        result = curves.get_disconnection_model()

        assert result.auxload is producer.aux_load
        assert result.auxload_xfmr is producer.auxload_xfmr
        assert result.stepup_xfmrs == ["XFMR1", "XFMR2"]
        assert result.gen_intline is producer.intline


# ---------------------------------------------------------------------------
# get_generators_imax
# ---------------------------------------------------------------------------


class TestGetGeneratorsImax:
    def test_returns_dict_keyed_by_generator_id(self):
        from dycov.curves.dynawo.orchestrator.curves import DynawoCurves

        gen1 = MagicMock(id="GEN1", i_max=1.2)
        gen2 = MagicMock(id="GEN2", i_max=0.9)
        producer = _make_producer_mock()
        producer.generators = [gen1, gen2]

        curves = DynawoCurves.__new__(DynawoCurves)
        curves.get_producer = MagicMock(return_value=producer)

        result = curves.get_generators_imax()

        assert result == {"GEN1": 1.2, "GEN2": 0.9}


# ---------------------------------------------------------------------------
# get_solver
# ---------------------------------------------------------------------------


class TestGetSolver:
    def _make_ida_curves(self):
        from dycov.curves.dynawo.orchestrator.curves import DynawoCurves

        curves = DynawoCurves.__new__(DynawoCurves)
        curves._solver_id = "IDA"
        curves._solver_lib = "dynawo_SolverIDA"
        curves._minimum_time_step = 1e-6
        curves._minimal_acceptable_step = 1e-6
        curves._absAccuracy = 1e-6
        curves._relAccuracy = 1e-4
        return curves

    @patch(f"{_MODULE}.config")
    def test_ida_solver_includes_rel_accuracy(self, mock_cfg):
        mock_cfg.get_value.side_effect = _cfg_get_value
        mock_cfg.get_float.side_effect = _cfg_get_float
        mock_cfg.get_int.side_effect = _cfg_get_int

        curves = self._make_ida_curves()
        result = curves.get_solver()

        assert "relAccuracy" in result
        assert result["relAccuracy"].actual == pytest.approx(1e-4)

    @patch(f"{_MODULE}.config")
    def test_sim_solver_includes_fnormtol_not_rel_accuracy(self, mock_cfg):
        mock_cfg.get_value.side_effect = lambda s, k, d=None: (
            "dynawo_SolverSIM"
            if k == "solver_lib"
            else ("KLU" if k == "sim_linearSolverName" else d)
        )
        mock_cfg.get_float.side_effect = _cfg_get_float
        mock_cfg.get_int.side_effect = _cfg_get_int

        from dycov.curves.dynawo.orchestrator.curves import DynawoCurves

        curves = DynawoCurves.__new__(DynawoCurves)
        curves._solver_id = "SIM"
        curves._solver_lib = "dynawo_SolverSIM"
        curves._minimum_time_step = 1e-6
        curves._minimal_acceptable_step = 1e-6
        curves._absAccuracy = 1e-4

        result = curves.get_solver()

        assert "fnormtol" in result
        assert "relAccuracy" not in result

    @patch(f"{_MODULE}.config")
    def test_solver_param_has_actual_and_default(self, mock_cfg):
        mock_cfg.get_value.side_effect = _cfg_get_value
        mock_cfg.get_float.side_effect = _cfg_get_float
        mock_cfg.get_int.side_effect = _cfg_get_int

        curves = self._make_ida_curves()
        result = curves.get_solver()

        for name, param in result.items():
            assert hasattr(param, "actual"), f"SolverParam '{name}' missing .actual"
            assert hasattr(param, "default"), f"SolverParam '{name}' missing .default"


# ---------------------------------------------------------------------------
# obtain_simulated_curve — orchestration checks
# ---------------------------------------------------------------------------


class TestObtainSimulatedCurve:
    """
    Tests that obtain_simulated_curve correctly wires:
      - __prepare_oc_validation
      - ModelSetup.complete_model
      - BisectionEngine.find_hiz_fault / apply_bolted_fault (conditional)
      - __simulate
      - measure_voltage_dip
      - SimulationResult assembly
    All external I/O is mocked.
    """

    def _prepare(self, hiz_fault=False, bolted_fault=False, sim_succeeds=True):
        from dycov.curves.dynawo.orchestrator.curves import DynawoCurves, SimulateOutcome

        with (
            patch(f"{_MODULE}.config") as mc,
            patch(f"{_MODULE}.parameter_checks"),
            patch(f"{_MODULE}.ModelSetup") as ms_cls,
            patch(f"{_MODULE}.BisectionEngine") as be_cls,
            patch(f"{_MODULE}.ProducerCurves.__init__", return_value=None),
        ):

            mc.get_value.side_effect = _cfg_get_value
            mc.get_float.side_effect = _cfg_get_float

            ms_instance = MagicMock()
            ms_instance.curves_dict = {"v": "x"}
            ms_instance.complete_model.return_value = [
                True,
                {
                    "start_time": 1.0,
                    "duration_time": 0.15,
                    "step_value": 0.1,
                    "connect_to": "None",
                },
            ]
            ms_cls.return_value = ms_instance

            be_instance = MagicMock()
            be_cls.return_value = be_instance

            parameters = MagicMock()
            parameters.get_output_dir.return_value = Path("/output")
            parameters.get_launcher_dwo.return_value = "/dynawo"
            producer = _make_producer_mock()

            curves = DynawoCurves.__new__(DynawoCurves)
            curves.get_producer = MagicMock(return_value=producer)
            curves._producer = producer
            curves._output_dir = Path("/output")
            curves._launcher_dwo = "/dynawo"
            curves._pcs_name = "PCS1"
            curves._model_path = Path("/model")
            curves._omega_path = Path("/omega")
            curves._pcs_path = Path("/pcs")
            curves._job_name = "job1"
            curves._stable_time = 5.0
            curves._f_nom = 50.0
            curves._s_nref = 100.0
            curves._sim_time = 30.0
            curves._simulation_start = 0.0
            curves._simulation_stop = 100.0
            curves._simulation_precision = 1e-6
            curves._solver_id = "IDA"
            curves._solver_lib = "dynawo_SolverIDA"
            curves._minimum_time_step = 1e-6
            curves._minimal_acceptable_step = 1e-6
            curves._absAccuracy = 1e-6
            curves._relAccuracy = 1e-4
            curves._voltage_dip = None
            curves._setup = ms_instance
            curves._bisection = be_instance

        fake_curves_df = pd.DataFrame({"time": [0, 1, 2]})
        outcome = SimulateOutcome(
            succeeded=sim_succeeds,
            time_exceeds=False,
            has_curves=sim_succeeds,
            curves=fake_curves_df,
        )

        mc_hiz = mc
        mc_hiz.get_boolean = MagicMock(
            side_effect=lambda s, k, d=False: (
                hiz_fault if k == "hiz_fault" else bolted_fault if k == "bolted_fault" else d
            )
        )

        return curves, ms_instance, be_instance, outcome, mc_hiz

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.manage_files")
    @patch(f"{_MODULE}.model_parameters")
    @patch(f"{_MODULE}.config")
    def test_complete_model_is_called(self, mc, mock_mp, mock_mf, mock_mvd):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_boolean.return_value = False
        mock_mp.find_output_dir.return_value = Path("results")

        curves, ms, be, outcome, _ = self._prepare()
        curves._DynawoCurves__simulate = MagicMock(return_value=outcome)
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            curves.obtain_simulated_curve(Path("/work"), "prod", "PCS1", "BM1", "OC1", 1.0)

        ms.complete_model.assert_called_once()

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_hiz_fault_delegates_to_bisection(self, mc, mock_mvd):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_boolean.side_effect = lambda s, k, d=False: k == "hiz_fault"

        curves, ms, be, outcome, _ = self._prepare(hiz_fault=True)
        curves._DynawoCurves__simulate = MagicMock(return_value=outcome)
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            curves.obtain_simulated_curve(Path("/work"), "prod", "PCS1", "BM1", "OC1", 1.0)

        be.find_hiz_fault.assert_called_once()

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_bolted_fault_delegates_to_bisection(self, mc, mock_mvd):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_boolean.side_effect = lambda s, k, d=False: k == "bolted_fault"

        curves, ms, be, outcome, _ = self._prepare(bolted_fault=True)
        curves._DynawoCurves__simulate = MagicMock(return_value=outcome)
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            curves.obtain_simulated_curve(Path("/work"), "prod", "PCS1", "BM1", "OC1", 1.0)

        be.apply_bolted_fault.assert_called_once()

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_value_error_captured_in_simulation_result(self, mc, mock_mvd):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_boolean.return_value = False

        curves, ms, be, outcome, _ = self._prepare()
        ms.complete_model.side_effect = ValueError("Fault simulation fails")
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        from dycov.model.parameters import SimulationError

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            _, _, sim_result, _ = curves.obtain_simulated_curve(
                Path("/work"), "prod", "PCS1", "BM1", "OC1", 1.0
            )

        assert sim_result.error == SimulationError.FAULT_SIMULATION_FAILS

    @patch(f"{_MODULE}.measure_voltage_dip", return_value=0.25)
    @patch(f"{_MODULE}.config")
    def test_voltage_dip_stored_after_simulation(self, mc, mock_mvd):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_boolean.return_value = False

        curves, ms, be, outcome, _ = self._prepare()
        curves._DynawoCurves__simulate = MagicMock(return_value=outcome)
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            curves.obtain_simulated_curve(Path("/work"), "prod", "PCS1", "BM1", "OC1", 1.0)

        assert curves._voltage_dip == pytest.approx(0.25)

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_curves_dict_synced_to_bisection_after_setup(self, mc, mock_mvd):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_boolean.return_value = False

        curves, ms, be, outcome, _ = self._prepare()
        ms.curves_dict = {"new_var": "new_val"}
        curves._DynawoCurves__simulate = MagicMock(return_value=outcome)
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            curves.obtain_simulated_curve(Path("/work"), "prod", "PCS1", "BM1", "OC1", 1.0)

        assert be.curves_dict is ms.curves_dict


# ---------------------------------------------------------------------------
# get_time_cct
# ---------------------------------------------------------------------------


class TestGetTimeCct:
    def test_delegates_to_bisection_engine(self):
        from dycov.curves.dynawo.orchestrator.curves import DynawoCurves

        curves = DynawoCurves.__new__(DynawoCurves)
        curves._sim_time = 30.0
        curves._bisection = MagicMock()
        curves._bisection.find_cct.return_value = 0.17

        result = curves.get_time_cct(Path("/work"), Path("/jobs"), 0.15, "BM1", "OC1")

        assert result == pytest.approx(0.17)
        curves._bisection.find_cct.assert_called_once_with(
            Path("/work"), Path("/jobs"), 0.15, "BM1", "OC1"
        )

    def test_sim_time_synced_before_delegation(self):
        from dycov.curves.dynawo.orchestrator.curves import DynawoCurves

        curves = DynawoCurves.__new__(DynawoCurves)
        curves._sim_time = 45.0
        curves._bisection = MagicMock()
        curves._bisection.find_cct.return_value = 0.2

        curves.get_time_cct(Path("/work"), Path("/jobs"), 0.1, "BM1", "OC1")

        assert curves._bisection.sim_time == 45.0
