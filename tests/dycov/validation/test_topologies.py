#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import pytest

from dycov.model import parameters
from dycov.validation import sanity_checks


def test_check_topology_s():
    generators = [
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
            equiv_int_line=None,
        )
    ]
    transformers = [
        parameters.Xfmr_params(
            id="StepUp_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
        )
    ]
    auxiliary_load = None
    auxiliary_transformer = None
    transformer = None
    internal_line = None
    sanity_checks.check_topology(
        "S",
        generators,
        transformers,
        auxiliary_load,
        auxiliary_transformer,
        transformer,
        internal_line,
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        sanity_checks.check_topology(
            "S+i",
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    assert pytest_wrapped_e.type == ValueError
    assert pytest_wrapped_e.value.args[0] == (
        "The 'S+i' topology expects the following models:\n"
        "  - A generator with id:\n"
        "      * 'Synch_Gen' if a synchronous generator is modeled\n"
        "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
        "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
        "      * 'Bess' if a storage or a park of storages is modeled\n"
        "  - A transformer with id 'StepUp_Xfmr' connected between the generator and the "
        "internal line\n"
        "  - An internal line with id 'IntNetwork_Line' connected between the transformer "
        "and the PDR bus\n"
    )


def test_check_topology_si():
    generators = [
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
            equiv_int_line=None,
        )
    ]
    transformers = [
        parameters.Xfmr_params(
            id="StepUp_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
        )
    ]
    auxiliary_load = None
    auxiliary_transformer = None
    transformer = None
    internal_line = parameters.Line_params(
        id="IntNetwork_Line", lib=None, connectedPdr=None, R=0.01, X=0.01, B=0.1, G=0.3
    )
    sanity_checks.check_topology(
        "S+i",
        generators,
        transformers,
        auxiliary_load,
        auxiliary_transformer,
        transformer,
        internal_line,
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        sanity_checks.check_topology(
            "S",
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    assert pytest_wrapped_e.type == ValueError
    assert pytest_wrapped_e.value.args[0] == (
        "The 'S' topology expects the following models:\n"
        "  - A generator with id:\n"
        "      * 'Synch_Gen' if a synchronous generator is modeled\n"
        "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
        "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
        "      * 'Bess' if a storage or a park of storages is modeled\n"
        "  - A transformer with id 'StepUp_Xfmr' connected between the generator and the PDR "
        "bus\n"
    )


def test_check_topology_saux():
    generators = [
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
            equiv_int_line=None,
        )
    ]
    transformers = [
        parameters.Xfmr_params(
            id="StepUp_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
        )
    ]
    auxiliary_load = parameters.Load_params(
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
    auxiliary_transformer = parameters.Xfmr_params(
        id="AuxLoad_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
    )
    transformer = None
    internal_line = None
    sanity_checks.check_topology(
        "S+Aux",
        generators,
        transformers,
        auxiliary_load,
        auxiliary_transformer,
        transformer,
        internal_line,
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        sanity_checks.check_topology(
            "S+Aux+i",
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    assert pytest_wrapped_e.type == ValueError
    assert pytest_wrapped_e.value.args[0] == (
        "The 'S+Aux+i' topology expects the following models:\n"
        "  - A generator with id:\n"
        "      * 'Synch_Gen' if a synchronous generator is modeled\n"
        "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
        "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
        "      * 'Bess' if a storage or a park of storages is modeled\n"
        "  - A transformer with id 'StepUp_Xfmr' connected between the generator and the "
        "internal bus\n"
        "  - An auxiliary load with id 'Aux_Load'\n"
        "  - A transformer with id 'AuxLoad_Xfmr' connected between the auxiliary "
        "load and the internal bus\n"
        "  - An internal line with id 'IntNetwork_Line' connected between the transformer and "
        "the PDR bus\n"
    )


def test_check_topology_sauxi():
    generators = [
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
            equiv_int_line=None,
        )
    ]
    transformers = [
        parameters.Xfmr_params(
            id="StepUp_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
        )
    ]
    auxiliary_load = parameters.Load_params(
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
    auxiliary_transformer = parameters.Xfmr_params(
        id="AuxLoad_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
    )
    transformer = None
    internal_line = parameters.Line_params(
        id="IntNetwork_Line", lib=None, connectedPdr=None, R=0.01, X=0.01, B=0.1, G=0.3
    )
    sanity_checks.check_topology(
        "S+Aux+i",
        generators,
        transformers,
        auxiliary_load,
        auxiliary_transformer,
        transformer,
        internal_line,
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        sanity_checks.check_topology(
            "S+Aux",
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    assert pytest_wrapped_e.type == ValueError
    assert pytest_wrapped_e.value.args[0] == (
        "The 'S+Aux' topology expects the following models:\n"
        "  - A generator with id:\n"
        "      * 'Synch_Gen' if a synchronous generator is modeled\n"
        "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
        "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
        "      * 'Bess' if a storage or a park of storages is modeled\n"
        "  - A transformer with id 'StepUp_Xfmr' connected between the generator and the PDR "
        "bus\n"
        "  - An auxiliary load with id 'Aux_Load'\n"
        "  - A transformer with id 'AuxLoad_Xfmr' connected between the auxiliary "
        "load and the PDR bus\n"
    )


def test_check_topology_m():
    generators = [
        parameters.Gen_params(
            id="Wind_Turbine1",
            lib="WTG4AWeccCurrentSource",
            connectedXmfr="",
            SNom=90,
            IMax=100.0,
            par_id="",
            P=0.1,
            Q=0.05,
            VoltageDroop=None,
            UseVoltageDroop=False,
            equiv_int_line=None,
        ),
        parameters.Gen_params(
            id="Wind_Turbine2",
            lib="WTG4AWeccCurrentSource",
            connectedXmfr="",
            SNom=90,
            IMax=120.0,
            par_id="",
            P=0.12,
            Q=0.025,
            VoltageDroop=None,
            UseVoltageDroop=False,
            equiv_int_line=None,
        ),
    ]
    transformers = [
        parameters.Xfmr_params(
            id="StepUp_Xfmr1", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
        ),
        parameters.Xfmr_params(
            id="StepUp_Xfmr2", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
        ),
    ]
    auxiliary_load = None
    auxiliary_transformer = None
    transformer = parameters.Xfmr_params(
        id="Main_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
    )
    internal_line = None
    sanity_checks.check_topology(
        "M",
        generators,
        transformers,
        auxiliary_load,
        auxiliary_transformer,
        transformer,
        internal_line,
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        sanity_checks.check_topology(
            "M+i",
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    assert pytest_wrapped_e.type == ValueError
    assert pytest_wrapped_e.value.args[0] == (
        "The 'M+i' topology expects the following models:\n"
        "  - Two or more generators, their ids start with:\n"
        "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
        "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
        "      * 'Bess' if a storage or a park of storages is modeled\n"
        "  - A transformer for each generator, its id starts with 'StepUp_Xfmr' and it is "
        "connected between a generator and the internal bus\n"
        "  - A transformer with id 'Main_Xfmr' connected between the internal bus and the "
        "internal line\n"
        "  - An internal line with id 'IntNetwork_Line' connected between the transformer "
        "with id 'transformer' and the PDR bus\n"
    )


def test_check_topology_mi():
    generators = [
        parameters.Gen_params(
            id="Wind_Turbine1",
            lib="WTG4AWeccCurrentSource",
            connectedXmfr="",
            SNom=90,
            IMax=100.0,
            par_id="",
            P=0.1,
            Q=0.05,
            VoltageDroop=None,
            UseVoltageDroop=False,
            equiv_int_line=None,
        ),
        parameters.Gen_params(
            id="Wind_Turbine2",
            lib="WTG4AWeccCurrentSource",
            connectedXmfr="",
            SNom=90,
            IMax=120.0,
            par_id="",
            P=0.12,
            Q=0.025,
            VoltageDroop=None,
            UseVoltageDroop=False,
            equiv_int_line=None,
        ),
    ]
    transformers = [
        parameters.Xfmr_params(
            id="StepUp_Xfmr1", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
        ),
        parameters.Xfmr_params(
            id="StepUp_Xfmr2", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
        ),
    ]
    auxiliary_load = None
    auxiliary_transformer = None
    transformer = parameters.Xfmr_params(
        id="Main_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
    )
    internal_line = parameters.Line_params(
        id="IntNetwork_Line", lib=None, connectedPdr=None, R=0.01, X=0.01, B=0.1, G=0.3
    )
    sanity_checks.check_topology(
        "M+i",
        generators,
        transformers,
        auxiliary_load,
        auxiliary_transformer,
        transformer,
        internal_line,
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        sanity_checks.check_topology(
            "M",
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    assert pytest_wrapped_e.type == ValueError
    assert pytest_wrapped_e.value.args[0] == (
        "The 'M' topology expects the following models:\n"
        "  - Two or more generators, their ids start with:\n"
        "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
        "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
        "      * 'Bess' if a storage or a park of storages is modeled\n"
        "  - A transformer for each generator, its id starts with 'StepUp_Xfmr' and it is "
        "connected between a generator and the internal bus\n"
        "  - A transformer with id 'Main_Xfmr' connected between the internal bus and the "
        "PDR bus\n"
    )


def test_check_topology_maux():
    generators = [
        parameters.Gen_params(
            id="Wind_Turbine1",
            lib="WTG4AWeccCurrentSource",
            connectedXmfr="",
            SNom=90,
            IMax=100.0,
            par_id="",
            P=0.1,
            Q=0.05,
            VoltageDroop=None,
            UseVoltageDroop=False,
            equiv_int_line=None,
        ),
        parameters.Gen_params(
            id="Wind_Turbine2",
            lib="WTG4AWeccCurrentSource",
            connectedXmfr="",
            SNom=90,
            IMax=120.0,
            par_id="",
            P=0.12,
            Q=0.025,
            VoltageDroop=None,
            UseVoltageDroop=False,
            equiv_int_line=None,
        ),
    ]
    transformers = [
        parameters.Xfmr_params(
            id="StepUp_Xfmr1", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
        ),
        parameters.Xfmr_params(
            id="StepUp_Xfmr2", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
        ),
    ]
    auxiliary_load = parameters.Load_params(
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
    auxiliary_transformer = parameters.Xfmr_params(
        id="AuxLoad_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
    )
    transformer = parameters.Xfmr_params(
        id="Main_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
    )
    internal_line = None
    sanity_checks.check_topology(
        "M+Aux",
        generators,
        transformers,
        auxiliary_load,
        auxiliary_transformer,
        transformer,
        internal_line,
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        sanity_checks.check_topology(
            "M+Aux+i",
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    assert pytest_wrapped_e.type == ValueError
    assert pytest_wrapped_e.value.args[0] == (
        "The 'M+Aux+i' topology expects the following models:\n"
        "  - Two or more generators, their ids start with:\n"
        "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
        "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
        "      * 'Bess' if a storage or a park of storages is modeled\n"
        "  - A transformer for each generator, its id starts with 'StepUp_Xfmr' and it is "
        "connected between a generator and the internal bus\n"
        "  - An auxiliary load with id 'Aux_Load'\n"
        "  - A transformer with id 'AuxLoad_Xfmr' connected between the auxiliary "
        "load and the internal bus\n"
        "  - A transformer with id 'Main_Xfmr' connected between the internal bus and the "
        "internal line\n"
        "  - An internal line with id 'IntNetwork_Line' connected between the transformer "
        "with id 'transformer' and the PDR bus\n"
    )


def test_check_topology_mauxi():
    generators = [
        parameters.Gen_params(
            id="Wind_Turbine1",
            lib="WTG4AWeccCurrentSource",
            connectedXmfr="",
            SNom=90,
            IMax=100.0,
            par_id="",
            P=0.1,
            Q=0.05,
            VoltageDroop=None,
            UseVoltageDroop=False,
            equiv_int_line=None,
        ),
        parameters.Gen_params(
            id="Wind_Turbine2",
            lib="WTG4AWeccCurrentSource",
            connectedXmfr="",
            SNom=90,
            IMax=120.0,
            par_id="",
            P=0.12,
            Q=0.025,
            VoltageDroop=None,
            UseVoltageDroop=False,
            equiv_int_line=None,
        ),
    ]
    transformers = [
        parameters.Xfmr_params(
            id="StepUp_Xfmr1", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
        ),
        parameters.Xfmr_params(
            id="StepUp_Xfmr2", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
        ),
    ]
    auxiliary_load = parameters.Load_params(
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
    auxiliary_transformer = parameters.Xfmr_params(
        id="AuxLoad_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
    )
    transformer = parameters.Xfmr_params(
        id="Main_Xfmr", lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
    )
    internal_line = parameters.Line_params(
        id="IntNetwork_Line", lib=None, connectedPdr=None, R=0.01, X=0.01, B=0.1, G=0.3
    )
    sanity_checks.check_topology(
        "M+Aux+i",
        generators,
        transformers,
        auxiliary_load,
        auxiliary_transformer,
        transformer,
        internal_line,
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        sanity_checks.check_topology(
            "M+Aux",
            generators,
            transformers,
            auxiliary_load,
            auxiliary_transformer,
            transformer,
            internal_line,
        )
    assert pytest_wrapped_e.type == ValueError
    assert pytest_wrapped_e.value.args[0] == (
        "The 'M+Aux' topology expects the following models:\n"
        "  - Two or more generators, their ids start with:\n"
        "      * 'Wind_Turbine' if a wind turbine or a wind turbine farm is modeled\n"
        "      * 'PV_Array' if a solar panel or a park of solar panels is modeled\n"
        "      * 'Bess' if a storage or a park of storages is modeled\n"
        "  - A transformer for each generator, its id starts with 'StepUp_Xfmr' and it is "
        "connected between a generator and the internal bus\n"
        "  - An auxiliary load with id 'Aux_Load'\n"
        "  - A transformer with id 'AuxLoad_Xfmr' connected between the auxiliary "
        "load and the internal bus\n"
        "  - A transformer with id 'Main_Xfmr' connected between the internal bus and the "
        "PDR bus\n"
    )
