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
from dycov.curves.dynawo.dynawo import DynawoSimulator
from dycov.files import manage_files


def _prepare_ddb_path(launcher_dwo: Path, ddb_dir: Path, force: bool) -> bool:
    """
    Prepares the Dynawo database (DDB) path by checking version compatibility and
    handling recompilation.

    This internal helper function checks if the Dynawo version used in previous runs
    matches the current Dynawo version. If there's a mismatch or if `force` is True,
    it prompts the user for re-compilation or removes the existing DDB.

    Parameters
    ----------
    launcher_dwo: Path
        Path to the Dynawo launcher executable.
    ddb_dir: Path
        Path to the Dynawo database (DDB) directory.
    force: bool
        If True, forces the removal of the existing DDB directory without prompting.

    Returns
    -------
    bool
        True if the tool execution should be aborted (e.g., user chose to abort due to
        version mismatch), False otherwise.
    """
    dynawo_version = DynawoSimulator().get_dynawo_version(launcher_dwo)
    if force:
        manage_files.remove_dir(ddb_dir)

    different_versions = False
    compiled_version = None

    # Check if DDB directory exists and contains a version file
    if ddb_dir.is_dir() and (ddb_dir / "dynawo.version").exists():
        with open(ddb_dir / "dynawo.version") as version_file:
            compiled_version = version_file.read()

        if compiled_version != dynawo_version:
            different_versions = True
    # If DDB directory exists but no version file, it's considered a different version
    elif ddb_dir.is_dir() and not (ddb_dir / "dynawo.version").exists():
        different_versions = True

    if different_versions:
        option = input(
            f"WARNING: you are going to run the dycov tool using a Dynawo version "
            f"({dynawo_version})\nthat does not coincide with the version you used in previous "
            f"runs ({compiled_version}).\nIf you go ahead, all your preassembled models will be "
            f"recompiled. Do you want to abort now? ([Y]/n)"
        )
        if option in ("Y", "y", "yes", "Yes", "YES", ""):
            return True
        manage_files.remove_dir(ddb_dir)

    # Create DDB directory if it doesn't exist after checks and potential removal
    if not ddb_dir.is_dir():
        manage_files.create_dir(ddb_dir)

    return False


def precompile(launcher_dwo: Path, model: str = None, force: bool = False) -> bool:
    """
    Precompiles all Dynawo dynamic models or a specific model.

    This function sets up the necessary directory structure for Dynawo compilation,
    checks for Dynawo version compatibility, and then initiates the model precompilation
    process using the DynawoSimulator.

    Parameters
    ----------
    launcher_dwo: Path
        Path to the Dynawo launcher executable.
    model: str, optional
        Name of the dynamic model to compile. If None, all models will be compiled.
        Defaults to None.
    force: bool, optional
        If True, forces the removal of all previously compiled models in the target
        directory before recompilation. Defaults to False.

    Returns
    -------
    bool
        True if the tool execution was aborted by the user during the DDB path preparation,
        False otherwise.
    """
    modelica_path = Path(config.get_value("Global", "modelica_path"))

    # Ensure the main configuration directory exists
    if not config.get_config_dir().is_dir():
        manage_files.create_dir(config.get_config_dir())

    # Prepare the Dynawo DDB directory, handling version checks and user prompts
    ddb_dir = config.get_config_dir() / "ddb"
    if _prepare_ddb_path(launcher_dwo, ddb_dir, force):
        return True

    # Ensure the user models directory and its 'dictionary' subdirectory exist
    user_models = config.get_config_dir() / "user_models"
    if not user_models.is_dir():
        manage_files.create_dir(user_models)

    if not (user_models / "dictionary").is_dir():
        manage_files.create_dir(user_models / "dictionary")

    # Determine the file path for the current script's parent directory
    file_path = Path(__file__).resolve().parent.parent

    # Initiate the model precompilation process using DynawoSimulator
    DynawoSimulator().precompile_models(
        launcher_dwo,
        file_path / modelica_path,
        user_models,
        model,
        ddb_dir,
    )

    return False
