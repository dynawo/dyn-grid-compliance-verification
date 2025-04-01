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
from importlib.metadata import version
import shutil
import sys
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.core.validation import Validation
from dycov.dynawo.prepare_tool import precompile
from dycov.files import manage_files
from dycov.logging.logging import dycov_logging

dycov_CONFIG_SECTION = "dycov"
dycov_CONFIG_TYPE_KEY = "type"
dycov_CONFIG_VERSION_KEY = "version"
dycov_TOOL_VERSION = "1.0.0.RC"


def _template_cmd_config(template: str, cmd: str):
    config_dir = config.get_config_dir()
    template_dir = config_dir / "templates" / template / cmd
    if (
        not (config_dir / "templates").is_dir()
        or not (config_dir / "templates" / template).is_dir()
        or not template_dir.is_dir()
    ):
        manage_files.create_dir(template_dir)


def _template_config(template: str):
    subdirs = ["model", "performance"]
    models = ["BESS", "PPM", "SM"]
    for subdir in subdirs:
        _template_cmd_config(template, subdir)
        for model in models:
            _template_cmd_config(f"{template}/{subdir}", model)


def _templates_config(tool_path: Path):
    templates = ["PCS", "reports"]
    for template in templates:
        _template_config(template)
        _dummysamples_config(tool_path, template)

    shutil.copy(tool_path / "templates" / "README.md", config.get_config_dir() / "templates")
    for template in templates:
        shutil.copy(
            tool_path / "templates" / template / "README.md",
            config.get_config_dir() / "templates" / template,
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
    categories = ["performance", "model"]
    models = ["SM", "PPM", "BESS"]
    for category in categories:
        for model in models:
            src = tool_path / "templates" / source / category / model / ".DummySample"
            dest = (
                config.get_config_dir() / "templates" / source / category / model / ".DummySample"
            )
            if src.exists():
                try:
                    shutil.copytree(src, dest, dirs_exist_ok=True)
                except Exception as e:
                    dycov_logging.get_logger("Initialization").error(
                        f"Failed to copy {src} to {dest}: {e}"
                    )


def _user_models():
    if (
        not (config.get_config_dir() / "user_models").is_dir()
        or not (config.get_config_dir() / "user_models" / "dictionary").is_dir()
    ):
        manage_files.create_dir(config.get_config_dir() / "user_models" / "dictionary")

    files = [
        "Bus.ini",
        "Line.ini",
        "Load.ini",
        "Power_Park.ini",
        "Storage.ini",
        "Synch_Gen.ini",
        "Transformer.ini",
    ]
    for file in files:
        manage_files.create_empty_file(
            config.get_config_dir() / "user_models" / "dictionary" / file
        )


def _is_valid_config_file(config_file: Path) -> bool:
    if not config_file.is_file():
        return False

    config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    config.read(config_file)
    if not config.has_option(dycov_CONFIG_SECTION, dycov_CONFIG_VERSION_KEY):
        return False

    if config.get(dycov_CONFIG_SECTION, dycov_CONFIG_VERSION_KEY) != dycov_TOOL_VERSION:
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


def _get_key_value_by_line(line: str) -> tuple[str, str]:
    key, value = line.split("=")
    return (key.replace("#  ", "").strip(), value.strip())


def _check_config_file(tool_config_file: Path, user_config_file: Path):
    tool_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    tool_config.read(tool_config_file)
    user_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    user_config.read(user_config_file)

    deprecated_parameters = []
    for section in user_config.sections():
        for key in user_config.options(section):
            if not tool_config.has_option(section, key):
                deprecated_parameters.append(
                    {"section": section, "key": key, "value": user_config.get(section, key)}
                )

    for parameter in deprecated_parameters:
        dycov_logging.get_logger("Initialization").warning(
            f"Deprecated in {user_config_file.name}: section {parameter['section']} "
            f"key {parameter['key']} value {parameter['value']}"
        )

    files = [
        int(path.name.replace("config.ini.OLD.", ""))
        for path in config.get_config_dir().glob("config.ini.OLD.*")
    ]
    id = max(files) + 1 if len(files) > 0 else 0
    user_config_file.rename(config.get_config_dir() / f"config.ini.OLD.{id}")

    if (
        not user_config.has_section(dycov_CONFIG_SECTION)
        or not user_config.has_option(dycov_CONFIG_SECTION, dycov_CONFIG_TYPE_KEY)
        or user_config.get(dycov_CONFIG_SECTION, dycov_CONFIG_TYPE_KEY) == "basic"
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


def _setup_user_config():
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


def _setup_templates_and_models(tool_path: Path):
    _templates_config(tool_path)
    _user_models()


def _initialize_logger(debug: bool):
    log_dir = config.get_config_dir() / "log"
    if not log_dir.is_dir():
        manage_files.create_dir(log_dir)

    file_log_level = config.get_value("Global", "file_log_level")
    file_formatter = config.get_value("Global", "file_formatter")
    file_max_bytes = config.get_int("Global", "file_log_max_bytes", 50 * 1024 * 1024)

    console_log_level = config.get_value("Global", "console_log_level")
    console_formatter = config.get_value("Global", "console_formatter")

    if debug:
        file_log_level = "DEBUG"
        console_log_level = "DEBUG"

    dycov_logging.init_handlers(
        file_log_level,
        file_formatter,
        file_max_bytes,
        console_log_level,
        console_formatter,
        log_dir,
    )


def init(launcher_dwo: Path, debug: bool) -> None:
    """
    Initialize the dycov tool by setting up the user configuration path.

    Parameters
    ----------
    launcher_dwo: Path
        Path to the Dynawo launcher.
    debug: bool
        Flag to enable debug mode.
    """

    tool_path = Path(__file__).resolve().parent.parent
    _setup_user_config()
    _setup_templates_and_models(tool_path)
    _initialize_logger(debug)
    dycov_logging.get_logger("Initialization").info(f"Starting DyCoV - version {version('dycov')}")

    # Precompiled modelica models
    if launcher_dwo:
        _prepare_dynawo_models(launcher_dwo)
