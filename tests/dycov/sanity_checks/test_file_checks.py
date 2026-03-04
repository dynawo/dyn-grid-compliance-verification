#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023-2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path

import pytest
from lxml import etree

from dycov.sanity_checks import file_checks


def _get_resources_path():
    return (Path(__file__).resolve().parent) / "resources"


def xml_check(xml_filename):
    file_checks.validate_xml_syntax(_get_resources_path() / xml_filename)


def test_xmls():
    xml_check("wellformed.xml")

    with pytest.raises(etree.XMLSyntaxError) as pytest_wrapped_e:
        xml_check("badformed.xml")
    assert pytest_wrapped_e.type == etree.XMLSyntaxError
    assert pytest_wrapped_e.value.code == 76
    assert (
        pytest_wrapped_e.value.args[0]
        == "Opening and ending tag mismatch: elementwithoutend line 3 and root, line 4, column 8"
    )


def test_curves_file():
    file_checks.check_curves_files(None, _get_resources_path() / "Curves", "")

    with pytest.raises(FileNotFoundError) as pytest_wrapped_e:
        file_checks.check_curves_files(None, _get_resources_path() / "Non-Curves", "")
    assert pytest_wrapped_e.type == FileNotFoundError
