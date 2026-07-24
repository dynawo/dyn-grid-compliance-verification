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

# We patch at the model_setup module level throughout.
_MS = "dycov.curves.dynawo.orchestrator.model_setup"

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_gen(
    p0: float = -0.8,
    q0: float = -0.2,
    u0: float = 1.0,
    use_voltage_droop: bool = False,
    voltage_droop: float = 0.0,
    s_nom: float = 100.0,
    ppc_local: bool = True,
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
    gen.s_nom = s_nom
    gen.ppc_local = ppc_local
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
    @patch(f"{_MS}.get_cfg_oc_name", return_value="A.B.C")
    def test_no_suffix(self, mock_gcn):
        setup = _make_setup()
        assert setup._cfg_section("A", "B", "C") == "A.B.C"

    @patch(f"{_MS}.get_cfg_oc_name", return_value="A.B.C")
    def test_with_suffix(self, mock_gcn):
        setup = _make_setup()
        assert setup._cfg_section("A", "B", "C", ".Model") == "A.B.C.Model"

    @patch(f"{_MS}.get_cfg_oc_name", return_value="A.B.C")
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

    @patch(f"{_MS}.line_pimodel")
    def test_single_line_returns_its_params(self, mock_pimodel):
        mock_pimodel.return_value = MagicMock(y_tr=1.0, y_sh1=0.1, y_sh2=0.2)
        line = MagicMock()
        result = self.setup._get_lines_for_initial_calcs([line])
        assert result == PimodelParams(1.0, 0.1, 0.2)

    @patch(f"{_MS}.line_pimodel")
    def test_multiple_lines_sums_admittances(self, mock_pimodel):
        mock_pimodel.side_effect = [
            MagicMock(y_tr=1.0, y_sh1=0.1, y_sh2=0.2),
            MagicMock(y_tr=2.0, y_sh1=0.3, y_sh2=0.4),
        ]
        result = self.setup._get_lines_for_initial_calcs([MagicMock(), MagicMock()])
        assert result.y_tr == pytest.approx(3.0)
        assert result.y_sh1 == pytest.approx(0.4)
        assert result.y_sh2 == pytest.approx(0.6)

    @patch(f"{_MS}.line_pimodel")
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

    @patch(f"{_MS}.config")
    def test_raises_when_udip_equals_uinf(self, mock_config):
        mock_config.get_float.return_value = 1.0
        with pytest.raises(ValueError, match="division by zero"):
            self.setup._calculate_xv(udip=1.0, zcc=0.1, uinf=1.0)

    @patch(f"{_MS}.config")
    def test_returns_positive_value(self, mock_config):
        mock_config.get_float.return_value = 1.0  # ztanphi
        xv = self.setup._calculate_xv(udip=0.9, zcc=0.1, uinf=1.0)
        assert xv > 0

    @patch(f"{_MS}.config")
    def test_zero_xv_clamped_to_minimum(self, mock_config):
        # Force xv to zero by making ztanphi = 0
        mock_config.get_float.return_value = 0.0
        xv = self.setup._calculate_xv(udip=0.5, zcc=1.0, uinf=1.0)
        assert xv == pytest.approx(1e-3)

    @patch(f"{_MS}.config")
    def test_formula_correctness(self, mock_config):
        ztanphi = 1.0
        mock_config.get_float.return_value = ztanphi
        udip, zcc, uinf = 0.8, 0.5, 1.0
        zv = (udip * zcc) / (uinf - udip)
        expected_xv = (zv * ztanphi) / math.sqrt(1 + ztanphi * ztanphi)
        result = self.setup._calculate_xv(udip=udip, zcc=zcc, uinf=uinf)
        assert result == pytest.approx(expected_xv)

    @patch(f"{_MS}.config")
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

    @patch(f"{_MS}.generator_variables")
    @patch(f"{_MS}.config")
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

    @patch(f"{_MS}.generator_variables")
    @patch(f"{_MS}.config")
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

    @patch(f"{_MS}.generator_variables")
    @patch(f"{_MS}.config")
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

    @patch(f"{_MS}.generator_variables")
    @patch(f"{_MS}.config")
    def test_unknown_connect_to_leaves_pre_value_as_float(self, mock_config, mock_gv):
        setup = _make_setup()
        self._setup_config(mock_config, connect_to="SomethingElse")
        result = setup._get_event_parameters(
            "PCS1", "BM1", "OC1", pdr=PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        )
        assert isinstance(result["pre_value"], float)

    @patch(f"{_MS}.generator_variables")
    @patch(f"{_MS}.config")
    def test_start_time_and_duration_in_result(self, mock_config, mock_gv):
        setup = _make_setup()
        self._setup_config(mock_config, start_time=2.5, fault_duration=0.3)
        result = setup._get_event_parameters(
            "PCS1", "BM1", "OC1", pdr=PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        )
        assert result["start_time"] == pytest.approx(2.5)
        assert result["duration_time"] == pytest.approx(0.3)

    @patch(f"{_MS}.generator_variables")
    @patch(f"{_MS}.config")
    def test_step_value_scaled_by_generator_snom(self, mock_config, mock_gv):
        gen = _make_gen(s_nom=50.0)
        producer = _make_producer(s_nom=50.0, generators=[gen])
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
        # per-generator factor = s_nref / gen.s_nom = 100/50 = 2.0
        assert result["step_value"] == [pytest.approx(0.2)]

    @patch(f"{_MS}.generator_variables")
    @patch(f"{_MS}.config")
    def test_multi_unit_pre_value_uses_generator_snom(self, mock_config, mock_gv):
        """Regression for #359: 2 x 90 MVA units (plant SNom = 180). The setpoint must
        be converted with each unit's SNom, not the plant aggregate."""
        gens = [_make_gen(s_nom=90.0, ppc_local=False) for _ in range(2)]
        producer = _make_producer(s_nom=180.0, generators=gens)
        owner = _make_owner(producer)
        setup = _make_setup(owner, s_nref=100.0)
        self._setup_config(mock_config, connect_to="ActivePowerSetpointPu")

        result = setup._get_event_parameters(
            "PCS1", "BM1", "OC1", pdr=PdrParams(1.0, 0.0, complex(-0.75, 0.0), -0.75, 0.0)
        )

        # pre_value = -pdr.p * s_nref / gen.s_nom = 0.75 * 100/90 (NOT 100/180)
        assert result["pre_value"] == [pytest.approx(0.75 * 100 / 90)] * 2

    @patch(f"{_MS}.generator_variables")
    @patch(f"{_MS}.config")
    def test_multi_unit_step_value_uses_generator_snom(self, mock_config, mock_gv):
        """Regression for #359: step_value in the WECC4 case must be 0.75*100/90 = 0.8333
        per unit, not 0.75*100/180 = 0.4167."""
        gens = [_make_gen(s_nom=90.0, ppc_local=False) for _ in range(2)]
        producer = _make_producer(s_nom=180.0, generators=gens)
        owner = _make_owner(producer)
        owner.obtain_value.side_effect = lambda v: 0.75  # raw step (SnRef base)
        setup = _make_setup(owner, s_nref=100.0)
        self._setup_config(
            mock_config,
            connect_to="ActivePowerSetpointPu",
            has_step_value=True,
            step_value=0.75,
        )
        result = setup._get_event_parameters(
            "PCS1", "BM1", "OC1", pdr=PdrParams(1.0, 0.0, complex(-0.75, 0.0), -0.75, 0.0)
        )
        assert result["step_value"] == [pytest.approx(0.75 * 100 / 90)] * 2

    @patch(f"{_MS}.generator_variables")
    @patch(f"{_MS}.config")
    def test_step_value_not_scaled_for_voltage_setpoint(self, mock_config, mock_gv):
        gen = _make_gen(s_nom=50.0)
        producer = _make_producer(s_nom=50.0, generators=[gen])
        owner = _make_owner(producer)
        owner.obtain_value.side_effect = lambda v: 0.02
        setup = _make_setup(owner, s_nref=100.0)
        self._setup_config(
            mock_config,
            connect_to="VoltageSetpointPu",
            has_step_value=True,
            step_value=0.02,
        )
        result = setup._get_event_parameters(
            "PCS1", "BM1", "OC1", pdr=PdrParams(1.0, 0.0, complex(0.5, 0.2), 0.5, 0.2)
        )
        # Voltage setpoint carries no SNom conversion and stays scalar
        assert result["step_value"] == pytest.approx(0.02)

    @patch(f"{_MS}.generator_variables")
    @patch(f"{_MS}.config")
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
    @patch(f"{_MS}.config")
    def test_no_line_option_returns_zeros(self, mock_config):
        mock_config.has_option.return_value = False
        setup = _make_setup()
        rpu, xpu = setup._get_line("PCS1", "BM1", "OC1")
        assert rpu == 0.0
        assert xpu == 0.0
        assert setup.has_line is False

    @patch(f"{_MS}.config")
    def test_line_xpu_sets_has_line_true(self, mock_config):
        def has_option(section, key):
            return key == "line_XPu"

        mock_config.has_option.side_effect = has_option
        mock_config.get_value.return_value = "0.1"
        setup = _make_setup()
        setup._get_line("PCS1", "BM1", "OC1")
        assert setup.has_line is True

    @patch(f"{_MS}.config")
    def test_line_xpu_numeric_string_parsed(self, mock_config):
        def has_option(section, key):
            return key == "line_XPu"

        mock_config.has_option.side_effect = has_option
        mock_config.get_value.return_value = "0.15"
        setup = _make_setup()
        _, xpu = setup._get_line("PCS1", "BM1", "OC1")
        assert xpu == pytest.approx(0.15)

    @patch(f"{_MS}.config")
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

    @patch(f"{_MS}.config")
    def test_scr_zero_leaves_has_line_true_but_xpu_zero(self, mock_config):
        def has_option(section, key):
            return key == "SCR"

        mock_config.has_option.side_effect = has_option
        mock_config.get_float.side_effect = lambda s, k, d=None: 0.0
        setup = _make_setup()
        _, xpu = setup._get_line("PCS1", "BM1", "OC1")
        assert xpu == 0.0

    @patch(f"{_MS}.config")
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

    @patch(f"{_MS}.config")
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

    @patch(f"{_MS}.config")
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

    @patch(f"{_MS}.model_parameters")
    @patch(f"{_MS}.config")
    def test_returns_pdr_params(self, mock_config, mock_mp):
        setup = _make_setup()
        self._config_for_pdr(mock_config)
        mock_mp.extract_defined_value.return_value = 1.0

        result = setup._get_pdr("PCS1", "BM1", "OC1", u_dim=20.0)

        from dycov.model.parameters import PdrParams

        assert isinstance(result, PdrParams)

    @patch(f"{_MS}.model_parameters")
    @patch(f"{_MS}.config")
    def test_pmax_consumption_sets_consumption_flag(self, mock_config, mock_mp):
        producer = _make_producer()
        owner = _make_owner(producer)
        setup = _make_setup(owner)
        self._config_for_pdr(mock_config, p_cfg="PmaxConsumption")
        mock_mp.extract_defined_value.return_value = 1.0

        setup._get_pdr("PCS1", "BM1", "OC1", u_dim=20.0)

        producer.set_consumption.assert_called_once_with(True)

    @patch(f"{_MS}.model_parameters")
    @patch(f"{_MS}.config")
    def test_pmax_injection_does_not_set_consumption(self, mock_config, mock_mp):
        producer = _make_producer()
        owner = _make_owner(producer)
        setup = _make_setup(owner)
        self._config_for_pdr(mock_config, p_cfg="PmaxInjection")
        mock_mp.extract_defined_value.return_value = 1.0

        setup._get_pdr("PCS1", "BM1", "OC1", u_dim=20.0)

        producer.set_consumption.assert_called_once_with(False)

    @patch(f"{_MS}.model_parameters")
    @patch(f"{_MS}.config")
    def test_qmin_key_used_when_present(self, mock_config, mock_mp):
        setup = _make_setup()
        self._config_for_pdr(mock_config, q_cfg="Qmin*0.5")
        calls = []
        mock_mp.extract_defined_value.side_effect = lambda cfg, key, val, sign=1: (
            calls.append(key) or 0.0
        )

        setup._get_pdr("PCS1", "BM1", "OC1", u_dim=20.0)

        assert "Qmin" in calls

    @patch(f"{_MS}.model_parameters")
    @patch(f"{_MS}.config")
    def test_qmax_key_used_when_present(self, mock_config, mock_mp):
        setup = _make_setup()
        self._config_for_pdr(mock_config, q_cfg="Qmax*0.5")
        calls = []
        mock_mp.extract_defined_value.side_effect = lambda cfg, key, val, sign=1: (
            calls.append(key) or 0.0
        )

        setup._get_pdr("PCS1", "BM1", "OC1", u_dim=20.0)

        assert "Qmax" in calls


# ---------------------------------------------------------------------------
# complete_model — orchestration wiring
# ---------------------------------------------------------------------------


class TestCompleteModel:
    """Tests for the complete_model orchestration, with all collaborators mocked."""

    def _run(
        self,
        producer=None,
        reference_event_start_time=None,
        applicable=True,
        has_line=False,
        event_params=None,
    ):
        owner = _make_owner(producer)
        setup = _make_setup(owner)
        event_params = event_params if event_params is not None else {"start_time": 5.0}
        with (
            patch(f"{_MS}.model_parameters") as mock_mp,
            patch(f"{_MS}.init_calcs"),
            patch(f"{_MS}.omega_file") as mock_of,
            patch(f"{_MS}.tso_file") as mock_tf,
            patch(f"{_MS}.crv") as mock_crv,
            patch(f"{_MS}.config"),
            patch(f"{_MS}.get_cfg_oc_name", return_value="PCS1.BM.OC"),
            patch(f"{_MS}.generator_variables"),
            patch(f"{_MS}.JobsFile") as mock_jobs,
            patch(f"{_MS}.ParFile") as mock_par,
            patch(f"{_MS}.DydFile") as mock_dyd,
            patch(f"{_MS}.TableFile") as mock_table,
            patch(f"{_MS}.SolversFile") as mock_solvers,
            patch.object(setup, "_get_pdr"),
            patch.object(setup, "_get_line", return_value=(0.01, 0.1)),
            patch.object(setup, "_get_lines_for_initial_calcs"),
            patch.object(setup, "_sort_stepup_xfmrs_to_generators", return_value=[]),
            patch.object(setup, "_get_tso_loads", return_value=(None, None)),
            patch.object(setup, "_get_event_parameters", return_value=event_params),
            patch.object(setup, "_adjust_event_value"),
            patch.object(setup, "_calculate_xv_values"),
        ):
            mock_mp.adjust_producer_init.return_value = applicable
            mock_mp.get_pcs_load_params.return_value = []
            mock_mp.get_pcs_lines_params.return_value = []
            mock_mp.get_pcs_generators_params.return_value = []
            mock_crv.create_curves_file.return_value = {"var": "curve"}
            setup.has_line = has_line
            result = setup.complete_model(
                Path("/work"), "PCS1", "BM", "OC", reference_event_start_time
            )
            mocks = dict(
                mp=mock_mp,
                of=mock_of,
                tf=mock_tf,
                crv=mock_crv,
                jobs=mock_jobs,
                par=mock_par,
                dyd=mock_dyd,
                table=mock_table,
                solvers=mock_solvers,
            )
        return setup, result, mocks

    def test_happy_path_completes_all_input_files(self):
        setup, (is_applicable, event_params), mocks = self._run()

        assert is_applicable is True
        assert event_params["start_time"] == 5.0
        for file_mock in ("jobs", "par", "dyd", "table", "solvers"):
            mocks[file_mock].return_value.complete_file.assert_called_once()
        mocks["of"].complete_omega.assert_called_once()
        mocks["tf"].complete_setpoint.assert_called_once()
        mocks["crv"].create_curves_file.assert_called_once()
        assert setup.curves_dict == {"var": "curve"}

    def test_not_applicable_skips_file_writing(self):
        setup, (is_applicable, _), mocks = self._run(applicable=False)

        assert is_applicable is False
        mocks["jobs"].return_value.complete_file.assert_not_called()
        mocks["crv"].create_curves_file.assert_not_called()

    def test_reference_event_start_time_overrides_configured(self):
        _, (_, event_params), _ = self._run(
            reference_event_start_time=2.0, event_params={"start_time": 5.0}
        )

        assert event_params["start_time"] == 2.0

    def test_matching_reference_start_time_is_kept(self):
        _, (_, event_params), _ = self._run(
            reference_event_start_time=5.0, event_params={"start_time": 5.0}
        )

        assert event_params["start_time"] == 5.0

    def test_line_params_read_only_when_has_line(self):
        _, _, mocks = self._run(has_line=True)
        mocks["mp"].get_pcs_lines_params.assert_called_once()

        _, _, mocks = self._run(has_line=False)
        mocks["mp"].get_pcs_lines_params.assert_not_called()

    def test_aux_and_ppm_xfmrs_included_in_curves_file(self):
        producer = _make_producer()
        aux_xfmr = MagicMock(id="AUX_XFMR")
        ppm_xfmr = MagicMock(id="PPM_XFMR")
        producer.auxload_xfmr = aux_xfmr
        producer.ppm_xfmr = ppm_xfmr

        _, _, mocks = self._run(producer=producer)

        xmfrs = mocks["crv"].create_curves_file.call_args[0][2]
        assert aux_xfmr in xmfrs
        assert ppm_xfmr in xmfrs


# ---------------------------------------------------------------------------
# compute_rx_from_scr
# ---------------------------------------------------------------------------


class TestComputeRxFromScr:
    def test_impedance_magnitude_matches_scr(self):
        from dycov.curves.dynawo.orchestrator.model_setup import compute_rx_from_scr

        r, x = compute_rx_from_scr(3.0)
        assert math.hypot(r, x) == pytest.approx(1.0 / 3.0)

    def test_x_over_r_ratio_respected(self):
        from dycov.curves.dynawo.orchestrator.model_setup import compute_rx_from_scr

        r, x = compute_rx_from_scr(5.0, x_over_r=7.0)
        assert x / r == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# _get_line — remaining branches
# ---------------------------------------------------------------------------


class TestGetLineBranches:
    @patch(f"{_MS}.generator_variables")
    @patch(f"{_MS}.get_cfg_oc_name", return_value="SEC")
    @patch(f"{_MS}.config")
    def test_line_xpu_multiplier_with_symbolic_xtype(self, mock_config, mock_gcn, mock_gv):
        mock_config.has_option.side_effect = lambda s, k: k == "line_XPu"
        mock_config.get_value.return_value = "1.5*Xa"
        mock_gv.calculate_line_xpu.return_value = 0.2
        setup = _make_setup()

        _, xpu = setup._get_line("PCS1", "BM1", "OC1")

        assert xpu == pytest.approx(0.3)
        mock_gv.calculate_line_xpu.assert_called_once()
        assert mock_gv.calculate_line_xpu.call_args[0][0] == "Xa"

    @patch(f"{_MS}.get_cfg_oc_name", return_value="SEC")
    @patch(f"{_MS}.config")
    def test_scr_nonzero_computes_scaled_impedance(self, mock_config, mock_gcn):
        mock_config.has_option.side_effect = lambda s, k: k == "SCR"
        mock_config.get_float.side_effect = lambda s, k, d=None: {
            ("SEC.Model", "SCR"): 3.0,
            ("GridCode", "SCR_r_factor"): 10.0,
        }.get((s, k), d)
        setup = _make_setup()

        rpu, xpu = setup._get_line("PCS1", "BM1", "OC1")

        factor = math.sqrt(1 + 10.0**2)
        assert rpu == pytest.approx(1.0 / (factor * 3.0))
        assert xpu == pytest.approx(10.0 / (factor * 3.0))

    @patch(f"{_MS}.generator_variables")
    @patch(f"{_MS}.get_cfg_oc_name", return_value="SEC")
    @patch(f"{_MS}.config")
    def test_zcc_branch_derives_impedance_from_scc(self, mock_config, mock_gcn, mock_gv):
        mock_config.has_option.side_effect = lambda s, k: k == "Zcc"
        mock_config.get_float.side_effect = lambda s, k, d=None: (
            2.0 if k == "Ztanphi" else d
        )
        mock_gv.get_scc.return_value = 1000.0
        mock_gv.get_generator_u_dim.return_value = 20.0
        setup = _make_setup()

        rpu, xpu = setup._get_line("PCS1", "BM1", "OC1")

        zcc = 1.0**2 / (1000.0 / 100.0)
        expected_xpu = 2.0 * zcc / math.sqrt(1 + 4.0)
        assert xpu == pytest.approx(expected_xpu)
        assert rpu == pytest.approx(expected_xpu / 2.0)
        assert setup.has_line is True


# ---------------------------------------------------------------------------
# _sort_stepup_xfmrs_to_generators
# ---------------------------------------------------------------------------


class TestSortStepupXfmrs:
    def test_orders_xfmrs_by_generator_connection(self):
        gen_a = _make_gen()
        gen_a.terminals[0].connected_equipment = "XFMR_A"
        gen_b = _make_gen()
        gen_b.terminals[0].connected_equipment = "XFMR_B"
        producer = _make_producer(generators=[gen_a, gen_b])
        xfmr_a = MagicMock(id="XFMR_A")
        xfmr_b = MagicMock(id="XFMR_B")
        producer.stepup_xfmrs = [xfmr_b, xfmr_a]
        setup = _make_setup(_make_owner(producer))

        result = setup._sort_stepup_xfmrs_to_generators(producer)

        assert result == [xfmr_a, xfmr_b]


# ---------------------------------------------------------------------------
# _get_tso_loads / _complete_loads
# ---------------------------------------------------------------------------


class TestGetTsoLoads:
    @patch(f"{_MS}.model_parameters")
    def test_separates_pdr_and_grid_loads(self, mock_mp):
        setup = _make_setup()
        pdr_tso = MagicMock(id="L1")
        pdr_tso.terminals = [MagicMock(connected_equipment="BusPDR")]
        grid_tso = MagicMock(id="L2")
        grid_tso.terminals = [MagicMock(connected_equipment="Bus1")]
        setup.tso_loads = [pdr_tso, grid_tso]
        init_l1 = MagicMock(id="L1")
        init_l2 = MagicMock(id="L2")

        with patch.object(setup, "_complete_loads", return_value=[init_l1, init_l2]):
            setup._get_tso_loads("PCS1", "BM1", "OC1", u_dim=20.0)

        pdr_call, grid_call = mock_mp.get_grid_load.call_args_list
        assert pdr_call[0][0] == [init_l1]
        assert grid_call[0][0] == [init_l2]


class TestCompleteLoads:
    def test_numeric_load_values_parsed_directly(self):
        setup = _make_setup()
        load = MagicMock(id="L1", p="0.4", q="0.1", u="20.0", u_phase="0.5")
        setup.tso_loads = [load]

        result = setup._complete_loads("SEC", "BM1", "OC1", u_dim=20.0)

        assert len(result) == 1
        load_init = result[0]
        assert load_init.id == "L1"
        assert load_init.p0 == pytest.approx(0.4)
        assert load_init.q0 == pytest.approx(0.1)
        assert load_init.u0 == pytest.approx(1.0)  # 20.0 / u_nom 20.0
        assert load_init.u_phase0 == pytest.approx(0.5)

    @patch(f"{_MS}.model_parameters")
    @patch(f"{_MS}.config")
    def test_symbolic_load_values_resolved_from_config(self, mock_config, mock_mp):
        setup = _make_setup()
        load = MagicMock(id="L1", p="P0", q="0.1", u="20.0", u_phase="0.0")
        setup.tso_loads = [load]
        mock_config.get_value.return_value = "pmax*0.5"
        mock_mp.extract_defined_value.return_value = 0.7

        result = setup._complete_loads("SEC", "BM1", "OC1", u_dim=20.0)

        assert result[0].p0 == pytest.approx(0.7)
        mock_mp.extract_defined_value.assert_called_once_with("pmax*0.5", "pmax", 1.0)


# ---------------------------------------------------------------------------
# _calculate_xv_values
# ---------------------------------------------------------------------------


class TestCalculateXvValues:
    @patch(f"{_MS}.generator_variables")
    @patch(f"{_MS}.get_cfg_oc_name", return_value="SEC")
    @patch(f"{_MS}.config")
    def test_populates_xv_entries_from_u_options(self, mock_config, mock_gcn, mock_gv):
        setup = _make_setup()
        mock_gv.get_generator_type.return_value = "HTB1"
        mock_config.get_options.return_value = ["u_dip_HTB1", "unrelated_option"]
        mock_config.get_float.return_value = 0.5
        event_params = {}

        with patch.object(setup, "_calculate_xv", return_value=1.23):
            setup._calculate_xv_values(event_params, 0.1, 0.01, 1.0, "PCS1", "BM1", "OC1")

        assert event_params == {"Xv_dip": 1.23}


# ---------------------------------------------------------------------------
# _apply_reference_event_start_time
# ---------------------------------------------------------------------------


class TestApplyReferenceEventStartTime:
    def test_none_keeps_configured_value(self):
        setup = _make_setup()
        event_params = {"start_time": 20.0}

        setup._apply_reference_event_start_time(event_params, None)

        assert event_params["start_time"] == 20.0

    def test_equal_value_keeps_configured_value(self):
        setup = _make_setup()
        event_params = {"start_time": 20.0}

        setup._apply_reference_event_start_time(event_params, 20.0)

        assert event_params["start_time"] == 20.0

    def test_different_value_overrides_configured_value(self):
        setup = _make_setup()
        event_params = {"start_time": 20.0}

        setup._apply_reference_event_start_time(event_params, 30.0)

        assert event_params["start_time"] == 30.0
