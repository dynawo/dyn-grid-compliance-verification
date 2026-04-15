#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#
import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dycov.curves.dynawo.orchestrator.model_setup import ModelSetup
from dycov.model.parameters import PdrParams, PimodelParams

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_gen(
    p0: float = -0.8,
    q0: float = -0.2,
    u0: float = 1.0,
    use_voltage_droop: bool = False,
    voltage_droop: float = 0.0,
) -> MagicMock:
    terminal = MagicMock()
    terminal.p0 = p0
    terminal.q0 = q0
    terminal.u0 = u0
    terminal.connected_equipment = "XFMR1"
    gen = MagicMock()
    gen.terminals = [terminal]
    gen.use_voltage_droop = use_voltage_droop
    gen.voltage_droop = voltage_droop
    return gen


def _make_producer(
    u_nom: float = 20.0,
    s_nom: float = 100.0,
    p_max_pu: float = 1.0,
    q_min_pu: float = -0.5,
    q_max_pu: float = 0.5,
    zone: int = 1,
    generators=None,
) -> MagicMock:
    producer = MagicMock()
    producer.u_nom = u_nom
    producer.s_nom = s_nom
    producer.p_max_pu = p_max_pu
    producer.q_min_pu = q_min_pu
    producer.q_max_pu = q_max_pu
    producer.get_zone.return_value = zone
    producer.generators = generators or [_make_gen()]
    xfmr = MagicMock(id="XFMR1")
    producer.stepup_xfmrs = [xfmr]
    producer.aux_load = None
    producer.auxload_xfmr = None
    producer.ppm_xfmr = None
    producer.intline = None
    return producer


def _make_owner(producer: MagicMock | None = None) -> MagicMock:
    owner = MagicMock()
    owner.get_producer.return_value = producer or _make_producer()
    owner._solver_id = "IDA"
    owner._solver_lib = "dynawo_SolverIDA"
    owner.get_generator_u_dim.return_value = 20.0
    owner.obtain_value.side_effect = lambda v: float(v)
    owner.complete_unit_characteristics = MagicMock()
    return owner


def _make_setup(owner: MagicMock | None = None, **kwargs) -> ModelSetup:
    if owner is None:
        owner = _make_owner()
    defaults = dict(pcs_name="PCS1", s_nref=100.0, f_nom=50.0)
    defaults.update(kwargs)
    return ModelSetup(owner, **defaults)


# ---------------------------------------------------------------------------
# _cfg_section
# ---------------------------------------------------------------------------


class TestCfgSection:
    @patch("dycov.curves.dynawo.orchestrator.model_setup.get_cfg_oc_name", return_value="A.B.C")
    def test_no_suffix(self, mock_gcn):
        setup = _make_setup()
        assert setup._cfg_section("A", "B", "C") == "A.B.C"

    @patch("dycov.curves.dynawo.orchestrator.model_setup.get_cfg_oc_name", return_value="A.B.C")
    def test_with_suffix(self, mock_gcn):
        setup = _make_setup()
        assert setup._cfg_section("A", "B", "C", ".Model") == "A.B.C.Model"

    @patch("dycov.curves.dynawo.orchestrator.model_setup.get_cfg_oc_name", return_value="A.B.C")
    def test_empty_suffix_unchanged(self, mock_gcn):
        setup = _make_setup()
        assert setup._cfg_section("A", "B", "C", "") == "A.B.C"


# ---------------------------------------------------------------------------
# _get_lines_for_initial_calcs
# ---------------------------------------------------------------------------


class TestGetLinesForInitialCalcs:
    def setup_method(self):
        self.setup = _make_setup()

    def test_empty_list_returns_infinite_admittance(self):
        result = self.setup._get_lines_for_initial_calcs([])
        assert result.y_tr == math.inf
        assert result.y_sh1 == 0
        assert result.y_sh2 == 0

    @patch("dycov.curves.dynawo.orchestrator.model_setup.line_pimodel")
    def test_single_line_returns_its_params(self, mock_pimodel):
        mock_pimodel.return_value = MagicMock(y_tr=1.0, y_sh1=0.1, y_sh2=0.2)
        line = MagicMock()
        result = self.setup._get_lines_for_initial_calcs([line])
        assert result == PimodelParams(1.0, 0.1, 0.2)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.line_pimodel")
    def test_multiple_lines_sums_admittances(self, mock_pimodel):
        mock_pimodel.side_effect = [
            MagicMock(y_tr=1.0, y_sh1=0.1, y_sh2=0.2),
            MagicMock(y_tr=2.0, y_sh1=0.3, y_sh2=0.4),
        ]
        result = self.setup._get_lines_for_initial_calcs([MagicMock(), MagicMock()])
        assert result.y_tr == pytest.approx(3.0)
        assert result.y_sh1 == pytest.approx(0.4)
        assert result.y_sh2 == pytest.approx(0.6)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.line_pimodel")
    def test_calls_pimodel_for_each_line(self, mock_pimodel):
        mock_pimodel.return_value = MagicMock(y_tr=0.0, y_sh1=0.0, y_sh2=0.0)
        lines = [MagicMock(), MagicMock(), MagicMock()]
        self.setup._get_lines_for_initial_calcs(lines)
        assert mock_pimodel.call_count == 3


# ---------------------------------------------------------------------------
# _calculate_xv
# ---------------------------------------------------------------------------


class TestCalculateXv:
    def setup_method(self):
        self.setup = _make_setup()

    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_raises_when_udip_equals_uinf(self, mock_config):
        mock_config.get_float.return_value = 1.0
        with pytest.raises(ValueError, match="division by zero"):
            self.setup._calculate_xv(udip=1.0, zcc=0.1, uinf=1.0)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_returns_positive_value(self, mock_config):
        mock_config.get_float.return_value = 1.0  # ztanphi
        xv = self.setup._calculate_xv(udip=0.9, zcc=0.1, uinf=1.0)
        assert xv > 0

    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_zero_xv_clamped_to_minimum(self, mock_config):
        # Force xv to zero by making ztanphi = 0
        mock_config.get_float.return_value = 0.0
        xv = self.setup._calculate_xv(udip=0.5, zcc=1.0, uinf=1.0)
        assert xv == pytest.approx(1e-3)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_formula_correctness(self, mock_config):
        ztanphi = 1.0
        mock_config.get_float.return_value = ztanphi
        udip, zcc, uinf = 0.8, 0.5, 1.0
        zv = (udip * zcc) / (uinf - udip)
        expected_xv = (zv * ztanphi) / math.sqrt(1 + ztanphi * ztanphi)
        result = self.setup._calculate_xv(udip=udip, zcc=zcc, uinf=uinf)
        assert result == pytest.approx(expected_xv)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_larger_ztanphi_increases_xv(self, mock_config):
        # With higher ztanphi the result should be larger (up to limit)
        def xv_for_ztanphi(ztanphi):
            mock_config.get_float.return_value = ztanphi
            return self.setup._calculate_xv(udip=0.5, zcc=0.3, uinf=1.0)

        assert xv_for_ztanphi(2.0) > xv_for_ztanphi(0.5)


# ---------------------------------------------------------------------------
# _adjust_event_value
# ---------------------------------------------------------------------------


class TestAdjustEventValue:
    def test_noop_when_not_voltage_setpoint(self):
        setup = _make_setup()
        params = {"connect_to": "ActivePowerSetpointPu", "pre_value": [1.0]}
        pdr = PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        setup._adjust_event_value(params, pdr)
        assert params["pre_value"] == [1.0]  # unchanged

    def test_noop_when_droop_disabled(self):
        gen = _make_gen(use_voltage_droop=False)
        owner = _make_owner(_make_producer(generators=[gen]))
        setup = _make_setup(owner)
        params = {"connect_to": "VoltageSetpointPu", "pre_value": [1.0]}
        pdr = PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        setup._adjust_event_value(params, pdr)
        assert params["pre_value"] == [1.0]

    def test_updates_pre_value_when_droop_enabled(self):
        gen = _make_gen(u0=1.02, use_voltage_droop=True, voltage_droop=0.05)
        gen.terminals[0].q0 = -0.1
        owner = _make_owner(_make_producer(generators=[gen]))
        setup = _make_setup(owner)
        params = {"connect_to": "VoltageSetpointPu", "pre_value": [0.0]}
        pdr = PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        setup._adjust_event_value(params, pdr)
        expected = 1.02 + 0.05 * (-0.1)
        assert params["pre_value"][0] == pytest.approx(expected)

    def test_only_droop_enabled_generators_are_updated(self):
        gen1 = _make_gen(u0=1.0, use_voltage_droop=False)
        gen2 = _make_gen(u0=1.05, use_voltage_droop=True, voltage_droop=0.1)
        gen2.terminals[0].q0 = -0.2
        owner = _make_owner(_make_producer(generators=[gen1, gen2]))
        setup = _make_setup(owner)
        params = {"connect_to": "VoltageSetpointPu", "pre_value": [1.0, 1.05]}
        pdr = PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        setup._adjust_event_value(params, pdr)
        assert params["pre_value"][0] == pytest.approx(1.0)  # gen1 unchanged
        assert params["pre_value"][1] == pytest.approx(1.05 + 0.1 * (-0.2))


# ---------------------------------------------------------------------------
# _get_event_parameters
# ---------------------------------------------------------------------------


class TestGetEventParameters:
    def _setup_config(
        self,
        mock_config,
        connect_to="ActivePowerSetpointPu",
        start_time=1.0,
        fault_duration=0.15,
        step_value=None,
        has_fault_duration=True,
        has_step_value=False,
    ):
        def get_value(section, key, default=None):
            if key == "connect_event_to":
                return connect_to
            if key == "setpoint_step_value":
                return str(step_value or 0.1)
            return default

        def get_float(section, key, default=None):
            if key == "sim_t_event_start":
                return start_time
            if key == "fault_duration":
                return fault_duration
            return default or 0.0

        def has_option(section, key):
            if key == "fault_duration":
                return has_fault_duration
            if key == "setpoint_step_value":
                return has_step_value
            return False

        mock_config.get_value.side_effect = get_value
        mock_config.get_float.side_effect = get_float
        mock_config.has_option.side_effect = has_option

    @patch("dycov.curves.dynawo.orchestrator.model_setup.generator_variables")
    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_active_power_setpoint_pre_value(self, mock_config, mock_gv):
        gen = _make_gen(p0=-0.8)
        gen.terminals[0].p0 = -0.8
        producer = _make_producer(s_nom=100.0, generators=[gen])
        owner = _make_owner(producer)
        setup = _make_setup(owner, s_nref=100.0)
        self._setup_config(mock_config, connect_to="ActivePowerSetpointPu")

        result = setup._get_event_parameters(
            "PCS1", "BM1", "OC1", pdr=PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        )

        # pre_value = -(-0.8) * (100/100) = 0.8
        assert result["pre_value"] == [pytest.approx(0.8)]
        assert result["connect_to"] == "ActivePowerSetpointPu"

    @patch("dycov.curves.dynawo.orchestrator.model_setup.generator_variables")
    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_reactive_power_setpoint_pre_value(self, mock_config, mock_gv):
        gen = _make_gen(q0=-0.3)
        gen.terminals[0].q0 = -0.3
        producer = _make_producer(s_nom=100.0, generators=[gen])
        owner = _make_owner(producer)
        setup = _make_setup(owner, s_nref=100.0)
        self._setup_config(mock_config, connect_to="ReactivePowerSetpointPu")

        result = setup._get_event_parameters(
            "PCS1", "BM1", "OC1", pdr=PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        )

        assert result["pre_value"] == [pytest.approx(0.3)]

    @patch("dycov.curves.dynawo.orchestrator.model_setup.generator_variables")
    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_voltage_setpoint_pre_value(self, mock_config, mock_gv):
        gen = _make_gen(u0=1.02)
        gen.terminals[0].u0 = 1.02
        producer = _make_producer(generators=[gen])
        owner = _make_owner(producer)
        setup = _make_setup(owner)
        self._setup_config(mock_config, connect_to="VoltageSetpointPu")

        result = setup._get_event_parameters(
            "PCS1", "BM1", "OC1", pdr=PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        )

        assert result["pre_value"] == [pytest.approx(1.02)]

    @patch("dycov.curves.dynawo.orchestrator.model_setup.generator_variables")
    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_unknown_connect_to_leaves_pre_value_as_float(self, mock_config, mock_gv):
        setup = _make_setup()
        self._setup_config(mock_config, connect_to="SomethingElse")
        result = setup._get_event_parameters(
            "PCS1", "BM1", "OC1", pdr=PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        )
        assert isinstance(result["pre_value"], float)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.generator_variables")
    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_start_time_and_duration_in_result(self, mock_config, mock_gv):
        setup = _make_setup()
        self._setup_config(mock_config, start_time=2.5, fault_duration=0.3)
        result = setup._get_event_parameters(
            "PCS1", "BM1", "OC1", pdr=PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        )
        assert result["start_time"] == pytest.approx(2.5)
        assert result["duration_time"] == pytest.approx(0.3)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.generator_variables")
    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_step_value_scaled_by_setpoint_factor(self, mock_config, mock_gv):
        producer = _make_producer(s_nom=50.0)
        owner = _make_owner(producer)
        owner.obtain_value.side_effect = lambda v: 0.1  # raw step
        setup = _make_setup(owner, s_nref=100.0)
        self._setup_config(
            mock_config,
            connect_to="ActivePowerSetpointPu",
            has_step_value=True,
            step_value=0.1,
        )
        result = setup._get_event_parameters(
            "PCS1", "BM1", "OC1", pdr=PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        )
        # setpoint_factor = 100/50 = 2.0
        assert result["step_value"] == pytest.approx(0.2)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.generator_variables")
    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_fault_duration_falls_back_to_generator_type_key(self, mock_config, mock_gv):
        """When fault_duration key is absent, uses fault_duration_{generator_type}."""
        setup = _make_setup()
        mock_gv.get_generator_type.return_value = "hv"

        def has_option(section, key):
            return key == "fault_duration_hv"

        def get_float(section, key, default=None):
            if key == "sim_t_event_start":
                return 1.0
            if key == "fault_duration_hv":
                return 0.25
            return default or 0.0

        mock_config.get_value.return_value = "ActivePowerSetpointPu"
        mock_config.get_float.side_effect = get_float
        mock_config.has_option.side_effect = has_option

        result = setup._get_event_parameters(
            "PCS1", "BM1", "OC1", pdr=PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        )
        assert result["duration_time"] == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# _get_line — has_line flag and return values
# ---------------------------------------------------------------------------


class TestGetLine:
    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_no_line_option_returns_zeros(self, mock_config):
        mock_config.has_option.return_value = False
        setup = _make_setup()
        rpu, xpu = setup._get_line("PCS1", "BM1", "OC1")
        assert rpu == 0.0
        assert xpu == 0.0
        assert setup.has_line is False

    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_line_xpu_sets_has_line_true(self, mock_config):
        def has_option(section, key):
            return key == "line_XPu"

        mock_config.has_option.side_effect = has_option
        mock_config.get_value.return_value = "0.1"
        setup = _make_setup()
        setup._get_line("PCS1", "BM1", "OC1")
        assert setup.has_line is True

    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_line_xpu_numeric_string_parsed(self, mock_config):
        def has_option(section, key):
            return key == "line_XPu"

        mock_config.has_option.side_effect = has_option
        mock_config.get_value.return_value = "0.15"
        setup = _make_setup()
        _, xpu = setup._get_line("PCS1", "BM1", "OC1")
        assert xpu == pytest.approx(0.15)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_scr_sets_has_line_true(self, mock_config):
        def has_option(section, key):
            return key == "SCR"

        mock_config.has_option.side_effect = has_option
        mock_config.get_float.side_effect = lambda s, k, d=None: {
            ("", "SCR"): 3.0,
            ("GridCode", "SCR_r_factor"): 10.0,
        }.get((s, k), d)
        setup = _make_setup()
        setup._get_line("PCS1", "BM1", "OC1")
        assert setup.has_line is True

    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_scr_zero_leaves_has_line_true_but_xpu_zero(self, mock_config):
        def has_option(section, key):
            return key == "SCR"

        mock_config.has_option.side_effect = has_option
        mock_config.get_float.side_effect = lambda s, k, d=None: 0.0
        setup = _make_setup()
        _, xpu = setup._get_line("PCS1", "BM1", "OC1")
        assert xpu == 0.0

    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_zone3_adds_rpu_from_xpu_r_factor(self, mock_config):
        producer = _make_producer(zone=3)
        owner = _make_owner(producer)
        setup = _make_setup(owner)

        def has_option(section, key):
            return key == "line_XPu"

        mock_config.has_option.side_effect = has_option
        mock_config.get_value.return_value = "0.1"
        mock_config.get_float.side_effect = lambda s, k, d=None: {
            ("GridCode", "XPu_r_factor"): 10.0,
        }.get((s, k), d)

        rpu, xpu = setup._get_line("PCS1", "BM1", "OC1")
        assert rpu == pytest.approx(xpu / 10.0)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_non_zone3_rpu_is_zero(self, mock_config):
        producer = _make_producer(zone=1)
        owner = _make_owner(producer)
        setup = _make_setup(owner)

        def has_option(section, key):
            return key == "line_XPu"

        mock_config.has_option.side_effect = has_option
        mock_config.get_value.return_value = "0.1"
        rpu, _ = setup._get_line("PCS1", "BM1", "OC1")
        assert rpu == 0.0

    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_complete_unit_characteristics_called(self, mock_config):
        def has_option(section, key):
            return key == "line_XPu"

        mock_config.has_option.side_effect = has_option
        mock_config.get_value.return_value = "0.2"
        setup = _make_setup()
        setup._get_line("PCS1", "BM1", "OC1")
        setup._owner.complete_unit_characteristics.assert_called_once_with(pytest.approx(0.2))


# ---------------------------------------------------------------------------
# _get_pdr
# ---------------------------------------------------------------------------


class TestGetPdr:
    def _config_for_pdr(self, mock_config, p_cfg="Pmax", q_cfg="0.0", u_cfg="Udim"):
        mock_config.get_value.side_effect = lambda s, k, d=None: {
            "pdr_P": p_cfg,
            "pdr_Q": q_cfg,
            "pdr_U": u_cfg,
        }.get(k, d)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.model_parameters")
    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_returns_pdr_params(self, mock_config, mock_mp):
        setup = _make_setup()
        self._config_for_pdr(mock_config)
        mock_mp.extract_defined_value.return_value = 1.0

        result = setup._get_pdr("PCS1", "BM1", "OC1", u_dim=20.0)

        from dycov.model.parameters import PdrParams

        assert isinstance(result, PdrParams)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.model_parameters")
    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_pmax_consumption_sets_consumption_flag(self, mock_config, mock_mp):
        producer = _make_producer()
        owner = _make_owner(producer)
        setup = _make_setup(owner)
        self._config_for_pdr(mock_config, p_cfg="PmaxConsumption")
        mock_mp.extract_defined_value.return_value = 1.0

        setup._get_pdr("PCS1", "BM1", "OC1", u_dim=20.0)

        producer.set_consumption.assert_called_once_with(True)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.model_parameters")
    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_pmax_injection_does_not_set_consumption(self, mock_config, mock_mp):
        producer = _make_producer()
        owner = _make_owner(producer)
        setup = _make_setup(owner)
        self._config_for_pdr(mock_config, p_cfg="PmaxInjection")
        mock_mp.extract_defined_value.return_value = 1.0

        setup._get_pdr("PCS1", "BM1", "OC1", u_dim=20.0)

        producer.set_consumption.assert_called_once_with(False)

    @patch("dycov.curves.dynawo.orchestrator.model_setup.model_parameters")
    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_qmin_key_used_when_present(self, mock_config, mock_mp):
        setup = _make_setup()
        self._config_for_pdr(mock_config, q_cfg="Qmin*0.5")
        calls = []
        mock_mp.extract_defined_value.side_effect = lambda cfg, key, val, sign=1: (
            calls.append(key) or 0.0
        )

        setup._get_pdr("PCS1", "BM1", "OC1", u_dim=20.0)

        assert "Qmin" in calls

    @patch("dycov.curves.dynawo.orchestrator.model_setup.model_parameters")
    @patch("dycov.curves.dynawo.orchestrator.model_setup.config")
    def test_qmax_key_used_when_present(self, mock_config, mock_mp):
        setup = _make_setup()
        self._config_for_pdr(mock_config, q_cfg="Qmax*0.5")
        calls = []
        mock_mp.extract_defined_value.side_effect = lambda cfg, key, val, sign=1: (
            calls.append(key) or 0.0
        )

        setup._get_pdr("PCS1", "BM1", "OC1", u_dim=20.0)

        assert "Qmax" in calls
