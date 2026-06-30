#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#
import math
from collections import namedtuple
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

from dycov.curves.dynawo.orchestrator.bisection import (
    BISECTION_ROUND,
    BOLTED_FAULT_XPU,
    CCT_REL_TOL,
    BisectionEngine,
)
from dycov.curves.voltage_dip import VoltDipResult

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SimulateOutcome = namedtuple("SimulateOutcome", "succeeded time_exceeds has_curves curves")


def _make_engine(**overrides) -> BisectionEngine:
    """Return a BisectionEngine with sensible defaults, overrideable per-test."""
    producer = MagicMock()
    producer.get_zone.return_value = 1
    producer.generators = [MagicMock(id="GEN1", lib="GenLib")]
    producer.s_nom = 100.0

    defaults = dict(
        pcs_name="PCS1",
        launcher_dwo="/path/to/dynawo",
        producer=producer,
        s_nref=100.0,
        f_nom=50.0,
        sim_time=30.0,
        thr_ss_tol=10.0,
        curves_dict={"var1": "GEN1_var1"},
    )
    defaults.update(overrides)
    return BisectionEngine(**defaults)


def _succeed_outcome(curves: pd.DataFrame | None = None) -> SimulateOutcome:
    return SimulateOutcome(
        succeeded=True,
        time_exceeds=False,
        has_curves=True,
        curves=curves if curves is not None else pd.DataFrame(),
    )


def _fail_outcome() -> SimulateOutcome:
    return SimulateOutcome(
        succeeded=False, time_exceeds=False, has_curves=False, curves=pd.DataFrame()
    )


# ---------------------------------------------------------------------------
# _fault_rpu_from_xpu
# ---------------------------------------------------------------------------


class TestFaultRpuFromXpu:
    def test_normal_division(self):
        assert BisectionEngine._fault_rpu_from_xpu(1.0, 10.0) == pytest.approx(0.1)

    def test_zero_r_factor_returns_zero(self):
        assert BisectionEngine._fault_rpu_from_xpu(5.0, 0.0) == 0.0

    def test_zero_xpu(self):
        assert BisectionEngine._fault_rpu_from_xpu(0.0, 10.0) == 0.0

    def test_large_r_factor(self):
        assert BisectionEngine._fault_rpu_from_xpu(1.0, 1e6) == pytest.approx(1e-6)


# ---------------------------------------------------------------------------
# _is_bisection_complete
# ---------------------------------------------------------------------------


class TestIsBisectionComplete:
    def setup_method(self):
        self.engine = _make_engine()

    def test_identical_values_complete(self):
        assert self.engine._is_bisection_complete(1.0, 1.0, 1e-4, "BM", "OC") is True

    def test_far_apart_not_complete(self):
        assert self.engine._is_bisection_complete(2.0, 1.0, 1e-4, "BM", "OC") is False

    def test_within_tolerance_complete(self):
        # 1.00001 vs 1.0 — rel diff ~1e-5, tolerance 1e-4 → complete
        assert self.engine._is_bisection_complete(1.00001, 1.0, 1e-4, "BM", "OC") is True

    def test_just_outside_tolerance_not_complete(self):
        # 1.01 vs 1.0 — rel diff ~1e-2, tolerance 1e-4 → not complete
        assert self.engine._is_bisection_complete(1.01, 1.0, 1e-4, "BM", "OC") is False

    def test_uses_math_isclose(self):
        # Symmetry: math.isclose is symmetric
        engine = self.engine
        a, b, tol = 1.0001, 1.0, 1e-3
        assert engine._is_bisection_complete(a, b, tol, "BM", "OC") == math.isclose(
            a, b, rel_tol=tol
        )


# ---------------------------------------------------------------------------
# _modify_fault
# ---------------------------------------------------------------------------


class TestModifyFault:
    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    def test_zone1_calls_fault_par_file(self, mock_rp):
        engine = _make_engine()
        engine._producer.get_zone.return_value = 1
        engine._modify_fault(Path("/work"), 1.0, 0.15, 0.5, 0.05)
        mock_rp.fault_par_file.assert_called_once_with(
            Path("/work"),
            "TSOModel.par",
            1.15,  # fault_start + fault_duration
            0.5,
            0.05,
        )

    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    def test_non_zone1_is_noop(self, mock_rp):
        engine = _make_engine()
        engine._producer.get_zone.return_value = 2
        engine._modify_fault(Path("/work"), 1.0, 0.15, 0.5, 0.05)
        mock_rp.fault_par_file.assert_not_called()

    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    def test_fault_end_time_is_start_plus_duration(self, mock_rp):
        engine = _make_engine()
        engine._modify_fault(Path("/work"), 2.5, 0.3, 0.1, 0.01)
        _, args, _ = mock_rp.fault_par_file.mock_calls[0]
        fault_end = args[2]
        assert fault_end == pytest.approx(2.8)


# ---------------------------------------------------------------------------
# apply_bolted_fault
# ---------------------------------------------------------------------------


class TestApplyBoltedFault:
    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_uses_bolted_fault_xpu_constant(self, mock_config, mock_rp):
        mock_config.get_float.return_value = 10.0  # fault_r_factor
        engine = _make_engine()
        engine.apply_bolted_fault(Path("/work"), 1.0, 0.1)
        _, args, _ = mock_rp.fault_par_file.mock_calls[0]
        fault_xpu = args[3]
        assert fault_xpu == BOLTED_FAULT_XPU

    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_rpu_derived_from_r_factor(self, mock_config, mock_rp):
        mock_config.get_float.return_value = 10.0
        engine = _make_engine()
        engine.apply_bolted_fault(Path("/work"), 1.0, 0.1)
        _, args, _ = mock_rp.fault_par_file.mock_calls[0]
        fault_xpu, fault_rpu = args[3], args[4]
        assert fault_rpu == pytest.approx(fault_xpu / 10.0)


# ---------------------------------------------------------------------------
# find_hiz_fault — logic flow
# ---------------------------------------------------------------------------


class TestFindHizFault:
    """Tests for the HIZ bisection control flow, with all I/O mocked."""

    def _engine_with_config(self, config_mock):
        config_mock.get_float.side_effect = lambda section, key, default=None: {
            ("GridCode", "fault_r_factor"): 10.0,
            ("Global", "maximum_hiz_fault"): 10.0,
            ("Global", "minimum_hiz_fault"): 1e-10,
            ("Global", "hiz_fault_rel_tol"): 1e-5,
        }.get((section, key), default)
        return _make_engine()

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_voltage_dip")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_raises_when_all_simulations_fail(self, mock_config, mock_mf, mock_cvd):
        engine = self._engine_with_config(mock_config)
        simulate_fn = MagicMock(return_value=_fail_outcome())
        reset_fn = MagicMock()

        with patch.object(engine, "_modify_fault"):
            with patch.object(engine, "_isolated_copy") as mock_iso:
                mock_iso.return_value.__enter__ = MagicMock(return_value=Path("/tmp/work"))
                mock_iso.return_value.__exit__ = MagicMock(return_value=False)
                # Make bisection converge immediately
                with patch.object(engine, "_is_bisection_complete", return_value=True):
                    with pytest.raises(ValueError, match="Fault simulation fails"):
                        engine.find_hiz_fault(
                            Path("/out"),
                            Path("/work"),
                            Path("/jobs"),
                            1.0,
                            0.15,
                            0.2,
                            "BM",
                            "OC",
                            simulate_fn,
                            reset_fn,
                        )

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_voltage_dip")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_raises_when_dip_unachievable(self, mock_config, mock_mf, mock_cvd):
        engine = self._engine_with_config(mock_config)
        mock_cvd.return_value = VoltDipResult.DIP_TOO_LARGE
        simulate_fn = MagicMock(return_value=_succeed_outcome())
        reset_fn = MagicMock()

        with patch.object(engine, "_modify_fault"):
            with patch.object(engine, "_isolated_copy") as mock_iso:
                mock_iso.return_value.__enter__ = MagicMock(return_value=Path("/tmp/work"))
                mock_iso.return_value.__exit__ = MagicMock(return_value=False)
                with patch.object(engine, "_is_bisection_complete", return_value=True):
                    with pytest.raises(ValueError, match="Fault dip unachievable"):
                        engine.find_hiz_fault(
                            Path("/out"),
                            Path("/work"),
                            Path("/jobs"),
                            1.0,
                            0.15,
                            0.2,
                            "BM",
                            "OC",
                            simulate_fn,
                            reset_fn,
                        )

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_voltage_dip")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_succeeds_and_applies_fault_to_original_dir(
        self, mock_config, mock_rp, mock_mf, mock_cvd
    ):
        engine = self._engine_with_config(mock_config)
        mock_cvd.return_value = VoltDipResult.DIP_CORRECT
        simulate_fn = MagicMock(return_value=_succeed_outcome())
        reset_fn = MagicMock()

        with patch.object(engine, "_isolated_copy") as mock_iso:
            mock_iso.return_value.__enter__ = MagicMock(return_value=Path("/tmp/work"))
            mock_iso.return_value.__exit__ = MagicMock(return_value=False)
            # One iteration, then converge
            call_count = 0

            def converge_after_one(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                return call_count >= 1

            with patch.object(engine, "_is_bisection_complete", side_effect=converge_after_one):
                engine.find_hiz_fault(
                    Path("/out"),
                    Path("/work"),
                    Path("/jobs"),
                    1.0,
                    0.15,
                    0.2,
                    "BM",
                    "OC",
                    simulate_fn,
                    reset_fn,
                )
        # _modify_fault must be called on the original working_oc_dir at the end
        final_call_args = mock_rp.fault_par_file.call_args_list[-1]
        assert final_call_args[0][0] == Path("/work")

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_voltage_dip")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_reset_solver_called_after_each_simulation(self, mock_config, mock_mf, mock_cvd):
        engine = self._engine_with_config(mock_config)
        mock_cvd.return_value = VoltDipResult.DIP_CORRECT
        simulate_fn = MagicMock(return_value=_succeed_outcome())
        reset_fn = MagicMock()

        with patch.object(engine, "_isolated_copy") as mock_iso:
            mock_iso.return_value.__enter__ = MagicMock(return_value=Path("/tmp/work"))
            mock_iso.return_value.__exit__ = MagicMock(return_value=False)
            with patch.object(engine, "_is_bisection_complete", return_value=True):
                with patch.object(engine, "_modify_fault"):
                    engine.find_hiz_fault(
                        Path("/out"),
                        Path("/work"),
                        Path("/jobs"),
                        1.0,
                        0.15,
                        0.2,
                        "BM",
                        "OC",
                        simulate_fn,
                        reset_fn,
                    )
        assert reset_fn.call_count == simulate_fn.call_count

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_voltage_dip")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_dip_too_large_narrows_from_below(self, mock_config, mock_mf, mock_cvd):
        """DIP_TOO_LARGE (fault too strong) → min_val = fault_xpu → next midpoint is higher."""
        engine = self._engine_with_config(mock_config)
        iterations = [VoltDipResult.DIP_TOO_LARGE, VoltDipResult.DIP_CORRECT]
        mock_cvd.side_effect = iterations
        simulate_fn = MagicMock(return_value=_succeed_outcome())
        reset_fn = MagicMock()

        with patch.object(engine, "_isolated_copy") as mock_iso:
            mock_iso.return_value.__enter__ = MagicMock(return_value=Path("/tmp/work"))
            mock_iso.return_value.__exit__ = MagicMock(return_value=False)
            converge_calls = 0

            def converge_on_second(*args, **kwargs):
                nonlocal converge_calls
                converge_calls += 1
                return converge_calls >= 2

            with patch.object(engine, "_is_bisection_complete", side_effect=converge_on_second):
                with patch.object(engine, "_modify_fault"):
                    engine.find_hiz_fault(
                        Path("/out"),
                        Path("/work"),
                        Path("/jobs"),
                        1.0,
                        0.15,
                        0.2,
                        "BM",
                        "OC",
                        simulate_fn,
                        reset_fn,
                    )
        assert simulate_fn.call_count == 2

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_voltage_dip")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_raises_when_column_missing(self, mock_config, mock_mf, mock_cvd):
        engine = self._engine_with_config(mock_config)
        mock_cvd.return_value = VoltDipResult.COLUMN_MISSING
        simulate_fn = MagicMock(return_value=_succeed_outcome())
        reset_fn = MagicMock()

        with patch.object(engine, "_isolated_copy") as mock_iso:
            mock_iso.return_value.__enter__ = MagicMock(return_value=Path("/tmp/work"))
            mock_iso.return_value.__exit__ = MagicMock(return_value=False)
            with patch.object(engine, "_is_bisection_complete", return_value=True):
                with patch.object(engine, "_modify_fault"):
                    with pytest.raises(ValueError, match="Voltage curve missing"):
                        engine.find_hiz_fault(
                            Path("/out"),
                            Path("/work"),
                            Path("/jobs"),
                            1.0,
                            0.15,
                            0.2,
                            "BM",
                            "OC",
                            simulate_fn,
                            reset_fn,
                        )


# ---------------------------------------------------------------------------
# _run_time_cct
# ---------------------------------------------------------------------------


class TestRunTimeCct:
    def _engine(self):
        engine = _make_engine(thr_ss_tol=5.0)
        engine._producer.generators = [
            MagicMock(id="GEN1", lib="GenLib"),
            MagicMock(id="GEN2", lib="GenLib"),
        ]
        return engine

    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.DynawoSimulator")
    def test_returns_false_when_simulator_fails(self, mock_sim, mock_rp):
        engine = self._engine()
        mock_sim.run_simple.return_value = MagicMock(succeeded=False)
        result = engine._run_time_cct(Path("/work"), Path("/jobs"), 0.2, "BM", "OC")
        assert result is False

    @patch("dycov.curves.dynawo.orchestrator.bisection.common")
    @patch("dycov.curves.dynawo.orchestrator.bisection.dynawo_translator")
    @patch("dycov.curves.dynawo.orchestrator.bisection.pd")
    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.DynawoSimulator")
    def test_returns_true_when_all_generators_stable(
        self, mock_sim, mock_rp, mock_pd, mock_trans, mock_common
    ):
        engine = self._engine()
        mock_sim.run_simple.return_value = MagicMock(succeeded=True)
        mock_trans.get_curve_variable.side_effect = lambda gen_id, lib, var: f"{gen_id}_{var}"
        fake_curves = MagicMock()
        mock_pd.read_csv.return_value = fake_curves
        mock_common.is_stable.return_value = (True, None)

        result = engine._run_time_cct(Path("/work"), Path("/jobs"), 0.2, "BM", "OC")
        assert result is True

    @patch("dycov.curves.dynawo.orchestrator.bisection.common")
    @patch("dycov.curves.dynawo.orchestrator.bisection.dynawo_translator")
    @patch("dycov.curves.dynawo.orchestrator.bisection.pd")
    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.DynawoSimulator")
    def test_returns_false_when_any_generator_unstable(
        self, mock_sim, mock_rp, mock_pd, mock_trans, mock_common
    ):
        engine = self._engine()
        mock_sim.run_simple.return_value = MagicMock(succeeded=True)
        mock_trans.get_curve_variable.side_effect = lambda gen_id, lib, var: f"{gen_id}_{var}"
        mock_pd.read_csv.return_value = MagicMock()
        # GEN1 stable, GEN2 unstable
        mock_common.is_stable.side_effect = [(True, None), (False, None)]

        result = engine._run_time_cct(Path("/work"), Path("/jobs"), 0.2, "BM", "OC")
        assert result is False

    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.DynawoSimulator")
    def test_fault_time_written_before_simulation(self, mock_sim, mock_rp):
        engine = self._engine()
        call_order = []
        mock_rp.fault_time.side_effect = lambda *a, **kw: call_order.append("fault_time")
        mock_sim.run_simple.side_effect = lambda *a, **kw: (
            call_order.append("run_simple"),
            MagicMock(succeeded=False),
        )[-1]

        engine._run_time_cct(Path("/work"), Path("/jobs"), 0.2, "BM", "OC")
        assert call_order.index("fault_time") < call_order.index("run_simple")

    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.DynawoSimulator")
    def test_simulation_limit_is_sim_time_plus_10(self, mock_sim, mock_rp):
        engine = self._engine()
        engine.sim_time = 30.0
        mock_sim.run_simple.return_value = MagicMock(succeeded=False)

        engine._run_time_cct(Path("/work"), Path("/jobs"), 0.2, "BM", "OC")
        _, kwargs = mock_sim.run_simple.call_args
        assert kwargs.get("simulation_limit", mock_sim.run_simple.call_args[0][-1]) == 40.0


# ---------------------------------------------------------------------------
# _find_max_duration
# ---------------------------------------------------------------------------


class TestFindMaxDuration:
    def test_doubles_until_unstable(self):
        engine = _make_engine()
        # Stable on first two calls, unstable on third
        engine._run_time_cct = MagicMock(side_effect=[True, True, False])

        min_val, max_val = engine._find_max_duration(Path("/work"), Path("/jobs"), 0.1, "BM", "OC")

        assert engine._run_time_cct.call_count == 3
        # starts at 0.2, grows to 0.3, then 0.45 (unstable)
        assert min_val == pytest.approx(0.3)
        assert max_val == pytest.approx(0.45)

    def test_immediately_unstable(self):
        engine = _make_engine()
        engine._run_time_cct = MagicMock(return_value=False)

        min_val, max_val = engine._find_max_duration(Path("/work"), Path("/jobs"), 0.1, "BM", "OC")

        engine._run_time_cct.assert_called_once()
        assert min_val == pytest.approx(0.1)
        assert max_val == pytest.approx(0.2)

    def test_initial_max_val_is_double_fault_duration(self):
        engine = _make_engine()
        calls = []

        def capture_and_fail(work_dir, jobs_dir, duration, bm, oc):
            calls.append(duration)
            return False

        engine._run_time_cct = MagicMock(side_effect=capture_and_fail)
        engine._find_max_duration(Path("/work"), Path("/jobs"), 0.5, "BM", "OC")

        assert calls[0] == pytest.approx(1.0)  # 0.5 * 2


# ---------------------------------------------------------------------------
# find_cct — integration of bisection loop
# ---------------------------------------------------------------------------


class TestFindCct:
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    def test_returns_midpoint_when_converged(self, mock_mf):
        engine = _make_engine()
        mock_mf.clone_as_subdirectory.return_value = Path("/work/max")

        # _find_max_duration returns a tight interval
        engine._find_max_duration = MagicMock(return_value=(0.149, 0.151))
        # First bisection step: stable at midpoint, then converge
        run_calls = [True]
        engine._run_time_cct = MagicMock(side_effect=run_calls)

        with patch.object(engine, "_isolated_copy") as mock_iso:
            mock_iso.return_value.__enter__ = MagicMock(return_value=Path("/tmp/work"))
            mock_iso.return_value.__exit__ = MagicMock(return_value=False)
            with patch.object(engine, "_is_bisection_complete", return_value=True):
                result = engine.find_cct(Path("/work"), Path("/jobs"), 0.149, "BM", "OC")

        expected = round((0.15 + 0.151) / 2, BISECTION_ROUND)
        assert result == pytest.approx(expected)

    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    def test_stable_result_raises_min_val(self, mock_mf):
        """When a CCT attempt is stable, min_val must move up."""
        engine = _make_engine()
        mock_mf.clone_as_subdirectory.return_value = Path("/work/max")
        engine._find_max_duration = MagicMock(return_value=(0.1, 0.2))

        intervals = []

        def capture_bisection(max_v, min_v, tol, bm, oc):
            intervals.append((min_v, max_v))
            return len(intervals) >= 2

        engine._run_time_cct = MagicMock(return_value=True)

        with patch.object(engine, "_isolated_copy") as mock_iso:
            mock_iso.return_value.__enter__ = MagicMock(return_value=Path("/tmp/work"))
            mock_iso.return_value.__exit__ = MagicMock(return_value=False)
            with patch.object(engine, "_is_bisection_complete", side_effect=capture_bisection):
                engine.find_cct(Path("/work"), Path("/jobs"), 0.1, "BM", "OC")

        # After first stable step, min_val should have moved from 0.1 to 0.15
        first_min, _ = intervals[0]
        assert first_min == pytest.approx(0.15)

    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    def test_unstable_result_lowers_max_val(self, mock_mf):
        """When a CCT attempt is unstable, max_val must move down."""
        engine = _make_engine()
        mock_mf.clone_as_subdirectory.return_value = Path("/work/max")
        engine._find_max_duration = MagicMock(return_value=(0.1, 0.2))

        intervals = []

        def capture_bisection(max_v, min_v, tol, bm, oc):
            intervals.append((min_v, max_v))
            return len(intervals) >= 2

        engine._run_time_cct = MagicMock(return_value=False)

        with patch.object(engine, "_isolated_copy") as mock_iso:
            mock_iso.return_value.__enter__ = MagicMock(return_value=Path("/tmp/work"))
            mock_iso.return_value.__exit__ = MagicMock(return_value=False)
            with patch.object(engine, "_is_bisection_complete", side_effect=capture_bisection):
                engine.find_cct(Path("/work"), Path("/jobs"), 0.1, "BM", "OC")

        # After first unstable step, max_val should have moved from 0.2 to 0.15
        _, first_max = intervals[0]
        assert first_max == pytest.approx(0.15)

    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    def test_temp_dir_is_removed_after_max_duration_search(self, mock_mf):
        engine = _make_engine()
        max_dir = Path("/work/max")
        mock_mf.clone_as_subdirectory.return_value = max_dir
        engine._find_max_duration = MagicMock(return_value=(0.1, 0.2))
        engine._run_time_cct = MagicMock(return_value=True)

        with patch.object(engine, "_isolated_copy") as mock_iso:
            mock_iso.return_value.__enter__ = MagicMock(return_value=Path("/tmp/work"))
            mock_iso.return_value.__exit__ = MagicMock(return_value=False)
            with patch.object(engine, "_is_bisection_complete", return_value=True):
                engine.find_cct(Path("/work"), Path("/jobs"), 0.1, "BM", "OC")

        mock_mf.remove_dir.assert_called_once_with(max_dir)

    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    def test_bisection_uses_cct_rel_tol(self, mock_mf):
        """find_cct must pass CCT_REL_TOL, not a custom value."""
        engine = _make_engine()
        mock_mf.clone_as_subdirectory.return_value = Path("/work/max")
        engine._find_max_duration = MagicMock(return_value=(0.1, 0.2))
        engine._run_time_cct = MagicMock(return_value=True)

        captured_tol = []

        def capture(*args, **kwargs):
            captured_tol.append(args[2])
            return True

        with patch.object(engine, "_isolated_copy") as mock_iso:
            mock_iso.return_value.__enter__ = MagicMock(return_value=Path("/tmp/work"))
            mock_iso.return_value.__exit__ = MagicMock(return_value=False)
            with patch.object(engine, "_is_bisection_complete", side_effect=capture):
                engine.find_cct(Path("/work"), Path("/jobs"), 0.1, "BM", "OC")

        assert all(t == CCT_REL_TOL for t in captured_tol)
