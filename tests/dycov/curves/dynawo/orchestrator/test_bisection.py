#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#
import logging
import math
from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dycov.curves.dynawo.orchestrator.bisection import (
    BISECTION_ROUND,
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


@contextmanager
def _fake_isolated_copy(engine):
    """Patches engine._isolated_copy so each iteration runs in a fixed fake dir."""
    with patch.object(engine, "_isolated_copy") as mock_iso:
        mock_iso.return_value.__enter__ = MagicMock(return_value=Path("/tmp/work"))
        mock_iso.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_iso


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
# _isolated_copy
# ---------------------------------------------------------------------------


class TestIsolatedCopy:
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    def test_yields_populated_temp_dir_and_cleans_up(self, mock_mf):
        engine = _make_engine()

        with engine._isolated_copy(Path("/src")) as work:
            assert work.name.startswith("fault_time_execution_")
            mock_mf.copy_directory.assert_called_once_with(Path("/src"), work)
            temp_root = work.parent
            assert temp_root.exists()

        assert not temp_root.exists()


# ---------------------------------------------------------------------------
# _bolted_fault_max_residual_voltage
# ---------------------------------------------------------------------------


class TestBoltedFaultMaxResidualVoltage:
    def _engine_with_config(self, config_mock, s_nom):
        config_mock.get_float.side_effect = lambda section, key, default=None: {
            ("Global", "bolted_fault_max_voltage_small"): 0.01,
            ("Global", "bolted_fault_max_voltage_large"): 0.005,
            ("Global", "bolted_fault_snom_small"): 4.0,
            ("Global", "bolted_fault_snom_large"): 90.0,
        }.get((section, key), default)
        engine = _make_engine()
        engine._producer.s_nom = s_nom
        return engine

    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_small_reference_generator(self, mock_config):
        engine = self._engine_with_config(mock_config, s_nom=4.0)
        assert engine._bolted_fault_max_residual_voltage() == pytest.approx(0.01)

    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_large_reference_generator(self, mock_config):
        engine = self._engine_with_config(mock_config, s_nom=90.0)
        assert engine._bolted_fault_max_residual_voltage() == pytest.approx(0.005)

    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_interpolates_between_references(self, mock_config):
        engine = self._engine_with_config(mock_config, s_nom=47.0)
        assert engine._bolted_fault_max_residual_voltage() == pytest.approx(0.0075)

    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_clamps_below_small_reference(self, mock_config):
        engine = self._engine_with_config(mock_config, s_nom=0.25)
        assert engine._bolted_fault_max_residual_voltage() == pytest.approx(0.01)

    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_clamps_above_large_reference(self, mock_config):
        engine = self._engine_with_config(mock_config, s_nom=500.0)
        assert engine._bolted_fault_max_residual_voltage() == pytest.approx(0.005)

    def _engine_with_degenerate_config(self, config_mock, s_nom, snom_small=50.0, snom_large=50.0):
        config_mock.get_float.side_effect = lambda section, key, default=None: {
            ("Global", "bolted_fault_max_voltage_small"): 0.01,
            ("Global", "bolted_fault_max_voltage_large"): 0.005,
            ("Global", "bolted_fault_snom_small"): snom_small,
            ("Global", "bolted_fault_snom_large"): snom_large,
        }.get((section, key), default)
        engine = _make_engine()
        engine._producer.s_nom = s_nom
        return engine

    @patch("dycov.curves.dynawo.orchestrator.bisection.dycov_logging")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_equal_references_fall_back_to_stricter_threshold(self, mock_config, mock_logging):
        for s_nom in (100.0, 10.0):
            engine = self._engine_with_degenerate_config(mock_config, s_nom=s_nom)
            assert engine._bolted_fault_max_residual_voltage() == pytest.approx(0.005)

    @patch("dycov.curves.dynawo.orchestrator.bisection.dycov_logging")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_inverted_references_fall_back_to_stricter_threshold(self, mock_config, mock_logging):
        engine = self._engine_with_degenerate_config(
            mock_config, s_nom=10.0, snom_small=90.0, snom_large=4.0
        )
        assert engine._bolted_fault_max_residual_voltage() == pytest.approx(0.005)

    @patch("dycov.curves.dynawo.orchestrator.bisection.dycov_logging")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_inconsistent_references_log_warning(self, mock_config, mock_logging):
        engine = self._engine_with_degenerate_config(mock_config, s_nom=10.0)
        engine._bolted_fault_max_residual_voltage()
        mock_logging.get_logger.return_value.warning.assert_called_once()


# ---------------------------------------------------------------------------
# find_bolted_fault — logic flow
# ---------------------------------------------------------------------------


class TestFindBoltedFault:
    """Tests for the bolted fault search control flow, with all I/O mocked."""

    def _engine_with_config(self, config_mock):
        config_mock.get_float.side_effect = lambda section, key, default=None: {
            ("GridCode", "fault_r_factor"): 10.0,
            ("Global", "bolted_fault_max_impedance"): 1.0,
            ("Global", "bolted_fault_min_impedance"): 1e-5,
            ("Global", "bolted_fault_rel_tol"): 1e-5,
            ("Global", "bolted_fault_max_voltage_small"): 0.01,
            ("Global", "bolted_fault_max_voltage_large"): 0.005,
            ("Global", "bolted_fault_snom_small"): 4.0,
            ("Global", "bolted_fault_snom_large"): 90.0,
        }.get((section, key), default)
        return _make_engine()

    def _find(self, engine, simulate_fn, reset_fn):
        engine.find_bolted_fault(
            Path("/out"),
            Path("/work"),
            Path("/jobs"),
            1.0,
            0.15,
            "BM",
            "OC",
            simulate_fn,
            reset_fn,
        )

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_residual_voltage")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_non_zone1_is_noop(self, mock_config, mock_rp, mock_mf, mock_crv):
        engine = self._engine_with_config(mock_config)
        engine._producer.get_zone.return_value = 3
        simulate_fn = MagicMock()

        self._find(engine, simulate_fn, MagicMock())

        simulate_fn.assert_not_called()
        mock_rp.fault_par_file.assert_not_called()

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_residual_voltage")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_keeps_most_severe_impedance_when_it_converges(
        self, mock_config, mock_rp, mock_mf, mock_crv
    ):
        engine = self._engine_with_config(mock_config)
        mock_crv.return_value = VoltDipResult.DIP_CORRECT
        simulate_fn = MagicMock(return_value=_succeed_outcome())

        with _fake_isolated_copy(engine):
            self._find(engine, simulate_fn, MagicMock())

        assert simulate_fn.call_count == 1
        final_call_args = mock_rp.fault_par_file.call_args_list[-1]
        assert final_call_args[0][0] == Path("/work")
        assert final_call_args[0][3] == pytest.approx(1e-5)

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_residual_voltage")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_relaxes_impedance_on_non_convergence(self, mock_config, mock_rp, mock_mf, mock_crv):
        engine = self._engine_with_config(mock_config)
        mock_crv.return_value = VoltDipResult.DIP_CORRECT
        simulate_fn = MagicMock(side_effect=[_fail_outcome(), _succeed_outcome()])

        with _fake_isolated_copy(engine):
            self._find(engine, simulate_fn, MagicMock())

        assert simulate_fn.call_count == 2
        final_call_args = mock_rp.fault_par_file.call_args_list[-1]
        assert final_call_args[0][0] == Path("/work")
        assert final_call_args[0][3] == pytest.approx((1.0 + 1e-5) / 2)

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_residual_voltage")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_raises_when_all_simulations_fail(self, mock_config, mock_rp, mock_mf, mock_crv):
        engine = self._engine_with_config(mock_config)
        simulate_fn = MagicMock(return_value=_fail_outcome())

        with _fake_isolated_copy(engine):
            with patch.object(engine, "_is_bisection_complete", return_value=True):
                with pytest.raises(ValueError, match="Fault simulation fails"):
                    self._find(engine, simulate_fn, MagicMock())

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_residual_voltage")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_raises_when_residual_voltage_unachievable(
        self, mock_config, mock_rp, mock_mf, mock_crv
    ):
        """Converges at the most severe impedance but the residual stays above the
        threshold: no larger impedance can help, so the search must fail."""
        engine = self._engine_with_config(mock_config)
        mock_crv.return_value = VoltDipResult.DIP_TOO_SMALL
        simulate_fn = MagicMock(return_value=_succeed_outcome())

        with _fake_isolated_copy(engine):
            with pytest.raises(ValueError, match="Fault dip unachievable"):
                self._find(engine, simulate_fn, MagicMock())
        assert simulate_fn.call_count == 1

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_residual_voltage")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_raises_when_column_missing(self, mock_config, mock_rp, mock_mf, mock_crv):
        engine = self._engine_with_config(mock_config)
        mock_crv.return_value = VoltDipResult.COLUMN_MISSING
        simulate_fn = MagicMock(return_value=_succeed_outcome())

        with _fake_isolated_copy(engine):
            with pytest.raises(ValueError, match="Voltage curve missing"):
                self._find(engine, simulate_fn, MagicMock())

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_residual_voltage")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_reset_solver_called_after_each_simulation(
        self, mock_config, mock_rp, mock_mf, mock_crv
    ):
        engine = self._engine_with_config(mock_config)
        mock_crv.return_value = VoltDipResult.DIP_CORRECT
        simulate_fn = MagicMock(side_effect=[_fail_outcome(), _succeed_outcome()])
        reset_fn = MagicMock()

        with _fake_isolated_copy(engine):
            self._find(engine, simulate_fn, reset_fn)

        assert reset_fn.call_count == simulate_fn.call_count

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_residual_voltage")
    @patch("dycov.curves.dynawo.orchestrator.bisection.dycov_logging")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.replace_placeholders")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_debug_level_renames_iteration_dir(
        self, mock_config, mock_rp, mock_mf, mock_log, mock_crv
    ):
        engine = self._engine_with_config(mock_config)
        mock_log.get_logger.return_value.getEffectiveLevel.return_value = logging.DEBUG
        mock_crv.return_value = VoltDipResult.DIP_CORRECT
        simulate_fn = MagicMock(return_value=_succeed_outcome())

        with _fake_isolated_copy(engine):
            self._find(engine, simulate_fn, MagicMock())

        mock_mf.rename_path.assert_called_once_with(
            Path("/tmp/work"), Path("/work") / "bisection_last_success"
        )


# ---------------------------------------------------------------------------
# find_hiz_fault — logic flow
# ---------------------------------------------------------------------------


class TestFindHizFault:
    """Tests for the HIZ bisection control flow, with all I/O mocked."""

    def _engine_with_config(self, config_mock):
        config_mock.get_float.side_effect = lambda section, key, default=None: {
            ("GridCode", "fault_r_factor"): 10.0,
            ("Global", "hiz_fault_max_impedance"): 10.0,
            ("Global", "hiz_fault_min_impedance"): 1e-10,
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
            with _fake_isolated_copy(engine):
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
            with _fake_isolated_copy(engine):
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

        with _fake_isolated_copy(engine):
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

        with _fake_isolated_copy(engine):
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

        with _fake_isolated_copy(engine):
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

        with _fake_isolated_copy(engine):
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

    def _run_until_correct(self, engine, mock_cvd, simulate_outcomes, classifications):
        """Runs find_hiz_fault with the given simulation/classification sequences."""
        mock_cvd.side_effect = classifications
        simulate_fn = MagicMock(side_effect=simulate_outcomes)
        with _fake_isolated_copy(engine):
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
                    MagicMock(),
                )
        return simulate_fn

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_voltage_dip")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_failure_after_dip_too_large_narrows_from_above(self, mock_config, mock_mf, mock_cvd):
        """A failed simulation reuses the last classification: after DIP_TOO_LARGE,
        the failure moves max_val down instead of the no-classification default."""
        engine = self._engine_with_config(mock_config)

        simulate_fn = self._run_until_correct(
            engine,
            mock_cvd,
            [_succeed_outcome(), _fail_outcome(), _succeed_outcome()],
            [VoltDipResult.DIP_TOO_LARGE, VoltDipResult.DIP_CORRECT],
        )

        assert simulate_fn.call_count == 3

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_voltage_dip")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_failure_after_dip_too_small_narrows_from_below(self, mock_config, mock_mf, mock_cvd):
        """After a DIP_TOO_SMALL classification, a failed simulation moves min_val up."""
        engine = self._engine_with_config(mock_config)

        simulate_fn = self._run_until_correct(
            engine,
            mock_cvd,
            [_succeed_outcome(), _fail_outcome(), _succeed_outcome()],
            [VoltDipResult.DIP_TOO_SMALL, VoltDipResult.DIP_CORRECT],
        )

        assert simulate_fn.call_count == 3

    @patch("dycov.curves.dynawo.orchestrator.bisection.classify_voltage_dip")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    @patch("dycov.curves.dynawo.orchestrator.bisection.dycov_logging")
    @patch("dycov.curves.dynawo.orchestrator.bisection.config")
    def test_debug_level_renames_iteration_dir(self, mock_config, mock_log, mock_mf, mock_cvd):
        engine = self._engine_with_config(mock_config)
        mock_log.get_logger.return_value.getEffectiveLevel.return_value = logging.DEBUG
        mock_cvd.return_value = VoltDipResult.DIP_CORRECT
        simulate_fn = MagicMock(return_value=_succeed_outcome())

        with _fake_isolated_copy(engine):
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
                    MagicMock(),
                )

        mock_mf.rename_path.assert_called_once_with(
            Path("/tmp/work"), Path("/work") / "bisection_last_success"
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

        with _fake_isolated_copy(engine):
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

        with _fake_isolated_copy(engine):
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

        with _fake_isolated_copy(engine):
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

        with _fake_isolated_copy(engine):
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

        with _fake_isolated_copy(engine):
            with patch.object(engine, "_is_bisection_complete", side_effect=capture):
                engine.find_cct(Path("/work"), Path("/jobs"), 0.1, "BM", "OC")

        assert all(t == CCT_REL_TOL for t in captured_tol)


# ---------------------------------------------------------------------------
# find_cct — debug artifacts
# ---------------------------------------------------------------------------


class TestFindCctDebugRename:
    @patch("dycov.curves.dynawo.orchestrator.bisection.dycov_logging")
    @patch("dycov.curves.dynawo.orchestrator.bisection.manage_files")
    def test_debug_level_renames_iteration_dir(self, mock_mf, mock_log):
        engine = _make_engine()
        mock_log.get_logger.return_value.getEffectiveLevel.return_value = logging.DEBUG

        with patch.object(engine, "_find_max_duration", return_value=(0.1, 0.100005)):
            with patch.object(engine, "_run_time_cct", return_value=False):
                with _fake_isolated_copy(engine):
                    engine.find_cct(Path("/work"), Path("/jobs"), 0.1, "BM", "OC")

        mock_mf.rename_path.assert_called_with(
            Path("/tmp/work"), Path("/work") / "bisection_last_failure"
        )
