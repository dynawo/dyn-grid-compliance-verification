#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#
import pytest

from dycov.model import parameters
from dycov.sanity_checks import topology_checks


# -------------------------
# Helper functions
# -------------------------
def make_generator(gen_type="S"):
    if gen_type == "S":
        return [
            parameters.Gen_params(
                id="Synch_Gen",
                lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a",
                connectedXmfr="",
                SNom=90,
                IMax=100.0,
                par_id="",
                P=0.1,
                Q=0.05,
                VoltageDroop=None,
                UseVoltageDroop=False,
            )
        ]
    elif gen_type == "M":
        return [
            parameters.Gen_params(
                id="Wind_Turbine1",
                lib="WTG4AWeccCurrentSource1",
                connectedXmfr="",
                SNom=90,
                IMax=100.0,
                par_id="",
                P=0.1,
                Q=0.05,
                VoltageDroop=None,
                UseVoltageDroop=False,
            ),
            parameters.Gen_params(
                id="Wind_Turbine2",
                lib="WTG4AWeccCurrentSource1",
                connectedXmfr="",
                SNom=90,
                IMax=120.0,
                par_id="",
                P=0.12,
                Q=0.025,
                VoltageDroop=None,
                UseVoltageDroop=False,
            ),
        ]


def make_transformers(topology="S"):
    if topology == "S":
        return [
            parameters.Xfmr_params(
                id="StepUp_Xfmr",
                lib=None,
                R=0.0003,
                X=0.0268,
                B=0.0,
                G=0.0,
                rTfo=0.9574,
                par_id="",
            )
        ]
    elif topology == "M":
        return [
            parameters.Xfmr_params(
                id="StepUp_Xfmr1",
                lib=None,
                R=0.0003,
                X=0.0268,
                B=0.0,
                G=0.0,
                rTfo=0.9574,
                par_id="",
            ),
            parameters.Xfmr_params(
                id="StepUp_Xfmr2",
                lib=None,
                R=0.0003,
                X=0.0268,
                B=0.0,
                G=0.0,
                rTfo=0.9574,
                par_id="",
            ),
        ]


def make_main_transformer():
    return parameters.Xfmr_params(
        id="Main_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
    )


def make_auxiliary_load():
    return parameters.Load_params(
        id="Aux_Load",
        lib=None,
        connectedXmfr="",
        P=0.1,
        Q=0.05,
        U=1.0,
        UPhase=0.0,
        Alpha=None,
        Beta=None,
    )


def make_auxiliary_transformer():
    return parameters.Xfmr_params(
        id="AuxLoad_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
    )


def make_internal_line():
    return parameters.Line_params(
        id="IntNetwork_Line", lib=None, connectedPdr=None, R=0.01, X=0.01, B=0.1, G=0.3
    )


def _assert_error_contains(pytest_wrapped_e, topology_name):
    message = pytest_wrapped_e.value.args[0]
    assert f"The '{topology_name}' topology expects" in message
    assert (
        "internal line" in message
        or "StepUp_Xfmr" in message
        or "AuxLoad_Xfmr" in message
        or "Main_Xfmr" in message
    )


# -------------------------
# Tests
# -------------------------


# Expected fail tests for S topologies
def test_check_topology_s_expected_fail():
    generators = make_generator("S")
    transformers = make_transformers("S")
    internal_line = make_internal_line()
    with pytest.raises(ValueError) as e:
        topology_checks.check_topology(
            "S", generators, transformers, None, None, None, internal_line
        )
    _assert_error_contains(e, "S")


def test_check_topology_si_expected_fail():
    generators = make_generator("S")
    transformers = make_transformers("S")
    with pytest.raises(ValueError) as e:
        topology_checks.check_topology("S+i", generators, transformers, None, None, None, None)
    _assert_error_contains(e, "S+i")


def test_check_topology_saux_expected_fail():
    generators = make_generator("S")
    transformers = make_transformers("S")
    aux_load = make_auxiliary_load()
    aux_transformer = make_auxiliary_transformer()
    internal_line = make_internal_line()
    with pytest.raises(ValueError) as e:
        topology_checks.check_topology(
            "S+Aux", generators, transformers, aux_load, aux_transformer, None, internal_line
        )
    _assert_error_contains(e, "S+Aux")


def test_check_topology_sauxi_expected_fail():
    generators = make_generator("S")
    transformers = make_transformers("S")
    aux_load = make_auxiliary_load()
    aux_transformer = make_auxiliary_transformer()
    with pytest.raises(ValueError) as e:
        topology_checks.check_topology(
            "S+Aux+i", generators, transformers, aux_load, aux_transformer, None, None
        )
    _assert_error_contains(e, "S+Aux+i")


# Expected fail tests for M topologies
def test_check_topology_m_expected_fail():
    generators = make_generator("M")
    transformers = make_transformers("M")
    main_transformer = make_main_transformer()
    internal_line = make_internal_line()
    with pytest.raises(ValueError) as e:
        topology_checks.check_topology(
            "M", generators, transformers, None, None, main_transformer, internal_line
        )
    _assert_error_contains(e, "M")


def test_check_topology_mi_expected_fail():
    generators = make_generator("M")
    transformers = make_transformers("M")
    main_transformer = make_main_transformer()
    with pytest.raises(ValueError) as e:
        topology_checks.check_topology(
            "M+i", generators, transformers, None, None, main_transformer, None
        )
    _assert_error_contains(e, "M+i")


def test_check_topology_maux_expected_fail():
    generators = make_generator("M")
    transformers = make_transformers("M")
    aux_load = make_auxiliary_load()
    aux_transformer = make_auxiliary_transformer()
    main_transformer = make_main_transformer()
    internal_line = make_internal_line()
    with pytest.raises(ValueError) as e:
        topology_checks.check_topology(
            "M+Aux",
            generators,
            transformers,
            aux_load,
            aux_transformer,
            main_transformer,
            internal_line,
        )
    _assert_error_contains(e, "M+Aux")


def test_check_topology_mauxi_expected_fail():
    generators = make_generator("M")
    transformers = make_transformers("M")
    aux_load = make_auxiliary_load()
    aux_transformer = make_auxiliary_transformer()
    main_transformer = make_main_transformer()
    with pytest.raises(ValueError) as e:
        topology_checks.check_topology(
            "M+Aux+i", generators, transformers, aux_load, aux_transformer, main_transformer, None
        )
    _assert_error_contains(e, "M+Aux+i")


# Success tests for S topologies
def test_check_topology_S_success():
    generators = make_generator("S")
    transformers = make_transformers("S")
    topology_checks.check_topology("S", generators, transformers, None, None, None, None)


def test_check_topology_Si_success():
    generators = make_generator("S")
    transformers = make_transformers("S")
    internal_line = make_internal_line()
    topology_checks.check_topology(
        "S+i", generators, transformers, None, None, None, internal_line
    )


def test_check_topology_SAux_success():
    generators = make_generator("S")
    transformers = make_transformers("S")
    aux_load = make_auxiliary_load()
    aux_transformer = make_auxiliary_transformer()
    topology_checks.check_topology(
        "S+Aux", generators, transformers, aux_load, aux_transformer, None, None
    )


def test_check_topology_SAuxi_success():
    generators = make_generator("S")
    transformers = make_transformers("S")
    aux_load = make_auxiliary_load()
    aux_transformer = make_auxiliary_transformer()
    internal_line = make_internal_line()
    topology_checks.check_topology(
        "S+Aux+i", generators, transformers, aux_load, aux_transformer, None, internal_line
    )


# Success tests for M topologies
def test_check_topology_M_success():
    generators = make_generator("M")
    transformers = make_transformers("M")
    main_transformer = make_main_transformer()
    topology_checks.check_topology(
        "M", generators, transformers, None, None, main_transformer, None
    )


def test_check_topology_Mi_success():
    generators = make_generator("M")
    transformers = make_transformers("M")
    main_transformer = make_main_transformer()
    internal_line = make_internal_line()
    topology_checks.check_topology(
        "M+i", generators, transformers, None, None, main_transformer, internal_line
    )


def test_check_topology_MAux_success():
    generators = make_generator("M")
    transformers = make_transformers("M")
    aux_load = make_auxiliary_load()
    aux_transformer = make_auxiliary_transformer()
    main_transformer = make_main_transformer()
    topology_checks.check_topology(
        "M+Aux", generators, transformers, aux_load, aux_transformer, main_transformer, None
    )


def test_check_topology_MAuxi_success():
    generators = make_generator("M")
    transformers = make_transformers("M")
    aux_load = make_auxiliary_load()
    aux_transformer = make_auxiliary_transformer()
    main_transformer = make_main_transformer()
    internal_line = make_internal_line()
    topology_checks.check_topology(
        "M+Aux+i",
        generators,
        transformers,
        aux_load,
        aux_transformer,
        main_transformer,
        internal_line,
    )
