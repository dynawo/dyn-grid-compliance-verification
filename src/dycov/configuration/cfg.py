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
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dycov.logging.logging import dycov_logging


@dataclass(frozen=True)
class Config:
    """Manages application configuration from various sources.

    Configuration is loaded with the following priority:
    1. User configuration
    2. Performance Checking Sheet (PCS) configuration
    3. Default configuration

    Attributes
    ----------
    _config_dir: Path
        The directory where configuration files are located.
    _default_config: configparser.ConfigParser
        Parser for the default configuration.
    _user_config: configparser.ConfigParser
        Parser for the user-specific configuration.
    _pcs_config: configparser.ConfigParser
        Parser for the Performance Checking Sheet (PCS) configuration.
    """

    _config_dir: Path
    _default_config: configparser.ConfigParser
    _user_config: configparser.ConfigParser
    _pcs_config: configparser.ConfigParser

    def _is_valid_value(self, value: str) -> bool:
        """Internal helper to validate if a string value is not None or empty.

        Parameters
        ----------
        value: str
            The string value to validate.

        Returns
        -------
        bool
            True if the validated string is not None or empty, otherwise False.
        """
        return value is not None and value != ""

    def _get_config_value(self, section: str, key: str) -> Optional[str]:
        """Gets a configuration value for a given key and section.

        The priority defined in the configuration is:
          1. User config
          2. Performance Checking Sheet (PCS) config
          3. Default config

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.

        Returns
        -------
        Optional[str]
            The string value if it exists, None otherwise.
        """
        if self._user_config.has_option(section, key):
            value = self._user_config.get(section, key)
            if self._is_valid_value(value):
                return value

        if self._pcs_config.has_option(section, key):
            value = self._pcs_config.get(section, key)
            if self._is_valid_value(value):
                return value

        if self._default_config.has_option(section, key):
            value = self._default_config.get(section, key)
            if self._is_valid_value(value):
                return value

        return None

    def load_pcs_config(self, pcs_path: str) -> None:
        """Load the Performance Checking Sheet (PCS) configuration file. It
        also implements an inheritance mechanism using alias files.
        It searches for any file named "*aliases*" located two levels above the
        pcs path. If a section in the main config contains an "inherit" key,
        it will load the key-value pairs from the corresponding section in the
        alias files. This allows for shared, default configurations.
        Values already present in the main config section will NOT be overwritten.

        Parameters
        ----------
        pcs_path: str
            Path to the PCS configuration file to read.
        """
        dycov_logging.get_logger("Cfg").info("Loading PCS configuration from: %s", pcs_path)
        try:
            self._pcs_config.read(pcs_path, encoding="utf-8")

            single_pcs_config = configparser.ConfigParser()
            single_pcs_config.read(pcs_path, encoding="utf-8")

            pcs_aliases_path = Path(pcs_path).resolve().parent.parent
            aliases_files = [str(p) for p in pcs_aliases_path.rglob("*aliases*") if p.is_file()]

            aliases_config = configparser.ConfigParser()
            aliases_config.optionxform = str
            aliases_config.read(aliases_files, encoding="utf-8")

            for section_to_modify in list(self._pcs_config.sections()):
                if self._pcs_config.has_option(section_to_modify, "inherit"):
                    alias_section_name = self._pcs_config.get(section_to_modify, "inherit")
                    if aliases_config.has_section(alias_section_name):
                        for key_to_inherit, value_to_inherit in aliases_config.items(
                            alias_section_name
                        ):
                            if not single_pcs_config.has_option(section_to_modify, key_to_inherit):
                                self._pcs_config.set(
                                    section_to_modify, key_to_inherit, value_to_inherit
                                )
                        self._pcs_config.remove_option(section_to_modify, "inherit")
                    else:
                        dycov_logging.get_logger("Cfg").warning(
                            f"  [WARNING] The alias section '[{alias_section_name}]' was not found"
                            " in the alias files."
                        )

            dycov_logging.get_logger("Cfg").info("Successfully loaded PCS configuration.")
        except Exception as e:
            dycov_logging.get_logger("Cfg").error(
                "Error loading PCS configuration from %s: %s", pcs_path, e
            )
            raise

    def get_config_dir(self) -> Path:
        """Returns the configuration directory path.

        Returns
        -------
        Path
            The defined configuration directory path.
        """
        return self._config_dir

    def has_option(self, section: str, key: str) -> bool:
        """Check if config contains the specified key within any configuration source.

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.

        Returns
        -------
        bool
            True if the key exists in any of the configuration sources, False otherwise.
        """
        return (
            self._user_config.has_option(section, key)
            or self._pcs_config.has_option(section, key)
            or self._default_config.has_option(section, key)
        )

    def set_value(self, section: str, key: str, value: str) -> None:
        """Sets (or overrides) a configuration value at runtime using the same
        precedence policy as get_value().

        The precedence to choose the target source mirrors get_value() by checking:
        1. User config
        2. PCS config
        3. Default config

        Concretely:
        - If (section, key) exists with a valid (non-empty) value in user → pcs → default
        (checked with _is_valid_value), the override is applied in that same source.
        - If it does not exist in any source with a valid value, the key is created in
        the user config.

        This method updates the in-memory configuration and creates the section if it
        does not exist. It does not persist values to disk.

        Parameters
        ----------
        section : str
            Section header.
        key : str
            Key within the section.
        value : str
            New value to set.

        Returns
        -------
        None
            The value is set in-memory. No value is returned.
        """
        target_parser = None

        # user
        if self._user_config.has_option(section, key):
            current = self._user_config.get(section, key)
            if self._is_valid_value(current):
                target_parser = self._user_config

        # pcs (solo si no se decidió aún)
        if target_parser is None and self._pcs_config.has_option(section, key):
            current = self._pcs_config.get(section, key)
            if self._is_valid_value(current):
                target_parser = self._pcs_config

        # default (solo si no se decidió aún)
        if target_parser is None and self._default_config.has_option(section, key):
            current = self._default_config.get(section, key)
            if self._is_valid_value(current):
                target_parser = self._default_config

        # Si no se encontró un valor válido en ningún origen, crear en user
        if target_parser is None:
            target_parser = self._user_config

        # Asegurar la sección en el origen elegido
        if not target_parser.has_section(section):
            target_parser.add_section(section)

        # Log old -> new y escribir
        target_parser.set(section, key, value)

    def get_value(self, section: str, key: str, default: str = None) -> str:
        """Gets a configuration value for a given key and section.

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.
        default: str
            Default value to return if the key is not found.

        Returns
        -------
        str
            The string value if it exists, otherwise the default value.
        """
        value = self._get_config_value(section, key)
        if value is None:
            return default
        return value

    def get_int(self, section: str, key: str, default: int) -> int:
        """Gets an integer value for a given key and section.

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.
        default: int
            Default value to return if the key is not found.

        Returns
        -------
        int
            The integer value if it exists, otherwise the default value.
        """
        value = self._get_config_value(section, key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            dycov_logging.get_logger("Cfg").error(
                f"Could not convert value '{value}' to integer for "
                f"section '{section}', key '{key}'. Using default: {default}"
            )
            return default

    def get_float(self, section: str, key: str, default: float) -> float:
        """Gets a float value for a given key and section.

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.
        default: float
            Default value to return if the key is not found.

        Returns
        -------
        float
            The float value if it exists, otherwise the default value.
        """
        value = self._get_config_value(section, key)
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            dycov_logging.get_logger("Cfg").error(
                f"Could not convert value '{value}' to float for "
                f"section '{section}', key '{key}'. Using default: {default}",
            )
            return default

    def get_boolean(self, section: str, key: str, default: bool = False) -> bool:
        """Gets a boolean value for a given key and section.

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.
        default: bool
            Default value to return if the key is not found (default is False).

        Returns
        -------
        bool
            The boolean value if it exists, otherwise the default value.
        """
        value = self._get_config_value(section, key)
        if value is None:
            return default
        return value.lower() == "true"

    def get_list(self, section: str, key: str) -> list:
        """Gets a list of string values for a given key and section.
        Values are assumed to be comma-separated in the configuration file.

        Parameters
        ----------
        section: str
            Section header.
        key: str
            Key within the section.

        Returns
        -------
        list
            A list of strings if the key exists, an empty list otherwise.
        """
        value = self._get_config_value(section, key)
        if value is None:
            return []
        return value.split(",")

    def get_options(self, section: str) -> list:
        """Returns a list of keys of a section.

        The priority for retrieving options is:
        1. User config
        2. Performance Checking Sheet (PCS) config
        3. Default config

        Parameters
        ----------
        section: str
            Section header.

        Returns
        -------
        list
            A list of keys in the specified section, or an empty list otherwise.
        """
        if self._user_config.has_section(section):
            options = self._user_config.options(section)
            if options:
                return options

        if self._pcs_config.has_section(section):
            options = self._pcs_config.options(section)
            if options:
                return options

        if self._default_config.has_section(section):
            return self._default_config.options(section)

        return []


def _get_instance() -> Config:
    """Internal function to create and return a singleton Config instance.

    This function sets up the configuration directories and loads default
    and user-specific configuration files.

    Returns
    -------
    Config
        A Config object initialized with default, user, and PCS config parsers.
    """
    dycov_logging.get_logger("Cfg").info("Initializing Config instance.")
    config_dir = Path.home() / ("AppData/Local/dycov" if os.name == "nt" else ".config/dycov")
    dycov_logging.get_logger("Cfg").debug("Config directory set to: %s", config_dir)

    # Initialize ConfigParser objects for different configuration sources
    default_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    default_config.optionxform = str
    user_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    user_config.optionxform = str
    pcs_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    pcs_config.optionxform = str

    # Load default configuration from the package
    default_config_path = Path(__file__).resolve().parent / "defaultConfig.ini"
    dycov_logging.get_logger("Cfg").info(
        "Loading default configuration from: %s", default_config_path
    )
    try:
        if not default_config_path.exists():
            dycov_logging.get_logger("Cfg").warning(
                "Default configuration file not found at: %s", default_config_path
            )
        default_config.read(default_config_path)
        dycov_logging.get_logger("Cfg").info("Successfully loaded default configuration.")
    except Exception as e:
        dycov_logging.get_logger("Cfg").error(
            "Error loading default configuration from %s: %s", default_config_path, e
        )
        raise

    # Load user configuration
    user_config_file = config_dir / (
        "config.ini" if os.name != "nt" else ""
    )  # Adjusted for Windows not needing /config.ini suffix
    dycov_logging.get_logger("Cfg").info("Loading user configuration from: %s", user_config_file)
    try:
        if not user_config_file.exists():
            dycov_logging.get_logger("Cfg").debug(
                "User configuration file not found at: %s (This is often expected)",
                user_config_file,
            )
        user_config.read(user_config_file)
        dycov_logging.get_logger("Cfg").info("Successfully loaded user configuration.")
    except Exception as e:
        dycov_logging.get_logger("Cfg").warning(
            "Could not load user configuration from %s: %s", user_config_file, e
        )

    return Config(config_dir, default_config, user_config, pcs_config)


# Global instance of the Config class
config = _get_instance()
