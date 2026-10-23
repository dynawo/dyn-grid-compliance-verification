#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path
from typing import Optional

import pytest

import dycov
from dycov.configuration.cfg import config, is_base_revision

PACKAGE_ROOT = Path(dycov.__file__).resolve().parent
BASE_REVISION = "20240215"


def _select_revision(name: str) -> None:
    """Puts the tool on a revision of the DTR, as the option --dtr does."""
    config.set_value("DTR", "current", name)
    config.load_dtr_delta_config(name)


def _delta_of(verification: str, technology: str, pcs: str) -> Optional[Path]:
    """The description the selected revision of the DTR writes for a PCS, if it writes one."""
    revision = config.get_value("DTR", "current")
    if is_base_revision(revision):
        return None

    path = (
        PACKAGE_ROOT
        / "templates"
        / "revisions"
        / revision
        / "PCS"
        / verification
        / technology
        / pcs
    ) / "PCSDescription.ini"
    return path if path.is_file() else None


@pytest.fixture(autouse=True)
def base_revision():
    """Reads the base, until the test selects another revision.

    The configuration names the newest revision, so a test that said nothing would answer
    for a different DTR at every release.
    """
    selected = config.get_value("DTR", "current")

    _select_revision(BASE_REVISION)
    yield

    config.set_value("DTR", "current", selected)
    config.load_dtr_delta_config(BASE_REVISION)


@pytest.fixture
def revision():
    """Selects the revision of the DTR the test answers for.

    Call it before ``description``: the revision says which delta the description reads.
    """
    return _select_revision


@pytest.fixture
def description():
    """Loads the description of a PCS the tool ships, and leaves no layer behind.

    The test names the kind of unit and the fiche, and reads the options through the
    configuration, so it sees the value the tool sees: the one of the shipped catalogue,
    or the one the delta of the selected revision writes over it.
    """

    def load(verification: str, technology: str, pcs: str) -> None:
        path = (
            PACKAGE_ROOT / "templates" / "PCS" / verification / technology / pcs
        ) / "PCSDescription.ini"
        assert path.is_file(), f"the tool ships no description for {technology} {pcs}"
        config.load_pcs_config(path, None, _delta_of(verification, technology, pcs))

    yield load

    config.load_pcs_config(None)


@pytest.fixture
def value(description):
    """Reads an option the way the tool reads it, following the suffix of the category."""

    def read(section: str, key: str, *suffixes: str) -> str:
        option = config.find_option(section, key, *suffixes)
        assert option is not None, f"[{section}] defines no {key}"
        return config.get_value(section, option)

    return read
