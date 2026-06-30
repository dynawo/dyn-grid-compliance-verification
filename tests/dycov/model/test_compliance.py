#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#

import pytest


def test_to_str_all_members_unique_and_non_empty():
    from dycov.model.compliance import Compliance

    labels = [member.to_str() for member in Compliance]

    assert all(isinstance(label, str) and label for label in labels)
    assert len(set(labels)) == len(labels)


@pytest.mark.parametrize(
    "member, expected",
    [
        ("Compliant", "Compliant"),
        ("NonCompliant", "Non-compliant"),
        ("InvalidTest", "Invalid test"),
        ("FailedSimulation", "Failed simulation"),
        ("UndefinedValidations", "Undefined validations"),
        ("WithoutCurves", "Missing some curves"),
        ("WithoutReferenceCurves", "Missing some reference curves"),
        ("WithoutProducerCurves", "Missing some producer curves"),
        ("FaultSimulationFails", "Fault simulation fails"),
        ("FaultDipUnachievable", "Fault dip unachievable"),
        ("SimulationTimeOut", "Simulation time out"),
        ("NotApplicableTest", "Not applicable test"),
    ],
)
def test_to_str_values(member, expected):
    from dycov.model.compliance import Compliance

    assert Compliance[member].to_str() == expected


def test_show_report_true_members():
    from dycov.model.compliance import Compliance

    reported = {
        Compliance.Compliant,
        Compliance.NonCompliant,
        Compliance.FaultDipUnachievable,
        Compliance.WithoutReferenceCurves,
    }

    for member in Compliance:
        assert member.show_report() is (member in reported)
