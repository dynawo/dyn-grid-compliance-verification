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
from dycov.curves.dynawo.runtime.dynawo_precompile import get_dynawo_version, precompile_models
from dycov.files import manage_files
from dycov.logging.logging import dycov_logging


def _prepare_ddb_path(launcher_dwo: Path, ddb_dir: Path, force: bool) -> bool:
    """
    Prepare the Dynawo database (DDB) path by checking version compatibility
    and handling recompilation.

    If Dynawo version differs from previous runs or `force` is True, the existing
    DDB is removed. Prompts the user to abort if versions differ.

    Parameters
    ----------
    launcher_dwo : Path
        Path to the Dynawo launcher executable.
    ddb_dir : Path
        Path to the Dynawo database (DDB) directory.
    force : bool
        If True, forces removal of the existing DDB directory without prompting.

    Returns
    -------
    bool
        True if execution should be aborted (user chose to abort), False otherwise.
    """
    dynawo_version = get_dynawo_version(launcher_dwo)

    if force:
        manage_files.remove_dir(ddb_dir)

    compiled_version = None
    different_versions = False

    # Check if DDB directory exists and version file is present
    if ddb_dir.is_dir():
        version_file = ddb_dir / "dynawo.version"
        if version_file.exists():
            compiled_version = version_file.read_text().strip()
            different_versions = compiled_version != dynawo_version
        else:
            different_versions = True

    if different_versions:
        option = input(
            f"WARNING: you are going to run the dycov tool using a Dynawo version "
            f"({dynawo_version})\nthat does not coincide with the version you used in previous "
            f"runs ({compiled_version}).\nIf you go ahead, all your preassembled models will be "
            f"recompiled. Do you want to abort now? ([Y]/n)"
        )
        if option.strip().lower() in ("y", "yes", ""):
            return True
        manage_files.create_dir(ddb_dir, clean_first=True)

    return False


def precompile(launcher_dwo: Path, model: str = None, force: bool = False) -> bool:
    """
    Precompile all Dynawo dynamic models or a specific model.

    Sets up directory structure, checks Dynawo version compatibility,
    and initiates model precompilation using DynawoSimulator.

    Parameters
    ----------
    launcher_dwo : Path
        Path to the Dynawo launcher executable.
    model : str, optional
        Name of the dynamic model to compile. If None, all models will be compiled.
    force : bool, optional
        If True, forces removal of previously compiled models before recompilation.

    Returns
    -------
    bool
        True if execution was aborted during DDB preparation, False otherwise.
    """
    # Resolve paths
    modelica_path = Path(config.get_value("Global", "modelica_path"))
    file_path = Path(__file__).resolve().parent.parent.parent
    user_models = config.get_config_dir() / "user_models"
    ddb_dir = config.get_config_dir() / "ddb"

    # Ensure required directories exist without deleting previous content
    manage_files.create_dir(config.get_config_dir(), clean_first=False)
    manage_files.create_dir(user_models, clean_first=False)
    manage_files.create_dir(user_models / "dictionary", clean_first=False)
    manage_files.create_dir(ddb_dir, clean_first=False)

    # Helper to check XML files
    def has_xml_files(path: Path) -> bool:
        return any(path.glob("*.[xX][mM][lL]"))

    # Skip precompilation if both directories have no XML files
    if not has_xml_files(file_path / modelica_path) and not has_xml_files(user_models):
        dycov_logging.get_logger("PrepareTool").info(
            "No XML files found in modelica_path or user_models. Skipping precompile."
        )
        return False

    # Prepare DDB directory
    if _prepare_ddb_path(launcher_dwo, ddb_dir, force):
        return True

    # Execute precompilation
    precompile_models(
        launcher_dwo,
        file_path / modelica_path,
        user_models,
        model,
        ddb_dir,
    )

    return False
