import configparser
import shutil
import sys
from pathlib import Path

from dgcv.configuration.cfg import config
from dgcv.core.validation import Validation
from dgcv.dynawo.prepare_tool import precompile
from dgcv.files import manage_files
from dgcv.logging.logging import dgcv_logging

DGCV_SECTION = "DGCV"
DGCV_TYPE_KEY = "type"
DGCV_VERSION_KEY = "version"
DGCV_VERSION = "1.0.0.RC"


def _template_cmd_config(template: str, cmd: str):
    if (
        not (config.get_config_dir() / "templates").is_dir()
        or not (config.get_config_dir() / "templates" / template).is_dir()
        or not (config.get_config_dir() / "templates" / template / cmd).is_dir()
    ):
        manage_files.create_dir(config.get_config_dir() / "templates" / template / cmd)


def _template_config(template: str):
    _template_cmd_config(template, "model")
    _template_cmd_config(f"{template}/model", "BESS")
    _template_cmd_config(f"{template}/model", "PPM")
    _template_cmd_config(template, "performance")
    _template_cmd_config(f"{template}/performance", "BESS")
    _template_cmd_config(f"{template}/performance", "PPM")
    _template_cmd_config(f"{template}/performance", "SM")


def _templates_config(tool_path: Path):
    _template_config("PCS")
    _template_config("reports")
    _dummysamples_config(tool_path, "PCS")
    _dummysamples_config(tool_path, "reports")

    shutil.copy(tool_path / "templates" / "README.md", config.get_config_dir() / "templates")
    shutil.copy(
        tool_path / "templates" / "PCS" / "README.md",
        config.get_config_dir() / "templates" / "PCS",
    )
    shutil.copy(
        tool_path / "templates" / "reports" / "README.md",
        config.get_config_dir() / "templates" / "reports",
    )
    shutil.copy(
        tool_path / "templates" / "reports" / "TSO_logo.pdf",
        config.get_config_dir() / "templates" / "reports",
    )
    shutil.copy(
        tool_path / "templates" / "reports" / "fig_placeholder.pdf",
        config.get_config_dir() / "templates" / "reports",
    )


def _dummysamples_config(tool_path: Path, source: str):
    shutil.copytree(
        tool_path / "templates" / source / "performance" / "SM" / ".DummySample",
        config.get_config_dir() / "templates" / source / "performance" / "SM" / ".DummySample",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        tool_path / "templates" / source / "performance" / "PPM" / ".DummySample",
        config.get_config_dir() / "templates" / source / "performance" / "PPM" / ".DummySample",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        tool_path / "templates" / source / "performance" / "BESS" / ".DummySample",
        config.get_config_dir() / "templates" / source / "performance" / "BESS" / ".DummySample",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        tool_path / "templates" / source / "model" / "PPM" / ".DummySample",
        config.get_config_dir() / "templates" / source / "model" / "PPM" / ".DummySample",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        tool_path / "templates" / source / "model" / "BESS" / ".DummySample",
        config.get_config_dir() / "templates" / source / "model" / "BESS" / ".DummySample",
        dirs_exist_ok=True,
    )


def _user_models():
    if (
        not (config.get_config_dir() / "user_models").is_dir()
        or not (config.get_config_dir() / "user_models" / "dictionary").is_dir()
    ):
        manage_files.create_dir(config.get_config_dir() / "user_models" / "dictionary")


def _is_valid_config_file(config_file: Path) -> bool:
    if not config_file.is_file():
        return False

    config = configparser.ConfigParser()
    config.read(config_file)
    if not config.has_option(DGCV_SECTION, DGCV_VERSION_KEY):
        return False

    if config.get(DGCV_SECTION, DGCV_VERSION_KEY) != DGCV_VERSION:
        return False

    return True


def _prepare_dynawo_models(launcher_dwo: Path) -> None:
    is_aborted = precompile(launcher_dwo)
    if is_aborted:
        sys.exit()


def _section_key_in_deprecated(deprecated_parameters: list, section: str, key: str) -> str:
    for parameter in deprecated_parameters:
        if parameter["section"] == section and parameter["key"] == key:
            return parameter["value"]

    return ""


def _get_section_by_line(line: str) -> str:
    return line.replace("[", "").replace("]", "").strip()


def _get_key_value_by_line(line: str) -> str:
    key, value = line.split("=")
    return (key.replace("#  ", "").strip(), value.strip())


def _check_config_file(tool_config_file: Path, user_config_file: Path):
    tool_config = configparser.ConfigParser()
    tool_config.read(tool_config_file)
    user_config = configparser.ConfigParser()
    user_config.read(user_config_file)

    deprecated_parameters = []
    for section in user_config.sections():
        for key in user_config.options(section):
            if not tool_config.has_option(section, key):
                deprecated_parameters.append(
                    {"section": section, "key": key, "value": user_config.get(section, key)}
                )

    for parameter in deprecated_parameters:
        dgcv_logging.get_logger("Initialization").warning(
            f"Deprecated: section {parameter['section']} key {parameter['key']} value "
            f"{parameter['value']}"
        )

    files = [
        int(path.name.replace("config.ini.OLD.", ""))
        for path in config.get_config_dir().glob("config.ini.OLD.*")
    ]
    id = max(files) + 1 if len(files) > 0 else 0
    user_config_file.rename(config.get_config_dir() / f"config.ini.OLD.{id}")

    if (
        not user_config.has_section(DGCV_SECTION)
        or not user_config.has_option(DGCV_SECTION, DGCV_TYPE_KEY)
        or user_config.get(DGCV_SECTION, DGCV_TYPE_KEY) == "basic"
    ):
        config_file = config.get_config_dir() / "config.ini_BASIC"
    else:
        config_file = config.get_config_dir() / "config.ini_ADVANCED"

    with open(config_file, "r") as input_file:
        with open(config.get_config_dir() / "config.ini", "w") as output_file:
            for line in input_file:
                output_file.write(line)
                if line.startswith("["):
                    section = _get_section_by_line(line)
                elif " = " in line and line.count("#") == 1:
                    key, value = _get_key_value_by_line(line)
                    if user_config.has_option(section, key):
                        output_file.write(f"{key} = {user_config.get(section, key)}\n")


def init(launcher_dwo: Path, debug: bool) -> None:
    # Tool installation path
    tool_path = Path(__file__).resolve().parent.parent

    # User config path
    if not config.get_config_dir().is_dir():
        manage_files.create_dir(config.get_config_dir())

    manage_files.create_config_file(
        Validation.get_project_path() / "configuration" / "config.ini",
        config.get_config_dir() / "config.ini_BASIC",
    )

    manage_files.create_config_file(
        Validation.get_project_path() / "configuration" / "defaultConfig.ini",
        config.get_config_dir() / "config.ini_ADVANCED",
    )

    if not _is_valid_config_file(config.get_config_dir() / "config.ini"):
        if not (config.get_config_dir() / "config.ini").is_file():
            manage_files.create_config_file(
                Validation.get_project_path() / "configuration" / "config.ini",
                config.get_config_dir() / "config.ini",
            )
        else:
            _check_config_file(
                Validation.get_project_path() / "configuration" / "defaultConfig.ini",
                config.get_config_dir() / "config.ini",
            )

    _templates_config(tool_path)
    _user_models()

    # Initialize logger
    log_dir = config.get_config_dir() / "log"
    if not log_dir.is_dir():
        manage_files.create_dir(log_dir)

    file_log_level = config.get_value("Global", "file_log_level")
    file_formatter = config.get_value("Global", "file_formatter")
    file_max_bytes = config.get_int("Global", "file_log_max_bytes", 50 * 1024 * 1024)
    if debug:
        file_log_level = "DEBUG"
    console_log_level = config.get_value("Global", "console_log_level")
    console_formatter = config.get_value("Global", "console_formatter")
    if debug:
        console_log_level = "DEBUG"
    dgcv_logging.init_handlers(
        file_log_level,
        file_formatter,
        file_max_bytes,
        console_log_level,
        console_formatter,
        log_dir,
    )

    # Precompiled modelica models
    if launcher_dwo:
        _prepare_dynawo_models(launcher_dwo)
