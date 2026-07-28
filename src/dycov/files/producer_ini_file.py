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

from dycov.logging import dycov_logging


def _kv(key: str, value) -> str:
    """Render an INI ``key = value`` line, leaving it blank when no value is given."""
    return f"{key} =" if value in (None, "") else f"{key} = {value}"


def _render_ini_text(
    topology: str,
    values: dict,
    gen_sharing: dict,
    include_consumption: bool,
) -> str:
    """Single source of the Producer INI layout.

    Both the blank template (``values={}``, ``gen_sharing={"[GEN_ID]": ("", "")}``) and the
    value-filled Excel flow render from here.
    """
    lines = [
        "[DEFAULT]",
        "# p_{max_unite} injection as defined by the DTR in MW",
        _kv("p_max_injection_at_PDR", values.get("p_max_injection_at_PDR", "")),
    ]
    if include_consumption:
        lines += [
            "# p_{max_unite} consumption as defined by the DTR in MW (only for BESS)",
            _kv("p_max_consumption_at_PDR", values.get("p_max_consumption_at_PDR", "")),
        ]
    lines += [
        "# u_nom is the nominal voltage at the PDR bus (in kV)",
        "# Allowed values: 400, 225, 150, 90, 63 (land) and 132, 66 (offshore)",
        _kv("u_nom_at_PDR", values.get("u_nom_at_PDR", "")),
        "# q_max is the maximum reactive power at the PDR bus (in MVar)",
        _kv("q_max_at_PDR", values.get("q_max_at_PDR", "")),
        "# q_min is the minimum reactive power at the PDR bus (in MVar)",
        _kv("q_min_at_PDR", values.get("q_min_at_PDR", "")),
        "# Active power sharing per generator unit (%).  Values must be between 0 and 1.",
    ]
    lines += [_kv(f"P_sharing_{gen_id}", p) for gen_id, (p, _q) in gen_sharing.items()]
    lines += ["# Reactive power sharing per generator unit (%).  Values must be between 0 and 1."]
    lines += [_kv(f"Q_sharing_{gen_id}", q) for gen_id, (_p, q) in gen_sharing.items()]
    lines += ["# topology", f"topology = {topology}"]
    return "\n".join(lines) + "\n"


def _create_producer_ini_file(
    target: Path,
    filename: str,
    topology: str,
    values: dict = None,
    gen_sharing: dict = None,
    include_consumption: bool = True,
) -> None:
    if (target / "Producer.ini").exists():
        (target / "Producer.ini").rename(target / filename)

    text = _render_ini_text(
        topology,
        values or {},
        gen_sharing or {"[GEN_ID]": ("", "")},
        include_consumption,
    )
    with open(target / filename, "w") as f:
        f.write(text)


def write_producer_ini_file(
    target: Path,
    filename: str,
    topology: str,
    values: dict,
    gen_sharing: dict,
    include_consumption: bool = False,
) -> None:
    """Write a value-filled INI (Excel-driven flow) using the shared layout.

    Thin wrapper over ``_create_producer_ini_file``; the only difference from the blank template
    is the data (``values`` and per-generator ``gen_sharing`` ``{id -> (P_sharing, Q_sharing)}``).
    Set ``include_consumption`` for BESS (adds ``p_max_consumption_at_PDR``).
    """
    _create_producer_ini_file(
        target, filename, topology, values, gen_sharing, include_consumption
    )


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
    n_generators: int = 2,
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
    n_generators: int
        Number of generators for an ``M`` topology (one ``Producer_G<i>.ini`` per ``Zone1<x>``
        sheet); default 2.
    """
    if template.startswith("model"):
        if topology.casefold().startswith("m"):
            for i in range(1, n_generators + 1):
                _create_producer_ini_file(target / "Zone1", f"Producer_G{i}.ini", "S")
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
