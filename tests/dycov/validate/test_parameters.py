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

import pytest

from dycov.validate.parameters import ValidationParameters


def _get_resources_path():
    return (Path(__file__).resolve().parent) / "resources"


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
