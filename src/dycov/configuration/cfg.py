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

    def _get_valid_value(self, value: str) -> Optional[str]:
        """Internal helper to validate if a string value is not None or empty.

        Parameters
        ----------
        value: str
            The string value to validate.

        Returns
        -------
        Optional[str]
            The validated string if not None or empty, otherwise None.
        """
        return value if value is not None and value != "" else None

    def load_pcs_config(self, pcs_path: str) -> None:
        """Load the Performance Checking Sheet (PCS) configuration file.

        Parameters
        ----------
        pcs_path: str
            Path to the PCS configuration file to read.
        """
        self._pcs_config.read(pcs_path)

    def get_config_dir(self) -> Path:
        """Returns the configuration directory path.

        Returns
        -------
        Path
            The defined configuration directory path.
        """
        return self._config_dir

    def has_key(self, section: str, key: str) -> bool:
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

    def get_value(self, section: str, key: str) -> Optional[str]:
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
        value = None
        if self._user_config.has_option(section, key):
            value = self._user_config.get(section, key)

        if not self._get_valid_value(value) and self._pcs_config.has_option(section, key):
            value = self._pcs_config.get(section, key)

        if not self._get_valid_value(value) and self._default_config.has_option(section, key):
            value = self._default_config.get(section, key)

        return self._get_valid_value(value)

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
        value = self.get_value(section, key)
        return int(value) if value is not None else default

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
        value = self.get_value(section, key)
        return float(value) if value is not None else default

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
        value = self.get_value(section, key)
        return value.lower() == "true" if value is not None else default

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
        value = self.get_value(section, key)
        return value.split(",") if value is not None else []

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
        options = []
        if self._user_config.has_section(section):
            options = self._user_config.options(section)
            if options:  # Check if the list of options is not empty
                return options

        if self._pcs_config.has_section(section):
            options = self._pcs_config.options(section)
            if options:  # Check if the list of options is not empty
                return options

        if self._default_config.has_section(section):
            options = self._default_config.options(section)
            return options  # Return default options even if empty

        return []  # If no section found in any config


def _get_instance() -> Config:
    """Internal function to create and return a singleton Config instance.

    This function sets up the configuration directories and loads default
    and user-specific configuration files.

    Returns
    -------
    Config
        A Config object initialized with default, user, and PCS config parsers.
    """
    # Determine configuration directory based on operating system
    if os.name == "nt":
        config_dir = Path.home() / "AppData/Local/dycov"
    else:
        config_dir = Path.home() / ".config/dycov"

    # Initialize ConfigParser objects for different configuration sources
    default_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    default_config.optionxform = str  # Preserve case for options
    user_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    user_config.optionxform = str
    pcs_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    pcs_config.optionxform = str

    # Load default configuration from the package
    default_config.read(Path(__file__).resolve().parent / "defaultConfig.ini")

    # Load user configuration
    user_config_file = config_dir
    if os.name != "nt":
        user_config_file = config_dir / "config.ini"
    user_config.read(user_config_file)

    return Config(config_dir, default_config, user_config, pcs_config)


# Global instance of the Config class
config = _get_instance()
