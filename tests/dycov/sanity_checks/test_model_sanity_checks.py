#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from tests.dycov.utils import MODEL

from dycov.core.global_variables import MODEL_VALIDATION
from dycov.validate.producer import ModelProducer


def run_model_sanity_check(model_path, reference_path):
    ModelProducer(
        model_path,
        None,
        reference_path,
        MODEL_VALIDATION,
    )


def test_bess_wecc_model_sanity():
    run_model_sanity_check(
        MODEL / "BESS" / "WECC" / "Dynawo",
        MODEL / "BESS" / "WECC" / "ReferenceCurves",
    )


def test_photovoltaics_wecccurrentsource_model_sanity():
    run_model_sanity_check(
        MODEL / "Photovoltaics" / "WECCCurrentSource" / "Dynawo",
        MODEL / "Photovoltaics" / "WECCCurrentSource" / "ReferenceCurves",
    )


def test_photovoltaics_weccvoltagesource1_model_sanity():
    run_model_sanity_check(
        MODEL / "Photovoltaics" / "WECCVoltageSource1" / "Dynawo",
        MODEL / "Photovoltaics" / "WECCVoltageSource1" / "ReferenceCurves",
    )


def test_photovoltaics_weccvoltagesource2_model_sanity():
    run_model_sanity_check(
        MODEL / "Photovoltaics" / "WECCVoltageSource2" / "Dynawo",
        MODEL / "Photovoltaics" / "WECCVoltageSource2" / "ReferenceCurves",
    )


def test_photovoltaics_weccvoltagesource3_model_sanity():
    run_model_sanity_check(
        MODEL / "Photovoltaics" / "WECCVoltageSource3" / "Dynawo",
        MODEL / "Photovoltaics" / "WECCVoltageSource3" / "ReferenceCurves",
    )


def test_photovoltaics_weccvoltagesource4_model_sanity():
    run_model_sanity_check(
        MODEL / "Photovoltaics" / "WECCVoltageSource4" / "Dynawo",
        MODEL / "Photovoltaics" / "WECCVoltageSource4" / "ReferenceCurves",
    )


def test_wind_ieca2015_model_sanity():
    run_model_sanity_check(
        MODEL / "Wind" / "IECA2015" / "Dynawo",
        MODEL / "Wind" / "IECA2015" / "ReferenceCurves",
    )


def test_wind_ieca2020_model_sanity():
    run_model_sanity_check(
        MODEL / "Wind" / "IECA2020" / "Dynawo",
        MODEL / "Wind" / "IECA2020" / "ReferenceCurves",
    )


def test_wind_ieca2020withprotections_model_sanity():
    run_model_sanity_check(
        MODEL / "Wind" / "IECA2020WithProtections" / "Dynawo",
        MODEL / "Wind" / "IECA2020WithProtections" / "ReferenceCurves",
    )


def test_wind_iecb2015_model_sanity():
    run_model_sanity_check(
        MODEL / "Wind" / "IECB2015" / "Dynawo",
        MODEL / "Wind" / "IECB2015" / "ReferenceCurves",
    )


def test_wind_iecb2020_model_sanity():
    run_model_sanity_check(
        MODEL / "Wind" / "IECB2020" / "Dynawo",
        MODEL / "Wind" / "IECB2020" / "ReferenceCurves",
    )


def test_wind_iecb2020withprotections_model_sanity():
    run_model_sanity_check(
        MODEL / "Wind" / "IECB2020WithProtections" / "Dynawo",
        MODEL / "Wind" / "IECB2020WithProtections" / "ReferenceCurves",
    )


def test_wind_wecc31_model_sanity():
    run_model_sanity_check(
        MODEL / "Wind" / "WECC31" / "Dynawo",
        MODEL / "Wind" / "WECC31" / "ReferenceCurves",
    )


def test_wind_wecc32_model_sanity():
    run_model_sanity_check(
        MODEL / "Wind" / "WECC32" / "Dynawo",
        MODEL / "Wind" / "WECC32" / "ReferenceCurves",
    )


def test_wind_wecc4a_model_sanity():
    run_model_sanity_check(
        MODEL / "Wind" / "WECC4A" / "Dynawo",
        MODEL / "Wind" / "WECC4A" / "ReferenceCurves",
    )


def test_wind_wecc4b_model_sanity():
    run_model_sanity_check(
        MODEL / "Wind" / "WECC4B" / "Dynawo",
        MODEL / "Wind" / "WECC4B" / "ReferenceCurves",
    )


def test_wind_wecc4_model_sanity():
    run_model_sanity_check(
        MODEL / "Wind" / "WECC4" / "Dynawo",
        MODEL / "Wind" / "WECC4" / "ReferenceCurves",
    )
