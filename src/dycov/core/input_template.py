#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path

from dycov.configuration.cfg import config
from dycov.files import manage_files
from dycov.files.producer_curves import check_curves, create_producer_curves
from dycov.files.producer_dyd_file import check_dynamic_models, create_producer_dyd_file
from dycov.files.producer_ini_file import check_ini_parameters, create_producer_ini_file
from dycov.files.producer_par_file import check_parameters, create_producer_par_file
from dycov.logging.logging import dycov_logging


def _get_input(text):
    return input(text)


def _copy_input_templates(target: Path, template: str) -> None:
    input_templates_path = config.get_value("Global", "input_templates_path")
    if template == "performance_SM":
        manage_files.copy_path(Path(input_templates_path) / "performance/SM", target)
    elif template in ["performance_PPM", "performance_BESS"]:
        manage_files.copy_path(Path(input_templates_path) / "performance/PPM", target)
    elif template.startswith("model"):
        manage_files.copy_path(Path(input_templates_path) / "model", target)


def _create_dyd_template(target: Path, topology: str, template: str) -> None:
    dycov_logging.get_logger("Create input files").info(
        f"Creating the input DYD file in {target}."
    )
    create_producer_dyd_file(target, topology, template)
    _get_input(
        "Edit Producer.dyd to complete each equipment with a dynamic model. Press Enter when done."
    )
    while not check_dynamic_models(target, template):
        _get_input(
            "Edit Producer.dyd is necessary to complete each equipment  with a dynamic model."
            "Press Enter when done."
        )


def _create_par_template(launcher_dwo: Path, target: Path, topology: str, template: str) -> None:
    dycov_logging.get_logger("Create input files").info(
        f"Creating the input PAR file in {target}."
    )
    create_producer_par_file(launcher_dwo, target, template)
    _get_input("Edit Producer.par to complete each parameter with a value. Press Enter when done.")
    while not check_parameters(target, template):
        _get_input(
            "Edit Producer.par is necessary to complete each parameter with a value."
            "Press Enter when done."
        )


def _create_ini_template(target: Path, topology: str, template: str) -> None:
    dycov_logging.get_logger("Create input files").info(
        f"Creating the input INI file in {target}."
    )
    create_producer_ini_file(target, topology, template)
    _get_input("Edit Producer.ini to complete each parameter with a value. Press Enter when done.")
    while not check_ini_parameters(target, template):
        _get_input(
            "Edit Producer.ini is necessary to complete each parameter with a value."
            "Press Enter when done."
        )


def _create_curves_template(target: Path, topology: str, template: str) -> None:
    ref_target = target / "ReferenceCurves"
    dycov_logging.get_logger("Create input files").info(
        f"Creating the reference curves files in {ref_target}."
    )
    create_producer_curves(target, ref_target, template)
    _get_input(
        "Edit CurvesFiles.ini to complete each parameter with a curves file. Press Enter when "
        "done."
    )
    while not check_curves(ref_target):
        _get_input(
            "Edit CurvesFiles.ini is necessary to complete each parameter with a curves file."
            "Press Enter when done."
        )


def create_input_template(launcher_dwo: Path, target: Path, topology: str, template: str) -> None:
    """Create an input template in target path with the selected topology.

    Parameters
    ----------
    launcher_dwo: Path
        Dynawo launcher
    target: Path
        Target path
    topology: str
        Topology to the DYD file
    template: str
        Input template name:
        * 'performance_SM' if it is electrical performance for Synchronous Machine Model
        * 'performance_PPM' if it is electrical performance for Power Park Module Model
        * 'performance_BESS' if it is electrical performance for Storage Model
        * 'model_PPM' if it is model validation for Power Park Module Model
        * 'model_BESS' if it is model validation for Storage Model
    """

    if target.exists():
        dycov_logging.get_logger("Create Input").error(
            "The output path already exists, please indicate a new path"
        )
        return

    manage_files.create_dir(target)
    _copy_input_templates(target, template)

    _create_dyd_template(target, topology, template)

    _create_par_template(launcher_dwo, target, topology, template)

    _create_ini_template(target, topology, template)

    _create_curves_template(target, topology, template)
    print("Done")
