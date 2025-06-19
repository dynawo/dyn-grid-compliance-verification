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

from dycov.model import parameters
from dycov.sanity_checks import parameter_checks


def test_trafos():
    xfmr = parameters.Xfmr_params(
        id=None, lib=None, R=0.0003, X=0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
    )
    parameter_checks.check_trafo(xfmr)

    bad_xfmr = parameters.Xfmr_params(
        id="Xfmr", lib=None, R=0.0003, X=-0.0268, B=0.0, G=0.0, rTfo=0.9574, par_id=""
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_trafo(bad_xfmr)
    assert pytest_wrapped_e.type == ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The admittance of the transformer Xfmr must be greater than zero."
    )


def test_auxiliary_loads():
    load = parameters.Load_params(
        id=None,
        lib=None,
        connectedXmfr="",
        P=0.1,
        Q=0.05,
        U=1.0,
        UPhase=0.0,
        Alpha=None,
        Beta=None,
    )
    parameter_checks.check_auxiliary_load(load)

    bad_load = parameters.Load_params(
        id=None,
        lib=None,
        connectedXmfr="",
        P=-0.1,
        Q=0.05,
        U=1.0,
        UPhase=0.0,
        Alpha=None,
        Beta=None,
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_auxiliary_load(bad_load)
    assert pytest_wrapped_e.type == ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The active flow of the auxiliary load must be greater than zero."
    )


def test_generators():
    sm = parameters.Gen_params(
        id=None,
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
    ppm = parameters.Gen_params(
        id=None,
        lib="WTG4AWeccCurrentSource",
        connectedXmfr="",
        SNom=90,
        IMax=100.0,
        par_id="",
        P=0.1,
        Q=0.05,
        VoltageDroop=None,
        UseVoltageDroop=False,
    )
    bess = parameters.Gen_params(
        id=None,
        lib="BESScbWeccCurrentSource",
        connectedXmfr="",
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
    line = parameters.Line_params(
        id="Line", lib=None, connectedPdr=True, R=0.02, X=0.004, B=0.0, G=0.0
    )
    parameter_checks.check_internal_line(line)

    bad_line = parameters.Line_params(
        id="Line", lib=None, connectedPdr=True, R=-0.02, X=0.004, B=0.0, G=0.0
    )
    with pytest.raises(ValueError) as pytest_wrapped_e:
        parameter_checks.check_internal_line(bad_line)
    assert pytest_wrapped_e.type == ValueError
    assert (
        pytest_wrapped_e.value.args[0]
        == "The reactance and admittance of the internal line must be greater than zero."
    )
