from pathlib import Path

from dycov.configuration.cfg import config
from dycov.curves.dynawo import dynawo
from dycov.files import manage_files


def _prepare_ddb_path(launcher_dwo: Path, ddb_dir: Path, force: bool) -> bool:
    dynawo_version = dynawo.get_dynawo_version(launcher_dwo)
    if force:
        manage_files.remove_dir(ddb_dir)

    different_versions = False
    compiled_version = None
    if ddb_dir.is_dir() and (ddb_dir / "dynawo.version").exists():
        with open(ddb_dir / "dynawo.version") as version_file:
            compiled_version = version_file.read()

        if compiled_version != dynawo_version:
            different_versions = True

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

    if not ddb_dir.is_dir():
        manage_files.create_dir(ddb_dir)

    return False


def precompile(launcher_dwo: Path, model: str = None, force: bool = False) -> bool:
    """Precompile all Dynawo dynamic models.

    Parameters
    ----------
    launcher_dwo: Path
        Dynawo launcher
    model: str
        Dynamic model name, None for compile all models
    force: bool
        True to remove all compiled models at target directory

    Returns
    -------
    bool
        True if the tool execution was aborted
    """

    modelica_path = Path(config.get_value("Global", "modelica_path"))

    if not config.get_config_dir().is_dir():
        manage_files.create_dir(config.get_config_dir())

    ddb_dir = config.get_config_dir() / "ddb"
    if _prepare_ddb_path(launcher_dwo, ddb_dir, force):
        return True

    user_models = config.get_config_dir() / "user_models"
    if not user_models.is_dir():
        manage_files.create_dir(user_models)

    if not (user_models / "dictionary").is_dir():
        manage_files.create_dir(user_models / "dictionary")

    file_path = Path(__file__).resolve().parent.parent

    dynawo.precompile_models(
        launcher_dwo,
        file_path / modelica_path,
        user_models,
        model,
        ddb_dir,
    )

    return False
