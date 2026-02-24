#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import configparser
from pathlib import Path

from dycov.logging.logging import dycov_logging


def _create_producer_ini_file(
    target: Path,
    filename: str,
    topology: str,
) -> None:
    if (target / "Producer.ini").exists():
        (target / "Producer.ini").rename(target / filename)

    producer_ini_txt = (
        f"[DEFAULT]\n"
        f"# p_{{max_unite}} injection as defined by the DTR in MW\n"
        f"p_max_injection_at_PDR =\n"
        f"# p_{{max_unite}} consumption as defined by the DTR in MW (only for BESS)\n"
        f"p_max_consumption_at_PDR =\n"
        f"# u_nom is the nominal voltage at the PDR bus (in kV)\n"
        f"# Allowed values: 400, 225, 150, 90, 63 (land) and 132, 66 (offshore)\n"
        f"u_nom =\n"
        f"# q_max is the maximum reactive power at the PDR bus (in MVar)\n"
        f"q_max_at_PDR =\n"
        f"# q_min is the minimum reactive power at the PDR bus (in MVar)\n"
        f"q_min_at_PDR =\n"
        f"# Active power sharing per generator unit (%).  Values must be between 0 and 1.\n"
        f"P_sharing_[GEN_ID] =\n"
        f"# Reactive power sharing per generator unit (%).  Values must be between 0 and 1.\n"
        f"Q_sharing_[GEN_ID] =\n"
        f"# topology\n"
        f"topology = {topology}\n"
    )

    with open(target / filename, "w") as f:
        f.write(producer_ini_txt)


def _check_ini_parameters(target: Path, filename: str) -> bool:
    default_section = "DEFAULT"
    producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    producer_config.read(target / filename)

    success = True
    empty_values = []
    for key, value in producer_config.items(default_section):
        if value == "":
            empty_values.append(key)
            success = False

    if not success:
        dycov_logging.get_logger("Create INI input").error(
            f"The INI file contains parameters without value.\nPlease fix {empty_values}."
        )
    return success


def create_producer_ini_file(
    target: Path,
    topology: str,
    template: str,
) -> None:
    """Create a INI file in target path

    Parameters
    ----------
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
    if template.startswith("model"):
        if topology.casefold().startswith("m"):
            _create_producer_ini_file(target / "Zone1", "Producer_G1.ini", "S")
            _create_producer_ini_file(target / "Zone1", "Producer_G2.ini", "S")
        else:
            _create_producer_ini_file(target / "Zone1", "Producer.ini", "S")
        _create_producer_ini_file(target / "Zone3", "Producer.ini", topology)
    else:
        _create_producer_ini_file(target, "Producer.ini", topology)


def check_ini_parameters(target: Path, template: str) -> bool:
    """Checks if all parameters in the INI file have a value defined.

    Parameters
    ----------
    target: Path
        Target path
    template: str
        Input template name:
        * 'performance_SM' if it is electrical performance for Synchronous Machine Model
        * 'performance_PPM' if it is electrical performance for Power Park Module Model
        * 'performance_BESS' if it is electrical performance for Storage Model
        * 'model_PPM' if it is model validation for Power Park Module Model
        * 'model_BESS' if it is model validation for Storage Model

    Returns
    -------
    bool
        False if there are empty values in the INI file
    """
    if template.startswith("model"):
        ini_files = list((target / "Zone1").glob("*.[iI][nN][iI]"))
        for ini_file in ini_files:
            if not _check_ini_parameters(target / "Zone1", ini_file.name):
                return False
        check_zone3 = _check_ini_parameters(target / "Zone3", "Producer.ini")
        return check_zone3
    else:
        return _check_ini_parameters(target, "Producer.ini")
