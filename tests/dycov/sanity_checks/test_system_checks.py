#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023-2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import shutil

import pytest

from dycov.sanity_checks import system_checks


@pytest.mark.skipif(shutil.which("dynawo.sh") is not None, reason="Dynawo installed")
def test_launchers():
    with pytest.raises(OSError) as pytest_wrapped_e:
        system_checks.check_launchers("dynawo.sh")
    assert pytest_wrapped_e.type == OSError
    assert pytest_wrapped_e.value.args[0] == "Dynawo not found.\nPdfLatex not found.\n"
