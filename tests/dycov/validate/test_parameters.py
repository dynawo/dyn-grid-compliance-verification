#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/25 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from dycov.validate.parameters import ValidationParameters


def _get_resources_path():
    return (Path(__file__).resolve().parent) / "resources"


def _parameters_with_producer(is_dynawo_model, is_user_curves, has_reference_curves_path):
    params = ValidationParameters.__new__(ValidationParameters)
    params._producer = SimpleNamespace(
        is_dynawo_model=lambda: is_dynawo_model,
        is_user_curves=lambda: is_user_curves,
        has_reference_curves_path=lambda: has_reference_curves_path,
    )
    return params


def test_parameters():
    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        shutil.copytree(_get_resources_path(), path, dirs_exist_ok=True)

        launcher_dwo = path / "launcher_dwo"
        producer_model = None
        producer_curves_path = path / "curves"
        reference_curves_path = None
        selected_pcs = "selected_pcs"
        output_dir = path / "output_dir"
        only_dtr = True
        verification_type = 0

        # Usamos match para evitar problemas entre Windows/Linux
        with pytest.raises(FileNotFoundError, match="Configuration file is not present"):
            ValidationParameters(
                launcher_dwo,
                producer_model,
                producer_curves_path,
                reference_curves_path,
                selected_pcs,
                output_dir,
                only_dtr,
                verification_type,
            )


def test_model_with_reference_curves_is_valid_and_complete():
    params = _parameters_with_producer(
        is_dynawo_model=True, is_user_curves=False, has_reference_curves_path=True
    )

    assert params.is_valid()
    assert params.is_complete()


def test_model_without_reference_curves_is_valid_but_not_complete():
    params = _parameters_with_producer(
        is_dynawo_model=True, is_user_curves=False, has_reference_curves_path=False
    )

    assert params.is_valid()
    assert not params.is_complete()


def test_without_model_nor_curves_is_not_valid():
    params = _parameters_with_producer(
        is_dynawo_model=False, is_user_curves=False, has_reference_curves_path=True
    )

    assert not params.is_valid()
    assert not params.is_complete()
