#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023-2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import logging

import pytest

from dycov.model.parameters import GenParams, LineParams, LoadParams, Terminal, XfmrParams
from dycov.sanity_checks import parameter_checks

PRE_EVENT_TOLERANCE = 0.005


def test_trafos():
    xfmr = XfmrParams(
        id=None,
        lib=None,
        r=0.0003,
        x=0.0268,
        b=0.0,
        g=0.0,
        r_tfo=0.9574,
        alpha_tfo=0.0,
        par_id="",
        terminals=(
            Terminal(connected_equipment=None),
            Terminal(connected_equipment=None),
        ),
    )
    parameter_checks.check_trafo(xfmr)

    bad_xfmr = XfmrParams(
        id="Xfmr",
        lib=None,
        r=0.0003,
        x=-0.0268,
        b=0.0,
        g=0.0,
        r_tfo=0.9574,
        alpha_tfo=0.0,
        par_id="",
        terminals=(
            Terminal(connected_equipment=None),
            Terminal(connected_equipment=None),
        ),
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_trafo(bad_xfmr)
    assert pytest_wrapped_e.type is ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The reactance of the transformer Xfmr must be greater than zero."
    )


def test_trafo_with_a_non_zero_alpha():
    xfmr = XfmrParams(
        id="Xfmr",
        lib=None,
        r=0.0003,
        x=0.0268,
        b=0.0,
        g=0.0,
        r_tfo=0.9574,
        alpha_tfo=1.0,
        par_id="",
        terminals=(
            Terminal(connected_equipment=None),
            Terminal(connected_equipment=None),
        ),
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_trafo(xfmr)
    assert pytest_wrapped_e.type is ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The alphaTfo parameter of the transformer Xfmr must be equal to zero."
    )


def test_check_trafo_none():
    """Test check_trafo with None transformer."""
    parameter_checks.check_trafo(None)


def test_auxiliary_loads():
    load = LoadParams(
        id=None,
        lib=None,
        p=0.1,
        q=0.05,
        u=1.0,
        u_phase=0.0,
        alpha=None,
        beta=None,
        par_id=None,
        terminals=(Terminal(connected_equipment=None),),
    )
    parameter_checks.check_auxiliary_load(load)

    bad_load = LoadParams(
        id=None,
        lib=None,
        p=-0.1,
        q=0.05,
        u=1.0,
        u_phase=0.0,
        alpha=None,
        beta=None,
        par_id=None,
        terminals=(Terminal(connected_equipment=None),),
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_auxiliary_load(bad_load)
    assert pytest_wrapped_e.type is ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The active flow of the auxiliary load must be greater than zero."
    )


def test_generators():
    sm = GenParams(
        id=None,
        lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
        terminals=(Terminal(connected_equipment=""),),
        s_nom=90,
        i_max=100.0,
        par_id="",
        p=0.1,
        q=0.05,
        voltage_droop=None,
        use_voltage_droop=False,
    )
    ppm = GenParams(
        id=None,
        lib="WTG4AWeccCurrentSource",
        terminals=(Terminal(connected_equipment=""),),
        s_nom=90,
        i_max=100.0,
        par_id="",
        p=0.1,
        q=0.05,
        voltage_droop=None,
        use_voltage_droop=False,
    )
    bess = GenParams(
        id=None,
        lib="BESSWeccCurrentSource",
        terminals=(Terminal(connected_equipment=""),),
        s_nom=90,
        i_max=100.0,
        par_id="",
        p=0.1,
        q=0.05,
        voltage_droop=None,
        use_voltage_droop=False,
    )
    sm_models, ppm_models, bess_models = parameter_checks.check_generators([sm])
    assert sm_models == 1
    assert ppm_models == 0
    assert bess_models == 0
    sm_models, ppm_models, bess_models = parameter_checks.check_generators([ppm])
    assert sm_models == 0
    assert ppm_models == 1
    assert bess_models == 0
    sm_models, ppm_models, bess_models = parameter_checks.check_generators([bess])
    assert sm_models == 0
    assert ppm_models == 0
    assert bess_models == 1

    with pytest.raises(ValueError) as pytest_wrapped_e:
        sm_models, ppm_models, bess_models = parameter_checks.check_generators([sm, ppm])
    assert pytest_wrapped_e.type is ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The supplied network contains two or more different generator model types."
    )


def test_internal_lines():
    line = LineParams(
        id="Line",
        lib=None,
        r=0.02,
        x=0.004,
        b=0.0,
        g=0.0,
        par_id="",
        terminals=(
            Terminal(connected_equipment=None),
            Terminal(connected_equipment=None),
        ),
    )
    parameter_checks.check_internal_line(line)

    bad_line = LineParams(
        id="Line",
        lib=None,
        r=-0.02,
        x=0.004,
        b=0.0,
        g=0.0,
        par_id="",
        terminals=(
            Terminal(connected_equipment=None),
            Terminal(connected_equipment=None),
        ),
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_internal_line(bad_line)
    assert pytest_wrapped_e.type is ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The resistance and reactance of the internal line must be greater than zero."
    )


def test_producer_params_consistency():
    gen1 = GenParams(
        id=None,
        lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
        terminals=(Terminal(connected_equipment=""),),
        s_nom=90,
        i_max=100.0,
        par_id="",
        p=0.1,
        q=0.05,
        voltage_droop=None,
        use_voltage_droop=False,
        p_max=0.5,
        q_max=0.3,
        q_min=-0.3,
    )
    gen2 = GenParams(
        id=None,
        lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
        terminals=(Terminal(connected_equipment=""),),
        s_nom=90,
        i_max=100.0,
        par_id="",
        p=0.1,
        q=0.05,
        voltage_droop=None,
        use_voltage_droop=False,
        p_max=0.5,
        q_max=0.3,
        q_min=-0.3,
    )
    parameter_checks.check_producer_params_consistency(
        [gen1, gen2], p_max_pu=0.8, q_max_pu=0.5, q_min_pu=-0.5
    )

    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_producer_params_consistency(
            [gen1, gen2], p_max_pu=1.0, q_max_pu=0.5, q_min_pu=-0.5
        )
    assert pytest_wrapped_e.type is ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "Inconsistency detected: INI values are less restrictive than PAR values."
    )

    gen_none = GenParams(
        id=None,
        lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
        terminals=(Terminal(connected_equipment=""),),
        s_nom=90,
        i_max=100.0,
        par_id="",
        p=0.1,
        q=0.05,
        voltage_droop=None,
        use_voltage_droop=False,
        p_max=None,
        q_max=None,
        q_min=None,
    )
    parameter_checks.check_producer_params_consistency(
        [gen_none], p_max_pu=0.5, q_max_pu=0.5, q_min_pu=-0.3
    )

    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_producer_params_consistency(
            [gen1], p_max_pu=0.5, q_max_pu=0.5, q_min_pu=-0.3
        )
    assert pytest_wrapped_e.type is ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "Inconsistency detected: INI values are less restrictive than PAR values."
    )


def test_check_generators_with_zone3():
    sm = GenParams(
        id=None,
        lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
        terminals=(Terminal(connected_equipment=""),),
        s_nom=90,
        i_max=100.0,
        par_id="",
        p=0.1,
        q=0.05,
        voltage_droop=None,
        use_voltage_droop=False,
    )
    sm_models, ppm_models, bess_models = parameter_checks.check_generators([sm], [sm])
    assert sm_models == 2
    assert ppm_models == 0
    assert bess_models == 0

    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_generators([sm], [sm, sm])
    assert pytest_wrapped_e.type is ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The model validation must contain the same number of generators in both zones."
    )


def test_check_generators_zone3_different_types():
    sm = GenParams(
        id=None,
        lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
        terminals=(Terminal(connected_equipment=""),),
        s_nom=90,
        i_max=100.0,
        par_id="",
        p=0.1,
        q=0.05,
        voltage_droop=None,
        use_voltage_droop=False,
    )
    ppm = GenParams(
        id=None,
        lib="WTG4AWeccCurrentSource",
        terminals=(Terminal(connected_equipment=""),),
        s_nom=90,
        i_max=100.0,
        par_id="",
        p=0.1,
        q=0.05,
        voltage_droop=None,
        use_voltage_droop=False,
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_generators([sm], [ppm])
    assert pytest_wrapped_e.type is ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The supplied network contains two or more different generator model types."
    )


def test_check_t_fault():
    """Test check_t_fault function."""
    # Should not raise any warning when event_time - start_time >= range_len
    parameter_checks.check_t_fault(start_time=0.0, event_time=5.0, range_len=5.0)
    parameter_checks.check_t_fault(start_time=0.0, event_time=10.0, range_len=5.0)


@pytest.fixture
def sanity_check_warnings(monkeypatch, caplog):
    """Capture the warnings emitted by the sanity checks under a known steady-state tolerance."""
    monkeypatch.setattr(
        "dycov.configuration.cfg.Config.get_float",
        lambda self, section, key, default: PRE_EVENT_TOLERANCE,
    )
    monkeypatch.setattr("dycov.logging.dycov_logging.get_logger", logging.getLogger)
    caplog.set_level(logging.WARNING)
    return caplog


def _pre_event_window(values: list[float]) -> tuple[list[float], list[float]]:
    return [sample * 0.01 for sample in range(len(values))], values


def test_check_t_fault_warns_on_a_short_pre_event_window(sanity_check_warnings):
    """An event triggered before the required range has elapsed must be reported."""
    parameter_checks.check_t_fault(start_time=0.0, event_time=2.0, range_len=5.0)

    assert any(
        "The event is triggered before 5.0 seconds have elapsed" in record.message
        for record in sanity_check_warnings.records
    )


def test_check_pre_stable_warns_on_an_unstable_pre_event_curve(sanity_check_warnings):
    """An oscillation wider than the steady-state band must be reported as unstable, even
    though its amplitude is far below the several-second span of the window."""
    time, curve = _pre_event_window([1.0 + 0.05 * (-1) ** sample for sample in range(200)])

    parameter_checks.check_pre_stable(time, curve)

    assert any(
        "Unstable curve before the event is triggered." in record.message
        for record in sanity_check_warnings.records
    )


def test_check_pre_stable_of_a_settled_pre_event_curve(sanity_check_warnings):
    """A ripple inside the steady-state band must not be reported."""
    time, curve = _pre_event_window([1.0 + 0.001 * (-1) ** sample for sample in range(200)])

    parameter_checks.check_pre_stable(time, curve)

    assert not sanity_check_warnings.records


def test_check_sampling_interval():
    """Test check_sampling_interval function."""
    # Valid sampling interval
    parameter_checks.check_sampling_interval(sampling_interval=0.001, cutoff=100.0)

    # Invalid sampling interval
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_sampling_interval(sampling_interval=0.01, cutoff=50.0)
    assert pytest_wrapped_e.type is ValueError
    assert "Unexpected sampling interval" in pytest_wrapped_e.value.args[0]


def test_check_producer_params(monkeypatch):
    """Test check_producer_params function."""

    # Mock config to return valid voltage dimensions
    def mock_get_list(self, section, key):
        if "Udims" in key:
            return ["380"]
        return []

    monkeypatch.setattr("dycov.configuration.cfg.Config.get_list", mock_get_list)

    # Valid parameters
    parameter_checks.check_producer_params(
        p_max_injection_pu=100.0, p_max_consumption_pu=50.0, u_nom=380
    )

    # Invalid p_max_injection_pu
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_producer_params(
            p_max_injection_pu=-1.0, p_max_consumption_pu=50.0, u_nom=380
        )
    assert (
        "maximum active power generation must be greater or equal than 0"
        in pytest_wrapped_e.value.args[0]
    )

    # Invalid p_max_consumption_pu
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_producer_params(
            p_max_injection_pu=100.0, p_max_consumption_pu=-1.0, u_nom=380
        )
    assert (
        "maximum active power consumption must be greater or equal than 0"
        in pytest_wrapped_e.value.args[0]
    )

    # Invalid u_nom
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_producer_params(
            p_max_injection_pu=100.0, p_max_consumption_pu=50.0, u_nom=999
        )
    assert "Unexpected nominal voltage" in pytest_wrapped_e.value.args[0]

    # Zone 1 has no PDR: an out-of-list u_nom must not raise
    parameter_checks.check_producer_params(
        p_max_injection_pu=100.0, p_max_consumption_pu=50.0, u_nom=999, zone=1
    )

    # Zone 3 is the PDR: the check still applies there
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_producer_params(
            p_max_injection_pu=100.0, p_max_consumption_pu=50.0, u_nom=999, zone=3
        )
    assert "Unexpected nominal voltage" in pytest_wrapped_e.value.args[0]


def test_check_simulation_duration():
    """Test check_simulation_duration function."""
    # Should not raise warning for sufficient duration
    parameter_checks.check_simulation_duration(time=100.0)

    # Should warn for short duration
    parameter_checks.check_simulation_duration(time=30.0)


def test_check_solver():
    """Test check_solver function."""
    # Valid solvers
    parameter_checks.check_solver(id="dynawo_SolverIDA", lib="dynawo_SolverIDA")
    parameter_checks.check_solver(id="dynawo_SolverSIM", lib="dynawo_SolverSIM")

    # Invalid library
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_solver(id="dynawo_SolverIDA", lib="invalid_solver")
    assert "solver library is not available" in pytest_wrapped_e.value.args[0]

    # Invalid id
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_solver(id="invalid_id", lib="dynawo_SolverIDA")
    assert "solver id is incorrect" in pytest_wrapped_e.value.args[0]


def test_check_auxiliary_load_with_alpha_beta_warning():
    """Test check_auxiliary_load with alpha and beta both zero."""
    load = LoadParams(
        id=None,
        lib=None,
        p=0.1,
        q=0.05,
        u=1.0,
        u_phase=0.0,
        alpha=0,
        beta=0,
        par_id=None,
        terminals=(Terminal(connected_equipment=None),),
    )
    parameter_checks.check_auxiliary_load(load)


def test_check_auxiliary_load_none():
    """Test check_auxiliary_load with None load."""
    parameter_checks.check_auxiliary_load(load=None)


def test_check_trafos():
    """Test check_trafos function."""
    xfmr = XfmrParams(
        id="Xfmr1",
        lib=None,
        r=0.0003,
        x=0.0268,
        b=0.0,
        g=0.0,
        r_tfo=0.9574,
        alpha_tfo=0.0,
        par_id="",
        terminals=(
            Terminal(connected_equipment=None),
            Terminal(connected_equipment=None),
        ),
    )
    parameter_checks.check_trafos([xfmr])


def test_check_internal_line_none():
    """Test check_internal_line with None line."""
    parameter_checks.check_internal_line(line=None)


def _tap_changer(id: str) -> XfmrParams:
    return XfmrParams(
        id=id,
        lib="TransformerRatioTapChanger",
        r=0.0003,
        x=0.0268,
        b=0.0,
        g=0.0,
        r_tfo=1.0,
        alpha_tfo=0.0,
        par_id=id,
        terminals=(
            Terminal(connected_equipment=None),
            Terminal(connected_equipment=None),
        ),
    )


@pytest.mark.parametrize("xfmr_id", ["Main_Xfmr", "Group_Xfmr", "AuxLoad_Xfmr"])
def test_check_trafo_accepts_a_tap_changer_on_any_transformer(xfmr_id):
    """RTE allows either transformer model on any block of the topology."""
    parameter_checks.check_trafo(_tap_changer(xfmr_id))
