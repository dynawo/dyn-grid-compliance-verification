#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023-2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import pytest

from dycov.model.parameters import Gen_params, Line_params, Load_params, Terminal, Xfmr_params
from dycov.sanity_checks import parameter_checks


def test_trafos():
    xfmr = Xfmr_params(
        id=None,
        lib=None,
        R=0.0003,
        X=0.0268,
        B=0.0,
        G=0.0,
        rTfo=0.9574,
        par_id="",
        terminals=(
            Terminal(connectedEquipment=None),
            Terminal(connectedEquipment=None),
        ),
    )
    parameter_checks.check_trafo(xfmr)

    bad_xfmr = Xfmr_params(
        id="Xfmr",
        lib=None,
        R=0.0003,
        X=-0.0268,
        B=0.0,
        G=0.0,
        rTfo=0.9574,
        par_id="",
        terminals=(
            Terminal(connectedEquipment=None),
            Terminal(connectedEquipment=None),
        ),
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_trafo(bad_xfmr)
    assert pytest_wrapped_e.type == ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The admittance of the transformer Xfmr must be greater than zero."
    )


def test_auxiliary_loads():
    load = Load_params(
        id=None,
        lib=None,
        P=0.1,
        Q=0.05,
        U=1.0,
        UPhase=0.0,
        Alpha=None,
        Beta=None,
        par_id=None,
        terminals=(Terminal(connectedEquipment=None),),
    )
    parameter_checks.check_auxiliary_load(load)

    bad_load = Load_params(
        id=None,
        lib=None,
        P=-0.1,
        Q=0.05,
        U=1.0,
        UPhase=0.0,
        Alpha=None,
        Beta=None,
        par_id=None,
        terminals=(Terminal(connectedEquipment=None),),
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_auxiliary_load(bad_load)
    assert pytest_wrapped_e.type == ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The active flow of the auxiliary load must be greater than zero."
    )


def test_generators():
    sm = Gen_params(
        id=None,
        lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
        terminals=(Terminal(connectedEquipment=""),),
        SNom=90,
        IMax=100.0,
        par_id="",
        P=0.1,
        Q=0.05,
        VoltageDroop=None,
        UseVoltageDroop=False,
    )
    ppm = Gen_params(
        id=None,
        lib="WTG4AWeccCurrentSource1",
        terminals=(Terminal(connectedEquipment=""),),
        SNom=90,
        IMax=100.0,
        par_id="",
        P=0.1,
        Q=0.05,
        VoltageDroop=None,
        UseVoltageDroop=False,
    )
    bess = Gen_params(
        id=None,
        lib="BESSWeccCurrentSource",
        terminals=(Terminal(connectedEquipment=""),),
        SNom=90,
        IMax=100.0,
        par_id="",
        P=0.1,
        Q=0.05,
        VoltageDroop=None,
        UseVoltageDroop=False,
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
    assert pytest_wrapped_e.type == ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The supplied network contains two or more different generator model types."
    )


def test_internal_lines():
    line = Line_params(
        id="Line",
        lib=None,
        R=0.02,
        X=0.004,
        B=0.0,
        G=0.0,
        par_id="",
        terminals=(
            Terminal(connectedEquipment=None),
            Terminal(connectedEquipment=None),
        ),
    )
    parameter_checks.check_internal_line(line)

    bad_line = Line_params(
        id="Line",
        lib=None,
        R=-0.02,
        X=0.004,
        B=0.0,
        G=0.0,
        par_id="",
        terminals=(
            Terminal(connectedEquipment=None),
            Terminal(connectedEquipment=None),
        ),
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_internal_line(bad_line)
    assert pytest_wrapped_e.type == ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The reactance and admittance of the internal line must be greater than zero."
    )


def test_producer_params_consistency():
    gen1 = Gen_params(
        id=None,
        lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
        terminals=(Terminal(connectedEquipment=""),),
        SNom=90,
        IMax=100.0,
        par_id="",
        P=0.1,
        Q=0.05,
        VoltageDroop=None,
        UseVoltageDroop=False,
        PMax=0.5,
        QMax=0.3,
        QMin=-0.3,
    )
    gen2 = Gen_params(
        id=None,
        lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
        terminals=(Terminal(connectedEquipment=""),),
        SNom=90,
        IMax=100.0,
        par_id="",
        P=0.1,
        Q=0.05,
        VoltageDroop=None,
        UseVoltageDroop=False,
        PMax=0.5,
        QMax=0.3,
        QMin=-0.3,
    )
    parameter_checks.check_producer_params_consistency(
        [gen1, gen2], p_max_pu=1.0, q_max_pu=0.6, q_min_pu=-0.6
    )

    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_producer_params_consistency(
            [gen1, gen2], p_max_pu=1.2, q_max_pu=0.6, q_min_pu=-0.6
        )
    assert pytest_wrapped_e.type == ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "Inconsistency detected: INI values are less restrictive than PAR values."
    )

    gen_none = Gen_params(
        id=None,
        lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
        terminals=(Terminal(connectedEquipment=""),),
        SNom=90,
        IMax=100.0,
        par_id="",
        P=0.1,
        Q=0.05,
        VoltageDroop=None,
        UseVoltageDroop=False,
        PMax=None,
        QMax=None,
        QMin=None,
    )
    parameter_checks.check_producer_params_consistency(
        [gen_none], p_max_pu=0.5, q_max_pu=0.5, q_min_pu=-0.3
    )

    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_producer_params_consistency(
            [gen1], p_max_pu=0.5, q_max_pu=0.5, q_min_pu=-0.3
        )
    assert pytest_wrapped_e.type == ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "Inconsistency detected: INI values are less restrictive than PAR values."
    )


def test_check_generators_with_zone3():
    sm = Gen_params(
        id=None,
        lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
        terminals=(Terminal(connectedEquipment=""),),
        SNom=90,
        IMax=100.0,
        par_id="",
        P=0.1,
        Q=0.05,
        VoltageDroop=None,
        UseVoltageDroop=False,
    )
    sm_models, ppm_models, bess_models = parameter_checks.check_generators([sm], [sm])
    assert sm_models == 2
    assert ppm_models == 0
    assert bess_models == 0

    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_generators([sm], [sm, sm])
    assert pytest_wrapped_e.type == ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The model validation must contain the same number of generators in both zones."
    )


def test_check_generators_zone3_different_types():
    sm = Gen_params(
        id=None,
        lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
        terminals=(Terminal(connectedEquipment=""),),
        SNom=90,
        IMax=100.0,
        par_id="",
        P=0.1,
        Q=0.05,
        VoltageDroop=None,
        UseVoltageDroop=False,
    )
    ppm = Gen_params(
        id=None,
        lib="WTG4AWeccCurrentSource1",
        terminals=(Terminal(connectedEquipment=""),),
        SNom=90,
        IMax=100.0,
        par_id="",
        P=0.1,
        Q=0.05,
        VoltageDroop=None,
        UseVoltageDroop=False,
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_generators([sm], [ppm])
    assert pytest_wrapped_e.type == ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The supplied network contains two or more different generator model types."
    )


def test_check_t_fault():
    """Test check_t_fault function."""
    # Should not raise any warning when event_time - start_time >= range_len
    parameter_checks.check_t_fault(start_time=0.0, event_time=5.0, range_len=5.0)
    parameter_checks.check_t_fault(start_time=0.0, event_time=10.0, range_len=5.0)


def test_check_sampling_interval():
    """Test check_sampling_interval function."""
    # Valid sampling interval
    parameter_checks.check_sampling_interval(sampling_interval=0.001, cutoff=100.0)

    # Invalid sampling interval
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_sampling_interval(sampling_interval=0.01, cutoff=50.0)
    assert pytest_wrapped_e.type == ValueError
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
    load = Load_params(
        id=None,
        lib=None,
        P=0.1,
        Q=0.05,
        U=1.0,
        UPhase=0.0,
        Alpha=0,
        Beta=0,
        par_id=None,
        terminals=(Terminal(connectedEquipment=None),),
    )
    parameter_checks.check_auxiliary_load(load)


def test_check_auxiliary_load_none():
    """Test check_auxiliary_load with None load."""
    parameter_checks.check_auxiliary_load(load=None)


def test_check_trafos():
    """Test check_trafos function."""
    xfmr = Xfmr_params(
        id="Xfmr1",
        lib=None,
        R=0.0003,
        X=0.0268,
        B=0.0,
        G=0.0,
        rTfo=0.9574,
        par_id="",
        terminals=(
            Terminal(connectedEquipment=None),
            Terminal(connectedEquipment=None),
        ),
    )
    parameter_checks.check_trafos([xfmr])


def test_check_internal_line_none():
    """Test check_internal_line with None line."""
    parameter_checks.check_internal_line(line=None)
