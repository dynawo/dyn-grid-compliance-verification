#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The Fiche I5 of a storage installation, which the revision 20260723 asks of type B alone.

Article 8.3.3 v3.6 says "Type B" in the synthesis table and in the application condition of the
fiche, where the earlier revisions said "Types B, C, D", and article 8.3.4 v1.9 §3.4.7 agrees. So
the revision gives types C and D a version of the fiche without any test, and type B keeps the
fiche the revision gives the PCS. A power park keeps the fiche whatever its type.
"""

from pathlib import Path

import pytest

import dycov
from dycov.configuration.cfg import config
from dycov.model.pcs_layers import version_for_category

BASE_REVISION = "20240215"
PREVIOUS_REVISION = "20251013"
REVISION = "20260723"
TEMPLATES = Path(dycov.__file__).resolve().parent / "templates"


def _in(revision: str, technology: str) -> Path:
    return TEMPLATES / "revisions" / revision / "PCS" / "performance" / technology / "PCS_RTE-I5"


@pytest.fixture
def fiche_i5(revision):
    """Loads the Fiche I5 as the tool loads it under a revision for the category of an
    installation: the base, the delta of the revision, and the version for that category."""

    def load(selected: str, technology: str, category: str) -> list:
        revision(selected)
        delta, version = None, None
        if selected != BASE_REVISION:
            delta = _in(selected, technology) / "PCSDescription.ini"
            version = version_for_category(_in(selected, technology), category)
        config.load_pcs_config(
            TEMPLATES / "PCS" / "performance" / technology / "PCS_RTE-I5" / "PCSDescription.ini",
            None,
            delta if delta and delta.is_file() else None,
            version,
        )
        return config.get_list("PCS-Benchmarks", "PCS_RTE-I5")

    yield load
    config.load_pcs_config(None)


@pytest.mark.parametrize(
    "category, benchmarks", [("B", ["ThreePhaseFault"]), ("C", []), ("D", [])]
)
def test_20260723_asks_the_fault_of_the_fiche_I5_of_a_storage_of_type_B_alone(
    fiche_i5, category, benchmarks
):
    assert fiche_i5(REVISION, "BESS", category) == benchmarks


@pytest.mark.parametrize("selected", [BASE_REVISION, PREVIOUS_REVISION])
@pytest.mark.parametrize("category", ["B", "C", "D"])
def test_the_earlier_revisions_ask_it_of_a_storage_of_any_type(fiche_i5, selected, category):
    assert fiche_i5(selected, "BESS", category) == ["ThreePhaseFault"]


@pytest.mark.parametrize("category", ["B", "C", "D"])
def test_a_power_park_keeps_the_fiche_I5_whatever_its_type(fiche_i5, category):
    assert fiche_i5(REVISION, "PPM", category) == ["ThreePhaseFault"]


def test_type_b_keeps_the_impedant_fault_the_revision_adds(fiche_i5):
    fiche_i5(REVISION, "BESS", "B")

    assert config.get_list("PCS-OperatingConditions", "PCS_RTE-I5.ThreePhaseFault") == [
        "TransientBoltedInjection",
        "TransientBoltedConsumption",
        "TransientImpedantInjection",
        "TransientImpedantConsumption",
    ]
