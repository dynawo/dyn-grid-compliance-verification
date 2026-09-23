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
     module level (config, parameter_checks, manage_files, simulation_files,
     ModelSetup, BisectionEngine, SolverRetryStrategy).
  2. Test each public method by asserting on which collaborator is called,
     with which arguments, and how the return value is assembled.
"""

from collections import namedtuple
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dycov.curves.dynawo.runtime.run_types import SolverParams
from dycov.files.simulation_files import SIMULATION_INPUTS_FILE
from dycov.model.parameters import PdrParams, SimulationError, SimulationOutcomeError

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
    producer.group_xfmrs = []
    return producer


# ---------------------------------------------------------------------------
# __reset_solver
# ---------------------------------------------------------------------------


class TestResetSolver:
    def test_ida_solver_sets_rel_accuracy(self):
        curves, _, _ = _make_real_curves()

        assert curves._solver.solver_id == "IDA"
        assert curves._solver.relAccuracy == pytest.approx(1e-4)

    def test_sim_solver_leaves_rel_accuracy_unset(self):
        curves, _, _ = _make_real_curves(solver_lib="dynawo_SolverSIM")

        assert curves._solver.solver_id == "SIM"
        assert curves._solver.relAccuracy is None

    def test_reset_discards_the_values_a_retry_left_behind(self):
        curves, _, _ = _make_real_curves()
        curves._solver.solver_id = "SIM"
        curves._solver.solver_lib = "dynawo_SolverSIM"
        curves._solver.minimum_time_step = 1e-9
        curves._solver.absAccuracy = 1e-3

        with patch(f"{_MODULE}.config") as mc, patch(f"{_MODULE}.parameter_checks"):
            mc.get_value.side_effect = _cfg_get_value
            mc.get_float.side_effect = _cfg_get_float
            curves._DynawoCurves__reset_solver()

        assert curves._solver.solver_id == "IDA"
        assert curves._solver.minimum_time_step == pytest.approx(1e-6)
        assert curves._solver.absAccuracy == pytest.approx(1e-6)


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
        from dycov.curves.dynawo.orchestrator.curves import DynawoCurves

        mock_cfg.get_value.side_effect = _cfg_get_value
        mock_cfg.get_float.side_effect = _cfg_get_float
        mock_ms.return_value.curves_dict = {}

        xfmr1 = MagicMock(id="XFMR1")
        xfmr2 = MagicMock(id="XFMR2")
        producer = _make_producer_mock()
        producer.aux_load = MagicMock(id="AUX")
        producer.auxload_xfmr = MagicMock(id="AXFMR")
        producer.group_xfmrs = [xfmr1, xfmr2]
        producer.main_xfmr = MagicMock(id="MAIN")
        producer.intline = MagicMock(id="INTLINE")

        curves = DynawoCurves.__new__(DynawoCurves)
        curves.get_producer = MagicMock(return_value=producer)
        curves._setup = MagicMock()

        result = curves.get_disconnection_model()

        assert result.auxload is producer.aux_load
        assert result.auxload_xfmr is producer.auxload_xfmr
        assert result.connection_xfmrs == ["XFMR1", "XFMR2", "MAIN"]
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
        curves._solver = SolverParams(
            solver_id="IDA",
            solver_lib="dynawo_SolverIDA",
            minimum_time_step=1e-6,
            minimal_acceptable_step=1e-6,
            absAccuracy=1e-6,
            relAccuracy=1e-4,
        )
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
        curves._solver = SolverParams(
            solver_id="SIM",
            solver_lib="dynawo_SolverSIM",
            minimum_time_step=1e-6,
            minimal_acceptable_step=1e-6,
            absAccuracy=1e-4,
            relAccuracy=None,
        )

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

    @patch(f"{_MODULE}.config")
    def test_reports_the_values_a_retry_left_behind(self, mock_cfg):
        mock_cfg.get_value.side_effect = _cfg_get_value
        mock_cfg.get_float.side_effect = _cfg_get_float
        mock_cfg.get_int.side_effect = _cfg_get_int

        curves = self._make_ida_curves()
        curves._solver.minimum_time_step = 1e-7
        curves._solver.absAccuracy = 1e-5

        result = curves.get_solver()

        assert result["minStep"].actual == pytest.approx(1e-7)
        assert result["minStep"].default == pytest.approx(1e-6)
        assert result["absAccuracy"].actual == pytest.approx(1e-5)
        assert result["absAccuracy"].default == pytest.approx(1e-6)

    @patch(f"{_MODULE}.config")
    def test_a_solver_no_retry_touched_declares_no_added_parameters(self, mock_cfg):
        mock_cfg.get_value.side_effect = _cfg_get_value
        mock_cfg.get_float.side_effect = _cfg_get_float
        mock_cfg.get_int.side_effect = _cfg_get_int

        result = self._make_ida_curves().get_solver()

        assert "mxiterAlg" not in result

    @patch(f"{_MODULE}.config")
    def test_reports_the_parameters_a_retry_added(self, mock_cfg):
        mock_cfg.get_value.side_effect = _cfg_get_value
        mock_cfg.get_float.side_effect = _cfg_get_float
        mock_cfg.get_int.side_effect = _cfg_get_int

        curves = self._make_ida_curves()
        curves._solver.added_parameters = {"mxiterAlg": "30"}

        result = curves.get_solver()

        assert result["mxiterAlg"].actual == "30"
        assert result["mxiterAlg"].default == "not set"

    @patch(f"{_MODULE}.config")
    def test_reports_the_solver_a_retry_flipped_to(self, mock_cfg):
        mock_cfg.get_value.side_effect = _cfg_get_value
        mock_cfg.get_float.side_effect = _cfg_get_float
        mock_cfg.get_int.side_effect = _cfg_get_int

        curves = self._make_ida_curves()
        curves._solver.solver_id = "SIM"
        curves._solver.solver_lib = "dynawo_SolverSIM"

        result = curves.get_solver()

        assert result["lib"].actual == "dynawo_SolverSIM"
        assert result["lib"].default == "dynawo_SolverIDA"
        assert "fnormtol" in result
        assert "minStep" not in result


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
            curves._thr_ss_tol = 5.0
            curves._f_nom = 50.0
            curves._s_nref = 100.0
            curves._sim_time = 30.0
            curves._simulation_start = 0.0
            curves._simulation_stop = 100.0
            curves._simulation_precision = 1e-6
            curves._solver = SolverParams(
                solver_id="IDA",
                solver_lib="dynawo_SolverIDA",
                minimum_time_step=1e-6,
                minimal_acceptable_step=1e-6,
                absAccuracy=1e-6,
                relAccuracy=1e-4,
            )
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
    @patch(f"{_MODULE}.simulation_files")
    @patch(f"{_MODULE}.config")
    def test_complete_model_is_called(self, mc, mock_sf, mock_mf, mock_mvd, tmp_path):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_boolean.return_value = False
        mock_sf.find_output_dir.return_value = Path("results")

        curves, ms, be, outcome, _ = self._prepare()
        curves._DynawoCurves__simulate = MagicMock(return_value=outcome)
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            curves.obtain_simulated_curve(tmp_path, "prod", "PCS1", "BM1", "OC1", 1.0)

        ms.complete_model.assert_called_once()

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_hiz_fault_delegates_to_bisection(self, mc, mock_mvd, tmp_path):
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
            curves.obtain_simulated_curve(tmp_path, "prod", "PCS1", "BM1", "OC1", 1.0)

        be.find_hiz_fault.assert_called_once()

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_bolted_fault_delegates_to_bisection(self, mc, mock_mvd, tmp_path):
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
            curves.obtain_simulated_curve(tmp_path, "prod", "PCS1", "BM1", "OC1", 1.0)

        be.find_bolted_fault.assert_called_once()

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_not_applicable_returns_without_simulating(self, mc, mock_mvd, tmp_path):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_boolean.return_value = False

        curves, ms, be, outcome, _ = self._prepare()
        ms.complete_model.return_value = (False, {"start_time": 1.0})
        curves._DynawoCurves__simulate = MagicMock(return_value=outcome)
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            _, _, result, curves_df = curves.obtain_simulated_curve(
                tmp_path, "prod", "PCS1", "BM1", "OC1", 1.0
            )

        assert result.appicable is False
        curves._DynawoCurves__simulate.assert_not_called()
        assert curves_df.empty

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_simulation_outcome_error_captured_in_simulation_result(self, mc, mock_mvd, tmp_path):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_boolean.return_value = False

        curves, ms, be, outcome, _ = self._prepare()
        ms.complete_model.side_effect = SimulationOutcomeError(
            "Fault simulation fails", SimulationError.FAULT_SIMULATION_FAILS
        )
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            _, _, sim_result, _ = curves.obtain_simulated_curve(
                tmp_path, "prod", "PCS1", "BM1", "OC1", 1.0
            )

        assert sim_result.error == SimulationError.FAULT_SIMULATION_FAILS

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_rejected_value_definition_aborts_the_run(self, mc, mock_mvd, tmp_path):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_boolean.return_value = False

        curves, ms, be, outcome, _ = self._prepare()
        ms.complete_model.side_effect = ValueError(
            "Unknown magnitude 'Pnom' in value definition '0.5*Pnom'."
        )
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            with pytest.raises(ValueError, match="Unknown magnitude 'Pnom'"):
                curves.obtain_simulated_curve(tmp_path, "prod", "PCS1", "BM1", "OC1", 1.0)

    @patch(f"{_MODULE}.measure_voltage_dip", return_value=0.25)
    @patch(f"{_MODULE}.config")
    def test_voltage_dip_stored_after_simulation(self, mc, mock_mvd, tmp_path):
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
            curves.obtain_simulated_curve(tmp_path, "prod", "PCS1", "BM1", "OC1", 1.0)

        assert curves._voltage_dip == pytest.approx(0.25)

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_curves_dict_synced_to_bisection_after_setup(self, mc, mock_mvd, tmp_path):
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
            curves.obtain_simulated_curve(tmp_path, "prod", "PCS1", "BM1", "OC1", 1.0)

        assert be.curves_dict is ms.curves_dict

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_simulation_record_carries_the_curves_metadata(self, mc, mock_mvd, tmp_path):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_int.side_effect = _cfg_get_int
        mc.get_boolean.return_value = False

        curves, ms, be, outcome, _ = self._prepare()
        curves._DynawoCurves__simulate = MagicMock(return_value=outcome)
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            curves.obtain_simulated_curve(tmp_path, "prod", "PCS1", "BM1", "OC1", 1.0)

        record = (tmp_path / SIMULATION_INPUTS_FILE).read_text()
        assert "sim_t_event_start = 1.0" in record
        assert "fault_duration = 0.15" in record
        assert "frequency_sampling = 15.0" in record

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_simulation_record_carries_the_solver_the_run_used(self, mc, mock_mvd, tmp_path):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_int.side_effect = _cfg_get_int
        mc.get_boolean.return_value = False

        curves, ms, be, outcome, _ = self._prepare()
        curves._solver.minimum_time_step = 1e-4
        curves._DynawoCurves__simulate = MagicMock(return_value=outcome)
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            curves.obtain_simulated_curve(tmp_path, "prod", "PCS1", "BM1", "OC1", 1.0)

        record = (tmp_path / SIMULATION_INPUTS_FILE).read_text()
        assert "solver_lib = dynawo_SolverIDA" in record
        assert "solver_minStep = 0.0001" in record
        assert "simulation_stop = 100.0" in record

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_simulation_record_carries_the_operating_point(self, mc, mock_mvd, tmp_path):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_int.side_effect = _cfg_get_int
        mc.get_boolean.return_value = False

        curves, ms, be, outcome, _ = self._prepare()
        ms.pdr = PdrParams(u=1.05, u_phase=0.1, s=complex(0.8, 0.2), p=0.8, q=0.2)
        curves._producer.get_zone.return_value = 3
        curves._DynawoCurves__simulate = MagicMock(return_value=outcome)
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            curves.obtain_simulated_curve(tmp_path, "prod", "PCS1", "BM1", "OC1", 1.0)

        record = (tmp_path / SIMULATION_INPUTS_FILE).read_text()
        assert "init_BusPDR_BUS_Voltage = 1.05" in record
        assert "init_BusPDR_BUS_ActivePower = 0.8" in record
        assert "init_BusPDR_BUS_ReactivePower = 0.2" in record

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_simulation_record_names_the_operating_point_for_its_zone(
        self, mc, mock_mvd, tmp_path
    ):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_int.side_effect = _cfg_get_int
        mc.get_boolean.return_value = False

        curves, ms, be, outcome, _ = self._prepare()
        ms.pdr = PdrParams(u=1.05, u_phase=0.1, s=complex(0.8, 0.2), p=0.8, q=0.2)
        curves._producer.get_zone.return_value = 1
        curves._DynawoCurves__simulate = MagicMock(return_value=outcome)
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            curves.obtain_simulated_curve(tmp_path, "prod", "PCS1", "BM1", "OC1", 1.0)

        record = (tmp_path / SIMULATION_INPUTS_FILE).read_text()
        assert "init_InternalNode1_BUS_Voltage = 1.05" in record
        assert "init_BusPDR_BUS_Voltage" not in record

    @patch(f"{_MODULE}.measure_voltage_dip")
    @patch(f"{_MODULE}.config")
    def test_no_simulation_record_when_the_test_does_not_apply(self, mc, mock_mvd, tmp_path):
        mc.get_value.side_effect = _cfg_get_value
        mc.get_float.side_effect = _cfg_get_float
        mc.get_boolean.return_value = False

        curves, ms, be, outcome, _ = self._prepare()
        ms.complete_model.return_value = [False, {}]
        curves._DynawoCurves__prepare_oc_validation = MagicMock(
            return_value=(Path("/out"), Path("/jobs"))
        )
        curves._DynawoCurves__reset_solver = MagicMock()

        with patch(f"{_MODULE}.get_cfg_oc_name", return_value="PCS1.BM1.OC1"):
            curves.obtain_simulated_curve(tmp_path, "prod", "PCS1", "BM1", "OC1", 1.0)

        assert not (tmp_path / SIMULATION_INPUTS_FILE).exists()


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


# ---------------------------------------------------------------------------
# Real __init__ / __reset_solver / __prepare_oc_validation / __simulate
# ---------------------------------------------------------------------------


def _make_real_curves(solver_lib="dynawo_SolverIDA"):
    """Construct a DynawoCurves running its real __init__, with heavy deps mocked."""
    from dycov.curves.dynawo.orchestrator.curves import DynawoCurves

    cfg_values = dict(_CONFIG_VALUES)
    cfg_values[("Dynawo", "solver_lib")] = solver_lib

    def get_value(section, key, default=None):
        return cfg_values.get((section, key), default)

    def get_float(section, key, default=None):
        v = cfg_values.get((section, key))
        return float(v) if v is not None else (default if default is not None else 0.0)

    producer = _make_producer_mock()
    with (
        patch(f"{_MODULE}.config") as mc,
        patch(f"{_MODULE}.parameter_checks"),
        patch(f"{_MODULE}.ModelSetup") as ms_cls,
        patch(f"{_MODULE}.BisectionEngine") as be_cls,
        patch(f"{_MODULE}.ProducerCurves.__init__", return_value=None),
        patch.object(DynawoCurves, "get_producer", return_value=producer),
        patch.object(DynawoCurves, "get_snref", return_value=100.0),
    ):
        mc.get_value.side_effect = get_value
        mc.get_float.side_effect = get_float

        parameters = MagicMock()
        parameters.get_output_dir.return_value = Path("/output")
        parameters.get_launcher_dwo.return_value = "/dynawo"

        instance = DynawoCurves(
            parameters=parameters,
            producer=producer,
            pcs_name="PCS1",
            model_path=Path("/model"),
            omega_path=Path("/omega"),
            pcs_path=Path("/pcs"),
            job_name="job1",
            thr_ss_tol=5.0,
        )

    instance.get_producer = MagicMock(return_value=producer)
    instance.get_snref = MagicMock(return_value=100.0)
    return instance, ms_cls.return_value, be_cls.return_value


class TestConstructorWiring:
    def test_init_wires_ida_solver_and_collaborators(self):
        curves, ms, be = _make_real_curves()

        assert curves._solver.solver_id == "IDA"
        assert curves._solver.relAccuracy == pytest.approx(1e-4)
        assert curves._solver.minimum_time_step == pytest.approx(1e-6)
        assert curves._setup is ms
        assert curves._bisection is be
        assert curves._voltage_dip is None

    def test_init_sim_solver_leaves_rel_accuracy_unset(self):
        curves, _, _ = _make_real_curves(solver_lib="dynawo_SolverSIM")

        assert curves._solver.solver_id == "SIM"
        assert curves._solver.relAccuracy is None
        assert curves._solver.absAccuracy == pytest.approx(1e-4)

    def test_get_voltage_dip_returns_none_before_simulation(self):
        curves, _, _ = _make_real_curves()
        assert curves.get_voltage_dip() is None

    def test_obtain_gen_value_maps_sign_conventions(self):
        curves, _, _ = _make_real_curves()
        gen = MagicMock(p0=-0.5, q0=0.1, u0=1.02)

        assert curves._obtain_gen_value(gen, "P0") == pytest.approx(0.5)
        assert curves._obtain_gen_value(gen, "Q0") == pytest.approx(-0.1)
        assert curves._obtain_gen_value(gen, "U0") == pytest.approx(1.02)
        assert curves._obtain_gen_value(gen, "AnythingElse") == 0.0


class TestPrepareOcValidation:
    @patch(f"{_MODULE}.simulation_files")
    @patch(f"{_MODULE}.manage_files")
    def test_copies_base_case_and_resolves_output_dirs(self, mock_mf, mock_sf):
        curves, _, _ = _make_real_curves()
        mock_sf.find_output_dir.return_value = Path("outputs")

        output_dir, jobs_output_dir = curves._DynawoCurves__prepare_oc_validation(
            Path("/work"), "PCS1", "BM1", "OC1"
        )

        mock_mf.copy_base_case_files.assert_called_once()
        assert jobs_output_dir == Path("outputs")
        assert output_dir == Path("/output") / "PCS1" / "BM1" / "OC1"


class TestSimulateOutcomeAssembly:
    def _simulate(self, curves, result, working_dir=Path("/work")):
        with (
            patch(f"{_MODULE}.SolverRetryStrategy") as strat_cls,
            patch(f"{_MODULE}.RetrySettings"),
            patch(f"{_MODULE}.config") as mc,
        ):
            mc.get_float.side_effect = _cfg_get_float
            strat_cls.return_value.run.return_value = result
            outcome = curves._DynawoCurves__simulate(
                Path("/out"), working_dir, Path("outputs"), "BM1", "OC1"
            )
        return outcome

    def test_success_outcome_within_time(self):
        curves, _, _ = _make_real_curves()
        result = MagicMock(succeeded=True, sim_time=10.0, curves=pd.DataFrame(), log="")

        outcome = self._simulate(curves, result)

        assert outcome.succeeded is True
        assert outcome.time_exceeds is False
        assert outcome.has_curves is False

    def test_a_retry_mutation_reaches_the_solver_the_report_reads(self):
        curves, _, _ = _make_real_curves()

        def run(**kwargs):
            kwargs["solver"].minimum_time_step = 1e-9
            return MagicMock(succeeded=True, sim_time=1.0, curves=pd.DataFrame(), log="")

        with (
            patch(f"{_MODULE}.SolverRetryStrategy") as strat_cls,
            patch(f"{_MODULE}.RetrySettings"),
            patch(f"{_MODULE}.config") as mc,
        ):
            mc.get_value.side_effect = _cfg_get_value
            mc.get_float.side_effect = _cfg_get_float
            mc.get_int.side_effect = _cfg_get_int
            strat_cls.return_value.run.side_effect = run

            curves._DynawoCurves__simulate(
                Path("/out"), Path("/work"), Path("outputs"), "BM1", "OC1"
            )
            reported = curves.get_solver()

        assert reported["minStep"].actual == pytest.approx(1e-9)
        assert reported["minStep"].default == pytest.approx(1e-6)

    def test_failure_outcome_exceeding_time(self):
        curves, _, _ = _make_real_curves()
        result = MagicMock(succeeded=False, sim_time=50.0, curves=pd.DataFrame(), log="boom")

        outcome = self._simulate(curves, result)

        assert outcome.succeeded is False
        assert outcome.time_exceeds is True
        assert outcome.has_curves is False

    def test_has_curves_when_csv_exists(self, tmp_path):
        curves, _, _ = _make_real_curves()
        csv_dir = tmp_path / "outputs" / "curves"
        csv_dir.mkdir(parents=True)
        (csv_dir / "curves.csv").write_text("time;\n")
        result = MagicMock(succeeded=True, sim_time=1.0, curves=pd.DataFrame(), log="")

        outcome = self._simulate(curves, result, working_dir=tmp_path)

        assert outcome.has_curves is True
