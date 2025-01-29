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

from dgcv.core.execution_parameters import Parameters


def _get_resources_path():
    return (Path(__file__).resolve().parent) / "resources"


def test_parameters():
    path = _get_resources_path() / "tmp"
    shutil.copytree(_get_resources_path(), path, dirs_exist_ok=True)

    launcher_dwo = Path("/tmp/launcher_dwo")
    producer_model = None
    producer_curves_path = path
    reference_curves_path = None
    selected_pcs = "selected_pcs"
    output_dir = Path("/tmp/output_dir")
    only_dtr = True
    verification_type = 0

    try:
        parameters = Parameters(
            launcher_dwo,
            producer_model,
            producer_curves_path,
            reference_curves_path,
            selected_pcs,
            output_dir,
            only_dtr,
            verification_type,
        )

        assert parameters.get_launcher_dwo() == launcher_dwo
        assert parameters.get_selected_pcs() == selected_pcs
        assert parameters.get_output_dir() == output_dir
        assert parameters.get_only_dtr() == only_dtr
    finally:
        shutil.rmtree(path)
