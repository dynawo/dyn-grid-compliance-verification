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
import sys
from importlib.metadata import version
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.curves.dynawo.prepare_tool import precompile
from dycov.files import manage_files
from dycov.logging.logging import dycov_logging


class DycovInitializer:
    """
    Handles the initialization process for the DYCOV tool, including
    setting up user configurations, templates, models, and logging.
    """

    # --- Constants ---
    _DYCOV_CONFIG_SECTION = "dycov"
    _DYCOV_CONFIG_TYPE_KEY = "type"
    _DYCOV_CONFIG_VERSION_KEY = "version"
    _DYCOV_TOOL_VERSION = "1.0.0.RC"

    def __init__(self):
        """
        Initializes the DycovInitializer.
        """
        self._logger = dycov_logging.get_logger("Initialization")

    def init(self, launcher_dwo: Path, debug: bool) -> None:
        """
        Initializes the DYCOV tool by setting up the user configuration path,
        templates, models, and logging.

        Parameters
        ----------
        launcher_dwo: Path
            Path to the Dynawo launcher.
        debug: bool
            Flag to enable debug mode for logging.
        """
        tool_path = Path(__file__).resolve().parent.parent
        self._setup_user_config(tool_path)
        self._setup_templates_and_models(tool_path)
        self._initialize_logger(debug)
        self._logger.info(f"Starting DyCoV - version {version('dycov')}")

        # Precompile Modelica models if a Dynawo launcher is provided.
        if launcher_dwo:
            self._prepare_dynawo_models(launcher_dwo)

    def _setup_user_config(self, tool_path: Path):
        """
        Sets up the user configuration directory and files.
        This includes creating the config directory if it doesn't exist,
        and setting up basic and advanced configuration files.
        """
        if not config.get_config_dir().is_dir():
            manage_files.create_dir(config.get_config_dir())

        # Create basic and advanced configuration files from templates.
        manage_files.create_config_file(
            tool_path / "configuration" / "config.ini",
            config.get_config_dir() / "config.ini_BASIC",
        )
        manage_files.create_config_file(
            tool_path / "configuration" / "defaultConfig.ini",
            config.get_config_dir() / "config.ini_ADVANCED",
        )

        # Check and set up the main user config file.
        if not self._is_valid_config_file(config.get_config_dir() / "config.ini"):
            if not (config.get_config_dir() / "config.ini").is_file():
                # If no config file exists, create a basic one.
                manage_files.create_config_file(
                    tool_path / "configuration" / "config.ini",
                    config.get_config_dir() / "config.ini",
                )
            else:
                # If an invalid config file exists, check and update it.
                self._check_config_file(
                    tool_path / "configuration" / "defaultConfig.ini",
                    config.get_config_dir() / "config.ini",
                )

    def _setup_templates_and_models(self, tool_path: Path):
        """
        Sets up the template directories and user model dictionaries.
        """
        self._configure_templates(tool_path)
        self._configure_user_models()

    def _initialize_logger(self, debug: bool):
        """
        Initializes the logging system for the DYCOV tool.
        Sets up file and console loggers based on configuration settings.
        """
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

    def _template_cmd_config(self, template_path: Path):
        """
        Ensures the existence of a specific template command directory.
        """
        if not template_path.is_dir():
            manage_files.create_dir(template_path)

    def _configure_template_category(self, base_template_dir: Path, sub_template: str):
        """
        Configures subdirectories for a given template category (e.g., 'PCS', 'reports').
        """
        category_path = base_template_dir / sub_template
        self._template_cmd_config(category_path)  # Create the base category directory

        subdirs = ["model", "performance"]
        models = ["BESS", "PPM", "SM"]

        for subdir in subdirs:
            self._template_cmd_config(category_path / subdir)
            for model in models:
                self._template_cmd_config(category_path / subdir / model)

    def _configure_templates(self, tool_path: Path):
        """
        Sets up the overall template directory structure and copies necessary template files.
        """
        templates_to_configure = ["PCS", "reports"]
        config_templates_dir = config.get_config_dir() / "templates"

        # Create base templates directory if it doesn't exist
        if not config_templates_dir.is_dir():
            manage_files.create_dir(config_templates_dir)

        for template in templates_to_configure:
            self._configure_template_category(config_templates_dir, template)
            self._copy_dummy_samples(tool_path, template)

        # Copy top-level READMEs and report-specific assets
        manage_files.copy_files(tool_path / "templates" / "README.md", config_templates_dir)
        for template in templates_to_configure:
            manage_files.copy_files(
                tool_path / "templates" / template / "README.md",
                config_templates_dir / template,
            )
        manage_files.copy_files(
            tool_path / "templates" / "reports" / "TSO_logo.pdf",
            config_templates_dir / "reports",
        )
        manage_files.copy_files(
            tool_path / "templates" / "reports" / "fig_placeholder.pdf",
            config_templates_dir / "reports",
        )

    def _copy_dummy_samples(self, tool_path: Path, source: str):
        """
        Copies dummy sample files from the tool's templates to the user's configuration directory.
        """
        categories = ["performance", "model"]
        models = ["SM", "PPM", "BESS"]
        for category in categories:
            for model in models:
                src = tool_path / "templates" / source / category / model / ".DummySample"
                dest = (
                    config.get_config_dir()
                    / "templates"
                    / source
                    / category
                    / model
                    / ".DummySample"
                )
                if src.exists():
                    try:
                        manage_files.copy_path(src, dest, dirs_exist_ok=True)
                    except Exception as e:
                        self._logger.error(f"Failed to copy {src} to {dest}: {e}")

    def _configure_user_models(self):
        """
        Sets up the user models directory and creates empty dictionary files.
        """
        user_models_dict_path = config.get_config_dir() / "user_models" / "dictionary"
        if not user_models_dict_path.is_dir():
            manage_files.create_dir(user_models_dict_path)

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
            manage_files.create_empty_file(user_models_dict_path / file)

    def _is_valid_config_file(self, config_file: Path) -> bool:
        """
        Checks if the provided configuration file is valid based on version.

        Parameters
        ----------
        config_file: Path
            The path to the configuration file to check.

        Returns
        -------
        bool
            True if the configuration file is valid, False otherwise.
        """
        if not config_file.is_file():
            return False

        cfg_parser = configparser.ConfigParser(inline_comment_prefixes=("#",))
        cfg_parser.read(config_file)
        if not cfg_parser.has_option(self._DYCOV_CONFIG_SECTION, self._DYCOV_CONFIG_VERSION_KEY):
            return False

        if (
            cfg_parser.get(self._DYCOV_CONFIG_SECTION, self._DYCOV_CONFIG_VERSION_KEY)
            != self._DYCOV_TOOL_VERSION
        ):
            return False

        return True

    def _prepare_dynawo_models(self, launcher_dwo: Path) -> None:
        """
        Precompiles Dynawo models.

        Parameters
        ----------
        launcher_dwo: Path
            Path to the Dynawo launcher.
        """
        is_aborted = precompile(launcher_dwo)
        if is_aborted:
            sys.exit()

    def _check_config_file(self, tool_config_file: Path, user_config_file: Path):
        """
        Compares the user's configuration file with the tool's default
        configuration, identifies deprecated parameters, and updates the user's file.

        Parameters
        ----------
        tool_config_file: Path
            Path to the tool's default configuration file.
        user_config_file: Path
            Path to the user's configuration file.
        """
        tool_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        tool_config.read(tool_config_file)
        user_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        user_config.read(user_config_file)

        deprecated_parameters = self._find_deprecated_parameters(tool_config, user_config)
        self._log_deprecated_parameters(deprecated_parameters, user_config_file.name)
        self._backup_and_update_user_config(user_config_file, user_config)

    def _find_deprecated_parameters(
        self, tool_config: configparser.ConfigParser, user_config: configparser.ConfigParser
    ) -> list:
        """
        Identifies parameters in the user's config that are deprecated compared to the
        tool's config.
        """
        deprecated = []
        for section in user_config.sections():
            for key in user_config.options(section):
                if not tool_config.has_option(section, key):
                    deprecated.append(
                        {"section": section, "key": key, "value": user_config.get(section, key)}
                    )
        return deprecated

    def _log_deprecated_parameters(self, deprecated_parameters: list, file_name: str):
        """
        Logs warnings for deprecated parameters found in the user's configuration file.
        """
        for parameter in deprecated_parameters:
            self._logger.warning(
                f"Deprecated in {file_name}: section {parameter['section']} "
                f"key {parameter['key']} value {parameter['value']}"
            )

    def _backup_and_update_user_config(
        self, user_config_file: Path, user_config: configparser.ConfigParser
    ):
        """
        Backs up the current user configuration file and updates it based on the
        tool's default or advanced configuration.
        """
        self._backup_config_file(user_config_file)
        self._write_updated_config(user_config_file, user_config)

    def _backup_config_file(self, user_config_file: Path):
        """
        Creates a backup of the user's configuration file with a timestamp.
        """
        existing_backups = [
            int(path.name.replace("config.ini.OLD.", ""))
            for path in config.get_config_dir().glob("config.ini.OLD.*")
        ]
        next_id = max(existing_backups) + 1 if existing_backups else 0
        user_config_file.rename(config.get_config_dir() / f"config.ini.OLD.{next_id}")

    def _write_updated_config(
        self, user_config_file: Path, user_config: configparser.ConfigParser
    ):
        """
        Writes the updated configuration to the main config.ini file,
        merging values from the old user config if applicable.
        """
        # Determine which base configuration file to use (basic or advanced).
        if (
            not user_config.has_section(self._DYCOV_CONFIG_SECTION)
            or not user_config.has_option(self._DYCOV_CONFIG_SECTION, self._DYCOV_CONFIG_TYPE_KEY)
            or user_config.get(self._DYCOV_CONFIG_SECTION, self._DYCOV_CONFIG_TYPE_KEY) == "basic"
        ):
            source_config_path = config.get_config_dir() / "config.ini_BASIC"
        else:
            source_config_path = config.get_config_dir() / "config.ini_ADVANCED"

        # Read the source config and write to the main config.ini,
        # incorporating existing user settings where applicable.
        with open(source_config_path, "r") as input_file:
            with open(config.get_config_dir() / "config.ini", "w") as output_file:
                current_section = ""
                for line in input_file:
                    output_file.write(line)
                    if line.strip().startswith("[") and line.strip().endswith("]"):
                        current_section = line.strip()[1:-1]
                    elif (
                        "=" in line and "#" not in line.split("=")[0]
                    ):  # Only consider lines with assignment, ignoring commented-out lines
                        key = line.split("=")[0].strip()
                        if user_config.has_option(current_section, key):
                            # Overwrite with user's existing value if present.
                            output_file.write(f"{key} = {user_config.get(current_section, key)}\n")


# Instantiate the initializer for external use
dycov_initializer = DycovInitializer()
