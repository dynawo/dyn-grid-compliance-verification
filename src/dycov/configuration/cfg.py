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
    _config_dir: Path
    _default_config: configparser.ConfigParser
    _user_config: configparser.ConfigParser
    _pcs_config: configparser.ConfigParser

    def __get_valid_value(self, value: str) -> str:
        if value is None or value == "":
            return None
        return value

    def load_pcs_config(self, pcs_path: str) -> None:
        """Load the pcs CFG file.

        Parameters
        ----------
        pcs_path: str
            Name of the pcs file to read
        """
        self._pcs_config.read(pcs_path)

    def get_config_dir(self) -> Path:
        """Returns the configuration path.

        Returns
        -------
        Path
            Defined configuration path
        """
        return self._config_dir

    def has_key(self, section: str, key: str) -> bool:
        """Check if config contains element with key and section.

        Parameters
        ----------
        section: str
            Section header
        key: str
            Key in a section

        Returns
        -------
        bool
            True if exists the given key and section, False otherwise
        """
        return (
            self._user_config.has_option(section, key)
            or self._pcs_config.has_option(section, key)
            or self._default_config.has_option(section, key)
        )

    def get_value(self, section: str, key: str) -> Optional[str]:
        """Gets an element for a given key and section, if it doesn't exist it returns None.

        The priority defined in the configuration is:
          1 user config
          2 pcs config
          3 default config

        Parameters
        ----------
        section: str
            Section header
        key: str
            Key in a section

        Returns
        -------
        Optional[str]
            A string if exists the given key and section, None otherwise
        """
        value = None
        if self._user_config.has_option(section, key):
            value = self._user_config.get(section, key)
        if not self.__get_valid_value(value) and self._pcs_config.has_option(section, key):
            value = self._pcs_config.get(section, key)
        if not self.__get_valid_value(value) and self._default_config.has_option(section, key):
            value = self._default_config.get(section, key)
        return self.__get_valid_value(value)

    def get_int(self, section: str, key: str, default: int) -> int:
        """Gets an integer for a given key and section.

        Parameters
        ----------
        section: str
            Section header
        key: str
            Key in a section
        default: int
            Default value if the given key and section do not exist

        Returns
        -------
        int
            An integer if exists the given key and section, default otherwise
        """
        value = self.get_value(section, key)
        if value is not None:
            return int(value)
        return default

    def get_float(self, section: str, key: str, default: float) -> float:
        """Gets a float for a given key and section.

        Parameters
        ----------
        section: str
            Section header
        key: str
            Key in a section
        default: float
            Default value if the given key and section do not exist

        Returns
        -------
        float
            A float if exists the given key and section, default otherwise
        """
        value = self.get_value(section, key)
        if value is not None:
            return float(value)
        return default

    def get_boolean(self, section: str, key: str, default: bool = False) -> bool:
        """Gets a boolean for a given key and section.

        Parameters
        ----------
        section: str
            Section header
        key: str
            Key in a section
        default: bool
            Default value if the given key and section do not exist

        Returns
        -------
        bool
            A boolean if exists the given key and section, False otherwise
        """
        value = self.get_value(section, key)
        if value is not None:
            return value.lower() == "true"
        return default

    def get_list(self, section: str, key: str) -> list:
        """Gets a list for a given key and section.

        Parameters
        ----------
        section: str
            Section header
        key: str
            Key in a section

        Returns
        -------
        bool
            A list if exists the given key and section, empty list otherwise
        """
        value = self.get_value(section, key)
        if value is not None:
            return value.split(",")
        return []

    def get_options(self, section: str) -> list:
        """Returns a list of keys of a section.

        Parameters
        ----------
        section: str
            Section header
        prefix: str


        Returns
        -------
        list
            A list of keys of a section that start with a given prefix, empty otherwise
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
            options = self._default_config.options(section)
            return options
        return []


def _get_instance() -> Config:
    if os.name == "nt":
        config_dir = Path.home() / "AppData/Local/dycov"
    else:
        config_dir = Path.home() / ".config/dycov"

    default_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    default_config.optionxform = str
    user_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    user_config.optionxform = str
    pcs_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    pcs_config.optionxform = str

    default_config.read(Path(__file__).resolve().parent / "defaultConfig.ini")

    config_file = config_dir
    if os.name != "nt":
        config_file = config_dir / "config.ini"
    user_config.read(config_file)
    return Config(config_dir, default_config, user_config, pcs_config)


config = _get_instance()
