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

        with pytest.raises(FileNotFoundError) as pytest_wrapped_e:
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

        assert pytest_wrapped_e.type == FileNotFoundError
        print(pytest_wrapped_e.value)
        assert (
            str(pytest_wrapped_e.value) == "[Errno 2] No such file or directory: "
            "'Configuration file is not present in the curves path.'"
        )
