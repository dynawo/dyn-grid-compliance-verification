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

import pytest

import dycov
from dycov.configuration.cfg import config

PACKAGE_ROOT = Path(dycov.__file__).resolve().parent
BASE_REVISION = "20240215"


@pytest.fixture
def description():
    """Loads the description of a PCS the tool ships, and leaves no layer behind.

    The test names the kind of unit and the fiche, and reads the options through the
    configuration, so the same test reads a delta once a revision writes one.
    """
    loaded = []

    def load(verification: str, technology: str, pcs: str) -> None:
        path = (
            PACKAGE_ROOT / "templates" / "PCS" / verification / technology / pcs
        ) / "PCSDescription.ini"
        assert path.is_file(), f"the tool ships no description for {technology} {pcs}"
        config.load_pcs_config(path)
        loaded.append(path)

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
