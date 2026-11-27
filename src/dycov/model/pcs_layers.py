#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Where the description of a PCS is read from, and the tests it runs.

A PCS is described in layers: the description shipped with the tool, what the selected revision of
the DTR writes differently (its delta, and the version of the fiche it gives some categories of
installation) and the user's own. Reading them takes no more than the PCS, the kind of
verification and the category of the installation, so anything that needs to know the tests a
PCS runs can ask here without preparing the PCS itself.
"""

import configparser
from pathlib import Path
from typing import Optional, Union

from dycov.configuration import cfg
from dycov.configuration.cfg import config
from dycov.core.global_variables import CASE_SEPARATOR

_SOURCE = Path(__file__).resolve().parent.parent


def description_in(path: Path) -> Union[Path, None]:
    files = {file.stem.lower(): file for file in path.glob("*.[iI][nN][iI]")}
    return files.get("pcsdescription")


def version_for_category(path: Path, category: Optional[str]) -> Union[Path, None]:
    """The version of a fiche the DTR gives some categories of unit: a ``Type<categories>.ini``
    in the directory of the delta of the PCS, named after the categories it is for
    (``TypeCD.ini`` for the categories C and D), which patches the description the revision
    gives the PCS."""
    if category is None:
        return None
    for version in sorted(path.glob("Type*.[iI][nN][iI]")):
        if category in version.stem[len("Type") :]:
            return version
    return None


def description_declaring(path: Path, pcs_name: str) -> Union[Path, None]:
    """The ``<fiche>Description.ini`` delivered with the reference curves that declares the
    benchmarks of the PCS, if any: such a file names the PCS it describes."""
    for description in sorted(path.glob("*[dD]escription.[iI][nN][iI]")):
        parser = configparser.ConfigParser(inline_comment_prefixes=("#",))
        parser.optionxform = str
        parser.read(description, encoding="utf-8")
        if parser.has_option("PCS-Benchmarks", pcs_name):
            return description
    return None


def templates_path() -> Path:
    return Path(config.get_value("Global", "templates_path"))


def description_path(source: Path, templates: Path, sim_type: str, pcs_name: str):
    """The description of a PCS under a tree of templates, None when the tree has none."""
    path = source / templates / sim_type / pcs_name
    if not path.exists():
        return None
    return description_in(path)


def delta_templates_path(templates: Path) -> Union[Path, None]:
    """The templates of the delta of the selected revision of the DTR, which mirror the
    shipped ones, or None for the base revision, which has no delta."""
    revision = config.get_value("DTR", "current")
    if cfg.is_base_revision(revision):
        return None
    return templates.parent / "revisions" / revision / templates.name


def description_layers(
    pcs_name: str,
    sim_type: str,
    category: Optional[str],
    user_path: Optional[Path],
) -> tuple:
    """The files of the layers of a PCS, in the order ``config.load_pcs_config`` takes them: the
    shipped description, the user's, the delta of the selected revision of the DTR and the
    version it writes for the category of the installation."""
    templates = templates_path()
    delta_templates = delta_templates_path(templates)
    if delta_templates is None:
        return description_path(_SOURCE, templates, sim_type, pcs_name), user_path, None, None
    return (
        description_path(_SOURCE, templates, sim_type, pcs_name),
        user_path,
        description_path(_SOURCE, delta_templates, sim_type, pcs_name),
        version_for_category(_SOURCE / delta_templates / sim_type / pcs_name, category),
    )


def user_description(sim_type: str, pcs_name: str) -> Union[Path, None]:
    """The user's description of a PCS in the configuration directory."""
    return description_path(config.get_config_dir(), templates_path(), sim_type, pcs_name)


def optional_operating_point(pcs_bm_oc_name: str) -> Optional[str]:
    """The operating point of the DTR an operating condition is, when the DTR asks for it
    only under a condition the tool does not check on a model."""
    return config.get_value(pcs_bm_oc_name, "optional_operating_point") or None


def is_run(pcs_name: str, pcs_bm_oc_name: str) -> bool:
    """An optional operating condition is run when the ``run_<point>`` key of the PCS says
    so for its operating point, and every other one always."""
    point = optional_operating_point(pcs_bm_oc_name)
    return point is None or config.get_boolean(pcs_name, f"run_{point}", False)


def tests_it_runs(pcs_name: str, sim_type: str, category: Optional[str]) -> list:
    """The tests, ``PCS.Benchmark.OperatingCondition``, a PCS runs for an installation of a
    category, as the layers of its description declare them. The layers of the PCS prepared
    before are put back."""
    kept = config.pcs_description_paths()
    config.load_pcs_config(
        *description_layers(pcs_name, sim_type, category, user_description(sim_type, pcs_name))
    )
    try:
        tests = []
        for benchmark in config.get_list("PCS-Benchmarks", pcs_name):
            name = pcs_name + CASE_SEPARATOR + benchmark
            tests += [
                name + CASE_SEPARATOR + oc
                for oc in config.get_list("PCS-OperatingConditions", name)
                if is_run(pcs_name, name + CASE_SEPARATOR + oc)
            ]
        return tests
    finally:
        config.load_pcs_config(*kept)
