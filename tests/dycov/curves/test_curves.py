#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the ProducerCurves value-definition helpers."""

from types import SimpleNamespace

import pytest

from dycov.curves.curves import ProducerCurves


def _producer(p_max_pu=0.8, q_max_pu=0.5, q_min_pu=-0.5, s_nom_pu=1.8, u_nom=20.0):
    return SimpleNamespace(
        p_max_pu=p_max_pu,
        q_max_pu=q_max_pu,
        q_min_pu=q_min_pu,
        s_nom_pu=s_nom_pu,
        u_nom=u_nom,
    )


class _Curves(ProducerCurves):
    """Concrete ProducerCurves exercising the real value-definition helpers."""

    def __init__(self, producer, u_dim=20.0, line_Xpu=0.0):
        self._producer = producer
        self._u_dim = u_dim
        self._line_Xpu = line_Xpu
        self._s_nref = 100.0

    def get_producer(self):
        return self._producer

    def get_generator_u_dim(self):
        return self._u_dim

    def get_solver(self):
        return {}

    def get_generators_imax(self):
        return {}

    def obtain_reference_curve(self, *args):
        return (None, None)

    def obtain_simulated_curve(self, *args):
        return ("", {}, None, None)

    def get_time_cct(self, *args):
        return 0.0

    def get_voltage_dip(self):
        return None

    def get_disconnection_model(self):
        return None


def test_get_unit_characteristics_includes_snom():
    curves = _Curves(_producer(), u_dim=21.0, line_Xpu=0.05)

    chars = curves.get_unit_characteristics()

    assert chars["Snom"] == pytest.approx(1.8)
    assert chars["Udim"] == pytest.approx(21.0 / 20.0)
    assert chars["line_XPu"] == pytest.approx(0.05)


def test_obtain_value_resolves_snom():
    curves = _Curves(_producer(s_nom_pu=1.8))

    assert curves.obtain_value("0.5*Snom") == pytest.approx(0.9)


def test_obtain_value_resolves_pmax_alias():
    curves = _Curves(_producer(p_max_pu=0.8))

    assert curves.obtain_value("0.5*PmaxInjection") == pytest.approx(0.4)


def test_obtain_value_passes_through_unknown_token():
    curves = _Curves(_producer())

    assert curves.obtain_value("SomeSolverName") == "SomeSolverName"
