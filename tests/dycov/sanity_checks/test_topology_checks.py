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

from dycov.model.parameters import GenParams, LineParams, LoadParams, Terminal, XfmrParams
from dycov.sanity_checks import topology_checks


# -------------------------
# Helper functions
# -------------------------
def make_generator(gen_type="S"):
    if gen_type == "S":
        return [
            GenParams(
                id="Synch_Gen",
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
        ]
    elif gen_type == "M":
        return [
            GenParams(
                id="Wind_Turbine1",
                lib="WTG4AWeccCurrentSource1",
                terminals=(Terminal(connected_equipment=""),),
                s_nom=90,
                i_max=100.0,
                par_id="",
                p=0.1,
                q=0.05,
                voltage_droop=None,
                use_voltage_droop=False,
            ),
            GenParams(
                id="Wind_Turbine2",
                lib="WTG4AWeccCurrentSource1",
                terminals=(Terminal(connected_equipment=""),),
                s_nom=90,
                i_max=120.0,
                par_id="",
                p=0.12,
                q=0.025,
                voltage_droop=None,
                use_voltage_droop=False,
            ),
        ]


def make_transformers(topology="S"):
    if topology == "S":
        return [
            XfmrParams(
                id="StepUp_Xfmr",
                lib=None,
                r=0.0003,
                x=0.0268,
                b=0.0,
                g=0.0,
                r_tfo=0.9574,
                alpha_tfo=0.0,
                par_id="",
                terminals=(Terminal(connected_equipment=""), Terminal(connected_equipment="")),
            )
        ]
    elif topology == "M":
        return [
            XfmrParams(
                id="StepUp_Xfmr1",
                lib=None,
                r=0.0003,
                x=0.0268,
                b=0.0,
                g=0.0,
                r_tfo=0.9574,
                alpha_tfo=0.0,
                par_id="",
                terminals=(Terminal(connected_equipment=""), Terminal(connected_equipment="")),
            ),
            XfmrParams(
                id="StepUp_Xfmr2",
                lib=None,
                r=0.0003,
                x=0.0268,
                b=0.0,
                g=0.0,
                r_tfo=0.9574,
                alpha_tfo=0.0,
                par_id="",
                terminals=(Terminal(connected_equipment=""), Terminal(connected_equipment="")),
            ),
        ]


def make_main_transformer():
    return XfmrParams(
        id="Main_Xfmr",
        lib=None,
        r=0.0003,
        x=0.0268,
        b=0.0,
        g=0.0,
        r_tfo=0.9574,
        alpha_tfo=0.0,
        par_id="",
        terminals=(Terminal(connected_equipment=""), Terminal(connected_equipment="")),
    )


def make_auxiliary_load():
    return LoadParams(
        id="Aux_Load",
        lib=None,
        par_id="",
        terminals=(Terminal(connected_equipment=""),),
        p=0.1,
        q=0.05,
        u=1.0,
        u_phase=0.0,
        alpha=None,
        beta=None,
    )


def make_auxiliary_transformer():
    return XfmrParams(
        id="AuxLoad_Xfmr",
        lib=None,
        r=0.0003,
        x=0.0268,
        b=0.0,
        g=0.0,
        r_tfo=0.9574,
        alpha_tfo=0.0,
        par_id="",
        terminals=(Terminal(connected_equipment=""), Terminal(connected_equipment="")),
    )


def make_internal_line():
    return LineParams(
        id="IntNetwork_Line",
        lib=None,
        r=0.01,
        x=0.01,
        b=0.1,
        g=0.3,
        par_id="",
        terminals=(Terminal(connected_equipment=""), Terminal(connected_equipment="")),
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
